# -*- coding: utf-8 -*-
"""
Created on Wed Jul 24 13:42:48 2024

@author: tongh
"""

import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from scipy.optimize import minimize, least_squares
import random
from tqdm import tqdm
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_samples, silhouette_score


class LPPLS():
    def __init__(self, tc_search_space=1, w_search_space=[1,50], m_search_space=[0.001,1], confidence_threshold=0.4, max_dtc=90):
        self.tc_search_space = tc_search_space
        self.max_dtc = max_dtc                            # tc must be within this many obs of t2 to count as a bubble (imminent-crash filter)
        self.w_search_space = w_search_space
        self.m_search_space = m_search_space
        self.confidence_threshold = confidence_threshold
    
    def check_data_format(self, price_hist):
        for i in range(len(list(price_hist.index))):
            if not isinstance(price_hist.index[i], date):
                try:
                    price_hist.index[i] = price_hist.index[i].date()
                except:
                    raise TypeError('Index of the price series must be datetime.date')
        return price_hist

    def regulate_data(self, p, t):
        if len(p) != len(t):
            raise ValueError('p and t must be same length')
            
        if isinstance(p, list):
            p = pd.Series(p).rename('p')
        elif isinstance(p, pd.Series):
            p = p.reset_index(drop=True).rename('p')
        else:
            raise TypeError('p must be list or pd.Series')
        
        if isinstance(t, list):
            t = pd.Series(t).rename('t')
        elif isinstance(t, pd.Series):
            t = t.reset_index(drop=True).rename('t')
        else:
            raise TypeError('p must be list or pd.Series')
        y = np.log(p).rename('y')
        return p, t, y
    
    def generate_linear_terms(self, t, tc, m, w):        # numpy arrays -- no pandas in the hot loop
        dt = np.abs(tc - t)
        log_dt = np.log(dt)
        f = dt ** m
        g = f * np.cos(w * log_dt)
        h = f * np.sin(w * log_dt)
        return f, g, h

    def residuals(self, y, t, tc, m, w):                 # y, t are numpy arrays
        f, g, h = self.generate_linear_terms(t, tc, m, w)
        X = np.column_stack([np.ones_like(f), f, g, h])
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        return y - X @ beta

    
    def estimate_parameters(self, y, t):                 # y, t are numpy arrays
        t1, t2 = t[0], t[-1]
        dt = t2 - t1
        tc0, m0, w0 = t2 + dt/6, 0.5, 10

        result = least_squares(
            fun=lambda params: self.residuals(y, t, params[0], params[1], params[2]),
            x0=[tc0, m0, w0],
            bounds=([t2 + 1, self.m_search_space[0], self.w_search_space[0]],
                    [t2 + self.tc_search_space * dt, self.m_search_space[1], self.w_search_space[1]]),
            method="trf")

        tc, m, w = result.x
        f, g, h = self.generate_linear_terms(t, tc, m, w)
        X = np.column_stack([np.ones_like(f), f, g, h])
        A, B, C1, C2 = np.linalg.lstsq(X, y, rcond=None)[0]   # final linear params (was sm.OLS)
        C = (C1**2 + C2**2)**0.5

        return {
            'A': A,
            'B': B,
            'C': C,
            'C1': C1,                                    # oscillation coefficients (phase) -- needed to rebuild the curve
            'C2': C2,
            'D': m * abs(B) / (w * C),
            'O': w / np.pi * np.log(abs(tc - t1) / abs(tc - t2)),
            'm': m,
            'w': w,
            'tc': tc,
            't1': t1,
            't2': t2,
            'n_obs': len(t),
            'cost': result.cost}                         # 0.5*SSE from least_squares -> per-obs fit quality

    def fit(self, p, t, min_obs=60, max_obs=None, max_sample=200, progress_bar=True):
        index = p.index if isinstance(p, pd.Series) else None   # keep the (dated) price index for plotting
        p, t, y = self.regulate_data(p, t)
        y_arr = y.to_numpy()                              # pull numpy arrays out once, up front
        t_arr = t.to_numpy(dtype=float)
        n = len(t_arr)
        max_obs = n if max_obs is None else max_obs
        lst = list(range(n))[-max_obs:-min_obs]           # window start positions

        if len(lst) <= max_sample:
            samples = lst
        else:
            idx = np.linspace(0, len(lst)-1, max_sample, dtype=int)
            samples = [lst[i] for i in idx]
        samples.sort()

        params = {}
        iteration = tqdm(range(len(samples))) if progress_bar else range(len(samples))
        for k in iteration:
            s = samples[k]
            params[k] = self.estimate_parameters(y_arr[s:], t_arr[s:])
        return LPPLSResult(p=p, t=t, params=pd.DataFrame(params).T, index=index, max_dtc=self.max_dtc)
        
        
    
class LPPLSResult:
    def __init__(self, p, t, params, index=None, max_dtc=90):
        self.p = p
        self.t = t
        self.index = index                            # original (dated) price index, or None if p was a list
        self.max_dtc = max_dtc                         # tc-distance cap used by is_bubble (imminent-crash filter)
        self.params = self.bubble_filter(params)
    
    def is_bubble(self, B, D, O, m, w, t1, t2, tc):
        condition1 = B < 0
        condition2 = 0.01 < m < 0.99
        condition3 = 4 < w < 25
        condition4 = t2+1 <= tc <= min(2*t2-t1-1, t2 + self.max_dtc)   # tc in the future AND within max_dtc (not a far-off drift)
        condition5 = D >= 0.6
        condition6 = O >= 2.5 # if abs(self.C/self.B)>=0.05 else True
        return condition1 and condition2 and condition3 and condition4 and condition5 and condition6
    
    def bubble_filter(self, params):
        params['bubble'] = params.apply(lambda est: self.is_bubble(B=est['B'], D=est['D'], O=est['O'], m=est['m'], w=est['w'], t1=est['t1'], t2=est['t2'], tc=est['tc']), axis=1)
        return params
        
    
    def bubble_probability(self, obs_range=None):
        if obs_range is None:
            subset = self.params.copy()
            cutoff = subset.loc[subset['bubble'],'t1'].min()
            subset = subset[subset['t1']>=cutoff]
        elif isinstance(obs_range, tuple) and len(obs_range)==2:
            subset = self.params[(self.params['n_obs']>=min(obs_range))&(self.params['n_obs']<=max(obs_range))]
        else:
            return ValueError('obs_range must be None or a two-element tuple')
        if len(subset.index) <= 30:
            raise ValueError('Sample size to small to estimate bubble probability')
        return len(subset[subset['bubble']==True].index) / len(subset.index)
    
    def predict_crash(self):
        bubbles = self.params[(self.params['bubble']==True)].copy()
        self.params['cluster'] = -1                   # kmeans group of each bubble (-1 = not a bubble / unclustered)

        silhouette = -1
        cluster_labels = None
        n_clusters=1
        
        prediction = pd.DataFrame(columns=['cluster','n','prob','t2','tc_mean','tc_std','tc_min','tc_max'])
        
        if len(np.unique(bubbles['tc'])) == 1:
            self.params.loc[bubbles.index, 'cluster'] = 0
            prediction.loc[0] = [0, len(bubbles['tc']), 1, bubbles['t2'].iloc[0], bubbles['tc'].mean(), bubbles['tc'].std(), min(bubbles['tc']), max(bubbles['tc'])]
            return prediction
                                        
        n_distinct = len(np.unique(bubbles['tc']))    # cap clusters at distinct tc's -> no KMeans warning
        for i in range(2, min(5, n_distinct + 1)):
            kmeans = KMeans(n_clusters=i)
            labels = kmeans.fit_predict(np.array(bubbles['tc']).reshape(-1, 1))
            silhouette_avg = silhouette_score(np.array(bubbles['tc']).reshape(-1, 1), labels)
            
            if silhouette_avg > silhouette:
                silhouette = silhouette_avg
                cluster_labels = labels
                n_clusters=i 
        
        bubbles['cluster'] = cluster_labels
        self.params.loc[bubbles.index, 'cluster'] = cluster_labels   # write group back onto params

        for i in range(n_clusters):
            subset = bubbles[bubbles['cluster']==i]
            tc_mean, tc_std = subset['tc'].mean(), subset['tc'].std()
            tc_min, tc_max = min(subset['tc']), max(subset['tc'])
            t2 = subset['t2'].iloc[0]
            prediction.loc[len(prediction.index)] = [i, len(subset.index), len(subset.index)/len(bubbles.index), t2, tc_mean, tc_std, tc_min, tc_max]

        return prediction

    def best_fit(self, cluster=None, top_k=5):
        # Distill ONE coherent fit from the dominant tc-cluster: the lowest per-observation RMSE window
        # (best explains the data, so its tc/w/phase are the ones to trust for trough timing / the drawn
        # curve). Also returns R = circular resultant of the top_k phases in [0,1]: R~1 the good fits agree
        # on phase (troughs meaningful), R~0 the log-periodicity is not identified (drop trough timing).
        if 'cluster' not in self.params.columns:
            self.predict_crash()
        grouped = self.params[self.params['cluster'] >= 0]
        if not len(grouped):
            raise ValueError('no bubble cluster to distill')
        cl = cluster if cluster is not None else grouped['cluster'].value_counts().idxmax()

        fits = self.params[self.params['cluster'] == cl].copy()
        fits['rmse'] = np.sqrt(2 * fits['cost'] / fits['n_obs'])   # per-obs residual (log space) -- window-length fair
        fits['score'] = fits['rmse'] / np.sqrt(fits['O'])         # length-aware: reward low residual AND many cycles (O)
        fits = fits.sort_values('score')                          # -> longer, better-resolved windows win over short lucky ones
        top = fits.head(top_k)
        phi = np.arctan2(top['C2'], top['C1'])
        R = float(np.hypot(np.cos(phi).mean(), np.sin(phi).mean()))
        return fits.iloc[0], R

    def fitted_curve(self, cluster=None, band=(25, 75)):
        # Reconstruct the LPPLS fit for the highest-prob tc cluster (or a given one). Each qualifying
        # fit in that cluster is rebuilt on a common trading-day grid over its own window .. tc; the
        # pointwise MEDIAN (+ band percentiles) across fits is the representative curve. Returns a
        # price-space DataFrame ['fit','fit_lo','fit_hi','price'] indexed by trading-day position.
        if 'cluster' not in self.params.columns:
            self.predict_crash()                          # populate the cluster labels
        grouped = self.params[self.params['cluster'] >= 0]
        if not len(grouped):
            raise ValueError('no bubble cluster to reconstruct')
        if cluster is None:
            cluster = grouped['cluster'].value_counts().idxmax()      # dominant = highest-prob cluster

        fits = self.params[self.params['cluster'] == cluster]
        tc = fits['tc'].mean()                            # cluster crash time -- LPPLS is only defined for t < tc
        grid = np.arange(0, int(np.ceil(tc)))             # stop at the crash: never draw t >= tc
        curves = []
        for _, r in fits.iterrows():
            dt = r['tc'] - grid
            ok = (dt > 0) & (grid >= r['t1'])             # this fit's window start .. its own critical time
            log_dt = np.log(dt[ok])
            fpow = dt[ok] ** r['m']
            yfit = r['A'] + r['B']*fpow + r['C1']*fpow*np.cos(r['w']*log_dt) + r['C2']*fpow*np.sin(r['w']*log_dt)
            s = pd.Series(np.nan, index=grid)
            s[grid[ok]] = np.exp(yfit)                    # log-price -> price
            curves.append(s)
        mat = pd.concat(curves, axis=1)

        out = pd.DataFrame({'fit': mat.median(axis=1),
                            'fit_lo': mat.quantile(band[0] / 100, axis=1),
                            'fit_hi': mat.quantile(band[1] / 100, axis=1),
                            'coverage': mat.notna().mean(axis=1)})   # fraction of cluster fits defined at each t
        price = pd.Series(self.p.values, index=self.t.values)   # price indexed by the fit's time variable t
        out['price'] = price.reindex(out.index)                 # actual price where it exists (NaN past t2 = extrapolation)
        return out

    def _t_to_x(self, tvals):
        # Map model t-values -> plotting x. Dates if we captured a dated index at fit time, else the raw t.
        tvals = np.asarray(tvals, dtype=float)
        if self.index is None:
            return tvals
        if np.array_equal(self.t.values, np.arange(len(self.t))):        # trading-day t (position == t)
            n = len(self.index)
            x = [self.index[k] if k < n else self.index[-1] + pd.offsets.BDay(k - (n - 1))
                 for k in np.round(tvals).astype(int)]                   # in-sample dates, then business days past the end
            return pd.DatetimeIndex(x)
        return pd.DatetimeIndex(self.index[0] + pd.to_timedelta(tvals, unit='D'))   # calendar-day t -> offset from t0

    def plot(self, cluster=None, band=(25, 75), mode='fit', troughs=True, ylabel='price', ax=None):
        # Price with the ensemble 25-75 band and, depending on mode, either the single distilled best_fit
        # curve ('fit', default -- one coherent oscillation, annotated with its phase-coherence R) or the
        # smooth ensemble median ('median'). In 'fit' mode the log-periodic troughs are marked. Dotted line
        # at the crash tc. Dates on the x-axis when a dated index was captured at fit time.
        try:
            import matplotlib.pyplot as plt
            from matplotlib.patches import Patch
        except ImportError:
            raise ImportError('matplotlib is required for LPPLSResult.plot()')

        if 'cluster' not in self.params.columns:
            self.predict_crash()
        grouped = self.params[self.params['cluster'] >= 0]
        cl = cluster if cluster is not None else grouped['cluster'].value_counts().idxmax()

        curve = self.fitted_curve(cl, band)
        x = self._t_to_x(curve.index.values)
        lo, hi, cov = curve['fit_lo'].values, curve['fit_hi'].values, curve['coverage'].values
        ax = ax or plt.gca()
        handles = [ax.plot(x, curve['price'].values, '-', color='0.4', lw=1, label='price')[0]]

        base = 0.20                                               # band alpha fades with ensemble coverage
        step = max(1, len(x) // 400)                              # -> dims where fits thin out (start + into tc)
        for i in range(0, len(x) - 1, step):
            j = min(i + step, len(x) - 1)
            a = base * np.nanmean(cov[i:j + 1])
            if a > 0.01:
                ax.fill_between(x[i:j + 1], lo[i:j + 1], hi[i:j + 1], color='steelblue', alpha=a, lw=0)
        handles.append(Patch(facecolor='steelblue', alpha=base, label=f'ensemble {band[0]}-{band[1]} band'))

        if mode == 'median':
            handles.append(ax.plot(x, curve['fit'].values, '--', label='ensemble median')[0])
            tc = self.params.loc[self.params['cluster'] == cl, 'tc'].mean()
        else:                                                     # 'fit' -- distilled coherent curve
            best, R = self.best_fit(cl)
            grid = np.arange(int(best['t1']), int(np.ceil(best['tc'])))
            dt = best['tc'] - grid
            y = (best['A'] + best['B'] * dt ** best['m']
                 + best['C1'] * dt ** best['m'] * np.cos(best['w'] * np.log(dt))
                 + best['C2'] * dt ** best['m'] * np.sin(best['w'] * np.log(dt)))
            handles.append(ax.plot(self._t_to_x(grid), np.exp(y), '-', color='crimson', lw=1.3,
                                   label=f'best fit (R={R:.2f})')[0])
            if troughs:
                phi = np.arctan2(best['C2'], best['C1'])
                tr = [best['tc'] - np.exp(((2 * k + 1) * np.pi + phi) / best['w']) for k in range(80)]
                tr = [v for v in tr if best['t1'] < v < best['tc']]   # log-periodic minima inside the window..tc
                for v in tr:
                    ax.axvline(self._t_to_x([v])[0], color='green', ls=':', lw=0.7, alpha=0.7)
            tc = best['tc']

        ax.axvline(self._t_to_x([tc])[0], color='0.5', ls='--', lw=1)   # crash tc
        ax.set_ylabel(ylabel)
        ax.legend(handles=handles)
        return ax


if __name__ == '__main__':

    from tongubako.ibkrkkun import IBKR

    ibkr = IBKR(port=7497, client_id=2, market_data_type='delayed')
    ibkr.connect()
    adi = ibkr.get_stock('CSX')                     # Analog Devices (ADI US Equity)
    bars = ibkr.get_historical_data(adi, duration='2 Y', bar_size='1 day')
    ibkr.disconnect()

    p = bars.set_index('date')['close'].dropna()
    t = pd.Series([(x - p.index[0]).days for x in p.index])

    test = LPPLS()
    test3 = test.fit(p, t, 30, 500, 400, progress_bar=True)
    
    fuck1 = test3.bubble_probability((100,250))
    fuck3 = test3.predict_crash()
    burst = p.index[-1] + timedelta(days=sum((fuck3['tc_mean'] - fuck3['t2']) * fuck3['prob']))
    fuck2 = test3.params

    fuck4 = test3.fitted_curve()                               # raw curve df: fit / band / price / coverage, by t
    fuck5, R = test3.best_fit()                                # distilled coherent fit + phase-coherence R (0..1)
    ax = test3.plot(ylabel='USD')                             # price + best_fit (crimson) + faded band + troughs + tc
    #   mode='median' for the smooth ensemble trend instead; troughs=False to drop the green markers

# =============================================================================
#     t2 = date(2015,6,5)
#     t1 = t2 - timedelta(days=365)
#     dates = pd.Series(pd.date_range(start=t1, end=t2, freq='W')).apply(lambda x: x.date())
#     bubble_prob = pd.Series(index=dates, name='bubble_prob', data=np.nan)
# 
#     for i in range(len(bubble_prob)):
#         t2 = dates.iloc[i]
#         data = bbg.BDH('SHCOMP Index','PX_Last', start_date=t2 - timedelta(days=600), end_date=t2).squeeze().dropna()
#         p = data.squeeze()
#         t = pd.Series([(x-data.index[0]).days for x in data.index])
#         model = LPPLS()
#         test3 = model.fit(p, t, 50, 250, 200, progress_bar=False)
#         bubble_prob.iloc[i] = test3.bubble_probability()
#     fuck3 = test3.predict_crash()
#     burst = t2+timedelta(days=sum((fuck3['tc_mean']-fuck3['t2'])*fuck3['prob']))
# 
# =============================================================================
