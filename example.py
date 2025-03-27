from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
import string
import numpy as np

class TradeHistory:
    def __init__(self, max_length=10):
        self.ask_list=[]
        self.bid_list=[]
        self.max_length=max_length
        self.trade_state="H"
        self.buy_low=-1
        self.sell_high=1e10
    def push_ask(self, ask):
        if len(self.ask_list)==self.max_length:
            self.ask_list=self.ask_list[1:]+[ask]
        else:
            self.ask_list.append(ask)
        self.current_ask=ask
        self.is_falling()
        self.is_rising()
    def push_bid(self, bid):
        if len(self.ask_list)==self.max_length:
            self.ask_list=self.ask_list[1:]+[bid]
        else:
            self.ask_list.append(bid)
        self.current_bid=bid
    def push_both(self, ask, bid):
        self.push_ask(ask)
        self.push_bid(bid)
    def is_falling(self):
        if len(self.ask_list)==self.max_length and len(self.bid_list)==self.max_length:
            max_bid=np.mean(self.bid_list[:-1])
            if self.current_ask<max_bid:
                if self.trade_state=="H":
                    self.trade_state="B"
                    self.buy_low=np.mean(self.bid_list[:-1])
                elif self.trade_state=="S":
                    self.trade_state="H"
                else:
                    pass
                return True
            else:
                return False
        else:
            return False
    def is_rising(self):
        if len(self.ask_list)==self.max_length and len(self.bid_list)==self.max_length:
            min_ask=np.mean(self.ask_list[:-1])
            if self.current_bid>min_ask:
                if self.trade_state=="H":
                    self.trade_state="S"
                    self.sell_high=np.mean(self.ask_list[:-1])
                elif self.trade_state=="B":
                    self.trade_state="H"
                else:
                    pass
                return True
            else:
                return False
        else:
            return False
                  
full_history={}

def resin_strat(buy_low, sell_high, position, order_depth, orders, symbol):
    if len(order_depth.sell_orders) != 0:
        for ask, ask_amount in order_depth.sell_orders.items():
            if int(ask) < buy_low and position<100:
                print("BUY", str(-ask_amount) + "x", ask)
                orders.append(Order(symbol, ask, -ask_amount))

    if len(order_depth.buy_orders) != 0:
        for bid, bid_amount in order_depth.sell_orders.items():
            if int(bid) > sell_high and position>0:
                print("SELL", str(-bid_amount) + "x", bid)
                orders.append(Order(symbol, bid, -bid_amount))   

def kelp_strat(history, position, order_depth, orders, symbol) :
    kelp_history=history[symbol]
    if len(order_depth.sell_orders) != 0:
        if kelp_history.trade_state=="B" and position<100:
            for ask, ask_amount in order_depth.sell_orders.items():
                if int(ask) < kelp_history.buy_low:
                    print("BUY", str(-bid_amount) + "x", bid)
                    orders.append(Order(symbol, bid, -bid_amount))   

    if len(order_depth.buy_orders) != 0:
        if kelp_history.trade_state=="S" and position>0:
            for bid, bid_amount in order_depth.sell_orders.items():
                if int(bid) < kelp_history.sell_high:
                    print("SELL", str(-ask_amount) + "x", ask)
                    orders.append(Order(symbol, ask, -ask_amount))  

class Trader:
    def run(self, state: TradingState):
        print("traderData: " + state.traderData)
        print("Observations: " + str(state.observations))
        trade_dict={"RAINFOREST_RESIN": [10000, 10000], 
                    "KELP": [2015, 2020]}
        result = {}
        time=state.timestamp
        if time==0:
            for symbol in state.order_depths:
                full_history[symbol]=TradeHistory
        for symbol in state.order_depths:
            if symbol not in full_history:
                full_history[symbol] = TradeHistory() 
            order_depth: OrderDepth = state.order_depths[symbol]
            orders: List[Order] = []
            current_product=state.listings[symbol].denomination
            position=state.position[current_product]
            if len(order_depth.sell_orders) != 0:
                best_ask, best_ask_amount = list(order_depth.sell_orders.items())[0]
                full_history[symbol].push_ask(best_ask)
            if len(order_depth.buy_orders) != 0:
                best_bid, best_bid_amount = list(order_depth.buy_orders.items())[0]
                full_history[symbol].push_bid(best_bid)
            buy_low, sell_high = trade_dict[symbol]
            if symbol=="KELP":
                resin_strat(buy_low, sell_high, position, order_depth, orders, symbol)
            elif symbol=="RAINFOREST_RESIN":
                kelp_strat(full_history, position, order_depth, orders, symbol)
            
            result[symbol] = orders
    
		    # String value holding Trader state data required. 
				# It will be delivered as TradingState.traderData on next execution.
        traderData = "SAMPLE" 
        
				# Sample conversion request. Check more details below. 
        conversions = 1
        return result, conversions, traderData
    
