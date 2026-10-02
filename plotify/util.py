# -*- coding: utf-8 -*-
"""
Created on Sun May 12 20:47:15 2024

@author: Hogan
"""

import matplotlib.pyplot as plt


def make_patch_spines_invisible(ax):
    ax.set_frame_on(True)
    ax.patch.set_visible(False)
    for sp in ax.spines.values():
        sp.set_visible(False)

        
def move_spine(ax, direction, dist):
    ax.spines[direction].set_position(("axes", dist))
    make_patch_spines_invisible(ax)
    ax.spines[direction].set_visible(True)
    