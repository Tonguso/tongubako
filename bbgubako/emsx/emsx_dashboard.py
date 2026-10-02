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
import random

if __name__ != '__main__':
    from . import admin, emsx_order_ticket
else:
    from eqdogubako.bbgubako.emsx import admin, emsx_order_ticket, broker_strategy


class EMSXHandler():
    def __init__(self, host='localhost', port=8194):
        admin.create_cache_db()
        self.host = host
        self.port = port
        self.session = admin.initiate_bbg(self.host, self.port)
        self.service_opened = admin.initiate_service(session=self.session, service=["//blp/instruments","//blp/refdata","//blp/emapisvc","//blp/emsx.history"])
        
        self.initialize_local_cache()    
    
    def initialize_local_cache(self):
        emsx_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(emsx_dir, 'cache.db')
        os.makedirs(emsx_dir, exist_ok=True)
        check = os.path.exists(db_path)
        if not check:
            admin.create_local_cache_db()
        self.cache = sqlite3.connect(db_path, timeout=30, check_same_thread=False)     
        
    
    def cache_parent_order(self, order_summary):
        
        with self.cache as conn:
            conn.execute(f'delete FROM parent_orders where order_id={order_summary.order_id}')
            conn.execute(
            "INSERT OR REPLACE INTO parent_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?,  ?, ?)",
            (
                order_summary.order_id,
                order_summary.account,
                order_summary.basket_name,
                order_summary.ticker,
                order_summary.order_type,
                order_summary.side,
                order_summary.quantity,
                order_summary.limit_price,
                order_summary.cfd,
                order_summary.create_time.isoformat()
                )
            )    
            
    def cache_child_route(self, route_summary):
        
        with self.cache as conn:
            conn.execute(f'delete FROM child_routes where order_id={route_summary.order_id} and route_id={route_summary.route_id}')
            conn.execute(
            "INSERT OR REPLACE INTO child_routes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                route_summary.order_id,
                route_summary.route_id,
                route_summary.ticker,
                route_summary.order_type,
                route_summary.side,
                route_summary.quantity,
                route_summary.limit_price,
                route_summary.broker,
                route_summary.strategy,
                route_summary.start_time,
                route_summary.end_time,
                route_summary.create_time.isoformat()
                )
            )

    
    def create_order(self, ticket, show=True):
        
        service = self.service_opened.get("//blp/emapisvc")
        request = service.createRequest("CreateOrder")
     
        request.set("EMSX_TICKER", ticket.ticker)
        request.set("EMSX_AMOUNT", ticket.quantity)
        request.set("EMSX_ORDER_TYPE", ticket.order_type)
        request.set("EMSX_TIF", "DAY")
        request.set("EMSX_HAND_INSTRUCTION", "ANY")
        request.set("EMSX_SIDE", ticket.side)
        if ticket.account is not None:
            request.set("EMSX_ACCOUNT", ticket.account)
        if ticket.limit_price is not None and ticket.order_type=='LMT':
            request.set("EMSX_LIMIT_PRICE", ticket.limit_price)
        if ticket.basket_name is not None:
            request.set("EMSX_BASKET_NAME", ticket.basket_name)

        cid = blpapi.CorrelationId()
        self.session.sendRequest(request, correlationId=cid)
        sequence = self._wait_for_response(cid)
        
        result = ticket.generate_summary(sequence)
        if result.success:
            self.cache_parent_order(result)
        if show:
            result.show()
        return result
    

    def route_order(self, execution_config, order_id=None, parent_order=None, show=True):
        service = self.service_opened.get("//blp/emapisvc")
        request = service.createRequest("RouteEx")
        parent_order = self.get_parent_order(order_id) if parent_order is None else parent_order
        order_id = order_id if order_id is not None else parent_order.order_id
        order_type, limit_price, quantity = emsx_order_ticket.rectify_parent_and_child(parent_order, execution_config)
        
        request.set("EMSX_SEQUENCE", order_id)
        request.set("EMSX_AMOUNT",  quantity)
        request.set("EMSX_BROKER", execution_config.broker)
        request.set("EMSX_HAND_INSTRUCTION", "ANY")
        request.set("EMSX_ORDER_TYPE", order_type)
        request.set("EMSX_TICKER", parent_order.ticker)
        request.set("EMSX_TIF", "DAY")
        
        if order_type == 'LMT':
            request.set("EMSX_LIMIT_PRICE", limit_price)
        
        strategy = request.getElement("EMSX_STRATEGY_PARAMS")
        strategy.setElement("EMSX_STRATEGY_NAME", execution_config.strategy)
                
        indicator = strategy.getElement("EMSX_STRATEGY_FIELD_INDICATORS")
        data = strategy.getElement("EMSX_STRATEGY_FIELDS")
        
        for k in broker_strategy.STRATEGY_PARAMS[execution_config.broker][execution_config.strategy]:
            field, exclude, default_value = k
            intended_value = getattr(execution_config, field, None)
            data.appendElement().setElement("EMSX_FIELD_DATA", intended_value if intended_value is not None else default_value)
            indicator.appendElement().setElement("EMSX_FIELD_INDICATOR", exclude)
  
        cid = blpapi.CorrelationId()
        self.session.sendRequest(request, correlationId=cid)
        sequence = self._wait_for_response(cid)
        
        result = execution_config.generate_summary(parent_order, sequence)
        
        if show:
            result.show()
        if result.success:
            self.cache_child_route(result)
        
        return result
    
    
    def create_order_and_route(self, ticket, execution_config, show=True):
        emsx_service = self.service_opened.get("//blp/emapisvc")
        request = emsx_service.createRequest("CreateOrderAndRouteEx")
        
        order_type, limit_price, quantity = emsx_order_ticket.rectify_parent_and_child(ticket, execution_config)
        
         # The fields below are mandatory
        request.set("EMSX_TICKER", ticket.ticker)
        request.set("EMSX_AMOUNT", quantity)
        request.set("EMSX_ORDER_TYPE", order_type)
        request.set("EMSX_TIF", "DAY")
        request.set("EMSX_HAND_INSTRUCTION", "ANY")
        request.set("EMSX_SIDE", ticket.side)
        request.set("EMSX_BROKER", execution_config.broker)
        if ticket.account is not None:
            request.set("EMSX_ACCOUNT", ticket.account)
        if limit_price is not None and order_type=='LMT':
            request.set("EMSX_LIMIT_PRICE", limit_price)
        if ticket.basket_name is not None:
            request.set("EMSX_BASKET_NAME", ticket.basket_name)
        request.set("EMSX_REQUEST_SEQ", random.randint(10**12, 10**13-1))
        
        
        strategy = request.getElement("EMSX_STRATEGY_PARAMS")
        strategy.setElement("EMSX_STRATEGY_NAME", execution_config.strategy)
                
        indicator = strategy.getElement("EMSX_STRATEGY_FIELD_INDICATORS")
        data = strategy.getElement("EMSX_STRATEGY_FIELDS")
        
        for k in broker_strategy.STRATEGY_PARAMS[execution_config.broker][execution_config.strategy]:
            field, exclude, default_value = k
            intended_value = getattr(execution_config, field, None)
            data.appendElement().setElement("EMSX_FIELD_DATA", intended_value if intended_value is not None else default_value)
            indicator.appendElement().setElement("EMSX_FIELD_INDICATOR", exclude)
         
        cid = blpapi.CorrelationId()
        self.session.sendRequest(request, correlationId=cid)
        sequence = self._wait_for_response(cid)
        
        order_result = ticket.generate_summary(sequence)
        route_result = execution_config.generate_summary(ticket, sequence)
        
        if show:
            route_result.show()
        
        if order_result.success and route_result.success:
            self.cache_parent_order(order_result)
            self.cache_child_route(route_result)  
            
        return route_result
    
    def get_parent_order(self, order_id):
        query = f'SELECT * FROM parent_orders WHERE order_id={order_id}'
        with self.cache as conn:
            df = pd.read_sql(query, conn)
        order = df.iloc[0].to_dict()

        return emsx_order_ticket.OrderSummary(
            order_id = order['order_id'],
            ticker = order['ticker'],
            quantity = order['quantity'],
            side = order['side'],
            order_type = order['order_type'],
            limit_price = order['limit_price'],
            account = order['account'],
            basket_name = order['basket_name'],
            cfd = order['cfd'],
            create_time = datetime.fromisoformat(order['create_time']))
    
    def get_child_route(self, order_id, route_id):
        query = f'SELECT * FROM child_routes WHERE order_id={order_id} AND route_id={route_id}'
        with self.cache as conn:
            df = pd.read_sql(query, conn)
        order = df.iloc[0].to_dict()
        
        return emsx_order_ticket.RouteSummary(
            order_id = order['order_id'],
            route_id = order['route_id'],
            ticker = order['ticker'],
            quantity = order['quantity'],
            side = order['side'],
            order_type = order['order_type'],
            limit_price = order['limit_price'],
            broker = order['broker'],
            strategy = order['strategy'],
            create_time = datetime.fromisoformat(order['create_time'])
            )

    def load_orders(self, start=datetime.now()-timedelta(days=1), end=datetime.now()):
        query = f'SELECT * FROM parent_orders WHERE create_time>="{start.isoformat(sep=" ", timespec="microseconds")}" AND create_time<="{end.isoformat(sep=" ", timespec="microseconds")}"'
        with self.cache as conn:
            df = pd.read_sql(query, conn)
        return df
    
    def clear_order_cache(self):
        if utils.confirm_action("Are you sure you want to clear order cache? (Y/N): "):
            with self.cache as conn:
                conn.execute("DELETE FROM parent_orders")
                conn.execute("DELETE FROM child_routes")
        
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
    
    
    def modify_parent_order(self, order_id, parent_order, show=True):
        
        parent_order = self.get_parent_order(order_id) if parent_order is None else parent_order
        order_id = order_id if order_id is not None else parent_order.order_id
        
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
    
    
    def cancel_routes(self, order_id=None, route_id = 1, child_route=None, show=True):
        child = self.get_child_route(order_id, route_id) if child_route is None else child_route
        order_id = order_id if child_route is  None else child_route.order_id
        route_id = route_id if child_route is None else child_route.route_id
        
        service = self.service_opened.get("//blp/emapisvc")
        request = service.createRequest("CancelRoute")
        
        routes = request.getElement("ROUTES")
        route = routes.appendElement()
        route.getElement("EMSX_SEQUENCE").setValue(order_id)
        route.getElement("EMSX_ROUTE_ID").setValue(route_id)

        cid = blpapi.CorrelationId()
        self.session.sendRequest(request, correlationId=cid)
        sequence = self._wait_for_response(cid)
        
        child.message = emsx_order_ticket.parse_emsx_sequence(sequence)['message']
        
        if show:
            child.show()
        self.cache_child_route(child)
            
        return child
    
    def cancel_order(self, order_id=None, parent_order=None, show=True): 
        parent_order = self.get_parent_order(order_id) if parent_order is None else parent_order
        order_id = order_id if order_id is not None else parent_order.order_id
        
        service = self.service_opened.get("//blp/emapisvc")
        request = service.createRequest("CancelOrderEx")
        
        request.getElement("EMSX_SEQUENCE").appendValue(order_id)
        
        cid = blpapi.CorrelationId()
        self.session.sendRequest(request, correlationId=cid)
        sequence = self._wait_for_response(cid)
        
        parent_order.message = emsx_order_ticket.parse_emsx_sequence(sequence)['message']
        
        if show:
            parent_order.show()
        self.cache_parent_order(parent_order)
            
        return parent_order
    
    def get_fills(self, order_id=None, parent_order=None, start_date=date.today(), end_date=date.today()+timedelta(days=1)):
        
        parent_order = self.get_parent_order(order_id) if parent_order is None else parent_order
        order_id = order_id if order_id is not None else parent_order.order_id
        
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
        
        fills = pd.DataFrame(columns=['order_id','ticker','side','route_id','filled_quantity','avg_price'])
        n_routes = len(response.getElement("Fills"))
        
        for i in range(n_routes):
            temp = response.getElement("Fills").getValueAsElement(i)
            fills.loc[len(fills.index)] = [temp['OrderId'], parent_order.ticker, temp['Side'], temp['RouteId'], temp['FillShares'], temp['FillPrice']]
        
        return fills
        
        
if __name__ == '__main__': 
    
    
    ticket = emsx_order_ticket.ParentOrder(ticker='EWJ US Equity', order_type='mkt', limit_price=280.18, quantity=10, side='sell', account='EXO-X_TB')
    execution = emsx_order_ticket.ExecutionConfig(broker='CLSW', strategy='POV', order_type='lmt', limit_price=260)
    
    test = EMSXHandler()
    test1 = test.get_broker_strategy('CLEA', 'VWAP')
    
    test2 = test.create_order(ticket)
    test3 = test.get_parent_order(test2.order_id)
    test4 = test.route_order(order_id=test2.order_id, execution_config=execution)
    #test5 = test.create_order_and_route(ticket, execution)
    time.sleep(3)
    #test6 = test.cancel_routes(order_id=test2.order_id, route_id=1)
    time.sleep(3)
    #test7 = test.cancel_order(order_id=test2.order_id)
    
    test8 = test.get_fills(order_id=test2.order_id)