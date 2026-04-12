"""
market_scanner.py — Escaneia o mercado e detecta sinais de pump.
Busca automaticamente os top 50 pares USDT com mais volume.
"""

import logging
import time
import requests
from binance.client import Client
from binance.exceptions import BinanceAPIException

log = logging.getLogger(__name__)

BLACKLIST = {
    "USDCUSDT", "BUSDUSDT", "TUSDUSDT", "USDTUSDT",
    "FDUSDUSDT", "DAIUSDT", "EURUSDT", "GBPUSDT",
}

# ---------------------------------------------------------------------------
# Free SOCKS5 proxy pool — rotated on each Client build attempt.
# These are well-known public SOCKS5 relays; the list is tried in order and
# the first one that successfully reaches the Binance API is kept.  When a
# proxy stops working the scanner rebuilds the client with the next one.
# ---------------------------------------------------------------------------
_FREE_PROXIES = [
    "socks5://72.195.34.58:4145",
    "socks5://72.195.34.35:4145",
    "socks5://98.162.25.7:31653",
    "socks5://98.162.96.41:4145",
    "socks5://192.111.139.165:4145",
    "socks5://192.111.137.37:18762",
    "socks5://184.178.172.14:4145",
    "socks5://184.178.172.28:15294",
    "socks5://67.201.33.9:25283",
    "socks5://proxy.torguard.org:1080",
]


def _build_client(api_key: str, api_secret: str, testnet: bool,
                  proxy_url: str = "") -> tuple["Client", str]:
    """
    Build a Binance Client, routing traffic through a proxy when available.

    Priority:
      1. Explicit ``proxy_url`` (from PROXY_URL env var / cfg.PROXY_URL).
      2. Rotate through ``_FREE_PROXIES`` until one works.
      3. Direct connection (no proxy) as a last resort.

    Returns (client, proxy_used_or_"direct").
    """
    candidates: list[str] = []

    if proxy_url:
        candidates.append(proxy_url)          # user-supplied proxy first
    candidates.extend(_FREE_PROXIES)
    candidates.append("")                      # sentinel → direct connection

    for proxy in candidates:
        label = proxy if proxy else "direct"
        try:
            proxies = {"https": proxy, "http": proxy} if proxy else {}
            session = requests.Session()
            session.proxies.update(proxies)

            client = Client(
                api_key,
                api_secret,
                testnet=testnet,
                requests_params={"proxies": proxies} if proxies else {},
            )
            # Quick connectivity check — raises on geo-block or network error
            client.ping()
            log.info(f"Binance conectado via {label}")
            return client, label
        except Exception as exc:
            log.warning(f"Proxy {label} falhou: {exc}")

    # Should never reach here because the sentinel ("") is always last,
    # but guard anyway.
    raise RuntimeError("Não foi possível conectar à Binance com nenhum proxy.")


def _is_geo_blocked(exc: BinanceAPIException) -> bool:
    """Return True when the exception looks like a Binance geo-restriction."""
    msg = str(exc).lower()
    return "restricted location" in msg or "eligibility" in msg or exc.status_code == 451


class MarketScanner:
    def __init__(self, cfg):
        self.cfg = cfg
        self._proxy_url = getattr(cfg, "PROXY_URL", "")
        self.client, self._active_proxy = _build_client(
            cfg.API_KEY, cfg.API_SECRET, cfg.TESTNET, self._proxy_url
        )
        self._price_cache = {}
        self._watchlist = []
        self._last_watchlist_update = 0
        self._watchlist_ttl = 300  # atualiza a cada 5 minutos

    def _reconnect(self) -> bool:
        """Rebuild the client, rotating to the next proxy on failure."""
        log.warning("Tentando reconectar à Binance com novo proxy…")
        try:
            self.client, self._active_proxy = _build_client(
                self.cfg.API_KEY, self.cfg.API_SECRET,
                self.cfg.TESTNET, self._proxy_url
            )
            return True
        except RuntimeError as exc:
            log.error(f"Reconexão falhou: {exc}")
            return False

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
            if _is_geo_blocked(e):
                self._reconnect()
            return self._watchlist or self.cfg.WATCHLIST

    def get_price(self, symbol: str) -> float:
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])
            self._price_cache[symbol] = price
            return price
        except BinanceAPIException as e:
            log.error(f"Erro ao buscar preco {symbol}: {e}")
            if _is_geo_blocked(e):
                self._reconnect()
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
            if _is_geo_blocked(e):
                self._reconnect()
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
