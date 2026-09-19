# ChefBook Contracts

The 0.5.0-draft contract introduces typed authentication steps and /completion.
Auth, gateway and mobile adapters are updated locally; gateway/mobile pin this same
contract. Dev still runs 0.4.0-draft. See AUTH_IMPLEMENTATION_STATUS.md for checks
and platform limitations, and AUTH_API_MIGRATION.md for the deployment boundary.

Shared, versioned contracts between ChefBook clients and the public API gateway.
The HTTP API source is [openapi/src/chefbook.yaml](openapi/src/chefbook.yaml),
which references domain files. [openapi/chefbook.yaml](openapi/chefbook.yaml) is the
generated, self-contained delivery bundle; do not edit it manually.
Internal service gRPC contracts remain in their owning backend repositories.

[NAMING.md](NAMING.md) defines JSON identifier naming and records the current
URL casing conventions and pending consumer field migrations.

The agreed auth redesign was consolidated on **2026-09-17**:

- [AUTH_API_DRAFT.md](AUTH_API_DRAFT.md): all 38 target routes under `/v1`, common
  authentication/step flows, registration and session creation.
- [AUTH_OPERATION_NAMES.md](AUTH_OPERATION_NAMES.md): agreed operation IDs and
  generated method names for those 38 routes, including the new step endpoints.
- [AUTH_DATABASE_PLAN.md](AUTH_DATABASE_PLAN.md): agreed **initial database schema**;
  implement from an empty schema, without incremental conversion of legacy tables.
- [AUTH_MFA_DESIGN.md](AUTH_MFA_DESIGN.md): TOTP, passkeys, backup codes and reuse of
  recent reauthentication within the same session.
- [AUTH_API_MIGRATION.md](AUTH_API_MIGRATION.md): implementation order and remaining
  protocol details. Its filename is historical; it does not request SQL data migrations.
- [FIREBASE_MIGRATION.md](FIREBASE_MIGRATION.md): separate one-time legacy import via
  outbox, with progress and idempotency owned by the import executor.
- [AUTH_ABUSE_PROTECTION.md](AUTH_ABUSE_PROTECTION.md): deferred microservice protection
  work. `abuse_counters` is not part of the agreed initial schema.

The `0.5.0-draft` source and generated bundle implement the agreed 38-operation
multi-step authentication contract. Backend/mobile are implemented locally;
see `AUTH_IMPLEMENTATION_STATUS.md` for validation and rollout limitations.
`AUTH_OPENAPI_SNAPSHOT.md` is historical, not the current machine-readable contract.
The previous 0.4.0-draft auth API is deployed in dev; 0.5.0-draft is not deployed.
A tagged contract release has not been published.
Deployment revisions and verification are recorded in the infrastructure handoff.

## Layout

```text
openapi/src/chefbook.yaml    Bundle manifest with metadata and source lists
openapi/src/<domain>/paths.yaml     Domain routes
openapi/src/<domain>/schemas.yaml   Domain DTOs
openapi/src/auth/paths/*.yaml       Auth routes by feature
openapi/src/auth/schemas/*.yaml     Auth DTOs by feature
openapi/src/auth/schemas/common.yaml Shared auth reauthentication models
openapi/chefbook.yaml        Generated delivery bundle
scripts/bundle.py           Assemble or check the bundle
scripts/validate.py         Check freshness and validate with pinned OpenAPI Generator
```

The initial `0.1.0` contract was migrated from the gateway's Swagger 2.0 document
at commit `3a5a010`. It contains 83 operations. Model names no longer contain Go
package paths, and every operation has a stable `operationId`.

## Domain ownership

Each domain directory separates routes from schemas: `auth`, `profile`, `recipes`,
`collections`, `tags`, `shopping-lists`, `encryption`, and `subscriptions`.
`common` owns shared responses. Collection models live in `collections`.
Reusable HTTP errors are declared in the entry point's `components.responses` and
referenced by auth operations. Endpoint-specific error examples remain beside the
operation; response headers retain the same no-store and authentication requirements.
Recipe-to-collection assignment operations remain in `recipes`. Auth is split
further into `account`, `password`, `email`, `identities`, `sessions`, and
`usernames`. Account deletion DTOs live in auth and use account terminology.
Schema names describe operations or data without mechanical domain prefixes;
[SCHEMA_RENAMES.md](SCHEMA_RENAMES.md) maps the old names to the new ones.

Declare each route only in its owning `paths.yaml` or `paths/*.yaml` file.
The root `x-path-sources` lists path files or directories; it does not repeat routes.
The bundler rejects duplicate paths, including definitions with disjoint methods.
Source list order determines endpoint order in the delivery bundle and Scalar.
Auth files are listed explicitly in user-flow order: authentication, sessions,
username, password, email, OAuth, identities, TOTP, passkeys, backup codes, account
deletion. Directory entries use alphabetical file order. Within each path,
methods remain GET, POST, PUT, PATCH, DELETE.
Reference each model
in the file that defines it, without an intermediate registry. Simple domains
keep their definitions in `schemas.yaml`; auth uses `schemas/*.yaml`.
For example, an auth route references `../schemas/sessions.yaml#/schemas/TokensResponse`.
Shared reauthentication models live in `auth/schemas/common.yaml`. Cross-domain
references and discriminator mappings also point directly to definition files.

The root `x-schema-sources` extension lists schema files or directories. For auth,
it lists `./auth/schemas/`: the bundler discovers `.yaml` and `.yml` files
recursively in sorted order and includes all their models, even those not yet used
by a route. No separate list of auth models or files needs maintenance.
Both source-list extensions are removed from the delivery bundle, which contains
standard `paths` and `components.schemas` references. The source manifest is not a
standalone OpenAPI document: pass `openapi/chefbook.yaml` to validators, generators
and documentation tools. `scripts/validate.py` checks source resolution and bundle
freshness before validating the generated specification. Duplicate schema names,
empty schema directories and references outside the source directory are rejected.
Recursive model properties remain references rather than being expanded indefinitely.
Legacy alias-based sources remain supported by the bundler, but new source files
should reference definitions directly.

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
directory. Validation resolves the multi-file source and checks the delivery bundle
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

## Request examples and display names

Named `requestBody.content.application/json.examples` in the owning paths files
are the single source of request samples. Include a summary, scenario context when
needed, and a complete `value`. The bundler appends all examples as separate JSON
blocks to the operation description, so Scalar displays every scenario together
while retaining its schema and native example picker. Do not copy these blocks
into source descriptions or add them manually to the generated delivery bundle.

`scripts/validate.py` checks every sample with an OpenAPI 3.0 write validator,
including references, oneOf, nullable fields and formats. Contract tests also
check auth union coverage and reject mixed provider credentials. Passing schema
validation does not make demonstration tokens or WebAuthn bytes real credentials;
provider setup, issued tokens and server state still apply.

Tag identifiers remain stable for consumers; `x-displayName` supplies singular,
human-readable headings such as `Authentication`, `Recipe` and `Shopping list`.

## Consumer integration

The gateway generates Go types, a Gin server interface, and route registration
with oapi-codegen. Its adapters keep service calls and domain mapping in the
existing handlers. Scalar renders the vendored OpenAPI file; Go annotations
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
  response retains `deletionTimestamp`; there is no separate auth deletion GET.
- `200 OK`: useful response bodies. Auth mutations with no result use `204 No Content`;
  meaningless message bodies have been removed and affected consumers updated.
- The previous machine-readable snapshot returns a restricted session from
  registration. The current contract instead completes `signUp` in
  `/v1/authentications`, creates the account after verification, and exchanges an
  authorization token through `POST /v1/sessions`. The old behavior is historical;
  see [AUTH_API_DRAFT.md](AUTH_API_DRAFT.md) and the implementation plan above.
- Encrypted-vault creation remains `200` because it also handles an existing vault.
  OAuth and upload-link
  generation likewise do not unconditionally mean a new domain entity was created.
- `400`: invalid input; `401`: missing/invalid authentication; `403`: denied access;
  `404`: missing resource; `409`: conflicting state/version or occupied identifier;
  `500`: internal failure; `503`: unavailable upstream service.

The gateway normalizes legacy `400` errors with `not_found`, conflict, and access
reasons while preserving the JSON error identifier and message. It does not guess
from message text or turn arbitrary database failures into conflicts. Authentication
credential errors retain their existing handling to preserve refresh behavior.
