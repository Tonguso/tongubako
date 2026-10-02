# -*- coding: utf-8 -*-
"""
Created on Tue Apr 23 10:01:34 2024

@author: tongh
"""

import blpapi


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

if __name__ == '__main__': 
    
    test1 = initiate_bbg()
    test2 = initiate_service(test1, "//blp/instruments")