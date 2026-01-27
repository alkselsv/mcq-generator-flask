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
poetry run gunicorn -w 4 -b 0.0.0.0:5000 --pythonpath src app:app
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
docker run -d -p 8080:5000 --name mcq-generator-flask mcq-generator-flask
```

После запуска приложение будет доступно по адресу `http://localhost:8080`.