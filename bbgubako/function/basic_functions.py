# -*- coding: utf-8 -*-
"""
Created on Tue Apr 23 10:00:41 2024

@author: tongh
"""
import blpapi
from collections import defaultdict
import datetime as dt
import pandas as pd
import numpy as np
import math
import time


def BDH(session, service_opened, tickers, fields, start_date, end_date=dt.datetime.now().strftime('%Y%m%d'), field_overrides=None, optional_parameters=None, period='DAILY'):
    refDataService = service_opened.get("//blp/refdata")
    
    if isinstance(fields, str):
        fields = [fields]
    if isinstance(tickers, str):
        tickers = [tickers]
    if hasattr(start_date, 'strftime'):
        start_date = start_date.strftime('%Y%m%d')
    if hasattr(end_date, 'strftime'):
        end_date = end_date.strftime('%Y%m%d')
    
    request = refDataService.createRequest("HistoricalDataRequest")
    for t in tickers:
        request.getElement("securities").appendValue(t)
    for f in fields:
        request.getElement("fields").appendValue(f)
    
    if field_overrides is not None:
        overrideOuter = request.getElement('overrides')
        for fld, value in field_overrides.items():
            override1 = overrideOuter.appendElement()
            override1.setElement('fieldId', fld)
            override1.setElement('value', value)
            
    if optional_parameters is not None:
        for k,v in optional_parameters.items():
            request.set(k, v)
    
    request.set("periodicitySelection", period)
    request.set("startDate", start_date)
    request.set("endDate", end_date)

    session.sendRequest(request)
    
    data = defaultdict(dict)
    while True:
        result = session.nextEvent(500)
        for msg in result:
            security_data = msg.getElement('securityData')
            ticker = security_data.getElementValue('security')#.getValue()
            fieldData = security_data.getElement('fieldData')
            for j in range(len(fields)):
                field = fields[j]
                for i in range(fieldData.numValues()):
                    element_value = fieldData.getValue(i)
                    timestamp = element_value.getElementValue("date")#.getValue()
                    data[(ticker,field)][timestamp] = element_value.getElementValue(field) if element_value.hasElement(field) else np.nan
        if result.eventType() == blpapi.Event.RESPONSE:
            break
    data = pd.DataFrame(data)
    if len(tickers)==1 and len(data.columns)!=0:
        data.columns=data.columns.droplevel()
    return data


def BDS(session, service_opened, ticker, field, field_overrides=None):

    refDataService = service_opened.get("//blp/refdata")
    
    request = refDataService.createRequest("ReferenceDataRequest")
    request.getElement("securities").appendValue(ticker)
    request.getElement("fields").appendValue(field)
    
    if field_overrides is not None:
        overrideOuter = request.getElement('overrides')
        for fld, value in field_overrides.items():
            override1 = overrideOuter.appendElement()
            override1.setElement('fieldId', fld)
            override1.setElement('value', value)
    
    session.sendRequest(request)
    
    data = defaultdict(dict)
    while True:
        result = session.nextEvent(500)
        for msg in result:
            securityData = msg.getElement("securityData")
            for i in range(securityData.numValues()):
                fieldData = securityData.getValue(i).getElement("fieldData").getElement(field)
                for i, row in enumerate(fieldData.values()):
                    for j in range(row.numElements()):
                        e = row.getElement(j)
                        k = str(e.name())
                        v = e.getValue()
                        if k not in data:
                            data[k] = list()

                        data[k].append(v)

        if result.eventType() == blpapi.Event.RESPONSE:
            break
    
    return pd.DataFrame.from_dict(data)


def BDP(session, service_opened, ticker, fields, field_overrides=None):
    refDataService = service_opened.get("//blp/refdata")
    
    if isinstance(fields, str):
        fields = [fields]
    
    request = refDataService.createRequest("ReferenceDataRequest")
    request.getElement("securities").appendValue(ticker)
    for f in fields:
        request.getElement("fields").appendValue(f)
    
    if field_overrides is not None:
        overrideOuter = request.getElement('overrides')
        for fld, value in field_overrides.items():
            override1 = overrideOuter.appendElement()
            override1.setElement('fieldId', fld)
            override1.setElement('value', value)
    
    
    session.sendRequest(request)
      
    data = defaultdict(dict)
    
    while True:
        result = session.nextEvent(500)
        for msg in result:
            securityData = msg.getElement("securityData")
            for j in range(len(fields)):
                field = fields[j]
                for i in range(securityData.numValues()):
                    fieldData = securityData.getValue(i).getElement("fieldData")
                    secId = securityData.getValue(i).getElement("security").getValue()
                    
                    for field in fields:
                        if fieldData.hasElement(field):
                            data[secId][field] = fieldData.getElement(field).getValue()
                        else:
                            data[secId][field] = np.nan
        if result.eventType() == blpapi.Event.RESPONSE:
            break
    return pd.DataFrame(data)



