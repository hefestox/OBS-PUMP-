
print("INICIANDO FLASK - app.py")


from flask import Flask, render_template_string, request, redirect, url_for, session
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
        print("Banco de dados inicializado com sucesso.")
    except Exception as e:
        print(f"ERRO ao inicializar banco de dados: {e}")

# --- Templates ---
TEMPLATE_LOGIN = '''
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Login - OBS Pump Sniper Bot</title>
    <style>
        body { background: #181818; color: #f1f1f1; font-family: 'Segoe UI', Arial, sans-serif; }
        .login-box { max-width: 350px; margin: 60px auto; background: #232323; padding: 32px 28px 24px 28px; border-radius: 12px; box-shadow: 0 0 16px #000a; }
        h2 { color: #00e676; text-align: center; margin-bottom: 24px; }
        label { display: block; margin-bottom: 6px; color: #00e676; }
        input[type=text], input[type=password] { width: 100%; padding: 8px 10px; margin-bottom: 16px; border: none; border-radius: 6px; background: #181818; color: #f1f1f1; font-size: 1em; }
        button { width: 100%; background: #00e676; color: #181818; border: none; border-radius: 6px; padding: 10px; font-size: 1.1em; font-weight: bold; cursor: pointer; margin-bottom: 10px; }
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
Usuário: <input name="username" required><br>
Senha: <input name="password" type="password" required><br>
Link de indicação (obrigatório): <input name="indic_ref" value="{{ ref or '' }}" required><br>
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
        .dash-box { max-width: 400px; margin: 60px auto 24px auto; background: #232323; padding: 32px 28px 24px 28px; border-radius: 12px; box-shadow: 0 0 16px #000a; }
        h2, h3 { color: #00e676; text-align: center; }
        label { display: block; margin-bottom: 6px; color: #00e676; }
        input[type=text], input[type=number] { width: 100%; padding: 8px 10px; margin-bottom: 16px; border: none; border-radius: 6px; background: #181818; color: #f1f1f1; font-size: 1em; box-sizing: border-box; }
        button { width: 100%; background: #00e676; color: #181818; border: none; border-radius: 6px; padding: 10px; font-size: 1.1em; font-weight: bold; cursor: pointer; margin-bottom: 10px; }
        button:hover { background: #00bfae; }
        .status-aprovado { color: #00e676; font-weight: bold; }
        .status-pendente { color: #ffea00; font-weight: bold; }
        .links { text-align: center; margin-top: 18px; }
        .links a { color: #00e676; text-decoration: none; margin: 0 10px; }
        .links a:hover { text-decoration: underline; }
        .planos, .indicacao, .rede { background: #181818; border-radius: 12px; box-shadow: 0 0 10px #0007; margin: 24px auto 0 auto; padding: 18px 16px 10px 16px; max-width: 500px; }
        .planos h3, .indicacao h3, .rede h3 { color: #00e676; margin-top: 0; }
        .plano-tabela { width: 100%; margin-bottom: 10px; border-collapse: collapse; }
        .plano-tabela th, .plano-tabela td { border: 1px solid #333; padding: 7px 4px; text-align: center; }
        .plano-tabela th { background: #222; color: #00e676; }
        .mais-popular { color: #00e676; font-weight: bold; font-size: 0.95em; }
        .usdt { color: #00e676; font-weight: bold; }
        .binario { color: #00e676; font-weight: bold; }
        .indic-link-box { background: #232323; border-radius: 8px; padding: 10px; margin: 10px 0; text-align: center; }
        .indic-link { color: #00e676; font-weight: bold; word-break: break-all; }
    </style>
</head>
<body>
<div class="dash-box">
    <h2>Painel do Usuário</h2>

    <form method="post" style="margin-bottom:18px;">
        <h3 style="margin-bottom:10px;">Configuração de Estratégia</h3>
        <label>Take Profit (%)</label>
        <input name="take_profit_pct" type="number" min="0.1" max="20" step="0.1" value="{{ take_profit_pct or 4.0 }}">
        <label>Stop Loss (%)</label>
        <input name="stop_loss_pct" type="number" min="0.1" max="10" step="0.1" value="{{ stop_loss_pct or 1.0 }}">
        <label>Mín. Volume Ratio</label>
        <input name="min_volume_ratio" type="number" min="1" max="10" step="0.1" value="{{ min_volume_ratio or 2.0 }}">
        <label>Mín. Price Change (%)</label>
        <input name="min_price_change_pct" type="number" min="0.1" max="10" step="0.1" value="{{ min_price_change_pct or 1.5 }}">
        <button type="submit">Salvar Estratégia</button>
    </form>

    <form method="post" style="margin-bottom:18px;">
        <label for="api_key">API KEY:</label>
        <input name="api_key" id="api_key" value="{{api_key or ''}}" type="text">
        <label for="api_secret">API SECRET:</label>
        <input name="api_secret" id="api_secret" value="{{api_secret or ''}}" type="text">
        <button type="submit">Salvar API</button>
    </form>

    <form action="/aporte" method="get" style="margin-bottom:18px; text-align:center;">
        <button type="submit">Fazer Aporte / Assinatura</button>
    </form>

    <p>Status: {% if approved %}<span class="status-aprovado">Aprovado</span>{% else %}<span class="status-pendente">Aguardando aprovação</span>{% endif %}</p>

    <div class="indic-link-box">
        <div>Seu link de indicação:</div>
        <div class="indic-link">{{ indic_link }}</div>
        <div style="font-size:0.95em; color:#aaa;">Compartilhe para ganhar 20% de comissão em USDT!</div>
    </div>

    <div class="links">
        <a href="/logout">Sair</a>
        <a href="http://127.0.0.1:5001" target="_blank">Ir para o Dashboard do Bot</a>
    </div>
</div>

<div class="rede">
    <h3>Sua Rede Binária</h3>
    <div style="font-size:0.97em; margin-bottom:8px;">Veja seus indicados diretos e indiretos (nível 2):</div>
    {% if indicados1 %}
        <ul>
        {% for ind in indicados1 %}
            <li><b>{{ ind[1] }}</b>
                {% if indicados2[ind[1]] %}
                    <ul>
                    {% for sub in indicados2[ind[1]] %}
                        <li>{{ sub }}</li>
                    {% endfor %}
                    </ul>
                {% endif %}
            </li>
        {% endfor %}
        </ul>
    {% else %}
        <div style="color:#aaa;">Nenhum indicado ainda.</div>
    {% endif %}
</div>

<div class="planos">
    <h3>Planos & Assinaturas</h3>
    <table class="plano-tabela">
        <tr><th>Plano</th><th>Valor</th><th>Banca</th><th>Benefícios</th></tr>
        <tr><td>Starter</td><td>R$97<br><span class="usdt">17 USDT</span></td><td>até 100 USDT</td><td>Bot pronto, Dashboard, Suporte WhatsApp</td></tr>
        <tr><td class="mais-popular">Pro (Mais Popular)</td><td>R$197<br><span class="usdt">35 USDT</span></td><td>até 500 USDT</td><td>Notificações Telegram, Relatório diário, Grupo VIP, Suporte 24h</td></tr>
        <tr><td>Elite</td><td>R$497<br><span class="usdt">87 USDT</span></td><td>Ilimitada</td><td>VPS dedicada, Parâmetros customizados, Sessão 1:1, Vitalício</td></tr>
    </table>
    <div style="font-size:0.98em; color:#ffea00; margin-bottom:8px;">20% de comissão por indicação em USDT!</div>
</div>

<div class="indicacao">
    <h3>Programa de Indicação Binário <span class="binario">20% em USDT</span></h3>
    <p>Indique amigos e ganhe <b>20% de comissão</b> em USDT sobre cada assinatura paga.<br>
    Sistema binário: cada novo indicado gera comissão automática, sem limite de indicações.</p>
    <ul>
        <li>Starter: 3.4 USDT/mês por indicado</li>
        <li>Pro: 7 USDT/mês por indicado</li>
        <li>Elite: 17.4 USDT/mês por indicado</li>
    </ul>
    <div style="font-size:0.97em; color:#aaa;">Pagamentos automáticos em USDT, rastreados pelo sistema.</div>
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
            if user and bcrypt.checkpw(password.encode('utf-8'), user[1].encode('utf-8')):
                session['user_id'] = user[0]
                session['username'] = username
                return redirect(url_for('dashboard'))
            else:
                error = 'Usuário ou senha inválidos.'
    return render_template_string(TEMPLATE_LOGIN, error=error)

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
    return render_template_string(TEMPLATE_REGISTER, error=error, ref=ref)

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

    return render_template_string(
        TEMPLATE_DASH + """
<div style='background:#232323;color:#fff;padding:16px;margin:24px auto;max-width:600px;border-radius:10px;'>
  <h3 style='color:#00e676;'>TODOS OS PARES DISPONÍVEIS NA BINANCE</h3>
  <ul>
    {% for p in all_pairs %}<li>{{p}}</li>{% endfor %}
  </ul>
</div>
""",
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
    return render_template_string(TEMPLATE_ADMIN, users=users)

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