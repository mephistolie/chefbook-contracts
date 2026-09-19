# Начальная схема БД auth

Обновление 2026-09-19: целевой план для API 0.5.0-draft с authentication_steps.
Начальный DDL и локальный auth runtime реализованы по этому плану (20 таблиц).
Действующая dev-БД и развёрнутый backend пока используют предыдущую схему с
authentication_challenges. Облачные БД не изменялись; автоматической конвертации нет.

Согласованный дизайн с обновлением 2026-09-19. Это исходное состояние новой БД, НЕ план
инкрементальных миграций старых таблиц. DDL и репозитории проверены на временной
локальной PostgreSQL; реальные БД и данные не изменены. Runtime отвергает прежнюю
схему; старые таблицы и credentials не конвертируем автоматически. Импорт данных Firebase —
отдельная бизнес-операция, см. [FIREBASE_MIGRATION.md](FIREBASE_MIGRATION.md).

API: [AUTH_API_DRAFT.md](AUTH_API_DRAFT.md). Правила факторов и реаутентификации:
[AUTH_MFA_DESIGN.md](AUTH_MFA_DESIGN.md). Порядок реализации:
[AUTH_API_MIGRATION.md](AUTH_API_MIGRATION.md).

## Общие правила

- Даты — TIMESTAMPTZ, названия `*_timestamp`. UUID аккаунта неизменяемый, случайный;
  session_id — BIGINT. Текстовые значения subject внешнего провайдера храним как TEXT.
- Если NULL не указан, поле NOT NULL. PK/UNIQUE создают соответствующий индекс.
  Хеши токенов — BYTEA; исходные пароли/refresh/flow/confirmation tokens не храним.
- UUID генерирует сервер, он не доказывает доступ. Нормализация email/username
  едина для чтения, записи и уникальности. Не удалять точки и +suffix произвольно.
- TEXT со списком допустимых значений ограничивается CHECK при реализации.
  Первичные ключи не заменяют проверку владельца, purpose и исходной сессии.
- Таблицы и набор полей ниже согласованы. Конкретные TTL, индексы для рабочих
  запросов, политика очистки и некоторые provider-specific параметры — детали
  реализации, отмеченные ниже; произвольные JSONB-контексты не добавляем.
- FK-каскады, кроме явно указанного passkey_transports, определить под жизненный
  цикл при DDL: временные секреты нужно удалять, историю свежих проверок нельзя
  терять до окончания окна доверия. Не распространять CASCADE на всё автоматически.

## Аккаунты и сессии

### accounts

```text
account_id                    UUID, PK
email                         TEXT, UNIQUE
email_verification_timestamp  TIMESTAMPTZ, NULL
username                      TEXT, UNIQUE, NULL
password_hash                 TEXT, NULL
password_change_timestamp     TIMESTAMPTZ, NULL
blocking_timestamp            TIMESTAMPTZ, NULL
creation_timestamp            TIMESTAMPTZ
```

При signUp строка создаётся только после всех проверок, включая собственный код
ChefBook на email. Nullable verification timestamp сохранён из согласованной модели,
но новая завершённая регистрация всегда заполняет его. Не создавать pending accounts.

### identities

```text
account_id          UUID, FK → accounts
provider            TEXT
subject             TEXT
creation_timestamp  TIMESTAMPTZ

PK (account_id, provider)
UNIQUE (provider, subject)
```

Google/VK по одной identity каждого провайдера на аккаунт. Email провайдера не
разрешает автопривязку identity к существующему аккаунту. В JSON ID остаётся
типизированным по провайдеру (Google string, VK integer), в БД единое TEXT.

### sessions

```text
session_id              BIGINT, PK
account_id              UUID, FK → accounts
refresh_token_hash      BYTEA, UNIQUE
ip                      INET
user_agent              TEXT
creation_timestamp      TIMESTAMPTZ
last_refresh_timestamp  TIMESTAMPTZ
expiration_timestamp    TIMESTAMPTZ
```

Ротация refresh сохраняет session_id; новый вход создаёт новую сессию. Обновление
пары проверяет соответствие refresh и ID в URL. Метаданные client в списке сессий
выводятся сервером, вход не требует client в JSON. В JWT добавляется sessionId (разрешено пользователем 2026-09-17), без новых claims прав.

## Аутентификация, регистрация и проверки

### authentications

```text
authentication_id                  UUID, PK
purpose                            TEXT
status                             TEXT
account_id                         UUID, FK → accounts, NULL
session_id                         BIGINT, FK → sessions, NULL
flow_token_hash                    BYTEA, UNIQUE
failed_attempts                    INTEGER
creation_timestamp                 TIMESTAMPTZ
expiration_timestamp               TIMESTAMPTZ
completion_timestamp               TIMESTAMPTZ, NULL
invalidation_timestamp             TIMESTAMPTZ, NULL
confirmation_token_hash            BYTEA, UNIQUE, NULL
confirmation_expiration_timestamp  TIMESTAMPTZ, NULL
```

- purpose: signIn, signUp, passwordChange, emailChange, accountDeletion,
  totpEnrollment, totpRemoval, passkeyEnrollment, passkeyRemoval,
  backupCodesRotation, identityLink, identityUnlink. В API объект `{type: ...}`;
  в БД сохраняем тип. Новые варианты только с определённой серверной политикой.
- status: pending, completed, failed, cancelled. Истечение — по expiry, не отдельная
  обязательная фоновая смена статуса. completion_timestamp фиксирует завершение.
- Для signIn account_id определяется после доказательства; для signUp после
  создания аккаунта. Для реаутентификации account_id/session_id обязательны и
  соответствуют действующей исходной сессии. Сессия результата входа здесь не хранится.
- failed_attempts — ошибки всего процесса, не сбрасываются новым шагом.
- После завершения выдаём короткоживущее разрешение. Использование разрешения и
  действие выполняются атомарно; хеш и expiry обнуляются, consumption_timestamp нет.
- invalidation_timestamp аннулирует и разрешение, и повторное использование
  проверок для окна доверия. При отзыве сессии её процессы также непригодны.
- Недавнюю реаутентификацию находим по исходной сессии, успешным проверочным steps и
  фактическому времени их completion. Автоматически завершённый новый процесс
  не создаёт фиктивных проверок и не продлевает доверие. Не складываем произвольные
  частичные проверки разных процессов. См. AUTH_MFA_DESIGN.md.

### registrations

```text
authentication_id  UUID, PK/FK → authentications
email              TEXT
password_hash      TEXT, NULL
```

Строка появляется после завершения шага registration, а не при старте signUp.
Username отсутствует: пользователь выбирает его позже с действующей сессией.
Email фиксируется в процессе; смена адреса требует нового процесса. До успешного
emailVerification запрещено сохранять password_hash. Подтверждение выводится из
completed email-шагов этого процесса, отдельный timestamp в registrations не нужен.

Регистрация завершается только установкой пароля. ID аккаунта генерируется при
финализации; заранее резервировать его не нужно. Passkey и Google/VK подключаются
к уже созданному аккаунту отдельными защищёнными ручками.

Завершение passwordSetup, создание accounts, завершение процесса и запись событий
в outbox атомарны. Повторно проверяется уникальность email. Установка пароля не
изменяет существующий аккаунт. Конкурирующая регистрация даёт account_exists только
после подтверждения почты; процесс завершается без grant. После финализации временный
хеш удаляется. Независимые процессы не перезаписывают данные друг друга. До подтверждения
email одинаково создаются и проверяются коды для существующего и свободного адреса;
существование аккаунта не отражается в публичном next.

### authentication_steps

```text
step_id               UUID, PK
authentication_id     UUID, FK → authentications
type                  TEXT
status                TEXT
failed_attempts       INTEGER
creation_timestamp    TIMESTAMPTZ
expiration_timestamp  TIMESTAMPTZ
completion_timestamp  TIMESTAMPTZ, NULL
```

type: registration, passwordSetup, passwordVerification, emailVerification,
totpVerification, backupCodeVerification, googleVerification, vkVerification,
passkeyVerification. SMS — последующее расширение.
status: pending, completed, failed, cancelled. Expiry проверяется независимо от статуса.
completion — атомарный переход pending → completed, отдельной таблицы нет.
Неверное доказательство оставляет pending до лимита; общий счётчик процесса не сбрасывается
при создании другого шага. Секреты completion не записываем в step/журнал запросов.
Нет JSONB payload: типизированные поля находятся в registrations или расширениях ниже.

Политика процесса определяет допустимые переходы. Проверять её внутри транзакции
и при старте, и при completion; принятие альтернативы отменяет устаревшие pending-шаги
этого этапа. Повтор завершения не выдаёт новый grant и не создаёт второй credential.
registration/passwordSetup не дают доказательства для окна
реаутентификации существующего аккаунта. Для окна доверия учитываются только настоящие
проверки личности и их фактические completion_timestamp.

### email_authentication_steps

```text
step_id    UUID, PK/FK → authentication_steps
email      TEXT
code_hash  BYTEA
```

Email фиксируется сервером из регистрации/проверяемого аккаунта, а не произвольно
подставляется в запрос подтверждения. Хеш короткого кода — HMAC с серверным секретом
и контекстом step, не простой SHA-256. Код проверяется вместе с доступом к
исходному процессу; прочитать письмо можно на другом устройстве. Новый resend
создаёт новую проверку и аннулирует предыдущий код этого процесса, не чужие процессы.

### passkey_authentication_steps

```text
step_id    UUID, PK/FK → authentication_steps
challenge  BYTEA
```

Случайный WebAuthn challenge для входа/реаутентификации, не регистрации ключа.
Результат проверяется WebAuthn-библиотекой с серверными RP/origin/UV требованиями.

### sms_authentication_steps — будущее расширение, не стартовый DDL

```text
step_id    UUID, PK/FK → authentication_steps
phone      TEXT
code_hash  BYTEA
```

Телефонный вход, привязка номера, доставка SMS и тарифы ещё не реализуются.

## OAuth

### google_authentication_steps

```text
step_id     UUID, PK, FK → authentication_steps.step_id
nonce_hash  BYTEA
```

Типизированное расширение для native Google ID-token challenge. Сервер создаёт nonce,
клиент передаёт его SDK, сервер проверяет nonce в подписанном ID token. Не создаём
фиктивный OAuth state. Погашение связано с базовым step. Поддержка нативного SDK
и configured audience обязательны; наличие таблицы не включает неподдержанный flow.

### oauth_requests

```text
state_hash               BYTEA, PK
provider                 TEXT
step_id                  UUID, FK → authentication_steps, NULL
session_id               BIGINT, FK → sessions, NULL
client_binding_hash      BYTEA
redirect_uri             TEXT
nonce_hash               BYTEA, NULL
encrypted_code_verifier  BYTEA, NULL
creation_timestamp       TIMESTAMPTZ
expiration_timestamp     TIMESTAMPTZ
```

CHECK: ровно один из step_id/session_id задан. Первый вариант — вход, регистрация
или реаутентификация; контекст через процесс. Второй — отдельная привязка identity;
аккаунт через исходную сессию. oauth_request_id, account_id, consumption_timestamp нет.

Валидируем срок/инициатора и атомарно забираем запрос через DELETE RETURNING с
фиксацией удаления ДО сетевого обмена. При сбое после удаления OAuth начинается
заново; одновременно продолжает только один запрос. Неверный инициатор не должен
погасить чужой запрос. Ответ провайдера повторно проверяется относительно актуального
состояния аккаунта/процесса до выдачи разрешения или привязки.

consumed_auth_proofs не создаём. ID token должен быть привязан серверным случайным
nonce к одноразовой проверке. Проверяем подпись, issuer, audience, срок, nonce и
владельца; nonce, присланный клиентом отдельно от подписанного токена, недостаточен.
Nullable nonce_hash допускает другие протокольные сценарии, но не downgrade
сценария, где nonce обязателен. Правило передачи/хеширования зависит от SDK.

Нативный ID-token flow без redirect/state не должен создавать фиктивный oauth_request.
Его nonce хранится в типизированном расширении provider challenge (PK/FK step_id,
nonce_hash): для Google реализуется google_authentication_steps.
Поддержку nonce в нативном SDK проверять перед включением соответствующего клиента.
Это оставшаяся протокольная деталь реализации, а не разрешение принимать неподвязанные
токены. Если SDK не позволяет нужную привязку — выбрать поддерживаемый иной флоу.

PKCE verifier нужен в восстановимом виде для обмена кода: шифрование, не хеш.
Сервер хранит его, только если он владеет этим PKCE-флоу. Nonce не доказывает свежую
авторизацию пользователя у провайдера: auth_time/другие гарантии проверяются отдельно.
Текущую backend-защиту ConsumeReauthentication нельзя убрать до готовности замены.

## Изменения аккаунта

### email_change_requests

```text
account_id          UUID, PK/FK → accounts
previous_email      TEXT
email               TEXT
stage               TEXT
token_hash          BYTEA, UNIQUE
creation_timestamp  TIMESTAMPTZ
expiration_timestamp TIMESTAMPTZ
```

stage: awaiting_previous_email / awaiting_new_email. Одна заявка на аккаунт.
После старого адреса меняем stage и токен, отправляем письмо на новый. Новый email
во время незавершённой смены требует отдельного решения о замене заявки; безопасный
старт — конфликт, без неявного переписывания. Адрес меняем после второго подтверждения.

### password_reset_requests

```text
account_id           UUID, PK/FK → accounts
token_hash           BYTEA, UNIQUE
creation_timestamp   TIMESTAMPTZ
expiration_timestamp TIMESTAMPTZ
```

Одноразовый сброс. Не отключает TOTP, не создаёт обходящую MFA сессию.

### account_deletion_requests

```text
account_id          UUID, PK/FK → accounts
delete_shared_data  BOOLEAN
request_timestamp   TIMESTAMPTZ
deletion_timestamp  TIMESTAMPTZ
```

PATCH меняет только delete_shared_data, не срок. Отмена удаляет заявку. Автор
сохранённых рецептов показывается удалённым; закладки ссылаются на оригинал, не копии.
Политику владения общими коллекциями при удалении реализовать явно, не терять чужие данные.

## Факторы

### totp

```text
account_id             UUID, PK/FK → accounts
encrypted_secret       BYTEA
last_used_step         BIGINT
activation_timestamp   TIMESTAMPTZ
```

Один активный секрет. last_used_step NOT NULL: сразу записываем шаг первого успешного
кода при активации. При входе/реаутентификации принимаем только допустимый по времени
код со step больше сохранённого; обновление атомарно с завершением проверки.
Ключ шифрования находится вне БД. Параметры алгоритма/длины/периода фиксируются
серверной конфигурацией и должны соответствовать otpauthUri.

### totp_activation_requests

```text
account_id           UUID, PK/FK → accounts
session_id           BIGINT, FK → sessions
encrypted_secret     BYTEA
expiration_timestamp TIMESTAMPTZ
```

Одна заявка на аккаунт. Нет setup_token_hash, creation_timestamp, failed_attempts.
Подтверждение требует исходную живую сессию и первый правильный код. Новая заявка
заменяет pending secret. Ограничение попыток через защиту по аккаунту/окну необходимо
перед публичным запуском, его хранилище отложено вместе с abuse_counters.

### passkeys

```text
passkey_id          UUID, PK
account_id          UUID, FK → accounts
credential_id       BYTEA, UNIQUE
public_key          BYTEA
name                TEXT
sign_count          BIGINT
backup_eligible     BOOLEAN
backup_state        BOOLEAN
creation_timestamp  TIMESTAMPTZ
last_use_timestamp  TIMESTAMPTZ, NULL
```

public_key — COSE с алгоритмом. user_handle получаем из бинарного неизменяемого UUID
аккаунта; отдельной колонки нет. Это правило нельзя менять для уже зарегистрированных
ключей без поддержки прежних значений. Приватные ключи/биометрию не храним.
sign_count/backup flags обрабатывает WebAuthn-библиотека: нельзя требовать безусловного
роста счётчика от всех синхронизируемых passkey. Один passkey не равен одному устройству.

### passkey_transports

```text
passkey_id  UUID, FK → passkeys, ON DELETE CASCADE
transport   TEXT

PK (passkey_id, transport)
```

Нормализованное многозначное свойство, без отдельного справочника transport.
Нет строк — транспорты не сообщены. Массива/JSONB transports в passkeys нет.

### passkey_registration_requests

```text
request_id           UUID, PK
session_id           BIGINT, FK → sessions
challenge            BYTEA
expiration_timestamp TIMESTAMPTZ
```

Нет account_id (через сессию), request_token_hash, user_handle, creation_timestamp,
consumption_timestamp. Проверяем исходную сессию, expiry и WebAuthn-ответ. Сохранение
ключа и удаление заявки в одной транзакции. Параллельные заявки различаются request_id.
Минимальная структура предполагает единую серверную политику RP/origins/алгоритмов/UV;
если библиотеке нужен per-request контекст, явно дополнить типизированную схему.

### backup_codes

```text
account_id           UUID, FK → accounts
code_hash            BYTEA
generation_timestamp TIMESTAMPTZ

PK (account_id, code_hash)
```

Высокоэнтропийные случайные коды; хеш — HMAC-SHA-256 с ключом вне БД.
Нет code_id и consumption_timestamp. DELETE RETURNING и успешное завершение проверки
атомарны. Перевыпуск атомарно заменяет весь набор; plaintext возвращается один раз.
Первый набор выдаём при успешной активации TOTP, но коды принадлежат аккаунту, не TOTP.
Пока это резервный второй фактор, не самостоятельный вход без первого доказательства.
Когда строк не осталось, remainingCount=0, generationTimestamp=null в API.

## События

### outbox

```text
message_id          UUID, PK
exchange            TEXT
type                TEXT
body                JSONB
creation_timestamp  TIMESTAMPTZ
```

Событие записывается в транзакции с изменением данных. Читаем старые первыми:
ORDER BY creation_timestamp, message_id; это не обещает глобального порядка при
нескольких исполнителях. Получатели обязаны поддерживать повторную доставку.
Не добавляем отдельные email_jobs и поля lease/attempts auth-outbox без требований.

## Что исключено или отложено

- roles/account_roles: исключены. Пока проверяем действия над объектами и ограничения;
  назначаемые permissions/роли добавим с конкретными требованиями, не через роль user
  по умолчанию. Подписка и restrictions не являются универсальными правами.
- abuse_counters: отложена вся таблица; числа квот и хранилище лимитеров не утверждены.
  TTL, одноразовость, failed_attempts процессов/steps сохраняются. Публичный
  запуск регистрации/почты требует базовой защиты. См. AUTH_ABUSE_PROTECTION.md.
- consumed_auth_proofs: не создаём при обязательной provider binding, описанной выше.
- reauthentications: заменена общими authentications.
- authentication_attempts: не храним; результат в step, ошибки в безопасных логах.
- passkey_removal_authentications/identity_authentications: исключены. Разрешение
  ограничено purpose, аккаунтом и сессией, но не конкретным passkey/provider.
- firebase_accounts/firebase_imports: в auth не создаём. Импорт запускается через
  outbox, состояние/идемпотентность — у исполнителя миграции.
- email_verification_requests/ограниченные регистрационные sessions: заменены
  registrations и steps, нового аккаунта до подтверждения нет.

## Проверки начального DDL и репозиториев

Проверить пустую PostgreSQL: создание схемы, FK/UNIQUE/CHECK, индексы выборок и очистки.
Затем проверить реальные конкурентные транзакции: два signUp одной почты, повторное
погашение grants/backup codes, TOTP replay, параллельный refresh, отзыв между шагами,
удаление OAuth state до обмена, повтор attestation, смена credentials и invalidation.
SQL mocks недостаточны для доказательства корректности этих гонок.
