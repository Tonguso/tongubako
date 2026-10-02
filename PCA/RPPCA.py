# -*- coding: utf-8 -*-
"""
Created on Fri Apr 26 18:33:57 2024

@author: homoi
"""

 
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os
import math 
import matplotlib.pyplot as plt
from datetime import datetime,timedelta,date,time
 
 
 
class RPPCA():
    def __init__(self, n_components=None, gamma=-1, sign_convention='first_eigen_positive'):
        self.n_components = n_components
        self.gamma = gamma
        self.sign_convention = sign_convention
        
    def _X(self, X: pd.DataFrame):
        if isinstance(X, pd.DataFrame):
            self.X = np.mat(X)
            self._T = pd.Series(X.index)
            self._N = pd.Series(X.columns)
            self.df = True
        elif isinstance(X, np.mat):
            self.X = X
            self.df = False
        self.X_mean = self.X.mean(axis=0).T
        self.N = len(X.columns)
        self.T = len(X.index)
        self.K = self.n_components
        return
    
    def _pseudo_cov_matrix(self):
        self.pseudo_cov_matrix = (1/self.T)*self.X.T.dot(self.X)+self.gamma*self.X_mean.dot(self.X_mean.T)
        return
    
    def eigen_decomposition(self):
        self.eigenvalues, self.eigenvectors = np.linalg.eig(self.pseudo_cov_matrix)
        return
    
    def _loadings(self):
        self.loadings = np.real(self.eigenvectors[:,:self.n_components]) # There should not be any complex number in eigenvectors of a symmetric matrix
        if self.sign_convention == 'first_eigen_positive':
            self.loadings = self.loadings if np.sign(self.loadings[0,0])>0 else -self.loadings
        elif self.sign_convention == 'first_eigen_negative':
            self.loadings = -self.loadings if np.sign(self.loadings[0,0])>0 else self.loadings
        return self.loadings
    
    def _factorsOLS(self):
        temp = self.X.dot(self.loadings)
        self.factors = pd.DataFrame(index=self._T, columns=['factor_'+str(int(i)) for i in range(self.n_components)], data=temp)
        return
    
    def fit(self, X):
        self._X(X)
        self._pseudo_cov_matrix()
        self.eigen_decomposition()
        self._loadings()
        self._factorsOLS()
        self.residuals = self.X - self.factors.dot(self.loadings.T)
        self.Xfitted = self.factors.dot(self.loadings.T)
        return
 
 
if __name__ == '__main__':
    pass