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
import math
import os
import re
import unicodedata
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Romanian month vocabulary
# ---------------------------------------------------------------------------

ROMANIAN_MONTHS = [
    "Ianuarie", "Februarie", "Martie", "Aprilie", "Mai", "Iunie",
    "Iulie", "August", "Septembrie", "Octombrie", "Noiembrie", "Decembrie",
]


def romanian_month_name(month_int: int) -> str:
    """1-indexed Romanian month name. 1 -> Ianuarie, 12 -> Decembrie."""
    if not 1 <= month_int <= 12:
        raise ValueError(f"month_int out of range: {month_int}")
    return ROMANIAN_MONTHS[month_int - 1]


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
# values (one decimal is tolerated even though the system prompt asks
# for integers, so we can still recover and snap rather than drop the
# prediction outright), optionally followed by a "°C" / "C" unit which
# we discard.
_INTERVAL_RE = re.compile(
    r"\[\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\]"
    r"(?:\s*\xb0?\s*C)?",
    flags=re.IGNORECASE,
)

# Fluent-Romanian forms used in the ANM GT paragraphs (no brackets):
#   "intre 4 si 6 °C"  -> (4, 6)
#   "peste 6 °C"       -> (6, 8)    semi-open above, snapped to 2 degC bin
#   "sub 0 °C"         -> (-2, 0)   semi-open below
# 'peste' / 'sub' require a temperature unit (°C / C / degC / grade
# Celsius) so we don't false-match prose like "sub 5 minute". Unit
# spellings cover all ANM-typical variants.
_TEMP_UNIT_PATTERN = (
    r"(?:\xb0\s*[Cc]|deg\s*[Cc]|grad[ei]?(?:\s+Celsius)?|[Cc]\b)"
)
_INTRE_INTERVAL_RE = re.compile(
    r"\b(?:intre|într?e|între)\s+(-?\d+(?:\.\d+)?)\s+(?:si|și)\s+"
    r"(-?\d+(?:\.\d+)?)"
    r"(?:\s*" + _TEMP_UNIT_PATTERN + r")?",
    flags=re.IGNORECASE,
)
_PESTE_INTERVAL_RE = re.compile(
    r"\bpeste\s+(-?\d+(?:\.\d+)?)\s*" + _TEMP_UNIT_PATTERN,
    flags=re.IGNORECASE,
)
_SUB_INTERVAL_RE = re.compile(
    r"\bsub\s+(-?\d+(?:\.\d+)?)\s*" + _TEMP_UNIT_PATTERN,
    flags=re.IGNORECASE,
)


def _extract_fluent_intervals(text: str) -> List[Tuple[int, int, float, float]]:
    """
    Return [(start, end, a_raw, b_raw), ...] for fluent Romanian
    temperature expressions: 'intre A si B' (range), 'peste A' (open
    above), 'sub A' (open below). 'peste'/'sub' yield a 2 degC bin
    anchored at A: peste -> (A, A+2), sub -> (A-2, A). The caller
    still passes the result through _snap_to_2c_bin so the final
    interval is always on the standard grid.
    """
    out: List[Tuple[int, int, float, float]] = []
    for m in _INTRE_INTERVAL_RE.finditer(text):
        out.append((m.start(), m.end(),
                    float(m.group(1)), float(m.group(2))))
    for m in _PESTE_INTERVAL_RE.finditer(text):
        a = float(m.group(1))
        out.append((m.start(), m.end(), a, a + 2.0))
    for m in _SUB_INTERVAL_RE.finditer(text):
        b = float(m.group(1))
        out.append((m.start(), m.end(), b - 2.0, b))
    return out


_BIN_WIDTH_C: float = 2.0


def _snap_to_2c_bin(
    x_raw: float, y_raw: float, bin_width: float = _BIN_WIDTH_C,
) -> Tuple[int, int, bool]:
    """
    Project a possibly-non-compliant raw interval [x_raw, y_raw] onto
    the standard 2 degC ANM bin grid (..., -4, -2, 0, 2, 4, ...). The
    system prompt mandates integer-anchored bins, but models occasionally
    emit floats, off-grid integers, or off-width pairs - rather than
    drop the prediction we snap by midpoint:

        m         = (x_raw + y_raw) / 2
        bin_start = bin_width * floor(m / bin_width)
        bin_end   = bin_start + bin_width

    Returns (x_snapped, y_snapped, was_snapped) where was_snapped is
    True iff (x_raw, y_raw) didn't already sit on the grid (within a
    1e-9 tolerance for round-trip float artefacts). The runner uses
    that flag to count non-compliant rows.

    Examples:
        (0, 2)        -> (0, 2, False)              already on grid
        (10.5, 12.5)  -> (10, 12, True)             snapped down
        (1, 3)        -> (2, 4, True)               m=2 lands on the [2, 4] bin
        (10, 13)      -> (10, 12, True)             width corrected from 3 to 2
        (-4.1, -2.1)  -> (-6, -4, True)             snapped down across zero
    """
    m = (x_raw + y_raw) / 2.0
    bin_start = bin_width * math.floor(m / bin_width)
    bin_end = bin_start + bin_width
    was_snapped = (
        abs(bin_start - x_raw) > 1e-9 or abs(bin_end - y_raw) > 1e-9
    )
    return int(bin_start), int(bin_end), was_snapped


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

        intervals = []
        for m in _INTERVAL_RE.finditer(sent):
            x_raw, y_raw = float(m.group(1)), float(m.group(2))
            x_snap, y_snap, was_snapped = _snap_to_2c_bin(x_raw, y_raw)
            intervals.append((
                m.start(), m.end(),
                x_snap, y_snap,
                x_raw, y_raw, was_snapped,
            ))
        # Also pick up fluent Romanian forms ('intre A si B', 'peste A',
        # 'sub A') so GT paragraphs (which never use brackets) populate
        # zone+interval pairs too. Predictions normally use brackets,
        # but the same path tolerates fluent post-processed outputs.
        for start, end, a_raw, b_raw in _extract_fluent_intervals(sent):
            a_snap, b_snap, was_snapped = _snap_to_2c_bin(a_raw, b_raw)
            intervals.append((
                start, end,
                a_snap, b_snap,
                a_raw, b_raw, was_snapped,
            ))
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
            for i_start, i_end, x, y, x_raw, y_raw, was_snapped in intervals:
                # Distance from zone span to interval span (zero if they overlap).
                mid_iv = (i_start + i_end) / 2.0
                d = abs(zs - mid_iv)
                if best_d is None or d < best_d:
                    best_d = d
                    best = (x, y, x_raw, y_raw, was_snapped)
            x, y, x_raw, y_raw, was_snapped = best
            out.append({
                "raw_phrase": z["raw_phrase"],
                "axis": z["axis"],
                "key": z["key"],
                "ident": z.get("ident"),
                "cardinal": z["cardinal"],
                "stations": list(z["stations"]),
                "interval": [x, y],
                "interval_raw": [x_raw, y_raw],
                "snapped_to_2c_grid": was_snapped,
                "midpoint": (x + y) / 2.0,
                "sentence": sent.strip(),
            })
    return out


# ---------------------------------------------------------------------------
# Per-zone aggregators
# ---------------------------------------------------------------------------
#
# A "zone record" (the structure returned by extract_zones_from_text /
# dedupe_zones) carries a list of station IDs. The aggregators below
# convert that station list into observed monthly or daily values for
# the four available variables. The two regimes differ:
#
#  - Monthly: read temperature_YYYY-MM.json's per_station_mean_celsius
#    block. For each station in the zone, pull its monthly mean; average
#    over stations to get the zone-month value.
#
#  - Daily: read daily_county_*.csv (mean, precip, wind, nebulosity).
#    Each station resolves to a county (via metadata); take the mean of
#    the relevant columns across the counties that contain at least one
#    station of the zone, equally weighted. This avoids needing the raw
#    per-station daily series.


def _zone_to_counties(zone: Dict, metadata: dict) -> List[str]:
    """List of county codes that contain at least one of `zone['stations']`."""
    st2cls = metadata["station_to_classifications"]
    seen: List[str] = []
    for s in zone["stations"]:
        rec = st2cls.get(s)
        if not rec:
            continue
        county = rec.get("county")
        if county and county not in seen:
            seen.append(county)
    return seen


def zone_monthly_value(
    zone: Dict,
    month_int: int,
    year: int = 2024,
    variable: str = "mean_temp",
    date_folder: str = "date",
) -> Optional[float]:
    """
    Mean monthly value for the zone, computed by averaging the
    per-station monthly means of the zone's stations.

    `variable` is one of:
        - 'mean_temp' -> mean_temp from per_station_mean_celsius
        - 'mean_tmax' / 'mean_tmin'

    Returns None when none of the zone's stations have usable data
    that month.
    """
    valid_keys = {"mean_temp", "mean_tmax", "mean_tmin"}
    if variable not in valid_keys:
        raise ValueError(f"variable must be one of {valid_keys}, got {variable!r}")

    path = Path(date_folder) / f"temperature_{year}-{month_int:02d}.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} not found. Generate it via the `temperature` subcommand."
        )
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    per_station = data.get("per_station_mean_celsius", {})

    vals = []
    for s in zone["stations"]:
        rec = per_station.get(s)
        if rec is None:
            continue
        v = rec.get(variable)
        if v is None:
            continue
        vals.append(float(v))
    if not vals:
        return None
    return float(np.mean(vals))


def zone_daily_value(
    zone: Dict,
    date: pd.Timestamp,
    matrix: pd.DataFrame,
) -> Optional[float]:
    """
    Mean of `matrix.loc[date, county]` over the counties containing
    this zone's stations. `matrix` is one of daily_county_mean,
    daily_county_precip, daily_county_wind, daily_county_nebulosity
    pre-loaded as a DataFrame indexed by date with county columns.
    """
    counties = _zone_to_counties(zone, _zone_metadata_cache())
    if not counties:
        return None
    available = [c for c in counties if c in matrix.columns]
    if not available:
        return None
    try:
        return float(matrix.loc[date, available].mean())
    except KeyError:
        return None


# Module-level metadata cache so zone_daily_value doesn't reload on
# every call. The cache is keyed by absolute path; set explicitly via
# set_metadata_for_aggregators() in production code.
_METADATA_CACHE: Dict[str, dict] = {}


def set_metadata_for_aggregators(metadata: dict) -> None:
    """Stash the metadata dict so zone_daily_value can look up station -> county
    without the caller passing it on every invocation."""
    _METADATA_CACHE["current"] = metadata


def _zone_metadata_cache() -> dict:
    if "current" not in _METADATA_CACHE:
        raise RuntimeError(
            "metadata not set; call set_metadata_for_aggregators(metadata) "
            "before using zone_daily_value"
        )
    return _METADATA_CACHE["current"]


def load_county_daily_matrix(
    csv_filename: str,
    date_folder: str = "date",
) -> pd.DataFrame:
    """Load a daily_county_*.csv into a date-indexed DataFrame."""
    path = Path(date_folder) / csv_filename
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} not found. Generate it via the county_* subcommands "
            f"of check_data_availability."
        )
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    return df


# Pretty Romanian phrasing for the zone records, used when echoing
# zones back to the model in the user prompt. The model's OUTPUT is
# expected to use natural Romanian wording too, but for input we want
# unambiguous labels that the model can map back to its own vocabulary.
def zone_label_romanian(zone: Dict) -> str:
    """
    Return a Romanian-language label for the zone record, suitable for
    use in the user prompt's per-zone section headers.
    """
    axis = zone["axis"]
    ident = zone["ident"]
    card = zone.get("cardinal")
    if axis == "climatic":
        return ident
    if axis == "region":
        if card is None:
            return ident
        card_word = {"N": "nord", "S": "sud", "E": "est", "V": "vest"}[card]
        return f"{ident} ({card_word})"
    if axis == "region_compound":
        return ident
    if axis == "region_part":
        return ident
    if axis == "subregion":
        return ident
    return ident


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_RO = """Esti un meteorolog specializat in caracterizarea climatica a Romaniei.
Trebuie sa generezi un paragraf in limba romana care descrie EXCLUSIV
temperatura medie a aerului pentru o luna data, urmand convențiile ANM
(Administratia Nationala de Meteorologie).

CONSTRANGERE FUNDAMENTALA - VARIABILA DE IESIRE:

Singura variabila pe care o prezici este TEMPERATURA MEDIE A AERULUI in
grade Celsius (°C). Chiar daca prompt-ul utilizatorului iti ofera ca
INPUT date auxiliare (precipitatii in mm, viteza vantului in m/s,
nebulozitate pe scara WMO 0-8), ACELE date sunt DOAR informatii de
context care te ajuta sa estimezi temperatura. Tu NU trebuie sa
generezi, sa mentionezi sau sa includi:

  - intervale de precipitatii (mm, l/m²)
  - intervale de viteza a vantului (m/s, km/h, Beaufort)
  - intervale de nebulozitate (octa, procente de acoperire)
  - intervale ale oricarei alte variabile in afara de temperatura

Toate valorile [x, y] din output-ul tau sunt IMPLICIT in grade Celsius
si reprezinta EXCLUSIV temperatura medie lunara a aerului. Nu mentiona
unitatea de masura in interiorul parantezelor; unitatea °C poate sa
apara optional dupa paranteze (de exemplu "[10, 12] °C"), dar NICIODATA
alte unitati.

REGULI DE FORMAT (foarte importante - un algoritm automat va extrage
valorile din paragraful tau):

1. Paragraful trebuie sa acopere intreaga tara Romania, mentionand fie
   regiuni intregi (Muntenia, Dobrogea, Moldova, Oltenia, Banat,
   Crisana, Transilvania, Maramures), fie subdiviziuni dupa puncte
   cardinale ale unei regiuni (de exemplu: "sud-estul Munteniei",
   "nord-vestul Banatului"), fie zone climatice (litoral, Delta
   Dunarii, zona montana, zona montana inalta, depresiuni intramontane,
   zona de deal si podis, campie).

2. Pentru fiecare zona mentionata, OBLIGATORIU trebuie sa indici
   intervalul de TEMPERATURA intre paranteze drepte in formatul EXACT:

       [x, y]

   unde:
     - x si y sunt NUMERE INTREGI (nu folosi zecimale - NU emite
       valori ca [1.5, 3.5] sau [10.0, 12.0]; foloseste DOAR [1, 3]
       sau [10, 12]),
     - x trebuie sa fie un numar par (..., -4, -2, 0, 2, 4, 6, 8, 10,
       12, 14, 16, 18, 20, 22, 24, ...) - intervalele sunt ancorate
       pe grila standard ANM de 2 °C,
     - diferenta y - x trebuie sa fie EXACT 2 (binul standard ANM
       de 2 °C, deci y = x + 2).

3. Fiecare propozitie trebuie sa contina cel putin o referire la o
   zona si cel putin un interval [x, y] de TEMPERATURA. Daca o
   propozitie mentioneaza mai multe zone, intervalul se aplica
   tuturor zonelor mentionate in acea propozitie.

4. Acopera intreaga tara. Toate marile regiuni (Muntenia, Moldova,
   Oltenia, Transilvania, Banat-Crisana, Maramures, Dobrogea) trebuie
   sa fie acoperite fie direct, fie prin subdiviziuni cardinale sau
   zone climatice.

5. Genereaza UN SINGUR paragraf coerent, fara titluri sau sub-secțiuni.
   Limbajul trebuie sa fie similar cu cel folosit in caracterizările
   lunare ANM oficiale. NU descrie precipitatii, vant sau nori chiar
   daca primesti aceste date in input; ele exista doar pentru a-ti da
   context.

6. NU adauga comentarii, explicații sau metadate dupa paragraf.
   Output-ul trebuie sa fie EXCLUSIV paragraful despre temperatura,
   nimic altceva.

Exemple corecte de fragmente (toate intervalele sunt in °C):

  "Mediile lunare de temperatura au fost cuprinse intre [0, 2] °C in
   Muntenia, in cea mai mare parte a Dobrogei si Olteniei."

  "Pe litoral si in Delta Dunarii valorile au depasit [2, 4] °C, in
   timp ce in sud-estul Munteniei mediile au variat intre [-2, 0] °C."

  "In zona montana inalta temperatura medie lunara a fost cuprinsa
   intre [-8, -6] °C, iar pe creste, la peste 2500 m altitudine,
   valorile au scazut sub [-10, -8] °C."
"""


def build_system_prompt() -> str:
    """Return the Romanian system prompt with the strict [x, y] format requirement."""
    return SYSTEM_PROMPT_RO


# ---------------------------------------------------------------------------
# User prompt builders
# ---------------------------------------------------------------------------
#
# Five input modes x two scenarios. Each builder receives:
#   - the extracted+deduplicated zones for the run
#   - the test target identifier (target month for both scenarios)
#   - the relevant data sources (historic paragraphs, monthly stats,
#     daily matrices)
# and returns the user prompt string.


MODES = (
    "historic_only",
    "historic_plus_temp",
    "historic_plus_aux",
    "temp_only",
    "aux_only",
    "historic_only_with_prior",
    "historic_plus_temp_with_prior",
    "historic_plus_aux_with_prior",
)

# Modes whose user prompt embeds prior-year target-month ANM
# paragraphs in addition to the same-year prior-month context. When
# --n_prior_years is 0 these modes are silently filtered from any
# selected run (no prior-year data available -> they would be
# byte-identical to their non-prior counterparts and pollute the
# comparison plot).
PRIOR_YEAR_MODES = (
    "historic_only_with_prior",
    "historic_plus_temp_with_prior",
    "historic_plus_aux_with_prior",
)

# Base historic mode name a prior-year mode is built on. Used by
# the prompt builders to decide which information blocks to include
# (text only, text + temp, text + aux).
_PRIOR_YEAR_BASE_MODE: Dict[str, str] = {
    "historic_only_with_prior":      "historic_only",
    "historic_plus_temp_with_prior": "historic_plus_temp",
    "historic_plus_aux_with_prior":  "historic_plus_aux",
}

SCENARIOS = ("monthly", "daily")


def _format_zone_monthly_block(
    zone: Dict,
    months: List[int],
    year: int,
    include_temp: bool,
    include_aux: bool,
    date_folder: str = "date",
    aux_matrices: Optional[Dict[str, pd.DataFrame]] = None,
) -> str:
    """One zone's monthly evolution block. Used by the monthly scenario."""
    lines = [f"  [{zone_label_romanian(zone)}]"]
    if include_temp or include_aux:
        for m in months:
            month_label = romanian_month_name(m)
            temp = zone_monthly_value(
                zone, month_int=m, year=year, variable="mean_temp",
                date_folder=date_folder,
            )
            parts = []
            if include_temp and temp is not None:
                parts.append(f"temperatura medie = {temp:.2f} °C")
            if include_aux and aux_matrices is not None:
                # For aux in the MONTHLY scenario we take the monthly
                # mean of each daily aux matrix over the month's days.
                month_dates = pd.date_range(
                    f"{year}-{m:02d}-01", periods=31, freq="D",
                ).intersection(aux_matrices["precip"].index)
                month_dates = [
                    d for d in month_dates if d.month == m and d.year == year
                ]
                if month_dates:
                    precip = float(
                        aux_matrices["precip"]
                        .loc[month_dates, _zone_to_counties(zone, _zone_metadata_cache())]
                        .filter(items=aux_matrices["precip"].columns)
                        .mean()
                        .mean()
                    ) if zone["stations"] else None
                    wind = float(
                        aux_matrices["wind"]
                        .loc[month_dates, _zone_to_counties(zone, _zone_metadata_cache())]
                        .filter(items=aux_matrices["wind"].columns)
                        .mean()
                        .mean()
                    ) if zone["stations"] else None
                    neb = float(
                        aux_matrices["nebulosity"]
                        .loc[month_dates, _zone_to_counties(zone, _zone_metadata_cache())]
                        .filter(items=aux_matrices["nebulosity"].columns)
                        .mean()
                        .mean()
                    ) if zone["stations"] else None
                    if precip is not None and not np.isnan(precip):
                        parts.append(f"precipitatii = {precip:.2f} mm/zi")
                    if wind is not None and not np.isnan(wind):
                        parts.append(f"vant = {wind:.2f} m/s")
                    if neb is not None and not np.isnan(neb):
                        parts.append(f"nebulozitate = {neb:.2f} octanti")
            if parts:
                lines.append(f"    {month_label}: " + ", ".join(parts))
    return "\n".join(lines)


def _format_zone_daily_block(
    zone: Dict,
    target_month: int,
    target_year: int,
    n_known_days: int,
    include_temp: bool,
    include_aux: bool,
    aux_matrices: Dict[str, pd.DataFrame],
) -> str:
    """One zone's daily evolution block. Used by the daily scenario."""
    lines = [f"  [{zone_label_romanian(zone)}]"]
    counties = [
        c for c in _zone_to_counties(zone, _zone_metadata_cache())
        if c in aux_matrices["temp"].columns
    ]
    if not counties:
        lines.append("    (no stations resolvable to county-day matrices)")
        return "\n".join(lines)
    month_start = pd.Timestamp(year=target_year, month=target_month, day=1)
    dates = pd.date_range(month_start, periods=n_known_days, freq="D")
    dates = [d for d in dates if d in aux_matrices["temp"].index]
    for d in dates:
        parts = []
        if include_temp:
            temp = float(aux_matrices["temp"].loc[d, counties].mean())
            parts.append(f"temp = {temp:.2f} °C")
        if include_aux:
            precip = float(aux_matrices["precip"].loc[d, counties].mean()) \
                if "precip" in aux_matrices else None
            wind = float(aux_matrices["wind"].loc[d, counties].mean()) \
                if "wind" in aux_matrices else None
            neb = float(aux_matrices["nebulosity"].loc[d, counties].mean()) \
                if "nebulosity" in aux_matrices else None
            if precip is not None:
                parts.append(f"precipitatii = {precip:.2f} mm")
            if wind is not None:
                parts.append(f"vant = {wind:.2f} m/s")
            if neb is not None:
                parts.append(f"nebulozitate = {neb:.2f}")
        lines.append(f"    {d.strftime('%Y-%m-%d')}: " + ", ".join(parts))
    return "\n".join(lines)


def build_user_prompt_monthly(
    *,
    fold_n: int,
    target_month: int,
    year: int,
    mode: str,
    historic_paragraphs: Dict[str, str],
    zones: List[Dict],
    aux_matrices: Optional[Dict[str, pd.DataFrame]] = None,
    date_folder: str = "date",
    prior_year_paragraphs: Optional[Dict[int, str]] = None,
) -> str:
    """
    Build the monthly-scenario user prompt.

    Args:
        fold_n: 3, 6, or 9 - the number of known months prior to the target.
        target_month: 1-indexed month to predict.
        year: 2024.
        mode: one of MODES.
        historic_paragraphs: {romanian_month_name: paragraph} for known months.
        zones: deduplicated zone records extracted from those paragraphs.
        aux_matrices: required for modes that include aux; dict of pd.DataFrame
            keyed by 'temp', 'precip', 'wind', 'nebulosity'.
        prior_year_paragraphs: optional {year -> paragraph} for the target
            month from prior years. Consumed only by the `*_with_prior`
            modes; passed through as None for the other modes.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")

    known_months = list(range(target_month - fold_n, target_month))
    if any(m < 1 for m in known_months):
        raise ValueError(
            f"target_month={target_month} with fold_n={fold_n} requires "
            f"months in 1..12; need at least {fold_n} months before it"
        )

    target_label = romanian_month_name(target_month)
    known_labels = [romanian_month_name(m) for m in known_months]
    base_mode = _PRIOR_YEAR_BASE_MODE.get(mode, mode)
    show_historic = base_mode in (
        "historic_only", "historic_plus_temp", "historic_plus_aux"
    )
    show_data = base_mode in (
        "historic_plus_temp", "historic_plus_aux", "temp_only", "aux_only"
    )

    parts = [
        f"Cunoastem caracterizarile climatice si/sau datele observate pentru "
        f"lunile {', '.join(known_labels)} {year}.",
    ]
    if mode in PRIOR_YEAR_MODES and prior_year_paragraphs:
        prior_years_sorted = sorted(prior_year_paragraphs.keys(), reverse=True)
        parts.append(
            f"In plus, ai si caracterizarile lunii {target_label} din "
            f"ultimii {len(prior_years_sorted)} ani "
            f"({', '.join(str(y) for y in prior_years_sorted)}) ca "
            f"referinta climatologica - NU adevarul pentru {year}, ci "
            f"contextul climatologic istoric pentru aceeasi luna."
        )
    parts += [
        f"Genereaza paragraful de caracterizare climatica pentru luna "
        f"{target_label} {year} folosind aceleasi conventii ca in exemple.",
        "",
        "Zonele acoperite in paragraf trebuie sa includa cel putin urmatoarele "
        "(extrase din caracterizarile lunilor cunoscute, dupa deduplicare):",
    ]
    for z in zones:
        parts.append(f"  - {zone_label_romanian(z)}")
    parts.append("")

    if (
        mode in PRIOR_YEAR_MODES
        and prior_year_paragraphs
        and show_historic
    ):
        parts.append(
            f"CARACTERIZARI ISTORICE PENTRU LUNA {target_label.upper()} "
            f"DIN ANII ANTERIORI (referinta climatologica, NU adevarul "
            f"pentru {year}):"
        )
        for prior_year in sorted(prior_year_paragraphs.keys(), reverse=True):
            para = prior_year_paragraphs[prior_year]
            if para:
                parts.append(f"  {target_label} {prior_year}: {para}")
        parts.append("")

    if show_historic:
        parts.append("CARACTERIZARI ISTORICE (din arhiva ANM):")
        for m, label in zip(known_months, known_labels):
            para = historic_paragraphs.get(label, "")
            if para:
                parts.append(f"  {label}: {para}")
        parts.append("")

    if show_data:
        include_temp = base_mode in (
            "historic_plus_temp", "historic_plus_aux", "temp_only"
        )
        include_aux = base_mode in ("historic_plus_aux", "aux_only")
        if include_temp and include_aux:
            header = "DATE OBSERVATE (temperatura medie + auxiliare per zona, lunar):"
        elif include_temp:
            header = "DATE OBSERVATE (temperatura medie per zona, lunar):"
        else:
            header = "DATE OBSERVATE (variabile auxiliare per zona, lunar):"
        parts.append(header)
        for z in zones:
            parts.append(
                _format_zone_monthly_block(
                    z, known_months, year,
                    include_temp=include_temp,
                    include_aux=include_aux,
                    date_folder=date_folder,
                    aux_matrices=aux_matrices,
                )
            )
        parts.append("")

    parts.append(
        f"Genereaza acum paragraful pentru {target_label} {year}, "
        f"respectand regulile de format si folosind intervalele [x, y]."
    )
    return "\n".join(parts)


def build_user_prompt_daily(
    *,
    n_known_days: int,
    target_month: int,
    year: int,
    mode: str,
    historic_paragraphs: Dict[str, str],
    zones: List[Dict],
    aux_matrices: Optional[Dict[str, pd.DataFrame]] = None,
    prior_year_paragraphs: Optional[Dict[int, str]] = None,
) -> str:
    """
    Build the daily-scenario user prompt.

    The model knows the first `n_known_days` of the target month (per
    zone, daily observed values) and the historic paragraphs of all
    months PRIOR to the target month. It must produce the FULL-month
    caracterizare.

    `prior_year_paragraphs` ({year -> paragraph}) is consumed only by
    the `*_with_prior` modes; non-prior modes ignore it.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")

    target_label = romanian_month_name(target_month)
    # Previous months for the historic-paragraph context.
    previous_months = list(range(1, target_month))
    previous_labels = [romanian_month_name(m) for m in previous_months]
    base_mode = _PRIOR_YEAR_BASE_MODE.get(mode, mode)
    show_historic = base_mode in (
        "historic_only", "historic_plus_temp", "historic_plus_aux"
    )
    show_data = base_mode in (
        "historic_plus_temp", "historic_plus_aux", "temp_only", "aux_only"
    )

    parts = [
        f"Cunoastem caracterizarile climatice ale lunilor anterioare "
        f"{', '.join(previous_labels) if previous_labels else '(niciuna disponibila)'} {year}, "
        f"si datele observate zilnic pentru primele {n_known_days} zile ale lunii "
        f"{target_label} {year}.",
    ]
    if mode in PRIOR_YEAR_MODES and prior_year_paragraphs:
        prior_years_sorted = sorted(prior_year_paragraphs.keys(), reverse=True)
        parts.append(
            f"In plus, ai si caracterizarile lunii {target_label} din "
            f"ultimii {len(prior_years_sorted)} ani "
            f"({', '.join(str(y) for y in prior_years_sorted)}) ca "
            f"referinta climatologica - NU adevarul pentru {year}, ci "
            f"contextul climatologic istoric pentru aceeasi luna."
        )
    parts += [
        "",
        f"Genereaza paragraful de caracterizare climatica pentru INTREAGA luna "
        f"{target_label} {year}, tinand cont ca doar primele {n_known_days} zile "
        f"sunt cunoscute - restul lunii trebuie sa fie prognozat ca o "
        f"extensie autoregresiva a tendintei observate.",
        "",
        "Zonele acoperite in paragraf trebuie sa includa cel putin urmatoarele "
        "(extrase din caracterizarile lunilor anterioare, dupa deduplicare):",
    ]
    for z in zones:
        parts.append(f"  - {zone_label_romanian(z)}")
    parts.append("")

    if (
        mode in PRIOR_YEAR_MODES
        and prior_year_paragraphs
        and show_historic
    ):
        parts.append(
            f"CARACTERIZARI ISTORICE PENTRU LUNA {target_label.upper()} "
            f"DIN ANII ANTERIORI (referinta climatologica, NU adevarul "
            f"pentru {year}):"
        )
        for prior_year in sorted(prior_year_paragraphs.keys(), reverse=True):
            para = prior_year_paragraphs[prior_year]
            if para:
                parts.append(f"  {target_label} {prior_year}: {para}")
        parts.append("")

    if show_historic:
        if previous_labels:
            parts.append("CARACTERIZARI ISTORICE (lunile anterioare lunii prognozate):")
            for m, label in zip(previous_months, previous_labels):
                para = historic_paragraphs.get(label, "")
                if para:
                    parts.append(f"  {label}: {para}")
            parts.append("")

    if show_data:
        include_temp = base_mode in (
            "historic_plus_temp", "historic_plus_aux", "temp_only"
        )
        include_aux = base_mode in ("historic_plus_aux", "aux_only")
        if include_temp and include_aux:
            header = (
                f"DATE OBSERVATE ZILNIC (temperatura + auxiliare per zona, "
                f"primele {n_known_days} zile din {target_label} {year}):"
            )
        elif include_temp:
            header = (
                f"DATE OBSERVATE ZILNIC (temperatura medie per zona, "
                f"primele {n_known_days} zile din {target_label} {year}):"
            )
        else:
            header = (
                f"DATE OBSERVATE ZILNIC (variabile auxiliare per zona, "
                f"primele {n_known_days} zile din {target_label} {year}):"
            )
        parts.append(header)
        if aux_matrices is None:
            raise ValueError(
                "aux_matrices is required for daily-scenario modes that include "
                "temp or aux"
            )
        for z in zones:
            parts.append(
                _format_zone_daily_block(
                    z, target_month, year, n_known_days,
                    include_temp=include_temp,
                    include_aux=include_aux,
                    aux_matrices=aux_matrices,
                )
            )
        parts.append("")

    parts.append(
        f"Genereaza acum paragraful pentru intreaga luna {target_label} {year}, "
        f"respectand regulile de format si folosind intervalele [x, y]."
    )
    return "\n".join(parts)


def load_prior_year_target_month_paragraphs(
    *,
    target_year: int,
    target_month: int,
    n_prior_years: int,
    date_folder: str | Path = "date",
    filename_pattern: str = "historic_data_{year}.json",
) -> Dict[int, str]:
    """
    Load the target-month ANM paragraph from each of the `n_prior_years`
    years preceding `target_year`. Counting down: target_year=2024 with
    n_prior_years=2 returns paragraphs from 2023 and 2022 (the two most
    recent prior years).

    Missing files are silently skipped (e.g. n_prior_years=3 on 2024 with
    only 2021/2022/2023 archives gives all three; raising n_prior_years
    further would just return what is available).

    Returns: { year: paragraph_text } - empty dict if nothing was found.
    """
    if n_prior_years <= 0:
        return {}
    target_label = romanian_month_name(target_month)
    out: Dict[int, str] = {}
    for k in range(1, n_prior_years + 1):
        y = target_year - k
        path = Path(date_folder) / filename_pattern.format(year=y)
        if not path.is_file():
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                blob = json.load(f)
        except Exception as e:
            print(f"  warn: failed to read {path.name}: {e}; skipping {y}")
            continue
        para = (blob.get("caracterizare_lunara") or {}).get(target_label, "")
        if para:
            out[y] = para
    return out


# Driver helper: given a scenario + fold + mode, extract the zones from
# the right historic paragraphs and build the prompt. This is the
# function the runner will call per (model, mode, scenario, fold).
def build_prompt_pair(
    *,
    scenario: str,
    fold_n: int,
    mode: str,
    target_month: int,
    year: int,
    historic_data_path: str | Path,
    metadata: dict,
    aux_matrices: Optional[Dict[str, pd.DataFrame]] = None,
    date_folder: str = "date",
    prior_year_paragraphs: Optional[Dict[int, str]] = None,
) -> Tuple[str, str, List[Dict], str]:
    """
    Returns (system_prompt, user_prompt, deduped_zones, gt_paragraph).

    `gt_paragraph` is the historic_data paragraph for the target month
    (kept alongside so the scoring code has a single object to consume).

    `prior_year_paragraphs` (year -> paragraph) is only consumed by the
    three `*_with_prior` modes; non-prior modes ignore it so the same
    runner can interleave both families without separate dispatch.
    """
    if scenario not in SCENARIOS:
        raise ValueError(f"scenario must be one of {SCENARIOS}, got {scenario!r}")

    with open(historic_data_path, "r", encoding="utf-8") as f:
        historic = json.load(f)
    paragraphs: Dict[str, str] = historic["caracterizare_lunara"]
    gt_paragraph = paragraphs.get(romanian_month_name(target_month), "")

    set_metadata_for_aggregators(metadata)

    if scenario == "monthly":
        known_months = list(range(target_month - fold_n, target_month))
    else:
        # Daily: zones extracted from ALL previous months (to maximise
        # vocabulary). Per the user's spec the dedup happens via
        # dedupe_zones.
        known_months = list(range(1, target_month))

    if any(m < 1 for m in known_months):
        raise ValueError(
            f"target_month={target_month}, fold_n={fold_n}: not enough "
            f"prior months in the same year for this combination"
        )

    # Extract + dedupe zones from the known months' GT paragraphs.
    all_zones: List[Dict] = []
    for m in known_months:
        para = paragraphs.get(romanian_month_name(m), "")
        if para:
            all_zones.extend(extract_zones_from_text(para, metadata))
    # The `*_with_prior` modes also see prior-year target-month
    # paragraphs in the user prompt - widen the zone vocabulary so
    # the LLM's required-coverage list reflects what it can read.
    if mode in PRIOR_YEAR_MODES and prior_year_paragraphs:
        for para in prior_year_paragraphs.values():
            if para:
                all_zones.extend(extract_zones_from_text(para, metadata))
    zones = dedupe_zones(all_zones)

    system_prompt = build_system_prompt()
    if scenario == "monthly":
        user_prompt = build_user_prompt_monthly(
            fold_n=fold_n, target_month=target_month, year=year, mode=mode,
            historic_paragraphs=paragraphs, zones=zones,
            aux_matrices=aux_matrices, date_folder=date_folder,
            prior_year_paragraphs=prior_year_paragraphs,
        )
    else:
        user_prompt = build_user_prompt_daily(
            n_known_days=fold_n, target_month=target_month, year=year, mode=mode,
            historic_paragraphs=paragraphs, zones=zones,
            aux_matrices=aux_matrices,
            prior_year_paragraphs=prior_year_paragraphs,
        )

    return system_prompt, user_prompt, zones, gt_paragraph


# ---------------------------------------------------------------------------
# Post-processing [x, y] -> fluent Romanian
# ---------------------------------------------------------------------------

# The fluent-Romanian rewriter consumes (optionally) a Romanian
# quantifier word in front of the bracket ('sub', 'peste', 'pana la',
# 'de la', 'intre' / 'într?e' / 'între'), the bracket itself, and
# any trailing unit. Without quantifier handling, "valori sub
# [0, 2] °C" would become the broken "valori sub intre 0 si 2 °C".
# Diacritic variants (pana / pâna / pană / până, intre / între /
# într?e) are all accepted; unit forms covered are '°C', 'oC', 'C',
# 'degC'.
#
# Collapse rules are PARAGRAPH-AWARE:
#   'sub' / 'de la'       collapse to single value only when the
#                         bracket is the LOWEST in the paragraph
#   'peste' / 'pana la'   collapse only when the bracket is the
#                         HIGHEST in the paragraph
# Any other quantifier+bracket combination drops the quantifier
# word and falls back to 'intre x si y'. This matches the model's
# intent (the value sits inside the bin) without leaving broken
# Romanian when a directional word lands on a middle bin.

_QUANTIFIER_PATTERN = (
    r"(?:p[aâ]n[aă]\s+la|p[aâ]n[aă]|sub|peste|de\s+la|intre|într?e)"
)

_FLUENT_REWRITE_RE = re.compile(
    rf"(?:\b({_QUANTIFIER_PATTERN})\s+)?"                # optional quantifier
    r"\[\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\]"
    r"(?:\s*(?:\xb0\s*[Cc]|deg\s*[Cc]|[Cc]))?",          # optional unit
    flags=re.IGNORECASE,
)


def _normalize_quantifier(raw: str) -> str:
    """Lower-case + diacritic-strip + collapse whitespace so every
    Romanian variant maps to a small set of canonical keys."""
    if not raw:
        return ""
    return re.sub(r"\s+", " ", _strip_diacritics(raw.lower())).strip()


def postprocess_brackets_to_fluent_romanian(text: str) -> str:
    """
    Rewrite every '[x, y]' (optionally preceded by a Romanian
    quantifier - 'sub', 'peste', 'pana la', 'de la', 'intre' - and
    optionally followed by '°C' / 'degC' / 'C') into grammatical
    fluent Romanian.

    Quantifier-aware AND paragraph-aware: 'sub' / 'de la' collapse
    to a single value only when the bracket is the LOWEST in the
    paragraph; 'peste' / 'pana la' collapse only when the bracket
    is the HIGHEST. Any other quantifier+bracket combination drops
    the quantifier word and falls back to 'intre x si y'.

    The bracket values are also snapped to the standard 2 degC ANM
    grid via _snap_to_2c_bin so the fluent text matches what
    manual_score consumed.

    This function can be re-run over already-finished llm_runs JSON
    files via the `postprocess` CLI subcommand without rerunning
    any LLM inference - useful for iterating on the rewriter without
    burning compute.
    """
    # First pass: collect all snapped (x, y) pairs in the paragraph
    # to determine min(x) and max(y). Quantifier collapse depends on
    # whether the current bracket sits at one of those extremes.
    pairs: List[Tuple[int, int]] = []
    for m in _FLUENT_REWRITE_RE.finditer(text):
        x, y, _ = _snap_to_2c_bin(float(m.group(2)), float(m.group(3)))
        pairs.append((x, y))
    if not pairs:
        return text
    min_x = min(p[0] for p in pairs)
    max_y = max(p[1] for p in pairs)

    def _format(match: "re.Match") -> str:
        q = _normalize_quantifier(match.group(1) or "")
        x_raw, y_raw = float(match.group(2)), float(match.group(3))
        x, y, _ = _snap_to_2c_bin(x_raw, y_raw)

        if q == "sub" and x == min_x:
            return f"sub {x} °C"
        if q == "de la" and x == min_x:
            return f"de la {x} °C"
        if q == "peste" and y == max_y:
            return f"peste {y} °C"
        if q in ("pana", "pana la") and y == max_y:
            return f"pana la {y} °C"

        return f"intre {x} si {y} °C"

    return _FLUENT_REWRITE_RE.sub(_format, text)


def refresh_fluent_paragraphs(
    llm_runs_dir: str | Path = "llm_runs",
    backup: bool = False,
) -> Dict[str, int]:
    """
    Re-apply `postprocess_brackets_to_fluent_romanian` over every
    record in every llm_runs_*.json under `llm_runs_dir`, updating
    `predicted_paragraph_fluent` in place. Records without a
    `predicted_paragraph_raw` (e.g. rows that errored out during
    the LLM call) are skipped without touching them.

    Args:
        llm_runs_dir: directory containing llm_runs_<model>.json
        backup: if True, write each file's previous contents to
            <name>.json.bak before overwriting.

    Returns: { json_filename: n_rows_with_changed_fluent_string }
    """
    out_dir = Path(llm_runs_dir)
    if not out_dir.is_dir():
        raise FileNotFoundError(f"llm_runs directory not found: {out_dir}")

    summary: Dict[str, int] = {}
    for path in sorted(out_dir.glob("llm_runs_*.json")):
        with open(path, "r", encoding="utf-8") as f:
            blob = json.load(f)
        results = blob.get("results", [])
        n_seen = 0
        n_changed = 0
        for r in results:
            raw = r.get("predicted_paragraph_raw")
            if not raw:
                continue
            new_fluent = postprocess_brackets_to_fluent_romanian(raw)
            if new_fluent != r.get("predicted_paragraph_fluent"):
                n_changed += 1
            r["predicted_paragraph_fluent"] = new_fluent
            n_seen += 1
        if backup:
            path.with_suffix(".json.bak").write_text(
                json.dumps(blob, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        with open(path, "w", encoding="utf-8") as f:
            json.dump(blob, f, ensure_ascii=False, indent=2)
        summary[path.name] = n_changed
        print(f"  {path.name}: refreshed {n_seen} rows "
              f"({n_changed} fluent strings changed)")
    return summary


# ---------------------------------------------------------------------------
# Manual scoring algorithm
# ---------------------------------------------------------------------------
#
# Per-station distance d(s):
#
#   d(s) = dist(T(s), [a, b])              if s in S_GT ∩ S_pred
#   d(s) = w                                if s in S_GT \\ S_pred  (missed)
#   d(s) = max(dist(T(s), [a, b]), w)       if s in S_pred \\ S_GT  (false +)
#
#   dist(T, [a, b]) = a - T   if T < a
#                   = T - b   if T > b
#                   = 0       if T ∈ [a, b]
#
# Aggregation:
#   d_bar = mean of d(s) over S_eval = (S_GT ∪ S_pred) restricted to
#           stations with usable T(s) data.
#
# Normalisation:
#   accuracy = 1 / (1 + d_bar / w)        in [0, 1]
#
# Maps d_bar=0 -> 100%, d_bar=w -> 50%, d_bar=2w -> 33%, etc.


def _point_to_interval_distance(T: float, a: float, b: float) -> float:
    """L1 distance from a scalar to a closed interval. 0 when T ∈ [a, b]."""
    if T < a:
        return a - T
    if T > b:
        return T - b
    return 0.0


def _build_station_intervals(
    predicted_records: List[Dict],
) -> Dict[str, List[float]]:
    """
    Collapse the per-zone predicted intervals into a per-station
    interval map. When a station belongs to multiple predicted zones
    (the LLM mentioned it under both 'Muntenia' and 'sud-estul
    Munteniei', say), we take the LAST mention's interval - matching
    the natural reading order in Romanian paragraphs where the more
    specific phrasing tends to come second.
    """
    station_to_interval: Dict[str, List[float]] = {}
    for rec in predicted_records:
        a, b = rec["interval"]
        for s in rec["stations"]:
            station_to_interval[s] = [float(a), float(b)]
    return station_to_interval


def _build_gt_station_set(gt_paragraph: str, metadata: dict) -> List[str]:
    """All stations that fall under any zone mentioned in the GT paragraph."""
    zones = extract_zones_from_text(gt_paragraph, metadata)
    seen: List[str] = []
    for z in zones:
        for s in z["stations"]:
            if s not in seen:
                seen.append(s)
    return seen


def _load_station_temperatures_for_month(
    target_month: int, year: int, date_folder: str = "date",
) -> Dict[str, float]:
    """{station: monthly_mean_temp} from temperature_YYYY-MM.json. Stations
    with no usable data that month are omitted (-> excluded from S_eval)."""
    path = Path(date_folder) / f"temperature_{year}-{target_month:02d}.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"{path} not found. Generate via the `temperature` subcommand."
        )
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    per_station = data.get("per_station_mean_celsius", {})
    return {s: float(rec["mean_temp"]) for s, rec in per_station.items()
            if rec.get("mean_temp") is not None}


def manual_score(
    *,
    predicted_paragraph: str,
    gt_paragraph: str,
    target_month: int,
    year: int,
    metadata: dict,
    date_folder: str = "date",
    bin_width: float = 2.0,
) -> Dict:
    """
    Implement the hyperbolic per-station scoring algorithm from the
    user's spec. T(s) is the monthly mean of each station for the
    target month - both monthly and daily scenarios use this same
    target because in both cases the LLM is being asked for the
    full-month characterisation.

    Args:
        predicted_paragraph: LLM output following the [x, y] format.
        gt_paragraph:        ANM historic_data_yyyy.json paragraph.
        target_month, year:  used to look up the per-station monthly mean.
        metadata:            stations_metadata.json contents.
        bin_width:           w in the formula; 2 °C per spec.

    Returns:
        {
            'accuracy':        float in [0, 1],
            'error_pct':       float in [0, 1]  (= 1 - accuracy),
            'd_bar':           float (mean per-station distance, °C),
            'w':               bin_width,
            'counts': {
                'intersection': int,
                'missed':       int,
                'false_pos':    int,
                'unscorable':   int    # stations w/ no T(s) data
            },
            'per_station': [
                {station, T, interval, d, category}, ...
            ],
            'pred_zones': [...],
            'pred_records': [...],
        }
    """
    # Per-station target temperatures for the target month.
    T_per_station = _load_station_temperatures_for_month(
        target_month, year, date_folder=date_folder,
    )

    # GT side: any station under any zone mentioned in the GT paragraph.
    gt_stations = set(_build_gt_station_set(gt_paragraph, metadata))

    # Pred side: extract (zone, interval) records, then collapse to
    # station -> interval. If the model produced zero parseable
    # intervals, every GT station becomes missed and the score is the
    # flat-w penalty.
    pred_records = extract_predictions_from_paragraph(
        predicted_paragraph, metadata,
    )
    station_to_interval = _build_station_intervals(pred_records)
    pred_stations = set(station_to_interval.keys())

    # S_eval = stations with both a usable T(s) AND a non-empty role on
    # at least one side.
    all_stations = gt_stations | pred_stations

    per_station: List[Dict] = []
    n_intersection = n_missed = n_false_pos = n_unscorable = 0
    distances: List[float] = []
    for s in sorted(all_stations):
        T = T_per_station.get(s)
        if T is None:
            n_unscorable += 1
            per_station.append({
                "station": s,
                "T": None,
                "interval": station_to_interval.get(s),
                "d": None,
                "category": "unscorable",
            })
            continue
        in_gt = s in gt_stations
        in_pred = s in pred_stations
        if in_gt and in_pred:
            a, b = station_to_interval[s]
            d = _point_to_interval_distance(T, a, b)
            cat = "intersection"
            n_intersection += 1
        elif in_gt and not in_pred:
            d = bin_width
            cat = "missed"
            n_missed += 1
        else:  # in_pred and not in_gt
            a, b = station_to_interval[s]
            d = max(_point_to_interval_distance(T, a, b), bin_width)
            cat = "false_positive"
            n_false_pos += 1
        distances.append(d)
        per_station.append({
            "station": s,
            "T": T,
            "interval": station_to_interval.get(s),
            "d": d,
            "category": cat,
        })

    if not distances:
        # No scorable stations. Pretend d_bar = w (i.e. all missed).
        d_bar = bin_width
    else:
        d_bar = float(np.mean(distances))

    accuracy = 1.0 / (1.0 + d_bar / bin_width)
    error_pct = 1.0 - accuracy

    n_intervals_total = len(pred_records)
    n_snapped = sum(
        1 for r in pred_records if r.get("snapped_to_2c_grid", False)
    )
    return {
        "accuracy": accuracy,
        "error_pct": error_pct,
        "d_bar": d_bar,
        "w": bin_width,
        "counts": {
            "intersection": n_intersection,
            "missed": n_missed,
            "false_pos": n_false_pos,
            "unscorable": n_unscorable,
        },
        "format_compliance": {
            "n_intervals_total": n_intervals_total,
            "n_snapped_to_2c_grid": n_snapped,
            "compliance_ratio": (
                1.0 - n_snapped / n_intervals_total
                if n_intervals_total > 0 else None
            ),
        },
        "per_station": per_station,
        "pred_records": [
            {k: v for k, v in r.items() if k != "stations"}
            for r in pred_records
        ],
    }


# ---------------------------------------------------------------------------
# LLM-as-a-judge scorer
# ---------------------------------------------------------------------------

JUDGE_SYSTEM_PROMPT_COT_RO = """Esti un evaluator climatic specializat. Primesti
doua paragrafe in limba romana:

  1) REFERINTA - adevarul, asa cum apare in arhiva ANM.
  2) PREDICTIE - paragraful generat de un model.

Procedura ta:

PASUL 1 - Extragere REFERINTA. Identifica toate zonele mentionate
impreuna cu intervalele lor de temperatura si scrie-le ca o lista
de perechi [zona, [a, b]]. Zonele pot fi parti cardinale de regiuni
(ex: "sud-estul Munteniei"), regiuni intregi (ex: "Muntenia") sau
zone climatice (ex: "litoral", "Delta Dunarii", "zona montana
inalta").

PASUL 2 - Extragere PREDICTIE. Acelasi proces aplicat paragrafului
generat de model. Rezultatul este o a doua lista de perechi
[zona, [a, b]].

PASUL 3 - Motivatie. Scrie o singura propozitie scurta care explica
diferentele dintre lista REFERINTA si lista PREDICTIE (zone lipsa
sau in plus, distanta intre intervale). Prefixeaz-o cu
"Motivatie:" pentru a fi usor de extras.

PASUL 4 - Rezultat. Pe baza celor doua liste si a motivatiei, alege
un singur scor intreg de acuratete intre 0 si 100. Cu cat sunt mai
apropiate intervalele si cu cat coincid mai mult zonele, cu atat
scorul este mai mare. Pe ULTIMA linie, scrie scorul ca un singur
numar intreg intre paranteze drepte, exact in formatul:

  [N]

unde N este cuprins intre 0 si 100. Scrie doar [N] pe ultima linie
ca rezultat final. Exemplu: [73]
"""

JUDGE_USER_PROMPT_COT_TEMPLATE = """REFERINTA:
{gt}

PREDICTIE:
{pred}

Raspunde urmand procedura din 4 pasi din mesajul de sistem. Ultima
linie a raspunsului tau trebuie sa fie [N], unde N este scorul de
acuratete."""


# Old single-shot judge prompt restored as an explicit baseline.
# Used by --judge_style zero_shot. Both styles cohabit the same
# llm_runs_<model>.json schema; only `metadata.judge_style` and
# `judge_score.judge_raw_reply` differ between two runs of the same
# model with the same predictions.
JUDGE_SYSTEM_PROMPT_ZERO_SHOT_RO = """Esti un evaluator climatic specializat. Vei primi
doua paragrafe:

  1) Paragraful de referinta (adevarul, asa cum apare in arhiva ANM).
  2) Paragraful generat (predictia unui model).

Compara cele doua paragrafe si determina cat de exact este paragraful
generat fata de referinta. Considera:

  - Acoperirea geografica (aceleasi regiuni, zone climatice, subdiviziuni
    cardinale sunt mentionate).
  - Acuratețea intervalelor de temperatura (intervalele predictiei se
    suprapun cu ce ar fi spus referinta).
  - Consistența cu structura de caracterizare ANM.

Returneaza UN SINGUR numar intreg intre 0 si 100, reprezentand procentul
de acuratețe (100 = identice ca informație, 0 = complet gresit). NU
adauga explicații, comentarii sau text suplimentar - DOAR numarul.
"""

JUDGE_USER_PROMPT_ZERO_SHOT_TEMPLATE = """REFERINTA:
{gt}

PREDICTIE:
{pred}

Acuratețe (0-100):"""


JUDGE_STYLES = ("cot", "zero_shot")


def build_judge_prompt(
    gt_paragraph: str,
    predicted_paragraph: str,
    style: str = "cot",
) -> Tuple[str, str]:
    """Return (system, user) prompts for the LLM-as-a-judge scorer.
    `style` is 'cot' (4-step chain-of-thought with motivation, default)
    or 'zero_shot' (single-integer reply, no reasoning)."""
    if style == "zero_shot":
        sys_p = JUDGE_SYSTEM_PROMPT_ZERO_SHOT_RO
        user_p = JUDGE_USER_PROMPT_ZERO_SHOT_TEMPLATE.format(
            gt=gt_paragraph.strip(), pred=predicted_paragraph.strip(),
        )
    elif style == "cot":
        sys_p = JUDGE_SYSTEM_PROMPT_COT_RO
        user_p = JUDGE_USER_PROMPT_COT_TEMPLATE.format(
            gt=gt_paragraph.strip(), pred=predicted_paragraph.strip(),
        )
    else:
        raise ValueError(
            f"judge style must be one of {JUDGE_STYLES}, got {style!r}"
        )
    return (sys_p, user_p)


# Pull the motivation sentence out of a CoT judge reply. The CoT
# prompt explicitly asks the judge to prefix its motivation line
# with 'Motivatie:'. Falls back to the line immediately preceding
# the final '[N]' bracket if no prefix was emitted.
_MOTIVATION_PREFIX_RE = re.compile(
    r"(?im)^\s*motiva[tț]ie\s*[:\-]\s*(.+?)\s*$"
)


def extract_judge_motivation(reply: str) -> Optional[str]:
    """Return the judge's one-sentence motivation from a CoT reply,
    or None for zero-shot replies / malformed CoT replies."""
    if not reply:
        return None
    m = _MOTIVATION_PREFIX_RE.search(reply)
    if m:
        return m.group(1).strip()
    # Fallback: take the last non-empty line before the final '[N]'.
    lines = [ln.strip() for ln in reply.splitlines() if ln.strip()]
    if not lines:
        return None
    for i in range(len(lines) - 1, -1, -1):
        if _RESULT_BRACKET_RE.search(lines[i]):
            for j in range(i - 1, -1, -1):
                if lines[j] and not _RESULT_BRACKET_RE.search(lines[j]):
                    return lines[j]
            break
    return None


# The new judge prompt asks for the aggregate score on the last line
# wrapped in '[]' WITHOUT a comma inside (e.g. [73]). That marker is
# distinguishable from the temperature ranges [a, b] sprinkled
# throughout the comparison table, which always contain a comma.
# Pick the LAST occurrence of a single-integer bracket so per-zone
# justifications that happen to use 'scor [N]' inline don't get
# mistaken for the aggregate.
_RESULT_BRACKET_RE = re.compile(r"\[\s*(\d{1,3})\s*\]")

# Fallback: plain integer-percentage extractor for replies that
# ignore the bracket convention. Kept so a misbehaving judge still
# produces a score instead of an unscored row.
_PERCENT_RE = re.compile(r"(?<![-\d.])(\d{1,3})(?:\s*%)?(?![.\d])")


def parse_judge_score(reply: str) -> Optional[int]:
    """
    Extract the 0..100 integer the judge was asked to return on the
    last line wrapped in '[]'. Falls back to the legacy bare-integer
    extractor (last value in [0, 100]) only when no bracketed marker
    is present so a non-compliant judge still produces a score.
    """
    if not reply:
        return None
    bracket_matches = _RESULT_BRACKET_RE.findall(reply)
    if bracket_matches:
        for raw in reversed(bracket_matches):
            v = int(raw)
            if 0 <= v <= 100:
                return v
    for m in reversed(list(_PERCENT_RE.finditer(reply))):
        v = int(m.group(1))
        if 0 <= v <= 100:
            return v
    return None


# ---------------------------------------------------------------------------
# Ollama client wrapper
# ---------------------------------------------------------------------------
#
# Talks to a local Ollama HTTP API (default http://localhost:11434).
# Per-call options:
#   - num_ctx: lifted from Ollama's 4K-8K default to a value that fits
#              the largest prompt our runner will produce (~16K input
#              tokens plus headroom). Default 32768; configurable per
#              model.
#   - keep_alive: keep the model loaded in GPU between calls so the
#              hot-path through (5 modes x 4 folds) doesn't pay the
#              load-from-disk cost on every iteration. "30m" is plenty
#              for one model's full pass.
#   - temperature: low (0.2) so the [x, y] format constraint is more
#              consistently honoured.
#
# This client is intentionally PER-MODEL. Different models can run
# with different num_ctx settings (gpt-oss has a larger context than
# the q4_K_M llama models). The runner instantiates one client per
# model in the iteration.

_OLLAMA_DEFAULT_BASE_URL = "http://localhost:11434"
_OLLAMA_DEFAULT_NUM_CTX = 36864
_OLLAMA_DEFAULT_KEEP_ALIVE = "30m"
_OLLAMA_DEFAULT_TEMPERATURE = 0.2


class OllamaClient:
    """
    Thin wrapper around Ollama's /api/chat endpoint. Stateless between
    calls - each chat() invocation is an independent (system, user)
    request, but the model stays warm in GPU thanks to keep_alive.
    """

    def __init__(
        self,
        model: str,
        base_url: str = _OLLAMA_DEFAULT_BASE_URL,
        num_ctx: int = _OLLAMA_DEFAULT_NUM_CTX,
        temperature: float = _OLLAMA_DEFAULT_TEMPERATURE,
        keep_alive: str = _OLLAMA_DEFAULT_KEEP_ALIVE,
        timeout_s: int = 600,
        auth_token: Optional[str] = None,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.num_ctx = num_ctx
        self.temperature = temperature
        self.keep_alive = keep_alive
        self.timeout_s = timeout_s
        self.auth_token = auth_token
        self.last_meta: Dict = {}

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """
        Send a (system, user) chat to Ollama, return the assistant's
        reply as a string. Raises requests.HTTPError on transport
        failure; the runner should treat that as a missing prediction
        (and surface in the JSON).

        Side effect: populates self.last_meta with token-usage and
        stop-reason fields so the runner can detect input truncation
        and output cut-offs.
        """
        import requests  # local import keeps llm_comparison usable without HTTP
        self.last_meta = {}
        url = f"{self.base_url}/api/chat"
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {
                "num_ctx": self.num_ctx,
                "temperature": self.temperature,
            },
            "stream": False,
            "keep_alive": self.keep_alive,
        }
        resp = requests.post(
            url, json=payload, headers=headers, timeout=self.timeout_s,
        )
        resp.raise_for_status()
        body = resp.json()
        if "message" not in body or "content" not in body["message"]:
            raise RuntimeError(
                f"unexpected Ollama response shape: {list(body.keys())}"
            )
        self.last_meta = {
            "provider": "ollama",
            "model": self.model,
            "num_ctx": self.num_ctx,
            "input_tokens": body.get("prompt_eval_count"),
            "output_tokens": body.get("eval_count"),
            "done_reason": body.get("done_reason"),
        }
        return body["message"]["content"]


class MockOllamaClient:
    """
    Drop-in replacement for OllamaClient that returns canned Romanian
    paragraphs in the [x, y] format, without any HTTP calls. Used by
    --dry_run to validate the runner's orchestration end-to-end before
    any real GPU time gets spent.

    The fake reply is deterministic given the (model_id, fold, mode,
    scenario) signature embedded in the user prompt, so the same
    dry-run invocation produces the same outputs every time and
    differences across modes/folds are visible.
    """

    _CANNED_TEMPLATE = (
        "Mediile lunare de temperatura au fost cuprinse intre [{a1}, {b1}] °C "
        "in Muntenia, in Dobrogei, in Olteniei si in Banatului. "
        "Pe litoral si in Delta Dunarii, mediile au fost intre [{a2}, {b2}] °C. "
        "In sud-estul Munteniei si in nordul Moldovei, intervalul a fost "
        "[{a3}, {b3}] °C. In Transilvania si in Maramures, mediile au variat "
        "intre [{a4}, {b4}] °C. In zona montana inalta temperaturile au fost "
        "cuprinse intre [{a5}, {b5}] °C, iar pe creste sub [{a6}, {b6}] °C."
    )

    def __init__(self, model: str, **_kwargs):
        self.model = model
        self.last_meta: Dict = {}

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        # Derive the canned intervals from a stable hash of the prompts
        # so dry-runs are reproducible. The bins are always 2 °C wide
        # to honour the system prompt's spec.
        import hashlib
        h = hashlib.sha256((self.model + user_prompt).encode("utf-8")).hexdigest()
        seed = int(h[:8], 16)
        # Six bins covering roughly the plausible temperature range.
        base = (seed % 30) - 10                              # -10..+19
        bins = [base + 2 * i for i in range(6)]
        ranges = [(b, b + 2) for b in bins]
        self.last_meta = {
            "provider": "mock",
            "model": self.model,
            "num_ctx": None,
            "input_tokens": None,
            "output_tokens": None,
            "done_reason": "stop",
        }
        return self._CANNED_TEMPLATE.format(
            a1=ranges[0][0], b1=ranges[0][1],
            a2=ranges[1][0], b2=ranges[1][1],
            a3=ranges[2][0], b3=ranges[2][1],
            a4=ranges[3][0], b4=ranges[3][1],
            a5=ranges[4][0], b5=ranges[4][1],
            a6=ranges[5][0], b6=ranges[5][1],
        )


_OPENAI_JUDGE_DEFAULT_MODEL = "gpt-5-mini"
_OPENAI_JUDGE_REASONING_EFFORT = "minimal"
_OPENAI_JUDGE_MAX_OUTPUT_TOKENS = 2048


def _resolve_openai_api_key(provided: Optional[str]) -> str:
    """
    Resolve an OpenAI API key from an explicit argument or the
    OPENAI_API_KEY environment variable. Raises with a clear message
    otherwise. NEVER read or write the key from/to code or config
    files - environment-only is the only supported path.
    """
    if provided:
        return provided
    env = os.environ.get("OPENAI_API_KEY")
    if env:
        return env
    raise RuntimeError(
        "OpenAI API key not provided. Set the OPENAI_API_KEY environment "
        "variable (PowerShell: setx OPENAI_API_KEY \"sk-...\" then reopen "
        "the terminal) or pass --judge_provider ollama to use a local "
        "Ollama model as judge instead."
    )


class OpenAIJudgeClient:
    """
    Judge-side client that exposes the same .chat(system, user) -> str
    interface as OllamaClient, but routes to the OpenAI Responses API
    (default model: gpt-5-mini). The key is read from OPENAI_API_KEY -
    never hard-coded.
    """

    def __init__(
        self,
        model: str = _OPENAI_JUDGE_DEFAULT_MODEL,
        api_key: Optional[str] = None,
        reasoning_effort: str = _OPENAI_JUDGE_REASONING_EFFORT,
        max_output_tokens: int = _OPENAI_JUDGE_MAX_OUTPUT_TOKENS,
    ):
        from openai import OpenAI  # local import: only needed when judge is OpenAI
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.max_output_tokens = max_output_tokens
        self.last_meta: Dict = {}
        self._client = OpenAI(api_key=_resolve_openai_api_key(api_key))

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        self.last_meta = {}
        try:
            response = self._client.responses.create(
                model=self.model,
                reasoning={"effort": self.reasoning_effort},
                instructions=system_prompt,
                input=user_prompt,
                max_output_tokens=self.max_output_tokens,
            )
            usage = getattr(response, "usage", None)
            incomplete = getattr(response, "incomplete_details", None)
            self.last_meta = {
                "provider": "openai",
                "model": self.model,
                "num_ctx": self.max_output_tokens,
                "input_tokens": getattr(usage, "input_tokens", None) if usage else None,
                "output_tokens": getattr(usage, "output_tokens", None) if usage else None,
                "status": getattr(response, "status", None),
                "incomplete_reason": getattr(incomplete, "reason", None) if incomplete else None,
                "done_reason": (
                    "length"
                    if getattr(incomplete, "reason", None) == "max_output_tokens"
                    else "stop"
                ),
            }
            return response.output_text or ""
        except Exception as e:
            self.last_meta = {
                "provider": "openai",
                "model": self.model,
                "error": f"{type(e).__name__}: {e}",
            }
            return f"Error: {e}"


def llm_judge_score(
    *,
    gt_paragraph: str,
    predicted_paragraph: str,
    llm_call,
    style: str = "cot",
) -> Dict:
    """
    LLM-as-judge scoring. `llm_call` is a callable
    `(system_prompt, user_prompt) -> reply_text` so this function is
    decoupled from any specific Ollama / OpenAI client. `style` is
    'cot' (default, 4-step CoT with motivation) or 'zero_shot' (single
    integer reply).

    Returns:
        {
          'judge_style':       'cot' | 'zero_shot',
          'judge_accuracy':    float in [0, 1] | None,
          'judge_score_int':   int in [0, 100] | None,
          'judge_raw_reply':   str,
          'judge_motivation':  str | None   (CoT only; None for zero_shot)
        }
    """
    system_p, user_p = build_judge_prompt(
        gt_paragraph, predicted_paragraph, style=style,
    )
    reply = llm_call(system_p, user_p)
    score_int = parse_judge_score(reply or "")
    accuracy = score_int / 100.0 if score_int is not None else None
    motivation = extract_judge_motivation(reply) if style == "cot" else None
    return {
        "judge_style": style,
        "judge_accuracy": accuracy,
        "judge_score_int": score_int,
        "judge_raw_reply": reply,
        "judge_motivation": motivation,
    }


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------
#
# Iterates model x scenario x fold x mode for ONE model at a time, per
# the spec "iterating through the llms (so all tests for a single llm
# and move on the the next model)". Persists the running results to a
# per-model JSON file after each individual evaluation, so a crash or
# Ctrl-C mid-pass loses at most one prediction.
#
# Fold schedules:
#   monthly: fold_n in {3, 6, 9}, target_month derived as
#            target_month = fold_n + 1 (predict the month right after
#            the known span; the spec calls for 'predict the next
#            month only')
#   daily:   n_known_days in {6, 12, 18, 24}, target_month is
#            user-configurable (default 4 = April)

MONTHLY_FOLDS = (3, 6, 9)
DAILY_FOLDS = (6, 12, 18, 24)


# Fraction of num_ctx above which we flag an input prompt as
# "near-context-limit" - Ollama silently drops the front of the
# message list when the input exceeds num_ctx, so a fill close to
# 1.0 means content may already be missing from what the model sees.
_NEAR_LIMIT_FRACTION = 0.95


def _extract_truncation_flags(meta: Dict, role: str) -> Dict:
    """
    Turn a client's last_meta into a normalised flags dict. `role` is
    'predictor' or 'judge'. Detects two failure modes:

      * output_truncated: generation stopped because it hit a length
        limit (Ollama done_reason == 'length' / OpenAI status
        'incomplete' with reason 'max_output_tokens').
      * input_near_limit: prompt_eval_count >= num_ctx * 0.95 - Ollama
        does not raise on input overflow; it silently drops the front
        of the messages array, so a near-full input is the only signal
        we get that content may have been lost.
    """
    flags = {
        "role": role,
        "provider": meta.get("provider"),
        "model": meta.get("model"),
        "input_tokens": meta.get("input_tokens"),
        "output_tokens": meta.get("output_tokens"),
        "done_reason": meta.get("done_reason"),
        "status": meta.get("status"),
        "incomplete_reason": meta.get("incomplete_reason"),
        "output_truncated": False,
        "input_near_limit": False,
        "input_fill_ratio": None,
    }
    if meta.get("done_reason") == "length":
        flags["output_truncated"] = True
    if meta.get("incomplete_reason") == "max_output_tokens":
        flags["output_truncated"] = True
    num_ctx = meta.get("num_ctx")
    in_tok = meta.get("input_tokens")
    if num_ctx and in_tok is not None and meta.get("provider") == "ollama":
        ratio = in_tok / float(num_ctx)
        flags["input_fill_ratio"] = round(ratio, 3)
        if ratio >= _NEAR_LIMIT_FRACTION:
            flags["input_near_limit"] = True
    return flags


def _flag_is_problem(flag: Dict) -> bool:
    return bool(flag.get("output_truncated") or flag.get("input_near_limit"))


def _log_token_limit_event(
    log_path: Path,
    eval_idx: int,
    total: int,
    scenario: str,
    fold_n: int,
    mode: str,
    target_month: int,
    pred_flags: Dict,
    judge_flags: Dict,
) -> None:
    """
    Append a single human-readable line per problematic evaluation to
    {output_dir}/logs/token_limits_{model}.log. Only writes when at
    least one of pred/judge actually tripped a limit, so the log stays
    short and grep-able.
    """
    if not (_flag_is_problem(pred_flags) or _flag_is_problem(judge_flags)):
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    import datetime as _dt
    stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parts = [
        stamp,
        f"[{eval_idx}/{total}]",
        f"scenario={scenario}",
        f"fold_n={fold_n}",
        f"mode={mode}",
        f"target_month={target_month:02d}",
    ]
    for role, flag in (("PREDICTOR", pred_flags), ("JUDGE", judge_flags)):
        issues = []
        if flag.get("output_truncated"):
            issues.append(
                f"output_truncated(done_reason={flag.get('done_reason')!r}, "
                f"incomplete_reason={flag.get('incomplete_reason')!r}, "
                f"out_tokens={flag.get('output_tokens')})"
            )
        if flag.get("input_near_limit"):
            issues.append(
                f"input_near_limit(in_tokens={flag.get('input_tokens')}/"
                f"{flag.get('input_tokens') and round(flag.get('input_tokens') / max(flag.get('input_fill_ratio'), 1e-9))}, "
                f"fill_ratio={flag.get('input_fill_ratio')})"
            )
        if issues:
            parts.append(f"{role}({flag.get('provider')}/{flag.get('model')}): "
                         + "; ".join(issues))
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(" | ".join(parts) + "\n")


def _monthly_target_month(fold_n: int) -> int:
    """fold_n=3 -> April; fold_n=6 -> July; fold_n=9 -> October."""
    return fold_n + 1


def _model_id_for_filename(model_name: str) -> str:
    """'llama3.1:70b-instruct-q4_K_S' -> 'llama3.1_70b-instruct-q4_K_S'."""
    return model_name.replace(":", "_").replace("/", "_")


def run_llm_tests(
    *,
    model_name: str,
    client,
    judge_client,
    metadata: dict,
    historic_data_path: str | Path,
    output_dir: str | Path = "llm_runs",
    year: int = 2024,
    daily_test_month: int = 11,
    aux_matrices: Optional[Dict[str, pd.DataFrame]] = None,
    modes: Sequence[str] = MODES,
    date_folder: str = "date",
    n_prior_years: int = 0,
    judge_style: str = "cot",
    on_progress=None,
) -> Dict:
    """
    Run the full (5 modes x [3 monthly folds + 4 daily folds]) test
    matrix for ONE model. Writes the running results to
    {output_dir}/llm_runs_{model_id}.json incrementally.

    Args:
        model_name:     human-readable model identifier, e.g.
                        'gpt-oss:latest'. Used in JSON metadata + the
                        output filename.
        client:         OllamaClient or MockOllamaClient. Must expose
                        .chat(system_prompt, user_prompt) -> str.
        judge_client:   same shape; can be the same instance as client
                        or a different one (e.g. a stronger judge model
                        to mitigate same-model bias).
        metadata:       stations_metadata.json contents.
        historic_data_path: path to historic_data_yyyy.json.
        output_dir:     directory for per-model JSON outputs.
        year:           data year (2024).
        daily_test_month: month to use for the daily scenario (default
                        April = month 4).
        aux_matrices:   dict of pd.DataFrame keyed by 'temp', 'precip',
                        'wind', 'nebulosity'. Required for any mode
                        that uses temperature or aux data.
        modes:          which modes to run; defaults to all five.
        on_progress:    optional callback (event_dict) for live UI.

    Returns:
        Same dict that gets written to disk.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"llm_runs_{_model_id_for_filename(model_name)}.json"
    log_path = out_dir / "logs" / f"token_limits_{_model_id_for_filename(model_name)}.log"

    is_dry_run = isinstance(client, MockOllamaClient)
    print(f"\n{'=' * 60}")
    print(f"LLM test run: model={model_name} (dry_run={is_dry_run})")
    print(f"Output: {out_path}")
    print(f"{'=' * 60}")

    # Drop the prior-year modes when no prior-year history is being
    # consumed: they would be byte-identical to their base modes and
    # only add noise to the plot.
    effective_modes = list(modes)
    if n_prior_years <= 0:
        effective_modes = [m for m in effective_modes if m not in PRIOR_YEAR_MODES]

    run_metadata = {
        "model": model_name,
        "dry_run": is_dry_run,
        "year": year,
        "daily_test_month": daily_test_month,
        "monthly_folds": list(MONTHLY_FOLDS),
        "daily_folds": list(DAILY_FOLDS),
        "modes": list(effective_modes),
        "n_prior_years": int(n_prior_years),
        "judge_style": judge_style,
        "num_ctx": getattr(client, "num_ctx", None),
    }
    results: List[Dict] = []

    def _persist():
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(
                {"metadata": run_metadata, "results": results},
                f, ensure_ascii=False, indent=2,
            )

    # Prior-year target-month paragraphs are constant across folds for
    # a given target_month, so cache to avoid reading the JSON files
    # 7 times per target.
    prior_cache: Dict[int, Dict[int, str]] = {}

    def _get_prior_paragraphs(tm: int) -> Dict[int, str]:
        if tm not in prior_cache:
            prior_cache[tm] = (
                load_prior_year_target_month_paragraphs(
                    target_year=year, target_month=tm,
                    n_prior_years=n_prior_years, date_folder=date_folder,
                ) if n_prior_years > 0 else {}
            )
        return prior_cache[tm]

    total = (len(MONTHLY_FOLDS) + len(DAILY_FOLDS)) * len(effective_modes)
    done = 0
    for scenario, folds in (("monthly", MONTHLY_FOLDS), ("daily", DAILY_FOLDS)):
        for fold_n in folds:
            if scenario == "monthly":
                target_month = _monthly_target_month(fold_n)
            else:
                target_month = daily_test_month
            for mode in effective_modes:
                done += 1
                print(f"\n[{done}/{total}] {scenario} fold={fold_n} target={target_month:02d} "
                      f"mode={mode}")
                try:
                    sys_p, usr_p, zones, gt_para = build_prompt_pair(
                        scenario=scenario, fold_n=fold_n, mode=mode,
                        target_month=target_month, year=year,
                        historic_data_path=historic_data_path,
                        metadata=metadata, aux_matrices=aux_matrices,
                        date_folder=date_folder,
                        prior_year_paragraphs=_get_prior_paragraphs(target_month),
                    )
                    pred_raw = client.chat(sys_p, usr_p)
                    pred_flags = _extract_truncation_flags(
                        getattr(client, "last_meta", {}) or {}, role="predictor"
                    )
                    pred_fluent = postprocess_brackets_to_fluent_romanian(pred_raw)

                    manual = manual_score(
                        predicted_paragraph=pred_raw,
                        gt_paragraph=gt_para,
                        target_month=target_month, year=year,
                        metadata=metadata, date_folder=date_folder,
                    )
                    judge = llm_judge_score(
                        gt_paragraph=gt_para,
                        predicted_paragraph=pred_raw,
                        llm_call=judge_client.chat,
                        style=judge_style,
                    )
                    judge_flags = _extract_truncation_flags(
                        getattr(judge_client, "last_meta", {}) or {}, role="judge"
                    )
                    _log_token_limit_event(
                        log_path, done, total, scenario, fold_n, mode,
                        target_month, pred_flags, judge_flags,
                    )
                    fc = manual["format_compliance"]
                    snap_note = (
                        f"  snapped={fc['n_snapped_to_2c_grid']}/{fc['n_intervals_total']}"
                        if fc["n_snapped_to_2c_grid"] else ""
                    )
                    print(f"    manual accuracy={manual['accuracy']:.3f}  "
                          f"judge accuracy="
                          f"{('%.3f' % judge['judge_accuracy']) if judge['judge_accuracy'] is not None else 'None'}"
                          f"{snap_note}")
                    if _flag_is_problem(pred_flags) or _flag_is_problem(judge_flags):
                        print(f"    WARNING: token-limit event logged to {log_path}")
                    rec = {
                        "scenario": scenario,
                        "fold_n": fold_n,
                        "mode": mode,
                        "target_month": target_month,
                        "year": year,
                        "n_zones": len(zones),
                        "zones": [
                            {"axis": z["axis"], "key": z["key"],
                             "cardinal": z["cardinal"],
                             "n_stations": len(z["stations"])}
                            for z in zones
                        ],
                        "gt_paragraph": gt_para,
                        "predicted_paragraph_raw": pred_raw,
                        "predicted_paragraph_fluent": pred_fluent,
                        "manual_score": {
                            "accuracy": manual["accuracy"],
                            "d_bar": manual["d_bar"],
                            "w": manual["w"],
                            "counts": manual["counts"],
                            "format_compliance": manual["format_compliance"],
                        },
                        "judge_score": judge,
                        "input_prompt_chars": len(usr_p) + len(sys_p),
                        "output_chars": len(pred_raw),
                        "truncation_flags": {
                            "predictor": pred_flags,
                            "judge": judge_flags,
                        },
                    }
                    results.append(rec)
                    if on_progress:
                        on_progress(rec)
                    _persist()
                except Exception as e:
                    err_rec = {
                        "scenario": scenario, "fold_n": fold_n, "mode": mode,
                        "target_month": target_month, "year": year,
                        "error": f"{type(e).__name__}: {e}",
                    }
                    print(f"    ERROR: {err_rec['error']}")
                    results.append(err_rec)
                    _persist()

    print(f"\nDone. {len(results)} evaluations written to {out_path}")
    return {"metadata": run_metadata, "results": results}


# ---------------------------------------------------------------------------
# Baseline -> LLM-format bridge
# ---------------------------------------------------------------------------
#
# Re-uses the existing AR rollout machinery in baselines.py to produce
# per-county temperature predictions for the daily test month, then:
#
#   1. Aggregates per-zone (mean over the zone's counties x all days
#      of the month), bins into a 2 degC interval [a, b] anchored at
#      floor(mean / 2) * 2 so the structure matches what the LLM is
#      asked to emit.
#   2. Builds a synthetic Romanian paragraph in the same [x, y] format
#      so manual_score and the OpenAI judge can score it without any
#      code changes - the resulting JSON file plugs straight into the
#      existing comparison plotter.
#
# The baselines retrain at W = H = 6 corresponds to the daily scenario
# only. There is no monthly equivalent (the baselines operate at daily
# granularity), so this writer only emits daily-scenario rows.

# Maps the baseline retrain --label values to the LLM input modes
# they correspond to. Lines with the same colour in the comparison
# plot will then represent the same input regime regardless of whether
# the row came from an LLM or a baseline.
_BASELINE_LABEL_TO_MODE: Dict[str, str] = {
    "wh6_target": "temp_only",
    "wh6_aux":    "historic_plus_aux",
}


def _bin_2c_floor(mean_value: float, bin_width: float = 2.0) -> Tuple[float, float]:
    """Bin a real value into the 2 degC interval [a, a + w] anchored at
    a = w * floor(mean / w). Returns plain floats so the synthesised
    paragraph parses without scientific notation."""
    a = bin_width * math.floor(mean_value / bin_width)
    return (float(a), float(a + bin_width))


def predict_baseline_full_month(
    *,
    ckpt_path: Path,
    target_month: int,
    year: int,
    n_known_days: int,
    date_folder: str,
    device: str,
) -> Tuple[pd.DataFrame, Dict]:
    """
    Run a one-shot AR rollout from `ckpt_path`. The input window is the
    last W days of the K known days at the start of the target month;
    the rollout fills in the remaining days_in_month - K days. The
    return is a (days_in_month, n_counties) DataFrame indexed by date,
    with the known days copied straight from the daily mean CSV and
    the unknown days filled by the AR predictions, so downstream code
    can aggregate per-zone over the entire month uniformly.
    """
    import torch                                                     # noqa
    from prompting.utils.baselines import (
        load_county_matrix, load_fold_checkpoint, autoregressive_rollout,
    )

    payload_peek = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    W = payload_peek["model_init_kwargs"]["window"]
    H = payload_peek["model_init_kwargs"]["horizon"]
    n_in = payload_peek["model_init_kwargs"]["n_input_channels"]
    n_out = payload_peek["model_init_kwargs"]["n_output_channels"]
    baseline_name = payload_peek["baseline"]
    label = payload_peek.get("label", "")
    extra_csv_filenames = payload_peek.get("extra_csv_filenames")

    input_matrix, target_matrix, dates, counties, _ = load_county_matrix(
        date_folder, "daily_county_mean.csv",
        extra_csv_filenames=extra_csv_filenames,
    )

    first_day = pd.Timestamp(year=year, month=target_month, day=1)
    n_days = (first_day + pd.offsets.MonthEnd(0)).day
    try:
        first_idx = dates.get_loc(first_day)
    except KeyError as e:
        raise ValueError(
            f"first day of {year}-{target_month:02d} not in matrix: {e}"
        )

    if n_known_days < W:
        raise ValueError(
            f"n_known_days={n_known_days} < W={W} - cannot build input window"
        )
    if n_known_days > n_days:
        raise ValueError(
            f"n_known_days={n_known_days} > days_in_month={n_days}"
        )
    days_to_predict = n_days - n_known_days
    window_start_idx = first_idx + (n_known_days - W)

    if window_start_idx + W + days_to_predict > len(dates):
        raise ValueError(
            f"matrix ends at {dates[-1].date()}; need data through "
            f"{(first_day + pd.Timedelta(days=n_days - 1)).date()}"
        )

    init_window = input_matrix[window_start_idx:window_start_idx + W]
    aux_truth = None
    if n_in > n_out and days_to_predict > 0:
        aux_truth = input_matrix[
            window_start_idx + W:window_start_idx + W + days_to_predict,
            n_out:,
        ]

    model, scaler, _payload = load_fold_checkpoint(ckpt_path)
    model = model.to(device).eval()

    if days_to_predict > 0:
        ar_pred = autoregressive_rollout(
            model, scaler, init_window, total_steps=days_to_predict, H=H,
            n_input_channels=n_in, n_output_channels=n_out,
            device=device, aux_truth=aux_truth,
        )
    else:
        ar_pred = np.empty((0, n_out), dtype=np.float32)

    known_days = target_matrix[first_idx:first_idx + n_known_days]
    full_month = np.concatenate([known_days, ar_pred], axis=0)
    pred_df = pd.DataFrame(
        full_month,
        index=pd.date_range(first_day, periods=n_days, freq="D"),
        columns=counties,
    )
    meta = {
        "baseline": baseline_name,
        "label": label,
        "W": W, "H": H,
        "n_input_channels": n_in,
        "n_output_channels": n_out,
        "days_known": n_known_days,
        "days_predicted": days_to_predict,
        "extra_csv_filenames": extra_csv_filenames,
    }
    return pred_df, meta


def baseline_paragraph_from_predictions(
    *,
    predictions: pd.DataFrame,
    zones: List[Dict],
    metadata: dict,
) -> str:
    """
    For each zone in `zones`, compute the predicted MONTHLY mean over
    the zone's counties across every day of `predictions`, snap to the
    nearest 2 degC bin, and emit one Romanian sentence in the
    `intre [a, b] degC` format the manual scorer parses. Zones with
    no matching county column are skipped (no false 'missed' penalty).
    """
    set_metadata_for_aggregators(metadata)
    sentences: List[str] = []
    for z in zones:
        counties_for_zone = _zone_to_counties(z, metadata)
        if not counties_for_zone:
            continue
        available = [c for c in counties_for_zone if c in predictions.columns]
        if not available:
            continue
        block = predictions[available].to_numpy(dtype=float)
        mask = np.isfinite(block)
        if not mask.any():
            continue
        zone_mean = float(block[mask].mean())
        a, b = _bin_2c_floor(zone_mean)
        label = zone_label_romanian(z)
        sentences.append(
            f"In {label}, mediile lunare au fost cuprinse intre "
            f"[{a}, {b}] °C."
        )
    return " ".join(sentences)


def _zones_for_daily_scenario(
    *,
    paragraphs: Dict[str, str],
    target_month: int,
    metadata: dict,
) -> List[Dict]:
    """Mirror build_prompt_pair's daily-scenario zone selection: extract
    + dedupe zones from every month before the target month. Same
    vocabulary the LLM sees."""
    all_zones: List[Dict] = []
    for m in range(1, target_month):
        para = paragraphs.get(romanian_month_name(m), "")
        if para:
            all_zones.extend(extract_zones_from_text(para, metadata))
    return dedupe_zones(all_zones)


def run_baseline_to_llm_format(
    *,
    baselines_dir: str = "baselines",
    output_dir: str = "llm_runs",
    fold: int = 4,
    year: int = 2024,
    daily_test_month: int = 11,
    historic_data_path: str | Path = "date/historic_data_2024.json",
    metadata: Optional[dict] = None,
    date_folder: str = "date",
    use_openai_judge: bool = False,
    judge_model: str = _OPENAI_JUDGE_DEFAULT_MODEL,
    judge_style: str = "cot",
    device: str = "auto",
) -> Dict[str, Path]:
    """
    Walk every fold-N checkpoint under {baselines_dir}/checkpoints/,
    run a daily-scenario evaluation matching the LLM eval matrix at
    K in {6, 12, 18, 24}, and write one
    {output_dir}/llm_runs_baseline_{baseline}_{label}.json per
    checkpoint in the SAME schema as the LLM runner. The existing
    aggregator/plotter then treats baselines as additional 'models'
    in the comparison without any further code changes.
    """
    if metadata is None:
        metadata = load_stations_metadata(Path(date_folder) / "stations_metadata.json")
    set_metadata_for_aggregators(metadata)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ckpt_dir = Path(baselines_dir) / "checkpoints"
    if not ckpt_dir.is_dir():
        raise FileNotFoundError(
            f"no checkpoints/ under {baselines_dir} - retrain with --save_weights"
        )
    ckpts = sorted(ckpt_dir.glob(f"*_fold{fold}.pt"))
    if not ckpts:
        raise FileNotFoundError(
            f"no fold-{fold} checkpoints under {ckpt_dir}"
        )

    if device == "auto":
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            device = "cpu"

    with open(historic_data_path, "r", encoding="utf-8") as f:
        historic = json.load(f)
    paragraphs: Dict[str, str] = historic["caracterizare_lunara"]
    gt_paragraph = paragraphs.get(romanian_month_name(daily_test_month), "")
    zones = _zones_for_daily_scenario(
        paragraphs=paragraphs, target_month=daily_test_month, metadata=metadata,
    )
    print(f"Baseline-as-LLM eval: fold={fold}, test_month={daily_test_month}, "
          f"zones={len(zones)}, device={device}")

    judge_client = OpenAIJudgeClient(model=judge_model) if use_openai_judge else None
    if use_openai_judge:
        print(f"Judge: OpenAI {judge_model} (key from OPENAI_API_KEY env var)")
    else:
        print("Judge: disabled (manual scoring only)")

    written: Dict[str, Path] = {}
    for ckpt_path in ckpts:
        print(f"\n  checkpoint: {ckpt_path.name}")
        run_meta: Dict = {}
        results: List[Dict] = []
        model_id: Optional[str] = None
        out_path: Optional[Path] = None

        for K in DAILY_FOLDS:
            try:
                pred_df, ck_meta = predict_baseline_full_month(
                    ckpt_path=ckpt_path,
                    target_month=daily_test_month, year=year,
                    n_known_days=K, date_folder=date_folder, device=device,
                )
                if model_id is None:
                    label = ck_meta["label"] or "unlabelled"
                    model_id = f"baseline:{ck_meta['baseline']}_{label}"
                    out_path = out_dir / (
                        f"llm_runs_{_model_id_for_filename(model_id)}.json"
                    )
                    run_meta = {
                        "model": model_id,
                        "kind": "baseline",
                        "year": year,
                        "daily_test_month": daily_test_month,
                        "fold": fold,
                        "checkpoint": str(ckpt_path),
                        "W": ck_meta["W"], "H": ck_meta["H"],
                        "n_input_channels": ck_meta["n_input_channels"],
                        "n_output_channels": ck_meta["n_output_channels"],
                        "extra_csv_filenames": ck_meta["extra_csv_filenames"],
                        "judge_style": judge_style if use_openai_judge else None,
                    }
                pred_paragraph = baseline_paragraph_from_predictions(
                    predictions=pred_df, zones=zones, metadata=metadata,
                )
                pred_fluent = postprocess_brackets_to_fluent_romanian(pred_paragraph)
                manual = manual_score(
                    predicted_paragraph=pred_paragraph,
                    gt_paragraph=gt_paragraph,
                    target_month=daily_test_month, year=year,
                    metadata=metadata, date_folder=date_folder,
                )
                if judge_client is not None:
                    judge = llm_judge_score(
                        gt_paragraph=gt_paragraph,
                        predicted_paragraph=pred_paragraph,
                        llm_call=judge_client.chat,
                        style=judge_style,
                    )
                else:
                    judge = {
                        "judge_style": None,
                        "judge_motivation": None,
                        "judge_accuracy": None,
                        "judge_score_int": None,
                        "judge_raw_reply": None,
                    }
                mode = _BASELINE_LABEL_TO_MODE.get(
                    ck_meta["label"], "temp_only"
                )
                rec = {
                    "scenario": "daily",
                    "fold_n": K,
                    "mode": mode,
                    "target_month": daily_test_month,
                    "year": year,
                    "n_zones": len(zones),
                    "zones": [
                        {"axis": z["axis"], "key": z["key"],
                         "cardinal": z["cardinal"],
                         "n_stations": len(z["stations"])}
                        for z in zones
                    ],
                    "gt_paragraph": gt_paragraph,
                    "predicted_paragraph_raw": pred_paragraph,
                    "predicted_paragraph_fluent": pred_fluent,
                    "manual_score": {
                        "accuracy": manual["accuracy"],
                        "d_bar": manual["d_bar"],
                        "w": manual["w"],
                        "counts": manual["counts"],
                        "format_compliance": manual["format_compliance"],
                    },
                    "judge_score": judge,
                    "input_prompt_chars": 0,
                    "output_chars": len(pred_paragraph),
                    "checkpoint_meta": ck_meta,
                }
                print(f"    K={K:>2d}: manual={manual['accuracy']:.3f}  "
                      f"judge="
                      f"{('%.3f' % judge['judge_accuracy']) if judge['judge_accuracy'] is not None else 'None'}")
                results.append(rec)
            except Exception as e:
                print(f"    K={K}: ERROR {type(e).__name__}: {e}")
                results.append({
                    "scenario": "daily", "fold_n": K, "mode": "temp_only",
                    "target_month": daily_test_month, "year": year,
                    "error": f"{type(e).__name__}: {e}",
                })

        if out_path is not None:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"metadata": run_meta, "results": results},
                    f, ensure_ascii=False, indent=2,
                )
            print(f"    -> {out_path}")
            written[model_id] = out_path

    return written


# ---------------------------------------------------------------------------
# Comparison plotter
# ---------------------------------------------------------------------------
#
# Aggregates everything that the runner produced and turns it into:
#
#   1. Per-(scenario, mode) accuracy lines across folds, one line per
#      (model, mode), separate figure per scenario. This is the
#      headline "more known data -> better accuracy" view.
#
#   2. Manual-vs-judge scatter per model. y=x reference + Spearman
#      correlation in the title - so you can see whether the judge is
#      biased relative to the manual algorithm, and in which direction.
#
#   3. Per-model summary CSV: one row per (model, scenario, fold, mode)
#      with manual_accuracy and judge_accuracy, ready for any
#      downstream analysis.


def aggregate_llm_runs(
    llm_runs_dir: str | Path = "llm_runs",
) -> "pd.DataFrame":
    """
    Load every llm_runs_<model>.json under `llm_runs_dir` and flatten
    the rows into one DataFrame with columns:
      [model, scenario, fold_n, mode, target_month, n_zones,
       manual_accuracy, manual_d_bar, manual_intersection, manual_missed,
       manual_false_pos, manual_unscorable,
       judge_accuracy, judge_score_int,
       input_prompt_chars, output_chars]

    Rows that ended in an error during the run are kept but have
    NaN scores so they're visible in any tally.
    """
    out_dir = Path(llm_runs_dir)
    if not out_dir.is_dir():
        raise FileNotFoundError(f"llm_runs directory not found: {out_dir}")

    rows: List[Dict] = []
    for path in sorted(out_dir.glob("llm_runs_*.json")):
        with open(path, "r", encoding="utf-8") as f:
            blob = json.load(f)
        meta = blob.get("metadata", {}) or {}
        model = meta.get("model", path.stem)
        kind = meta.get("kind", "llm")
        run_judge_style = meta.get("judge_style")
        for r in blob.get("results", []):
            ms = r.get("manual_score") or {}
            js = r.get("judge_score") or {}
            counts = ms.get("counts") or {}
            rows.append({
                "model": model,
                "kind": kind,
                "judge_style": js.get("judge_style") or run_judge_style,
                "scenario": r.get("scenario"),
                "fold_n": r.get("fold_n"),
                "mode": r.get("mode"),
                "target_month": r.get("target_month"),
                "n_zones": r.get("n_zones"),
                "manual_accuracy": ms.get("accuracy"),
                "manual_d_bar": ms.get("d_bar"),
                "manual_intersection": counts.get("intersection"),
                "manual_missed": counts.get("missed"),
                "manual_false_pos": counts.get("false_pos"),
                "manual_unscorable": counts.get("unscorable"),
                "judge_accuracy": js.get("judge_accuracy"),
                "judge_score_int": js.get("judge_score_int"),
                "input_prompt_chars": r.get("input_prompt_chars"),
                "output_chars": r.get("output_chars"),
                "had_error": "error" in r,
                "error": r.get("error"),
            })
    return pd.DataFrame(rows)


# Ordered mode list for consistent colour assignment across plots.
_MODE_ORDER = list(MODES)


def plot_llm_accuracy_curves(
    df: "pd.DataFrame",
    output_dir: str | Path,
    show: bool = False,
) -> List[str]:
    """
    Per-scenario figure: x = fold_n, y = manual_accuracy.
    One subplot per scenario; one line per (model, mode). Lines colour-
    coded by mode; one solid colour per mode (same hue across models).
    Models distinguished by linestyle (solid for the first, dashed for
    the second, etc.). With one model (the dry-run case) only solid
    lines appear.

    Writes one PNG per metric (manual + judge) per scenario, so 4 PNGs
    total when both scenarios have data and both scorers were called.
    """
    import matplotlib.pyplot as plt
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: List[str] = []
    if df.empty:
        print("aggregate_llm_runs returned empty df; nothing to plot.")
        return written

    cmap = plt.get_cmap("tab10")
    mode_color = {m: cmap(i) for i, m in enumerate(_MODE_ORDER)}
    models = sorted(df["model"].dropna().unique().tolist())
    model_style = {m: ls for m, ls in
                   zip(models, ["-", "--", ":", "-."])}

    for metric_key, metric_label in [
        ("manual_accuracy", "manual accuracy"),
        ("judge_accuracy", "judge accuracy"),
    ]:
        for scenario in sorted(df["scenario"].dropna().unique().tolist()):
            sub = df[(df["scenario"] == scenario) & df[metric_key].notna()]
            if sub.empty:
                continue
            fig, ax = plt.subplots(figsize=(8, 5.5))
            folds_sorted = sorted(sub["fold_n"].dropna().unique().tolist())

            for model in models:
                for mode in _MODE_ORDER:
                    line = sub[(sub["model"] == model) & (sub["mode"] == mode)]
                    if line.empty:
                        continue
                    line = line.sort_values("fold_n")
                    ax.plot(
                        line["fold_n"].astype(float).tolist(),
                        line[metric_key].astype(float).tolist(),
                        color=mode_color[mode],
                        linestyle=model_style.get(model, "-"),
                        marker="o", markersize=5, linewidth=2,
                        label=f"{model} | {mode}",
                    )

            fold_unit = "known months" if scenario == "monthly" else "known days"
            ax.set_xlabel(f"fold_n ({fold_unit})")
            ax.set_ylabel(metric_label)
            ax.set_xticks(folds_sorted)
            ax.set_ylim(0.0, 1.0)
            ax.grid(True, alpha=0.3)
            ax.set_title(
                f"LLM {metric_label} vs known-data quantity\n"
                f"scenario = {scenario}"
            )
            # Compact legend: one entry per unique (model, mode) — keep
            # outside the plot since 5+ entries get crowded.
            ax.legend(
                fontsize=8, loc="center left",
                bbox_to_anchor=(1.02, 0.5), frameon=False,
            )
            fig.tight_layout()
            out_path = out_dir / f"llm_{metric_key}_{scenario}.png"
            fig.savefig(out_path, dpi=150, bbox_inches="tight")
            written.append(str(out_path))
            print(f"Wrote {out_path}")
            if not show:
                plt.close(fig)
    return written


def plot_manual_vs_judge(
    df: "pd.DataFrame",
    output_dir: str | Path,
    show: bool = False,
) -> List[str]:
    """
    Per-model scatter: x = manual_accuracy, y = judge_accuracy. y=x
    reference line + Spearman correlation in the title. One figure per
    model.

    A judge that strongly correlates with the manual algorithm and
    sits near y=x is unbiased. Systematic deviation (most points
    above the diagonal -> judge over-scores; below -> judge under-
    scores) is what we want to detect.
    """
    import matplotlib.pyplot as plt
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: List[str] = []
    if df.empty:
        return written

    cmap = plt.get_cmap("tab10")
    mode_color = {m: cmap(i) for i, m in enumerate(_MODE_ORDER)}

    for model in sorted(df["model"].dropna().unique().tolist()):
        sub = df[(df["model"] == model)
                 & df["manual_accuracy"].notna()
                 & df["judge_accuracy"].notna()]
        if sub.empty:
            continue

        fig, ax = plt.subplots(figsize=(6.5, 6))
        for mode in _MODE_ORDER:
            mc = sub[sub["mode"] == mode]
            if mc.empty:
                continue
            ax.scatter(
                mc["manual_accuracy"], mc["judge_accuracy"],
                color=mode_color[mode], label=mode, s=70,
                edgecolor="black", linewidth=0.4, alpha=0.85,
            )
        # y = x reference
        ax.plot([0, 1], [0, 1], color="black", linestyle=":", linewidth=1.0,
                label="y = x (unbiased judge)")

        # Spearman correlation (rank-based; robust to monotonic
        # rescaling between the two scorers)
        x = sub["manual_accuracy"].astype(float).values
        y = sub["judge_accuracy"].astype(float).values
        if len(x) >= 3:
            x_rank = pd.Series(x).rank().values
            y_rank = pd.Series(y).rank().values
            corr = float(np.corrcoef(x_rank, y_rank)[0, 1])
            corr_txt = f"Spearman corr = {corr:+.3f}"
        else:
            corr_txt = "(too few points for Spearman)"

        ax.set_xlim(0.0, 1.0)
        ax.set_ylim(0.0, 1.0)
        ax.set_xlabel("manual accuracy")
        ax.set_ylabel("judge accuracy")
        ax.set_aspect("equal")
        ax.grid(True, alpha=0.3)
        ax.set_title(f"Manual vs judge agreement\n{model}\n{corr_txt}")
        ax.legend(fontsize=8, loc="upper left", frameon=False)
        fig.tight_layout()

        out_path = out_dir / f"manual_vs_judge_{_model_id_for_filename(model)}.png"
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        written.append(str(out_path))
        print(f"Wrote {out_path}")
        if not show:
            plt.close(fig)
    return written


def write_summary_table(
    df: "pd.DataFrame",
    output_dir: str | Path,
    filename: str = "summary.csv",
) -> str:
    """Persist the aggregated DataFrame as CSV next to the figures."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    df.to_csv(out_path, index=False, encoding="utf-8")
    print(f"Wrote {out_path}  ({len(df)} rows, "
          f"{df['model'].nunique()} model(s))")
    return str(out_path)


def _zone_interval_table(
    paragraph: str,
    metadata: dict,
) -> List[Tuple[str, Tuple[int, int]]]:
    """Extract one (zone_label, [a, b]) row per distinct zone mention
    in the paragraph, deduped by axis+key+cardinal. Intervals are
    already snapped to the 2 degC grid by extract_predictions_from_paragraph.
    """
    records = extract_predictions_from_paragraph(paragraph, metadata)
    rows: List[Tuple[str, Tuple[int, int]]] = []
    seen = set()
    for r in records:
        key = (r.get("axis"), r.get("key"), r.get("cardinal"))
        if key in seen:
            continue
        seen.add(key)
        z = {
            "axis": r["axis"],
            "ident": r.get("ident") or r.get("key"),
            "cardinal": r.get("cardinal"),
        }
        label = zone_label_romanian(z)
        a, b = r["interval"]
        rows.append((label, (int(a), int(b))))
    return rows


def _render_zone_table(ax, rows: List[Tuple[str, Tuple[int, int]]], title: str):
    """Render a list of (zone, interval) pairs as a tabular text block."""
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_linewidth(0.6)
    if not rows:
        ax.text(
            0.05, 0.95, "(no parseable\nzone+interval pairs)",
            transform=ax.transAxes, va="top", ha="left",
            fontsize=8, family="monospace", color="gray",
        )
        ax.set_title(title, fontsize=9, loc="left")
        return
    # Truncate over-long zone labels so the column lines up.
    max_label_chars = 32
    lines = []
    for label, (a, b) in rows:
        short = label if len(label) <= max_label_chars else label[: max_label_chars - 1] + "."
        lines.append(f"{short:<{max_label_chars}s}  [{a:>3d}, {b:>3d}]")
    ax.text(
        0.02, 0.97, "\n".join(lines),
        transform=ax.transAxes, va="top", ha="left",
        fontsize=7.5, family="monospace",
    )
    ax.set_title(title, fontsize=9, loc="left")


def plot_top3_paragraph_comparison(
    df: "pd.DataFrame",
    llm_runs_dir: str | Path,
    output_dir: str | Path,
    metadata: dict,
    metric: str = "manual_accuracy",
    show: bool = False,
) -> List[str]:
    """
    For each model, pick the three best-scoring evaluations by `metric`
    and render a figure with three rows x four columns:

        col 0: GT paragraph text (wrapped)
        col 1: GT zone -> interval table (extracted via the same parser
               manual_score uses)
        col 2: PRED paragraph text (fluent post-processed)
        col 3: PRED zone -> interval table

    Lets you read at a glance which scenario/fold/mode combinations
    a model is performing best on, see the prose side-by-side, and
    audit the zone coverage / interval correctness without scrolling
    through JSON files.

    Pass `metric="judge_accuracy"` for the judge-ranked variant; the
    output filename includes the metric so both can coexist.
    """
    import matplotlib.pyplot as plt
    import textwrap

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: List[str] = []
    if df.empty:
        return written

    runs_dir = Path(llm_runs_dir)
    json_blobs: Dict[str, Dict] = {}
    for path in sorted(runs_dir.glob("llm_runs_*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                blob = json.load(f)
        except Exception as e:
            print(f"  warn: failed to read {path.name}: {e}")
            continue
        model = (blob.get("metadata") or {}).get("model") or path.stem
        json_blobs[model] = blob

    set_metadata_for_aggregators(metadata)

    for model in sorted(df["model"].dropna().unique()):
        sub = df[(df["model"] == model) & df[metric].notna()]
        if sub.empty:
            continue
        top3 = sub.nlargest(3, metric)
        blob = json_blobs.get(model)
        if blob is None:
            continue
        records = blob.get("results") or []

        fig = plt.figure(figsize=(26, 22), layout="constrained")
        gs = fig.add_gridspec(
            nrows=3, ncols=4, width_ratios=[3.0, 1.3, 3.0, 1.3],
        )
        fig.suptitle(
            f"Top 3 evaluations by {metric.replace('_', ' ')} - {model}",
            fontsize=14, fontweight="bold",
        )

        for i, (_, row) in enumerate(top3.iterrows()):
            rec = next(
                (
                    r for r in records
                    if r.get("scenario") == row["scenario"]
                    and r.get("fold_n") == row["fold_n"]
                    and r.get("mode") == row["mode"]
                    and r.get("target_month") == row["target_month"]
                ),
                None,
            )
            gt = (rec or {}).get("gt_paragraph", "") or "(missing)"
            pred = (rec or {}).get("predicted_paragraph_fluent", "") or "(missing)"
            manual_a = row.get("manual_accuracy")
            judge_a = row.get("judge_accuracy")
            run_label = (
                f"{row['scenario']} fold_n={row['fold_n']} mode={row['mode']} "
                f"target_month={int(row['target_month']):02d}  "
                f"manual={('%.3f' % manual_a) if manual_a == manual_a else 'n/a'}  "
                f"judge={('%.3f' % judge_a) if judge_a == judge_a else 'n/a'}"
            )

            ax_gt_text = fig.add_subplot(gs[i, 0])
            ax_gt_tbl = fig.add_subplot(gs[i, 1])
            ax_pr_text = fig.add_subplot(gs[i, 2])
            ax_pr_tbl = fig.add_subplot(gs[i, 3])

            for ax, text, side in (
                (ax_gt_text, gt, "GROUND TRUTH"),
                (ax_pr_text, pred, "PREDICTION (filtered)"),
            ):
                wrapped = textwrap.fill(text, width=80)
                ax.text(
                    0.02, 0.97, wrapped,
                    transform=ax.transAxes,
                    va="top", ha="left",
                    fontsize=9, family="serif",
                )
                ax.set_title(f"{side}\n{run_label}", fontsize=10, loc="left")
                ax.set_xticks([])
                ax.set_yticks([])
                for s in ax.spines.values():
                    s.set_linewidth(0.6)

            _render_zone_table(
                ax_gt_tbl, _zone_interval_table(gt, metadata),
                title="GT zones -> [a, b]",
            )
            _render_zone_table(
                ax_pr_tbl, _zone_interval_table(pred, metadata),
                title="PRED zones -> [a, b]",
            )

        out_path = out_dir / (
            f"top3_comparison_{_model_id_for_filename(model)}_by_{metric}.png"
        )
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        written.append(str(out_path))
        print(f"Wrote {out_path}")
        if not show:
            plt.close(fig)
    return written


def plot_judge_style_comparison(
    zero_shot_dir: str | Path,
    cot_dir: str | Path,
    output_dir: str | Path,
    metadata: dict,
    show: bool = False,
    top_n: int = 3,
) -> Dict:
    """
    Compare two parallel `llm_runs_*` directories that differ only by
    `--judge_style` (one with `zero_shot`, one with `cot`). Intersect
    on model name (only models that appear in BOTH directories with
    the SAME predictions are usable) and emit:

      1. summary_judge_compare.csv  - flat table with two rows per
         (model, scenario, fold, mode), one per style, plus manual.
      2. accuracy_curves_zero_shot_vs_cot_<scenario>.png  - per-
         scenario accuracy curves with one line per
         (model, style). Manual curves overlap because the
         predictions are identical; judge curves are the interesting
         comparison.
      3. judge_style_side_by_side_<model>.png  - top-N evals by
         manual_accuracy for each model: GT + GT zone table + PRED +
         PRED zone table on one row, then a row beneath showing the
         zero-shot judge score and the CoT judge score + extracted
         motivation.

    Returns: { 'models_common': [...], 'rows': int, 'files': [...] }
    """
    import matplotlib.pyplot as plt
    import textwrap

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: List[str] = []
    set_metadata_for_aggregators(metadata)

    df_zs = aggregate_llm_runs(zero_shot_dir).assign(judge_style="zero_shot")
    df_ct = aggregate_llm_runs(cot_dir).assign(judge_style="cot")
    if df_zs.empty or df_ct.empty:
        print(f"  warn: one of the input dirs is empty "
              f"(zero_shot={len(df_zs)} rows, cot={len(df_ct)} rows); "
              f"skipping judge_compare.")
        return {"models_common": [], "rows": 0, "files": []}

    common = sorted(set(df_zs["model"].dropna()) & set(df_ct["model"].dropna()))
    if not common:
        print("  warn: no models appear in both directories; "
              "judge_compare needs the same --model run with each "
              "--judge_style. Skipping.")
        return {"models_common": [], "rows": 0, "files": []}

    df = pd.concat([df_zs, df_ct], ignore_index=True)
    df = df[df["model"].isin(common)]
    csv_path = out_dir / "summary_judge_compare.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8")
    written.append(str(csv_path))
    print(f"Wrote {csv_path}  ({len(df)} rows, {len(common)} common model(s))")

    # ---- accuracy curves overlaid by judge style ----
    for scenario in df["scenario"].dropna().unique():
        sub = df[df["scenario"] == scenario]
        if sub.empty:
            continue
        fig, axes = plt.subplots(
            1, 2, figsize=(16, 6), constrained_layout=True, sharey=True,
        )
        fig.suptitle(
            f"Zero-shot vs CoT judge - {scenario} scenario", fontweight="bold",
        )
        cmap = plt.get_cmap("tab10")
        for ax, metric, label in (
            (axes[0], "manual_accuracy", "Manual"),
            (axes[1], "judge_accuracy", "Judge"),
        ):
            for i, model in enumerate(common):
                for style, ls in (("zero_shot", ":"), ("cot", "-")):
                    mask = (
                        (sub["model"] == model)
                        & (sub["judge_style"] == style)
                        & sub[metric].notna()
                    )
                    rows = sub[mask].groupby("fold_n")[metric].mean()
                    if rows.empty:
                        continue
                    ax.plot(
                        rows.index, rows.values,
                        color=cmap(i % 10), linestyle=ls,
                        marker="o", markersize=4,
                        label=f"{model} [{style}]",
                    )
            ax.set_title(f"{label} accuracy")
            ax.set_xlabel("fold_n (known units)")
            ax.set_ylabel("accuracy")
            ax.grid(True, alpha=0.3)
            ax.set_ylim(0, 1)
        axes[1].legend(fontsize=7, loc="upper left", bbox_to_anchor=(1.02, 1.0))
        out_path = out_dir / f"accuracy_curves_zero_shot_vs_cot_{scenario}.png"
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        written.append(str(out_path))
        print(f"Wrote {out_path}")
        if not show:
            plt.close(fig)

    # ---- per-model side-by-side with motivation ----
    # Reload raw JSONs to fetch gt_paragraph / predicted_paragraph_fluent
    # / judge_motivation per (scenario, fold_n, mode, target_month).
    def _load_records(dir_path: Path) -> Dict[str, List[Dict]]:
        out: Dict[str, List[Dict]] = {}
        for path in sorted(Path(dir_path).glob("llm_runs_*.json")):
            with open(path, "r", encoding="utf-8") as f:
                blob = json.load(f)
            model = (blob.get("metadata") or {}).get("model") or path.stem
            out[model] = blob.get("results") or []
        return out

    zs_records = _load_records(Path(zero_shot_dir))
    ct_records = _load_records(Path(cot_dir))

    for model in common:
        # Pick top-N evals by CoT manual_accuracy (manual is identical
        # across styles, but the CoT JSON also carries motivation we
        # want to display).
        sub = df_ct[df_ct["model"] == model]
        sub = sub[sub["manual_accuracy"].notna()]
        if sub.empty:
            continue
        top = sub.nlargest(top_n, "manual_accuracy")

        fig = plt.figure(figsize=(26, 7 * len(top)), layout="constrained")
        gs = fig.add_gridspec(
            nrows=2 * len(top), ncols=4,
            width_ratios=[3.0, 1.3, 3.0, 1.3],
            height_ratios=[3] * (2 * len(top)),
        )
        fig.suptitle(
            f"Zero-shot vs CoT judge - top {top_n} evals - {model}",
            fontsize=14, fontweight="bold",
        )

        for i, (_, row) in enumerate(top.iterrows()):
            key = (
                row["scenario"], row["fold_n"], row["mode"],
                int(row["target_month"]),
            )

            def _find(records: List[Dict]) -> Optional[Dict]:
                for r in records:
                    if (
                        r.get("scenario") == key[0]
                        and r.get("fold_n") == key[1]
                        and r.get("mode") == key[2]
                        and r.get("target_month") == key[3]
                    ):
                        return r
                return None

            rec_ct = _find(ct_records.get(model, []))
            rec_zs = _find(zs_records.get(model, []))
            if rec_ct is None:
                continue
            gt = rec_ct.get("gt_paragraph", "") or "(missing)"
            pred = rec_ct.get("predicted_paragraph_fluent", "") or "(missing)"
            ct_js = (rec_ct.get("judge_score") or {})
            zs_js = (rec_zs.get("judge_score") or {}) if rec_zs else {}
            ct_score = ct_js.get("judge_accuracy")
            zs_score = zs_js.get("judge_accuracy")
            motivation = ct_js.get("judge_motivation") or "(no motivation parsed)"

            header = (
                f"{row['scenario']} fold_n={row['fold_n']} mode={row['mode']} "
                f"target_month={int(row['target_month']):02d}  "
                f"manual={row['manual_accuracy']:.3f}"
            )

            # Row 0: GT text | GT table | PRED text | PRED table
            ax_gt_text = fig.add_subplot(gs[2 * i, 0])
            ax_gt_tbl = fig.add_subplot(gs[2 * i, 1])
            ax_pr_text = fig.add_subplot(gs[2 * i, 2])
            ax_pr_tbl = fig.add_subplot(gs[2 * i, 3])
            for ax, text, side in (
                (ax_gt_text, gt, "GROUND TRUTH"),
                (ax_pr_text, pred, "PREDICTION (filtered)"),
            ):
                wrapped = textwrap.fill(text, width=80)
                ax.text(0.02, 0.97, wrapped, transform=ax.transAxes,
                        va="top", ha="left", fontsize=9, family="serif")
                ax.set_title(f"{side}\n{header}", fontsize=10, loc="left")
                ax.set_xticks([])
                ax.set_yticks([])
                for s in ax.spines.values():
                    s.set_linewidth(0.6)
            _render_zone_table(
                ax_gt_tbl, _zone_interval_table(gt, metadata),
                title="GT zones -> [a, b]",
            )
            _render_zone_table(
                ax_pr_tbl, _zone_interval_table(pred, metadata),
                title="PRED zones -> [a, b]",
            )

            # Row 1: zero-shot judge result on left half, CoT judge
            # result + motivation on right half.
            ax_zs = fig.add_subplot(gs[2 * i + 1, 0:2])
            ax_ct = fig.add_subplot(gs[2 * i + 1, 2:4])
            for ax, score, label, body in (
                (
                    ax_zs, zs_score, "ZERO-SHOT JUDGE",
                    f"score: {('%.3f' % zs_score) if zs_score is not None else 'n/a'}\n\n"
                    f"(zero-shot returns only the score; no motivation)",
                ),
                (
                    ax_ct, ct_score, "COT JUDGE",
                    f"score: {('%.3f' % ct_score) if ct_score is not None else 'n/a'}\n\n"
                    f"motivatie: {motivation}",
                ),
            ):
                wrapped = textwrap.fill(body, width=80)
                ax.text(0.02, 0.95, wrapped, transform=ax.transAxes,
                        va="top", ha="left", fontsize=9, family="serif")
                ax.set_title(label, fontsize=10, loc="left", fontweight="bold")
                ax.set_xticks([])
                ax.set_yticks([])
                for s in ax.spines.values():
                    s.set_linewidth(0.6)

        out_path = out_dir / (
            f"judge_style_side_by_side_{_model_id_for_filename(model)}.png"
        )
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        written.append(str(out_path))
        print(f"Wrote {out_path}")
        if not show:
            plt.close(fig)

    return {
        "models_common": common,
        "rows": int(len(df)),
        "files": written,
    }


def plot_all(
    llm_runs_dir: str | Path = "llm_runs",
    output_dir: str | Path = "llm_runs/plots",
    show: bool = False,
    metadata: Optional[dict] = None,
    date_folder: str | Path = "date",
) -> Dict:
    """Convenience wrapper: aggregate + write every artefact. Loads
    stations_metadata.json lazily if not provided - the top-3
    comparison figure needs it to re-extract zone+interval tables."""
    df = aggregate_llm_runs(llm_runs_dir)
    if df.empty:
        print(f"No llm_runs_*.json in {llm_runs_dir}; skipping plots.")
        return {"rows": 0, "files": []}
    if metadata is None:
        metadata = load_stations_metadata(
            Path(date_folder) / "stations_metadata.json"
        )
    csv_path = write_summary_table(df, output_dir)
    pngs = plot_llm_accuracy_curves(df, output_dir, show=show)
    pngs += plot_manual_vs_judge(df, output_dir, show=show)
    pngs += plot_top3_paragraph_comparison(
        df, llm_runs_dir, output_dir, metadata,
        metric="manual_accuracy", show=show,
    )
    pngs += plot_top3_paragraph_comparison(
        df, llm_runs_dir, output_dir, metadata,
        metric="judge_accuracy", show=show,
    )
    if show:
        import matplotlib.pyplot as plt
        plt.show()
    return {
        "rows": len(df),
        "files": [csv_path] + pngs,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli_main(argv: Optional[List[str]] = None) -> int:
    import argparse

    p = argparse.ArgumentParser(
        prog="python -m prompting.utils.llm_comparison",
        description=(
            "Run the LLM-vs-baseline comparison framework. The default "
            "subcommand `run` runs the 5 modes x (3 monthly + 4 daily) "
            "fold matrix for ONE model and writes a per-model JSON for "
            "downstream comparison plotting."
        ),
    )
    subs = p.add_subparsers(dest="subcommand", required=True)

    run = subs.add_parser("run", help="Run the test matrix for one model")
    run.add_argument("--model", type=str, required=True,
                     help="Ollama model id, e.g. 'gpt-oss:latest', "
                          "'llama3.1:70b-instruct-q4_K_S', 'llama3.1:8b-instruct-q4_K_M', "
                          "'gemma3:27b-it-q4_K_M'")
    run.add_argument("--judge_provider", type=str, default="openai",
                     choices=["openai", "ollama"],
                     help="Backend for the LLM-as-judge. Default 'openai' "
                          "calls the Responses API with --judge_model "
                          "(default gpt-5-mini); the key is read from the "
                          "OPENAI_API_KEY env var (never from code). Use "
                          "'ollama' to route the judge through a local "
                          "Ollama model instead - useful for offline runs.")
    run.add_argument("--judge_model", type=str, default=None,
                     help="Model id for the judge. With --judge_provider "
                          f"openai defaults to {_OPENAI_JUDGE_DEFAULT_MODEL!r}; "
                          "with --judge_provider ollama defaults to --model "
                          "so prediction and scoring share one Ollama client.")
    run.add_argument("--dry_run", action="store_true",
                     help="Use a mock client that returns canned "
                          "Romanian paragraphs without any HTTP calls. "
                          "Useful for verifying orchestration end-to-end "
                          "before any real GPU time.")
    run.add_argument("--ollama_base_url", type=str,
                     default=_OLLAMA_DEFAULT_BASE_URL,
                     help=f"Ollama server URL (default {_OLLAMA_DEFAULT_BASE_URL}).")
    run.add_argument("--num_ctx", type=int, default=_OLLAMA_DEFAULT_NUM_CTX,
                     help=f"Context window per call (default {_OLLAMA_DEFAULT_NUM_CTX}). "
                          "The largest user prompt we produce is ~16K input tokens, "
                          "so 32K gives a safe margin.")
    run.add_argument("--temperature", type=float, default=_OLLAMA_DEFAULT_TEMPERATURE,
                     help=f"Sampling temperature (default {_OLLAMA_DEFAULT_TEMPERATURE}, "
                          "low so the [x, y] format constraint holds).")
    run.add_argument("--keep_alive", type=str, default=_OLLAMA_DEFAULT_KEEP_ALIVE,
                     help=f"Ollama keep_alive (default {_OLLAMA_DEFAULT_KEEP_ALIVE}). "
                          "Keeps the model loaded in GPU between calls so the "
                          "full pass doesn't pay reload cost on every iteration.")
    run.add_argument("--date_folder", type=str, default="date",
                     help="Folder holding stations_metadata.json, temperature_*.json, "
                          "daily_county_*.csv, historic_data_*.json")
    run.add_argument("--historic_data_filename", type=str,
                     default="historic_data_2024.json")
    run.add_argument("--year", type=int, default=2024)
    run.add_argument("--daily_test_month", type=int, default=11,
                     help="Month (1..12) to use for the daily scenario. "
                          "Default 11 = November (gives the longest in-year "
                          "historic context: Jan..Oct).")
    run.add_argument("--output_dir", type=str, default="llm_runs",
                     help="Directory for per-model JSON outputs.")
    run.add_argument("--modes", type=str, nargs="*", default=None,
                     help=f"Subset of modes to run. With the default "
                          f"--n_prior_years 0, the three *_with_prior "
                          f"modes are auto-filtered, so the effective "
                          f"matrix is 5 modes x 7 folds = 35 evals - the "
                          f"apples-to-apples comparison with the baselines. "
                          f"Pass --n_prior_years > 0 to opt in to the full "
                          f"{len(MODES)}-mode matrix: {list(MODES)}.")
    run.add_argument("--n_prior_years", type=int, default=0,
                     help="How many years BEFORE --year contribute "
                          "target-month ANM paragraphs to the three "
                          "*_with_prior modes. DEFAULT 0 = disabled "
                          "(the *_with_prior modes are filtered out of "
                          "the run, giving the strict apples-to-apples "
                          "5-mode matrix that matches what the baselines "
                          "can see). Opt in by passing a positive int, "
                          "e.g. --n_prior_years 3 loads target-month "
                          "paragraphs from 2023/2022/2021 when --year 2024. "
                          "Missing historic_data_<year>.json files are "
                          "silently skipped.")
    run.add_argument("--judge_style", type=str, default="cot",
                     choices=list(JUDGE_STYLES),
                     help="Judge prompting style. 'cot' (default) is "
                          "the 4-step chain-of-thought with motivation "
                          "+ [N] result. 'zero_shot' restores the old "
                          "single-integer-only prompt for an ablation "
                          "against the CoT design. Use separate "
                          "--output_dir per style to keep the two JSON "
                          "families apart so `judge_compare` can later "
                          "intersect them on model name.")

    plot = subs.add_parser(
        "plot",
        help="Aggregate llm_runs_*.json into CSV + comparison plots.",
    )
    plot.add_argument("--llm_runs_dir", type=str, default="llm_runs",
                      help="Directory containing llm_runs_<model>.json files.")
    plot.add_argument("--output_dir", type=str, default=None,
                      help="Output directory for plots and summary.csv "
                           "(defaults to <llm_runs_dir>/plots).")
    plot.add_argument("--show", action="store_true",
                      help="Also call plt.show() after writing files.")
    plot.add_argument("--date_folder", type=str, default="date",
                      help="Folder holding stations_metadata.json. "
                           "The top-3 comparison figure re-extracts "
                           "zone+interval tables from GT and PRED "
                           "paragraphs via this metadata.")

    baseline_eval = subs.add_parser(
        "baseline_eval",
        help="Evaluate trained baseline checkpoints as if they were LLMs, "
             "writing one llm_runs_baseline_*.json per checkpoint that "
             "plugs into the same comparison plotter.",
    )
    baseline_eval.add_argument("--baselines_dir", type=str, default="baselines",
                               help="Directory holding checkpoints/ from the "
                                    "W=H=6 retrain (default 'baselines').")
    baseline_eval.add_argument("--output_dir", type=str, default="llm_runs",
                               help="Where to write the per-baseline JSON "
                                    "files. Default 'llm_runs' so the existing "
                                    "plotter picks them up automatically.")
    baseline_eval.add_argument("--fold", type=int, default=4,
                               help="Which fold's checkpoint to evaluate "
                                    "(default 4 - the deployable model).")
    baseline_eval.add_argument("--year", type=int, default=2024)
    baseline_eval.add_argument("--daily_test_month", type=int, default=11,
                               help="Month (1..12) to evaluate. Must match "
                                    "the daily_test_month used in the LLM "
                                    "runs so the comparison is apples-to-"
                                    "apples. Default 11 = November.")
    baseline_eval.add_argument("--date_folder", type=str, default="date")
    baseline_eval.add_argument("--historic_data_filename", type=str,
                               default="historic_data_2024.json")
    baseline_eval.add_argument("--use_openai_judge", action="store_true",
                               help="Also score with the OpenAI gpt-5-mini "
                                    "judge (mirrors the LLM eval). Disabled "
                                    "by default since baseline outputs are "
                                    "templated paragraphs and manual scoring "
                                    "is sufficient for the comparison plot.")
    baseline_eval.add_argument("--judge_model", type=str,
                               default=_OPENAI_JUDGE_DEFAULT_MODEL)
    baseline_eval.add_argument("--device", type=str, default="auto",
                               choices=["auto", "cpu", "cuda"])
    baseline_eval.add_argument("--judge_style", type=str, default="cot",
                               choices=list(JUDGE_STYLES),
                               help="Mirror the LLM runner's --judge_style. "
                                    "Only relevant when --use_openai_judge "
                                    "is set; otherwise the field stays None "
                                    "in the bridge JSON.")

    judge_compare = subs.add_parser(
        "judge_compare",
        help="Compare two parallel llm_runs_* directories that differ "
             "only by --judge_style (one zero_shot, one cot). Emits a "
             "merged summary CSV, per-scenario accuracy curves with one "
             "line per (model, style), and a side-by-side top-N "
             "paragraph figure per common model showing both judges' "
             "scores plus the CoT motivation.",
    )
    judge_compare.add_argument("--zero_shot_dir", type=str, required=True,
                               help="Directory holding the zero-shot run's "
                                    "llm_runs_<model>.json files.")
    judge_compare.add_argument("--cot_dir", type=str, required=True,
                               help="Directory holding the CoT run's "
                                    "llm_runs_<model>.json files.")
    judge_compare.add_argument("--output_dir", type=str,
                               default="judge_compare_plots",
                               help="Where to write the comparison CSV + PNGs.")
    judge_compare.add_argument("--top_n", type=int, default=3,
                               help="How many top-scoring evals to render "
                                    "in the per-model side-by-side figure.")
    judge_compare.add_argument("--date_folder", type=str, default="date",
                               help="For loading stations_metadata.json - "
                                    "needed by the zone-extraction tables.")
    judge_compare.add_argument("--show", action="store_true",
                               help="Also call plt.show() after writing files.")

    postprocess = subs.add_parser(
        "postprocess",
        help="Re-apply the fluent-Romanian rewriter over every "
             "llm_runs_*.json under --llm_runs_dir without rerunning "
             "any LLM. Useful for iterating on the rewriter (quantifier "
             "handling, snapping, unit formats) once raw paragraphs "
             "have already been generated.",
    )
    postprocess.add_argument("--llm_runs_dir", type=str, default="llm_runs",
                             help="Directory containing llm_runs_<model>.json.")
    postprocess.add_argument("--backup", action="store_true",
                             help="Write a .json.bak copy of each file "
                                  "before overwriting.")

    args = p.parse_args(argv)

    if args.subcommand == "postprocess":
        print(f"Re-running fluent post-processing over {args.llm_runs_dir}/")
        summary = refresh_fluent_paragraphs(
            llm_runs_dir=args.llm_runs_dir, backup=args.backup,
        )
        total_changed = sum(summary.values())
        print(f"Done. {total_changed} fluent strings changed across "
              f"{len(summary)} files.")
        return 0

    if args.subcommand == "judge_compare":
        metadata = load_stations_metadata(
            Path(args.date_folder) / "stations_metadata.json"
        )
        result = plot_judge_style_comparison(
            zero_shot_dir=args.zero_shot_dir,
            cot_dir=args.cot_dir,
            output_dir=args.output_dir,
            metadata=metadata,
            show=args.show,
            top_n=args.top_n,
        )
        print(f"Common models: {len(result['models_common'])} "
              f"({', '.join(result['models_common']) or '-'})")
        print("Wrote:")
        for f in result["files"]:
            print(f"  {f}")
        return 0

    if args.subcommand == "baseline_eval":
        metadata = load_stations_metadata(
            Path(args.date_folder) / "stations_metadata.json"
        )
        run_baseline_to_llm_format(
            baselines_dir=args.baselines_dir,
            output_dir=args.output_dir,
            fold=args.fold,
            year=args.year,
            daily_test_month=args.daily_test_month,
            historic_data_path=Path(args.date_folder) / args.historic_data_filename,
            metadata=metadata,
            date_folder=args.date_folder,
            use_openai_judge=args.use_openai_judge,
            judge_model=args.judge_model,
            judge_style=args.judge_style,
            device=args.device,
        )
        return 0

    if args.subcommand == "plot":
        output_dir = args.output_dir or str(Path(args.llm_runs_dir) / "plots")
        result = plot_all(
            llm_runs_dir=args.llm_runs_dir,
            output_dir=output_dir,
            show=args.show,
            date_folder=args.date_folder if hasattr(args, "date_folder") else "date",
        )
        print(f"Aggregated {result['rows']} rows across all llm_runs_*.json files.")
        print("Wrote:")
        for f in result["files"]:
            print(f"  {f}")
        return 0

    if args.subcommand != "run":
        p.print_help()
        return 1

    selected_modes = tuple(args.modes) if args.modes else MODES
    for m in selected_modes:
        if m not in MODES:
            print(f"ERROR: unknown mode {m!r}; valid: {MODES}")
            return 2

    metadata = load_stations_metadata(
        Path(args.date_folder) / "stations_metadata.json"
    )
    aux_matrices = {
        "temp":       load_county_daily_matrix("daily_county_mean.csv", args.date_folder),
        "precip":     load_county_daily_matrix("daily_county_precip.csv", args.date_folder),
        "wind":       load_county_daily_matrix("daily_county_wind.csv", args.date_folder),
        "nebulosity": load_county_daily_matrix("daily_county_nebulosity.csv", args.date_folder),
    }
    set_metadata_for_aggregators(metadata)

    if args.dry_run:
        client = MockOllamaClient(args.model)
        judge = MockOllamaClient(args.judge_model or args.model)
    else:
        client = OllamaClient(
            model=args.model, base_url=args.ollama_base_url,
            num_ctx=args.num_ctx, temperature=args.temperature,
            keep_alive=args.keep_alive,
        )
        if args.judge_provider == "openai":
            judge_model = args.judge_model or _OPENAI_JUDGE_DEFAULT_MODEL
            judge = OpenAIJudgeClient(model=judge_model)
            print(f"Judge: OpenAI Responses API, model={judge_model} "
                  "(key from OPENAI_API_KEY env var)")
        else:
            judge_model = args.judge_model or args.model
            if judge_model == args.model:
                judge = client
            else:
                judge = OllamaClient(
                    model=judge_model, base_url=args.ollama_base_url,
                    num_ctx=args.num_ctx, temperature=args.temperature,
                    keep_alive=args.keep_alive,
                )
            print(f"Judge: Ollama, model={judge_model}")

    run_llm_tests(
        model_name=args.model,
        client=client,
        judge_client=judge,
        metadata=metadata,
        historic_data_path=Path(args.date_folder) / args.historic_data_filename,
        output_dir=args.output_dir,
        year=args.year,
        daily_test_month=args.daily_test_month,
        aux_matrices=aux_matrices,
        modes=selected_modes,
        date_folder=args.date_folder,
        n_prior_years=args.n_prior_years,
        judge_style=args.judge_style,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
