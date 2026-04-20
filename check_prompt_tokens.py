import json
from pathlib import Path
from collections import defaultdict

stats = defaultdict(list)
for f in Path("responses").rglob("*.json"):
    if f.name.startswith("test_summary"):
        continue
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        model = d.get("model", "?")
        pd = d.get("past_days", "?")
        tokens = d.get("metadata", {}).get("prompt_tokens", 0)
        if tokens:
            stats[(model, pd)].append(tokens)
    except Exception:
        pass

for (model, pd), tokens in sorted(stats.items()):
    print(f"{model:50s} pd={pd}  n={len(tokens):3d}  "
          f"min={min(tokens):5d}  max={max(tokens):5d}  "
          f"mean={sum(tokens)//len(tokens):5d}")