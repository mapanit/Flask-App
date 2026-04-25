# Flask Vulnerable Application 🔓

Специально созданное веб-приложение с преднамеренными уязвимостями для тестирования сканеров безопасности.

## Уязвимости

1. **SQL Injection** - Внедрение SQL кода через параметры
2. **XSS (Cross-Site Scripting)** - Отраженный и хранимый XSS
3. **Command Injection** - Выполнение системных команд
4. **Path Traversal** - Обход директорий при загрузке файлов
5. **XXE (XML External Entity)** - Парсинг XML с внешними сущностями
6. **Insecure Deserialization** - Небезопасная десериализация Pickle
7. **IDOR** - Прямой доступ к ресурсам других пользователей
8. **Information Disclosure** - Утечка отладочной информации
9. **CORS Misconfiguration** - Неправильная конфигурация CORS
10. **SSRF** - Server-Side Request Forgery
11. **Broken Authentication** - Нарушения аутентификации
12. **Mass Assignment** - Массовое присваивание полей
13. **API Уязвимости** - JSON XSS, IDOR в API, утечка данных API

## Запуск через Docker Compose

### Требования
- Docker
- Docker Compose

### Установка и запуск

```bash
# Перейти в директорию проекта
cd /path/to/test

# Запустить приложение
docker-compose up --build

# Или в фоновом режиме
docker-compose up -d --build
```

### Доступ к приложению

После запуска приложение будет доступно по адресу:
```
http://localhost:5012
```

**Страницы с демонстрацией:**
- `/` - Главная страница
- `/login` - Вход (SQL Injection)
- `/ping` - Command Injection
- `/xml` - XXE
- `/upload` - Path Traversal
- `/api-demo` - 🆕 API уязвимости с JavaScript демонстрацией
- `/debug` - Утечка информации

### Тестовые учетные данные

```
Логин: admin
Пароль: admin123

Логин: user1
Пароль: password123
```

### Остановка приложения

```bash
# Остановить контейнер
docker-compose down

# Остановить и удалить образ
docker-compose down --rmi all
```

## Полезные команды

```bash
# Просмотр логов
docker-compose logs -f

# Просмотр логов конкретного сервиса
docker-compose logs -f vulnerable-app

# Перестроить образ
docker-compose build --no-cache

# Зайти в контейнер
docker-compose exec vulnerable-app /bin/bash

# Очистить все (удалить контейнер и образ)
docker-compose down --rmi all
```

### Использование скриптов управления

**Linux/Mac:**
```bash
./run.sh up        # Запуск
./run.sh down      # Остановка
./run.sh logs      # Логи
./run.sh rebuild   # Пересборка
./run.sh shell     # Оболочка
./run.sh clean     # Очистка
```

**Windows:**
```cmd
run.bat up        # Запуск
run.bat down      # Остановка
run.bat logs      # Логи
run.bat rebuild   # Пересборка
run.bat shell     # Оболочка
run.bat clean     # Очистка
```

## Примеры использования уязвимостей

### SQL Injection
```
Логин: ' OR '1'='1
Пароль: любой
```

### XSS
```
Поиск: <script>alert('XSS')</script>
```

### Command Injection
```

### API Уязвимости (JavaScript)

**На странице /api-demo:** Нажимайте на красные кнопки для демонстрации различных уязвимостей.

**Из консоли браузера (F12):**
```javascript
// XSS через API
VulnerabilityDemo.xss();

// CORS уязвимость
VulnerabilityDemo.cors();

// SQL Injection в API
fetch('/api/search?q=' + encodeURIComponent("' OR '1'='1"))
  .then(r => r.json())
  .then(d => console.log(d));

// IDOR - получить всех пользователей
fetc.gitignore           # Исключения для Git
├── .env.example         # Пример .env файла
├── run.sh               # Скрипт управления (Linux/Mac)
├── run.bat              # Скрипт управления (Windows)
├── README.md            # Этот файл
├── API_VULNERABILITIES.md  # 🆕 Документация по API уязвимостям
├── static/              # 🆕 Статические файлы
│   └── vulnerability-demo.js  # 🆕 JavaScript для демонстрации API уязвимостей
├── templates/           # HTML шаблоны
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── dashboard.html
│   ├── api-demo.html    # 🆕 Страница демонстрации API
// Утечка информации
fetch('/api/admin/stats').then(r => r.json()).then(d => console.log(d));
```

### Curl примеры

```bash
# SQL Injection в API поиске
curl "http://localhost:5012/api/search?q=' OR '1'='1"

# Получить всех пользователей (IDOR)
curl http://localhost:5012/api/users

# Экспортировать все данные
curl http://localhost:5012/api/export

# Получить статистику без авторизации
curl http://localhost:5012/api/admin/stats

# XSS через API
curl http://localhost:5012/api/user/1
```
Хост: 127.0.0.1; whoami
```

### XXE
```xml
<?xml version="1.0"?>
<!DOCTYPE test [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<test>&xxe;</test>

## Дополнительные ресурсы

- [API_VULNERABILITIES.md](API_VULNERABILITIES.md) - Подробное описание API уязвимостей
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP API Top 10](https://owasp.org/www-project-api-security/)
- [PortSwigger Web Security Academy](https://portswigger.net/web-security)
```

## Структура проекта

```
.
├── main.py              # Основное Flask приложение
├── requirements.txt     # Python зависимости
├── Dockerfile           # Конфигурация Docker
├── docker-compose.yml   # Конфигурация Docker Compose
├── .dockerignore        # Исключения для Docker
├── templates/           # HTML шаблоны
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── dashboard.html
│   ├── search.html
│   ├── posts.html
│   ├── ping.html
│   ├── xml.html
│   └── upload.html
└── uploads/             # Директория для загруженных файлов
```

## Файловые системы

- База данных: `database.db` (сохраняется между запусками)
- Загруженные файлы: `uploads/` (сохраняются между запусками)

## Примечание

⚠️ **Это приложение предназначено исключительно для учебных целей и тестирования сканеров безопасности!**

Не используйте в production окружении и не развертывайте в интернете без надлежащей защиты.
