from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState, OrderDepth, UserId
from typing import List, Dict, Any
import numpy as np
import statistics as stat
import math
from logger import Logger # Make sure to import jsonpickle
import jsonpickle

logger=Logger()

class Product:
    AMETHYSTS = "AMETHYSTS"
    STARFRUIT = "STARFRUIT"
    RAINFOREST_RESIN = "RAINFOREST_RESIN"
    KELP = "KELP"
    SQUID_INK = "SQUID_INK"
    PICNIC_BASKET2 = "PICNIC_BASKET2"
    PICNIC_BASKET1 = "PICNIC_BASKET1"
    CROISSANTS = "CROISSANTS"
    JAMS = "JAMS"
    DJEMBE="DJEMBES"

class Trader:
    """Main trading class implementing different strategies for different products."""

    PRODUCT_PARAMS = {
        Product.RAINFOREST_RESIN: {
            "fair_value": 10000,      # Base fair value (static for this example)
            "limit": 50,
            "take_width": 1,
            "clear_width": 2, # Increased clear width for potentially less liquid product
            "disregard_edge": 1,
            "join_edge": 7, # Adjusted join edge
            "default_edge": 0, # Adjusted default edge
            "soft_position_limit": 100, # Added for consistency if needed by make_orders
            "manage_position": True, # Added for consistency if needed by make_orders
        },
        Product.KELP: {
            "limit": 50,
            # Parameters for dynamic fair value calculation (like STARFRUIT)
            "adverse_volume": 15,   # Threshold for significant volume
            "reversion_beta": -0.2, # Mean reversion factor (tune based on KELP behavior)
            # Parameters for take/clear/make strategy
            "take_width": 1,        # How far from fair value to take aggressively
            "clear_width": 0,       # How far from fair value to clear (0 means clear at fair)
            "prevent_adverse": False,# Avoid trading against large orders at best bid/ask
            "disregard_edge": 0,    # Ignore book levels within this edge for making
            "join_edge": 20,         # Join book levels within this edge (0 means don't join, only penny or default)
            "default_edge": 5,      # Default edge to quote if no suitable level
            "soft_position_limit": 20, # No soft limit adjustment for KELP making (example)
            "manage_position": True, # Don't manage position explicitly in make_orders for KELP (example)
        },
        Product.SQUID_INK: {
            "limit": 50,
             # Parameters for dynamic fair value calculation (like STARFRUIT)
            "adverse_volume": 15,   # Threshold for significant volume (tune separately if needed)
            "reversion_beta": -0.15,# Mean reversion factor (tune based on INK behavior)
            # Parameters for take/clear/make strategy
            "take_width": 1,
            "clear_width": 0,
            "prevent_adverse": False,
            "disregard_edge": 0,
            "join_edge": 20,
            "default_edge": 5,
            "soft_position_limit": 20,
            "manage_position": True
        }, Product.DJEMBE: {
            "limit": 60,
            "adverse_volume": 15,
            "reversion_beta": -0.2,
            "take_width": 1,
            "clear_width": 0,
            "prevent_adverse": False,
            "disregard_edge": 0,
            "join_edge": 25,
            "default_edge": 5,
            "soft_position_limit": 20,
            "manage_position": True,
        },
        Product.JAMS: {
            "limit": 350,
            "adverse_volume": 15,
            "reversion_beta": -0.2,
            "take_width": 1,
            "clear_width": 0,
            "prevent_adverse": False,
            "disregard_edge": 0,
            "join_edge": 150,
            "default_edge": 5,
            "soft_position_limit": 20,
            "manage_position": True,
        },
        Product.CROISSANTS: {
            "limit": 250,
            "adverse_volume": 15,
            "reversion_beta": -0.2,
            "take_width": 1,
            "clear_width": 0,
            "prevent_adverse": False,
            "disregard_edge": 0,
            "join_edge": 20,
            "default_edge": 100,
            "soft_position_limit": 20,
            "manage_position": True,
        },
        Product.PICNIC_BASKET1: {
            "limit": 60,
            "adverse_volume": 20,
            "take_width": 1000,
            "clear_width": 0,
            "prevent_adverse": True,
            "disregard_edge": 0,
            "join_edge": 2000,
            "default_edge": 5000,
            "soft_position_limit": 25,
            "synthetic_formula": {"CROISSANTS": 6, "JAMS": 3, "DJEMBE": 1},
        },
        Product.PICNIC_BASKET2: {
            "limit": 100,
            "adverse_volume": 20,
            "take_width": 10000,
            "clear_width": 0,
            "prevent_adverse": True,
            "disregard_edge": 10000,
            "join_edge": 20000,
            "default_edge": 50000,
            "soft_position_limit": 20,
            "synthetic_formula": {"CROISSANTS": 4, "JAMS": 2},
        }
    }

    def __init__(self):
        self.active_products = [
            Product.RAINFOREST_RESIN, Product.KELP, Product.SQUID_INK,
            Product.PICNIC_BASKET1, Product.PICNIC_BASKET2,
            Product.DJEMBE, Product.JAMS, Product.CROISSANTS
        ]
    
    def execute_basket_arbitrage(self, symbol: str, state: TradingState, traderObject: Dict) -> Dict[str, List[Order]]:
        """Simultaneously trades basket and components when mispricing occurs"""
        params = self.PRODUCT_PARAMS[symbol]
        orders = {}
        
        # Get basket parameters
        basket_depth = state.order_depths.get(symbol)
        components = params["synthetic_formula"]
        position_limit = params["limit"]
        current_position = state.position.get(symbol, 0)
        
        # Calculate synthetic price
        synthetic = 0
        component_data = {}
        for product, quantity in components.items():
            if product not in state.order_depths:
                return {}
                
            depth = state.order_depths[product]
            best_bid = max(depth.buy_orders.keys()) if depth.buy_orders else None
            best_ask = min(depth.sell_orders.keys()) if depth.sell_orders else None
            
            if not best_bid or not best_ask:
                return {}
                
            mid_price = (best_bid + best_ask) / 2
            synthetic += mid_price * quantity
            component_data[product] = {
                'best_bid': best_bid,
                'best_ask': best_ask,
                'position': state.position.get(product, 0),
                'limit': self.PRODUCT_PARAMS[product]['limit']
            }

        # Get basket prices
        basket_bid = max(basket_depth.buy_orders.keys()) if basket_depth.buy_orders else None
        basket_ask = min(basket_depth.sell_orders.keys()) if basket_depth.sell_orders else None
        if not basket_bid or not basket_ask:
            return {}
        
        # Calculate maximum tradable quantities
        spread = (basket_bid + basket_ask)/2 - synthetic
        if spread > 0:  # Basket overpriced: sell basket, buy components
            # Basket sell capacity
            max_basket_sell = min(
                position_limit + current_position,
                basket_depth.buy_orders[basket_bid]
            )
            
            # Component buy constraints
            component_limits = []
            for product, data in component_data.items():
                available = data['limit'] - data['position']
                component_qty = components[product] * max_basket_sell
                component_limits.append(available // components[product])
            
            trade_qty = min(max_basket_sell, *component_limits)
            if trade_qty > 0:
                # Sell basket
                orders[symbol] = [Order(symbol, basket_bid, -trade_qty)]
                
                # Buy components
                for product, data in component_data.items():
                    qty = trade_qty * components[product]
                    orders[product] = [Order(product, data['best_ask'], qty)]
                    
        elif spread < 0:  # Basket underpriced: buy basket, sell components
            # Basket buy capacity
            max_basket_buy = min(
                position_limit - current_position,
                abs(basket_depth.sell_orders[basket_ask])
            )
            
            # Component sell constraints
            component_limits = []
            for product, data in component_data.items():
                available = data['position'] + data['limit']
                component_qty = components[product] * max_basket_buy
                component_limits.append(available // components[product])
            
            trade_qty = min(max_basket_buy, *component_limits)
            if trade_qty > 0:
                # Buy basket
                orders[symbol] = [Order(symbol, basket_ask, trade_qty)]
                
                # Sell components
                for product, data in component_data.items():
                    qty = trade_qty * components[product]
                    orders[product] = [Order(product, data['best_bid'], -qty)]
        
        return orders

    def compute_synthetic_price(self, symbol: str, state: TradingState) -> float | None:
        params = self.PRODUCT_PARAMS.get(symbol, {})
        synthetic_components = params.get("synthetic_formula", {})
        component_prices = {}
        for comp, weight in synthetic_components.items():
            comp_depth = state.order_depths.get(comp, None)
            if not comp_depth or not comp_depth.sell_orders or not comp_depth.buy_orders:
                return None
            best_ask = min(comp_depth.sell_orders.keys())
            best_bid = max(comp_depth.buy_orders.keys())
            component_prices[comp] = (best_ask + best_bid) / 2
        synthetic_price = sum(component_prices[comp] * weight for comp, weight in synthetic_components.items())
        return synthetic_price

    def calculate_dynamic_fair_value(self, symbol: str, order_depth: OrderDepth, traderObject: Dict) -> float | None:
        if symbol not in self.PRODUCT_PARAMS:
            return None
        params = self.PRODUCT_PARAMS[symbol]
        state_key = f"{symbol}_last_price"
        if len(order_depth.sell_orders) == 0 or len(order_depth.buy_orders) == 0:
            return None
        best_ask = min(order_depth.sell_orders.keys())
        best_bid = max(order_depth.buy_orders.keys())
        filtered_ask = [price for price, vol in order_depth.sell_orders.items() if abs(vol) >= params["adverse_volume"]]
        filtered_bid = [price for price, vol in order_depth.buy_orders.items() if abs(vol) >= params["adverse_volume"]]
        mm_ask = min(filtered_ask) if filtered_ask else None
        mm_bid = max(filtered_bid) if filtered_bid else None
        last_price = traderObject.get(state_key, None)
        if mm_ask is None or mm_bid is None:
            mmmid_price = (best_ask + best_bid) / 2 if last_price is None else last_price
        else:
            mmmid_price = (mm_ask + mm_bid) / 2
        fair_value = mmmid_price
        if last_price is not None and last_price != 0:
            try:
                last_returns = (mmmid_price - last_price) / last_price
                pred_returns = last_returns * params["reversion_beta"]
                fair_value = mmmid_price + (mmmid_price * pred_returns)
            except ZeroDivisionError:
                pass
        traderObject[state_key] = mmmid_price
        return fair_value

    def take_best_orders(self, product: str, fair_value: float, take_width: float, orders: List[Order], order_depth: OrderDepth, position: int, buy_vol: int, sell_vol: int, prevent_adverse: bool, adverse_volume: int) -> (int, int):
        position_limit = self.PRODUCT_PARAMS[product]["limit"]
        if order_depth.sell_orders:
            best_ask = min(order_depth.sell_orders.keys())
            best_ask_volume = order_depth.sell_orders[best_ask]
            should_trade = not prevent_adverse or abs(best_ask_volume) <= adverse_volume
            if should_trade and best_ask <= fair_value - take_width:
                max_buy = position_limit - (position + buy_vol)
                qty = min(abs(best_ask_volume), max_buy)
                if qty > 0:
                    orders.append(Order(product, best_ask, qty))
                    buy_vol += qty
        if order_depth.buy_orders:
            best_bid = max(order_depth.buy_orders.keys())
            best_bid_volume = order_depth.buy_orders[best_bid]
            should_trade = not prevent_adverse or abs(best_bid_volume) <= adverse_volume
            if should_trade and best_bid >= fair_value + take_width:
                max_sell = position_limit + (position - sell_vol)
                qty = min(best_bid_volume, max_sell)
                if qty > 0:
                    orders.append(Order(product, best_bid, -qty))
                    sell_vol += qty
        return buy_vol, sell_vol

    def clear_position_order(self, product: str, fair_value: float, clear_width: float, orders: List[Order], order_depth: OrderDepth, position: int, buy_vol: int, sell_vol: int) -> (int, int):
        position_limit = self.PRODUCT_PARAMS[product]["limit"]
        current_pos = position + buy_vol - sell_vol
        if current_pos > 0:
            target_price = round(fair_value + clear_width)
            available = sum(vol for price, vol in order_depth.buy_orders.items() if price >= target_price)
            qty = min(current_pos, available)
            if qty > 0:
                orders.append(Order(product, target_price, -qty))
                sell_vol += qty
        elif current_pos < 0:
            target_price = round(fair_value - clear_width)
            available = sum(abs(vol) for price, vol in order_depth.sell_orders.items() if price <= target_price)
            qty = min(abs(current_pos), available)
            if qty > 0:
                orders.append(Order(product, target_price, qty))
                buy_vol += qty
        return buy_vol, sell_vol

    def make_orders(self, product: str, order_depth: OrderDepth, fair_value: float, position: int, buy_vol: int, sell_vol: int, params: Dict[str, Any]):
        orders = []
        disregard = params["disregard_edge"]
        join_edge = params["join_edge"]
        default_edge = params["default_edge"]
        asks_above = [p for p in order_depth.sell_orders.keys() if p > fair_value + disregard]
        bids_below = [p for p in order_depth.buy_orders.keys() if p < fair_value - disregard]
        best_ask_above = min(asks_above) if asks_above else None
        best_bid_below = max(bids_below) if bids_below else None
        ask_price = round(fair_value + default_edge)
        if best_ask_above:
            ask_price = best_ask_above if best_ask_above <= fair_value + join_edge else best_ask_above - 1
        bid_price = round(fair_value - default_edge)
        if best_bid_below:
            bid_price = best_bid_below if best_bid_below >= fair_value - join_edge else best_bid_below + 1
        bid_price = min(bid_price, ask_price - 1)
        pos_after = position + buy_vol - sell_vol
        buy_allowed = params["limit"] - pos_after
        if buy_allowed > 0:
            orders.append(Order(product, bid_price, buy_allowed))
        sell_allowed = params["limit"] + pos_after
        if sell_allowed > 0:
            orders.append(Order(product, ask_price, -sell_allowed))
        return orders, buy_vol, sell_vol

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        result = {}
        conversions = 0
        traderObject = jsonpickle.decode(state.traderData) if state.traderData else {}



        for symbol in self.active_products:
            if symbol not in state.order_depths:
                continue
            order_depth = state.order_depths[symbol]
            orders = []
            position = state.position.get(symbol, 0)
            params = self.PRODUCT_PARAMS.get(symbol, {})
            if not params or params["limit"] == 0:
                continue
            buy_vol, sell_vol = 0, 0
            if symbol == Product.RAINFOREST_RESIN:
                fair_value = params["fair_value"]
                buy_vol, sell_vol = self.take_best_orders(symbol, fair_value, params["take_width"], orders, order_depth, position, buy_vol, sell_vol, False, 0)
                buy_vol, sell_vol = self.clear_position_order(symbol, fair_value, params["clear_width"], orders, order_depth, position, buy_vol, sell_vol)
                make_orders, _, _ = self.make_orders(symbol, order_depth, fair_value, position, buy_vol, sell_vol, params)
                orders.extend(make_orders)
            elif symbol in [Product.KELP, Product.SQUID_INK]:
                fair_value = self.calculate_dynamic_fair_value(symbol, order_depth, traderObject)
                if fair_value is None:
                    continue
                buy_vol, sell_vol = self.take_best_orders(symbol, fair_value, params["take_width"], orders, order_depth, position, buy_vol, sell_vol, params["prevent_adverse"], params["adverse_volume"])
                buy_vol, sell_vol = self.clear_position_order(symbol, fair_value, params["clear_width"], orders, order_depth, position, buy_vol, sell_vol)
                make_orders, _, _ = self.make_orders(symbol, order_depth, fair_value, position, buy_vol, sell_vol, params)
                orders.extend(make_orders)

        
            result[symbol] = orders
        traderData = jsonpickle.encode(traderObject, unpicklable=False)
        logger.flush(state, result, conversions, traderData)
        return result, conversions, traderData