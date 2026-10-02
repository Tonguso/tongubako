# -*- coding: utf-8 -*-
"""
Created on Fri May  2 19:48:54 2025

@author: tongh
"""


import blpapi
import sqlite3
import pandas as pd
import os

AUTHORIZED_UUID = [31350295, 30766934, 32413344, 24748171, 28102175, 31189010, 31407570, 32009639, 31561732, 32354052, 32520721, 32808013]

def initiate_bbg(host='localhost', port=8194):
    options = blpapi.SessionOptions()
    options.setServerHost(host)
    options.setServerPort(port)
    session = blpapi.Session(options)
    session.start()
    session.nextEvent()
    
    return session

def stop_bbg(session):
    return session.stop()


def initiate_service(session, service):
    if isinstance(service, str):
        service = [service]
    service_opened = {}
    for k in service:
        session.openService(k)
        session.nextEvent()
        service_opened[k] = session.getService(k)
        session.nextEvent(500)
    return service_opened

def create_cache_db():
    emsx_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(emsx_dir, 'orders_cache.db')
    os.makedirs(emsx_dir, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        ticket_id INT,
        order_id INT,
        bbg_ticker  TEXT,
        ord_type TEXT,
        side    TEXT,
        ord_qty INT,
        lmt_price  NUMERIC,
        create_time  TIMESTAMP
    )""")
    conn.commit()
    return

def create_local_cache_db():
    emsx_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(emsx_dir, 'cache.db')
    os.makedirs(emsx_dir, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS parent_orders (
        order_id INT,
        account TEXT,
        basket_name TEXT,
        ticker  TEXT,
        order_type TEXT,
        side    TEXT,
        quantity INT,
        limit_price  NUMERIC,
        cfd INT,
        create_time  TIMESTAMP
    )""")
    
    conn.execute("""
    CREATE TABLE IF NOT EXISTS child_routes (
        order_id INT,
        route_id INT,
        ticker  TEXT,
        order_type TEXT,
        side    TEXT,
        quantity INT,
        limit_price  NUMERIC,
        broker TEXT,
        strategy TEXT,
        start_time TEXT,
        end_time TEXT,
        create_time  TIMESTAMP
    )""")
    conn.commit()
    return

if __name__ == '__main__': 
    
    test1 = initiate_bbg()
    test2 = initiate_service(test1, "//blp/instruments")
    #conn = sqlite3.connect("cache.db", check_same_thread=False)
    #res = pd.read_sql("SELECT * FROM parent_orders", conn)
    
    create_local_cache_db()