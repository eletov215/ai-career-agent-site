# AI Career Agent — единый стандарт канонических документов

| Поле | Значение |
|---|---|
| Документ | DOCUMENT_STANDARD |
| Идентификатор | DOC-STD-001 |
| Версия | 1.3 |
| Дата | 14 сентября 2026 |
| Статус | ДЕЙСТВУЮЩИЙ |
| Область | PLAN_CURRENT, паспорт, package reports, runbooks, contract references, source audit |

> Начиная с версии 1.1 все активные канонические документы генерируются одним шаблоном. Изменение package status не должно менять визуальный язык, порядок разделов, поля страницы, таблицы, header/footer или палитру.

## 1. Контрольный статус

Единый шаблон обязателен для всех новых active canonical documents. Исторические документы сохраняются как архив и не смешиваются с действующим комплектом.

## 2. Цель и границы

Стандарт устраняет drift, который возникал при ручном перевыпуске DOCX/PDF разными способами. Он регулирует структуру, стили, экспорт, проверку и именование; содержание конкретного пакета остаётся в его собственном документе.

## 3. Обязательная структура

Каждый документ использует одинаковый порядок:

1. Метаданные и контрольный статус.
2. Цель и границы.
3. Реализация или фактическое состояние.
4. Влияние на код и сайт.
5. Проверки и доказательства.
6. Ограничения и риски.
7. Rollback или восстановление.
8. Следующее действие.
9. Журнал версий.

Краткие документы могут объединять соседние разделы, но не менять их смысл.

## 4. Единый визуальный шаблон

| Элемент | Правило |
|---|---|
| Формат | A4, поля 19 мм со всех сторон |
| Основной шрифт | Carlito 10.5 pt (Aptos equivalent), межстрочный интервал 1.15; абзац 4 pt after |
| H1 | 22 pt, left aligned, navy `#173B63`; 18 pt before / 8 pt after |
| H2 | 15 pt, navy `#173B63`, keep-with-next; 14 pt before / 6 pt after |
| H3 | 12.5 pt, blue `#2F6FA3`, keep-with-next |
| Таблица metadata | Navy header, light-blue body, adaptive column widths |
| Status cells | Green completed, amber verification/in progress, grey postponed, red blocked |
| Code blocks | Monospace 8.5 pt, light grey-blue background |
| Header | compact `AI CAREER AGENT / <DOCUMENT_ID>` from page 2 onward |
| Footer | document/version at left; page number at right |

Табличные строки не имеют фиксированной высоты; header row повторяется на новой странице; длинные таблицы могут переноситься, но не обрезаться.


## 4.1 Readability and page-flow rules / v1.3

- No dense title bands or oversized cover pages for operational documents: first page starts with a compact brand label, title, subtitle/status and metadata card.
- Documents longer than 10 pages include a compact navigation block listing H2 sections; Word/PDF heading hierarchy remains usable for navigation.
- Headings never remain alone at a page bottom; heading + first following paragraph/table are kept together.
- Widow/orphan control is enabled for body paragraphs; short lists and status callouts are kept visually together where practical.
- Metadata tables use a narrow label column and a wide value column; narrative tables use content-aware widths instead of equal columns.
- Tables use 8.8-9.2 pt type, generous cell padding, repeated header rows and semantic status fills. Fixed row height is forbidden.
- Long code/route blocks use a soft grey background and are allowed to wrap; they must never force horizontal clipping.
- The first page may use a status badge and short summary callout, but decorative elements must not compete with content.
- PDF output is accepted only after DOCX and PDF page renders show no clipping, overlap, orphan headings, broken glyphs or unintended blank pages.

## 5. Правила содержания

- Один факт — один однозначный источник.
- Source-derived evidence отделяется от архитектурного вывода.
- Команды, пути, IDs и переменные оформляются code style.
- Unknown значения не заменяются догадками.
- Статус ВЫПОЛНЕНО допускается только после измеримых доказательств.
- В package report обязательно перечисляются exclusions и rollback.

## 6. Экспорт и проверка

1. Markdown является текстовым первоисточником документа.
2. DOCX генерируется общим project generator без ручной смены стилей.
3. DOCX рендерится постранично и визуально проверяется.
4. PDF экспортируется из проверенного DOCX.
5. PDF рендерится постранично и визуально проверяется.
6. Контрольные суммы и FILE_INDEX входят в canonical ZIP.

Не допускаются clipping, пустые страницы, исчезнувшие строки таблиц, неправильные header/footer versions или разные палитры внутри одного active release.

## 7. Именование файлов

```text
AI_Career_Agent_<DOCUMENT>_v<version>_<YYYY-MM-DD>.md
AI_Career_Agent_<DOCUMENT>_v<version>_<YYYY-MM-DD>.docx
AI_Career_Agent_<DOCUMENT>_v<version>_<YYYY-MM-DD>.pdf
```

Кодовый архив:

```text
ai-career-agent-site-main-<stage>-<package>-v<version>.zip
```

## 8. Rollback

Если новый generator даёт visual regression, active release не публикуется. Исправляется generator, после чего весь active canonical set пересобирается одной версией; выборочная ручная правка одного DOCX запрещена.

## 9. Следующее действие

Применять DOC-STD-001 v1.3 ко всем документам SEARCH-001 и последующим пакетам. Исторические SYNC/INFRA материалы остаются архивом и не определяют новый стиль.

## 10. Журнал версий

| Версия | Дата | Изменение |
|---|---|---|
| 1.0 | 06.08.2026 | Введён базовый единый шаблон |
| 1.3 | 14.09.2026 | Readability overhaul: compact first page, stronger hierarchy, content-aware tables, widow/orphan control, stable page flow and render QA |
| 1.2 | 14.09.2026 | Carlito fallback clarification |
| 1.1 | 08.08.2026 | Зафиксированы единый generator, палитра, header/footer, стабильная структура и запрет выборочного style drift |


## 11. Renderer fallback clarification / v1.2

2026-09-14: When Aptos is not installed in the renderer, use Carlito consistently for all newly rendered documents. Preserve A4/19 mm, type sizes, navy/blue palette, tables, header/footer and code typography. Do not distribute font files. Previously accepted, unmodified document editions retain their original rendering. This clarification changes presentation only, not package status or project architecture.
