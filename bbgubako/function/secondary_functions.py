# -*- coding: utf-8 -*-
"""
Created on Tue Apr 23 11:06:59 2024

@author: tongh
"""

from . import basic_functions
import datetime as dt
import math
import pandas as pd
import numpy as np
import time
import warnings
from pandas.errors import PerformanceWarning
warnings.filterwarnings("ignore", category=PerformanceWarning)

max_tickers = 2000

def get_index_members(session, service_opened, index, date):
    if hasattr(date, 'strftime'):
        _date = int(date.strftime('%Y%m%d'))
    elif isinstance(date, str):
        _date = int(date)
    elif isinstance(date, int):
        _date = date
        
    temp = basic_functions.BDS(session=session, service_opened=service_opened, ticker=index, field="INDX_MWEIGHT_HIST", field_overrides={'END_DATE_OVERRIDE':_date}).iloc[:,0].squeeze()
    
    return temp

def get_option_chain(session, service_opened, ticker, date, expiration):
    if hasattr(date, 'strftime'):
        _date = int(date.strftime('%Y%m%d'))
    elif isinstance(date, str):
        _date = int(date)
    elif isinstance(date, int):
        _date = date
        
    return basic_functions.BDS(session=session, service_opened=service_opened, ticker=ticker, field="OPT_CHAIN", field_overrides={'SINGLE_DATE_OVERRIDE':_date, "OPTION_CHAIN_OVERRIDE":expiration}).rename(columns={'Security Description':'bbg_ticker'})



def BQL(session, service_opened, tickers, fields, start_date=None, end_date=dt.datetime.now().date, field_overrides=None, optional_parameters=None, period='DAILY', cd=None):
    if isinstance(tickers, str):
        tickers = [tickers]
    if isinstance(fields, str):
        fields = [fields]
    
    if start_date is None:
        data = []
        for k in tickers:
            data += [basic_functions.BDP(session, service_opened, k, fields, field_overrides)] 
        result = pd.concat(data,  axis=1).loc[fields, tickers]
        return result
    else:
        n = math.ceil(len(tickers)/max_tickers)
        data = []
        for j in range(n):
            subset = tickers[j*max_tickers:(j+1)*max_tickers]
            temp = basic_functions.BDH(session, service_opened, subset, fields, start_date, end_date, field_overrides, optional_parameters, period)
            if len(temp) == 0:
                continue
            if len(subset)==1:
                temp.columns = pd.MultiIndex.from_tuples([(subset[0], fld) for fld in temp.columns])
            elif isinstance(temp.columns[0], str):
                temp.columns = pd.MultiIndex.from_tuples([(subset[0], fields[0])])
            elif isinstance(temp.columns[0], tuple):
                pass

            data += [temp]
            if cd is not None:
                time.sleep(cd)
                
        result = pd.concat(data, axis=1).sort_index()

        for ticker in tickers:
            for fld in fields:
                if (ticker, fld) not in result.columns:
                    result[(ticker, fld)] = np.nan
        return result.loc[:, tickers]
 