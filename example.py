from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
import string

class TradeHistory:
    def __init__(self, max_length=10):
        self.ask_list=[]
        self.bid_list=[]
        self.max_length=max_length
    def push_ask(self, ask):
        if len(self.ask_list)==self.max_length:
            self.ask_list=self.ask_list[1:]+[ask]
        else:
            self.ask_list.append(ask)
        self.current_ask=ask
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
            max_bid=max(self.bid_list[:-1])
            if self.current_ask<max_bid:
                return True
            else:
                return False
        else:
            return False
    def is_rising(self):
        if len(self.ask_list)==self.max_length and len(self.bid_list)==self.max_length:
            min_ask=min(self.ask_list[:-1])
            if self.current_bid>min_ask:
                return True
            else:
                return False
        else:
            return False
        
            


class Trader:
    def run(self, state: TradingState, history: TradeHistory):
        print("traderData: " + state.traderData)
        print("Observations: " + str(state.observations))
        trade_dict={"RAINFOREST_RESIN": [10000, 10000], 
                    "KELP": [2015, 2020]}
        result = {}
        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []
              # Participant should calculate this value
            print("Buy Order depth : " + str(len(order_depth.buy_orders)) + ", Sell order depth : " + str(len(order_depth.sell_orders)))
            buy_low, sell_high = trade_dict[product]
            if len(order_depth.sell_orders) != 0:
                for ask, ask_amount in order_depth.sell_orders.items():
                    if int(ask) < buy_low:
                        print("BUY", str(-ask_amount) + "x", ask)
                        orders.append(Order(product, ask, -ask_amount))
    
            if len(order_depth.buy_orders) != 0:
                 for bid, bid_amount in order_depth.sell_orders.items():
                    if int(bid) > sell_high:
                        print("BUY", str(-bid_amount) + "x", bid)
                        orders.append(Order(product, bid, -bid_amount))
            
            result[product] = orders
    
		    # String value holding Trader state data required. 
				# It will be delivered as TradingState.traderData on next execution.
        traderData = "SAMPLE" 
        
				# Sample conversion request. Check more details below. 
        conversions = 1
        return result, conversions, traderData
    
