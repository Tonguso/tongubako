# -*- coding: utf-8 -*-
"""
Created on Fri May  2 19:47:26 2025

@author: tongh
"""

from datetime import datetime, timedelta, date
import pandas as pd
import numpy as np
import time
import os
import blpapi
import eqdogubako.utils as utils
import sqlite3

if __name__ != '__main__':
    from . import admin, order_ticket, broker_strategy
else:
    from eqdogubako.bbgubako.emsx import admin, order_ticket, broker_strategy


class EMSXAPI():
    def __init__(self, host='localhost', port=8194):
        admin.create_cache_db()
        self.host = host
        self.port = port
        self.session = admin.initiate_bbg(self.host, self.port)
        self.service_opened = admin.initiate_service(session=self.session, service=["//blp/instruments","//blp/refdata","//blp/emapisvc","//blp/emsx.history"])
        
        emsx_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(emsx_dir, 'orders_cache.db')
        os.makedirs(emsx_dir, exist_ok=True)
        self.cache = sqlite3.connect(db_path, timeout=30, check_same_thread=False)
        
    def regulate_ord_type(self, ord_type):
        if ord_type.upper() in ['MKT','MARKET']:
            return 'MKT'
        elif ord_type.upper() in ['LMT','LIMIT']:
            return 'LMT'
        else:
            raise TypeError('Unrecognized order type')
    
    def regulate_ord_qty(self, ord_qty):
        
        return
    
    def load_orders(self, order_id=None, ticket_id=None, start=None, end=None):
        if order_id is not None:
            query = f'SELECT * FROM orders WHERE order_id={order_id}'
        elif ticket_id is not None:
            query = f'SELECT * FROM orders WHERE ticket_id={ticket_id}'
        elif start is not None:
            if end is None:
                end = datetime.now()
            query = f'SELECT * FROM orders WHERE create_time>="{start.isoformat(sep=" ", timespec="microseconds")}" AND create_time<="{end.isoformat(sep=" ", timespec="microseconds")}"'
        with self.cache as conn:
            df = pd.read_sql(query, conn)
        return df
    
    def clear_order_cache(self):
        if utils.confirm_action("Are you sure you want to clear order cache? (Y/N): "):
            with self.cache as conn:
                conn.execute("DELETE FROM orders")
        
        
    def _wait_for_response(self, correlation_id, timeout=5000):

        start_time = time.time()
        deadline = start_time + timeout/1000.0
        while time.time() < deadline:
            event = self.session.nextEvent(100)  # 100ms
            if event.eventType() in (blpapi.Event.PARTIAL_RESPONSE,
                                     blpapi.Event.RESPONSE):
                for msg in event:
                    if msg.correlationIds()[0].value() == correlation_id.value():
                        return msg
        print("Timeout waiting for order response")
        return None
    
    def get_broker_strategy(self, broker_code, strategy):
        
        service = self.service_opened.get("//blp/emapisvc")
        request = service.createRequest("GetBrokerStrategyInfoWithAssetClass")
        request.set("EMSX_REQUEST_SEQ", 1)
        request.set("EMSX_ASSET_CLASS","EQTY")  # one of EQTY, OPT, FUT or MULTILEG_OPT
        request.set("EMSX_BROKER", broker_code)
        request.set("EMSX_STRATEGY", strategy)
        
        cid = blpapi.CorrelationId()
        self.session.sendRequest(request, correlationId=cid)
        sequence = self._wait_for_response(cid)
        
        strategy = pd.DataFrame(columns=['parameter','disable'])
        for s in sequence.getElement('EMSX_STRATEGY_INFO').values():
            strategy.loc[len(strategy.index)] = [s.getElementAsString("FieldName"), s.getElementAsString("Disable")]
        return strategy
    
    def create_order_and_route(self, ticket, show=True):
        emsx_service = self.service_opened.get("//blp/emapisvc")
        request = emsx_service.createRequest("CreateOrderAndRouteEx")

         # The fields below are mandatory
        request.set("EMSX_TICKER", ticket.bbg_ticker)
        request.set("EMSX_AMOUNT", ticket.ord_qty)
        request.set("EMSX_ORDER_TYPE", ticket.ord_type)
        request.set("EMSX_TIF", "DAY")
        request.set("EMSX_HAND_INSTRUCTION", "ANY")
        request.set("EMSX_SIDE", ticket.side)
        request.set("EMSX_BROKER", ticket.broker)
        request.set("EMSX_ACCOUNT",ticket.account)
        request.set("EMSX_REQUEST_SEQ", ticket.ticket_id) # Add a request sequence, in case bbg thinks its duplicate order
        
        if ticket.lmt_price is not None and ticket.ord_type=='LMT':
            request.set("EMSX_LIMIT_PRICE", ticket.lmt_price) 
        
        strategy = request.getElement("EMSX_STRATEGY_PARAMS")
        strategy.setElement("EMSX_STRATEGY_NAME", ticket.algo)
                
        indicator = strategy.getElement("EMSX_STRATEGY_FIELD_INDICATORS")
        data = strategy.getElement("EMSX_STRATEGY_FIELDS")
        
        for k in ticket.algo_field_sequence:
            param = getattr(ticket, k[0])
            data.appendElement().setElement("EMSX_FIELD_DATA", param) 
            indicator.appendElement().setElement("EMSX_FIELD_INDICATOR", k[1])
         
        cid = blpapi.CorrelationId()
        self.session.sendRequest(request, correlationId=cid)
        sequence = self._wait_for_response(cid)
        
        if sequence.hasElement('MESSAGE'):
            ticket.order_id = sequence['EMSX_SEQUENCE']
            ticket.create_time = datetime.now()
            ticket.cache_order(self.cache)
            message = sequence['MESSAGE']
        elif sequence.hasElement('ERROR_MESSAGE'):
            message = sequence['ERROR_MESSAGE']
        else:
            print('WTF')
        
        if show:
            if ticket.ord_type == 'MKT':
                print(f"{ticket.bbg_ticker.replace(' Equity','')} {ticket.side} {ticket.ord_qty} {ticket.ord_type}: {message}")
            elif ticket.ord_type == 'LMT':
                print(f"{ticket.bbg_ticker.replace(' Equity','')} {ticket.side} {ticket.ord_qty} {ticket.ord_type}{ticket.lmt_price}: {message}")
                
        return sequence
    
    def create_order(self, ticket, show=True):
        
        service = self.service_opened.get("//blp/emapisvc")
        request = service.createRequest("CreateOrder")
     
        request.set("EMSX_TICKER", ticket.bbg_ticker)
        request.set("EMSX_AMOUNT", ticket.ord_qty)
        request.set("EMSX_ORDER_TYPE", ticket.ord_type)
        request.set("EMSX_TIF", "DAY")
        request.set("EMSX_HAND_INSTRUCTION", "ANY")
        request.set("EMSX_SIDE", ticket.side)
        request.set("EMSX_ACCOUNT",ticket.account)
        if ticket.lmt_price is not None and ticket.ord_type=='LMT':
            request.set("EMSX_LIMIT_PRICE", ticket.lmt_price)
        if ticket.basket_name is not None:
            request.set("EMSX_BASKET_NAME", ticket.basket_name)
        
        
        cid = blpapi.CorrelationId()
        self.session.sendRequest(request, correlationId=cid)
        sequence = self._wait_for_response(cid)
        
        success = sequence.hasElement('MESSAGE')
        
        if success:
            ticket.order_id = sequence['EMSX_SEQUENCE']
            ticket.create_time = datetime.now()
            ticket.cache_order(self.cache)
            message = sequence['MESSAGE']
        elif sequence.hasElement('ERROR_MESSAGE'):
            message = sequence['ERROR_MESSAGE']
        else:
            raise ValueError('WTF')
        
        if show:
            if ticket.ord_type == 'MKT':
                print(f"{ticket.bbg_ticker.replace(' Equity','')} {ticket.side} {ticket.ord_qty} {ticket.ord_type}: {message}")
            elif ticket.ord_type == 'LMT':
                print(f"{ticket.bbg_ticker.replace(' Equity','')} {ticket.side} {ticket.ord_qty} {ticket.ord_type}{ticket.lmt_price}: {message}")
        
        output = {
            'request_id': sequence.getRequestId(),
            'message': message,
            'order_id': sequence['EMSX_SEQUENCE'] if success else None,
            'success': True,
            'bbg_ticker': ticket.bbg_ticker,
            'ord_qty': ticket.ord_qty,
            'ord_type':ticket.ord_type,
            'side': ticket.side,
            'lmt_price': ticket.lmt_price,
            }
        
        return output
    
    def route_order(self, order_id, ord_qty, broker_code, ord_type, bbg_ticker, algo, **kwargs):
        service = self.service_opened.get("//blp/emapisvc")
        request = service.createRequest("RouteEx")
        
        request.set("EMSX_SEQUENCE", order_id) # Order number
        request.set("EMSX_AMOUNT", ord_qty)
        request.set("EMSX_BROKER", broker_code)
        request.set("EMSX_HAND_INSTRUCTION", "ANY")
        request.set("EMSX_ORDER_TYPE", self.regulate_ord_type(ord_type))
        request.set("EMSX_TICKER", bbg_ticker)
        request.set("EMSX_TIF", "DAY")
        
        if self.regulate_ord_type(ord_type) == 'LMT' and 'lmt_price' in list(kwargs.keys()):
            request.set("EMSX_LIMIT_PRICE", kwargs['lmt_price'])
        
        strategy = request.getElement("EMSX_STRATEGY_PARAMS")
        strategy.setElement("EMSX_STRATEGY_NAME", ticket.algo)
                
        indicator = strategy.getElement("EMSX_STRATEGY_FIELD_INDICATORS")
        data = strategy.getElement("EMSX_STRATEGY_FIELDS")
        
        for k in broker_strategy.STRATEGY_PARAMS[broker_code][algo]:
            field, exclude, default_value = k
            if field in list(kwargs.keys()):
                data.appendElement().setElement("EMSX_FIELD_DATA", kwargs[field])
            else:
                data.appendElement().setElement("EMSX_FIELD_DATA", default_value)
            indicator.appendElement().setElement("EMSX_FIELD_INDICATOR", exclude)
        
        cid = blpapi.CorrelationId()
        self.session.sendRequest(request, correlationId=cid)
        sequence = self._wait_for_response(cid)
        
        if sequence['MESSAGE'].upper() == 'Order Routed'.upper():
            print('Order routed')   
        return sequence
    
    def modify_order(self, order_id, ord_qty, ord_type, lmt_price, bbg_ticker, show=True):
    
        fills = self.get_fills(ticket.order_id)
        filled_qty = 0 if fills is None else fills['filled_qty']
    
        service = self.service_opened.get("//blp/emapisvc")
        request = service.createRequest("ModifyOrderEx")
        
        request.set("EMSX_SEQUENCE", order_id)
        request.set("EMSX_TIF", "DAY")
        request.set("EMSX_TICKER", bbg_ticker)
        request.set("EMSX_ORDER_TYPE", self.regulate_ord_type(ord_type))
        if self.regulate_ord_type(ord_type) == 'LMT':
            request.set("EMSX_LIMIT_PRICE", lmt_price)
        request.set("EMSX_AMOUNT", max(filled_qty, ord_qty))
        
        cid = blpapi.CorrelationId()
        self.session.sendRequest(request, correlationId=cid)
        sequence = self._wait_for_response(cid)
        
        if sequence['MESSAGE'] == 'Order Modified':
            sql = 'UPDATE orders SET ord_type = ?, ord_qty = ?, lmt_price = ? WHERE order_id = ?'
            with self.cache as conn:
                conn.execute(sql, (ord_type, ord_qty, lmt_price, order_id))
            if show:
                print(f"{order_id}: {sequence['MESSAGE']}")
        return sequence
    
    
    def cancel_routes(self, order_id):
        
        service = self.service_opened.get("//blp/emapisvc")
        request = service.createRequest("CancelRoute")
        
        routes = request.getElement("ROUTES")
        route = routes.appendElement()
        route.getElement("EMSX_SEQUENCE").setValue(order_id)
        for i in range(1,5):
            try:
                route.getElement("EMSX_ROUTE_ID").setValue(1)
            except:
                continue
            
        cid = blpapi.CorrelationId()
        self.session.sendRequest(request, correlationId=cid)
        sequence = self._wait_for_response(cid)
        if sequence['MESSAGE'] == 'Route cancellation request sent to broker':
            print('Route canceled')
        return sequence
    
    
    def cancel_order(self, order_id):
        service = self.service_opened.get("//blp/emapisvc")
        request = service.createRequest("CancelOrderEx")
        
        request.getElement("EMSX_SEQUENCE").appendValue(order_id)
        
        cid = blpapi.CorrelationId()
        self.session.sendRequest(request, correlationId=cid)
        sequence = self._wait_for_response(cid)
        
        return
    
    def get_fills(self, order_id, timeout=5000, start_date=date.today(), end_date=date.today()+timedelta(days=1)):

        svc = self.service_opened.get("//blp/emsx.history")
        req = svc.createRequest("GetFills")
        req.set("FromDateTime", f"{start_date.isoformat()}T00:00:00.000+00:00")
        req.set("ToDateTime", f"{end_date.isoformat()}T23:59:00.000+00:00")
        
        # EMSX doesn't allow extracting fills for a given order ID. The only way is to get all the orders from a list of UUIDs and filter by something.
        scope = req.getElement("Scope")
        scope.setChoice("Uuids")
        uuids = scope.getElement("Uuids")
        for k in admin.AUTHORIZED_UUID:
            uuids.appendValue(k)
        
        # Only in the filter can we specify order ID
        filt = req.getElement("FilterBy")
        filt.setChoice("OrdersAndRoutes")
        orders_array = filt.getElement("OrdersAndRoutes")
        order_struct = orders_array.appendElement()
        order_struct.setElement("OrderId", order_id)
        
        cid = blpapi.CorrelationId()
        self.session.sendRequest(req, correlationId=cid)
        response = self._wait_for_response(cid)
        
        try:
            temp = response.getElement("Fills").getValueAsElement(0) # There should be only ONE fill in the response
        except:
            return None
        fill = {
            'ticker': f"{temp['Ticker']} {temp['Exchange']}",
            'side': temp['Side'],
            'avg_px': temp['FillPrice'],
            'filled_qty': temp['FillShares'],
            'order_qty': temp['Amount'],
            'order_id':temp['OrderId'],
            }  
        return fill
        
        
if __name__ == '__main__': 
    
    
    ticket = order_ticket.OrderTicket(bbg_ticker='AAPL US Equity', ord_type='mkt', lmt_price=None, ord_qty=10, side='buy', algo='VWAP', start_time='09:30:00', end_time='16:00:00', account='EXO-X_TB', broker='CLSW', style='Normal', basket_name='Test')
    
    test = EMSXAPI()
    test1 = test.get_broker_strategy('CLEA', 'VWAP')
    
    test2 = test.create_order(ticket)
    
    time.sleep(4)
    test3 = test.route_order(ticket.order_id, ticket.ord_qty, 'CLSW', ticket.ord_type, ticket.bbg_ticker, algo='VWAP')
    
    time.sleep(4)
    test4 = test.cancel_routes(ticket.order_id)
    
    time.sleep(4)
    test5 = test.modify_order(order_id=ticket.order_id, ord_qty=5, ord_type=ticket.ord_type, lmt_price=249, bbg_ticker=ticket.bbg_ticker)
    
    test6 = test.get_fills(ticket.order_id)
    
    time.sleep(4)
    if test6 is None:
        test6 = test.route_order(ticket.order_id, 5, 'CLSW', ticket.ord_type, ticket.bbg_ticker, algo='VWAP')
    else:
        test6 = test.route_order(ticket.order_id, 5-test6['filled_qty'], 'CLSW', ticket.ord_type, ticket.bbg_ticker, algo='VWAP')
    
    time.sleep(4)
    test8 = test.cancel_order(ticket.order_id)
    
    test5 = test.load_orders(start=datetime.now()-timedelta(days=10))
    
    #test.clear_order_cache()