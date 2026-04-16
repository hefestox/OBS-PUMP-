

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
                approved INTEGER DEFAULT 0,
                indicador_id INTEGER,
                take_profit_pct REAL,
                stop_loss_pct REAL,
                min_volume_ratio REAL,
                min_price_change_pct REAL,
                saldo_lucro REAL DEFAULT 0,
                saldo_indicacao REAL DEFAULT 0,
                carteira TEXT,
                plano TEXT,
                status_saque TEXT
            )''')
            # Adiciona colunas extras se não existirem
            for col, tipo in [
                ('indicador_id', 'INTEGER'),
                ('take_profit_pct', 'REAL'),
                ('stop_loss_pct', 'REAL'),
                ('min_volume_ratio', 'REAL'),
                ('min_price_change_pct', 'REAL'),
                ('saldo_lucro', 'REAL DEFAULT 0'),
                ('saldo_indicacao', 'REAL DEFAULT 0'),
                ('carteira', 'TEXT'),
                ('plano', 'TEXT'),
                ('status_saque', 'TEXT')
            ]:
                try:
                    c.execute(f'ALTER TABLE users ADD COLUMN {col} {tipo}')
                except sqlite3.OperationalError as e:
                    if 'duplicate column name' not in str(e):
                        print(f'Erro ao adicionar coluna {col}:', e)
            # Tabela de aportes e saques
            c.execute('''CREATE TABLE IF NOT EXISTS transacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                tipo TEXT,
                valor REAL,
                status TEXT,
                data TEXT,
                carteira TEXT
            )''')
            conn.commit()
    except Exception as e:
        print(f"ERRO ao inicializar banco de dados: {e}")

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
        username = request.form['username'].strip()
        password = request.form['password']
        if not username or not password:
            error = 'Usuário e senha são obrigatórios.'
        elif len(username) < 3 or len(username) > 32:
            error = 'Usuário deve ter entre 3 e 32 caracteres.'
        elif len(password) < 6:
            error = 'Senha deve ter pelo menos 6 caracteres.'
        else:
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
        username = request.form['username'].strip()
        password = request.form['password']
        indic_ref = request.form.get('indic_ref', '').strip()
        if not username or not password or not indic_ref:
            error = 'Todos os campos são obrigatórios.'
        elif len(username) < 3 or len(username) > 32:
            error = 'Usuário deve ter entre 3 e 32 caracteres.'
        elif len(password) < 6:
            error = 'Senha deve ter pelo menos 6 caracteres.'
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
            # Validação dos campos de API
            if 'api_key' in request.form:
                api_key = request.form['api_key'].strip()
                api_secret = request.form['api_secret'].strip()
                if not api_key or not api_secret:
                    print('API KEY e SECRET são obrigatórios.')
                else:
                    c.execute('UPDATE users SET api_key=?, api_secret=? WHERE id=?', (api_key, api_secret, user_id))
            # Validação dos parâmetros de estratégia
            for p in parametros:
                if p in request.form:
                    val = request.form[p]
                    try:
                        val_float = float(val)
                        if p == 'take_profit_pct' and not (0.1 <= val_float <= 20):
                            print('Take Profit fora do intervalo.')
                            continue
                        if p == 'stop_loss_pct' and not (0.1 <= val_float <= 10):
                            print('Stop Loss fora do intervalo.')
                            continue
                        if p == 'min_volume_ratio' and not (1 <= val_float <= 10):
                            print('Volume Ratio fora do intervalo.')
                            continue
                        if p == 'min_price_change_pct' and not (0.1 <= val_float <= 10):
                            print('Price Change fora do intervalo.')
                            continue
                        c.execute(f'UPDATE users SET {p}=? WHERE id=?', (val_float, user_id))
                    except ValueError:
                        print(f'Valor inválido para {p}:', val)
            conn.commit()
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('SELECT api_key, api_secret, approved, ' + ', '.join(parametros) + ', saldo_lucro, saldo_indicacao, carteira, plano, status_saque FROM users WHERE id=?', (user_id,))
        user = c.fetchone()
        # Histórico de transações
        c.execute('SELECT * FROM transacoes WHERE user_id=? ORDER BY id DESC LIMIT 20', (user_id,))
        transacoes = c.fetchall()
    indic_link = request.host_url.rstrip('/') + url_for('register') + f'?ref={username}'
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('SELECT id, username FROM users WHERE indicador_id=?', (user_id,))
        indicados1 = c.fetchall()
        indicados2 = {}
        for ind in indicados1:
            c.execute('SELECT username FROM users WHERE indicador_id=?', (ind[0],))
            indicados2[ind[1]] = [row[0] for row in c.fetchall()]
    param_dict = dict(zip(parametros, user[3:7]))
    saldo_lucro = user[7]
    saldo_indicacao = user[8]
    carteira = user[9]
    plano = user[10]
    status_saque = user[11]

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
        saldo_lucro=saldo_lucro,
        saldo_indicacao=saldo_indicacao,
        carteira=carteira,
        plano=plano,
        status_saque=status_saque,
        transacoes=transacoes,
        **param_dict
    )

@app.route('/aporte')
def aporte():
    return render_template('aporte.html')

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
        # Buscar saques pendentes
        c.execute('SELECT t.id, u.username, t.valor, t.status, t.data, t.carteira FROM transacoes t JOIN users u ON t.user_id=u.id WHERE t.tipo="saque" AND t.status="pendente" ORDER BY t.id DESC')
        saques_pendentes = c.fetchall()
    return render_template('admin.html', users=users, saques_pendentes=saques_pendentes)

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
    app.run(host="0.0.0.0", port=5000, debug=True)