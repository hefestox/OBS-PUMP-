# Script de instalação e execução para o projeto OBS Pump

# 1. Criação do ambiente virtual
python -m venv .venv

# 2. Ativação do ambiente virtual (Windows)
.\.venv\Scripts\Activate.ps1

# 3. Atualização de pip, setuptools e wheel
.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel

# 4. Instalação das dependências do projeto
.venv\Scripts\pip.exe install -r requirements.txt

# 5. Instalação manual de dependências extras para proxy SOCKS e compatibilidade
.venv\Scripts\pip.exe install requests[socks] PySocks

# 6. Instalação da versão correta do python-binance
.venv\Scripts\pip.exe install python-binance==1.0.19

# 7. Teste de importação do binance
.venv\Scripts\python.exe -c "from binance.client import Client; print('OK')"

# 8. Execução do bot
.venv\Scripts\python.exe bot.py
