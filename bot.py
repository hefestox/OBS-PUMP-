"""
OBS PUMP SNIPER BOT - Binance
Detecta pumps em tempo real e executa trades automaticamente.
"""

import time
import json
import logging
from datetime import datetime, date
from config import Config
from market_scanner import MarketScanner
from trader import Trader
from risk_manager import RiskManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('pump_sniper.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

STATUS_FILE = "status.json"


def save_status(cfg, risk, open_positions, trade_log, scanner):
    """Salva status atual para o dashboard."""
    try:
        positions_list = []
        for symbol, pos in open_positions.items():
            current = scanner.get_price(symbol)
            positions_list.append({
                "symbol": symbol,
                "entry_price": pos['entry_price'],
                "current_price": current,
                "size_usd": pos['size_usd'],
            })

        wins = sum(1 for t in trade_log if t['pnl'] > 0)
        pnl_today = sum(t['pnl'] for t in trade_log)

        top_movers = []
        try:
            tickers = scanner.client.get_ticker()
            usdt = [t for t in tickers if t['symbol'].endswith('USDT')]
            usdt.sort(key=lambda x: abs(float(x['priceChangePercent'])), reverse=True)
            top_movers = [
                {
                    "symbol": t['symbol'],
                    "change": float(t['priceChangePercent']),
                    "volume": float(t['quoteVolume']) if 'quoteVolume' in t else None
                }
                for t in usdt[:20]
            ]
        except Exception as e:
            log.error(f"Erro ao calcular top movers: {e}")

        status = {
            "pnl_today": round(pnl_today, 2),
            "balance": round(risk.get_balance(), 2),
            "total_trades": len(trade_log),
            "wins": wins,
            "paper": cfg.PAPER_TRADING,
            "watchlist_count": len(scanner._watchlist) or len(cfg.WATCHLIST),
            "open_positions": positions_list,
            "trade_log": trade_log[-50:],
            "top_movers": top_movers,
            "updated_at": datetime.now().strftime("%H:%M:%S"),
        }

        with open(STATUS_FILE, 'w') as f:
            json.dump(status, f)
    except Exception as e:
        log.error(f"Erro ao salvar status: {e}")


def main():
    log.info("=" * 50)
    log.info("  OBS PUMP SNIPER BOT — INICIANDO")
    log.info("=" * 50)

    cfg     = Config()
    scanner = MarketScanner(cfg)
    trader  = Trader(cfg)
    risk    = RiskManager(cfg)

    log.info(f"Banca disponível: ${risk.get_balance():.2f}")
    log.info(f"Pares monitorados: {', '.join(cfg.WATCHLIST)}")
    log.info(f"Modo: {'PAPER TRADING' if cfg.PAPER_TRADING else 'REAL'}")
    log.info("-" * 50)

    open_positions = {}
    trade_log      = []

    while True:
        try:
            # 1. Verifica posições abertas
            for symbol in list(open_positions.keys()):
                pos           = open_positions[symbol]
                current_price = scanner.get_price(symbol)
                action        = risk.should_exit(pos, current_price)

                if action in ("TAKE_PROFIT", "STOP_LOSS", "WEAK"):
                    pnl = trader.close_position(pos, current_price, reason=action)
                    risk.register_pnl(pnl)
                    trade_log.append({
                        "symbol": symbol,
                        "type": "SELL",
                        "pnl": round(pnl, 2),
                        "reason": action,
                        "time": datetime.now().strftime("%H:%M:%S"),
                    })
                    # emoji = "✅" if pnl > 0 else "🛑"
                    log.info(f"SAÍDA {action} | {symbol} | PNL: ${pnl:+.2f}")
                    del open_positions[symbol]

            # 2. Limita posições simultâneas
            if len(open_positions) >= cfg.MAX_OPEN_POSITIONS:
                save_status(cfg, risk, open_positions, trade_log, scanner)
                time.sleep(cfg.SCAN_INTERVAL)
                continue

            # 3. Escaneia mercado
            signals = scanner.scan()

            for sig in signals:
                symbol = sig['symbol']
                if symbol in open_positions:
                    continue
                if not risk.can_trade(symbol):
                    continue

                size  = risk.position_size()
                entry = trader.open_position(symbol, size, sig)

                if entry:
                    open_positions[symbol] = entry
                    trade_log.append({
                        "symbol": symbol,
                        "type": "BUY",
                        "pnl": 0,
                        "reason": f"Vol {sig['volume_ratio']:.1f}x +{sig['price_change']:.1f}%",
                        "time": datetime.now().strftime("%H:%M:%S"),
                    })
                    log.info(
                        f"ENTRADA | {symbol} | "
                        f"${size:.2f} @ ${entry['entry_price']:.4f} | "
                        f"Vol: {sig['volume_ratio']:.1f}x | "
                        f"Pump: +{sig['price_change']:.2f}%"
                    )

            # 4. Atualiza dashboard
            save_status(cfg, risk, open_positions, trade_log, scanner)
            time.sleep(cfg.SCAN_INTERVAL)

        except KeyboardInterrupt:
            log.info("Bot encerrado pelo usuário.")
            break
        except Exception as e:
            log.error(f"Erro no loop principal: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
