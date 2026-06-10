"""
LLM-vs-baseline unified-comparison framework.

This module hosts the pieces that bridge the historic_data ground-truth
paragraphs (in Romanian) and the multi-LLM forecasting setup. Built up
in stages; the first stage (this commit) provides the Romanian zone
parser used both to drive prompt construction and to extract structured
predictions from LLM outputs.

Subsequent stages will add:
  - prompt builders (system + user) for the five input modes and the
    two scenarios (daily 6/12/18/24 days, monthly 3/6/9 months)
  - Ollama client wrapper with per-model context sizing + chat history
  - manual scoring algorithm (hyperbolic per-station distance, formula
    from the user's spec)
  - LLM-as-a-judge scorer
  - one-shot test runner persisting per-LLM JSON outputs
  - comparison plotter (baselines vs LLMs, manual vs judge)

The parser is intentionally regex + lookup based rather than heuristic
NLP - the ANM ground-truth paragraphs follow a very limited vocabulary
of zones, so an exhaustive lookup is more reliable than a generic
parser would be.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Zone vocabulary
# ---------------------------------------------------------------------------
#
# Each entry maps a Romanian phrase (in its base / lemmatised form) to a
# resolved zone key. The key is structured as:
#
#   axis:identifier
#
# where axis is one of:
#   - region:           whole ANM CMR region (resolves to all stations
#                       in that region across all 41 counties)
#   - region_compound:  a label that decomposes into multiple regions
#                       (e.g. 'Transilvania' = TransilvaniaN + S, or
#                       'Banat și Crișana' which is one ANM region but
#                       the GT uses the compound name)
#   - climatic:         a climatic zone in stations_by_climatology
#   - cardinal:         region/direction, e.g. 'Muntenia/S'
#
# The phrases are matched case-insensitively and diacritic-insensitively
# (via _strip_diacritics) so the GT's natural Romanian spelling matches
# correctly.

_REGION_BASE_NAMES = {
    "Muntenia": "Muntenia",
    "Dobrogea": "Dobrogea",
    "Moldova":  "Moldova",
    "Oltenia":  "Oltenia",
    "TransilvaniaN": "TransilvaniaN",
    "TransilvaniaS": "TransilvaniaS",
    "Banat-Crisana": "Banat-Crisana",
}

# Romanian declensions: each region typically appears in the nominative
# ("Muntenia") and the definite-genitive ("Munteniei") form. The
# parser matches both. Note that "Banat-Crisana" rarely shows up under
# that exact label - the GT uses "Banat" and "Crișana" separately or
# together as "Banat și Crișana" - so we handle it via the compound list.
_REGION_DECLENSIONS = {
    # phrase (lower, diacritic-stripped) -> resolved key
    "muntenia":     "region:Muntenia",
    "munteniei":    "region:Muntenia",
    "dobrogea":     "region:Dobrogea",
    "dobrogei":     "region:Dobrogea",
    "moldova":      "region:Moldova",
    "moldovei":     "region:Moldova",
    "oltenia":      "region:Oltenia",
    "olteniei":     "region:Oltenia",
    "transilvania":     "region_compound:Transilvania",
    "transilvaniei":    "region_compound:Transilvania",
    "banatului":    "region_part:Banat",
    "banat":        "region_part:Banat",
    "crisanei":     "region_part:Crisana",
    "crisana":      "region_part:Crisana",
    # Sub-region inside TransilvaniaN; ANM treats it as a county tier
    # but the GT often uses it as a coarse zone.
    "maramures":        "subregion:Maramures",
    "maramuresului":    "subregion:Maramures",
}

# Climatic zones. Keys are phrase lemmas (lower, diacritic-stripped).
# Values are the EXACT key from stations_by_climatology so the lookup
# resolves straight to a station list.
_CLIMATIC_DECLENSIONS = {
    "litoral":                          "climatic:Litoral",
    "litoralul":                        "climatic:Litoral",
    "delta dunarii":                    "climatic:Delta Dunării",
    "delta":                            "climatic:Delta Dunării",
    "campie":                           "climatic:Câmpie (zone joase extracarpatice)",
    "campia":                           "climatic:Câmpie (zone joase extracarpatice)",
    "zonele extracarpatice":            "climatic:Câmpie (zone joase extracarpatice)",
    "zona de deal si podis":            "climatic:Zona de deal și podiș",
    "deal si podis":                    "climatic:Zona de deal și podiș",
    "podisuri":                         "climatic:Zona de deal și podiș",
    "zona submontana":                  "climatic:Zona submontană",
    "submontana":                       "climatic:Zona submontană",
    "depresiunile intramontane":        "climatic:Depresiuni intramontane",
    "depresiuni intramontane":          "climatic:Depresiuni intramontane",
    "interiorul arcului carpatic":      "climatic:Depresiuni intramontane",
    "interiorul carpatic":              "climatic:Depresiuni intramontane",
    "zona montana":                     "climatic:Zona montană",
    "zonele montane":                   "climatic:Zona montană",
    "zona montana inalta":              "climatic:Zona montană înaltă",
    "munti":                            "climatic:Zona montană",
    "creste":                           "climatic:Creste montane (peste 2500 m)",
    "creste montane":                   "climatic:Creste montane (peste 2500 m)",
}

# Cardinal modifiers. The cardinal_points file only has N/S/E/V; map
# compound directions to the nearest single direction by taking the
# leading component (per the user's spec).
_CARDINAL_LEMMAS = {
    # Single-direction bare and definite-article forms
    "nord":     "N",
    "nordul":   "N",
    "sud":      "S",
    "sudul":    "S",
    "est":      "E",
    "estul":    "E",
    "vest":     "V",
    "vestul":   "V",
    # Compound directions: per the user's spec, map to the FIRST
    # component (the dominant direction). Hyphenated and non-hyphenated
    # variants, with and without the -ul definite article.
    "nord-est":   "N",
    "nord-estul": "N",
    "nordest":    "N",
    "nordestul":  "N",
    "nord-vest":  "N",
    "nord-vestul": "N",
    "nordvest":   "N",
    "nordvestul": "N",
    "sud-est":    "S",
    "sud-estul":  "S",
    "sudest":     "S",
    "sudestul":   "S",
    "sud-vest":   "S",
    "sud-vestul": "S",
    "sudvest":    "S",
    "sudvestul":  "S",
    # Adjective forms (gender/number agreement)
    "estic":      "E",
    "estica":     "E",
    "estice":     "E",
    "vestic":     "V",
    "vestica":    "V",
    "vestice":    "V",
    "nordic":     "N",
    "nordica":    "N",
    "nordice":    "N",
    "sudic":      "S",
    "sudica":     "S",
    "sudice":     "S",
}

# Modifiers that should NOT contribute a cardinal subdivision but
# should keep the parser from falling back to "whole region". The
# rule from the spec: if there's no cardinality, use the whole region;
# 'centrul' and 'interior' / 'mijloc' end up exactly there.
_NEUTRAL_REGION_MODIFIERS = {
    "centrul",
    "central",
    "centrala",
    "interiorul",
    "interior",
    "mijlocul",
    "mijloc",
    "majoritatea",
    "izolat",
    "cea mai mare parte a",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_diacritics(s: str) -> str:
    """Lower-case + drop combining marks so 'Munteniei' and 'munteniei'
    both reduce to 'munteniei' and so 'sud-estul' matches whether it has
    typed Romanian diacritics or not."""
    if not s:
        return ""
    nfkd = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def load_stations_metadata(
    path: str | Path = "date/stations_metadata.json",
) -> dict:
    """
    Load the merged stations metadata produced by the
    `combine_stations_metadata` subcommand of
    `prompting.utils.check_data_availability`. Raises a clear error
    pointing at the right rebuild command if the file is missing.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(
            f"{p} not found. Build it with:\n"
            f"  python -m prompting.utils.check_data_availability "
            f"combine_stations_metadata"
        )
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Zone resolution
# ---------------------------------------------------------------------------

def _resolve_to_stations(
    zone_key: str,
    metadata: dict,
    cardinal: Optional[str] = None,
) -> List[str]:
    """
    Convert a resolved zone key (one of axis:identifier) into the list
    of station IDs it covers. Honours an optional cardinal modifier:

      (region:Muntenia, cardinal=None)  -> all Muntenia stations
      (region:Muntenia, cardinal='S')   -> Muntenia/S stations only
      (climatic:Litoral, *)             -> stations in the Litoral zone
      (region_compound:Transilvania)    -> TransilvaniaN + TransilvaniaS
      (region_part:Banat, ...)          -> Banat-Crisana stations in
                                            the corresponding cardinal
                                            subdivision (Banat = N+S+V
                                            of Banat-Crisana per ANM
                                            convention; Crișana = E+W
                                            roughly). We approximate by
                                            taking the whole region in
                                            the absence of cardinal info.
      (subregion:Maramures, ...)        -> TransilvaniaN/N stations
                                            (Maramures sits roughly
                                            there in the cardinal file).

    Returns an empty list if the zone can't be resolved (this is rare
    given the vocabulary but possible if the regions JSON has been
    regenerated and a zone disappeared).
    """
    if ":" not in zone_key:
        return []
    axis, ident = zone_key.split(":", 1)

    if axis == "climatic":
        return list(metadata["by_climatology"].get(ident, []))

    if axis == "region":
        if cardinal:
            return list(metadata["by_cardinal"].get(ident, {}).get(cardinal, []))
        # All stations in all counties of the region
        return [
            s
            for county_stations in metadata["by_region"].get(ident, {}).values()
            for s in county_stations
        ]

    if axis == "region_compound" and ident == "Transilvania":
        out: List[str] = []
        for r in ("TransilvaniaN", "TransilvaniaS"):
            if cardinal:
                out.extend(metadata["by_cardinal"].get(r, {}).get(cardinal, []))
            else:
                for s in metadata["by_region"].get(r, {}).values():
                    out.extend(s)
        return out

    if axis == "region_part":
        # Banat / Crișana within Banat-Crisana - the ANM CMR file
        # treats them as one. Without a finer subdivision JSON the
        # best we can do is the whole Banat-Crisana region (with the
        # optional cardinal modifier applied if given).
        if cardinal:
            return list(metadata["by_cardinal"].get("Banat-Crisana", {}).get(cardinal, []))
        return [
            s
            for county_stations in metadata["by_region"].get("Banat-Crisana", {}).values()
            for s in county_stations
        ]

    if axis == "subregion" and ident == "Maramures":
        # Maramureș is a county (MM). Pull its stations directly out
        # of the regions-by-county map.
        for region_counties in metadata["by_region"].values():
            if "MM" in region_counties:
                return list(region_counties["MM"])
        return []

    return []


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

# Precompile the matching patterns. Match the longest phrases first so
# 'sud-estul' wins over 'sud', 'delta dunarii' over 'delta', etc.
_REGION_PHRASES = sorted(_REGION_DECLENSIONS.keys(), key=len, reverse=True)
_CLIMATIC_PHRASES = sorted(_CLIMATIC_DECLENSIONS.keys(), key=len, reverse=True)
_CARDINAL_PHRASES = sorted(_CARDINAL_LEMMAS.keys(), key=len, reverse=True)
_NEUTRAL_PHRASES = sorted(_NEUTRAL_REGION_MODIFIERS, key=len, reverse=True)

# Regex helper: a word-boundary safe-ish match. Romanian words can be
# preceded/followed by Romanian-specific characters that aren't \w in
# the default regex flavour, so we use lookaround with explicit
# allow-list rather than \b.
_WORD_CHARS = "a-zA-Z0-9"


def _word_boundary_search(text_norm: str, phrase: str) -> List[Tuple[int, int]]:
    """Find all non-overlapping spans of `phrase` in `text_norm` with
    rough word boundaries on each side. Both arguments must already be
    in the normalised (diacritic-stripped, lower-case) form."""
    spans = []
    pat = re.compile(
        r"(?:^|[^" + _WORD_CHARS + r"])("
        + re.escape(phrase)
        + r")(?=$|[^" + _WORD_CHARS + r"])"
    )
    for m in pat.finditer(text_norm):
        spans.append(m.span(1))
    return spans


def extract_zones_from_text(
    text: str,
    metadata: dict,
) -> List[Dict]:
    """
    Extract every zone reference in `text` (a Romanian paragraph or a
    chunk of GT). Each returned record carries:

      - raw_phrase:  the substring (in the original text) that matched
      - axis:        'climatic' | 'region' | 'region_compound' |
                     'region_part' | 'subregion'
      - key:         the resolved zone key, e.g. 'region:Muntenia'
      - cardinal:    'N'|'S'|'E'|'V'|None - cardinal modifier if one
                     appeared adjacent to the region phrase
      - stations:    list of station IDs the zone covers (after
                     applying the cardinal modifier when present)
      - span:        (start, end) character offsets in the normalised
                     text - used for de-duplication and for the
                     LLM-output parser to slice out the [x, y] adjacent
                     to each zone mention

    Climatic-zone matches take priority over region matches when they
    overlap (e.g. 'litoral' is matched as climatic, not as a region
    word).
    """
    text_norm = _strip_diacritics(text)
    out: List[Dict] = []
    consumed: List[Tuple[int, int]] = []   # spans already claimed

    def _claimed(start: int, end: int) -> bool:
        return any(not (end <= cs or start >= ce) for cs, ce in consumed)

    # --- 1) climatic zones (longest phrases first) ---
    for phrase in _CLIMATIC_PHRASES:
        for start, end in _word_boundary_search(text_norm, phrase):
            if _claimed(start, end):
                continue
            key = _CLIMATIC_DECLENSIONS[phrase]
            ident = key.split(":", 1)[1]
            stations = _resolve_to_stations(key, metadata)
            out.append({
                "raw_phrase": text[start:end],
                "axis": "climatic",
                "key": key,
                "ident": ident,
                "cardinal": None,
                "stations": stations,
                "span": (start, end),
            })
            consumed.append((start, end))

    # --- 2) regions, optionally preceded by a cardinal modifier ---
    for phrase in _REGION_PHRASES:
        for start, end in _word_boundary_search(text_norm, phrase):
            if _claimed(start, end):
                continue
            key = _REGION_DECLENSIONS[phrase]
            axis, ident = key.split(":", 1)
            # Look backwards up to ~30 chars for a cardinal modifier
            # like 'sud-estul', 'nordul', 'jumatatea vestica a'. We
            # only accept it if it sits in a short window (so an
            # unrelated 'vestul Carpatilor' two sentences earlier
            # doesn't bleed onto this region).
            cardinal: Optional[str] = None
            window_start = max(0, start - 40)
            window = text_norm[window_start:start]
            # Cardinal phrases first - longest match wins.
            for cp in _CARDINAL_PHRASES:
                cspans = _word_boundary_search(window, cp)
                if cspans:
                    # take the LATEST cardinal match in the window
                    cardinal = _CARDINAL_LEMMAS[cp]
                    break
            # Defer to neutral modifiers (centrul, interior, ...): if
            # one of them sits between the cardinal and the region,
            # don't accept the cardinal (the GT phrase is "centrul X",
            # not "sud X").
            if cardinal:
                for neutral in _NEUTRAL_PHRASES:
                    if _word_boundary_search(window, neutral):
                        # Tie-break: if the neutral modifier is closer
                        # to the region than the cardinal was, drop
                        # the cardinal. (Cheap approximation: just
                        # drop the cardinal.)
                        cardinal = None
                        break

            stations = _resolve_to_stations(key, metadata, cardinal=cardinal)
            out.append({
                "raw_phrase": text[start:end],
                "axis": axis,
                "key": key,
                "ident": ident,
                "cardinal": cardinal,
                "stations": stations,
                "span": (start, end),
            })
            consumed.append((start, end))

    # Sort by position so downstream consumers can iterate left-to-right.
    out.sort(key=lambda d: d["span"][0])
    return out


def dedupe_zones(zones: Sequence[Dict]) -> List[Dict]:
    """
    Collapse zone mentions that resolve to the same (key, cardinal)
    cell into a single record per cell. Used to assemble the unique
    set of zones across multiple GT paragraphs (spec: 'the extraction
    algorithm should have a check to not place in the user prompt the
    same zones that might appear in multiple months').

    Returns the zone records sorted by (axis, key, cardinal). The
    `span` field is dropped since cross-paragraph spans aren't
    comparable.
    """
    seen: Dict[Tuple[str, str, Optional[str]], Dict] = {}
    for z in zones:
        cell = (z["axis"], z["key"], z["cardinal"])
        if cell not in seen:
            # Strip the per-span context; we want one canonical record
            rec = {
                "axis": z["axis"],
                "key": z["key"],
                "ident": z["ident"],
                "cardinal": z["cardinal"],
                "stations": list(z["stations"]),
                "raw_phrase": z["raw_phrase"],
            }
            seen[cell] = rec
    return [seen[k] for k in sorted(seen.keys(), key=lambda c: (c[0], c[1], c[2] or ""))]


# ---------------------------------------------------------------------------
# LLM-output parsing: zones + [x, y] temperature ranges
# ---------------------------------------------------------------------------

# Regex for the strict bracketed temperature range the system prompt
# will mandate. Accepts optional whitespace and integer or one-decimal
# values, optionally followed by a "°C" / "C" unit which we discard.
_INTERVAL_RE = re.compile(
    r"\[\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\]"
    r"(?:\s*\xb0?\s*C)?",
    flags=re.IGNORECASE,
)


def extract_predictions_from_paragraph(
    text: str,
    metadata: dict,
) -> List[Dict]:
    """
    Parse an LLM-generated paragraph that follows the strict format:
    Romanian sentences each containing one or more zone references and
    a [x, y] temperature range. Returns one record per (zone mention,
    interval) pair, with the bin-midpoint precomputed for use by the
    downstream scoring algorithm.

    Pairing rule: each zone mention in a sentence is paired with the
    NEAREST [x, y] bracket in that sentence (by character distance),
    regardless of whether the bracket appears before or after the
    zone. This handles both the GT-natural ordering 'Mediile au fost
    cuprinse intre [0, 2] degC in Muntenia, Dobrogei si Olteniei'
    (interval first, three zones after) and the reverse 'In Muntenia,
    Dobrogei si Olteniei mediile au fost [0, 2]' (three zones, then
    interval).

    Returns:
      [
        {
          'raw_phrase': str,
          'axis': str,
          'key': str,
          'cardinal': str | None,
          'stations': [station, ...],
          'interval': [x: float, y: float],
          'midpoint': float,           # (x + y) / 2
          'sentence': str,             # the source sentence
        }, ...
      ]
    """
    out: List[Dict] = []
    # Sentence segmentation - simple, since the GT uses '. ' as the
    # boundary. Keep the period attached so per-sentence span math
    # downstream is straightforward.
    sentences = re.split(r"(?<=\.)\s+", text)
    cursor = 0
    for sent in sentences:
        sent_start = text.find(sent, cursor)
        if sent_start < 0:
            sent_start = cursor
        sent_end = sent_start + len(sent)
        cursor = sent_end

        intervals = [
            (m.start(), m.end(), float(m.group(1)), float(m.group(2)))
            for m in _INTERVAL_RE.finditer(sent)
        ]
        if not intervals:
            continue

        zones_in_sentence = extract_zones_from_text(sent, metadata)

        # Pair each zone with the NEAREST interval in the same
        # sentence (by character distance), regardless of order. With
        # multiple intervals in one sentence, ties go to the earliest
        # interval - rare in practice because the GT-style structure
        # tends to alternate 'phrase ... [x,y]'.
        for z in zones_in_sentence:
            zs, _ = z["span"]
            # Find the closest interval midpoint.
            best = None
            best_d = None
            for i_start, i_end, x, y in intervals:
                # Distance from zone span to interval span (zero if they overlap).
                mid_iv = (i_start + i_end) / 2.0
                d = abs(zs - mid_iv)
                if best_d is None or d < best_d:
                    best_d = d
                    best = (x, y)
            x, y = best
            out.append({
                "raw_phrase": z["raw_phrase"],
                "axis": z["axis"],
                "key": z["key"],
                "ident": z.get("ident"),
                "cardinal": z["cardinal"],
                "stations": list(z["stations"]),
                "interval": [x, y],
                "midpoint": (x + y) / 2.0,
                "sentence": sent.strip(),
            })
    return out
