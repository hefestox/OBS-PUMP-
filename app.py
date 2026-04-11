from flask import Flask, render_template_string, request, redirect, url_for, session
import os
import sqlite3

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'supersecret')
DB_PATH = 'users.db'

# --- Banco de dados ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            api_key TEXT,
            api_secret TEXT,
            approved INTEGER DEFAULT 0
        )''')
        conn.commit()

init_db()

# --- Templates ---
TEMPLATE_LOGIN = '''
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Login - OBS Pump Sniper Bot</title>
    <style>
        body { background: #181818; color: #f1f1f1; font-family: 'Segoe UI', Arial, sans-serif; }
        .login-box {
            max-width: 350px;
            margin: 60px auto;
            background: #232323;
            padding: 32px 28px 24px 28px;
            border-radius: 12px;
            box-shadow: 0 0 16px #000a;
        }
        h2 { color: #00e676; text-align: center; margin-bottom: 24px; }
        label { display: block; margin-bottom: 6px; color: #00e676; }
        input[type=text], input[type=password] {
            width: 100%;
            padding: 8px 10px;
            margin-bottom: 16px;
            border: none;
            border-radius: 6px;
            background: #181818;
            color: #f1f1f1;
            font-size: 1em;
        }
        button {
            width: 100%;
            background: #00e676;
            color: #181818;
            border: none;
            border-radius: 6px;
            padding: 10px;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            margin-bottom: 10px;
        }
        button:hover { background: #00bfae; }
        .link { text-align: center; margin-top: 10px; }
        .link a { color: #00e676; text-decoration: none; }
        .link a:hover { text-decoration: underline; }
        .error { color: #ff5252; text-align: center; margin-top: 10px; }
    </style>
</head>
<body>
<div class="login-box">
    <h2>Login</h2>
    <form method="post">
        <label for="username">Usuário:</label>
        <input name="username" id="username" type="text" required>
        <label for="password">Senha:</label>
        <input name="password" id="password" type="password" required>
        <button type="submit">Entrar</button>
    </form>
    <div class="link">
        <a href="/register">Cadastrar-se</a>
    </div>
    {% if error %}<div class="error">{{error}}</div>{% endif %}
</div>
</body>
</html>
'''

TEMPLATE_REGISTER = '''
<!DOCTYPE html><html><head><title>Cadastro</title></head><body>
<h2>Cadastro</h2>
<form method="post">
Usuário: <input name="username"><br>
Senha: <input name="password" type="password"><br>
<button type="submit">Cadastrar</button>
</form>
<a href="/login">Login</a>
{% if error %}<p style="color:red">{{error}}</p>{% endif %}
</body></html>
'''

TEMPLATE_DASH = '''
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Painel do Usuário</title>
    <style>
        body { background: #181818; color: #f1f1f1; font-family: 'Segoe UI', Arial, sans-serif; }
        .dash-box {
            max-width: 400px;
            margin: 60px auto;
            background: #232323;
            padding: 32px 28px 24px 28px;
            border-radius: 12px;
            box-shadow: 0 0 16px #000a;
        }
        h2 { color: #00e676; text-align: center; margin-bottom: 24px; }
        label { display: block; margin-bottom: 6px; color: #00e676; }
        input[type=text], input[type=password] {
            width: 100%;
            padding: 8px 10px;
            margin-bottom: 16px;
            border: none;
            border-radius: 6px;
            background: #181818;
            color: #f1f1f1;
            font-size: 1em;
        }
        button {
            width: 100%;
            background: #00e676;
            color: #181818;
            border: none;
            border-radius: 6px;
            padding: 10px;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            margin-bottom: 10px;
        }
        button:hover { background: #00bfae; }
        .status-aprovado { color: #00e676; font-weight: bold; }
        .status-pendente { color: #ffea00; font-weight: bold; }
        .links { text-align: center; margin-top: 18px; }
        .links a { color: #00e676; text-decoration: none; margin: 0 10px; }
        .links a:hover { text-decoration: underline; }
    </style>
</head>
<body>
<div class="dash-box">
    <h2>Painel do Usuário</h2>
    <form method="post">
        <label for="api_key">API KEY:</label>
        <input name="api_key" id="api_key" value="{{api_key or ''}}" type="text" required>
        <label for="api_secret">API SECRET:</label>
        <input name="api_secret" id="api_secret" value="{{api_secret or ''}}" type="text" required>
        <button type="submit">Salvar</button>
    </form>
    <p>Status: {% if approved %}<span class="status-aprovado">Aprovado</span>{% else %}<span class="status-pendente">Aguardando aprovação</span>{% endif %}</p>
    <div class="links">
        <a href="/logout">Sair</a>
        <a href="http://127.0.0.1:5001" target="_blank">Ir para o Dashboard do Bot</a>
    </div>
</div>
</body>
</html>
'''

TEMPLATE_ADMIN = '''
<!DOCTYPE html><html><head><title>Admin</title></head><body>
<h2>Painel Admin</h2>
<table border=1><tr><th>ID</th><th>Usuário</th><th>Aprovado</th><th>Ação</th></tr>
{% for u in users %}
<tr><td>{{u[0]}}</td><td>{{u[1]}}</td><td>{{'Sim' if u[5] else 'Não'}}</td>
<td>
    {% if not u[5] %}<a href="/admin/approve/{{u[0]}}">Aprovar</a>{% endif %}
    <a href="/admin/delete/{{u[0]}}">Excluir</a>
</td></tr>
{% endfor %}
</table>
<a href="/logout">Sair</a>
</body></html>
'''

# --- Rotas ---
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('SELECT id, password FROM users WHERE username=?', (username,))
            user = c.fetchone()
            if user and user[1] == password:
                session['user_id'] = user[0]
                session['username'] = username
                return redirect(url_for('dashboard'))
            else:
                error = 'Usuário ou senha inválidos.'
    return render_template_string(TEMPLATE_LOGIN, error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
                conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            error = 'Usuário já existe.'
    return render_template_string(TEMPLATE_REGISTER, error=error)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        if request.method == 'POST':
            api_key = request.form['api_key']
            api_secret = request.form['api_secret']
            c.execute('UPDATE users SET api_key=?, api_secret=? WHERE id=?', (api_key, api_secret, user_id))
            conn.commit()
        c.execute('SELECT api_key, api_secret, approved FROM users WHERE id=?', (user_id,))
        user = c.fetchone()
    return render_template_string(TEMPLATE_DASH, api_key=user[0], api_secret=user[1], approved=user[2])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
def admin():
    # Simples: só permite acesso se username for 'admin'
    if session.get('username') != 'admin':
        return redirect(url_for('login'))
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM users')
        users = c.fetchall()
    return render_template_string(TEMPLATE_ADMIN, users=users)

@app.route('/admin/approve/<int:user_id>')
def approve(user_id):
    if session.get('username') != 'admin':
        return redirect(url_for('login'))
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('UPDATE users SET approved=1 WHERE id=?', (user_id,))
        conn.commit()
    return redirect(url_for('admin'))

@app.route('/admin/delete/<int:user_id>')
def delete(user_id):
    if session.get('username') != 'admin':
        return redirect(url_for('login'))
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('DELETE FROM users WHERE id=?', (user_id,))
        conn.commit()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
