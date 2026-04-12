#!/bin/bash
# Script para rodar o bot e o painel web em background na VPS

# Ativar venv se existir
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
fi

# Instalar dependências
pip install -r requirements.txt

# Iniciar o bot em background
nohup python bot.py > bot.log 2>&1 &

# Iniciar o painel web (dashboard_server) em background
nohup gunicorn -w 2 -b 0.0.0.0:5001 dashboard_server:app > dashboard.log 2>&1 &

echo "Bot e painel web iniciados em background."
