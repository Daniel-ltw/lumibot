import argparse
import logging
import sys
from datetime import datetime
from time import time

from credentials import AlpacaConfig

from lumibot.backtesting import YahooDataBacktesting
from lumibot.brokers import Alpaca
from lumibot.data_sources import AlpacaData
from lumibot.strategies.examples import (
    Diversification,
    IntradayMomentum,
    Momentum,
    Screener,
)
from lumibot.tools import indicators
from lumibot.traders import Trader

# Global parameters
debug = False
budget = 40000
backtesting_start = datetime(2018, 1, 1)
backtesting_end = datetime(2019, 1, 1)  # datetime.now()
logfile = "logs/test.log"

# Trading objects
alpaca_broker = Alpaca(AlpacaConfig)
alpaca_data_source = AlpacaData(AlpacaConfig)
trader = Trader(logfile=logfile, debug=debug)

# Strategies mapping
mapping = {
    "momentum": Momentum,
    "diversification": Diversification,
    "intraday_momentum": IntradayMomentum,
    "screener": Screener,
}

if __name__ == "__main__":
    # Set the benchmark asset for backtesting to be "SPY" by default
    benchmark_asset = "SPY"

    parser = argparse.ArgumentParser("Running AlgoTrader")
    parser.add_argument("strategies", nargs="+", help="list of strategies")
    parser.add_argument(
        "-l",
        "--live-trading",
        default=False,
        action="store_true",
        help="enable live trading",
    )

    args = parser.parse_args()
    strategies = args.strategies
    live_trading = args.live_trading

    for strategy_name in strategies:
        strategy_class = mapping.get(strategy_name)
        if strategy_class is None:
            raise ValueError(f"Strategy {strategy_name} does not exist")

        stat_file = f"logs/strategy_{strategy_class.__name__}_{int(time())}.csv"
        if live_trading:
            strategy = strategy_class(
                budget=budget, broker=alpaca_broker, stat_file=stat_file
            )
            trader.add_strategy(strategy)
        else:
            strategy_class.backtest(
                YahooDataBacktesting,
                budget,
                backtesting_start,
                backtesting_end,
                stat_file=stat_file,
            )

            logging.info(f"*** Benchmark Performance for {benchmark_asset} ***")
            indicators.calculate_returns(
                benchmark_asset, backtesting_start, backtesting_end
            )

    if live_trading:
        trader.run_all()

    logging.info("The end")
