# Предыдущий auth snapshot в OpenAPI

Архив описания текущего машинного контракта `0.3.0-draft`, сохранён 2026-09-17.
Это НЕ целевой дизайн. Он нужен для проверки существующего YAML и понимания
расхождений при следующей реализации. Текущие решения: [AUTH_API_DRAFT.md](AUTH_API_DRAFT.md).
Утверждения ниже о переносе в OpenAPI относятся только к этому старому snapshot.

---

# Проект API авторизации

Обновлено 2026-09-16. Список перенесён в OpenAPI `0.3.0-draft`.
Бэкенд и клиент пока используют прежний контракт. Детали миграции и предложения
по ещё не согласованным DTO описаны в [AUTH_API_MIGRATION.md](AUTH_API_MIGRATION.md).

## Список ручек

Общий префикс — `/v1/auth`.

| Метод | Путь | Назначение |
|---|---|---|
| `POST` | `/account` | Регистрация и автоматическая отправка подтверждения |
| `PUT` | `/account/password` | Смена пароля с проверкой текущего |
| `POST` | `/account/password/recovery` | Запрос восстановления пароля |
| `POST` | `/account/password/recovery/confirmation` | Подтверждение токеном и установка нового пароля |
| `PUT` | `/account/username` | Установка username |
| `POST` | `/account/email/verification` | Повтор кода своей регистрации или начало смены адреса |
| `POST` | `/account/email/verification/confirmation` | Код регистрации в исходной сессии либо токен смены email |
| `POST` | `/account/deletion` | Запрос отложенного удаления |
| `PATCH` | `/account/deletion` | Изменить deleteSharedData без изменения срока |
| `DELETE` | `/account/deletion` | Отмена удаления; 204 без тела, в том числе если заявки нет |
| `GET` | `/account/identities` | Список привязанных внешних аккаунтов |
| `POST` | `/account/identities/google` | Привязка Google |
| `DELETE` | `/account/identities/google` | Отвязка Google |
| `POST` | `/account/identities/vk` | Привязка VK |
| `DELETE` | `/account/identities/vk` | Отвязка VK |
| `POST` | `/oauth/google` | Создать OAuth-запрос Google, получить URL и срок действия |
| `POST` | `/oauth/vk` | Создать OAuth-запрос VK, получить URL и срок действия |
| `POST` | `/sessions` | Вход; способ определяется полем `method` в типизированном теле |
| `GET` | `/sessions` | Список своих сессий без токенов |
| `DELETE` | `/sessions/{id}` | Завершение конкретной сессии |
| `DELETE` | `/sessions` | Завершение всех своих сессий |
| `POST` | `/session/tokens` | Обновление пары токенов по refresh token |
| `DELETE` | `/session` | Выход из текущей сессии |
| `GET` | `/usernames/{username}/availability` | Проверка доступности username |

## Регистрация и подтверждение

- POST /account возвращает 201 + TokensResponse с emailVerificationRequired:
  временный аккаунт, отдельная попытка с хешем пароля и ограниченная сессия.
  Завершённый email — 409 account_exists; регистрация не сбрасывает пароль.
- POST /sessions создаёт сессию существующего аккаунта. Сохраняется исключение
  для Google/VK: новая identity начинает регистрацию с таким же ограниченным
  ответом. Перенос OAuth-регистрации на другую ручку здесь не выполняется.
- Код ChefBook нужен всем новым аккаунтам, включая Google/VK. Письмо можно читать
  где угодно, но код подтверждается только в исходной сессии той же попытки.
- Resend: bearer + `{ "purpose": "verify" }`; email выбирается на сервере.
- Confirmation: bearer + `{ "purpose": "verify", "code": "012345" }`.
  Ответ 200: purpose=verify, status=verified и tokens: TokensResponse. Сохраняется
  sessionId, меняется пара токенов; конкурирующие попытки и сессии отзываются.
- Refresh не повышает права чужой попытки по глобальному флагу подтверждения email.
  До завершения доступны только resend, confirmation, refresh и собственный logout.
  Локальные функции приложения не ограничиваются. JWT claims не меняются.
- Пароль или provider/subject закрепляются за аккаунтом только при успешном
  завершении соответствующей попытки. Подробности и схема БД:
  [AUTH_DATABASE_PLAN.md](AUTH_DATABASE_PLAN.md).
- Смена email сохраняет двухэтапное подтверждение старого/нового адреса токенами:
  `{ "purpose": "change", "token": "..." }`. Для этого варианта confirmation
  bearer не требуется, а запрос смены требует bearer и ReauthenticationRequest.
- Потеря исходной сессии означает новую независимую попытку. Потеря успешного
  ответа подтверждения — обычный вход с установленными credentials, а не повторная
  выдача токенов по использованному коду.
- Регистрационный код не является токеном восстановления пароля. Уже перенесённые
  Firebase-аккаунты восстанавливаются через password recovery. Legacy-миграция
  отложена; [FIREBASE_MIGRATION.md](FIREBASE_MIGRATION.md).

## Остальные решения

- Username принадлежит auth. PUT /account/username; доступность через публичный
  GET /usernames/{username}/availability. Профиль отдаёт GET /v1/profile.
- CreateSessionRequest использует method и oneOf: password (login/password),
  google (idToken либо code/state), vk (code/state). OAuth URL получают через
  POST /oauth/google или /oauth/vk. Redirect URI задаётся сервером.
- Авторизованный аккаунт явно привязывает identity отдельной ручкой; новая связь —
  201 с Location, та же проверенная связь — 204. Автопривязки по email нет.
- TokensResponse содержит userId, sessionId, accessToken, refreshToken,
  expirationTimestamp и restrictions. Текущие типы: pendingDeletion и
  emailVerificationRequired. JWT capabilities этим ответом не определяются.
- POST /session/tokens использует refreshToken в теле. DELETE /session — refresh
  Bearer и 204, без тела. Неизвестный уже отозванный refresh при logout — 204.
- GET /sessions возвращает список без токенов. DELETE /sessions отзывает все,
  DELETE /sessions/{id} — одну свою сессию. Для временной регистрации доступны
  только refresh и DELETE /session, не список/отзыв других попыток.
- Пароль и username меняются PUT. Восстановление пароля пока остаётся на текущих
  путях /account/password/recovery и /confirmation; обсуждённый rename в reset
  отдельно, в это изменение не включён.
- Удаление: POST 202 и PATCH 200 возвращают AccountDeletionResponse; DELETE 204.
  PATCH меняет только deleteSharedData, не дату. GET удаления отсутствует.
- Без полезного тела возвращаем 204; запросы resend/recovery дают 202.
- Bearer-ошибки — 401 с WWW-Authenticate; неправильные JSON proofs — 400;
  запрет — 403, конфликт — 409, лимит — 429 с Retry-After. Для refresh недействительный
  токен — 400 invalid_refresh_token. Недоступность зависимости — 503.
- Все ответы с токенами, включая регистрацию и confirmation, должны иметь
  Cache-Control: no-store и Pragma: no-cache, также на ошибках.

Контракт опережает реализацию. План расходов: [AUTH_ABUSE_PROTECTION.md](AUTH_ABUSE_PROTECTION.md).
Переход потребителей: [AUTH_API_MIGRATION.md](AUTH_API_MIGRATION.md).
