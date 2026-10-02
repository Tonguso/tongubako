# -*- coding: utf-8 -*-
"""
Created on Tue Jul 08 2026

@author: Hogan

openbbg -- a Bloomberg-flavoured wrapper on top of the OpenBB Platform.

Presents BDH / BDP / BQL / BDS with the same signatures and return shapes as the
`bbgubako` terminal tool, so strategy code runs unchanged whether OpenBB (free data)
or a real Bloomberg terminal sits underneath. This is Bloomberg-*shaped* access to
OpenBB data -- it is not a Bloomberg emulator (see the caveats in main.py).
"""

from .main import OpenBBG

BloombergAPI = OpenBBG            # drop-in alias: swap the import, keep the call sites
