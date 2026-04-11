"""
config.py — Configurações do OBS Pump Sniper Bot
"""

class Config:
    # ─── BINANCE API ───────────────────────────────────────
    API_KEY    = "6cE4SJ3jA5j2pJY4O8qK9YGbmlGeJzP4g6yOjjaU4eLokd9a17RGbcarzlfNQeEP"
    API_SECRET = "Waw8azHG9JYYMYMBgGiFCWXFJ8p77GDvU17LxysP518FznTICUiP1dQRbwOn9s88"
    TESTNET    = True           # Testnet habilitado — opera no sandbox da Binance (sem dinheiro real)

    # ─── MODO ──────────────────────────────────────────────
    PAPER_TRADING = False        # True = simula sem dinheiro real
                                # False = opera de verdade

    # ─── BANCA E RISCO ─────────────────────────────────────
    TOTAL_BANCA          = 51.0    # Saldo total em USDT
    TRADE_SIZE_USD       = 10.0    # Tamanho de cada trade em USDT
    MAX_OPEN_POSITIONS   = 5       # Máximo de posições simultâneas
    MAX_DAILY_LOSS_USD   = 5.0     # Trava o bot se perder mais que isso no dia

    # ─── SAÍDA ─────────────────────────────────────────────
    TAKE_PROFIT_PCT = 4.0   # Alvo de lucro (%)
    STOP_LOSS_PCT   = 2.0   # Stop de perda (%)
    MAX_HOLD_SECS   = 300   # Sai forçado após 5 minutos

    # ─── DETECÇÃO DE PUMP ──────────────────────────────────
    MIN_PRICE_CHANGE_PCT = 0.5   # Variação mínima de preço em % (janela recente)
    MIN_VOLUME_RATIO     = 1.2   # Volume atual deve ser Nx maior que a média
    LOOKBACK_CANDLES     = 20    # Candles usados para calcular média de volume
    CANDLE_INTERVAL      = "5m"  # Intervalo dos candles

    # ─── SCANNER ───────────────────────────────────────────
    SCAN_INTERVAL = 5          # Segundos entre cada scan

    WATCHLIST = [
        "ZAMUSDT", "INJUSDT", "SUIUSDT", "DOGEUSDT",
        "AVAXUSDT", "SOLUSDT", "ARBUSDT", "OPUSDT",
        "APTUSDT", "BNBUSDT", "LINKUSDT", "FETUSDT",
    ]
