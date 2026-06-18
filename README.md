# MCQ Generator

Приложение для генерации вопросов с множественным выбором.

## Требования

- Python 3.11 или выше
- Poetry

## Установка

1. Клонируйте репозиторий:
   ```
   git clone url
   cd mcq-generator-flask
   ```

2. Установите зависимости с помощью Poetry:
   ```
   poetry install
   ```

3. Создайте файл `.env` в корневой директории проекта и добавьте необходимые переменные окружения:
   ```
   APP_SECRET_KEY=your_secret_key
   OPENAI_API_KEY=your_openai_api_key
   ```

## Запуск приложения

Для запуска приложения в производственном режиме с использованием Gunicorn выполните следующую команду:

```
poetry run gunicorn -c gunicorn.conf.py app:app
```

После запуска приложение будет доступно по адресу `http://localhost:5000`.

## Разработка

Для запуска приложения в режиме разработки можно использовать встроенный сервер Flask:

```
flask --app src/app run --debug
```

## Docker

Сборка Docker-образа:

```
docker build -t mcq-generator-flask .
```

Запуск контейнера:

```
docker run -d -p 5000:5000 --name mcq-generator-flask mcq-generator-flask
```

После запуска приложение будет доступно по адресу `http://localhost:5000`.

## Память

Приложение обрабатывает большие тексты через OpenAI API, поэтому потребление памяти зависит от числа воркеров Gunicorn и размера входного текста.

По умолчанию используется **1 воркер** — это снижает пиковое потребление RAM. Для увеличения параллелизма (если памяти достаточно):

```
docker run -d -p 5000:5000 -e WEB_CONCURRENCY=2 --name mcq-generator-flask mcq-generator-flask
```

Дополнительные переменные:

| Переменная | По умолчанию | Описание |
|---|---|---|
| `WEB_CONCURRENCY` | `1` | Число процессов Gunicorn |
| `TEXT_CHUNK_SIZE` | `4000` | Максимальный размер фрагмента текста для одного запроса к LLM |

Рекомендуемый лимит памяти для Docker-контейнера: **512 MB** при `WEB_CONCURRENCY=1`, **1 GB** при `WEB_CONCURRENCY=2`.

## Логирование

Все запросы к модели логируются в stdout. Для отладки установите уровень `DEBUG`:

```
docker run -d -p 5000:5000 -e LOG_LEVEL=DEBUG --name mcq-generator-flask mcq-generator-flask
```

| Переменная | По умолчанию | Описание |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Уровень логирования (`DEBUG`, `INFO`, `WARNING`) |
| `LOG_LLM_PREVIEW_LENGTH` | `300` | Длина превью промпта/ответа в логах. `0` — только размер, `-1` — полный текст |

Пример логов при `LOG_LEVEL=INFO`:

```
2026-06-17 10:00:00 [INFO] llm.questions: Запрос генерации вопросов: text_length=5200, chunks=2, num_questions=5
2026-06-17 10:00:00 [INFO] llm: LLM start: generate_questions (chunk=1/2, text_length=4000, num_questions=3)
2026-06-17 10:00:12 [INFO] llm: LLM done: generate_questions in 12.34s (chunk=1/2, text_length=4000, num_questions=3)
2026-06-17 10:00:12 [INFO] llm.questions: Сгенерировано вопросов: 3 (chunk 1/2)
```

При `LOG_LEVEL=DEBUG` дополнительно выводятся полные промпты и ответы модели.

### Просмотр логов

Логи выводятся в stdout. Отдельный файл логов не создаётся.

**Docker:**

```
# все логи
docker logs mcq-generator-flask

# в реальном времени
docker logs -f mcq-generator-flask

# последние 100 строк
docker logs --tail 100 mcq-generator-flask

# только запросы к модели
docker logs mcq-generator-flask 2>&1 | grep llm
```

Перезапуск с подробным логированием:

```
docker stop mcq-generator-flask && docker rm mcq-generator-flask
docker run -d -p 5000:5000 -e LOG_LEVEL=DEBUG --name mcq-generator-flask mcq-generator-flask
docker logs -f mcq-generator-flask
```

**Локально (Gunicorn):**

```
LOG_LEVEL=DEBUG poetry run gunicorn -c gunicorn.conf.py app:app
```

**Локально (Flask, режим разработки):**

```
LOG_LEVEL=DEBUG flask --app src/app run
```

В Docker Desktop логи также доступны в разделе **Containers → mcq-generator-flask → Logs**.