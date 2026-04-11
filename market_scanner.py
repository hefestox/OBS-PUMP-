"""
market_scanner.py — Escaneia o mercado e detecta sinais de pump.
Busca automaticamente os top 50 pares USDT com mais volume.
"""

import logging
import time
from binance.client import Client
from binance.exceptions import BinanceAPIException

log = logging.getLogger(__name__)

BLACKLIST = {
    "USDCUSDT", "BUSDUSDT", "TUSDUSDT", "USDTUSDT",
    "FDUSDUSDT", "DAIUSDT", "EURUSDT", "GBPUSDT",
}


class MarketScanner:
    def __init__(self, cfg):
        self.cfg = cfg
        requests_params = {}
        if getattr(cfg, 'PROXY_ENABLED', False) and getattr(cfg, 'PROXY_URL', ''):
            requests_params['proxies'] = {
                'http':  cfg.PROXY_URL,
                'https': cfg.PROXY_URL,
            }
            log.info(f"Proxy habilitado: {cfg.PROXY_URL}")
        self.client = Client(
            cfg.API_KEY, cfg.API_SECRET,
            testnet=cfg.TESTNET,
            requests_params=requests_params or None,
        )
        self._price_cache = {}
        self._watchlist = []
        self._last_watchlist_update = 0
        self._watchlist_ttl = 300  # atualiza a cada 5 minutos

    def get_top_pairs(self) -> list[str]:
        """
        Busca os top 50 pares USDT com maior volume em 24h na Binance.
        Atualiza automaticamente a cada 5 minutos.
        """
        now = time.time()
        if self._watchlist and (now - self._last_watchlist_update) < self._watchlist_ttl:
            return self._watchlist

        try:
            tickers = self.client.get_ticker()

            usdt_pairs = [
                t for t in tickers
                if t['symbol'].endswith('USDT')
                and t['symbol'] not in BLACKLIST
                and float(t['quoteVolume']) > 0
            ]

            usdt_pairs.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
            top50 = [t['symbol'] for t in usdt_pairs[:50]]

            self._watchlist = top50
            self._last_watchlist_update = now

            log.info(f"Watchlist atualizada — Top 50 pares por volume")
            log.info(f"Top 10: {', '.join(top50[:10])}")

            return top50

        except BinanceAPIException as e:
            log.error(f"Erro ao buscar top pares: {e}")
            return self._watchlist or self.cfg.WATCHLIST

    def get_price(self, symbol: str) -> float:
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])
            self._price_cache[symbol] = price
            return price
        except BinanceAPIException as e:
            log.error(f"Erro ao buscar preco {symbol}: {e}")
            return self._price_cache.get(symbol, 0.0)

    def get_klines(self, symbol: str):
        try:
            klines = self.client.get_klines(
                symbol=symbol,
                interval=self.cfg.CANDLE_INTERVAL,
                limit=self.cfg.LOOKBACK_CANDLES + 2
            )
            return klines
        except BinanceAPIException as e:
            log.error(f"Erro ao buscar candles {symbol}: {e}")
            return []

    def analyze(self, symbol: str) -> dict | None:
        klines = self.get_klines(symbol)
        if len(klines) < self.cfg.LOOKBACK_CANDLES + 1:
            return None

        historical  = klines[:-2]
        current     = klines[-1]

        volumes     = [float(k[5]) for k in historical]
        avg_volume  = sum(volumes) / len(volumes)
        recent_high = max([float(k[2]) for k in historical[-5:]])

        current_price  = float(current[4])
        current_volume = float(current[5])
        prev_price     = float(historical[-1][4])

        price_change = (current_price - prev_price) / prev_price * 100
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0

        cond_price  = price_change  >= self.cfg.MIN_PRICE_CHANGE_PCT
        cond_volume = volume_ratio  >= self.cfg.MIN_VOLUME_RATIO
        cond_break  = current_price >  recent_high

        if cond_price and cond_volume and cond_break:
            return {
                'symbol':       symbol,
                'price':        current_price,
                'price_change': price_change,
                'volume_ratio': volume_ratio,
                'recent_high':  recent_high,
                'avg_volume':   avg_volume,
            }
        return None

    def scan(self) -> list[dict]:
        watchlist = self.get_top_pairs()
        signals   = []

        for symbol in watchlist:
            try:
                sig = self.analyze(symbol)
                if sig:
                    signals.append(sig)
            except Exception as e:
                log.error(f"Erro ao analisar {symbol}: {e}")

        signals.sort(key=lambda s: s['volume_ratio'] * s['price_change'], reverse=True)
        return signals
