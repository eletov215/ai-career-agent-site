# История изменений AI Career Agent

Формат основан на Keep a Changelog.

## [Unreleased]

### FND-002 — конфигурация приложения

#### Добавлено

- Новый модуль `config.py` с неизменяемым объектом `AppSettings`.
- Явные режимы `production`, `development` и `test`, выбираемые через `APP_ENV`.
- Централизованная проверка обязательных переменных, Fernet-ключа, числовых диапазонов и логических значений.
- Безопасные фиктивные OAuth-настройки только для `APP_ENV=test`; production и development не получают встроенных секретов.
- Unit-тесты конфигурации: отсутствие production-переменных, неверный режим, неверный Fernet-ключ, числа и boolean-параметры.
- Subprocess-проверки импорта `app.py` в режимах `production`, `development` и `test`, включая ранний отказ неполной production-конфигурации.
- `APP_ENV=production` в `render.yaml`.

#### Изменено

- `app.py` больше не читает переменные окружения по всему модулю: рабочие константы формируются из одного проверенного `SETTINGS`.
- `HeadHunterProvider` получает `DEBUG_HH` и `HH_CURRENCY_SCAN_PAGES` через конструктор и больше не читает окружение самостоятельно.
- Тестовая конфигурация больше не задаёт реальные по форме секреты в `tests/conftest.py`; достаточно `APP_ENV=test` и временного `DATA_DIR`.
- GitHub Actions теперь явно компилирует новый `config.py` перед запуском тестов.
- README и архитектурная документация дополнены правилами режимов окружения и диагностикой ошибок запуска.

#### Проверено локально

- `python -m compileall -q app.py config.py services tests scripts` — успешно.
- `python -m pytest -q` — `41 passed, 2 skipped`; route- и app-startup-модули пропущены только потому, что Flask недоступен в локальном sandbox и должны выполниться в GitHub Actions после установки `requirements.txt`.
- Репозиторий не требует реальных OAuth-токенов или API-ключей для unit-тестов.

#### Требует подтверждения

- Полный набор route smoke-тестов и subprocess-проверок трёх режимов в GitHub Actions.
- Импорт приложения с `APP_ENV=production` и действующими Render-переменными.
- Deploy на Render и smoke-проверка основных страниц и логов.

### FND-001 — базовые тесты и CI

#### Выполнено

- Добавлены `pytest.ini`, `requirements-dev.txt`, каталог `tests/`, mock-провайдеры и проверка чистоты репозитория.
- GitHub Actions проверен зелёным запуском, намеренно красным тестом и повторным зелёным запуском.
- Изменения объединены с `main`; Render deploy и ручная smoke-проверка подтверждены владельцем проекта.
- `Flask` уже зафиксирован на 3.1.3, `Werkzeug` — на 3.1.6.

### Ранее исправлено

- Поиск HH больше не использует пользовательский OAuth-токен соискателя.
- Добавлена необязательная авторизация приложения через `HH_APP_TOKEN`.
- Пустой параметр `text` больше не отправляется в HH API.
- Для `403` выводятся безопасные диагностические данные `Server` и `Request ID` без токенов.
- Старый маршрут `/hh/vacancies` перенаправляет в единый поиск.

## [0.3.0] — 2026-07-20

### Добавлено

- Единая страница поиска вакансий.
- Поддержка выбора источника.
- Провайдер HeadHunter.
- Повторный публичный запрос после `401` или `403`.
- Диагностическое логирование ответа HH.
- Отображение ошибок источника на странице.

### Изменено

- HeadHunterProvider заменён с заглушки на реальный HTTP-запрос.
- Провайдер HH подключён к рабочему `app.py`.
- Render продолжает запускать `gunicorn app:app`.

### Известные проблемы

- `GET https://api.hh.ru/vacancies` возвращает `403 Forbidden`.
- Запрос с OAuth и запрос без OAuth возвращают одинаковую ошибку.
- В ответе присутствует `Server: ddos-guard`.
- Причина блокировки не подтверждена поддержкой HH.

## [0.2.0]

### Добавлено

- Подключение «Работа России» / Trudvsem.
- Синхронизация вакансий.
- Статус фоновой синхронизации.
- Логирование запуска и ошибок.

## [0.1.0]

### Добавлено

- Flask-приложение.
- Базовые HTML-шаблоны.
- Развёртывание на Render.
- Подключение GitHub.
- Dashboard.
- Начальная OAuth-интеграция HeadHunter.
## 2026-07-20 — HH application token search

- Поиск вакансий HeadHunter теперь выполняется только с `HH_APP_TOKEN`.
- Удалён повторный публичный запрос, который HH отклоняет с HTTP 403.
- HeadHunter доступен в общем поиске независимо от пользовательского OAuth-аккаунта.
- Добавлены понятные ошибки при отсутствующем или отклонённом токене приложения.


## 2026-07-20 — устойчивость Trudvsem к тайм-аутам
- Добавлены до 5 повторных попыток для каждого запроса к API «Работы России».
- Использована экспоненциальная пауза между попытками: 1, 2, 4 и 8 секунд.
- Временные ошибки соединения, чтения, HTTP 429 и HTTP 5xx больше не останавливают синхронизацию после первой неудачи.
- Количество попыток и базовая пауза настраиваются через `TRUDVSEM_REQUEST_ATTEMPTS` и `TRUDVSEM_RETRY_BACKOFF`.

## 2026-07-21 — второй этап единого поиска
- Добавлены общие фильтры региона, опыта, занятости, формата работы и валюты.
- Фильтры адаптируются для HeadHunter и безопасно применяются после ответа там, где API источника не поддерживает точное сопоставление.
- Локальный кэш «Работы России» получил миграцию поля опыта и фильтрацию по новым параметрам.
- Все параметры сохраняются при пагинации и при запуске фонового обновления «Работы России».

## Исправление фильтров второго этапа

- Исправлено преобразование опыта работы в идентификаторы HeadHunter API.
- Добавлено преобразование валюты RUB в RUR для запроса HeadHunter.
- Добавлена обязательная фильтрация результатов по выбранной валюте после ответа провайдера.
- Ошибки отдельного источника показываются как нейтральное предупреждение без технического текста.
- Добавлено спокойное состояние для пустой выдачи вакансий.

## 2026-07-21 — исправление полноты поиска по валюте

- Валюта больше не используется как якобы строгий серверный фильтр HH без порога зарплаты.
- При выбранной валюте HH просматривается расширенными страницами по 100 вакансий и формирует локальную страницу только из вакансий с фактической валютой зарплаты.
- По умолчанию просматривается до 20 страниц HH; лимит можно изменить переменной `HH_CURRENCY_SCAN_PAGES`.
- Современный код белорусского рубля изменён на BYN; старые значения BYR продолжают распознаваться как BYN.
- Локальный SQLite-кэш сопоставляет BYN и устаревший BYR.

## 2026-07-25 — Automatic university emblem lookup
- Added `/api/university/logo` endpoint.
- Added Wikidata/official-site emblem resolver with SSRF and size checks.
- Resume builder now starts emblem lookup after the education answer and stores the result in the local draft.

## Resume fullscreen preview and PDF download
- Added adaptive fullscreen A4 reader for desktop, tablet, and mobile.
- Added PDF download actions in the preview toolbar and fullscreen reader.
- Added keyboard accessibility, Escape/background closing, and reduced-motion support.


## PDF export stage 1
- Added multi-page A4 export.
- Empty resume sections are removed from the final PDF.
- Semantic blocks are moved to the next page instead of being cut.
- Added page numbering for multi-page resumes.
- Profile photo and university emblem remain supported.

## Исправление пустого PDF после заполнения формы

- источник предпросмотра принудительно выводится из состояния `hidden` перед измерением;
- PDF больше не создаётся из одного сверхвысокого canvas;
- каждая страница A4 отрисовывается и добавляется в PDF отдельно;
- экспорт использует тот же постраничный макет и поля, что и живой предпросмотр;
- добавлена проверка, которая не позволяет сохранить полностью белую страницу.

## 2026-07-26 — исправление отрисовки последней страницы PDF

- Количество листов теперь рассчитывается по последней видимой строке или фотографии, без учёта пустого нижнего отступа колонок.
- Пустой автоматически созданный последний лист не добавляется в PDF.
- Проверка canvas больше не уменьшает редкий текст до миниатюры и не принимает заполненную страницу за белую.
- Для четвёртой и последующих страниц используется явное вертикальное позиционирование вместо большого `translateY`.
- При нестабильной первой отрисовке страница автоматически формируется повторно с более экономным масштабом.
- Нумерация PDF строится только по реально сформированным страницам.

## Resume preview pager refinement
- Кнопки переключения страниц увеличены и приведены к фирменному круглому стилю.
- Панель навигации вынесена ниже листа A4, чтобы не перекрывать текст предпросмотра.
- Добавлены адаптивные отступы для телефона и планшета.

## Mobile resume preview refinement
- Reduced the mobile preview toolbar height and placed Open/PDF actions in one compact row.
- Added safe margins around the A4 thumbnail on phones and tablets.
- Removed excess internal spacing from the preview panel.
- Reduced the mobile “Continue interview” area to a compact action button.
- Kept page navigation hidden when the resume has only one page.

## Mobile and tablet resume preview controls
- Removed the separate “Open” button from the preview toolbar.
- Disabled opening the fullscreen reader by tapping the A4 preview on screens up to 900 px.
- Kept desktop click-to-open behavior for large screens.
- Added compact page controls in a dedicated row below the A4 preview.
- Page controls remain hidden when the resume contains only one page.

## Mobile/tablet resume text bounds
- Added fixed inner gutters to the A4 resume layout on screens up to 900px.
- Added safe wrapping for long words, URLs, achievements and user-entered text.
- Constrained resume columns, lists and experience blocks to the available page width.
- Desktop resume layout and PDF export rules were not changed.
