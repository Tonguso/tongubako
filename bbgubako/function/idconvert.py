# -*- coding: utf-8 -*-
"""
Created on Wed Oct 16 11:31:24 2024

@author: tongh
"""

from . import basic_functions
import datetime as dt
import math
import pandas as pd
import numpy as np
import time

SEDOL_TAGS = ['SEDOL']
BBG_TAGS = ['BBG','BLOOMBERG','BBGTICKER']
RIC_TAGS = ['RIC','REUTERS','REFINITIV']
CUSIP_TAGS = ['CUSIP']

EXCH_CODE_MAPPING_BBG_TO_REUTERS={
    'UW':'OQ',
    'UQ':'OQ',
    'UN':'N',
    'HK':'HK',
    'UF':'Z',
    'UR':'OQ',
    'UV':'PK',
    'NA':'AS',
    'SW':'S',
    'SE':'S',
    'LN':'L',
    'FP':'PA',
    'GY':'DE',
    'GR':'DE',
    'DC':'CO',
    'AT':'AX',
    'UA':'A',
    'CV':'V',
    'CT':'TO',
    }

def stock_bbg_to_ric(session, service_opened, code, id_from, id_to):
    primary_exchange_code = basic_functions.BDP(session, service_opened, code, 'ORIG_PRIM_EXCH_CODE').iloc[0,0] # BGNE US Equity -> UW
    
    if pd.isna(primary_exchange_code):
        return np.nan
    
    exchange_symbol = basic_functions.BDP(session, service_opened, code, 'ID_EXCH_SYMBOL').iloc[0,0] # AAPL US Equity -> AAPL
    
    RIC_exch = EXCH_CODE_MAPPING_BBG_TO_REUTERS[primary_exchange_code]
    
    if '.' in exchange_symbol and RIC_exch in ['N','OQ']:
        ticker, suffix = exchange_symbol.split('.')
        if suffix.upper() in ['A','B','C']:
            ric = ticker + suffix.lower() + '.'+RIC_exch
    elif ' ' in exchange_symbol and RIC_exch in ['CO']:
        ticker, suffix = exchange_symbol.split(' ')
        if suffix.upper() in ['A','B','C']:
            ric = ticker + suffix.lower() + '.'+RIC_exch
    else:
        ric = exchange_symbol+'.'+RIC_exch
    
    return ric.replace('..','.')
    
