# -*- coding: utf-8 -*-
"""
Created on Wed Jul 09 2026

@author: Hogan

Direct Yahoo Finance client -- raw HTTP to the v8 chart endpoint, with no yfinance or OpenBB in
between. Returns the same OHLCV frame shape that OpenBB's `.to_df()` gives, so it drops in behind
BDH as source='yahoo'. The chart endpoint is keyless (User-Agent only) and returns the UNADJUSTED
close plus adj_close in one call -- exactly what bbg PX_LAST wants, with no adjustment ambiguity.
"""

import concurrent.futures as cf
import datetime as dt
import pandas as pd
import requests

CHART_URL = 'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}'
SPARK_URL = 'https://query1.finance.yahoo.com/v8/finance/spark'
HEADERS = {'User-Agent': 'Mozilla/5.0'}
INTERVAL = {'1d': '1d', '1W': '1wk', '1M': '1mo'}       # OpenBB interval string -> Yahoo interval
SPARK_MAX = 20                                          # symbols per spark request (>= ~30 -> HTTP 400)
SPARK_RANGES = [('5d', 5), ('1mo', 31), ('3mo', 93), ('6mo', 186), ('1y', 372),
                ('2y', 744), ('5y', 1860), ('10y', 3720), ('max', 10 ** 7)]


def _epoch(d, end=False):
    if d is None:
        return int(dt.datetime.now().timestamp()) if end else 0
    day = dt.datetime(d.year, d.month, d.day) + (dt.timedelta(days=1) if end else dt.timedelta())
    return int(day.timestamp())


def history(symbol, start=None, end=None, interval='1d'):
    # OHLCV (+ adj_close) DataFrame, date-indexed, unadjusted, for one Yahoo-suffixed symbol ('RR.L').
    params = {'period1': _epoch(start), 'period2': _epoch(end, end=True),
              'interval': INTERVAL.get(interval, '1d'), 'events': 'div,splits'}
    r = requests.get(CHART_URL.format(symbol=symbol), params=params, headers=HEADERS, timeout=15)
    r.raise_for_status()
    result = r.json().get('chart', {}).get('result')
    if not result or not result[0].get('timestamp'):
        return pd.DataFrame()
    result = result[0]
    ts = result['timestamp']
    quote = result['indicators']['quote'][0]
    gmt = result.get('meta', {}).get('gmtoffset', 0) or 0        # shift to exchange-local date
    idx = pd.to_datetime([t + gmt for t in ts], unit='s').normalize()
    df = pd.DataFrame({'open': quote.get('open'), 'high': quote.get('high'),
                       'low': quote.get('low'), 'close': quote.get('close'),
                       'volume': quote.get('volume')}, index=idx)
    adj = result['indicators'].get('adjclose')
    if adj:
        df['adj_close'] = adj[0].get('adjclose')
    return df


def _range_for(start):
    # smallest spark range preset that reaches back to `start` (spark ignores period1/period2)
    if start is None:
        return 'max'
    days = (dt.date.today() - start).days
    return next(r for r, d in SPARK_RANGES if d >= days)


def _spark_batch(batch, rng, yint):
    try:
        r = requests.get(SPARK_URL, params={'symbols': ','.join(batch), 'range': rng, 'interval': yint},
                         headers=HEADERS, timeout=25)
        j = r.json() if r.status_code == 200 else {}
    except Exception:
        return {}
    out = {}
    for sym in batch:
        d = j.get(sym)
        if isinstance(d, dict) and d.get('close') and d.get('timestamp'):
            out[sym] = pd.Series(d['close'], index=pd.to_datetime(d['timestamp'], unit='s').normalize())
    return out


def closes(symbols, start=None, end=None, interval='1d', n_jobs=8):
    # Bulk PX_LAST (close ONLY) for many symbols via the spark endpoint -- ~20 symbols/request instead
    # of one request per symbol. Returns {symbol: pd.Series(close, index=dates)}. Uses range presets,
    # so it fetches the smallest range covering `start` then trims to [start, end].
    rng, yint = _range_for(start), INTERVAL.get(interval, '1d')
    batches = [symbols[i:i + SPARK_MAX] for i in range(0, len(symbols), SPARK_MAX)]
    out = {}
    with cf.ThreadPoolExecutor(max_workers=n_jobs) as ex:
        for part in ex.map(lambda b: _spark_batch(b, rng, yint), batches):
            out.update(part)
    lo = pd.Timestamp(start) if start else None
    hi = pd.Timestamp(end) if end else None
    if lo is not None or hi is not None:
        for k, s in list(out.items()):
            if lo is not None:
                s = s[s.index >= lo]
            if hi is not None:
                s = s[s.index <= hi]
            out[k] = s
    return out
