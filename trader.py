"""
trader.py — Executa ordens na Binance (real ou simulado).
"""

import time
import logging
from binance.client import Client
from binance.exceptions import BinanceAPIException

log = logging.getLogger(__name__)


class Trader:
    def __init__(self, cfg):
        self.cfg    = cfg
        # Sem proxy para evitar erro de conexão
        self.client = Client(cfg.API_KEY, cfg.API_SECRET, testnet=cfg.TESTNET)
        self._paper_positions = {}   # Para simulação

    # ── Abertura ──────────────────────────────────────────


    def open_position(self, symbol: str, size_usd: float, signal: dict) -> dict | None:
        """
        Abre posição de compra (SPOT market order).
        Retorna dict com dados da posição, ou None em caso de falha.
        Agora checa o valor mínimo (notional) exigido pela Binance antes de tentar abrir ordem real.
        """
        entry_price = signal['price']

        if self.cfg.PAPER_TRADING:
            position = {
                'symbol':      symbol,
                'entry_price': entry_price,
                'size_usd':    size_usd,
                'qty':         size_usd / entry_price,
                'opened_at':   time.time(),
                'signal':      signal,
                'paper':       True,
            }
            log.info(f"[PAPER] COMPRA {symbol} @ ${entry_price:.4f} — ${size_usd:.2f}")
            return position

        # ── Real ──────────────────────────────────────────
        try:
            info     = self.client.get_symbol_info(symbol)
            qty      = self._calc_qty(symbol, size_usd, entry_price, info)

            # Checa valor mínimo (notional)
            min_notional = None
            for f in info.get('filters', []):
                if f['filterType'] == 'MIN_NOTIONAL':
                    min_notional = float(f['minNotional'])
                    break
            notional = qty * entry_price
            if min_notional is not None and notional < min_notional:
                log.warning(f"Ordem ignorada em {symbol}: valor {notional:.2f} USDT abaixo do mínimo ({min_notional:.2f} USDT)")
                return None

            if qty <= 0:
                log.warning(f"Quantidade inválida para {symbol}: {qty}")
                return None

            order = self.client.order_market_buy(symbol=symbol, quantity=qty)

            filled_price = float(order['fills'][0]['price']) if order.get('fills') else entry_price
            filled_qty   = float(order['executedQty'])

            position = {
                'symbol':      symbol,
                'entry_price': filled_price,
                'size_usd':    filled_qty * filled_price,
                'qty':         filled_qty,
                'opened_at':   time.time(),
                'order_id':    order['orderId'],
                'signal':      signal,
                'paper':       False,
            }
            return position

        except BinanceAPIException as e:
            log.error(f"Erro ao abrir posição {symbol}: {e}")
            return None

    # ── Fechamento ────────────────────────────────────────

    def close_position(self, position: dict, current_price: float, reason: str = "") -> float:
        """
        Fecha posição. Retorna PNL em USD.
        """
        entry = position['entry_price']
        qty   = position['qty']
        pnl   = (current_price - entry) * qty

        if position.get('paper'):
            log.info(
                f"[PAPER] VENDA {position['symbol']} @ ${current_price:.4f} | "
                f"PNL: ${pnl:+.2f} | {reason}"
            )
            return pnl

        # ── Real ──────────────────────────────────────────
        symbol = position['symbol']
        try:
            info       = self.client.get_symbol_info(symbol)
            lot_step   = self._get_lot_step(info)
            qty_fmt    = self._floor_qty(qty, lot_step)

            order = self.client.order_market_sell(symbol=symbol, quantity=qty_fmt)
            sold_price = float(order['fills'][0]['price']) if order.get('fills') else current_price
            real_pnl   = (sold_price - entry) * qty_fmt

            log.info(
                f"VENDA {symbol} @ ${sold_price:.4f} | "
                f"PNL: ${real_pnl:+.2f} | {reason}"
            )
            return real_pnl

        except BinanceAPIException as e:
            log.error(f"Erro ao fechar posição {symbol}: {e}")
            return 0.0

    # ── Helpers ───────────────────────────────────────────

    def _calc_qty(self, symbol: str, size_usd: float, price: float, info: dict) -> float:
        raw_qty  = size_usd / price
        lot_step = self._get_lot_step(info)
        return self._floor_qty(raw_qty, lot_step)

    def _get_lot_step(self, info: dict) -> float:
        for f in info.get('filters', []):
            if f['filterType'] == 'LOT_SIZE':
                return float(f['stepSize'])
        return 0.001

    def _floor_qty(self, qty: float, step: float) -> float:
        if step <= 0:
            return round(qty, 6)
        precision = len(str(step).rstrip('0').split('.')[-1])
        return round(int(qty / step) * step, precision)
