from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
from typing import List
import numpy as np
import statistics as stat
from typing import List, Dict, Any

class Trader:
    """Main trading class implementing different strategies for different products."""
    
    PRODUCT_PARAMS = {
        "RAINFOREST_RESIN": {"fp":10000, "limit":50},
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


    def stable_algo(self, product: str, 
                  fair_price: float,
                  order_depth: OrderDepth, orders: List[Order]) -> None:
        if len(order_depth.sell_orders)!=0:
            for ask, ask_amount in order_depth.sell_orders.items():
                if int(ask)<fair_price:
                    orders.append(Order(product, ask, -ask_amount))  
        if len(order_depth.buy_orders)!=0:
            for bid, bid_amount in order_depth.buy_orders.items():
                if int(bid)>=fair_price:
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
                fair=params["fp"]
                self.stable_algo(symbol, fair, order_depth, orders)
            else:
                pass
            result[symbol] = orders
        return result, 1, "SAMPLE"
    