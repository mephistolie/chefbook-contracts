# ChefBook Contracts Guide

This repository owns shared public API contracts, not server or client logic.

- Edit `openapi/src/chefbook.yaml` (entry point) and `openapi/src/domains/*.yaml` (domain paths and schemas).
- `openapi/chefbook.yaml` is a generated delivery bundle: run `python3 scripts/bundle.py`; never edit it manually.
- Keep domain schema references pointed at the entry point component registry; do not duplicate shared models.
- Keep operation IDs stable: they become generated method names.
- Keep Go/Kotlin names, generator configuration, and templates in consumers.
- Keep internal service gRPC contracts beside the owning services.
- Never infer required fields or nullability solely from convenient client types.
- When changing an existing operation, inspect its gateway implementation and
  corresponding mobile SDK adapter; preserve released-client compatibility.
- Run `python3 scripts/validate.py` after specification changes.
- Do not consider syntax validation proof of runtime contract conformance.
- Do not publish a release until provider and affected consumer checks pass.
