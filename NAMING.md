# Имена полей и URL

Согласовано 2026-09-16. Правила применены к DTO проекта OpenAPI `0.3.0-draft`.
Локальные gateway и клиент уже используют этот draft с обновлёнными DTO;
работающий dev не обновлялся. Ниже также сохранена история плана миграции.

## JSON

- Массивы не используются на верхнем уровне тела запроса или ответа. Коллекции
  помещаются в именованное обязательное поле объектного DTO: `{identities: []}`,
  `{sessions: []}`. Пустая коллекция — `[]`, а не null или отсутствие поля.
  Полное тело описывается в доменной схеме, путь содержит ссылку на неё.
- Объявленные свойства — `camelCase`: `userId`, `accessToken`, `displayName`.
  Произвольные ключи словарей (например, ID рецептов или поля формы S3) не переименовываются.
- Идентификатор самой сущности — `id`, включая краткий ответ создания и
  необязательный ID, предлагаемый клиентом при создании.
- Ссылка на другую сущность — имя сущности или роли с суффиксом `Id`:
  `userId`, `sessionId`, `recipeId`, `ownerId`, `groupId`.
- Аккаунт и профиль используют один идентификатор пользователя. В объекте
  аккаунта или профиля это `id`; в ответе с токенами — `userId` и `sessionId`.
- Участник коллекции представлен ссылкой на пользователя и ролью:
  `userId`, `role`. Отдельный идентификатор участия сейчас отсутствует.
- `googleId`, `vkId` — ссылки на внешние аккаунты. `subscriptionId` в запросе
  подтверждения Google — идентификатор внешнего продукта. Эти имена сохраняются.
- В ингредиентах, шагах приготовления и покупках `recipeId` — ссылка на рецепт,
  поэтому она не заменяется на `id`. Собственный `id` у этих объектов отдельный.

## Имена DTO

- Запрос — действие и сущность: `CreateAccountRequest`, `CreateSessionRequest`,
  `SetPasswordRequest`, `ConfirmEmailChangeRequest`.
- Ответ — содержимое: `ProfileResponse`, `TokensResponse`, `RecipeResponse`.
  Регистрация возвращает 201 с общим `TokensResponse`; отдельного `RegistrationResponse` нет.
- Вложенные модели — сущность: `Recipe`, `Collection`, `Ingredient`, `Purchase`.
  Краткие представления уточняются: `RecipeSummary`, `ProfileSummary`.
- Префикс домена механически не добавляется. Название сущности сохраняется там,
  где оно определяет смысл: `CreateCollectionRequest`, а не `CreateRequest`.
- Общая форма создания и обновления рецепта — `SaveRecipeRequest`; общая форма
  PUT/PATCH списка покупок — `UpdateShoppingListRequest`. Схемы не дублируются
  только ради названия метода. `IngredientTranslation` — вложенная часть запроса.
- `RecipeKeyAccessRequest` — представление заявки на доступ к ключу в списке,
  а не тело HTTP-запроса. `EncryptedKeyResponse` общий для ключа рецепта и vault.
- Имена уникальны в общем реестре компонентов. Директории не создают пространства
  имён. Суффиксы и имена схем не определяют JSON-поля или operationId.

Полная карта изменений — [SCHEMA_RENAMES.md](SCHEMA_RENAMES.md). Генераторы и
мапперы потребителей нужно адаптировать отдельно при обновлении закреплённого контракта.

## URL

Составные статические сегменты пути — `kebab-case`: `/shopping-lists`,
`/display-name`. JSON casing не определяет casing URL.

В существующем контракте query-параметры и имена плейсхолдеров преимущественно
в `snake_case`: `author_id`, `last_recipe_id`, `{shopping_list_id}`. У новых auth
маршрутов простые имена: `{id}`, `{provider}`, `{username}`. В этой итерации
параметры URL не менялись. Само имя плейсхолдера не передаётся в URL, но влияет
на сгенерированные аргументы и извлечение параметров в gateway; имя query-параметра
передаётся и является частью wire-контракта.

## Переименования DTO для миграции потребителей

Дополнительно семь прежних ответов-массивов получили объектную обёртку:

| Ручка | DTO | Поле |
|---|---|---|
| GET /v1/auth/account/identities | IdentitiesResponse | identities |
| GET /v1/auth/sessions | SessionsResponse | sessions |
| POST /v1/recipes/{recipe_id}/pictures | RecipePictureUploadLinksResponse | uploads |
| GET /v1/encryption/recipes/{recipe_id}/users | RecipeKeyAccessRequestsResponse | requests |
| GET /v1/shopping-lists | ShoppingListsResponse | shoppingLists |
| GET /v1/shopping-lists/{shopping_list_id}/users | ShoppingListUsersResponse | users |
| GET /v1/subscriptions | SubscriptionsResponse | subscriptions |

Элементы массивов не изменились. Перед обновлением consumer pins нужно изменить
сериализацию ответов gateway и чтение массивов в клиентских адаптерах. Прежние
клиенты, ожидающие массив без обёртки, с новым телом несовместимы. Backend и mobile
пока не изменены; это следующий шаг миграции проекта контракта.

| DTO | Было | Стало |
|---|---|---|
| CreateAccountRequest | userId | id |
| ProfileResponse | profileId | id |
| TokensResponse | profileId | userId |
| CreateCollectionRequest, CollectionCreatedResponse, Collection | collectionId | id |
| Contributor | contributorId | userId |
| RecipeCreatedResponse, SaveRecipeRequest | recipeId | id |
| CreateShoppingListRequest, ShoppingListCreatedResponse | shoppingListId | id |
| ShoppingListResponse, ShoppingListSummary | shoppingListId | id |
| Purchase | purchaseId | id |
| Tag, TagResponse | tagId | id |

Типы, nullable и обязательность сохранены. OperationId не менялись;
таблица выше использует новые имена схем из отдельной правки названий DTO.
Эти изменения несовместимы с прежними JSON-полями. Перед сменой consumer pins
нужно адаптировать Go DTO, Kotlin DTO/мапперы и совместимость поддерживаемых
клиентов. Некоторые клиентские DTO также используются для локального хранения:
нельзя автоматически менять их SerialName без проверки миграции сохранённых данных.
