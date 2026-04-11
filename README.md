# 🤖 OBS PUMP SNIPER BOT — Binance

Bot de scalping que detecta pumps em tempo real e opera automaticamente.

---

## 📁 Estrutura

```
pump_sniper/
├── bot.py            ← Ponto de entrada principal
├── config.py         ← TODAS as configurações ficam aqui
├── market_scanner.py ← Detecta sinais de pump
├── trader.py         ← Executa ordens na Binance
├── risk_manager.py   ← Controle de risco e banca
├── requirements.txt  ← Dependências
└── pump_sniper.log   ← Log gerado ao rodar
```

---

## ⚙️ Instalação

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar API da Binance em config.py
API_KEY    = "sua_key_aqui"
API_SECRET = "seu_secret_aqui"

# 3. Rodar em modo PAPER primeiro (simulado)
python bot.py
```

---

## 🔑 API Binance

1. Acesse https://www.binance.com/pt-BR/my/settings/api-management
2. Crie uma API Key
3. Permissões necessárias: **Leitura** + **Spot Trading**
4. **NÃO habilite saques**
5. Cole a Key e Secret em `config.py`

---

## ⚙️ Principais configurações (`config.py`)

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `PAPER_TRADING` | `True` | Simula sem dinheiro real |
| `TRADE_SIZE_USD` | `10.0` | Valor por trade em USDT |
| `MAX_OPEN_POSITIONS` | `3` | Máximo de posições ao mesmo tempo |
| `TAKE_PROFIT_PCT` | `4.0` | Sai com +4% de lucro |
| `STOP_LOSS_PCT` | `2.0` | Sai com -2% de perda |
| `MAX_HOLD_SECS` | `120` | Força saída após 2 minutos |
| `MIN_PRICE_CHANGE_PCT` | `1.5` | Variação mínima para entrar |
| `MIN_VOLUME_RATIO` | `2.5` | Volume deve ser 2.5x acima da média |
| `MAX_DAILY_LOSS_USD` | `5.0` | Para o bot se perder $5 no dia |

---

## 🧠 Lógica de Entrada

O bot só compra quando os 3 critérios são atendidos simultaneamente:

1. **Preço** subiu ≥ `MIN_PRICE_CHANGE_PCT`% nos últimos candles
2. **Volume** atual é ≥ `MIN_VOLUME_RATIO`x acima da média dos últimos 20 candles
3. **Rompimento**: preço fechou acima do topo recente dos últimos 5 candles

---

## 📉 Lógica de Saída

Sai automaticamente quando qualquer condição for atingida:

- ✅ Lucro ≥ `TAKE_PROFIT_PCT`%
- 🛑 Perda ≥ `STOP_LOSS_PCT`%
- ⏱️ Tempo máximo (`MAX_HOLD_SECS`) excedido
- 🔒 Perda diária acumulada ≥ `MAX_DAILY_LOSS_USD`

---

## ⚠️ Aviso

Este bot é fornecido para fins educacionais.
Trading de criptomoedas envolve risco de perda total do capital.
**Sempre teste em PAPER_TRADING antes de operar com dinheiro real.**
