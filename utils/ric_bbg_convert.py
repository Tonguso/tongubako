# -*- coding: utf-8 -*-
"""
Created on Wed Sep 24 09:02:14 2025

@author: tongh
"""

EXCH_CODE = {
    'T': 'JP',
    'OQ': 'US',
    'O': 'US',
    'N': 'US',
    'A':'US',
    'SZ': 'CH',
    'SS': 'CH',
    'SH': 'CH',
    'HK': 'HK',
    'AX': 'AU',
    'TO': 'CN',
    'L':'LN',
    'ST':'SS',
    'DE':'GR',
    'KS':'KP',
    'KQ':'KQ',
    'HE':'FH',
    }

def ric_to_bbg(ric):
    symbol, exchange = ric.split('.')
    bbg_exchange_code = EXCH_CODE[exchange]
    if bbg_exchange_code == 'US':
        symbol = ''.join(['/' + c.upper() if 'a' <= c <= 'z' else c for c in symbol])
    if bbg_exchange_code == 'HK':    
        symbol = symbol.lstrip('0')
    bbg_ticker = f'{symbol} {bbg_exchange_code} Equity'.format(symbol=symbol, bbg_exchange_code=bbg_exchange_code)
    return bbg_ticker