# V1 Usage Rules

## Principle

The existing V1 codebase is read-only reference only.

V2 is built from scratch according to approved V2 specs.

## Allowed Uses of V1

You may inspect V1 only to understand:
- existing business behavior
- approved formulas
- field names and data shapes
- edge cases
- implementation mistakes to avoid
- screen/workflow ideas

## Forbidden Uses of V1

You must not:
- copy V1 code
- copy V1 folder structure
- copy V1 models
- copy V1 routers
- copy V1 services
- copy V1 frontend components
- reuse V1 frontend calculations
- reuse V1 LLM/tool logic
- reuse V1 scenario mutation logic
- reuse V1 fallback behavior
- treat V1 as authority over approved V2 specs

## Conflict Rule

If V1 conflicts with approved V2 specs:
- follow the approved V2 specs
- mention the conflict in the task report if relevant

If V1 contains behavior not defined in V2 specs:
- record it as an open question
- do not implement it
