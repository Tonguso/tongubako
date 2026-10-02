# -*- coding: utf-8 -*-
"""
Created on Tue Jul 08 2026

@author: Hogan

OpenBBG -- Bloomberg-flavoured facade over the OpenBB Platform. Method signatures and
return shapes match bbgubako.BloombergAPI, so `bbg = OpenBBG()` is a drop-in for the
terminal tool on the BDH / BDP / BQL / BDS surface.

CAVEATS (this is Bloomberg-shaped access to OpenBB data, not an emulator):
  * PX_LAST etc. are UNADJUSTED on Bloomberg -- pin the provider adjustment to match.
  * BDP/BDS field coverage is whatever OpenBB exposes; unmapped fields RAISE by design.
  * BQL's computed fields / screening / let() expressions do NOT port -- only the plain
    "field(s) over ticker(s) over dates" mode is supported.
"""

import datetime as dt
import pandas as pd

try:
    from . import admin, basic_functions, secondary_functions, settings
except ImportError:                                 # run directly (F5 in Spyder)
    import admin, basic_functions, secondary_functions, settings


class OpenBBG():
    def __init__(self, provider=None, credentials=None):
        self.provider = provider or settings.DEFAULT_PROVIDER
        self._credentials = credentials
        self._obb = None                            # OpenBB is loaded lazily -- direct sources never touch it

    def _get_obb(self):
        if self._obb is None:
            self._obb = admin.initiate_openbb(credentials=self._credentials)
        return self._obb

    def _obb_for(self, source):                     # None for our own raw clients -> OpenBB stays unloaded
        return None if source in settings.DIRECT_SOURCES else self._get_obb()

    def _snapshot_src(self, source):                # snapshots have no direct backend -> fall back to OpenBB
        src = source or self.provider
        return settings.SNAPSHOT_PROVIDER if src in settings.DIRECT_SOURCES else src

    def BDH(self, tickers, fields, start_date, end_date=dt.datetime.now().strftime('%Y%m%d'),
            period='DAILY', field_overrides=None, optional_parameters=None, decimals=2, source=None):
        src = source or self.provider
        return basic_functions.BDH(self._obb_for(src), src, tickers=tickers, fields=fields,
                                   start_date=start_date, end_date=end_date, period=period,
                                   field_overrides=field_overrides, optional_parameters=optional_parameters,
                                   decimals=decimals)

    def BDS(self, ticker, field, field_overrides=None, source=None):
        # source=None -> BDS picks by field: index members from fmp, option chains from yfinance
        return basic_functions.BDS(self._get_obb(), source, ticker=ticker, field=field,
                                   field_overrides=field_overrides)

    def BDP(self, ticker, fields, field_overrides=None, source=None):
        src = self._snapshot_src(source)            # snapshot -> OpenBB (no direct backend)
        return basic_functions.BDP(self._obb_for(src), src, ticker=ticker, fields=fields,
                                   field_overrides=field_overrides)

    def BQL(self, tickers, fields, start_date=None, end_date=dt.datetime.now().date(),
            field_overrides=None, optional_parameters=None, period='DAILY', cd=None, field_header=True, source=None):
        # no start_date -> snapshot (OpenBB); with start_date -> time series (price default, can be direct)
        src = self._snapshot_src(source) if start_date is None else (source or self.provider)
        result = secondary_functions.BQL(self._obb_for(src), src, tickers=tickers, fields=fields,
                                         start_date=start_date, end_date=end_date, field_overrides=field_overrides,
                                         optional_parameters=optional_parameters, period=period, cd=cd)
        if not field_header and isinstance(result.columns, pd.MultiIndex):   # only meaningful for the time-series form
            result.columns = result.columns.droplevel(1)
        return result


if __name__ == '__main__':

    bbg = OpenBBG()                                 # needs `pip install openbb`

    test1 = bbg.BDH(tickers=['AAPL US Equity'], fields=['PX_LAST'], start_date=dt.date(2022, 1, 1))
    test2 = bbg.BDP(ticker='AAPL US Equity', fields=['CRNCY', 'PX_LAST'])
    test3 = bbg.BDS(ticker='SPX Index', field='INDX_MEMBERS')
    test4 = bbg.BQL(tickers=['AAPL US Equity', 'IBM US Equity'], fields=['PX_LAST', 'CUR_MKT_CAP'])
    test5 = bbg.BQL(tickers=['AAPL US Equity', 'IBM US Equity'], fields='PX_LAST',
                    start_date=dt.date(2023, 1, 1), field_header=False)
