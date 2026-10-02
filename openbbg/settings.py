# -*- coding: utf-8 -*-
"""
Created on Tue Jul 08 2026

@author: Hogan

Field / ticker / period translation tables + helpers that turn Bloomberg mnemonics
and tickers into OpenBB symbols and fields. This is the one place mappings live --
extend the maps as you hit new fields. Unknown fields RAISE (never silently NaN),
so a missing mapping is loud, not a wrong number.
"""

import datetime as dt


# ---------------------------------------------------------------- default sources (per capability)
# Default per function when no source= is passed. Prices default to our OWN raw Yahoo client
# (no OpenBB needed); snapshot/reference data have no direct backend yet so they default to an
# OpenBB provider and load OpenBB only when actually called. Pass source= to override with any
# installed provider ('yfinance'/'fmp'/'sec'/'intrinio'/...).
DEFAULT_PROVIDER  = 'yahoo'        # BDH / BQL time series -> direct raw Yahoo   (NO OpenBB)
SNAPSHOT_PROVIDER = 'yfinance'     # BDP / BQL snapshot    -> quote+profile via OpenBB (no direct backend yet)
INDEX_PROVIDER    = 'fmp'          # BDS index members     -> only provider for constituents (needs key)
OPTIONS_PROVIDER  = 'yfinance'     # BDS option chains     -> via OpenBB (free)

# sources served by our OWN raw clients (yahoo.py etc.), not routed through OpenBB
DIRECT_SOURCES = {'yahoo', 'yahoo_direct'}

# Bloomberg periodicity -> OpenBB/Yahoo interval. bbg BDH allows only these three.
PERIOD_INTERVAL = {'DAILY': '1d', 'WEEKLY': '1W', 'MONTHLY': '1M'}

# --- BDH (time series): bbg field -> column of obb.equity.price.historical().to_df()
# NB: bbg PX_LAST is the UNADJUSTED last price -- make sure the provider returns an
# unadjusted close (pin the adjustment arg) or you will silently mix adjusted/unadjusted.
HIST_FIELD_MAP = {
    'PX_LAST': 'close', 'LAST_PRICE': 'close', 'PX_CLOSE': 'close',
    'PX_OPEN': 'open', 'PX_HIGH': 'high', 'PX_LOW': 'low',
    'PX_VOLUME': 'volume', 'VOLUME': 'volume',
}

# --- BDP (snapshot): bbg field -> key in the merged profile+quote record.
# Values are OpenBB standardized-model field names; VERIFY against your provider and
# extend as needed (field names vary a little across providers/versions).
SNAP_FIELD_MAP = {
    'PX_LAST': 'last_price', 'LAST_PRICE': 'last_price',
    'PX_OPEN': 'open', 'PX_HIGH': 'high', 'PX_LOW': 'low',
    'PX_VOLUME': 'volume', 'VOLUME': 'volume',
    'PX_YEST_CLOSE': 'prev_close', 'PREV_CLOSE': 'prev_close',
    'CUR_MKT_CAP': 'market_cap',
    'CRNCY': 'currency', 'CURRENCY': 'currency',
    'NAME': 'name', 'SHORT_NAME': 'name', 'LONG_COMP_NAME': 'name', 'SECURITY_DES': 'name',
    'GICS_SECTOR_NAME': 'sector', 'INDUSTRY_SECTOR': 'sector',
    'COUNTRY': 'hq_country', 'CNTRY_OF_DOMICILE': 'inc_country',
    'ID_ISIN': 'isin', 'ID_CUSIP': 'cusip',
}

# bbg index ticker -> fmp constituents key
INDEX_MEMBERS_MAP = {'SPX': 'sp500', 'INDU': 'dowjones', 'CCMP': 'nasdaq', 'NDX': 'nasdaq'}

# bbg exchange code -> Yahoo/OpenBB suffix (US is bare). Extend as needed.
EXCH_SUFFIX = {
    'US': '', 'LN': '.L', 'JP': '.T', 'JT': '.T', 'GR': '.DE', 'GY': '.DE',
    'FP': '.PA', 'IM': '.MI', 'SM': '.MC', 'SW': '.SW', 'NA': '.AS', 'SS': '.ST',
    'HK': '.HK', 'KS': '.KS', 'KP': '.KS', 'AU': '.AX', 'TT': '.TW', 'IN': '.NS',
    'CH': '.SS', 'C1': '.SS', 'CG': '.SS', 'CS': '.SZ',
}

# bbg index ticker (without ' Index') -> OpenBB/Yahoo symbol. Verify per provider.
INDEX_MAP = {
    'SPX': '^GSPC', 'INDU': '^DJI', 'CCMP': '^IXIC', 'RIY': '^RUI', 'RTY': '^RUT',
    'UKX': '^FTSE', 'SX5E': '^STOXX50E', 'DAX': '^GDAXI', 'NKY': '^N225',
    'HSI': '^HSI', 'SHCOMP': '000001.SS',
}

# composite <- primary exchange codes (used if you route through security_master)
COMPOSITE_TICKER = {'UW': 'US', 'UN': 'US', 'UQ': 'US', 'GR': 'GY', 'SQ': 'SM',
                    'KP': 'KS', 'KQ': 'KS', 'JT': 'JP', 'CG': 'CH', 'CS': 'CH'}


def to_date(x):
    # accept datetime.date / datetime, 'YYYYMMDD' or 'YYYY-MM-DD' -> datetime.date (or None)
    if x is None:
        return None
    if isinstance(x, dt.datetime):
        return x.date()
    if isinstance(x, dt.date):
        return x
    s = str(x)
    if len(s) == 8 and s.isdigit():
        return dt.datetime.strptime(s, '%Y%m%d').date()
    return dt.datetime.strptime(s[:10], '%Y-%m-%d').date()


def to_openbb_symbol(bbg_ticker):
    # 'AAPL US Equity' -> 'AAPL'; '7203 JP Equity' -> '7203.T'; 'SPX Index' -> '^GSPC'.
    # Hook point: swap this for a security_master lookup (bbg_ticker -> yahoo_ticker) if
    # you want authoritative non-US resolution instead of the suffix table below.
    parts = str(bbg_ticker).split(' ')
    key = parts[-1].capitalize() if parts else ''
    if key == 'Equity' and len(parts) >= 3:
        # clean bbg symbol punctuation: 'RR/'->'RR', 'BT/A'->'BT-A', 'BRK/B'->'BRK-B'
        symbol = parts[0].replace('/', '-').rstrip('-')
        exch = parts[1].upper()
        return symbol + EXCH_SUFFIX.get(exch, '')
    if key == 'Index' and len(parts) >= 2:
        idx = ' '.join(parts[:-1]).upper()
        if idx in INDEX_MAP:
            return INDEX_MAP[idx]
        raise KeyError(f"No OpenBB symbol for index '{bbg_ticker}' -- add it to settings.INDEX_MAP")
    if key == 'Curncy':
        raise KeyError(f"Currency ticker '{bbg_ticker}' not supported yet (add an FX route)")
    return str(bbg_ticker)                          # already a bare symbol
