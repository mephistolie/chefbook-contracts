# ChefBook Contracts

Shared, versioned contracts between ChefBook clients and the public API gateway.
The HTTP API source is [openapi/src/chefbook.yaml](openapi/src/chefbook.yaml),
which references domain files. [openapi/chefbook.yaml](openapi/chefbook.yaml) is the
generated, self-contained delivery bundle; do not edit it manually.
Internal service gRPC contracts remain in their owning backend repositories.

## Layout

```text
openapi/src/chefbook.yaml    OpenAPI 3.0.3 entry point and component registry
openapi/src/domains/*.yaml   Domain routes and schemas
openapi/chefbook.yaml        Generated delivery bundle
scripts/bundle.py           Assemble or check the bundle
scripts/validate.py         Check freshness and validate with pinned OpenAPI Generator
```

The initial `0.1.0` contract was migrated from the gateway's Swagger 2.0 document
at commit `3a5a010`. It contains 83 operations. Model names no longer contain Go
package paths, and every operation has a stable `operationId`.

## Domain ownership

Each domain file contains `paths` and `schemas`: `auth`, `profile`, `recipes`,
`collections`, `tags`, `shopping-lists`, `encryption`, and `subscriptions`.
`common` owns shared error, message, and link responses. Collection models live
in `collections` even when their historical schema names start with `Recipe`.
Recipe-to-collection assignment operations remain in `recipes`.

To add an operation or model, define it in its domain and register its `$ref`
in `openapi/src/chefbook.yaml`. Inside domain files, reference models through
`../chefbook.yaml#/components/schemas/ModelName`. This keeps cross-domain and
recursive references stable without copying schemas. Registry path pointers
escape `/` as `~1`. The source entry point is also a standard multi-file OpenAPI
document usable by tools that resolve external references.

Run the bundler after editing and commit both source and bundle. Consumers keep
reading the existing `openapi/chefbook.yaml` path from a pinned Git revision;
their sync scripts, generators, and offline builds do not need changes. Splitting
the source does not itself require regenerating consumer code or changing pins.

## Validation

```sh
python3 -m venv .cache/venv
.cache/venv/bin/python -m pip install -r scripts/requirements.txt
.cache/venv/bin/python scripts/bundle.py
.cache/venv/bin/python scripts/validate.py
.cache/venv/bin/python -m unittest discover -s scripts/tests
```

`bundle.py --check` checks freshness offline without writing files. The bundler
rejects duplicate YAML keys, missing references, and references outside the source
directory. Validation checks both the multi-file source and the delivery bundle
after checking bundle freshness.

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

## HTTP response policy

- `201 Created` with `Location`: a new recipe, collection, or shared shopping list.
- `202 Accepted` with `Location`: profile deletion has been scheduled; the existing
  response retains `deletionTimestamp`, and `Location` points to its status endpoint.
- `200 OK`: reads, updates, commands, and deletes returning JSON. Existing message
  bodies are retained; `204` must not be introduced while consumers decode them.
- Sign-up and encrypted-vault creation remain `200`: they also successfully handle
  an existing resource, and current service responses do not distinguish creation
  from activation-mail resend or an already existing vault. OAuth and upload-link
  generation likewise do not unconditionally mean a new domain entity was created.
- `400`: invalid input; `401`: missing/invalid authentication; `403`: denied access;
  `404`: missing resource; `409`: conflicting state/version or occupied identifier;
  `500`: internal failure; `503`: unavailable upstream service.

The gateway normalizes legacy `400` errors with `not_found`, conflict, and access
reasons while preserving the JSON error identifier and message. It does not guess
from message text or turn arbitrary database failures into conflicts. Authentication
credential errors retain their existing handling to preserve refresh behavior.
