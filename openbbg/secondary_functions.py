# -*- coding: utf-8 -*-
"""
Created on Tue Jul 08 2026

@author: Hogan

Composite requests built on the basic ones -- chiefly BQL, the unified accessor:
no start_date  -> cross-sectional snapshot (fields x tickers), via BDP per ticker
with start_date -> time series MultiIndex(ticker, field),        via BDH per chunk
Mirrors bbgubako.secondary_functions.BQL exactly.
"""

import datetime as dt
import math
import time
import numpy as np
import pandas as pd

try:
    from . import basic_functions, settings
except ImportError:                                 # run directly (F5 in Spyder)
    import basic_functions, settings

max_tickers = 2000                                  # chunk size (kept for parity with bbg)


def BQL(obb, provider, tickers, fields, start_date=None,
        end_date=dt.datetime.now().date(), field_overrides=None,
        optional_parameters=None, period='DAILY', cd=None):
    if isinstance(tickers, str):
        tickers = [tickers]
    if isinstance(fields, str):
        fields = [fields]

    if start_date is None:                          # ---- snapshot: fields x tickers
        data = [basic_functions.BDP(obb, provider, k, fields, field_overrides) for k in tickers]
        return pd.concat(data, axis=1).loc[fields, tickers]

    # ---- time series: dates x MultiIndex(ticker, field)
    n = math.ceil(len(tickers) / max_tickers)
    data = []
    for j in range(n):
        subset = tickers[j * max_tickers:(j + 1) * max_tickers]
        temp = basic_functions.BDH(obb, provider, subset, fields, start_date, end_date,
                                   field_overrides, optional_parameters, period)
        if len(temp) == 0:
            continue
        if len(subset) == 1:                        # BDH collapsed to field columns -> re-add ticker level
            temp.columns = pd.MultiIndex.from_tuples([(subset[0], fld) for fld in temp.columns])
        data += [temp]
        if cd is not None:
            time.sleep(cd)

    if not data:
        return pd.DataFrame()
    result = pd.concat(data, axis=1).sort_index()
    for ticker in tickers:                          # backfill missing (ticker, field) pairs as NaN
        for fld in fields:
            if (ticker, fld) not in result.columns:
                result[(ticker, fld)] = np.nan
    return result.loc[:, [(t, f) for t in tickers for f in fields]]


def get_index_members(obb, provider, index, date=None):
    # thin helper mirroring bbg -- index constituents via BDS
    return basic_functions.BDS(obb, provider, index, 'INDX_MEMBERS')


def get_option_chain(obb, provider, ticker, date=None, expiration=None):
    return basic_functions.BDS(obb, provider, ticker, 'OPT_CHAIN')
