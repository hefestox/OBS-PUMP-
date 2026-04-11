"""
risk_manager.py — Controle de risco e gestão de banca.
"""

import logging
from datetime import date
from binance.client import Client

log = logging.getLogger(__name__)


class RiskManager:
    def __init__(self, cfg):
        self.cfg    = cfg
        self.client = Client(cfg.API_KEY, cfg.API_SECRET, testnet=cfg.TESTNET)

        self._daily_pnl   = 0.0
        self._daily_date  = date.today()
        self._traded_today = set()

    # ── Banca ─────────────────────────────────────────────

    def get_balance(self) -> float:
        """Retorna saldo em USDT. Em paper trading, retorna banca configurada."""
        if self.cfg.PAPER_TRADING:
            return self.cfg.TOTAL_BANCA
        try:
            info = self.client.get_asset_balance(asset='USDT')
            if info is None:
                log.error("API não retornou saldo para USDT. Verifique permissões e saldo na conta SPOT.")
                print("[ERRO] API não retornou saldo para USDT. Verifique permissões e saldo na conta SPOT.")
                return 0.0
            return float(info['free'])
        except Exception as e:
            import traceback
            log.error(f"Erro ao buscar saldo: {e}")
            print("[ERRO ao buscar saldo]")
            print(e)
            traceback.print_exc()
            return 0.0

    def position_size(self) -> float:
        """Tamanho fixo por trade conforme configurado."""
        balance = self.get_balance()
        size    = min(self.cfg.TRADE_SIZE_USD, balance * 0.25)
        return round(size, 2)

    # ── Validação de entrada ───────────────────────────────

    def can_trade(self, symbol: str) -> bool:
        """Verifica se pode abrir novo trade."""
        self._reset_daily_if_needed()

        if self._daily_pnl <= -self.cfg.MAX_DAILY_LOSS_USD:
            log.warning(f"🔒 Bot travado — perda diária atingida: ${self._daily_pnl:.2f}")
            return False

        balance = self.get_balance()
        if balance < self.cfg.TRADE_SIZE_USD:
            log.warning(f"Saldo insuficiente: ${balance:.2f}")
            return False

        return True

    # ── Lógica de saída ───────────────────────────────────

    def should_exit(self, position: dict, current_price: float) -> str | None:
        """
        Avalia se deve sair da posição.
        Retorna: 'TAKE_PROFIT' | 'STOP_LOSS' | 'WEAK' | None
        """
        import time

        entry    = position['entry_price']
        size     = position['size_usd']
        opened   = position['opened_at']
        elapsed  = time.time() - opened

        pct_change = (current_price - entry) / entry * 100

        # Take profit
        if pct_change >= self.cfg.TAKE_PROFIT_PCT:
            return "TAKE_PROFIT"

        # Stop loss
        if pct_change <= -self.cfg.STOP_LOSS_PCT:
            return "STOP_LOSS"

        # Tempo máximo excedido — momentum perdido
        if elapsed >= self.cfg.MAX_HOLD_SECS:
            return "WEAK"

        return None

    def register_pnl(self, pnl: float):
        """Registra PNL do trade no acumulado diário."""
        self._reset_daily_if_needed()
        self._daily_pnl += pnl
        log.info(f"PNL diário acumulado: ${self._daily_pnl:.2f}")

    def _reset_daily_if_needed(self):
        today = date.today()
        if today != self._daily_date:
            self._daily_pnl    = 0.0
            self._traded_today = set()
            self._daily_date   = today
            log.info("Novo dia — PNL resetado.")
