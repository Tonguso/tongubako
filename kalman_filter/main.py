# -*- coding: utf-8 -*-
"""
Created on Thu Apr 25 22:33:46 2024

@author: Hogan
"""

from datetime import datetime, timedelta, time, date
import pandas as pd
import numpy as np
from statsmodels.tsa.ar_model import AR

class KalmanFilter:
    def __init__(self):
        return



def update_one_step(x, z, P, F, H, R, Q=None, B=None, u=None):
    
    # Predict Step
    xNextPred = F.dot(x) if B is None else F.dot(x) + B.dot(u)
    pNextPred = F.dot(P).dot(F.T) if Q is None else F.dot(P).dot(F.T) + Q
    
    # Update Step
    K = P.dot(H.T).dot(np.linalg.inv(H.dot(P).dot(H.T)+R))
    xNextUpdt = xNextPred + K.dot(z-H.dot(xNextPred))
    pNextUpdt = pNextPred - K.dot(H).dot(pNextPred)
    
    result = {
        'xPosteriori':xNextPred,
        'PPosteriori':pNextPred,
        'xPriori':xNextUpdt,
        'PPriori':pNextUpdt,
        'K':K,   
        }
    
    return result