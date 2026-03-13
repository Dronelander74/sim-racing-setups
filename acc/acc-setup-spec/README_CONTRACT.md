

# ACC Setup Specification – Contract README

**Repository scope:** `acc-setup-spec`  
**Audience:** Base44 engineering / AI pipeline  
**Status:** **MANDATORY – Runtime dependency**



## 1. Purpose (Non‑negotiable)
This repository defines the hard technical contract for generating Assetto Corsa Competizione (ACC) setups.
It is not documentation and not advisory.


If this repository is not loaded at runtime, setup generation MUST FAIL.




## 2. Repository Structure (Required)

```text

acc-setup-spec/
├── field-manifest/
│   └── <car_id>.json
├── car-capabilities/
│   └── <car_id>.json
└── README_CONTRACT.md
``

For ACC GT3 Ferrari 296:
field-manifest/ferrari_296_gt3.json
car-capabilities/ferrari_296_gt3.json




## 3. Definitions
### 3.1 Field Manifest
Source of truth for structure.
Defines:

Which setup fields exist for a specific car
Valid ACC hierarchical structure
Does NOT define:

Ranges
Default values
Whether a field is modifiable


### 3.2 Car Capabilities
Source of truth for allowed actions.
Defines, per field:

modifiable: true → AI may apply deltas
modifiable: false → field MUST NEVER be changed
Derived automatically from real setups.


## 4. Runtime Contract (MANDATORY)
### 4.1 Load Order
At runtime the system MUST:

Load field-manifest/<car>.json
Load car-capabilities/<car>.json
Load baseline setup JSON
Apply delta rules
Validate final setup


### 4.2 Hard Validation Rules
The generator MUST FAIL if any of the following occur:

A field is present that is not listed in field-manifest
A field listed in car-capabilities has modifiable = false and is changed
A required field from the manifest is missing
A field path deviates from the manifest structure
No fallback, no auto‑completion, no silent fixes.


## 5. Explicit Examples
### 5.1 Allowed

```json
"aero.front.ride_height": {
  "modifiable": true
}


→ AI may change this field.


### 5.2 Forbidden (Must Fail)
```json
"aero.front.splitter": {
  "modifiable": false
}



If any delta attempts to modify splitter, generation MUST FAIL.
Same rule applies to:

electronics.electronic_elements.ecu_map
mechanical_grip.front.brake_power


## 6. AI Behaviour Constraints
The AI MUST NOT:

Invent fields
Omit mandatory fields
Infer missing values
Reconstruct partial setups
Modify non‑modifiable fields
The AI MUST:

Start from a complete baseline
Apply only allowed deltas
Output a complete ACC‑valid setup


### Documentation Usage (Clarification)


Official ACC documentation (physics notes, setup guides, FAQs) is **contextual only** and must be used to understand **physical ranges and cause–effect relationships**, **never** as a source of numeric setup values.  
All numeric values **must originate exclusively from real ACC setups** (official presets or verified community setups) and be traceable via a declared source.


### Domain-Specific Constraints (Non-Structural)

The field-manifest defines structure, paths, and modifiability only.  
Domain-specific constraints (e.g. wet vs dry tyre pressure targets, temperature-dependent heuristics) are **explicitly enforced outside the manifest** via deterministic policies or post-processing guards.

In particular:
- In Wet conditions, tyre pressure targets differ significantly from Dry conditions.
- Such constraints MUST NOT be encoded in the field-manifest.
- The AI MUST operate within these external constraints when generating or adjusting values.




### Wet Tyre Policy (Deterministic Guardrails)

Wet tyres require deterministic guardrails outside the field-manifest (policy, not structure).  
Use `acc/acc-setup-spec/handling-rules/WetPolicy.ts` as the authoritative rule-set for wet PSI targets and temperature evaluation.


## 7. Versioning & Integrity

This repository is versioned in Git
Any change to manifests constitutes a breaking change
Runtime systems must pin to a specific commit or tag


## 8. Responsibility Boundary
If a setup is invalid and this contract was violated:

The fault is in the generation pipeline, not in the data
If this contract is respected:

Setup output is guaranteed to be structurally valid


## 9. Final Statement

> This repository is part of the runtime.  
> It is not optional.  
> It is not advisory.

Any system that ignores or bypasses this contract is considered **non‑compliant**.



End of Contract
