from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
from typing import List
import string
import numpy as np
import scipy.stats as st
import json
from typing import List, Dict, Any
from logger import Logger


class Trader:
    """Main trading class implementing different strategies for different products."""
    
    PRODUCT_PARAMS = {
        "RAINFOREST_RESIN": {"fp_mean":10000, "fp_dev":1.5, "limit":50},
        "KELP": {"buy_low": 2015, "sell_high": 2020},
        "AMETHYSTS": {"fp_mean": 10000, "fp_dev":0.01, "limit":50},
        "STARFRUIT": {"fp_mean":5000, "fp_dev":50, "limit":50, "sigma":1}
    }
    
    def __init__(self):
        self.logger = Logger()
        self.active_products = ["AMETHYSTS", "STARFRUIT"]  

    def prob_algo(self, product: str, 
                  final_price_mean: float, final_price_dev: float,
                  order_depth: OrderDepth, orders: List[Order], 
                  position: int, trade_limit: int) -> None:
        def valid_orders(final_price_mean: float, final_price_dev: float,
                         order_dict: Dict[int,int], max_volume: int,
                         move_down_prices: bool) -> list:
            def gaussian_cdf(price: int, final_price_mean: float, 
                             final_price_dev: float, normal_cdf: bool) -> float:
                normal_z=(price-final_price_mean)/final_price_dev
                prob=st.norm.cdf(normal_z)
                if normal_cdf:
                    return prob
                else:
                    return 1-prob
            current_volume=0
            good_orders=[]
            for price, volume in sorted(order_dict.items(), key=lambda item: item[0], reverse=move_down_prices):
                real_volume=abs(volume)
                unscaled_volume=gaussian_cdf(price, final_price_mean, final_price_dev, move_down_prices)
                current_max_volume=int(unscaled_volume*max_volume//1)
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

    def current_mid_price(self, order_depth: OrderDepth) -> float:
        return (order_depth.buy_orders.items[0][0]
                +order_depth.sell_orders.items[0][0])/2

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        """Main trading method called each timestamp."""
        self.logger.print("traderData:", state.traderData)
        self.logger.print("Observations:", str(state.observations))
        time=state.timestamp/100
        result = {}
        
        for symbol, order_depth in state.order_depths.items():
            orders = []
            try:
                position=state.position[symbol]
            except KeyError:
                position=0
            params = self.PRODUCT_PARAMS.get(symbol, {})
            if symbol == self.active_products[1]:  # STARFRUIT/KELP
                current_price=self.current_mid_price(order_depth)
                current_var=params["sigma"]*time
                param_price=params["fp_mean"]
                param_var=params["fp_dev"]**2
                final_var=1/(1/current_var+1/param_var)
                final_price=(current_price/current_var+param_price/param_var)*final_var
                self.prob_algo(symbol, final_price, np.sqrt(final_var),
                               order_depth, orders, position, params["limit"]
                               )
            elif symbol == self.active_products[0]:  # AMETHYSTS/RESIN
                pass
            result[symbol] = orders
        self.logger.flush(state, result, 1, "SAMPLE")
        return result, 1, "SAMPLE"
    