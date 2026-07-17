# AI Career Agent — этап 2

Добавлено:
- зашифрованное хранение OAuth-токенов SuperJob;
- автоматическое обновление access token;
- личный кабинет;
- получение резюме пользователя;
- поиск вакансий SuperJob и прямые ссылки.

## Новая переменная Render

`TOKEN_ENCRYPTION_KEY`

Сгенерируйте на компьютере:

```powershell
py -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Вставьте результат в Render → Environment.

Важно: SQLite на бесплатном Render может очищаться при перезапуске или новом деплое. Для одного тестового пользователя это подходит. Следующий производственный этап — PostgreSQL.

## HeadHunter vacancies

Added `/hh/vacancies` with vacancy search, period and remote-work filters, pagination, and automatic HH access-token refresh.
