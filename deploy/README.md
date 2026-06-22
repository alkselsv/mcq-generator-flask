# Развёртывание nginx (HTTPS + Basic Auth)

Файлы в этом каталоге воспроизводят настройку reverse proxy для MCQ Generator на новом сервере.

## Архитектура

```
Браузер → nginx :443 (TLS + Basic Auth) → http://127.0.0.1:5000 (docker-compose web)
```

Порт **5000** не должен быть доступен снаружи — только с localhost. В `docker-compose.yml` уже указано:

```yaml
ports:
  - "127.0.0.1:5000:5000"
```

## Быстрый старт

```bash
# 1. Запустить приложение
cd /path/to/mcq-generator-flask
cp .env.example .env   # заполнить APP_SECRET_KEY, OPENAI_API_KEY
docker-compose up -d --build

# 2. Настроить nginx (указать IP или hostname для сертификата)
sudo ./deploy/scripts/setup-nginx.sh 203.0.113.10

# 3. Открыть в браузере
# https://203.0.113.10/
```

При первом заходе браузер предупредит о самоподписанном сертификате — это нормально, нужно принять исключение.

## Скрипты

| Скрипт | Назначение |
|--------|------------|
| `scripts/setup-nginx.sh` | Полная установка: пакеты, SSL, Basic Auth, конфиг nginx |
| `scripts/generate-ssl.sh` | Только самоподписанный сертификат в `/etc/nginx/ssl/` |
| `scripts/create-htpasswd.sh` | Создать или обновить пользователя Basic Auth |

### Примеры

```bash
# Только сертификат
sudo ./deploy/scripts/generate-ssl.sh 203.0.113.10

# Только пользователь Basic Auth
sudo ./deploy/scripts/create-htpasswd.sh admin

# Добавить ещё одного пользователя
sudo htpasswd /etc/nginx/.htpasswd editor
```

## Файлы конфигурации

| Файл | Куда копируется |
|------|-----------------|
| `nginx/mcq-generator.conf` | `/etc/nginx/sites-available/mcq-generator` |
| `nginx/ip-whitelist.conf.example` | опционально в `/etc/nginx/snippets/mcq-ip-whitelist.conf` |

### IP-whitelist (опционально)

Если нужен доступ только с определённых IP **в дополнение** к Basic Auth:

```bash
sudo cp deploy/nginx/ip-whitelist.conf.example /etc/nginx/snippets/mcq-ip-whitelist.conf
sudo nano /etc/nginx/snippets/mcq-ip-whitelist.conf
```

Раскомментируйте в `mcq-generator.conf`:

```nginx
include /etc/nginx/snippets/mcq-ip-whitelist.conf;
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

## Переменные окружения для скриптов

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `MCQ_SSL_DIR` | `/etc/nginx/ssl` | Каталог для сертификата |
| `MCQ_SSL_DAYS` | `3650` | Срок действия сертификата (дни) |
| `MCQ_HTPASSWD_FILE` | `/etc/nginx/.htpasswd` | Файл паролей Basic Auth |
| `MCQ_NGINX_SITE_NAME` | `mcq-generator` | Имя сайта в sites-available |
| `MCQ_BACKEND_URL` | `http://127.0.0.1:5000` | URL backend для проверки health |

## Логи nginx

```bash
sudo tail -f /var/log/nginx/qg-access.log
sudo tail -f /var/log/nginx/qg-error.log
```

Логи генерации и LLM — в docker-compose worker, см. основной README.

## Let's Encrypt (если появится домен)

Самоподписанный сертификат нужен только без домена. При наличии домена:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d qg.example.com
```

После этого certbot обновит `ssl_certificate` / `ssl_certificate_key` в конфиге.

## Безопасность

- **Не коммитьте** `/etc/nginx/.htpasswd` и `/etc/nginx/ssl/*` в git.
- Храните пароли Basic Auth отдельно (менеджер паролей).
- Проверьте, что порт 5000 не открыт наружу: `ss -tlnp | grep 5000` → `127.0.0.1:5000`.
