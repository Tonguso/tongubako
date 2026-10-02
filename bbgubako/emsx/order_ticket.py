# -*- coding: utf-8 -*-
"""
Created on Fri May  2 17:48:06 2025

@author: tongh
"""


from datetime import datetime, timedelta, date
import pandas as pd
import numpy as np
import requests
from requests.auth import HTTPBasicAuth
import random
import re

LOCAL_TIME_ZONE = 'Europe/London'

if __name__ != '__main__':
    from . import admin, broker_strategy
else:
    import admin, broker_strategy




#%% Order Ticket

class OrderTicket():
    def __init__(self, bbg_ticker, ord_qty, side, ord_type='MKT', algo=None, lmt_price=None, exchange=None, currency=None, start_time="", end_time="", target_volume=30, account=None, broker=None, trader=None, basket_name=None, style='Normal', participate_open='N', participate_close='N', iwould_price=None, iwould_pct=0, iwould_qty=0, **kwargs):
        self.bbg_ticker = bbg_ticker
        self.ord_qty = ord_qty
        self.side = self.check_side(side)
        self.lmt_price = lmt_price
        self.ord_type = self.check_ord_type(ord_type)
        self.target_volume = self.check_target_volume(target_volume)
        self.start_time = self.check_time_format(start_time)
        self.end_time = self.check_time_format(end_time)
        self.algo = self.check_algo(algo)
        self.broker = broker.upper() if broker is not None else None
        self.basket_name = basket_name
        self.account = account
        self.style = style
        self.participate_open = participate_open
        self.participate_close = participate_close
        self.generate_strategy()
        self.order_id = None
        self.ticket_id =  random.randint(10**12, 10**13-1)
        self.kwargs = kwargs

    
    def generate_strategy(self):
        if self.broker is not None and self.algo is not None:
            self.algo_field_sequence = broker_strategy.STRATEGY_PARAMS[self.broker][self.algo]
        return
    
    def check_side(self, side):
        if side.upper().replace(' ','') not in ['BUY','SELL','SHORT','COVERSHORT','COVER']:
            return TypeError('Unrecognized side type')
        return side.upper().replace(' ','')
    
    def check_ord_type(self, ord_type):
        if ord_type.upper().replace(' ','') in ['MKT','MARKET']:
            return 'MKT'
        elif ord_type.upper().replace(' ','') in ['LMT','LIMIT']:
            if self.lmt_price is None:
                raise ValueError('Limit order must have a lmt price')
            else:
                return 'LMT'
        else:
            raise TypeError('Order type must be MKT or LMT')
    
    def check_algo(self, algo):
        if algo is None:
            return None
        elif algo.upper() in ['DMA']:
            if self.lmt_price is None:
                raise ValueError('DMA order must have limit price')
        elif algo.upper() in ['TWAP','VWAP']:
            if self.start_time is None or self.end_time is None:
                raise ValueError('TWAP and VWAP orders require start_time and end_time')
        elif algo.upper() in ['POV']:
            pass
        else:
            raise TypeError('Unrecognized algo type')
        return algo
    
    def check_time_format(self, time_str):
        if time_str is None or time_str == "":
            return None
        else:
            if len(time_str) != 8 or time_str.count(':')!=2:
                raise ValueError('Time must be None or HH:MM:SS string')
            r = re.compile('.{2}:.{2}:.{2}')
            if r.match(time_str) is None:
                raise ValueError('Time must be None or HH:MM:SS string')
            hour, minute, second = time_str.split(':')
            if int(hour)>24 or int(hour)<0:
                raise ValueError('HH must be between 00 and 24')
            if int(minute)>60 or int(minute)<0 or int(second)>60 or int(second)<0:
                raise ValueError('MM and SS must be between 00 and 60')
            return time_str
    
    def check_target_volume(self, target_volume):
        if target_volume is None:
            return None
        elif target_volume<0 or target_volume>100:
            raise ValueError('Target volume must be between 0 and 100')
        elif target_volume >30:
            raise Warning('Target volume is higher than 30%')
        return int(target_volume)
    
    def cache_order(self, conn):
        
        with conn:
            conn.execute(f'delete FROM orders where ticket_id={self.ticket_id}')
            conn.execute(
            "INSERT OR REPLACE INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                self.ticket_id,
                self.order_id,
                self.bbg_ticker,
                self.ord_type,
                self.side,
                self.ord_qty,
                self.lmt_price,
                self.create_time
                )
            )
        

    
    
if __name__ == '__main__':
    
    test = OrderTicket(symbol='AAPL US Equity', ord_qty=1, side='buy', algo='TWAP', start_time='14:30:00', end_time='21:00:00')