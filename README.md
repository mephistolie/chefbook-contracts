# ChefBook Contracts

Shared, versioned contracts between ChefBook clients and the public API gateway.
The source of truth for the HTTP API is [openapi/chefbook.yaml](openapi/chefbook.yaml).
Internal service gRPC contracts remain in their owning backend repositories.

## Layout

```text
openapi/chefbook.yaml   Public HTTP contract (OpenAPI 3.0.3)
scripts/validate.py     Validate the contract with a pinned OpenAPI Generator
```

The initial `0.1.0` contract was migrated from the gateway's Swagger 2.0 document
at commit `3a5a010`. It contains 83 operations. Model names no longer contain Go
package paths, and every operation has a stable `operationId`.

## Validation

```sh
python3 scripts/validate.py
```

Requires Python 3 and Java 17+. The first run downloads OpenAPI Generator 7.14.0
from Maven Central into the ignored `.cache/` directory and verifies SHA-256.
Subsequent runs use the verified cached jar. For offline use, set
`OPENAPI_GENERATOR_JAR` to an already downloaded jar of the same version.

## Ownership and delivery

Edit the source specification here. Consumer snapshots and generated code are
not independently maintained contracts. Go and Kotlin generator versions,
templates, adapters, and build settings belong to their respective consumers.

Each consumer must pin a full contracts Git commit, vendor the specification,
and record its SHA-256. This allows a standalone consumer checkout to build
without the workspace, a running backend, or a floating `main` dependency.
Updating the pin and regenerating code is an explicit, reviewable change.

The workspace submodule pin records the contracts revision used for joint
development; it does not silently change individual consumer pins. Local
experiments may explicitly use the adjacent checkout. Reproducible builds must
use the pinned snapshot.

Recommended change sequence:

1. Change the contract, preserve existing `operationId`s, and validate it.
2. Implement and verify the matching gateway behavior.
3. Update the consumer pin, regenerate, and compile the affected SDK modules.
4. Record compatible submodule revisions in the workspace.

Contract release versions describe the document; `/v1` describes the HTTP API
compatibility boundary. Additive changes must preserve released mobile clients.
Do not remove or make fields mandatory merely because current generated code
would be easier to use that way.

## Consumer integration

The gateway generates Go types, a Gin server interface, and route registration
with oapi-codegen. Its adapters keep service calls and domain mapping in the
existing handlers. Swagger UI renders the vendored OpenAPI file; Go annotations
are no longer a second contract source.

The mobile SDK generates Kotlin Multiplatform API calls and transport models
with OpenAPI Generator. Existing SDK adapters map request models explicitly and
retain domain/persistence response models. All public API requests use generated
methods; direct file transfers still use their separate binary transport.

The `0.2.0` migration reconciles JSON field names, nullable DTO fields, request
bodies (including DELETE), repeated query values, and current/public profile
routing. Consumer regression tests cover Go DTO/schema parity, route protection,
profile targets, Kotlin serialization, and preservation of the existing token
refresh plugin. These checks do not replace testing a deployed service end to end.

The gateway consumer documents the discovered mismatches and their fixes in
`contracts/MIGRATION.md`. Optional legacy properties that also serve local client
storage are retained in client models; they are not promised by the HTTP contract.
