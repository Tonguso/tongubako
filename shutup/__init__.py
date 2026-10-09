# -*- coding: utf-8 -*-
"""
Created on Thu Feb 20 16:50:39 2025

@author: tongh
"""

try:
    from importlib.metadata import version as _version
    __version__ = _version(__name__)
except Exception: pass

import logging as _logging
import warnings as _warnings
_original_warn = None
_catcher = None # catch_warnings context holding an 'ignore' filter
_log_disable = _logging.NOTSET # logging.disable level before muting

def _warn(message:str, category:str='', stacklevel:int=1, source:str='', skip_file_prefixes:tuple=()): # need hints to work with pytorch
    pass # In the future, we can implement filters here. For now, just mute everything.

def please():
    global _original_warn, _catcher, _log_disable
    if _original_warn: return # already muted
    _original_warn = _warnings.warn
    _warnings.warn = _warn
    # Warnings raised from C code (e.g. numpy RuntimeWarning) bypass warnings.warn, so also add an ignore filter
    _catcher = _warnings.catch_warnings()
    _catcher.__enter__()
    _warnings.simplefilter('ignore')
    # Library chatter sent through logging at WARNING or below (e.g. matplotlib findfont, urllib3 retries). ERROR still shows.
    _log_disable = _logging.root.manager.disable
    _logging.disable(max(_log_disable, _logging.WARNING))

def jk():
    global _original_warn, _catcher
    if not _original_warn: return
    _warnings.warn = _original_warn
    _original_warn = None
    if _catcher:
        _catcher.__exit__(None, None, None)
        _catcher = None
    _logging.disable(_log_disable)

def are_warnings_muted():
    return _original_warn != None

class _mute_warnings:
    ''' Mute all warnings. Can also be used as a context manager.'''
    def __call__(self):
        please()
    def __enter__(self):
        self.muted = are_warnings_muted()
        please()
    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.muted: jk()
mute_warnings = _mute_warnings()

class unmute_warnings:
    ''' Unmute warnings if previously muted. Otherwise, do nothing. Can also be used as a context manager. '''
    def __call__(self):
        jk()
    def __enter__(self):
        self.muted = are_warnings_muted()
        jk()
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.muted: please()
unmute_warnings = unmute_warnings()