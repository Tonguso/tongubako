# -*- coding: utf-8 -*-
"""
Created on Fri Oct 10 11:09:45 2025

@author: tongh
"""


from datetime import datetime, timedelta, date
import pandas as pd
import numpy as np
import time
import blpapi
import eqdogubako.utils as utils
import sqlite3

if __name__ != '__main__':
    from . import admin, order_ticket
else:
    import admin, order_ticket


class EMSXSubscriptionHandler():
    def __init__(self, host='localhost', port=8194):
        admin.create_cache_db()
        self.host = host
        self.port = port
        self.session = admin.initiate_bbg(self.host, self.port)
        self.service_opened = admin.initiate_service(session=self.session, service=["//blp/instruments","//blp/refdata","//blp/emapisvc","//blp/emsx.history"])
        self.cache = sqlite3.connect("orders_cache.db", timeout=30, check_same_thread=False)
        self.orderSubscriptionID = blpapi.CorrelationId(98)
        self.routeSubscriptionID = blpapi.CorrelationId(99)
        
        
    def createOrderSubscription(self):

        orderTopic = "//blp/emapisvc" + "/order?fields="
        orderTopic = orderTopic + "API_SEQ_NUM,"
        orderTopic = orderTopic + "EMSX_ACCOUNT,"
        orderTopic = orderTopic + "EMSX_AMOUNT,"
        orderTopic = orderTopic + "EMSX_ASSET_CLASS,"
        orderTopic = orderTopic + "EMSX_ASSIGNED_TRADER,"
        orderTopic = orderTopic + "EMSX_AVG_PRICE,"
        orderTopic = orderTopic + "EMSX_BASKET_NAME,"
        orderTopic = orderTopic + "EMSX_BASKET_NUM,"
        orderTopic = orderTopic + "EMSX_BROKER,"
        orderTopic = orderTopic + "EMSX_BROKER_COMM,"
        orderTopic = orderTopic + "EMSX_BSE_AVG_PRICE,"
        orderTopic = orderTopic + "EMSX_BSE_FILLED,"
        orderTopic = orderTopic + "EMSX_CFD_FLAG,"
        orderTopic = orderTopic + "EMSX_COMM_DIFF_FLAG,"
        orderTopic = orderTopic + "EMSX_COMM_RATE,"
        orderTopic = orderTopic + "EMSX_CURRENCY_PAIR,"
        orderTopic = orderTopic + "EMSX_DATE,"
        orderTopic = orderTopic + "EMSX_DAY_AVG_PRICE,"
    
    
        subscriptions = blpapi.SubscriptionList()
    
        subscriptions.add(topic=orderTopic, correlationId=self.orderSubscriptionID)
    
        self.session.subscribe(subscriptions) 
        

        
        
if __name__ == '__main__': 
    
    
    test = EMSXSubscriptionHandler()
    
    test.createOrderSubscription()