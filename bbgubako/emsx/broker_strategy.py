# -*- coding: utf-8 -*-
"""
Created on Mon Oct 13 14:02:34 2025

@author: tongh
"""


STRATEGY_PARAMS = { # (field, exlcude, default value)
    'CLSW':{
        'VWAP':[
            ('start_time', 0, '09:30:00'),
            ('end_time', 0, '17:00:00'),
            ('target_volume', 0, 20),
            ('style', 0, 'Normal'),
            ('participate_open', 0, 'N'),
            ('participate_close', 0, 'N'),
            ],
        'TWAP':[
            ('start_time', 0, '09:30:00'),
            ('end_time', 0, '17:00:00'),
            ('target_volume', 0, 20),
            ('style', 0, 'Normal'),
            ('participate_open', 0, 'N'),
            ('participate_close', 0, 'N'),
            ],
        'POV':[
            ('start_time', 0, "07:40:00"),
            ('end_time', 0, "17:40:00"),
            ('target_volume', 0, 20),
            ('style', 0, 'Normal'),
            ('participate_open', 0, 'Y'),
            ('participate_close', 0, 'Y'),
            ],
        },
    'CLEA':{
        'VWAP':[
            ('start_time', 0, '09:00:00'),
            ('end_time', 0, '17:00:00'),
            ('style', 0, 'Normal'),
            ('target_volume', 0, 20),
            ],
        'TWAP':[
            ('start_time', 0, '09:00:00'),
            ('end_time', 0, '17:00:00'),
            ('style', 0, 'Normal'),
            ('target_volume', 0, 20),
            ],
        },
    
    }
