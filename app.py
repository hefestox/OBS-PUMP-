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
<!DOCTYPE html><html><head><title>Login</title></head><body>
<h2>Login</h2>
<form method="post">
Usuário: <input name="username"><br>
Senha: <input name="password" type="password"><br>
<button type="submit">Entrar</button>
</form>
<a href="/register">Cadastrar</a>
{% if error %}<p style="color:red">{{error}}</p>{% endif %}
</body></html>
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
<!DOCTYPE html><html><head><title>Painel</title></head><body>
<h2>Painel do Usuário</h2>
<form method="post">
API KEY: <input name="api_key" value="{{api_key or ''}}"><br>
API SECRET: <input name="api_secret" value="{{api_secret or ''}}"><br>
<button type="submit">Salvar</button>
</form>
<p>Status: {% if approved %}<b style="color:green">Aprovado</b>{% else %}<b style="color:orange">Aguardando aprovação</b>{% endif %}</p>
<a href="/logout">Sair</a>
</body></html>
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
