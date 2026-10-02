# -*- coding: utf-8 -*-
"""
Created on Tue Jul 08 2026

@author: Hogan

The primitive requests -- BDH / BDP / BDS -- built on the OpenBB Platform (obb),
returning the SAME shapes as bbgubako.basic_functions so downstream code is identical.
Column labels stay as the original Bloomberg tickers; symbols are translated only for
the underlying fetch.
"""

import datetime as dt
import numpy as np
import pandas as pd

try:
    from . import settings, yahoo
except ImportError:                                 # run directly (F5 in Spyder)
    import settings, yahoo


def _history(obb, source, sym, sd, ed, interval):
    # dispatch a single-symbol history fetch by source: our raw client vs an OpenBB provider.
    if source in settings.DIRECT_SOURCES:
        return yahoo.history(sym, start=sd, end=ed, interval=interval)
    return obb.equity.price.historical(sym, start_date=sd, end_date=ed,
                                       interval=interval, provider=source).to_df()


def BDH(obb, provider, tickers, fields, start_date,
        end_date=dt.datetime.now().strftime('%Y%m%d'),
        field_overrides=None, optional_parameters=None, period='DAILY', decimals=2):
    # History -> DataFrame indexed by date, columns = MultiIndex(ticker, field);
    # single ticker collapses to just the field columns (matches bbg). field_overrides /
    # optional_parameters are accepted for signature parity but are Bloomberg-only (ignored).
    if isinstance(fields, str):
        fields = [fields]
    if isinstance(tickers, str):
        tickers = [tickers]

    sd, ed = settings.to_date(start_date), settings.to_date(end_date)
    per = str(period).upper()
    if per not in settings.PERIOD_INTERVAL:           # bbg BDH allows only DAILY / WEEKLY / MONTHLY
        raise ValueError(f"BDH period must be one of {sorted(settings.PERIOD_INTERVAL)}, got '{period}'")
    interval = settings.PERIOD_INTERVAL[per]
    try:
        cols = [settings.HIST_FIELD_MAP[f.upper()] for f in fields]
    except KeyError as e:
        raise KeyError(f"BDH: no historical mapping for field {e}; supported "
                       f"{sorted(settings.HIST_FIELD_MAP)} -- add to settings.HIST_FIELD_MAP") from None

    frames = {}
    if provider in settings.DIRECT_SOURCES and len(tickers) > 1 and set(cols) == {'close'}:
        sym_map = {t: settings.to_openbb_symbol(t) for t in tickers}      # bbg ticker -> yahoo symbol
        series = yahoo.closes(list(sym_map.values()), start=sd, end=ed, interval=interval)   # spark: ~20/request
        for t, sym in sym_map.items():
            if sym in series:
                for f in fields:                                          # every requested field maps to close
                    frames[(t, f)] = series[sym]
    else:
        for t in tickers:
            sym = settings.to_openbb_symbol(t)
            df = _history(obb, provider, sym, sd, ed, interval)
            for f, col in zip(fields, cols):
                if col in df.columns:
                    frames[(t, f)] = df[col]

    if not frames:
        return pd.DataFrame()
    data = pd.DataFrame(frames)
    data.columns = pd.MultiIndex.from_tuples(data.columns)
    data.index = pd.to_datetime(data.index).date     # date objects, not Timestamps (freq is <= daily)
    data.index.name = None
    if len(tickers) == 1:
        data.columns = data.columns.droplevel(0)    # -> field columns only
    if decimals is not None:
        data = data.round(decimals)                 # strip yfinance float32 noise (1399.400024 -> 1399.4)
    return data


def BDP(obb, provider, ticker, fields, field_overrides=None):
    # Snapshot -> DataFrame with fields as the INDEX and the ticker as the single COLUMN,
    # so BDP(...).iloc[0, 0] yields the value (matches bbg).
    if provider in settings.DIRECT_SOURCES:
        raise NotImplementedError(f"BDP: direct source '{provider}' not built yet -- snapshots still go "
                                  f"through an OpenBB provider (use source=None / 'yfinance')")
    if isinstance(fields, str):
        fields = [fields]
    sym = settings.to_openbb_symbol(ticker)
    snap = _snapshot(obb, provider, sym)

    values = {}
    for f in fields:
        key = settings.SNAP_FIELD_MAP.get(f.upper())
        if key is None:
            raise KeyError(f"BDP: no snapshot mapping for field '{f}' -- add it to "
                           f"settings.SNAP_FIELD_MAP")
        values[f] = snap.get(key, np.nan)
    return pd.DataFrame({ticker: values})


def BDS(obb, provider, ticker, field, field_overrides=None):
    # Bulk/reference data. OpenBB only covers a slice of Bloomberg's bulk fields; the
    # supported ones are dispatched here and everything else RAISES (honest, not silent).
    f = str(field).upper()
    if f in ('INDX_MEMBERS', 'INDX_MWEIGHT', 'INDX_MWEIGHT_HIST', 'INDEX_MEMBERS'):
        idx = str(ticker).split(' ')[0].upper()      # 'SPX Index' -> 'SPX'
        key = settings.INDEX_MEMBERS_MAP.get(idx)
        if key is None:
            raise KeyError(f"BDS index members: map '{ticker}' in settings.INDEX_MEMBERS_MAP "
                           f"(fmp expects names like sp500 / dowjones / nasdaq)")
        return obb.index.constituents(key, provider=provider or settings.INDEX_PROVIDER).to_df()   # default fmp (needs key)
    if f in ('OPT_CHAIN', 'OPTION_CHAIN', 'CHAIN'):
        sym = settings.to_openbb_symbol(ticker)
        return obb.derivatives.options.chains(sym, provider=provider or settings.OPTIONS_PROVIDER).to_df()
    raise NotImplementedError(
        f"BDS field '{field}' has no OpenBB equivalent. Supported: INDX_MEMBERS "
        f"(index members), OPT_CHAIN (option chain). Bloomberg bulk fields such as "
        f"segment data or settlement calendars are not available via OpenBB.")


def _snapshot(obb, provider, sym):
    # Merge profile + quote into one flat dict; quote is applied last so live prices win.
    # Tolerate ONE endpoint failing (a provider may serve quote but not profile), but if BOTH
    # fail the source can't serve this name -> raise rather than silently returning all-NaN.
    out, errors = {}, []
    for getter in (lambda: obb.equity.profile(sym, provider=provider),
                   lambda: obb.equity.price.quote(sym, provider=provider)):
        try:
            res = getter().results
            rec = res[0] if isinstance(res, list) else res
            out.update({k: v for k, v in rec.model_dump().items() if v is not None})
        except Exception as e:
            errors.append(str(e).splitlines()[-1].strip())
    if not out:
        raise RuntimeError(f"BDP: source '{provider}' returned no data for '{sym}' -- "
                           f"{errors[-1][:160] if errors else 'empty response'}")
    return out
