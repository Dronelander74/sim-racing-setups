#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PMR Pack v2 upgrader:
- Rewrite uiLabel to in-game English labels.
- Add vsetParams + transform so packs are self-contained for Base44:
  -> no external mapping JSON required.

Important:
- For "click" dampers and "ratio" gearbox values, VSET encoding is not guaranteed.
  The script marks them as calibration_required unless you provide --calibration.

Usage:
  python tools/pmr_pack_v2_bind_vset.py --in-root pmr/Library/car_range_packs --out-root pmr/Library/car_range_packs_v2 --report
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Tuple, Optional

# --- A) UI label relabeling (ITA -> in-game EN) ---
ITA_TO_INGAME = {
    # Suspension/Geometry
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

    # Differential (various Italian phrasings observed)
    "Precarico": "Preload",
    "Frizione": "Clutches",
    "Angolo bloccaggio differenziale in accelerazione": "Power Ramp Angle",
    "Angolo bloccaggio differenziale in decelerazione": "Coast Ramp Angle",
    "Angolo bloccaggio in accelerazione": "Power Ramp Angle",
    "Angolo bloccaggio in decelerazione": "Coast Ramp Angle",
    "Angolo bloccaggio in accelerazione": "Power Ramp Angle",
    "Angolo bloccaggio in decelerazione": "Coast Ramp Angle",
    "Angolo bloccaggio in accelerazione": "Power Ramp Angle",
    "Angolo bloccaggio in decelerazione": "Coast Ramp Angle",

    # Engine/Electronics
    "Freno motore": "Engine Braking",
    "Engine Breaking": "Engine Braking",
    "TC": "Traction Control",

    # Brakes
    "BIAS FRENI": "Brake Bias",
    "PRESSIONE FRENI": "Brake Pressure",

    # Gearbox
    "Rapporto finale": "Final Drive",
    "Da 1a a 6a marcia": "from 1st to 6th Ratio",

    # Aero
    "ALA POSTERIORE": "Rear Wing Angle",

    # Sometimes section labels appear in uiLabel fields
    "DIFFERENZIALE": "DIFFERENTIAL",
    "MOTORE/ELETTRONICA": "ENGINE/ELECTRONICS"
}

EN_FIXUPS = {
    "Engine Breaking": "Engine Braking"
}

# --- B) Transform helpers ---
def scale_transform(ui_to_raw: float, raw_to_ui: float, unit_hint: str = "") -> Dict[str, Any]:
    return {"type": "scale", "uiToRaw": ui_to_raw, "rawToUi": raw_to_ui, "unitHint": unit_hint}

def identity_transform(unit_hint: str = "") -> Dict[str, Any]:
    return {"type": "identity", "unitHint": unit_hint}

def percent_transform() -> Dict[str, Any]:
    # UI 0..100 <-> raw 0..1
    return scale_transform(0.01, 100.0, "%")

def calibration_required(note: str) -> Dict[str, Any]:
    return {"type": "calibration_required", "note": note}

# --- C) Wheel mapping ---
WHEEL_AXLES = {
    "front": ("FL", "FR"),
    "rear": ("RL", "RR")
}

# --- D) Pack-key -> VSET bindings (best-effort + safe assumptions) ---
# Where we have strong evidence from VSET samples:
# - bumpstop-size looks like meters in VSET (0.02 => 20mm) -> mm <-> m scale
# - spring-platform looks like meters -> mm <-> m scale
# - antirollbar looks like N/m -> N/mm <-> N/m scale (x1000)
# - spring-rate looks like N/m -> N/mm <-> N/m scale (x1000)
#
# Dampers in VSET are numeric (e.g. 9000/11000), UI is "click".
# Without calibration we do not guess.
WHEEL_BINDINGS = {
    # Springs
    "steeringStiffness_N_per_mm": {
        "vset_suffix": "spring-rate",
        "transform": scale_transform(1000.0, 0.001, "N/mm")
    },
    # Dampers (click -> raw needs calibration)
    "slowBump_click": {
        "vset_suffix": "slow-bump",
        "transform": calibration_required("Damper click mapping differs per class/car. Provide calibration mapping.")
    },
    "slowRebound_click": {
        "vset_suffix": "slow-rebound",
        "transform": calibration_required("Damper click mapping differs per class/car. Provide calibration mapping.")
    },
    "fastBump_click": {
        "vset_suffix": "fast-bump",
        "transform": calibration_required("Damper click mapping differs per class/car. Provide calibration mapping.")
    },
    "fastRebound_click": {
        "vset_suffix": "fast-rebound",
        "transform": calibration_required("Damper click mapping differs per class/car. Provide calibration mapping.")
    },

    # Bumpstops
    "bumpstopSize_mm": {
        "vset_suffix": "bumpstop-size",
        "transform": scale_transform(0.001, 1000.0, "mm")  # mm <-> m
    },
    "bumpstopStiffness_N_per_mm": {
        "vset_suffix": "bumpstop-stiffness",
        "transform": scale_transform(1000.0, 0.001, "N/mm")  # N/mm <-> N/m
    },

    # Geometry
    "camber_deg": {"vset_suffix": "camber", "transform": identity_transform("deg")},
    "toe_deg": {"vset_suffix": "toe", "transform": identity_transform("deg")},

    # Caster Offset / KPI: VSET in your sample uses FL/FR-kpi-adjuster.
    # Some cars also have caster-adjuster. We provide candidates.
    "kpi_deg": {
        "vset_suffix": "kpi-adjuster",
        "vset_candidates": ["kpi-adjuster", "caster-adjuster", "caster"],
        "transform": identity_transform("deg")
    },

    # Ride Height Adjust: VSET sample uses *-spring-platform (meters)
    "rideHeightAdjust_mm": {
        "vset_suffix": "spring-platform",
        "transform": scale_transform(0.001, 1000.0, "mm")  # mm <-> m
    }
}

# --- E) Non-wheel bindings (single VSET params) ---
NONWHEEL_BINDINGS = {
    # ARB
    ("antiRollBars", "frontARB_N_per_mm"): {
        "vset_param": "F-antirollbar",
        "transform": scale_transform(1000.0, 0.001, "N/mm")
    },
    ("antiRollBars", "rearARB_N_per_mm"): {
        "vset_param": "R-antirollbar",
        "transform": scale_transform(1000.0, 0.001, "N/mm")
    },

    # Aero
    ("aero", "rearWingAngle_deg"): {
        "vset_param": "R-wing-angle",
        "transform": identity_transform("deg")
    },

    # Brakes
    ("brakes", "brakeBias_frontPct"): {
        "vset_param": "brake-bias",
        "transform": percent_transform(),
        "formatHint": "frontPercent"  # Base44 can render as F/R = front / (100-front)
    },
    ("brakes", "brakePressure_pct"): {
        "vset_param": "brake-pressure",
        "transform": percent_transform()
    },

    # Differential
    ("differential", "preload_N"): {
        "vset_param": "diff-preload",
        "transform": identity_transform("N")
    },
    ("differential", "clutches"): {
        "vset_param": "diff-clutches",
        "transform": identity_transform("count")
    },
    ("differential", "powerLockAngles_deg"): {
        "vset_param": "diff-ramp-power",
        "transform": identity_transform("deg")
    },
    ("differential", "coastLockAngles_deg"): {
        "vset_param": "diff-ramp-coast",
        "transform": identity_transform("deg")
    },

    # Electronics (common VSET params)
    ("engineElectronics", "tc"): {
        "vset_param": "tractionControl",
        "transform": identity_transform("level")
    },
    ("engineElectronics", "abs"): {
        "vset_param": "abs",
        "transform": identity_transform("level")
    },

    # Fuel (best-effort; unclear unit in VSET across classes, so mark calibration)
    ("meta", "fuelLevel_L"): {
        "vset_param": "fuelLevel",
        "transform": calibration_required("Fuel Level unit in VSET differs per car (L vs normalized). Calibrate if exporting/importing."),
    }
}

# --- F) Optional calibration overrides file ---
# Format example:
# {
#   "slowBump_click": {"type":"lookup","uiToRaw":{"1":1000,"2":2000}, "rawToUi":{"1000":1,"2000":2}, "unitHint":"raw"},
#   "fastRebound_click": {...}
# }
def apply_calibration_override(transform: Dict[str, Any], overrides: Optional[Dict[str, Any]], key: str) -> Dict[str, Any]:
    if not overrides:
        return transform
    ov = overrides.get(key)
    return ov if isinstance(ov, dict) else transform


def deep_relabel(obj: Any) -> Tuple[Any, int]:
    changes = 0
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k == "uiLabel" and isinstance(v, str):
                nv = ITA_TO_INGAME.get(v, v)
                nv = EN_FIXUPS.get(nv, nv)
                if nv != v:
                    changes += 1
                out[k] = nv
            else:
                nv, ch = deep_relabel(v)
                changes += ch
                out[k] = nv
        return out, changes
    if isinstance(obj, list):
        out_list = []
        for x in obj:
            nx, ch = deep_relabel(x)
            changes += ch
            out_list.append(nx)
        return out_list, changes
    return obj, 0


def add_bindings(pack: Dict[str, Any], overrides: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], int]:
    binding_changes = 0
    uc = pack.get("uiConstraints", {})
    if not isinstance(uc, dict):
        return pack, 0

    # Wheel sections
    for axle_key, wheels in WHEEL_AXLES.items():
        axle = uc.get(axle_key)
        if not isinstance(axle, dict):
            continue
        for pack_key, spec in axle.items():
            if pack_key not in WHEEL_BINDINGS:
                continue
            if not isinstance(spec, dict):
                continue  # skip "N/A"

            bind = WHEEL_BINDINGS[pack_key]
            suffix = bind.get("vset_suffix")
            candidates = bind.get("vset_candidates")

            vset_params = [f"{w}-{suffix}" for w in wheels] if suffix else []
            spec.setdefault("vsetParams", vset_params)

            tr = apply_calibration_override(bind["transform"], overrides, pack_key)
            spec.setdefault("transform", tr)

            if candidates:
                spec.setdefault("vsetParamCandidates", candidates)

            binding_changes += 1

    # Non-wheel sections
    for section_name, section_obj in uc.items():
        if not isinstance(section_obj, dict):
            continue
        for k, v in section_obj.items():
            rule = NONWHEEL_BINDINGS.get((section_name, k))
            if not rule:
                continue
            if not isinstance(v, dict):
                continue
            v.setdefault("vsetParams", [rule["vset_param"]])
            v.setdefault("transform", rule["transform"])
            if "formatHint" in rule:
                v.setdefault("formatHint", rule["formatHint"])
            binding_changes += 1

    # Special: engineBrake
    ee = uc.get("engineElectronics")
    if isinstance(ee, dict) and isinstance(ee.get("engineBrake"), dict):
        eb = ee["engineBrake"]
        # Relabel if typo
        if isinstance(eb.get("uiLabel"), str):
            eb["uiLabel"] = ITA_TO_INGAME.get(eb["uiLabel"], EN_FIXUPS.get(eb["uiLabel"], eb["uiLabel"]))
        # Bind only if supported true
        if eb.get("supported") is True:
            eb.setdefault("vsetParams", ["engineBrake", "engine-brake", "engine-braking"])
            eb.setdefault("transform", identity_transform("level"))
            binding_changes += 1

    return pack, binding_changes


def load_json(p: Path) -> Any:
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(p: Path, data: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-root", default="pmr/Library/car_range_packs", help="Input packs root")
    ap.add_argument("--out-root", default="pmr/Library/car_range_packs_v2", help="Output root (ignored with --in-place)")
    ap.add_argument("--in-place", action="store_true", help="Overwrite originals (not recommended)")
    ap.add_argument("--report", action="store_true", help="Per-file report")
    ap.add_argument("--calibration", default=None, help="Optional JSON overrides for click/ratio transforms")
    args = ap.parse_args()

    in_root = Path(args.in_root)
    if not in_root.exists():
        raise SystemExit(f"Input root not found: {in_root}")

    out_root = Path(args.out_root)
    overrides = load_json(Path(args.calibration)) if args.calibration else None

    scanned = 0
    written = 0
    total_label_changes = 0
    total_binding_changes = 0

    for path in in_root.rglob("*.json"):
        scanned += 1
        try:
            pack = load_json(path)
        except Exception as e:
            print(f"[SKIP] JSON parse failed: {path} ({e})")
            continue

        pack2, label_ch = deep_relabel(pack)
        pack3, bind_ch = add_bindings(pack2, overrides)

        if label_ch == 0 and bind_ch == 0:
            continue

        rel = path.relative_to(in_root)
        out_path = path if args.in_place else (out_root / rel)
        save_json(out_path, pack3)

        written += 1
        total_label_changes += label_ch
        total_binding_changes += bind_ch

        if args.report:
            print(f"[OK] {rel}  uiLabel:{label_ch}  bindings:{bind_ch} -> {out_path}")

    print("\n=== Summary ===")
    print(f"Files scanned: {scanned}")
    print(f"Files written: {written}")
    print(f"uiLabel replacements: {total_label_changes}")
    print(f"vset binding additions: {total_binding_changes}")
    if not args.in_place:
        print(f"Output folder: {out_root.resolve()}")


if __name__ == "__main__":
    main()