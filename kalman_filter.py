# -*- coding: utf-8 -*-
"""
Created on Tue Feb 10 11:13:17 2026

@author: tongh
"""


from datetime import datetime, timedelta, date, time
import statsmodels.api as sm
import pandas as pd
import numpy as np
from eqdogubako.bbgubako.function import BloombergAPI
bbg = BloombergAPI()


# Model settings and notations see: https://www.kaggle.com/code/residentmario/kalman-filters


class KalmanFilter():
    def __init__(self):
        return
    
    def one_step_forward(self, x, P, A, H, z, R, Q, B=None, u=None):
        # x: last state vector, must be column vector
        # A: current transition matrix: xk = Axk-1 + Buk + w
        # u: current control vector
        # B: current control matrix
        # P: last state covariance
        # Q: last control covariance, w~N(0,Q)
        # H: current sensor matrix
        # z: current observed reading, must be column vector, z = Hx + v
        # R: current reading uncertainty covariance, v~N(0,R)
        
        x, P, A, H, z, R, Q, B, u = self.regulate_dimension(x, P, A, H, z, R, Q, B, u)
        
        # Step 1: predict
        x_priori = A.dot(x) if B is None and u is None else A.dot(x) + B.dot(u)
        P_priori = A.dot(P).dot(A.T) + Q
        
        # Step 2: Kalman Gain
        K = P_priori.dot(H.T).dot(np.linalg.inv(H.dot(P_priori).dot(H.T)+R))
        
        # Step 3: Estimate with measurement reading z
        x_posteriori = x_priori + K*(z-H.dot(x_priori))
        
        # Step 4: Update error covariance
        P_posteriori = P_priori - K*H.dot(P_priori)
        
        return x_posteriori, P_posteriori
    
    def regulate_dimension(self, x, P, A, H, z, R, Q, B=None, u=None):
        x = np.asmatrix(x)
        P = np.asmatrix(P)
        A = np.asmatrix(A)
        H = np.asmatrix(H)
        if x.shape[1] != 1:
            raise ValueError("x must be a vertical vector.")
        if H.shape[1] != x.shape[0]:
            raise ValueError("H’s column dimension does not match x’s row dimension.")
        if H.shape[0] != z.shape[0]:
            raise ValueError("H’s row dimension does not match z’s row dimension.")
        if x.shape[1] != z.shape[1]:
            raise ValueError("x’s column dimension does not match z’s colum dimension.")
        if A.shape[1] != x.shape[0]:
            raise ValueError("A’s column dimension does not match x’s row dimension.")
        return x, P, A, H, z, R, Q, B, u

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    kf = KalmanFilter()
    
    start_date = date(2020,1,1)
    
    industry_groups = pd.read_excel('S:\\eqdldndata\\master_data\\macro_research\\sector_capital_flow.xlsx','sector_of_interest')
    stocks = dict(zip(industry_groups['index_ticker'], industry_groups['gics_name']))
    stocks_hist = bbg.BQL(list(stocks.keys()),'DAY_TO_DAY_TOT_RETURN_GROSS_DVDS', start_date, field_header=False).fillna(0).rename(columns=stocks)
    
    funds = pd.read_excel('S:\\eqdldndata\\master_data\\macro_research\\sector_capital_flow.xlsx','funds')#.iloc[0]
    
    fund_holdings = []
    fund_flow = []
    
    for fund in funds['fund_ticker']:
        fund_hist = bbg.BDH(fund,'DAY_TO_DAY_TOT_RETURN_GROSS_DVDS', start_date)
        fund_asset = bbg.BDH(fund,'FUND_TOTAL_ASSETS', start_date)
    
        dates = pd.Series(list(set.intersection(set(fund_hist.index), set(stocks_hist.index)))).sort_values().reset_index(drop=True)
        weights = pd.DataFrame(data=np.nan, index=dates, columns=[val for key, val in stocks.items()])
        x = np.asmatrix(np.ones(len(stocks_hist.columns)) / len(stocks_hist.columns)).T
        P = np.zeros((len(stocks_hist.columns), len(stocks_hist.columns)))
        Q = np.eye(len(stocks_hist.columns)) * 0.001
        R = np.eye(1) * 0.001
        for i in range(1, len(dates)):
            A = np.eye(len(stocks_hist.columns))
            H = np.asmatrix(stocks_hist.loc[dates[i]].values)
            z = np.asmatrix(fund_hist.loc[dates[i]].values)
            x, P = kf.one_step_forward(x, P, A, H, z, R, Q)
            x[x<0]=0
            x = x/x.sum()
            weights.loc[dates[i-1]] = x.T.tolist()[0]
        
        holdings = pd.DataFrame(index=weights.index, data=np.nan, columns=weights.columns)
        for i in range(len(holdings.index)):
            try:
                nav = fund_asset[fund_asset.index<=holdings.index[i]].iloc[-1,0]
                holdings.iloc[i] = nav * weights.iloc[i]
            except:
                pass
        fund_holdings += [holdings.fillna(0)]
        
        flow = pd.DataFrame(index=holdings.index, data=np.nan, columns=holdings.columns)
        for i in range(1, len(flow.index)):
            try:
                flow.iloc[i] = (holdings.iloc[i] - holdings.iloc[i-1] * (1 + stocks_hist.iloc[i] / 100)).values
            except:
                pass
        fund_flow += [flow.fillna(0)]
    
    fund_holdings = sum(fund_holdings).replace(0,np.nan).dropna(how='all').fillna(0)
    fund_flow = sum(fund_flow).replace(0,np.nan).dropna(how='all').fillna(0)/1000
    
    all_funds_weights = fund_holdings.div(fund_holdings.sum(axis=1), axis=0)
    
    sectors = ['Software','IT Services','Semiconductors']
    sectors = ['Materials','Capital Goods','Semiconductors']
   
    cumulative_flow = fund_flow.iloc[-126:].cumsum()-fund_flow.iloc[-126]
    
    cumulative_flow.plot(figsize=(7, 4.8))
    plt.show()
    
    colors = ['#A30000', '#0E345B', '#6E7E85', '#507AB5']
    fig, ax = plt.subplots(figsize=(7, 4.8))
    for i in range(len(sectors)):
        ax.plot(cumulative_flow.index, cumulative_flow[sectors[i]], color=colors[i], linewidth=2, label=sectors[i])
    legend = ax.legend(frameon=True)
    legend.get_title().set_horizontalalignment('left')
    legend_texts = legend.get_texts()
    for text in legend_texts:
        text.set_horizontalalignment('left')  # Align left
        text.set_position((0, text.get_position()[1]))  # Set horizontal position to 0
    ax.grid(which='major', linestyle='--', alpha=0.4)
    plt.ylabel(f"Cumulative Fund Flow ($bn) Since {cumulative_flow.index[0]}", fontsize=12, fontweight='semibold')
    plt.tight_layout()
    plt.show()
    
    igv_flow = bbg.BDH('IGV US Equity','FUND_FLOW', date(2022,1,1))
    igv_cumulative_flow = igv_flow.iloc[-126:].cumsum()-igv_flow.iloc[-126]
    fig, ax = plt.subplots(figsize=(7, 4.8))
    ax.plot(igv_cumulative_flow.index, igv_cumulative_flow, color=colors[0], linewidth=2, label='IGV US')
    legend = ax.legend(frameon=True)
    legend.get_title().set_horizontalalignment('left')
    legend_texts = legend.get_texts()
    for text in legend_texts:
        text.set_horizontalalignment('left')  # Align left
        text.set_position((0, text.get_position()[1]))  # Set horizontal position to 0
    ax.grid(which='major', linestyle='--', alpha=0.4)
    plt.ylabel(f"Cumulative Fund Flow ($mn) Since {igv_cumulative_flow.index[0]}", fontsize=12, fontweight='semibold')
    plt.tight_layout()
    plt.show()
