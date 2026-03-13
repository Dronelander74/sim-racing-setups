
ACC Setup Specification – Contract README
Repository scope: acc-setup-spec
Audience: Base44 engineering / AI pipeline
Status: MANDATORY – Runtime dependency


1. Purpose (Non‑negotiable)
This repository defines the hard technical contract for generating Assetto Corsa Competizione (ACC) setups.
It is not documentation and not advisory.


If this repository is not loaded at runtime, setup generation MUST FAIL.




2. Repository Structure (Required)
acc-setup-spec/
├── field-manifest/
│   └── <car_id>.json
│
├── car-capabilities/
│   └── <car_id>.json
│
├── track-profiles/        # optional, context only (no numeric values)
├── handling-rules/        # optional, atomic delta rules
└── README_CONTRACT.md


For ACC GT3 Ferrari 296:
field-manifest/ferrari_296_gt3.json
car-capabilities/ferrari_296_gt3.json




3. Definitions
3.1 Field Manifest
Source of truth for structure.
Defines:

Which setup fields exist for a specific car
Valid ACC hierarchical structure
Does NOT define:

Ranges
Default values
Whether a field is modifiable


3.2 Car Capabilities
Source of truth for allowed actions.
Defines, per field:

modifiable: true → AI may apply deltas
modifiable: false → field MUST NEVER be changed
Derived automatically from real setups.


4. Runtime Contract (MANDATORY)
4.1 Load Order
At runtime the system MUST:

Load field-manifest/<car>.json
Load car-capabilities/<car>.json
Load baseline setup JSON
Apply delta rules
Validate final setup


4.2 Hard Validation Rules
The generator MUST FAIL if any of the following occur:

A field is present that is not listed in field-manifest
A field listed in car-capabilities has modifiable = false and is changed
A required field from the manifest is missing
A field path deviates from the manifest structure
No fallback, no auto‑completion, no silent fixes.


5. Explicit Examples
5.1 Allowed
"aero.front.ride_height": {
  "modifiable": true
}


→ AI may change this field.


5.2 Forbidden (Must Fail)
"aero.front.splitter": {
  "modifiable": false
}


If any delta attempts to modify splitter, generation MUST FAIL.
Same rule applies to:

electronics.electronic_elements.ecu_map
mechanical_grip.front.brake_power


6. AI Behaviour Constraints
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


7. Versioning & Integrity

This repository is versioned in Git
Any change to manifests constitutes a breaking change
Runtime systems must pin to a specific commit or tag


8. Responsibility Boundary
If a setup is invalid and this contract was violated:

The fault is in the generation pipeline, not in the data
If this contract is respected:

Setup output is guaranteed to be structurally valid


9. Final Statement


This repository is part of the runtime.
It is not optional.
It is not advisory.


Any system that ignores or bypasses this contract is considered non‑compliant.


End of Contract
