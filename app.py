
print("INICIANDO FLASK - app.py")


from flask import Flask, render_template, render_template_string, request, redirect, url_for, session
import os
import sqlite3
import bcrypt

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'supersecret')
DB_PATH = 'users.db'

# --- Banco de dados ---
def init_db():
    try:
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
            for col in ['indicador_id', 'take_profit_pct', 'stop_loss_pct', 'min_volume_ratio', 'min_price_change_pct']:
                try:
                    c.execute(f'ALTER TABLE users ADD COLUMN {col} REAL')
                except sqlite3.OperationalError as e:
                    if 'duplicate column name' not in str(e):
                        print(f'Erro ao adicionar coluna {col}:', e)
            conn.commit()
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
            if user and bcrypt.checkpw(password.encode('utf-8'), user[1].encode('utf-8')):
                session['user_id'] = user[0]
                session['username'] = username
                return redirect(url_for('dashboard'))
            else:
                error = 'Usuário ou senha inválidos.'
    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    ref = request.args.get('ref')
    indicador_id = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        indic_ref = request.form.get('indic_ref', '').strip()
        if not indic_ref:
            error = 'O link de indicação é obrigatório.'
        else:
            if indic_ref.startswith('http') and 'ref=' in indic_ref:
                indic_username = indic_ref.split('ref=')[-1].split('&')[0]
            else:
                indic_username = indic_ref
            with sqlite3.connect(DB_PATH) as conn:
                c = conn.cursor()
                c.execute('SELECT id FROM users WHERE username=?', (indic_username,))
                row = c.fetchone()
                if row:
                    indicador_id = row[0]
                else:
                    error = 'Link de indicação inválido.'
        if not error:
            try:
                hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                with sqlite3.connect(DB_PATH) as conn:
                    c = conn.cursor()
                    c.execute('INSERT INTO users (username, password, indicador_id) VALUES (?, ?, ?)', (username, hashed.decode('utf-8'), indicador_id))
                    conn.commit()
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                error = 'Usuário já existe.'
    return render_template('register.html', error=error, ref=ref)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    username = session.get('username')
    parametros = ['take_profit_pct', 'stop_loss_pct', 'min_volume_ratio', 'min_price_change_pct']
    if request.method == 'POST':
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            if 'api_key' in request.form:
                api_key = request.form['api_key']
                api_secret = request.form['api_secret']
                c.execute('UPDATE users SET api_key=?, api_secret=? WHERE id=?', (api_key, api_secret, user_id))
            for p in parametros:
                if p in request.form:
                    c.execute(f'UPDATE users SET {p}=? WHERE id=?', (request.form[p], user_id))
            conn.commit()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('SELECT api_key, api_secret, approved, ' + ', '.join(parametros) + ' FROM users WHERE id=?', (user_id,))
        user = c.fetchone()
    indic_link = request.host_url.rstrip('/') + url_for('register') + f'?ref={username}'
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('SELECT id, username FROM users WHERE indicador_id=?', (user_id,))
        indicados1 = c.fetchall()
        indicados2 = {}
        for ind in indicados1:
            c.execute('SELECT username FROM users WHERE indicador_id=?', (ind[0],))
            indicados2[ind[1]] = [row[0] for row in c.fetchall()]
    param_dict = dict(zip(parametros, user[3:]))

    # NOVO: Exibir todos os pares disponíveis da Binance
    try:
        from binance.client import Client
        api_key = user[0]
        api_secret = user[1]
        client = Client(api_key, api_secret)
        tickers = client.get_ticker()
        # Exibe todos os pares
        all_pairs = [t['symbol'] for t in tickers]
    except Exception as e:
        all_pairs = [f'Erro ao buscar pares: {e}']

        return render_template(
                'dashboard.html',
                api_key=user[0],
                api_secret=user[1],
                approved=user[2],
                indic_link=indic_link,
                username=username,
                indicados1=indicados1,
                indicados2=indicados2,
                all_pairs=all_pairs,
                **param_dict
        )

@app.route('/aporte')
def aporte():
    return '''
    <html><head><title>Aporte / Assinatura</title></head>
    <body style="background:#181818;color:#f1f1f1;font-family:Segoe UI,Arial,sans-serif;">
    <div style="max-width:420px;margin:40px auto;background:#232323;padding:28px 22px 18px 22px;border-radius:12px;box-shadow:0 0 16px #000a;">
    <h2 style="color:#00e676;">Aporte / Assinatura</h2>
    <p>Para ativar seu acesso ao bot, envie o valor do plano desejado para o endereço USDT (TRC20 ou ERC20):</p>
    <div style="background:#181818;padding:12px 8px;border-radius:8px;margin:12px 0 18px 0;font-size:1.1em;word-break:break-all;color:#00e676;">
        0xBa4D5e87e8bcaA85bF29105AB3171b9fDb2eF9dd
    </div>
    <ul style="color:#ffea00;font-size:1.05em;">
        <li>Starter: 17 USDT</li>
        <li>Pro: 35 USDT</li>
        <li>Elite: 87 USDT</li>
    </ul>
    <p style="margin-top:18px;">Após o envio, envie o comprovante para o suporte ou aguarde aprovação do admin.</p>
    <a href="/dashboard" style="color:#00e676;">Voltar ao painel</a>
    </div></body></html>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin')
def admin():
    if session.get('username') != 'admin':
        return redirect(url_for('login'))
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM users')
        users = c.fetchall()
    return render_template('admin.html', users=users)

@app.route('/admin/approve/<int:user_id>')
def admin_approve(user_id):
    if session.get('username') != 'admin':
        return redirect(url_for('login'))
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('UPDATE users SET approved=1 WHERE id=?', (user_id,))
        conn.commit()
    return redirect(url_for('admin'))

@app.route('/admin/delete/<int:user_id>')
def admin_delete(user_id):
    if session.get('username') != 'admin':
        return redirect(url_for('login'))
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('DELETE FROM users WHERE id=?', (user_id,))
        conn.commit()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)