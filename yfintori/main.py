# -*- coding: utf-8 -*-
"""
Created on Sun Jul 05 2026

@author: Hogan

Yahoo Finance data fetcher for worldwide equities (via yfinance). Pass Yahoo-suffixed
tickers -- AAPL, 7203.T, GSK.L, 005930.KS, 600519.SS, MBG.DE ... The security_master
`yahoo_ticker` column produces these for the whole universe.
"""

import time
import datetime as dt
import pandas as pd

try:
    from . import fetch_data, process_data
    from .settings import DEFAULT_PERIOD, DEFAULT_INTERVAL, DEFAULT_FIELD, BATCH_SIZE
except ImportError:                                # run directly as a script (F5 in Spyder)
    import fetch_data, process_data
    from settings import DEFAULT_PERIOD, DEFAULT_INTERVAL, DEFAULT_FIELD, BATCH_SIZE


class YahooFinance():
    def __init__(self, proxies=None):
        self.proxies = proxies
        return

    def get_prices(self, tickers, start_date=None, end_date=None, period=DEFAULT_PERIOD, interval=DEFAULT_INTERVAL,
                   field=DEFAULT_FIELD, auto_adjust=True, batch=BATCH_SIZE, pause=0.5, retries=2):

        period = None if (start_date is not None or end_date is not None) else period
        single = isinstance(tickers, str)
        tickers = [tickers] if single else list(tickers)
        prices, pending = pd.DataFrame(), list(tickers)
        for attempt in range(retries + 1):
            if not pending:
                break
            frames = [prices] if len(prices.columns) else []
            for i in range(0, len(pending), batch):
                chunk = pending[i:i + batch]
                raw = fetch_data.download(chunk, start=start_date, end=end_date, period=period,
                                          interval=interval, auto_adjust=auto_adjust)
                part = process_data.extract_field(raw, field, chunk)
                if len(part):
                    frames.append(part)
                if i + batch < len(pending):
                    time.sleep(pause * (attempt + 1))              # back off harder each pass
            prices = pd.concat(frames, axis=1) if frames else pd.DataFrame()
            if len(prices.columns):
                prices = prices.loc[:, ~prices.columns.duplicated()]
            pending = [t for t in tickers if t not in prices.columns]
            if pending and attempt < retries:
                time.sleep(pause * 20 * (attempt + 1))             # cool-off before retrying the misses
        if len(prices):
            prices = prices.sort_index()
        return prices[tickers[0]] if single and tickers[0] in prices.columns else prices

    def get_history(self, ticker, start_date=None, end_date=None, period=DEFAULT_PERIOD, interval=DEFAULT_INTERVAL, auto_adjust=True):
        # Full OHLCV for a single ticker. start_date/end_date accept str 'YYYY-MM-DD' or datetime.date.
        period = None if (start_date is not None or end_date is not None) else period   # start_date/end_date override period
        raw = fetch_data.history(ticker, start=start_date, end=end_date, period=period, interval=interval, auto_adjust=auto_adjust)
        return process_data.clean_ohlcv(raw)

    def get_info(self, ticker, fields=None):
        # Fundamentals / metadata (marketCap, sector, currency, ...) -> Series.
        return process_data.select_info(fetch_data.info(ticker), fields)

    def get_fx(self, pair, period='5d'):
        # Latest FX rate, e.g. get_fx('USDJPY') / get_fx('EURUSD').
        return fetch_data.fx_rate(pair, period)


if __name__ == "__main__":

    test = YahooFinance()

    test1 = test.get_prices('AAPL', period='6mo')                              # single -> Series
    test2 = test.get_prices(['AAPL', 'MSFT', '7203.T', 'GSK.L', '005930.KS'])  # worldwide -> DataFrame
    test3 = test.get_prices(['AAPL', 'GSK.L'], start_date=dt.date(2024, 1, 1), end_date=dt.date(2024, 6, 30))  # date range
    test4 = test.get_history('AAPL', period='1y')                              # full OHLCV
    test5 = test.get_info('AAPL', fields=['marketCap', 'sector', 'currency'])
    test6 = test.get_fx('USDJPY')
