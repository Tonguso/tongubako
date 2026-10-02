# -*- coding: utf-8 -*-
"""
Created on Sun May 12 11:29:04 2024

@author: Hogan
"""

import numpy as np
import pandas as pd
import datetime as dt
from tongubako.utils import guess_frequency
import matplotlib.pyplot as plt 

colors = ['#BF2026','#0A3D66','#6699CC','#A6A6A6']

class Constructor():
    __slots__ = [
        "x",
        "y",
        "chart_type",
        "style",
        "width",
        "figsize",
        "color",
        "x_title",
        "y_title",
        "z_title",
        "chart_title",
        "axis_title",
        "axis_range",
        "axis_shift",
        "axis",
        "labels", 
        "order",
        "axis_invert",
    ]
    
    def __init__(self):
        self.reset()
        
    def reset(self):
        self.x, self.y = None, None
        self.chart_type = 'line'
        self.style = {}
        self.width = {}
        self.figsize = (8,5)
        self.color = {}
        self.x_title, self.y_title, self.z_title, self.chart_title = None, None, None, None
        self.axis = {}
        self.axis_title = {}
        self.axis_invert = {'L1':False,'L2':False,'R1':False,'R2':False,'R3':False}
        self.axis_range = {'L1':None,'L2':None,'R1':None,'R2':None,'R3':False}
        self.labels = {}
        self.axis_range = {}
        self.order = {}
    
    def regulate_data(self, x, y):
        if isinstance(y, list):
            y = pd.concat(y, axis=1)
        elif isinstance(y, pd.Series):
            y = y.to_frame()
        if len(x) != len(y.index):
            raise ValueError("x and y must have the same length")
        return x, y
    
    def add_data(self, x, y):
        self.x, self.y = self.regulate_data(x, y)
    
    def add_labels(self, labels_mapping=None):
        if self.y is None:
            raise ValueError("Add data before adding labels, use the add_data function")
        
        for i in range(len(self.y.columns)):
            self.labels[self.y.columns[i]] = self.y.columns[i]
        
        if labels_mapping is None:
            pass
        elif isinstance(labels_mapping, list):
            for i in range(len(self.y.columns)):
                self.labels[self.y.columns[i]] = labels_mapping[i]
        elif isinstance(labels_mapping, dict):
            self.labels = labels_mapping
            for i in range(len(self.y.columns)):
                if self.y.columns[i] not in labels_mapping.keys():
                    self.labels[self.y.columns[i]] = self.y.columns[i]

    def set_axis(self, axis_mapping=None):
        if not bool(self.labels):
            raise ValueError("Add labels before setting axis, use the add_labels function")
        if axis_mapping is None:
            for i in range(len(self.y.columns)):
                self.axis[self.y.columns[i]] = 'L1'
        elif isinstance(axis_mapping, list):
            for i in range(len(self.y.columns)):
                self.axis[self.y.columns[i]] = axis_mapping[i]
        elif isinstance(axis_mapping, dict):
            for i in range(len(self.y.columns)):
                if self.y.columns[i] not in axis_mapping.keys():
                    self.axis[self.y.columns[i]] = self.y.columns[i]
    
    def set_color(self, color_mapping=None):
        if not bool(self.labels):
            raise ValueError("Add labels before setting axis, use the add_labels function")
        
        for i in range(len(self.y.columns)):
            self.color[self.y.columns[i]] = colors[i]
        if color_mapping is None:
           pass
        elif isinstance(color_mapping, list):
            for i in range(len(self.y.columns)):
                self.color[self.y.columns[i]] = color_mapping[i]
        elif isinstance(color_mapping, dict):
            for i in range(len(self.y.columns)):
                if self.y.columns[i] not in color_mapping.keys():
                    self.color[self.y.columns[i]] = self.y.columns[i]
    
    def set_order(self, order_mapping=None):
        if not bool(self.labels):
            raise ValueError("Add labels before setting axis, use the add_labels function")
        
        for i in range(len(self.y.columns)):
            self.order[self.y.columns[i]] = 10-i
        if order_mapping is None:
           pass
        elif isinstance(order_mapping, list):
            for i in range(len(self.y.columns)):
                self.order[self.y.columns[i]] = order_mapping[i]
        elif isinstance(order_mapping, dict):
            for i in range(len(self.y.columns)):
                if self.y.columns[i] not in order_mapping.keys():
                    self.order[self.y.columns[i]] = self.y.columns[i]
    
    def add_axis_titles(self, axis_titles_mapping=None):
        if not bool(self.axis):
            raise ValueError("Set axis before adding axis titles, use the set_axis function")
        
        if axis_titles_mapping is None:
            for key, item in self.axis.items():
                label = self.labels[key]
                self.axis_title[item] = label               
        elif isinstance(axis_titles_mapping, dict):
            self.axis_title = axis_titles_mapping
        else:
            raise TypeError("axis_title_mapping must be a dictionary")
        return
    
    def set_axis_range(self, axis_range_mapping=None):
        
        for key, item in self.axis.items():
            self.axis_range[item] = None
        
        if axis_range_mapping is None:
            pass
        elif not isinstance(axis_range_mapping, dict):
            raise TypeError("axis_range_mapping must be a dictionary")
        else:
            for key, item in axis_range_mapping.items():
                if key.upper() not in ['L1','L2','L3','R1','R2','R3']:
                    raise ValueError('Unrecognized axis')
                self.axis_range[key] = item
        return
    
    def set_style(self, style_mapping=None):
        if not bool(self.labels):
            raise ValueError("Add labels before setting axis, use the add_labels function")
        
        for i in range(len(self.y.columns)):
            self.style[self.y.columns[i]] = None
        if style_mapping is None:
           pass
        elif isinstance(style_mapping, list):
            for i in range(len(self.y.columns)):
                self.style[self.y.columns[i]] = style_mapping[i]
        elif isinstance(style_mapping, dict):
            for key, item in style_mapping.items():
                self.style[key] = item
    
    def set_width(self, width_mapping=None):
        if not bool(self.labels):
            raise ValueError("Add labels before setting axis, use the add_labels function")
        
        for i in range(len(self.y.columns)):
            self.width[self.y.columns[i]] = None
        if width_mapping is None:
           pass
        elif isinstance(width_mapping, list):
            for i in range(len(self.y.columns)):
                self.width[self.y.columns[i]] = width_mapping[i]
        elif isinstance(width_mapping, dict):
            for key, item in width_mapping.items():
                self.width[key] = item
    

    def set_axis_invert(self, axis_invert_mapping=None):
        
        for key, item in self.axis.items():
            self.axis_invert[item] = False
        
        if axis_invert_mapping is None:
            pass
        elif not isinstance(axis_invert_mapping, dict):
            raise TypeError("axis_invert_mapping must be a dictionary")
        else:
            for key, item in axis_invert_mapping.items():
                if key.upper() not in ['L1','L2','L3','R1','R2','R3']:
                    raise ValueError('Unrecognized axis')
                self.axis_invert[key] = item if bool(item) else False
    
    
    def shift_data(self, shift_mapping=None):
        
        return

    def make_figure(self, x, y, labels=None, axis=None, axis_title=None, chart_type='line', figsize=(8,5), axis_range=None, axis_shift=50, color=None, order=None, style=None, width=None, axis_invert=None, *kwargs):
        self.reset()
        self.chart_type = chart_type
        self.add_data(x, y)
        self.add_labels(labels)
        self.set_axis(axis)
        self.add_axis_titles(axis_title)
        self.set_axis_range(axis_range)
        self.set_color(color)
        self.set_order(order)
        self.set_style(style)
        self.set_width(width)
        self.figsize = figsize
        self.axis_shift = axis_shift
        self.set_axis_invert(axis_invert)
        return
        
    


if __name__ == '__main__':
    test = Constructor()