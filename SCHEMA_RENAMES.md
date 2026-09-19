# Переименования схем OpenAPI

LinkIdentityRequest впоследствии удалён: Google/VK используют отдельные ручки и DTO.

`AccountDeletionStatusResponse` впоследствии удалён: POST и PATCH заявки используют
общий `AccountDeletionResponse` с датой и режимом удаления.

`AccountResponse` впоследствии удалён вместе с GET `/v1/auth/account`; карта ниже
сохраняет историю переименований.

Последующее уточнение: `RegistrationResponse` удалён; регистрация теперь возвращает
201 с общим `TokensResponse` ограниченной сессии. Строка ниже сохраняет историю предыдущего переименования.

2026-09-16. Только имена схем и ссылки: JSON, пути, методы и operationId сохранены.
Потребителям потребуется обновить импорты и конфигурацию генерации при переходе на новый контракт.

| Прежнее имя | Новое имя |
|---|---|
| `AuthSignUpRequest` | `CreateAccountRequest` |
| `AuthSignUpResponse` | `RegistrationResponse` |
| `AuthAccountResponse` | `AccountResponse` |
| `ProfileDeleteProfileRequest` | `RequestAccountDeletionRequest` |
| `ProfileDeleteProfileResponse` | `AccountDeletionResponse` |
| `ProfileProfileDeletionStatusResponse` | `AccountDeletionStatusResponse` |
| `AuthChangePasswordRequest` | `ChangePasswordRequest` |
| `AuthRequestPasswordResetRequest` | `RequestPasswordRecoveryRequest` |
| `AuthResetPasswordRequest` | `ConfirmPasswordRecoveryRequest` |
| `AuthVerifyEmailRequest` | `StartEmailVerificationRequest` |
| `AuthChangeEmailRequest` | `StartEmailChangeRequest` |
| `AuthEmailVerificationRequest` | `StartEmailBindingRequest` |
| `AuthEmailConfirmationRequest` | `ConfirmEmailRequest` |
| `AuthEmailConfirmationResponse` | `EmailConfirmationResponse` |
| `AuthIdentityResponse` | `Identity` |
| `AuthLinkIdentityRequest` | `LinkIdentityRequest` |
| `AuthGoogleIdentityRequest` | `LinkGoogleIdentityRequest` |
| `AuthVkIdentityRequest` | `LinkVkIdentityRequest` |
| `AuthSessionResponse` | `Session` |
| `AuthRefreshTokenRequest` | `RefreshTokensRequest` |
| `AuthTokensResponse` | `TokensResponse` |
| `AuthPasswordSignInRequest` | `CreatePasswordSessionRequest` |
| `AuthGoogleSignInRequest` | `CreateGoogleSessionRequest` |
| `AuthVkSignInRequest` | `CreateVkSessionRequest` |
| `AuthSignInRequest` | `CreateSessionRequest` |
| `AuthUsernameRequest` | `SetUsernameRequest` |
| `AuthCheckUsernameResponse` | `UsernameAvailabilityResponse` |
| `RecipeAddCollectionRequest` | `CreateCollectionRequest` |
| `RecipeAddCollectionResponse` | `CollectionCreatedResponse` |
| `RecipeCollectionInfoResponse` | `CollectionSummary` |
| `RecipeCollectionResponse` | `Collection` |
| `RecipeGetCollectionResponse` | `CollectionResponse` |
| `RecipeGetCollectionsResponse` | `CollectionsResponse` |
| `RecipeSaveCollectionToRecipeBookRequest` | `SaveCollectionRequest` |
| `RecipeUpdateCollectionRequest` | `UpdateCollectionRequest` |
| `RecipeContributorResponse` | `Contributor` |
| `RecipeCookingItem` | `CookingStep` |
| `RecipeCreateRecipeResponse` | `RecipeCreatedResponse` |
| `RecipeGenerateRecipePicturesUploadLinksRequest` | `CreateRecipePictureUploadLinksRequest` |
| `RecipeGetRecipeBookResponseResponse` | `RecipeBookResponse` |
| `RecipeGetRecipeResponseResponse` | `RecipeResponse` |
| `RecipeGetRecipesResponseResponse` | `RecipesResponse` |
| `RecipeIngredientItem` | `Ingredient` |
| `RecipeIngredientTranslationRequest` | `IngredientTranslation` |
| `RecipeMacronutrients` | `Macronutrients` |
| `RecipeRateRecipeRequest` | `RateRecipeRequest` |
| `RecipeRatingResponse` | `RecipeRating` |
| `RecipeRecipeInfoResponse` | `RecipeSummary` |
| `RecipeRecipeInputRequest` | `SaveRecipeRequest` |
| `RecipeRecipePictureUploadResponse` | `RecipePictureUpload` |
| `RecipeRecipePictures` | `RecipePictures` |
| `RecipeRecipeResponse` | `Recipe` |
| `RecipeRecipeStateResponse` | `RecipeState` |
| `RecipeSetRecipeCollectionsRequest` | `SetRecipeCollectionsRequest` |
| `RecipeSetRecipePicturesRequest` | `SetRecipePicturesRequest` |
| `RecipeSetRecipePicturesResponse` | `RecipePicturesResponse` |
| `RecipeTagResponse` | `RecipeTag` |
| `RecipeTranslateRecipeRequest` | `TranslateRecipeRequest` |
| `RecipeUpdateRecipeResponse` | `RecipeVersionResponse` |
| `EncryptionCreateEncryptedVaultRequest` | `CreateEncryptedVaultRequest` |
| `EncryptionDeleteEncryptedVaultRequest` | `ConfirmEncryptedVaultDeletionRequest` |
| `EncryptionGetEncryptedVaultKeyResponse` | `EncryptedKeyResponse` |
| `EncryptionRecipeKeyRequestResponse` | `RecipeKeyAccessRequest` |
| `EncryptionSetRecipeKeyRequest` | `SetRecipeKeyRequest` |
| `ShoppingListCreateSharedShoppingListRequest` | `CreateShoppingListRequest` |
| `ShoppingListCreateShoppingListResponse` | `ShoppingListCreatedResponse` |
| `ShoppingListGetShoppingListBodyResponse` | `ShoppingListResponse` |
| `ShoppingListGetShoppingListLinkResponse` | `ShoppingListLinkResponse` |
| `ShoppingListJoinShoppingListRequest` | `JoinShoppingListRequest` |
| `ShoppingListPurchase` | `Purchase` |
| `ShoppingListSetShoppingListNameRequest` | `SetShoppingListNameRequest` |
| `ShoppingListSetShoppingListRequest` | `UpdateShoppingListRequest` |
| `ShoppingListSetShoppingListResponse` | `ShoppingListVersionResponse` |
| `ShoppingListShoppingListInfoResponse` | `ShoppingListSummary` |
| `SubscriptionConfirmGoogleSubscriptionRequest` | `ConfirmGoogleSubscriptionRequest` |
| `SubscriptionSubscriptionResponse` | `Subscription` |
| `ProfileConfirmAvatarUploadingRequest` | `ConfirmAvatarUploadRequest` |
| `ProfileGenerateAvatarUploadLinkResponse` | `AvatarUploadResponse` |
| `ProfileInfo` | `ProfileSummary` |
| `ProfileMinInfo` | `ProfileSummaryFields` |
| `ProfileOAuthResponse` | `ProfileIdentities` |
| `ProfileProfileResponse` | `ProfileResponse` |
| `ProfileSetDescriptionRequest` | `SetProfileDescriptionRequest` |
| `ProfileSetDisplayNameRequest` | `SetDisplayNameRequest` |
| `TagTagResponse` | `Tag` |
| `TagTagWithGroupNameResponse` | `TagResponse` |
| `TagTagsAndGroupsResponse` | `TagsResponse` |
