# ChefBook Contracts Guide

This repository owns shared public API contracts, not server or client logic.

- Edit `openapi/src/chefbook.yaml` (entry point) and `openapi/src/**/*.yaml` (domain paths and schemas).
- `openapi/chefbook.yaml` is a generated delivery bundle: run `python3 scripts/bundle.py`; never edit it manually.
- Reference schemas directly in the file defining them, including discriminator mappings; do not introduce alias registries or duplicate shared models. Root `x-schema-sources` lists schema files or directories for bundling, not individual models. Schema directories are scanned recursively in sorted order.
- Declare each route only in its owning paths file. Root `x-path-sources` lists path files or directories; duplicate paths are rejected, even with different HTTP methods. Validate the generated bundle, not the source manifest, with external OpenAPI tools.
- Keep operation IDs stable: they become generated method names.
- Do not use top-level arrays in JSON request or response bodies. Put collections in required named properties of domain-owned object schemas and reference those schemas from paths; empty collections serialize as `[]` inside the object.
- Declare named `oneOf` union schemas before their referenced variants. Inline `oneOf` constraints on fields do not affect model order.
- Sort HTTP response codes in ascending order; put `default` after status codes. The YAML serializer preserves this order in the delivery bundle.
- Order path operations as GET, POST, PUT, PATCH, DELETE (then HEAD, OPTIONS, TRACE if present). Keep shared path metadata before operations.
- Indent YAML list items beneath their key by two spaces (including `required`, `oneOf`, `security` and `enum`). Use `scripts/bundle.py`'s `dump_yaml` when rewriting source YAML; the bundle uses the same format.
- Keep Go/Kotlin names, generator configuration, and templates in consumers.
- Keep internal service gRPC contracts beside the owning services.
- Never infer required fields or nullability solely from convenient client types.
- When changing an existing operation, inspect its gateway implementation and
  corresponding mobile SDK adapter; preserve released-client compatibility.
- Run `python3 scripts/validate.py` after specification changes.
- Do not consider syntax validation proof of runtime contract conformance.
- Do not publish a release until provider and affected consumer checks pass.
