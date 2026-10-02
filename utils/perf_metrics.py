# -*- coding: utf-8 -*-
"""
Created on Mon Nov 17 14:07:18 2025

@author: tongh
"""


from collections import defaultdict
from datetime import datetime, timedelta, date
import pandas as pd
import numpy as np
from scipy.stats import norm
from decimal import Decimal, ROUND_HALF_UP



def perf_metrics(price, rf_rate=None, ann_factor=252):
    ret = price.pct_change()
    if rf_rate is None:
        sharpe = ret.mean() * ann_factor / (ret.std() * np.sqrt(ann_factor))
    else:
        temp = pd.concat([price.pct_change(), rf_rate/365], join='inner', axis=1)
        excess_ret = temp.iloc[:,0] - temp.iloc[:,1]
        sharpe = excess_ret.mean() * ann_factor / (excess_ret.std() * np.sqrt(ann_factor))
    ann_ret = ret.mean() * ann_factor
    std_dev = ret.std() * np.sqrt(ann_factor)
    min_ret = ret.min()
    max_ret = ret.max()
    win_loss_ratio = -ret[ret>0].mean()/ret[ret<0].mean()
    win_rate = len(ret[ret>0])/(len(ret[ret>0])+len(ret[ret<0]))

    sortino = ann_ret / (ret[ret<0].std()*np.sqrt(ann_factor))

    max_drawdown, dd_start, dd_end, _ = max_dd(price)

    var_90 = value_at_risk(ret.iloc[1:], alpha=0.95)
    cvar_90 = cvar(ret.iloc[1:], alpha=0.95)

    return pd.Series([ann_ret, std_dev, sharpe, sortino, win_loss_ratio, win_rate, max_drawdown, dd_start,dd_end,- ann_ret/max_drawdown, min_ret, max_ret, var_90, cvar_90],
                  index=['annual_return', 'std_dev', 'sharpe_ratio','sortino_ratio', 'pl_ratio','win_rate', 'max_dd','dd_start', 'dd_end', 'RoMaD', 'min_return', 'max_return','var_95', 'cvar_95'])

def max_dd(price):
    max_p = 0
    dd = 0
    _max_dd = 0

    dd_start = price.index.min()
    max_dd_start = dd_start
    max_dd_end = dd_start

    max_dd_recovery = timedelta(0)

    for i in range(len(price)):
        cur_p = price[i]
        cur_date = price.index[i]
        if cur_p > max_p:
            max_p = cur_p
            dd_recovery = cur_date - dd_start
            if dd_recovery > max_dd_recovery:
                max_dd_recovery = dd_recovery

            dd_start = cur_date

        dd = cur_p / max_p - 1

        if dd < _max_dd:
            _max_dd = dd
            max_dd_start = dd_start
            max_dd_end = cur_date

    return _max_dd, max_dd_start, max_dd_end, max_dd_recovery

def value_at_risk(returns, alpha=0.95):
    return np.percentile(returns, 100 * (1 - alpha))


def cvar(returns, alpha=0.95):
    var = value_at_risk(returns, alpha)
    return np.nanmean(returns[returns < var])


def accurate_round(data: pd.Series, decimals=4):
    decimal_str = '.'
    for i in range(decimals):
        decimal_str += '0'
    result = data.apply(lambda x: Decimal(str(x)).quantize(Decimal(decimal_str), ROUND_HALF_UP))
    return result.astype('float')

def element_wise_max(s1, s2):
    if len(s1) != len(s2):
        raise ValueError('Series lengths do not match')
    res = [max(l1, l2) for l1, l2 in zip(s1, s2)]
    return res

def element_wise_min(s1, s2):
    if len(s1) != len(s2):
        raise ValueError('Series lengths do not match')
    res = [min(l1, l2) for l1, l2 in zip(s1, s2)]
    return res

if __name__ == '__main__':
    pass