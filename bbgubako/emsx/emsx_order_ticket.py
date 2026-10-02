# -*- coding: utf-8 -*-
"""
Created on Thu Apr  9 18:30:17 2026

@author: tongh
"""

# emsx_order_ticket.py

from __future__ import annotations

from dataclasses import dataclass, field, fields, asdict
from datetime import time
from typing import Optional, Literal, Dict, Any
import random
from datetime import datetime

if __name__ != '__main__':
    from . import admin, broker_strategy
else:
    import admin, broker_strategy



# ================================
# Layer 1 — Order Intent
# ================================

VALID_SIDES = {"BUY", "SELL", "SHRT", "COVR"}
VALID_ORD_TYPES = {"MKT", "LMT"}

def check_order_type(order_type):
    if not isinstance(order_type, str):
        raise TypeError('order_type must be a string')
    if order_type.upper() in ['MKT','MARKET']:
        return 'MKT'
    elif order_type.upper() in ['LMT','LIMIT']:
        return 'LMT'
    else:
        raise ValueError('Unrecognized order type. Must be "MKT" or "LMT".')

def check_side(side):
    if side.upper().replace(' ','') not in ['BUY','SELL','SHRT','COVR']:
        return TypeError('Unrecognized side type')
    return side.upper().replace(' ','')

def check_order_type_logic(parent_order, execution_config):
    if parent_order.order_type=='MKT':
        return (execution_config.order_type, execution_config.limit_price)
    else:
        if execution_config.order_type == 'MKT':
            return (execution_config.order_type, execution_config.limit_price)
        else:
            if execution_config.limit_price is None:
                return (execution_config.order_type, parent_order.limit_price)
            if parent_order.side in ['BUY','COVR']:
                if execution_config.limit_price > parent_order.limit_price:
                    print("The child's limit price exceeds the parent's limit price in a buy order; the routed limit price will be set to the parent's level.")
                return (execution_config.order_type, min(execution_config.limit_price, parent_order.limit_price))
            elif parent_order.side in ['SELL','SHRT']:
                if execution_config.limit_price < parent_order.limit_price:
                    print("The child's limit price is below the parent's limit price in a sell order; the routed limit price will be set to the parent's level.")
                return (execution_config.order_type, max(execution_config.limit_price, parent_order.limit_price))
            else:
                raise TypeError('Unrecognized order side')

def check_order_amount_logic(parent_order, execution_config):
    amount = execution_config.quantity if execution_config.quantity is not None else int(parent_order.quantity*execution_config.target_pct_quantity/100)
    return amount

def rectify_parent_and_child(parent_order, execution_config):
    order_type, limit_price = check_order_type_logic(parent_order, execution_config)
    quantity = check_order_amount_logic(parent_order, execution_config)
    return order_type, limit_price, quantity

def parse_emsx_sequence(emsx_sequence):
    success = emsx_sequence.hasElement('MESSAGE')
    
    if success:
        message = emsx_sequence['MESSAGE']
    elif emsx_sequence.hasElement('ERROR_MESSAGE'):
        message = emsx_sequence['ERROR_MESSAGE']
        
    order_id = emsx_sequence['EMSX_SEQUENCE'] if emsx_sequence.hasElement('EMSX_SEQUENCE') else None
    route_id = emsx_sequence['EMSX_ROUTE_ID'] if emsx_sequence.hasElement('EMSX_ROUTE_ID') else None

    return {'success':success, 'message':message, 'order_id': order_id, 'route_id': route_id}

@dataclass
class ParentOrder:  # Pure trading intent. No EMSX / broker logic.
    ticker: str
    quantity: int
    side: str
    order_type: str = "MKT"
    limit_price: Optional[float] = None
    account: Optional[str] = None
    basket_name: Optional[str] = None
    cfd: Optional[int] = 0

    def __post_init__(self):

        self.side = check_side(self.side)
        self.order_type = check_order_type(self.order_type)

        if self.side not in VALID_SIDES:
            raise ValueError(f"Invalid side: {self.side}")

        if self.order_type not in VALID_ORD_TYPES:
            raise ValueError(f"Invalid order type: {self.order_type}")

        if self.quantity <= 0:
            raise ValueError("quantity must be positive")

        if self.order_type == "LMT" and self.limit_price is None:
            raise ValueError("Limit order requires limit_price")

    
    def generate_summary(self, emsx_sequence):
        parsed_sequence = parse_emsx_sequence(emsx_sequence)  # dict-like

        allowed = {f.name for f in fields(OrderSummary) if f.init}
        filtered_sequence = {k: v for k, v in dict(parsed_sequence).items() if k in allowed}

        summary_kwargs = {
            **asdict(self),  # All ParentOrder fields
            **filtered_sequence,
            "create_time": datetime.now(),
            "last_update": datetime.now(),
        }

        return OrderSummary(**summary_kwargs)




@dataclass
class OrderSummary:  # Pure trading intent. No EMSX / broker logic.
    ticker: str
    quantity: int
    side: str
    order_type: str
    order_id: int
    limit_price: Optional[float] = None
    account: Optional[str] = None
    basket_name: Optional[str] = None
    create_time: Optional[datetime] = None
    cfd: Optional[int] = None
    message: Optional[str] = None
    success: Optional[bool] = None
    last_update: Optional[datetime] = None

    # Internal flag to avoid stamping last_update during __init__/post_init
    _initialized: bool = field(default=False, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        self._initialized = True

    
    def __setattr__(self, name: str, value):
        if getattr(self, "_initialized", False) and name not in {"last_update", "_initialized"}:
            if getattr(self, name, None) != value:
                super().__setattr__("last_update", datetime.now())
        super().__setattr__(name, value)
    
    def show(self):
        print(self.ticker.replace(' Equity',''), self.message, 'at', self.create_time)

    

@dataclass
class ExecutionConfig: #EMSX / broker execution instructions.

    broker: str
    strategy: str
    order_type: str
    quantity: Optional[int] = None
    limit_price: Optional[float] = None
    target_pct_quantity: Optional[int] = 100
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    target_volume: Optional[int] = 30
    participate_open: Optional[str] = None
    participate_close: Optional[str] = None
    notes: Optional[str] = None
    last_update: Optional[datetime] = None
    
    def __post_init__(self):
        
        self.broker = self.broker.upper()
        if self.broker not in list(broker_strategy.STRATEGY_PARAMS.keys()):
            raise TypeError(f'Broker "{self.broker}" is not supported.')
        if self.strategy not in list(broker_strategy.STRATEGY_PARAMS[self.broker].keys()):
            raise TypeError(f'Algo "{self.strategy}" is not supported for broker "{self.broker}"')
        self.order_type = check_order_type(self.order_type)
        
        if self.quantity is None and self.target_pct_quantity is None:
            raise ValueError('Must give quantity or target_pct_quantity')
        
        if self.target_volume is not None:
            if not 0 <= self.target_volume <= 100:
                raise ValueError("target_volume must be between 0 and 100")

        if self.strategy in {"TWAP", "VWAP"}:
            if self.start_time is None or self.end_time is None:
                raise ValueError(f"{self.strategy} requires start_time and end_time")

        if self.strategy == "DMA":
            # Limit price requirement enforced at ticket level
            pass
        
        if self.target_pct_quantity is not None:
            if self.target_pct_quantity<=1 or self.target_pct_quantity>100:
                raise ValueError('target_pct_quantity must be between 1 and 100')
    
    def generate_summary(self, parent_order, emsx_sequence):
        order_type, limit_price, quantity = rectify_parent_and_child(parent_order, self)
        parsed_sequence = parse_emsx_sequence(emsx_sequence)
        
        summary = RouteSummary(
            ticker = parent_order.ticker,
            quantity = quantity,
            side = parent_order.side,
            order_type = order_type,
            order_id = parsed_sequence['order_id'],
            route_id = parsed_sequence['route_id'],
            message = parsed_sequence['message'],
            success = parsed_sequence['success'],
            broker = self.broker,
            strategy = self.strategy,
            target_volume = self.target_volume,
            start_time = self.start_time,
            end_time = self.end_time,
            create_time = datetime.now(),
            last_update = datetime.now()
        )

        summary.last_update = datetime.now()
        return summary


@dataclass
class RouteSummary: #EMSX / broker execution instructions.
    order_id: int
    route_id: int
    ticker: str
    side: str
    quantity: int
    order_type: str
    broker: str
    strategy: str
    create_time: Optional[datetime] = None
    limit_price: Optional[float] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    target_volume: Optional[int] = None
    participate_open: Optional[str] = None
    participate_close: Optional[str] = None
    last_update: Optional[datetime] = None
    success: Optional[bool] = None
    message: Optional[str] = None
    
    # Internal flag to avoid stamping last_update during __init__/post_init
    _initialized: bool = field(default=False, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        self._initialized = True
    
    def __setattr__(self, name: str, value):
        if getattr(self, "_initialized", False) and name not in {"last_update", "_initialized"}:
            if getattr(self, name, None) != value:
                super().__setattr__("last_update", datetime.now())
        super().__setattr__(name, value)
    
    def show(self):
        print(self.ticker.replace(' Equity',''), self.message)
        return


if __name__ == '__main__':
    
    test1 = ParentOrder(ticker='MSFT US Equity', quantity=5, side='buy')
    execution = ExecutionConfig(broker='CLSW', strategy='Fuck', order_type='MKT')
