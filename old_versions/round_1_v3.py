from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
from typing import List
import numpy as np
import statistics as stat
from typing import List, Dict, Any

class Trader:
    """Main trading class implementing different strategies for different products."""
    
    PRODUCT_PARAMS = {
        "RAINFOREST_RESIN": {
            "fair_value": 10000,      # Base fair value (like fp)
            "limit": 50,              # Position limit
            # Parameters adapted from the second algorithm
            "take_width": 1,          # How far from fair value to take aggressively
            "clear_width": 2,         # How far from fair value to clear position
            "disregard_edge": 1,      # Ignore book levels within this edge for making decisions
            "join_edge": 7,           # Join book levels within this edge
            "default_edge": 0        # Default edge to quote if no suitable level to join/penny
        },
        "KELP": {"limit":50},
        "SQUID_INK": {"limit":50}
    }
    
    def __init__(self):
        self.active_products = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"]  


    def prob_algo(self, product: str, 
                  final_price_mean: float, final_price_dev: float,
                  order_depth: OrderDepth, orders: List[Order], 
                  position: int, trade_limit: int) -> None:
        def valid_orders(final_price_mean: float, final_price_dev: float,
                         order_dict: Dict[int,int], max_volume: int,
                         move_down_prices: bool) -> list:
            def gaussian_cdf(price: int, final_price_mean: float, 
                             final_price_dev: float, normal_cdf: bool) -> float:
                dist=stat.NormalDist(mu=final_price_mean, sigma=final_price_dev)
                prob=dist.cdf(price)
                if normal_cdf:
                    return prob
                else:
                    return 1-prob
            current_volume=0
            good_orders=[]
            for price, volume in sorted(order_dict.items(), key=lambda item: item[0], reverse=move_down_prices):
                real_volume=abs(volume)
                unscaled_volume=gaussian_cdf(price, final_price_mean, final_price_dev, move_down_prices)
                current_max_volume=unscaled_volume*1000
                #int(unscaled_volume*max_volume//1)
                if current_max_volume>current_volume:
                    this_price_max=current_max_volume-current_volume
                    trade_volume=min(this_price_max, real_volume)
                    current_volume+=trade_volume
                    good_orders.append((price, trade_volume))
                else:
                    break
            return good_orders
        buy_max_volume=trade_limit-position
        sell_max_volume=trade_limit+position
        possible_buys=valid_orders(final_price_mean, final_price_dev, 
                                   order_depth.sell_orders, buy_max_volume, False)
        possible_sells=valid_orders(final_price_mean, final_price_dev, 
                                    order_depth.buy_orders, sell_max_volume, True)
        def down_volume(order_list)->None:
            if order_list[-1][1]<2:
                order_list=order_list.pop(-1)
            else:
                order_list[-1]=(order_list[-1][0], order_list[-1][1]-1)
        while len(possible_buys)>0 and len(possible_sells)>0:
            down_volume(possible_buys)
            down_volume(possible_sells)
        for price, real_volume in possible_buys:
            orders.append(Order(product, price, real_volume))
        for price, real_volume in possible_sells:
            orders.append(Order(product, price, -real_volume))

# --- New Strategy Function for RAINFOREST_RESIN ---
    def run_rainforest_resin_strategy(self, symbol: str, order_depth: OrderDepth,
                                      current_position: int, params: Dict[str, Any],
                                      limit: int, orders: List[Order]) -> None:
        """
        Implements the take, clear, make strategy for RAINFOREST_RESIN.
        """

        fair_value = params["fair_value"]
        take_width = params["take_width"]
        clear_width = params["clear_width"]
        disregard_edge = params["disregard_edge"]
        join_edge = params["join_edge"]
        default_edge = params["default_edge"]

        buy_order_volume = 0  # Track volume bought in this timestep
        sell_order_volume = 0 # Track volume sold in this timestep

        # 1. TAKE Logic (Simplified take_best_orders)
        if order_depth.sell_orders:
            best_ask = min(order_depth.sell_orders.keys())
            best_ask_amount = abs(order_depth.sell_orders[best_ask])
            if best_ask <= fair_value - take_width:
                quantity_to_buy = min(best_ask_amount, limit - current_position - buy_order_volume)
                if quantity_to_buy > 0:
                    orders.append(Order(symbol, best_ask, quantity_to_buy))
                    buy_order_volume += quantity_to_buy

        if order_depth.buy_orders:
            best_bid = max(order_depth.buy_orders.keys())
            best_bid_amount = abs(order_depth.buy_orders[best_bid])
            if best_bid >= fair_value + take_width:
                quantity_to_sell = min(best_bid_amount, limit + current_position - sell_order_volume)
                if quantity_to_sell > 0:
                    orders.append(Order(symbol, best_bid, -quantity_to_sell))
                    sell_order_volume += quantity_to_sell

        # 2. CLEAR Logic (Simplified clear_position_order)
        position_after_take = current_position + buy_order_volume - sell_order_volume
        # Note: Remaining limits calculation was slightly off, corrected here.
        # It should reflect how much more volume can be added *from this point forward*
        # based on the initial position and the limit.
        buy_remaining_limit = limit - (current_position + buy_order_volume)
        sell_remaining_limit = limit + (current_position - sell_order_volume)

        if position_after_take > 0: # Need to sell to clear long position
            target_ask_price = round(fair_value + clear_width)
            # Calculate how much *more* we can sell based on limit and orders already placed
            clear_potential_sell = min(position_after_take, sell_remaining_limit)

            if clear_potential_sell > 0:
                # Check if there are actually bids at or above the target price to clear against
                potential_clear_volume = sum(vol for price, vol in order_depth.buy_orders.items() if price >= target_ask_price)
                actual_clear_sell = min(clear_potential_sell, potential_clear_volume)
                if actual_clear_sell > 0:
                    orders.append(Order(symbol, target_ask_price, -actual_clear_sell))
                    sell_order_volume += actual_clear_sell # Update total sell volume for this step

        elif position_after_take < 0: # Need to buy to clear short position
            target_bid_price = round(fair_value - clear_width)
            # Calculate how much *more* we can buy based on limit and orders already placed
            clear_potential_buy = min(abs(position_after_take), buy_remaining_limit)

            if clear_potential_buy > 0:
                # Check if there are actually asks at or below the target price to clear against
                potential_clear_volume = sum(abs(vol) for price, vol in order_depth.sell_orders.items() if price <= target_bid_price)
                actual_clear_buy = min(clear_potential_buy, potential_clear_volume)
                if actual_clear_buy > 0:
                    orders.append(Order(symbol, target_bid_price, actual_clear_buy))
                    buy_order_volume += actual_clear_buy # Update total buy volume for this step

        # 3. MAKE Logic (Simplified make_orders)
        # Determine best bid/ask levels outside the disregard zone
        asks_above_threshold = [p for p in order_depth.sell_orders.keys() if p > fair_value + disregard_edge]
        bids_below_threshold = [p for p in order_depth.buy_orders.keys() if p < fair_value - disregard_edge]

        best_ask_above = min(asks_above_threshold) if asks_above_threshold else None
        best_bid_below = max(bids_below_threshold) if bids_below_threshold else None

        # Determine target making ask price
        ask_price = round(fair_value + default_edge)
        if best_ask_above is not None:
            if best_ask_above <= fair_value + join_edge:
                ask_price = best_ask_above  # Join
            else:
                ask_price = best_ask_above - 1 # Penny

        # Determine target making bid price
        bid_price = round(fair_value - default_edge)
        if best_bid_below is not None:
            if best_bid_below >= fair_value - join_edge:
                bid_price = best_bid_below # Join
            else:
                bid_price = best_bid_below + 1 # Penny

        # Adjust based on soft position limit (using position *after* take/clear orders conceptually)
        # Use the total volume committed so far (buy_order_volume, sell_order_volume)
        effective_position = current_position + buy_order_volume - sell_order_volume

        # Ensure bid < ask
        bid_price = min(bid_price, ask_price - 1)

        # Place making orders respecting limits based on volume *already committed*
        buy_quantity_make = limit - (current_position + buy_order_volume) # Max buy = limit - (pos + buys_so_far)
        if buy_quantity_make > 0:
            orders.append(Order(symbol, bid_price, buy_quantity_make))
            # Note: We don't update buy_order_volume here as these orders might not fill

        sell_quantity_make = limit + (current_position - sell_order_volume) # Max sell = limit + (pos - sells_so_far)
        if sell_quantity_make > 0:
            orders.append(Order(symbol, ask_price, -sell_quantity_make))
            # Note: We don't update sell_order_volume here



    def stable_algo(self, product: str, 
                  fair_price: float,
                  order_depth: OrderDepth, orders: List[Order]) -> None:
        for ask, ask_amount in order_depth.sell_orders.items():
            if int(ask)<fair_price:
                orders.append(Order(product, ask, -ask_amount))  
        for bid, bid_amount in order_depth.buy_orders.items():
            if int(bid)>fair_price:
                orders.append(Order(product, bid, -bid_amount)) 
    
    def single_stable(self, product: str, 
                  fair_price: float,
                  order_depth: OrderDepth, orders: List[Order]) -> None:
        ask, ask_amount = list(order_depth.sell_orders.items())[0]
        if int(ask)<fair_price:
            orders.append(Order(product, ask, -ask_amount))  
        bid, bid_amount = list(order_depth.buy_orders.items())[0]
        if int(bid)>fair_price:
            orders.append(Order(product, bid, -bid_amount)) 
    
    def volitile_algo(self, product: str, 
                  order_depth: OrderDepth, orders: List[Order]) -> None:
        if len(order_depth.sell_orders.keys())>1:
            ask, ask_amount = list(order_depth.sell_orders.items())[0]
            orders.append(Order(product, ask, -ask_amount)) 
        if len(order_depth.buy_orders.keys())>1:
            bid, bid_amount = list(order_depth.buy_orders.items())[0]
            orders.append(Order(product, bid, -bid_amount)) 


    def current_mid_price(self, order_depth: OrderDepth) -> float:
        return (list(order_depth.buy_orders.items())[0][0]
                +list(order_depth.sell_orders.items())[0][0])/2

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        result = {}
        
        for symbol, order_depth in state.order_depths.items():
            orders = []
            try:
                position=state.position[symbol]
            except KeyError:
                position=0
            params = self.PRODUCT_PARAMS.get(symbol, {})
            if symbol == self.active_products[0]:  # STARFRUIT/KELP
                fair=params["fair_value"]
                limit=params["limit"]
                fair-=(position/limit)
                self.run_rainforest_resin_strategy(symbol, order_depth,position, params, limit, orders)
                #self.stable_algo(symbol, fair, order_depth, orders)
                #self.single_stable(symbol, fair, order_depth, orders)
            else:
                pass
            result[symbol] = orders
        return result, 1, "SAMPLE"
    