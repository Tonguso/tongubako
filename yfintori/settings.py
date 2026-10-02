# -*- coding: utf-8 -*-
"""
Created on Sun Jul 05 2026

@author: Hogan
"""

DEFAULT_PERIOD = '2y'          # yfinance period used when start/end are not given
DEFAULT_INTERVAL = '1d'        # daily bars
DEFAULT_FIELD = 'Close'        # field get_prices returns (auto-adjusted close by default)
PRICE_FIELDS = ['Open', 'High', 'Low', 'Close', 'Volume']
BATCH_SIZE = 200               # tickers per yf.download call (chunk large global universes)
