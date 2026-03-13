// acc/acc-setup-spec/handling-rules/WetPolicy.ts
// Deterministic policy for ACC Wet tyres (pressure + temperature guardrails).
//
// Sources in docs/acc:
// - Wet optimal pressure: 30–31 PSI; Wet target temp 75–95°C [1](https://gruppobarletta.sharepoint.com/sites/LeadingTrainsTeam/Documenti%20condivisi/Shared%20folder/04.%20Commercial/Events/T-Fest%20&%20Amour/TFest_and_Amour_2026%20(3)%20(1).pdf?web=1)
// - Core operating temp range: 70–100°C [2](https://gruppobarletta.sharepoint.com/sites/FileServer/HR/AX%20-%20Claudia/Policy%20Comportamentale%20On%20board%20-%20Lounge/Policy%20Comp.%20-%20ENG.pdf?web=1)
//
// IMPORTANT: This is a policy/guardrail module, NOT a physics simulation.
// It must be applied deterministically outside the field-manifest.

export type WetCondition = "Wet" | "HeavyRain";

export interface WetEnv {
  airTempC: number;
  trackTempC: number;
  condition: WetCondition;
}

export interface PressureSet {
  left_front: number;
  right_front: number;
  left_rear: number;
  right_rear: number;
}

export interface TempSetC {
  left_front: number;
  right_front: number;
  left_rear: number;
  right_rear: number;
}

export interface WetPolicyConfig {
  // HOT PSI window (wet): 30–31 PSI [1](https://gruppobarletta.sharepoint.com/sites/LeadingTrainsTeam/Documenti%20condivisi/Shared%20folder/04.%20Commercial/Events/T-Fest%20&%20Amour/TFest_and_Amour_2026%20(3)%20(1).pdf?web=1)
  hotPsiMin?: number;     // default 30.0
  hotPsiMax?: number;     // default 31.0
  hotPsiTarget?: number;  // default 30.5

  // Empirical expected cold->hot gain in wet (conservative)
  expectedColdToHotGainPsi?: number; // default 0.9

  // Cold PSI clamp/round
  coldClampMinPsi?: number; // default 27.5
  coldClampMaxPsi?: number; // default 33.0
  roundingStepPsi?: number; // default 0.1

  // Optional front/rear bias (+ => slightly higher front cold PSI)
  frontRearBiasPsi?: number; // default 0.0

  // Temperature core range (ACC): 70–100°C [2](https://gruppobarletta.sharepoint.com/sites/FileServer/HR/AX%20-%20Claudia/Policy%20Comportamentale%20On%20board%20-%20Lounge/Policy%20Comp.%20-%20ENG.pdf?web=1)
  coreTempMinC?: number;   // default 70
  coreTempMaxC?: number;   // default 100

  // Practical target band (guide): 75–95°C [1](https://gruppobarletta.sharepoint.com/sites/LeadingTrainsTeam/Documenti%20condivisi/Shared%20folder/04.%20Commercial/Events/T-Fest%20&%20Amour/TFest_and_Amour_2026%20(3)%20(1).pdf?web=1)
  targetTempMinC?: number; // default 75
  targetTempMaxC?: number; // default 95

  // Temperature enforcement:
  // - "warn": never hard-fail, only warnings
  // - "hard": fail ONLY if outside core range (70–100)
  temperatureEnforcement?: "warn" | "hard"; // default "warn"
}

export interface WetPolicyResult {
  recommendedColdPressures: PressureSet;          // symmetric L/R
  deltaPsiContractPaths: Record<string, number>;  // tyres.*.psi only
  tempRules: {
    coreRangeC: { min: number; max: number };
    targetBandC: { min: number; max: number };
    enforcement: "warn" | "hard";
  };
}

export interface EvalResult {
  status: "OK" | "WARN" | "FAIL";
  messages: string[];
  details?: Record<string, any>;
}

function clamp(x: number, min: number, max: number) {
  return Math.max(min, Math.min(max, x));
}

function roundToStep(x: number, step: number) {
  const inv = 1 / step;
  return Math.round(x * inv) / inv;
}

/**
 * Small, conservative environment correction (PSI).
 * Purpose: stability, not "true simulation".
 */
function envCorrectionPsi(airTempC: number, trackTempC: number) {
  const refTrack = 30;
  const refAir = 20;
  const kTrack = 0.03;
  const kAir = 0.015;
  return (trackTempC - refTrack) * kTrack + (airTempC - refAir) * kAir;
}

function withDefaults(cfg?: WetPolicyConfig) {
  return {
    hotPsiMin: cfg?.hotPsiMin ?? 30.0,
    hotPsiMax: cfg?.hotPsiMax ?? 31.0,
    hotPsiTarget: cfg?.hotPsiTarget ?? 30.5,

    expectedColdToHotGainPsi: cfg?.expectedColdToHotGainPsi ?? 0.9,

    coldClampMinPsi: cfg?.coldClampMinPsi ?? 27.5,
    coldClampMaxPsi: cfg?.coldClampMaxPsi ?? 33.0,
    roundingStepPsi: cfg?.roundingStepPsi ?? 0.1,
    frontRearBiasPsi: cfg?.frontRearBiasPsi ?? 0.0,

    coreTempMinC: cfg?.coreTempMinC ?? 70,
    coreTempMaxC: cfg?.coreTempMaxC ?? 100,
    targetTempMinC: cfg?.targetTempMinC ?? 75,
    targetTempMaxC: cfg?.targetTempMaxC ?? 95,

    temperatureEnforcement: cfg?.temperatureEnforcement ?? "warn",
  };
}

/**
 * Build policy output to be used by the generator.
 * - Produces symmetric L/R cold PSI suggestions.
 * - Provides temperature evaluation ranges.
 */
export function buildWetPolicy(env: WetEnv, cfg?: WetPolicyConfig): WetPolicyResult {
  const d = withDefaults(cfg);

  const envPsi = envCorrectionPsi(env.airTempC, env.trackTempC);

  // cold ≈ hotTarget - expectedGain - envCorrection +/- bias
  const baseCold = d.hotPsiTarget - d.expectedColdToHotGainPsi - envPsi;

  const frontCold = baseCold + d.frontRearBiasPsi;
  const rearCold = baseCold - d.frontRearBiasPsi;

  const lf = roundToStep(clamp(frontCold, d.coldClampMinPsi, d.coldClampMaxPsi), d.roundingStepPsi);
  const rf = lf; // enforce symmetry
  const lr = roundToStep(clamp(rearCold, d.coldClampMinPsi, d.coldClampMaxPsi), d.roundingStepPsi);
  const rr = lr; // enforce symmetry

  const recommendedColdPressures: PressureSet = {
    left_front: lf, right_front: rf, left_rear: lr, right_rear: rr,
  };

  const deltaPsiContractPaths = {
    "tyres.left_front.psi": lf,
    "tyres.right_front.psi": rf,
    "tyres.left_rear.psi": lr,
    "tyres.right_rear.psi": rr,
  };

  return {
    recommendedColdPressures,
    deltaPsiContractPaths,
    tempRules: {
      coreRangeC: { min: d.coreTempMinC, max: d.coreTempMaxC },
      targetBandC: { min: d.targetTempMinC, max: d.targetTempMaxC },
      enforcement: d.temperatureEnforcement,
    },
  };
}

/**
 * Evaluate measured HOT PSI vs wet window (30–31).
 * Warning-only (does not mutate values).
 */
export function evaluateHotPsi(hot: Partial<PressureSet>, cfg?: WetPolicyConfig): EvalResult {
  const d = withDefaults(cfg);
  const msgs: string[] = [];
  const details: any = {};

  (["left_front","right_front","left_rear","right_rear"] as (keyof PressureSet)[]).forEach(k => {
    const v = hot[k];
    if (typeof v !== "number" || !isFinite(v)) return;
    if (v < d.hotPsiMin || v > d.hotPsiMax) {
      msgs.push(`${k}: hot PSI ${v.toFixed(1)} outside wet window ${d.hotPsiMin.toFixed(1)}–${d.hotPsiMax.toFixed(1)}`);
      details[k] = v;
    }
  });

  return { status: msgs.length ? "WARN" : "OK", messages: msgs, details: msgs.length ? details : undefined };
}

/**
 * Evaluate core temps:
 * - FAIL only if outside core range and enforcement="hard"
 * - Otherwise WARN if outside target band or outside core range.
 */
export function evaluateCoreTemps(core: Partial<TempSetC>, cfg?: WetPolicyConfig): EvalResult {
  const d = withDefaults(cfg);

  const outCore: any = {};
  const outTarget: any = {};
  const msgs: string[] = [];

  (["left_front","right_front","left_rear","right_rear"] as (keyof TempSetC)[]).forEach(k => {
    const t = core[k];
    if (typeof t !== "number" || !isFinite(t)) return;

    if (t < d.coreTempMinC || t > d.coreTempMaxC) {
      outCore[k] = t;
      msgs.push(`${k}: core ${t.toFixed(1)}°C outside core range ${d.coreTempMinC}–${d.coreTempMaxC}°C`);
      return;
    }

    if (t < d.targetTempMinC || t > d.targetTempMaxC) {
      outTarget[k] = t;
      msgs.push(`${k}: core ${t.toFixed(1)}°C outside wet target ${d.targetTempMinC}–${d.targetTempMaxC}°C (still within core range)`);
    }
  });

  if (!msgs.length) return { status: "OK", messages: [] };

  if (d.temperatureEnforcement === "hard" && Object.keys(outCore).length) {
    return { status: "FAIL", messages: msgs, details: { outOfCoreRange: outCore, outOfTargetBand: outTarget } };
  }

  return { status: "WARN", messages: msgs, details: { outOfCoreRange: outCore, outOfTargetBand: outTarget } };
}