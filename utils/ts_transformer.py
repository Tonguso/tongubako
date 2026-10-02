# -*- coding: utf-8 -*-
"""
Created on Mon Feb  3 15:38:52 2025

@author: tongh
"""

import numpy as np
import pandas as pd




class ts_transformer():
    def __init__(self, data):
        if not isinstance(data, pd.DataFrame):
            raise TypeError('Data must be a dataframe') 
        self.data = data
        self.transformed_data = data.copy()
        self.transform_method = {}
        self.tag={'transform':False, 'normalize':False}
        
    def transform(self, how):
        if isinstance(how, list):
            if len(how) != len(self.data.columns):
                raise ValueError('Transform methods and data columns do not match')
            for i in range(len(how)):
                self.transformed_data.iloc[:,i] = self.transform_single_series(self.data.iloc[:,i], how[i])
                self.transform_method[self.data.columns[i]] = how[i]
        elif isinstance(how, dict):
            raise TypeError('Dict transform is not yet supported')
        self.tag['transform']=True
        return
    
    def normalize(self, how='mean-variance'):
        if how.upper().replace(' ','').replace('-','').replace('_','') in ['MEANVARIANCE','MEANVAR']:
            self.stddev = self.transformed_data.std()
            self.mean = self.transformed_data.mean()
            self.transformed_data = (self.transformed_data - self.mean) / self.stddev
        self.tag['normalize']=True
        return
    
    def label(self, labels):
        if isinstance(labels, list):
            if len(labels) != len(self.data.columns):
                raise ValueError('Transform methods and data columns do not match')
        elif isinstance(labels, dict):
            raise TypeError('Dict transform is not yet supported')
        return
    
    def transform_single_series(self, data, how):
        
        "No transformation"
        if isinstance(how, str):
            if how.upper().replace(' ','').replace('-','').replace('_','') in ['NONE','NO','NOTRANSFORMATION']:
                return data
            elif how.upper().replace(' ','').replace('-','').replace('_','') in ['FIRSTDIFFERENCE','FIRSTDIFF']:
                return data.diff(1)
            elif how.upper().replace(' ','').replace('-','').replace('_','') in ['LOGARITHM','LOG']:
                return np.log(data)
            elif how.upper().replace(' ','').replace('-','').replace('_','') in ['LOGARITHMRETURN','LOGRETURN']:
                return np.log(data)
        else:
            if how in [0, None]:
                return data
            if how in [1]:
                return data.diff(1)
            if how in [2]:
                return np.log(data)
            if how in [3]:
                return np.log(data) - np.log(data).shift(1)
    
        
if __name__ =="__main__":
    pass