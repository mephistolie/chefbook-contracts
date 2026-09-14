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

## Migration status

This is a preliminary contract, not a declaration that all runtime DTOs already
come from OpenAPI. The existing gateway and mobile adapters still require a
contract conformance review before switching to generated transport models.

The migration corrected known documentation errors: profile and avatar response
shapes; collection-list envelopes; shopping-list creation and naming; encryption
key objects; missing rating and collection assignment bodies; recipe search query
parameters; UUID path parameter types; and recipe book/favourites deletion paths.
These corrections describe existing handlers and do not deploy API changes.

Before declaring a stable contract, verify required/null semantics, error status
coverage, query serialization, and auth requirements against the gateway and
mobile consumers. In particular, the legacy gateway conflates current/public
profile routing, and mobile public-profile requests use a different path. Resolve
that behavior with a focused provider/consumer change, not by hiding the mismatch
in generated code.
