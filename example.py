from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
from typing import List
import string
import numpy as np
import json
from typing import Any

class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(
            self.to_json(
                [
                    self.compress_state(state, ""),
                    self.compress_orders(orders),
                    conversions,
                    "",
                    "",
                ]
            )
        )

        # We truncate state.traderData, trader_data, and self.logs to the same max. length to fit the log limit
        max_item_length = (self.max_log_length - base_length) // 3

        print(
            self.to_json(
                [
                    self.compress_state(state, self.truncate(state.traderData, max_item_length)),
                    self.compress_orders(orders),
                    conversions,
                    self.truncate(trader_data, max_item_length),
                    self.truncate(self.logs, max_item_length),
                ]
            )
        )

        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> list[Any]:
        return [
            state.timestamp,
            trader_data,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations),
        ]

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        compressed = []
        for listing in listings.values():
            compressed.append([listing.symbol, listing.product, listing.denomination])

        return compressed

    def compress_order_depths(self, order_depths: dict[Symbol, OrderDepth]) -> dict[Symbol, list[Any]]:
        compressed = {}
        for symbol, order_depth in order_depths.items():
            compressed[symbol] = [order_depth.buy_orders, order_depth.sell_orders]

        return compressed

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        compressed = []
        for arr in trades.values():
            for trade in arr:
                compressed.append(
                    [
                        trade.symbol,
                        trade.price,
                        trade.quantity,
                        trade.buyer,
                        trade.seller,
                        trade.timestamp,
                    ]
                )

        return compressed

    def compress_observations(self, observations: Observation) -> list[Any]:
        conversion_observations = {}
        for product, observation in observations.conversionObservations.items():
            conversion_observations[product] = [
                observation.bidPrice,
                observation.askPrice,
                observation.transportFees,
                observation.exportTariff,
                observation.importTariff,
                observation.sugarPrice,
                observation.sunlightIndex,
            ]

        return [observations.plainValueObservations, conversion_observations]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        compressed = []
        for arr in orders.values():
            for order in arr:
                compressed.append([order.symbol, order.price, order.quantity])

        return compressed

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        if len(value) <= max_length:
            return value

        return value[: max_length - 3] + "..."




class TradeHistory:
    def __init__(self, max_length=10):
        self.ask_list=[]
        self.bid_list=[]
        self.max_length=max_length
        self.trade_state="H"
        self.buy_low=-1
        self.sell_high=1e10
        self.position=0
    def push_ask(self, ask):
        if len(self.ask_list)==self.max_length:
            self.ask_list=self.ask_list[1:]+[ask]
        else:
            self.ask_list.append(ask)
        self.current_ask=ask
        self.is_falling()
        self.is_rising()
    def push_bid(self, bid):
        if len(self.bid_list)==self.max_length:
            self.bid_list=self.bid_list[1:]+[bid]
        else:
            self.bid_list.append(bid)
        self.current_bid=bid
        self.is_falling()
        self.is_rising()
    def push_both(self, ask, bid):
        self.push_ask(ask)
        self.push_bid(bid)
    def is_falling(self):
        if len(self.bid_list)==self.max_length:
            print("HIII")
            avg_bid=np.mean(self.bid_list[:-1])
            if self.current_ask<avg_bid:
                if self.trade_state=="H":
                    self.trade_state="B"
                    self.buy_low=avg_bid
                elif self.trade_state=="S":
                    self.trade_state="H"
                else:
                    pass
    def is_rising(self):
        if len(self.ask_list)==self.max_length:
            avg_ask=np.mean(self.ask_list[:-1])
            if self.current_bid>avg_ask:
                if self.trade_state=="H":
                    self.trade_state="S"
                    self.sell_high=avg_ask
                elif self.trade_state=="B":
                    self.trade_state="H"
                else:
                    pass
    def add_pos(self, num):
        self.position-=num
                  
full_history={}

def resin_strat(history, buy_low, sell_high, order_depth, orders, symbol):
    resin_history=history[symbol]
    if len(order_depth.sell_orders) != 0:
        for ask, ask_amount in order_depth.sell_orders.items():
            if int(ask) < buy_low:
                #print("BUY", str(symbol), str(-ask_amount) + "x", ask)
                orders.append(Order(symbol, ask, -ask_amount))
                resin_history.add_pos(ask_amount)

    if len(order_depth.buy_orders) != 0:
        for bid, bid_amount in order_depth.buy_orders.items():
            if int(bid) > sell_high:
                #print("SELL", str(symbol), str(-bid_amount) + "x", bid)
                orders.append(Order(symbol, bid, -bid_amount)) 
                resin_history.add_pos(bid_amount)  

def kelp_strat(history, order_depth, orders, symbol) :
    kelp_history=history[symbol]
    if len(order_depth.sell_orders) != 0:
        if kelp_history.trade_state=="B":
            for ask, ask_amount in order_depth.sell_orders.items():
                if int(ask) < kelp_history.buy_low:
                    real_amount=min(-ask_amount, 5)
                    #print("BUY", str(symbol), str(real_amount) + "x", ask)
                    orders.append(Order(symbol, ask, real_amount))  
                    kelp_history.add_pos(real_amount) 

    if len(order_depth.buy_orders) != 0:
        if kelp_history.trade_state=="S":
            for bid, bid_amount in order_depth.buy_orders.items():
                if int(bid) > kelp_history.sell_high:
                    real_amount=min(bid_amount, 5)
                    #print("SELL", str(symbol), str(real_amount) + "x", bid)
                    orders.append(Order(symbol, bid, -real_amount)) 
                    kelp_history.add_pos(-real_amount)  


logger = Logger()

class Trader:
    def run(self, state: TradingState):
        print("traderData: " + state.traderData)
        print("Observations: " + str(state.observations))
        trade_dict={"RAINFOREST_RESIN": [10000, 9999], 
                    "KELP": [2015, 2020]}
        result = {}
        time=state.timestamp
        if time==0:
            for symbol in state.order_depths:
                full_history[symbol]=TradeHistory()
        for i, symbol in enumerate(state.order_depths):
            if symbol not in full_history:
                full_history[symbol] = TradeHistory() 
            order_depth: OrderDepth = state.order_depths[symbol]
            orders: List[Order] = []
            if len(order_depth.sell_orders) != 0:
                best_ask, best_ask_amount = list(order_depth.sell_orders.items())[0]
                full_history[symbol].push_ask(best_ask)
            if len(order_depth.buy_orders) != 0:
                best_bid, best_bid_amount = list(order_depth.buy_orders.items())[0]
                full_history[symbol].push_bid(best_bid)
            if full_history[symbol].trade_state=="S":
                print("S_STATE", symbol)
            elif full_history[symbol].trade_state=="B":
                print("B_STATE", symbol)
            buy_low, sell_high = trade_dict[symbol]
            if symbol=="KELP":
                kelp_strat(full_history, order_depth, orders, symbol)
            elif symbol=="RAINFOREST_RESIN":
                resin_strat(full_history, buy_low, sell_high, order_depth, orders, symbol)
            
            result[symbol] = orders
    
		    # String value holding Trader state data required. 
				# It will be delivered as TradingState.traderData on next execution.
        traderData = "SAMPLE" 
        
				# Sample conversion request. Check more details below. 
        conversions = 1

        logger.flush(state, result, conversions, traderData)
        return result, conversions, traderData
    
