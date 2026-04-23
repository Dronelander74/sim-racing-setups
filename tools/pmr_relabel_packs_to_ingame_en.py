#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Rewrite PMR car_range_packs replacing Italian uiLabel with in-game English labels,
so Base44 can consume packs without an external mapping JSON.

Default behavior:
- Reads all *.json under --in-root (default: pmr/Library/car_range_packs)
- Writes rewritten packs to --out-root (default: pmr/Library/car_range_packs_en)
- Preserves everything else; only changes uiLabel string values (and a few known typos/corrections).

You can also use --in-place to overwrite the original files (not recommended).
"""

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Tuple

# 1) Italian -> in-game English mapping (exactly your corrected nomenclature)
ITA_TO_INGAME = {
    # Front/Rear suspension & geometry labels
    "Tasso rigidità sterzo": "Spring Rate",
    "Sobbalzo lento": "Slow Bump",
    "Ritorno lento": "Slow Rebound",
    "Sobbalzo rapido": "Fast Bump",
    "Ritorno rapido": "Fast Rebound",
    "Lunghezza fine corsa": "Bump Stop Length",
    "Tasso rigidità fine corsa": "Bump Stop Spring Rate",
    "Campanatura": "Camber",
    "Convergenza": "Toe",
    "Scostamento dal perno": "Caster Offset",
    "Modifica l'altezza dal suolo": "Ride Height Adjust",

    # ARB
    "Barra stabilizzatrice anteriore": "Front Anti-Roll Bar",
    "Barra stabilizzatrice posteriore": "Rear Anti-Roll Bar",

    # Brakes
    "BIAS FRENI": "Brake Bias",
    "PRESSIONE FRENI": "Brake Pressure",

    # Gearbox
    "Rapporto finale": "Final Drive",
    "Da 1a a 6a marcia": "from 1st to 6th Ratio",

    # Aero
    "ALA POSTERIORE": "Rear Wing Angle",

    # Engine/Electronics short labels sometimes appear in italian UIs
    "Freno motore": "Engine Braking",
    "TC": "Traction Control",
}

# 2) Fixes for already-English but wrong spelling you mentioned earlier
EN_FIXUPS = {
    "Engine Breaking": "Engine Braking",   # your correction
}

def deep_relabel(node: Any) -> Tuple[Any, int]:
    """
    Recursively traverse JSON structure.
    - If dict has key 'uiLabel' and it's a string, rewrite it when it matches ITA_TO_INGAME or EN_FIXUPS.
    Returns (new_node, num_changes).
    """
    changes = 0

    if isinstance(node, dict):
        new_dict: Dict[str, Any] = {}
        for k, v in node.items():
            if k == "uiLabel" and isinstance(v, str):
                new_v = ITA_TO_INGAME.get(v, v)
                new_v = EN_FIXUPS.get(new_v, new_v)
                if new_v != v:
                    changes += 1
                new_dict[k] = new_v
            else:
                new_v, ch = deep_relabel(v)
                changes += ch
                new_dict[k] = new_v
        return new_dict, changes

    if isinstance(node, list):
        new_list = []
        for item in node:
            new_item, ch = deep_relabel(item)
            changes += ch
            new_list.append(new_item)
        return new_list, changes

    # primitive
    return node, 0


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-root", default="pmr/Library/car_range_packs",
                    help="Input root folder containing PMR car_range_packs")
    ap.add_argument("--out-root", default="pmr/Library/car_range_packs_en",
                    help="Output root folder for rewritten packs (ignored with --in-place)")
    ap.add_argument("--in-place", action="store_true",
                    help="Overwrite original files in place (creates no output folder)")
    ap.add_argument("--report", action="store_true",
                    help="Print a per-file change report")
    args = ap.parse_args()

    in_root = Path(args.in_root)
    if not in_root.exists():
        raise SystemExit(f"Input root not found: {in_root}")

    out_root = Path(args.out_root)

    total_files = 0
    total_changed_files = 0
    total_label_changes = 0

    for path in in_root.rglob("*.json"):
        # skip the output folder if it sits under input by mistake
        if not args.in_place and out_root in path.parents:
            continue

        total_files += 1
        try:
            data = load_json(path)
        except Exception as e:
            print(f"[SKIP] JSON parse failed: {path} ({e})")
            continue

        new_data, changes = deep_relabel(data)

        # decide output path
        if args.in_place:
            out_path = path
        else:
            rel = path.relative_to(in_root)
            out_path = out_root / rel

        if changes > 0:
            total_changed_files += 1
            total_label_changes += changes
            save_json(out_path, new_data)

            if args.report:
                print(f"[OK] {relpath(path)} -> {relpath(out_path)}  (uiLabel changes: {changes})")
        else:
            # still write file if output folder is used? Usually no.
            if args.report:
                print(f"[NOOP] {path}")

    print("\n=== Summary ===")
    print(f"Files scanned: {total_files}")
    print(f"Files rewritten: {total_changed_files}")
    print(f"uiLabel replacements: {total_label_changes}")
    if not args.in_place:
        print(f"Output folder: {out_root.resolve()}")


def relpath(p: Path) -> str:
    try:
        return str(p.relative_to(Path.cwd()))
    except Exception:
        return str(p)

if __name__ == "__main__":
    main()