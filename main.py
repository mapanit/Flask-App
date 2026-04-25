# main.py (исправленный и полный)
import os
import sqlite3
import pickle
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, make_response,
    send_file, send_from_directory
)
from werkzeug.utils import secure_filename
import hashlib
import base64
import json

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = 'super_secret_key_123'  # Уязвимость 1: Слабый секретный ключ
app.config['UPLOAD_FOLDER'] = './uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Уязвимость 2: SQLite база без параметризации


def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, username TEXT, password TEXT, email TEXT, is_admin INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS posts
                 (id INTEGER PRIMARY KEY, title TEXT, content TEXT, author TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS comments
                 (id INTEGER PRIMARY KEY, post_id INTEGER, comment TEXT, user TEXT)''')

    # Добавляем тестовых пользователей
    c.execute("INSERT OR IGNORE INTO users (username, password, email, is_admin) VALUES ('admin', 'admin123', 'admin@test.com', 1)")
    c.execute("INSERT OR IGNORE INTO users (username, password, email) VALUES ('user1', 'password123', 'user1@test.com')")
    
    # Добавляем тестовые посты
    c.execute("INSERT OR IGNORE INTO posts (id, title, content, author) VALUES (1, 'Первый пост', 'Содержание первого поста', 'admin')")
    
    conn.commit()
    conn.close()


init_db()

# ====================== УЯЗВИМЫЕ ФУНКЦИИ ======================


def vulnerable_sqli(query):
    """Уязвимость 3: SQL инъекция через конкатенацию строк"""
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # КРИТИЧЕСКАЯ УЯЗВИМОСТЬ: прямое внедрение пользовательского ввода
    c.execute(f"SELECT * FROM users WHERE username = '{query}'")
    result = c.fetchall()
    conn.close()
    return result


def vulnerable_command_injection(cmd):
    """Уязвимость 4: Инъекция команд"""
    # КРИТИЧЕСКАЯ УЯЗВИМОСТЬ: выполнение shell команд
    result = subprocess.check_output(f"ping -c 1 {cmd}", shell=True)
    return result.decode()


def vulnerable_xxe(xml_data):
    """Уязвимость 5: XXE (XML External Entity)"""
    try:
        # УЯЗВИМОСТЬ: парсинг XML без отключения внешних сущностей
        root = ET.fromstring(xml_data)
        return ET.tostring(root, encoding='unicode')
    except Exception as e:
        return str(e)


def vulnerable_deserialize(data):
    """Уязвимость 6: Небезопасная десериализация"""
    # УЯЗВИМОСТЬ: использование pickle для десериализации
    return pickle.loads(base64.b64decode(data))

# ====================== API ЭНДПОИНТЫ ======================


@app.route('/api/user/<int:user_id>')
def api_get_user(user_id):
    """API эндпоинт для получения данных пользователя (XSS уязвимость)"""
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute(f"SELECT id, username, email FROM users WHERE id = {user_id}")
    user = c.fetchone()
    conn.close()

    if user:
        # УЯЗВИМОСТЬ: возвращаем неочищенные данные
        return jsonify({
            'id': user[0],
            'username': user[1],
            'email': user[2],
            'bio': f'<img src=x onerror="alert(\'XSS в профиле {user[1]}\')">'
        })
    return jsonify({'error': 'User not found'}), 404


@app.route('/api/users')
def api_list_users():
    """API для получения списка пользователей (IDOR)"""
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, username, email FROM users")
    users = c.fetchall()
    conn.close()

    return jsonify({
        'users': [{'id': u[0], 'username': u[1], 'email': u[2]} for u in users]
    })


@app.route('/api/comments')
def api_get_comments():
    """API для получения комментариев (потенциально хранимый XSS)"""
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, post_id, comment FROM comments")
    comments = c.fetchall()
    conn.close()

    return jsonify({
        'comments': [{'id': c[0], 'post_id': c[1], 'comment': c[2]} for c in comments]
    })


@app.route('/api/admin/stats')
def api_admin_stats():
    """API для получения статистики (требует проверки прав)"""
    # УЯЗВИМОСТЬ: нет проверки, является ли пользователь админ
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM users")
    users_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM posts")
    posts_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM comments")
    comments_count = c.fetchone()[0]

    conn.close()

    return jsonify({
        'total_users': users_count,
        'total_posts': posts_count,
        'total_comments': comments_count,
        'database_path': os.path.abspath('database.db')
    })


@app.route('/api/search', methods=['GET', 'POST'])
def api_search():
    """API поиска с потенциальной SQL инъекцией"""
    query = request.args.get('q', '') or request.form.get('q', '')

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # УЯЗВИМОСТЬ: SQL инъекция через параметр
    c.execute(f"SELECT * FROM users WHERE username LIKE '%{query}%'")
    results = c.fetchall()
    conn.close()

    return jsonify({
        'query': query,
        'count': len(results),
        'results': [{'id': r[0], 'username': r[1]} for r in results]
    })


@app.route('/api/export')
def api_export_data():
    """API для экспорта данных (информационная утечка)"""
    # УЯЗВИМОСТЬ: нет аутентификации для экспорта чувствительных данных
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("SELECT * FROM users")
    users = c.fetchall()

    c.execute("SELECT * FROM posts")
    posts = c.fetchall()

    conn.close()

    return jsonify({
        'users': users,
        'posts': posts,
        'exported_at': str(datetime.now()),
        'database_info': {
            'location': os.path.abspath('database.db'),
            'size': os.path.getsize('database.db') if os.path.exists('database.db') else 0
        }
    })

# ====================== МАРШРУТЫ ======================


@app.route('/')
def index():
    """Главная страница с разными уязвимостями"""
    return render_template('index.html')


@app.route('/api-demo')
def api_demo():
    """Страница с демонстрацией API уязвимостей"""
    return render_template('api-demo.html')

# Уязвимость 7: XSS (отраженный)


@app.route('/search')
def search():
    """Уязвимый поиск с отраженным XSS"""
    query = request.args.get('q', '')
    # УЯЗВИМОСТЬ: пользовательский ввод передается в шаблон без экранирования
    return render_template('search.html', query=query, results=[])

# Уязвимость 8: XSS (хранимый) через комментарии


@app.route('/comment', methods=['POST'])
def add_comment():
    """Добавление комментариев с хранимым XSS"""
    comment = request.form.get('comment', '')
    post_id = request.form.get('post_id', 1)

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # УЯЗВИМОСТЬ: XSS через хранение неочищенных данных
    c.execute(
        f"INSERT INTO comments (post_id, comment, user) VALUES ({post_id}, '{comment}', 'anonymous')")
    conn.commit()
    conn.close()

    return redirect(url_for('posts'))

# Уязвимость 9: Path Traversal


@app.route('/file')
def get_file():
    """Уязвимая загрузка файлов (Path Traversal)"""
    filename = request.args.get('name', '')
    # УЯЗВИМОСТЬ: нет проверки на ../ (path traversal)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Уязвимость 10: Небезопасная десериализация


@app.route('/deserialize', methods=['POST'])
def deserialize_data():
    """Эндпоинт с небезопасной десериализацией"""
    data = request.form.get('data', '')
    try:
        result = vulnerable_deserialize(data)
        return f"Десериализация успешна: {result}"
    except Exception as e:
        return f"Ошибка: {str(e)}"

# Уязвимость 11: SQL инъекция


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Уязвимая форма логина с SQLi"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # УЯЗВИМОСТЬ: SQL инъекция через конкатенацию
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        c.execute(query)
        user = c.fetchone()
        conn.close()

        if user:
            session['user'] = username
            session['is_admin'] = user[4] if len(user) > 4 else 0
            return redirect(url_for('dashboard'))
        else:
            flash('Неверные учетные данные')

    return render_template('login.html')

# Уязвимость 12: IDOR (Insecure Direct Object Reference)


@app.route('/profile/<int:user_id>')
def profile(user_id):
    """Уязвимый просмотр профиля (IDOR)"""
    # УЯЗВИМОСТЬ: нет проверки прав доступа
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute(f"SELECT * FROM users WHERE id = {user_id}")
    user = c.fetchone()
    conn.close()

    if user:
        return render_template('profile.html', user=user)
    return "Пользователь не найден"

# Уязвимость 13: Command Injection


@app.route('/ping', methods=['GET', 'POST'])
def ping():
    """Уязвимый ping (Command Injection)"""
    output = ""
    if request.method == 'POST':
        host = request.form.get('host', '127.0.0.1')
        # УЯЗВИМОСТЬ: инъекция команд через shell=True
        output = vulnerable_command_injection(host)

    return render_template('ping.html', output=output)

# Уязвимость 14: XXE


@app.route('/xml', methods=['GET', 'POST'])
def parse_xml():
    """Уязвимый XML парсер (XXE)"""
    result = ""
    if request.method == 'POST':
        xml_data = request.form.get('xml', '')
        result = vulnerable_xxe(xml_data)

    return render_template('xml.html', result=result)

# Уязвимость 15: Небезопасная загрузка файлов


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    """Уязвимая загрузка файлов"""
    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            # УЯЗВИМОСТЬ: нет проверки типа файла
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            return f"Файл {filename} загружен!"

    return render_template('upload.html')

# Уязвимость 16: Информационная утечка


@app.route('/debug')
def debug_info():
    """Утечка отладочной информации"""
    # УЯЗВИМОСТЬ: раскрытие системной информации
    info = {
        'python_version': os.sys.version,
        'working_dir': os.getcwd(),
        'env_vars': dict(os.environ),
        'database_path': os.path.abspath('database.db'),
        'session_data': dict(session)
    }
    return jsonify(info)

# Уязвимость 17: CORS misconfiguration


@app.route('/api/data')
def api_data():
    """API с неправильной CORS политикой"""
    # УЯЗВИМОСТЬ: разрешаем запросы с любого домена
    resp = make_response(jsonify({'data': 'sensitive_information_here'}))
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

# Уязвимость 18: SSRF (Server Side Request Forgery)


@app.route('/fetch')
def fetch_url():
    """Уязвимый прокси (SSRF)"""
    url = request.args.get('url', '')
    if url:
        import requests
        # УЯЗВИМОСТЬ: запрос к внутренним ресурсам
        try:
            response = requests.get(url, timeout=5)
            return response.text
        except Exception as e:
            return str(e)
    return "Укажите параметр ?url="

# Уязвимость 19: Broken Authentication


@app.route('/admin')
def admin_panel():
    """Панель администратора с плохой авторизацией"""
    # УЯЗВИМОСТЬ: проверка через сессию без токена
    if session.get('is_admin'):
        return "Админ панель: FLAG{ADMIN_PANEL_ACCESS}"
    return redirect(url_for('login'))

# Уязвимость 20: Mass Assignment


@app.route('/update_profile', methods=['POST'])
def update_profile():
    """Уязвимое обновление профиля (Mass Assignment)"""
    if 'user' not in session:
        return redirect(url_for('login'))

    data = request.form.to_dict()
    # УЯЗВИМОСТЬ: прямое использование пользовательского ввода
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    set_clause = ', '.join([f"{k} = '{v}'" for k, v in data.items()])
    c.execute(
        f"UPDATE users SET {set_clause} WHERE username = '{session['user']}'")
    conn.commit()
    conn.close()

    return "Профиль обновлен!"

# ====================== ВСПОМОГАТЕЛЬНЫЕ МАРШРУТЫ ======================


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['user'])


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/posts')
def posts():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM posts")
    posts_data = c.fetchall()
    c.execute("SELECT * FROM comments")
    comments_data = c.fetchall()
    conn.close()
    return render_template('posts.html', posts=posts_data, comments=comments_data)


@app.route('/profile_page')
def profile_page():
    return render_template('profile.html')


# ====================== СОЗДАНИЕ ШАБЛОНОВ ======================

def create_templates():
    """Создание HTML шаблонов"""
    templates_dir = 'templates'
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
    
    templates = {
        'base.html': '''<!DOCTYPE html>
<html>
<head>
    <title>Flask Vulnerable App</title>
    <style>
        body { font-family: Arial; margin: 40px; background: #f0f0f0; }
        .container { max-width: 1200px; margin: auto; background: white; padding: 20px; border-radius: 10px; }
        .menu { background: #333; padding: 10px; margin-bottom: 20px; }
        .menu a { color: white; margin-right: 15px; text-decoration: none; }
        .vuln { background: #ffe6e6; padding: 10px; margin: 10px 0; border-left: 4px solid red; }
        .info { background: #e6f7ff; padding: 10px; margin: 10px 0; border-left: 4px solid blue; }
    </style>
</head>
<body>
    <div class="container">
        <div class="menu">
            <a href="/">Главная</a>
            <a href="/login">Логин</a>
            <a href="/dashboard">Дашборд</a>
            <a href="/posts">Посты</a>
            <a href="/ping">Ping</a>
            <a href="/xml">XML</a>
            <a href="/upload">Загрузка</a>
            <a href="/debug">Дебаг</a>
            <a href="/api-demo">API Demo</a>
            {% if session.user %}
                <span style="color: lightgreen;">{{ session.user }}</span>
                <a href="/logout">Выйти</a>
            {% endif %}
        </div>
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="info">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
</body>
</html>''',

        'index.html': '''{% extends "base.html" %}
{% block content %}
    <h1>🔓 Flask Vulnerable App</h1>
    <p>Этот сайт специально создан с уязвимостями для тестирования сканеров безопасности.</p>

    <div class="vuln">
        <h3>Список уязвимостей:</h3>
        <ul>
            <li>SQL Injection (login, search)</li>
            <li>XSS (отраженный и хранимый)</li>
            <li>Command Injection (ping)</li>
            <li>Path Traversal (file download)</li>
            <li>XXE (XML parsing)</li>
            <li>Небезопасная десериализация</li>
            <li>IDOR (профили пользователей)</li>
            <li>Информационная утечка</li>
            <li>CORS misconfiguration</li>
            <li>SSRF</li>
            <li>Broken Authentication</li>
            <li>Mass Assignment</li>
        </ul>
    </div>

    <h3>Быстрые тесты:</h3>
    <form action="/search">
        <input type="text" name="q" placeholder="Поиск (попробуйте <script>alert(1)</script>)" style="width: 300px;">
        <button type="submit">Искать</button>
    </form>

    <h3>SQL Injection тест:</h3>
    <form action="/login" method="POST">
        <input type="text" name="username" placeholder="Логин (попробуйте ' OR '1'='1)">
        <input type="password" name="password" placeholder="Пароль">
        <button type="submit">Войти</button>
    </form>

    <h3>Command Injection:</h3>
    <form action="/ping" method="POST">
        <input type="text" name="host" placeholder="Хост (попробуйте 127.0.0.1; whoami)">
        <button type="submit">Ping</button>
    </form>
{% endblock %}''',

        'login.html': '''{% extends "base.html" %}
{% block content %}
    <h2>Уязвимая форма входа</h2>
    <p>Примеры для SQLi:</p>
    <ul>
        <li><code>' OR '1'='1</code> - обход аутентификации</li>
        <li><code>admin' --</code> - вход как admin</li>
        <li><code>' UNION SELECT 1,2,3,4,5 --</code> - union based</li>
    </ul>

    <form method="POST">
        <input type="text" name="username" placeholder="Логин" required><br><br>
        <input type="password" name="password" placeholder="Пароль" required><br><br>
        <button type="submit">Войти</button>
    </form>
{% endblock %}''',

        'dashboard.html': '''{% extends "base.html" %}
{% block content %}
    <h2>Привет, {{ user }}!</h2>

    <div class="info">
        <h3>Доступные уязвимые функции:</h3>
        <ul>
            <li><a href="/profile/1">Профиль пользователя 1 (IDOR)</a></li>
            <li><a href="/profile/2">Профиль пользователя 2</a></li>
            <li><a href="/admin">Админ панель</a></li>
            <li><a href="/api/data">Уязвимый API</a></li>
        </ul>
    </div>

    <div class="vuln">
        <h3>Небезопасное обновление профиля (Mass Assignment):</h3>
        <form action="/update_profile" method="POST">
            <input type="text" name="email" placeholder="Новый email"><br>
            <input type="text" name="is_admin" placeholder="is_admin (0/1)"><br>
            <button type="submit">Обновить</button>
        </form>
    </div>
{% endblock %}''',

        'search.html': '''{% extends "base.html" %}
{% block content %}
    <h2>Результаты поиска для: {{ query | safe }}</h2>
    <p>Уязвимость: отраженный XSS через | safe фильтр</p>
{% endblock %}''',

        'posts.html': '''{% extends "base.html" %}
{% block content %}
    <h2>Посты и комментарии</h2>

    <div class="vuln">
        <h3>Добавить комментарий (XSS):</h3>
        <form action="/comment" method="POST">
            <textarea name="comment" rows="3" cols="50" placeholder="Введите комментарий..."></textarea><br>
            <input type="hidden" name="post_id" value="1">
            <button type="submit">Отправить</button>
        </form>
    </div>

    <h3>Комментарии:</h3>
    {% for comment in comments %}
        <div>{{ comment[2] | safe }}</div> <!-- Уязвимость: хранимый XSS -->
        <hr>
    {% endfor %}
{% endblock %}''',

        'ping.html': '''{% extends "base.html" %}
{% block content %}
    <h2>Command Injection тест</h2>

    <form method="POST">
        <input type="text" name="host" placeholder="Введите хост" value="127.0.0.1" style="width: 300px;">
        <button type="submit">Выполнить ping</button>
    </form>

    {% if output %}
        <h3>Результат:</h3>
        <pre>{{ output }}</pre>
    {% endif %}
{% endblock %}''',

        'xml.html': '''{% extends "base.html" %}
{% block content %}
    <h2>XXE тест</h2>

    <form method="POST">
        <textarea name="xml" rows="10" cols="50">
<?xml version="1.0"?>
<!DOCTYPE test [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<test>&xxe;</test>
        </textarea><br>
        <button type="submit">Парсить XML</button>
    </form>
    
    {% if result %}
        <h3>Результат:</h3>
        <pre>{{ result }}</pre>
    {% endif %}
{% endblock %}''',

        'upload.html': '''{% extends "base.html" %}
{% block content %}
    <h2>Небезопасная загрузка файлов</h2>
    
    <form method="POST" enctype="multipart/form-data">
        <input type="file" name="file">
        <button type="submit">Загрузить</button>
    </form>
    
    <h3>Скачать файл (Path Traversal):</h3>
    <form action="/file">
        <input type="text" name="name" placeholder="Имя файла (например: ../../etc/passwd)">
        <button type="submit">Скачать</button>
    </form>
{% endblock %}''',

        'profile.html': '''{% extends "base.html" %}
{% block content %}
    <h2>Профиль пользователя</h2>
    {% if user %}
        <p><strong>ID:</strong> {{ user[0] }}</p>
        <p><strong>Username:</strong> {{ user[1] }}</p>
        <p><strong>Email:</strong> {{ user[3] }}</p>
        {% if user[4] %}
            <p><strong>Роль:</strong> Администратор</p>
        {% else %}
            <p><strong>Роль:</strong> Пользователь</p>
        {% endif %}
    {% else %}
        <p>Пользователь не найден</p>
    {% endif %}
{% endblock %}''',

        'api-demo.html': '''{% extends "base.html" %}
{% block content %}
    <h2>API Vulnerability Demonstrations</h2>

    <div class="info">
        <h3>🔍 Уязвимые API эндпоинты:</h3>
        <ul>
            <li><code>GET /api/user/&lt;id&gt;</code> - XSS через API</li>
            <li><code>GET /api/users</code> - IDOR (доступ к данным всех пользователей)</li>
            <li><code>GET /api/comments</code> - Хранимый XSS в комментариях</li>
            <li><code>GET /api/admin/stats</code> - Утечка информации (без проверки прав)</li>
            <li><code>GET /api/search?q=</code> - SQL инъекция</li>
            <li><code>GET /api/export</code> - Экспорт всех данных</li>
        </ul>
    </div>

    <div class="vuln">
        <h3>Тестирование API:</h3>
        <button onclick="testAPI()">Тестировать API</button>
        <div id="api-result"></div>
    </div>

    <h3>Примеры использования:</h3>
    <pre>
// XSS через API
fetch('/api/user/1').then(r=> r.json()).then(d => console.log(d));

// SQL инъекция
fetch('/api/search?q=\' OR \'1\'=\'1').then(r=> r.json()).then(d => console.log(d));

// Получение всех данных
fetch('/api/export').then(r=> r.json()).then(d => console.log(d));
    </pre>

    <script>
        async function testAPI() {
            const resultDiv = document.getElementById('api-result');
            resultDiv.innerHTML = 'Загрузка...';
            
            try {
                const response = await fetch('/api/users');
                const data = await response.json();
                resultDiv.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
            } catch (error) {
                resultDiv.innerHTML = 'Ошибка: ' + error.message;
            }
        }
    </script>
{% endblock %}'''
    }
    
    for filename, content in templates.items():
        with open(os.path.join(templates_dir, filename), 'w', encoding='utf-8') as f:
            f.write(content)
    
    print("✅ Шаблоны успешно созданы")


def create_static_files():
    """Создание статических файлов"""
    static_dir = 'static'
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    
    # Создаем пустой CSS файл
    with open(os.path.join(static_dir, 'style.css'), 'w', encoding='utf-8') as f:
        f.write('/* Vulnerable App Styles */\n')
    
    # Создаем JS файл с уязвимостями
    with open(os.path.join(static_dir, 'vulnerability-demo.js'), 'w', encoding='utf-8') as f:
        f.write('''// Демонстрация уязвимостей
const VulnerabilityDemo = {
    // XSS через API
    xss: async function() {
        const response = await fetch('/api/user/1');
        const data = await response.json();
        console.log('XSS Payload:', data);
        document.body.innerHTML += data.bio;
    },
    
    // CORS уязвимость
    cors: function() {
        fetch('http://localhost:5012/api/data')
            .then(r => r.json())
            .then(d => console.log('CORS Data:', d));
    },
    
    // SQL инъекция
    sqli: async function() {
        const response = await fetch(`/api/search?q=' OR '1'='1`);
        const data = await response.json();
        console.log('SQL Injection Result:', data);
    },
    
    // Информационная утечка
    debug: async function() {
        const response = await fetch('/debug');
        const data = await response.json();
        console.log('Debug Info:', data);
    }
};

console.log('Vulnerability Demo Loaded. Используйте VulnerabilityDemo.xss(), .cors(), .sqli(), .debug()');
''')
    
    print("✅ Статические файлы успешно созданы")


def create_uploads_dir():
    """Создание директории для загрузок"""
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
        # Создаем тестовый файл
        with open(os.path.join('uploads', 'test.txt'), 'w') as f:
            f.write('Это тестовый файл для демонстрации Path Traversal')
    print("✅ Директория uploads создана")


# ====================== ЗАПУСК ======================

if __name__ == '__main__':
    # Создаем все необходимые директории и файлы
    create_uploads_dir()
    create_templates()
    create_static_files()
    
    print("=" * 60)
    print("🚨 Flask Vulnerable App запускается...")
    print("⚠️  ВНИМАНИЕ: Сайт содержит преднамеренные уязвимости!")
    print("⚠️  Используйте ТОЛЬКО для тестирования в изолированной среде!")
    print("📍 Запуск: http://localhost:5012")
    print("=" * 60)
    print("\n📋 Доступные уязвимости:")
    print("  • SQL Injection: http://localhost:5012/login")
    print("  • XSS: http://localhost:5012/search?q=<script>alert(1)</script>")
    print("  • Command Injection: http://localhost:5012/ping")
    print("  • Path Traversal: http://localhost:5012/file?name=../../etc/passwd")
    print("  • XXE: http://localhost:5012/xml")
    print("  • IDOR: http://localhost:5012/profile/1")
    print("  • API endpoints: http://localhost:5012/api-demo")
    print("=" * 60)
    
    # Уязвимость: запуск в debug режиме в production-like среде
    app.run(debug=True, host='0.0.0.0', port=5012)