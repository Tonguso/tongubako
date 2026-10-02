# -*- coding: utf-8 -*-
"""
Created on Tue Jul 08 2026

@author: Hogan

OpenBB session/setup -- the analogue of bbgubako.admin (which opens a blpapi session).
There is no persistent session in OpenBB: `obb` is a process-wide singleton, so this
just imports it, optionally loads credentials, and hands the handle back.
"""


def initiate_openbb(credentials=None):
    try:
        from openbb import obb
    except ImportError as e:
        raise ImportError("openbbg requires the OpenBB Platform -- `pip install openbb`") from e

    if credentials:                                 # e.g. {'fmp_api_key': '...', 'polygon_api_key': '...'}
        for key, value in credentials.items():
            try:
                setattr(obb.user.credentials, key, value)
            except Exception:
                pass
    return obb


def stop_openbb(obb):
    return None                                     # nothing to tear down; kept for API symmetry
