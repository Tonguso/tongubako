# -*- coding: utf-8 -*-
"""
Created on Sun Jul 05 2026

@author: Hogan

Reshape yfinance raw output into clean, tz-naive frames.
"""

import pandas as pd


def _naive(index):
    return index.tz_localize(None) if getattr(index, 'tz', None) is not None else index


def extract_field(raw, field, tickers):
    # yf.download -> a single 'field' frame (dates x tickers). Handles multi- and single-ticker shapes.
    if raw is None or len(raw) == 0:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        if field not in set(raw.columns.get_level_values(0)):
            return pd.DataFrame()
        out = raw[field].copy()
    else:                                          # single ticker -> flat OHLCV columns
        if field not in raw.columns:
            return pd.DataFrame()
        out = raw[[field]].copy()
        out.columns = list(tickers)[:1]
    out.index = _naive(out.index)
    return out.dropna(how='all')


def clean_ohlcv(raw):
    # single-ticker full OHLCV -> tz-naive, date-indexed frame.
    if raw is None or len(raw) == 0:
        return pd.DataFrame()
    out = raw.copy()
    out.index = _naive(out.index)
    out.index.name = 'date'
    return out


def select_info(data, fields=None):
    if not isinstance(data, dict) or not data:
        return pd.Series(dtype=object)
    return pd.Series(data) if fields is None else pd.Series({f: data.get(f) for f in fields})
