from datamodel import OrderDepth, UserId, TradingState, Order
from typing import List
import string

class TradeHistory:
    def __init__(self, length=10):
        self.ask_list=[]


class Trader:
    def run(self, state: TradingState):
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
                    if int(ask) > sell_high:
                        print("BUY", str(-bid_amount) + "x", bid)
                        orders.append(Order(product, bid, -bid_amount))
            
            result[product] = orders
    
		    # String value holding Trader state data required. 
				# It will be delivered as TradingState.traderData on next execution.
        traderData = "SAMPLE" 
        
				# Sample conversion request. Check more details below. 
        conversions = 1
        return result, conversions, traderData
    
