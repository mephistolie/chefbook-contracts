# Auth operation names

Updated 2026-09-19. Target contract 0.5.0-draft; step changes are not yet deployed.
These operation IDs define generated Kotlin methods and Go router methods (with an
initial capital in Go). The step redesign changes paths and payloads. Request/confirm describes
account changes; start/complete describes authentication and individual steps.
An email confirmation advances one step and may not complete the email change.

| Endpoint | operationId | Purpose |
|---|---|---|
| `POST /v1/account/deletion` | `requestAccountDeletion` | Request account deletion |
| `PATCH /v1/account/deletion` | `updateAccountDeletion` | Update account deletion preferences |
| `DELETE /v1/account/deletion` | `cancelAccountDeletion` | Cancel account deletion |
| `POST /v1/authentications` | `startAuthentication` | Start authentication |
| `GET /v1/authentications/{id}` | `getAuthentication` | Get authentication state |
| `POST /v1/authentications/{id}/steps` | `startAuthenticationStep` | Start authentication step |
| `GET /v1/authentications/{id}/steps/{stepId}` | `getAuthenticationStep` | Get authentication step state |
| `POST /v1/authentications/{id}/steps/{stepId}/completion` | `completeAuthenticationStep` | Complete authentication step |
| `GET /v1/account/backup-codes` | `getBackupCodesStatus` | Get backup codes status |
| `POST /v1/account/backup-codes` | `generateBackupCodes` | Generate backup codes |
| `POST /v1/account/email/verification` | `requestEmailChange` | Request an email change |
| `POST /v1/account/email/verification/confirmation` | `confirmEmailChange` | Confirm an email change step |
| `GET /v1/account/identities` | `getIdentities` | Get linked identities |
| `POST /v1/account/identities/google` | `linkGoogleIdentity` | Link a Google identity |
| `DELETE /v1/account/identities/google` | `unlinkGoogleIdentity` | Unlink a Google identity |
| `POST /v1/account/identities/vk` | `linkVkIdentity` | Link a VK identity |
| `DELETE /v1/account/identities/vk` | `unlinkVkIdentity` | Unlink a VK identity |
| `POST /v1/oauth/google` | `createGoogleAuthorizationUrl` | Create a Google authorization URL |
| `POST /v1/oauth/vk` | `createVkAuthorizationUrl` | Create a VK authorization URL |
| `GET /v1/account/passkeys` | `getPasskeys` | Get registered passkeys |
| `POST /v1/account/passkeys` | `confirmPasskeyRegistration` | Confirm passkey registration |
| `POST /v1/account/passkeys/requests` | `requestPasskeyRegistration` | Request passkey registration |
| `PATCH /v1/account/passkeys/{id}` | `renamePasskey` | Rename a passkey |
| `DELETE /v1/account/passkeys/{id}` | `deletePasskey` | Delete a passkey |
| `PUT /v1/account/password` | `setPassword` | Set password |
| `POST /v1/account/password/reset` | `requestPasswordReset` | Request a password reset |
| `POST /v1/account/password/reset/confirmation` | `confirmPasswordReset` | Confirm a password reset |
| `GET /v1/sessions` | `getSessions` | Get active sessions |
| `POST /v1/sessions` | `createSession` | Create a session |
| `DELETE /v1/sessions` | `revokeAllSessions` | Revoke all sessions |
| `DELETE /v1/sessions/{id}` | `revokeSession` | Revoke session |
| `POST /v1/sessions/{id}/tokens` | `refreshSessionTokens` | Refresh session tokens |
| `GET /v1/account/totp` | `getTotpStatus` | Get TOTP status |
| `POST /v1/account/totp` | `requestTotpActivation` | Request TOTP activation |
| `DELETE /v1/account/totp` | `deleteTotp` | Delete TOTP configuration |
| `POST /v1/account/totp/confirmation` | `confirmTotpActivation` | Confirm TOTP activation |
| `PUT /v1/account/username` | `setUsername` | Set username |
| `GET /v1/usernames/{username}/availability` | `checkUsernameAvailability` | Check username availability |

## Request and response model names

Action-specific models use the agreed operation vocabulary. Shared resource models
(`AuthenticationResponse`, `AuthenticationStep`, `TokensResponse`, `Session`,
`Passkey`, `AccountDeletionResponse`, collection responses) retain content-based names.
Google and VK share the same authorization URL request and response schemas.

| Previous schema | Current schema |
| --- | --- |
| `CreateAuthenticationRequest` | `StartAuthenticationRequest` |
| `StartAuthenticationChallengeRequest` | `StartAuthenticationStepRequest` |
| `CompleteAuthenticationChallengeRequest` | `CompleteAuthenticationStepRequest` |
| `CompleteAuthenticationChallengeResponse` | `CompleteAuthenticationStepResponse` |
| `AuthenticationChallenge` | `AuthenticationStep` |
| `RefreshTokensRequest` | `RefreshSessionTokensRequest` |
| `ChangePasswordRequest` | `SetPasswordRequest` |
| `StartEmailChangeRequest` | `RequestEmailChangeRequest` |
| `ChangeEmailResponse` | `ConfirmEmailChangeResponse` |
| `CreateOAuthRequest` | `CreateAuthorizationUrlRequest` |
| `OAuthRequestResponse` | `CreateAuthorizationUrlResponse` |
| `ConfirmTotpRequest` | `ConfirmTotpActivationRequest` |
| `CreatePasskeyRequest` | `ConfirmPasskeyRegistrationRequest` |
| `TotpResponse` | `TotpStatusResponse` |
| `TotpActivationResponse` | `RequestTotpActivationResponse` |
| `PasskeyRegistrationResponse` | `RequestPasskeyRegistrationResponse` |

## Typed steps — 2026-09-19

The three challenge operations are replaced by start/get/completeAuthenticationStep.
StartAuthenticationRequest contains purpose only. Step requests and responses use
flat oneOf variants discriminated by type. CompleteAuthenticationStepResponse contains
the updated step and authentication. Challenge DTOs are superseded, not aliases in
the new contract. Completion variants carry their fields directly alongside type.
