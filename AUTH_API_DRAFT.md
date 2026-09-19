# Согласованный API аккаунтов и аутентификации

Обновлено 2026-09-19. Целевой OpenAPI `0.5.0-draft`: 38 операций,
типизированные шаги и POST /steps/{stepId}/completion. Это несовместимое изменение
контракта, реализованное локально в auth/gateway/mobile, но НЕ развёрнутое в dev.
Consumer snapshots синхронизированы с 0.5.0-draft; dev остаётся на 0.4.0-draft.
Результаты проверок и ограничения платформ: [AUTH_IMPLEMENTATION_STATUS.md](AUTH_IMPLEMENTATION_STATUS.md).
[AUTH_OPENAPI_SNAPSHOT.md](AUTH_OPENAPI_SNAPSHOT.md) — историческая версия.
Согласованные имена методов: [AUTH_OPERATION_NAMES.md](AUTH_OPERATION_NAMES.md).

Схема начальной БД: [AUTH_DATABASE_PLAN.md](AUTH_DATABASE_PLAN.md).
Факторы и доверие: [AUTH_MFA_DESIGN.md](AUTH_MFA_DESIGN.md).
Этапы реализации: [AUTH_API_MIGRATION.md](AUTH_API_MIGRATION.md).

## Маршруты

Общий префикс `/v1`, без `/auth`. Внутренний микросервис сохраняет имя auth.
Профиль и остальные домены не переносятся в auth. JSON camelCase, URL kebab-case.
`{id}` — ID ресурса маршрута; во вложенном маршруте второй ID — `{stepId}`.
Коллекции всегда в объекте, без массивов верхнего уровня.

Коды ниже — успешные ответы; полный набор ошибок определяется инвариантами ниже
и уточняется при переносе DTO в YAML, без механического копирования 401/404 везде.

| Метод | Путь | Успех | Назначение |
|---|---|---|---|
| `POST` | `/authentications` | 201 | Начать signIn/signUp или реаутентификацию; свежая достаточная проверка той же сессии может сразу завершить процесс |
| `GET` | `/authentications/{id}` | 200 | Состояние, созданные шаги и следующие альтернативы |
| `POST` | `/authentications/{id}/steps` | 201 | Начать предложенный шаг: сбор данных, настройку credential или проверку |
| `GET` | `/authentications/{id}/steps/{stepId}` | 200 | Типизированное состояние шага без повторной выдачи секретов |
| `POST` | `/authentications/{id}/steps/{stepId}/completion` | 200 | Завершить шаг типизированными данными; состояние шага и всего процесса |
| `GET` | `/sessions` | 200 | Список своих сессий без секретных токенов |
| `POST` | `/sessions` | 201 | Обменять разрешение завершённого signIn/signUp на сессию и токены |
| `DELETE` | `/sessions` | 204 | Завершить все свои сессии, включая текущую |
| `DELETE` | `/sessions/{id}` | 204 | Завершить конкретную свою сессию |
| `POST` | `/sessions/{id}/tokens` | 200 | Обновить пару токенов refresh-токеном этой сессии |
| `PUT` | `/account/password` | 204 | Установить первый пароль или сменить существующий |
| `POST` | `/account/password/reset` | 202 | Запросить письмо сброса, не раскрывая наличие аккаунта |
| `POST` | `/account/password/reset/confirmation` | 204 | Подтвердить одноразовый токен и установить пароль |
| `PUT` | `/account/username` | 204 | Установить/изменить username |
| `GET` | `/usernames/{username}/availability` | 200 | Проверить доступность публичного username; требуется Bearer-сессия |
| `POST` | `/account/email/verification` | 202 | Начать смену email, подтвердить сначала старый адрес |
| `POST` | `/account/email/verification/confirmation` | 200 | Токеном подтвердить очередной этап: старый, затем новый адрес |
| `POST` | `/account/deletion` | 202 | Запланировать удаление, вернуть дату и deleteSharedData |
| `PATCH` | `/account/deletion` | 200 | Изменить только deleteSharedData без изменения срока |
| `DELETE` | `/account/deletion` | 204 | Отменить удаление, в том числе если заявки уже нет |
| `GET` | `/account/identities` | 200 | Привязанные Google/VK-аккаунты |
| `POST` | `/account/identities/google` | 201/204 | Привязать доказанную Google identity; новая связь / уже существующая та же связь |
| `DELETE` | `/account/identities/google` | 204 | Отвязать Google, сохранив другой способ входа |
| `POST` | `/account/identities/vk` | 201/204 | Привязать доказанную VK identity |
| `DELETE` | `/account/identities/vk` | 204 | Отвязать VK, сохранив другой способ входа |
| `POST` | `/oauth/google` | 201 | Подготовить защищённый OAuth-запрос для привязки Google |
| `POST` | `/oauth/vk` | 201 | Подготовить защищённый OAuth-запрос для привязки VK |
| `GET` | `/account/totp` | 200 | enabled и activationTimestamp, без секрета |
| `POST` | `/account/totp` | 201 | Подготовить secret/otpauthUri и срок подключения после реаутентификации |
| `POST` | `/account/totp/confirmation` | 200 | Проверить первый код; активировать TOTP и выдать backupCodes |
| `DELETE` | `/account/totp` | 204 | Отключить TOTP после достаточного подтверждения |
| `GET` | `/account/passkeys` | 200 | Список ключей с именами и метаданными |
| `POST` | `/account/passkeys/requests` | 201 | Создать запрос регистрации, вернуть requestId и WebAuthn-параметры |
| `POST` | `/account/passkeys` | 201 | Проверить ответ устройства и сохранить ключ |
| `PATCH` | `/account/passkeys/{id}` | 200 | Переименовать ключ; обычная сессия, без реаутентификации |
| `DELETE` | `/account/passkeys/{id}` | 204 | Удалить ключ с подтверждением личности, не последний способ входа |
| `GET` | `/account/backup-codes` | 200 | remainingCount и generationTimestamp; если строк нет, дата null |
| `POST` | `/account/backup-codes` | 201 | Перевыпустить весь набор с реаутентификацией, показать plaintext один раз |

Нет POST /account, GET /account, GET /account/deletion, GET одной sessions/{id},
/session, /sessions/confirmation, отдельных /reauthentications и публичной Firebase-ручки.
Не добавляем /accounts/{id}: настройки по текущему account. Массовое удаление сессий
без ?ids; refresh в теле, его принадлежность path ID обязательна. У DELETE нет тела.

## Типизированный purpose и доказательства

Начало процесса принимает только purpose:

```json
{"purpose":{"type":"signUp"}}
```

Назначения: signIn, signUp, passwordChange, emailChange, accountDeletion,
totpEnrollment, totpRemoval, passkeyEnrollment, passkeyRemoval,
backupCodesRotation, identityLink, identityUnlink. Purpose — oneOf по type;
не передаём здесь registration, login, email, password или client/device.

StartAuthenticationStepRequest, AuthenticationStep и CompleteAuthenticationStepRequest
— именованные oneOf по type. Все поля варианта плоские, без data/registration/authentication
обёрток. Ответ завершения содержит step и authentication, поскольку это два разных
обновлённых ресурса, а не взаимоисключающие варианты входных данных.

| type | Данные завершения |
|---|---|
| registration | email; username запрещён |
| passwordSetup | новый password, только после подтверждения email в signUp |
| passwordVerification | login + password для signIn; только password для реаутентификации |
| emailVerification | шестизначный code |
| totpVerification | шестизначный code |
| backupCodeVerification | code |
| googleVerification | idToken либо code/state, строго по режиму созданного шага |
| vkVerification | code/state |
| passkeyVerification | credential с assertion |

Пример: `{"type":"registration","email":"alex.smith@example.com"}`.
Пароль позже: `{"type":"passwordSetup","password":"..."}`.
Код: `{"type":"emailVerification","code":"042731"}`.

next.options — список альтернатив следующего действия, а не все обязательные проверки.
authentication.steps — созданные шаги в порядке создания, с безопасным представлением
для GET. OAuth URL/nonce возвращаются только при создании шага. Данные регистрации,
пароль, коды и grants не повторяются при чтении. Неподдержанный клиентом тип требует
обновления приложения; клиент не пропускает его и не угадывает серверную политику.

Сервер определяет порядок и проверяет предпосылки повторно при создании и завершении
шага. Смена последовательности известных типов не требует изменения клиента;
новому типу может потребоваться новый UI. Повтор одного фактора не заменяет другой.
registration/passwordSetup не считаются доказательством существующей личности.
Создание credential не используется как реаутентификация существующего аккаунта.

Google authorizationCode по умолчанию требует allowlisted redirectUri. Native idToken
требует nonce-capable SDK и не допускает redirectUri. VK пока только code/state.
Регистрация passkey использует зарезервированный UUID будущего аккаунта как user.id,
не создавая аккаунт до завершения. Настройка passkey на существующем аккаунте остаётся
в защищённых /account/passkeys/requests и /account/passkeys.

## Доступ к процессу

- POST /authentications для signIn/signUp не требует существующей сессии.
- Для остальных purpose требуется действующий access bearer; аккаунт берём из него,
  не из переданного accountId. Процесс навсегда привязан к исходной session_id.
- Последующие запросы требуют flowToken. Транспорт: отдельный заголовок Flow-Token
  (деталь фиксации контракта; opaque secret, в OpenAPI apiKey/in:header).
  При реаутентификации дополнительно исходный access bearer, AND, а не OR.
- GET не отправляет письма, не погашает токены и не продлевает доверие. ID процесса
  или step сам по себе не разрешение. Проверять принадлежность вложенного ID.
- Итоговый confirmationToken — отдельный секрет, не access token. Для создания
  сессии передаётся как authenticationToken в POST /sessions; для действий —
  Reauthentication-Token вместе с access bearer. Это наши заголовки, не OAuth-стандарт.
- Разрешение одноразовое, связано с purpose/account/session, но не конкретным
  passkey/provider/email. Права на выбранный объект проверяет операция.
- GET состояния не выдаёт заново plaintext итогового токена. Повтор последней
  успешной попытки не создаёт новое разрешение/аккаунт. При потере ответа начать
  новый процесс; при свежей реаутентификации повторных действий пользователя может
  не потребоваться. Политику восстановления ответа по idempotency key пока не добавляем.

## Пример многошагового входа

1. POST /authentications с purpose=signIn → 201, id, flowToken, expiry,
   pending, steps=[] и next.options. До первого доказательства нет персональных факторов.
2. POST /authentications/{id}/steps с type=passwordVerification → 201 и Location шага.
3. POST .../steps/{stepId}/completion с type, login и password → 200, step + authentication.
   При необходимом втором факторе next.options предлагает totpVerification/backupCodeVerification.
4. Создать выбранный шаг и завершить его кодом через /completion.
5. Финальное успешное завершение → completed, confirmationToken и expiry.
6. POST /sessions с authenticationToken → 201 TokensResponse.

Число проверок не фиксировано. 200 означает завершение текущего шага, а не всей цепочки.
Неверное доказательство — 4xx, completion не возникает; шаг остаётся pending до
исчерпания лимита. Expired/cancelled/completed шаги нельзя завершить повторно: 409.
Повтор финального запроса не создаёт второй аккаунт, credential или grant.
Потерянный grant не выдаётся через GET; клиент начинает новый вход.
Completion — переход состояния, отдельная таблица или ID для него не нужны.

Создание emailVerification повторно разрешается политикой для resend: предыдущий
pending email-шаг этого процесса отменяется. Счётчики всего процесса и TTL не сбрасываются.
Конкурирующие варианты одного этапа нельзя использовать для обхода переходов;
при принятии одного устаревшие pending-альтернативы отменяются атомарно.
Новый процесс нужен для смены уже принятого регистрационного email.

Provider setup для входа/реаутентификации относится к шагу googleVerification/vkVerification.
Отдельные /oauth/google|vk сохраняются для привязки identity существующего аккаунта.

## Регистрация и защита от enumeration

- Client-first: регистрация нужна только для облачных функций.
- POST /authentications с signUp создаёт только процесс; первый вариант — registration.
- Завершение registration сохраняет только email в registrations. Username задаётся
  после создания аккаунта через защищённый PUT /account/username; availability остаётся
  Bearer-only. Пароль/provider не принимаются вместе с email.
- Затем одинаково предлагается emailVerification для существующего и свободного адреса.
  Создание шага отправляет код в обоих случаях. HTTP-статусы, форма ответа, next.options,
  лимиты/resend и наблюдаемое время не должны раскрывать существование аккаунта.
  Отправка асинхронная; 201 означает постановку письма, не доставку.
- Код можно прочитать на другом устройстве, но завершить шаг нужно с flowToken исходного
  процесса. Нет аккаунта/сессии или emailVerificationRequired restriction до финализации.
- Только после правильного кода можно раскрыть владельцу почты, что аккаунт существует:
  409 account_exists, signUp завершается failed без grant. Клиент предлагает отдельный
  signIn/reset. Это не вход, не автоматическое восстановление и не обход MFA.
- Для свободного подтверждённого адреса сервер предлагает только passwordSetup.
  Нельзя начать или завершить его до доказательства почты. Хеширование пароля
  выполняется после проверки доступа к процессу и всех предпосылок.
- Passkey и внешние identity Google/VK можно подключить после создания аккаунта.
  Их проверочные шаги используются для входа/реаутентификации, не для signUp.
- Финальное действие атомарно перепроверяет уникальность email, генерирует ID аккаунта,
  создаёт аккаунт с паролем, завершает процесс и выдаёт разрешение на сессию.
  При гонке регистрации — 409 после подтверждения email; чужие credentials не изменяются.
- Независимые процессы одной почты не перезаписывают данные друг друга. Успешная
  регистрация отменяет лишние pending-шаги своего процесса и удаляет временные секреты.
- Смена адреса требует новой регистрации/проверки. Подтверждение нельзя переносить
  между процессами. Сессия создаётся отдельно через POST /sessions.
- Ограничения расходов на письма/CPU остаются отдельной задачей: порядок шагов не
  является защитой от DDoS или обещанием ограничения облачного счёта.

## Сессии и ограничения

TokensResponse сохраняет userId, sessionId, accessToken, refreshToken,
expirationTimestamp, restrictions. restrictions — массив типизированных объектов,
не premium/capabilities. Pending deletion содержит deletionTimestamp и deleteSharedData;
вход/refresh учитывают состояние аккаунта на сервере. Пользователь отдельно разрешил claim sessionId для привязки к сессии;
новых claims прав/capabilities не вводим.

После регистрации и входа сессию создаём одной ручкой; confirmationToken signUp и
signIn допускает только это действие. Refresh принадлежит ID пути, ротация атомарна.
GET sessions возвращает {sessions:[...]}, метаданные client(name/platform/type),
ip, lastRefreshTimestamp, location; current удалён. Client не присылается при входе.

DELETE sessions/{id}: действующий access token для управления своими сессиями,
либо refresh bearer только указанной собственной сессии для выхода после expiry
access. Недействительный/уже отозванный refresh не раскрывает чужую сессию и не даёт
её удалить; повтор logout может быть 204 без эффекта. Отзыв проверяется сервером,
а не только по сроку JWT. DELETE sessions отзывает все без фильтра ID.

## Изменения аккаунта

- password: PUT с newPassword и разрешением passwordChange вместо oldPassword.
  Первый пароль разрешён без повторной проверки только при отсутствии password_hash
  и полноценной сессии. Это согласованное исключение, не разрешение менять существующий
  пароль по одной сессии. Семантически повтор установки того же состояния не должен
  заново менять дату/побочные эффекты; использованный grant не становится reusable.
- reset: email → нейтральный 202, затем token + новый пароль. Reset не отключает TOTP
  и не выдаёт обходящую MFA сессию. Изменение credentials инвалидирует старое доверие.
- email: только change, поле email вместо newEmail; регистрационный verify перенесён
  в шагах регистрации. Начало с bearer + emailChange grant; подтверждение токенами старого,
  затем нового адреса. Публичное подтверждение смены через токен не требует исходной
  регистрационной сессии. Статусы pendingNewEmail/changed; отдельной сессии не выдаёт.
- deletion: POST с accountDeletion grant, deleteSharedData; PATCH только флага с bearer,
  без повторных credentials и без смены срока; DELETE 204. GET отсутствует, нужный статус
  приходит в restrictions и ответах POST/PATCH. Закладка ссылается на оригинал.
- identities: привязка требует и identityLink grant, и независимое владение новой
  identity. Отвязка требует identityUnlink grant. Провайдеры отдельными маршрутами.
  Не удалять последний способ входа. Список {identities:[...]} с oneOf по provider.

## HTTP и хранение секретов

- 201 — создан процесс/step/session/credential; Location указывает осмысленный
  URI созданного ресурса, но не требует добавлять GET туда, где его не согласовали.
- 200 — полезное тело; 204 — без бессмысленного message; 202 — принята асинхронная
  отправка/заявка удаления. Ошибки внешней отправки не обещают фактическую доставку.
- 401 для отсутствующей/недействительной требуемой аутентификации; Bearer ответы
  используют общий Unauthorized с WWW-Authenticate. 403 — недостаточные права/grant,
  404 — недоступный ресурс без раскрытия чужих данных, 409 — конфликт состояния,
  429 + Retry-After — лимит, 503 — недоступность зависимости.
- Refresh: invalid_refresh_token — 400; malformed request не отзывает сессию клиента.
  До определения владельца не раскрывать block/deletion/factor settings.
- ErrorResponse с error/message пока сохраняем; переход на RFC 9457 отложен.
- Токены, коды подключения, challenge-контекст и защищённые ответы: no-store,
  Pragma: no-cache; секреты исключены из логов и URL. GET не возвращает credentials.
- Пока это собственный authentication API, не реализация OAuth token endpoint.
  Не заявлять соответствие всему OAuth/OIDC по одним именам полей.
- JSON DTO новых шагов, WebAuthn JSON, ответы ошибок и conditional security
  материализованы в OpenAPI; условные правила дополнительно проверяются runtime. Сохранять operationId операций,
  которые сохраняют смысл; новые операции получают новые имена, не старые SignUp.

## Уточнения при реализации

- Вход по Google idToken допускается только с nonce из нового challenge и поддержкой
  привязки в SDK. Непривязанные ранее полученные ID tokens не принимаются.
- Привязка Google/VK использует code/state из отдельной /oauth-ручки этой сессии.
  Привязка через native idToken требует отдельной согласованной подготовки nonce.
- WebAuthn DTO следуют [W3C WebAuthn](https://www.w3.org/TR/webauthn-3/);
  OIDC-проверки основаны на [OpenID Connect Core](https://openid.net/specs/openid-connect-core-1_0.html#IDTokenValidation).
