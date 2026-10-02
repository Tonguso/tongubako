# -*- coding: utf-8 -*-
"""
Created on Tue Apr 23 10:18:21 2024

@author: tongh
"""

import blpapi
import datetime as dt
import numpy as np
import pandas as pd

from . import admin, basic_functions, secondary_functions, idconvert, settings



class BloombergAPI():
    def __init__(self, host='localhost', port=8194):
        self.host = host
        self.port = port
        self.session = admin.initiate_bbg(self.host, self.port)
        self.service_opened = admin.initiate_service(session=self.session, service=["//blp/instruments","//blp/refdata"])
    
    def BDH(self, tickers, fields, start_date, end_date=dt.datetime.now().strftime('%Y%m%d'), period='DAILY', field_overrides=None, optional_parameters=None):
        result = basic_functions.BDH(session=self.session, service_opened=self.service_opened, tickers=tickers, fields=fields, start_date=start_date, end_date=end_date, field_overrides=field_overrides, optional_parameters=optional_parameters, period=period)
        return result
    
    def BDS(self, ticker, field, field_overrides=None):
        result =  basic_functions.BDS(session=self.session, service_opened=self.service_opened, ticker=ticker, field=field, field_overrides=field_overrides)
        return result
    
    def BDP(self, ticker, fields, field_overrides=None):
        result = basic_functions.BDP(session=self.session, service_opened=self.service_opened, ticker=ticker, fields=fields, field_overrides=field_overrides)
        return result
    
    def BQL(self, tickers, fields, start_date=None, end_date=dt.datetime.now().date(), field_overrides=None, optional_parameters=None, period='DAILY', cd=None, field_header=True):
        result = secondary_functions.BQL(session=self.session, service_opened=self.service_opened, tickers=tickers, fields=fields, start_date=start_date, end_date=end_date, field_overrides=field_overrides, optional_parameters=optional_parameters, period=period, cd=cd)
        if not field_header:
            result.columns = result.columns.droplevel(1)
        return result
    
    def get_index_members(self, index, date, composite_ticker=True):
        result = secondary_functions.get_index_members(session=self.session, service_opened=self.service_opened, index=index, date=date)
        
        if composite_ticker:
            def change_to_composite_ticker(ticker):
                for key, item in settings.COMPOSITE_TICKER.items():
                    ticker = ticker.replace(' {}'.format(key),' {}'.format(item))
                return ticker
                
            result = result.apply(lambda x: change_to_composite_ticker(x))
        return result
    
    def get_option_chain(self, ticker, asofdate, expiration='M', delta_range=None, tenure_range=None):
        temp = secondary_functions.get_option_chain(session=self.session, service_opened=self.service_opened, ticker=ticker, date=asofdate, expiration=expiration)
        temp['description'] = temp['bbg_ticker'].apply(lambda x: self.BDP(x, 'SECURITY_DES').iloc[0,0]).values
        temp['expiration'] = temp['description'].apply(lambda x: dt.datetime.strptime(x.split(' ')[2], '%m/%d/%y').date()).values
        temp['type'] = temp['description'].apply(lambda x: x.split(' ')[3][0]).values
        temp['strike'] = temp['description'].apply(lambda x: float(x.split(' ')[3][1:])).values
        
        result = temp
        return result
    
    def id_convert(self, code, id_from, id_to, country_override=None):
        if id_from.upper() in idconvert.BBG_TAGS:
            if id_to.upper() in idconvert.SEDOL_TAGS:
                output = self.BDP(code, "ID_SEDOL1").iloc[0,0]
            if id_to.upper() in idconvert.RIC_TAGS:
                return idconvert.stock_bbg_to_ric(self.session, self.service_opened, code=code, id_from=id_from, id_to=id_to)
        elif id_from.upper() in idconvert.SEDOL_TAGS:
            if id_to.upper() in idconvert.BBG_TAGS:
                ticker_and_exch_code = self.BDP("/sedol/"+code.upper(),"TICKER_AND_EXCH_CODE").iloc[0,0] # B616C79 -> TSLA US
                output = ticker_and_exch_code + ' Equity' if not pd.isna(ticker_and_exch_code) else np.nan
        elif id_from.upper() in idconvert.CUSIP_TAGS:
            if id_to.upper() in idconvert.BBG_TAGS:
                if country_override is None:
                    raise ValueError("To convert CUSIP to BBG, country_override must be provided")
                ticker = self.BDP("/cusip/"+code.upper(), "EQY_PRIM_SECURITY_TICKER").iloc[0,0] # 88160R101 -> TSLA
                output = ticker + ' ' + country_override + ' Equity' if not pd.isna(ticker) else np.nan

        return output
    
    def metric_segment(self, ticker, asofdate, field='PG_REVENUE', level=2):
        period=self.BDP(ticker,"FISCAL_YEAR_PERIOD", field_overrides={'EQY_FUND_DT':asofdate.strftime('%Y%m%d')}).iloc[0,0]
        year, quarter = int(period.split(' ')[0]), int(period.split(' ')[1][1])
        if quarter<4:
            prev_year = year-1
        else:
            prev_year = year
        temp = self.BDS(ticker,field, field_overrides={"PRODUCT_GEO_OVERRIDE":"G","FUND_PER":'Y',"EQY_FUND_YEAR":str(prev_year),'PG_HIERARCHY_LEVEL':str(level)})
            
        for k in temp.columns[2:]:
            n = int(k.split(' ')[1])
            temp = temp.rename(columns={k:str(prev_year-n+1)+'FY'})
        temp['Flag'] = True
        
        if level == 2:
            for i in range(len(temp.index)-1):
                if temp['Product Geographic Hierarchy Level'].iloc[i] == 1 and temp['Product Geographic Hierarchy Level'].iloc[i+1] == 2:
                    temp['Flag'].iloc[i] = False
                
                
        temp['Metric Name'] = temp['Metric Name'].apply(lambda x: x.lstrip())
        
        result = temp[temp['Flag']==True].rename(columns={'Metric Name':'Region'}).drop(['Product Geographic Hierarchy Level','Flag'],axis=1)
        result[result.iloc[:,1:].abs()<0.1]=np.nan

        return result
    
    def get_trading_dates(self, calendar, aggregate='union', start_date=dt.date(1950,1,1), end_date=dt.date(2099,1,1)):
        if isinstance(calendar, str):
            calendar = [calendar]
        
        holidays = []
        for k in calendar:
            result = self.BDS('SPX Index', "CALENDAR_NON_SETTLEMENT_DATES", field_overrides={"SETTLEMENT_CALENDAR_CODE":k,"CALENDAR_START_DATE":'19960101', "CALENDAR_END_DATE":'205012031'}).squeeze()
            holidays += [result]
            
        if aggregate.upper() in ['INTERSECTION','INTERSECT','IN']:
            holidays = pd.concat(holidays).unique()
        elif aggregate.upper() in ['UNION','U','OUT']:
            holidays = set.intersection(*[set(k) for k in holidays])
            
        business_dates = pd.date_range(start_date, end_date, freq='B').to_series().apply(lambda x: x.date()).reset_index(drop=True)
        trading_dates = business_dates[~business_dates.isin(holidays)].sort_values()
        return trading_dates

    

if __name__ == '__main__': 
    
    test = BloombergAPI()
    
    test1 = test.BDH(tickers=['AAPL US Equity'], fields=['PX_LAST'], start_date=dt.date(2022,1,1))
    test2 = test.BDP(ticker='AAPL US Equity', fields=['CRNCY','PX_LAST'])
    test3 = test.BDS(ticker='AAPL US Equity', field='PG_REVENUE')
    test4 = test.BQL(tickers=['AAPL US Equity','IBM US Equity'], fields=['PX_LAST','CUR_MKT_CAP'])
    test4 = test.BQL(tickers=['AAPL US Equity','IBM US Equity','ATVI US Equity'], fields='PX_LAST', start_date=dt.date(2023,1,1))
    test5 = test.get_index_members('RIY Index', dt.date(2024,4,1))
    test6 = test.id_convert('AAPL US Equity','BBG','RIC')
    test7 = test.get_option_chain('AAPL US Equity', dt.date(2022,1,1))
