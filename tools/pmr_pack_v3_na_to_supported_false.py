# tools/pmr_pack_v3_na_to_supported_false.py
import json
from pathlib import Path

def fix(node):
    if isinstance(node, dict):
        out = {}
        for k,v in node.items():
            if isinstance(v, str) and v.strip().upper() == "N/A":
                out[k] = {"supported": False, "uiLabel": k}
            else:
                out[k] = fix(v)
        return out
    if isinstance(node, list):
        return [fix(x) for x in node]
    return node

root = Path("pmr/Library/car_range_packs")
for p in root.rglob("*.json"):
    data = json.loads(p.read_text(encoding="utf-8"))
    fixed = fix(data)
    p.write_text(json.dumps(fixed, ensure_ascii=False, indent=2), encoding="utf-8")
print("done")