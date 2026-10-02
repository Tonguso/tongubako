# -*- coding: utf-8 -*-
"""
Created on Sun Jul 05 2026

@author: Hogan

Raw Yahoo Finance I/O via the yfinance library.
"""

import logging
import yfinance as yf

logging.getLogger('yfinance').setLevel(logging.CRITICAL)   # mute per-ticker "possibly delisted" noise on bulk pulls


def download(tickers, start=None, end=None, period=None, interval='1d', auto_adjust=True):
    return yf.download(tickers, start=start, end=end, period=period, interval=interval,
                       auto_adjust=auto_adjust, progress=False, group_by='column', threads=True)


def history(ticker, start=None, end=None, period='2y', interval='1d', auto_adjust=True):
    return yf.Ticker(ticker).history(start=start, end=end, period=period,
                                     interval=interval, auto_adjust=auto_adjust)


def info(ticker):
    try:
        return dict(yf.Ticker(ticker).info)
    except Exception:
        return {}


def fx_rate(pair, period='5d'):
    # 'USDJPY' / 'EURUSD' -> Yahoo '<pair>=X'. Returns the latest rate (float) or None.
    sym = pair.replace('.', '').replace('/', '').upper() + '=X'
    close = yf.download(sym, period=period, progress=False, auto_adjust=True)['Close']
    series = (close.iloc[:, 0] if hasattr(close, 'columns') else close).dropna()   # single-col frame -> Series
    return float(series.iloc[-1]) if len(series) else None
