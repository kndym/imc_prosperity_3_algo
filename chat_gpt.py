from datamodel import OrderDepth, TradingState, Order
from typing import List, Dict
import numpy as np

class TradeHistory:
    def __init__(self, max_length=10):
        self.ask_list, self.bid_list = [], []
        self.max_length, self.trade_state = max_length, "H"
        self.buy_low, self.sell_high = -1, float('inf')
        self.position = 0
    
    def _update_list(self, price_list, price):
        if len(price_list) == self.max_length:
            price_list.pop(0)
        price_list.append(price)
    
    def push_ask(self, ask):
        self._update_list(self.ask_list, ask)
        self._check_trend()
    
    def push_bid(self, bid):
        self._update_list(self.bid_list, bid)
    
    def push_both(self, ask, bid):
        self.push_ask(ask)
        self.push_bid(bid)
    
    def _check_trend(self):
        if len(self.ask_list) == self.max_length and len(self.bid_list) == self.max_length:
            max_bid, min_ask = np.mean(self.bid_list[:-1]), np.mean(self.ask_list[:-1])
            if self.ask_list[-1] < max_bid:
                self.trade_state = "B" if self.trade_state == "H" else "H"
                self.buy_low = max_bid
            elif self.bid_list[-1] > min_ask:
                self.trade_state = "S" if self.trade_state == "H" else "H"
                self.sell_high = min_ask
    
    def add_pos(self, num):
        self.position -= num

full_history: Dict[str, TradeHistory] = {}

def execute_orders(history, order_depth, orders, symbol, buy_low=None, sell_high=None):
    trade_history = history[symbol]
    for ask, amount in order_depth.sell_orders.items():
        if trade_history.trade_state == "B" and (buy_low is None or int(ask) < buy_low):
            print("BUY", symbol, f"{-amount}x", ask)
            orders.append(Order(symbol, ask, -amount))
            trade_history.add_pos(amount)
    for bid, amount in order_depth.buy_orders.items():
        if trade_history.trade_state == "S" and (sell_high is None or int(bid) > sell_high):
            print("SELL", symbol, f"{-amount}x", bid)
            orders.append(Order(symbol, bid, -amount))
            trade_history.add_pos(amount)

class Trader:
    def run(self, state: TradingState):
        trade_dict = {"RAINFOREST_RESIN": [10000, 10000], "KELP": [2015, 2020]}
        result = {}

        if state.timestamp == 0:
            for symbol in state.order_depths:
                full_history[symbol] = TradeHistory()

        for symbol, order_depth in state.order_depths.items():
            full_history.setdefault(symbol, TradeHistory())
            orders: List[Order] = []

            if order_depth.sell_orders:
                full_history[symbol].push_ask(min(order_depth.sell_orders))
            if order_depth.buy_orders:
                full_history[symbol].push_bid(max(order_depth.buy_orders))

            print(f"{full_history[symbol].trade_state}_STATE", symbol)

            if symbol in trade_dict:
                execute_orders(full_history, order_depth, orders, symbol, *trade_dict[symbol])
            else:
                execute_orders(full_history, order_depth, orders, symbol)
            
            result[symbol] = orders
        
        return result, 1, "SAMPLE"
