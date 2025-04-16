from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState, UserId
from typing import List, Dict, Any
import numpy as np
import jsonpickle

logger = Logger()

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
    DJEMBE = "DJEMBES"

class Trader:
    PRODUCT_PARAMS = {
        Product.RAINFOREST_RESIN: {
            "fair_value": 10000,
            "limit": 50,
            "take_width": 1,
            "clear_width": 2,
            "disregard_edge": 1,
            "join_edge": 7,
            "default_edge": 0,
            "soft_position_limit": 100,
            "manage_position": True,
        },
        Product.KELP: {
            "limit": 50,
            "adverse_volume": 15,
            "reversion_beta": -0.2,
            "take_width": 1,
            "clear_width": 0,
            "prevent_adverse": False,
            "disregard_edge": 0,
            "join_edge": 20,
            "default_edge": 5,
            "soft_position_limit": 20,
            "manage_position": False,
        },
        Product.SQUID_INK: {
            "limit": 50,
            "adverse_volume": 15,
            "reversion_beta": -0.15,
            "take_width": 1,
            "clear_width": 0,
            "prevent_adverse": False,
            "disregard_edge": 0,
            "join_edge": 20,
            "default_edge": 5,
            "soft_position_limit": 20,
            "manage_position": False,
        },
        Product.DJEMBE: {
            "limit": 50,
            "adverse_volume": 15,
            "reversion_beta": -0.2,
            "take_width": 1,
            "clear_width": 0,
            "prevent_adverse": False,
            "disregard_edge": 0,
            "join_edge": 20,
            "default_edge": 5,
            "soft_position_limit": 20,
            "manage_position": False,
        },
        Product.JAMS: {
            "limit": 350,
            "adverse_volume": 15,
            "reversion_beta": -0.15,
            "take_width": 1,
            "clear_width": 0,
            "prevent_adverse": False,
            "disregard_edge": 0,
            "join_edge": 150,
            "default_edge": 5,
            "soft_position_limit": 20,
            "manage_position": False,
        },
        Product.CROISSANTS: {
            "limit": 250,
            "adverse_volume": 15,
            "reversion_beta": -0.15,
            "take_width": 1,
            "clear_width": 0,
            "prevent_adverse": False,
            "disregard_edge": 0,
            "join_edge": 100,
            "default_edge": 5,
            "soft_position_limit": 20,
            "manage_position": False,
        },
        Product.PICNIC_BASKET1: {
            "limit": 60,
            "take_width": 1,
            "clear_width": 0,
            "prevent_adverse": False,
            "adverse_volume": 0,
            "disregard_edge": 0,
            "join_edge": 0,
            "default_edge": 0,
            "soft_position_limit": 0,
            "manage_position": False,
            "synthetic_formula": {"CROISSANTS": 6, "JAMS": 3, "DJEMBE": 1},
        },
        Product.PICNIC_BASKET2: {
            "limit": 100,
            "take_width": 1,
            "clear_width": 0,
            "prevent_adverse": False,
            "adverse_volume": 0,
            "disregard_edge": 0,
            "join_edge": 0,
            "default_edge": 0,
            "soft_position_limit": 0,
            "manage_position": False,
            "synthetic_formula": {"CROISSANTS": 4, "JAMS": 2},
        }
    }

    def __init__(self):
        self.active_products = [
            Product.RAINFOREST_RESIN, Product.KELP, Product.SQUID_INK,
            Product.PICNIC_BASKET1, Product.PICNIC_BASKET2,
            Product.DJEMBE, Product.JAMS, Product.CROISSANTS
        ]

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
            elif symbol in [Product.KELP, Product.SQUID_INK, Product.DJEMBE, Product.JAMS, Product.CROISSANTS]:
                fair_value = self.calculate_dynamic_fair_value(symbol, order_depth, traderObject)
                if fair_value is None:
                    continue
                buy_vol, sell_vol = self.take_best_orders(symbol, fair_value, params["take_width"], orders, order_depth, position, buy_vol, sell_vol, params["prevent_adverse"], params["adverse_volume"])
                buy_vol, sell_vol = self.clear_position_order(symbol, fair_value, params["clear_width"], orders, order_depth, position, buy_vol, sell_vol)
                make_orders, _, _ = self.make_orders(symbol, order_depth, fair_value, position, buy_vol, sell_vol, params)
                orders.extend(make_orders)
            elif symbol in [Product.PICNIC_BASKET1, Product.PICNIC_BASKET2]:
                synthetic_price = self.compute_synthetic_price(symbol, state)
                if synthetic_price is None:
                    continue
                buy_vol, sell_vol = self.take_best_orders(symbol, synthetic_price, params["take_width"], orders, order_depth, position, buy_vol, sell_vol, params["prevent_adverse"], params["adverse_volume"])
                buy_vol, sell_vol = self.clear_position_order(symbol, synthetic_price, params["clear_width"], orders, order_depth, position, buy_vol, sell_vol)
                make_orders, _, _ = self.make_orders(symbol, order_depth, synthetic_price, position, buy_vol, sell_vol, params)
                orders.extend(make_orders)
            result[symbol] = orders
        traderData = jsonpickle.encode(traderObject, unpicklable=False)
        logger.flush(state, result, conversions, traderData)
        return result, conversions, traderData