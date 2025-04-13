from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState, OrderDepth, UserId
from typing import List, Dict, Any
import numpy as np
import statistics as stat
import math
import jsonpickle # Make sure to import jsonpickle

# Assuming Logger is defined elsewhere or removing its usage for brevity
from logger import Logger

class Product: # Define Product constants if not already globally available
    AMETHYSTS = "AMETHYSTS" # Example, add others if needed
    STARFRUIT = "STARFRUIT" # Example
    RAINFOREST_RESIN = "RAINFOREST_RESIN"
    KELP = "KELP"
    SQUID_INK = "SQUID_INK"

class Trader:
    """Main trading class implementing different strategies for different products."""

    PRODUCT_PARAMS = {
        Product.RAINFOREST_RESIN: {
            "fair_value": 10000,      # Base fair value (static for this example)
            "limit": 50,
            "take_width": 1,
            "clear_width": 2, # Increased clear width for potentially less liquid product
            "disregard_edge": 1,
            "join_edge": 2, # Adjusted join edge
            "default_edge": 3, # Adjusted default edge
            "soft_position_limit": 10, # Added for consistency if needed by make_orders
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
            "prevent_adverse": True,# Avoid trading against large orders at best bid/ask
            "disregard_edge": 1,    # Ignore book levels within this edge for making
            "join_edge": 0,         # Join book levels within this edge (0 means don't join, only penny or default)
            "default_edge": 1,      # Default edge to quote if no suitable level
            "soft_position_limit": 0, # No soft limit adjustment for KELP making (example)
            "manage_position": False, # Don't manage position explicitly in make_orders for KELP (example)
        },
        Product.SQUID_INK: {
            "limit": 50,
             # Parameters for dynamic fair value calculation (like STARFRUIT)
            "adverse_volume": 15,   # Threshold for significant volume (tune separately if needed)
            "reversion_beta": -0.15,# Mean reversion factor (tune based on INK behavior)
            # Parameters for take/clear/make strategy
            "take_width": 1,
            "clear_width": 0,
            "prevent_adverse": True,
            "disregard_edge": 1,
            "join_edge": 0,
            "default_edge": 1,
            "soft_position_limit": 0,
            "manage_position": False,
        }
    }

    def __init__(self):
        self.active_products = [Product.RAINFOREST_RESIN, Product.KELP, Product.SQUID_INK]
        self.logger=Logger() # Assuming Logger class exists

    # --- Fair Value Calculation (Adapted from starfruit_fair_value) ---
    def calculate_dynamic_fair_value(self, symbol: str, order_depth: OrderDepth, traderObject: Dict) -> float | None:
        """ Calculates fair value based on filtered order book and mean reversion. """
        # Ensure the product has the necessary parameters defined
        if symbol not in self.PRODUCT_PARAMS or \
           "adverse_volume" not in self.PRODUCT_PARAMS[symbol] or \
           "reversion_beta" not in self.PRODUCT_PARAMS[symbol]:
            # print(f"Warning: Missing dynamic fair value parameters for {symbol}") # Optional logging
            return None # Cannot calculate without params

        params = self.PRODUCT_PARAMS[symbol]
        state_key = f"{symbol}_last_price" # Key for storing last price in traderObject

        if len(order_depth.sell_orders) == 0 or len(order_depth.buy_orders) == 0:
            return None # Not enough data

        best_ask = min(order_depth.sell_orders.keys())
        best_bid = max(order_depth.buy_orders.keys())

        # Filter orders by adverse_volume threshold
        filtered_ask = [
            price for price, volume in order_depth.sell_orders.items()
            if abs(volume) >= params["adverse_volume"]
        ]
        filtered_bid = [
            price for price, volume in order_depth.buy_orders.items()
            if abs(volume) >= params["adverse_volume"]
        ]

        mm_ask = min(filtered_ask) if filtered_ask else None
        mm_bid = max(filtered_bid) if filtered_bid else None

        mmmid_price = None
        # Calculate Market Maker Mid-Price (mmmid_price)
        if mm_ask is None or mm_bid is None:
            # Fallback if significant orders are missing
            last_price = traderObject.get(state_key, None)
            if last_price is None:
                mmmid_price = (best_ask + best_bid) / 2 # Use simple mid if no history
            else:
                mmmid_price = last_price # Use last known price for stability
        else:
            # Use mid-price based on significant volume orders
            mmmid_price = (mm_ask + mm_bid) / 2

        # Apply mean reversion if previous price exists
        last_price = traderObject.get(state_key, None)
        fair_value = mmmid_price # Default to mmmid_price if no history

        if last_price is not None and last_price != 0: # Avoid division by zero
            try:
                last_returns = (mmmid_price - last_price) / last_price
                pred_returns = last_returns * params["reversion_beta"]
                fair_value = mmmid_price + (mmmid_price * pred_returns)
            except ZeroDivisionError:
                 # print(f"Warning: ZeroDivisionError calculating returns for {symbol}") # Optional logging
                 pass # Keep fair_value as mmmid_price

        # Store the *current* mmmid_price for the next iteration's calculation
        traderObject[state_key] = mmmid_price

        return fair_value

    # --- Trading Logic Components (Adapted from first code block) ---

    def take_best_orders(
        self,
        product: str,
        fair_value: float,
        take_width: float,
        orders: List[Order],
        order_depth: OrderDepth,
        position: int,
        buy_order_volume: int,
        sell_order_volume: int,
        prevent_adverse: bool = False,
        adverse_volume: int = 0,
    ) -> (int, int):
        """ Places aggressive orders if prices cross the fair_value +/- take_width. """
        position_limit = self.PRODUCT_PARAMS[product]["limit"]

        # Take profitable asks (Buy)
        if order_depth.sell_orders:
            best_ask = min(order_depth.sell_orders.keys())
            best_ask_volume = order_depth.sell_orders[best_ask] # Typically negative

            # Check if we should avoid this trade due to large volume (adverse selection)
            should_trade_ask = not prevent_adverse or abs(best_ask_volume) <= adverse_volume

            if should_trade_ask and best_ask <= fair_value - take_width:
                quantity_can_buy = position_limit - (position + buy_order_volume) # Max we can still buy
                quantity_to_buy = min(abs(best_ask_volume), quantity_can_buy)
                if quantity_to_buy > 0:
                    orders.append(Order(product, best_ask, quantity_to_buy))
                    buy_order_volume += quantity_to_buy
                    # Note: In a real simulation/exchange, we wouldn't modify order_depth here.
                    # This might be for internal simulation within the original code.
                    # For Prosperity, just placing the order is sufficient.

        # Take profitable bids (Sell)
        if order_depth.buy_orders:
            best_bid = max(order_depth.buy_orders.keys())
            best_bid_volume = order_depth.buy_orders[best_bid] # Typically positive

            # Check if we should avoid this trade due to large volume (adverse selection)
            should_trade_bid = not prevent_adverse or abs(best_bid_volume) <= adverse_volume

            if should_trade_bid and best_bid >= fair_value + take_width:
                quantity_can_sell = position_limit + (position - sell_order_volume) # Max we can still sell
                quantity_to_sell = min(abs(best_bid_volume), quantity_can_sell)
                if quantity_to_sell > 0:
                    orders.append(Order(product, best_bid, -quantity_to_sell))
                    sell_order_volume += quantity_to_sell
                    # Again, avoid modifying order_depth for Prosperity.

        return buy_order_volume, sell_order_volume

    def clear_position_order(
        self,
        product: str,
        fair_value: float,
        clear_width: float, # Can be float now
        orders: List[Order],
        order_depth: OrderDepth,
        position: int,
        buy_order_volume: int,  # Volume already committed to buying this step
        sell_order_volume: int, # Volume already committed to selling this step
    ) -> (int, int):
        """ Places orders to reduce inventory risk if position exists after takes. """
        position_limit = self.PRODUCT_PARAMS[product]["limit"]
        position_after_take = position + buy_order_volume - sell_order_volume

        # How much more can we buy/sell within limits *after* take orders?
        buy_remaining_capacity = position_limit - (position + buy_order_volume)
        sell_remaining_capacity = position_limit + (position - sell_order_volume)

        # Clear long position (Need to sell)
        if position_after_take > 0 and sell_remaining_capacity > 0:
            target_ask_price = round(fair_value + clear_width) # Price to sell at
            # How much volume exists at or better (higher) than our target price?
            available_bid_volume = sum(vol for price, vol in order_depth.buy_orders.items() if price >= target_ask_price)
            # We sell the minimum of: what we need to clear, what capacity we have left, what the market offers
            quantity_to_clear = min(position_after_take, sell_remaining_capacity, available_bid_volume)
            if quantity_to_clear > 0:
                orders.append(Order(product, target_ask_price, -quantity_to_clear))
                sell_order_volume += quantity_to_clear

        # Clear short position (Need to buy)
        elif position_after_take < 0 and buy_remaining_capacity > 0:
            target_bid_price = round(fair_value - clear_width) # Price to buy at
            # How much volume exists at or better (lower) than our target price?
            available_ask_volume = sum(abs(vol) for price, vol in order_depth.sell_orders.items() if price <= target_bid_price)
             # We buy the minimum of: what we need to clear, what capacity we have left, what the market offers
            quantity_to_clear = min(abs(position_after_take), buy_remaining_capacity, available_ask_volume)
            if quantity_to_clear > 0:
                orders.append(Order(product, target_bid_price, quantity_to_clear))
                buy_order_volume += quantity_to_clear

        return buy_order_volume, sell_order_volume


    def market_make(
        self,
        product: str,
        orders: List[Order],
        bid_price: int,
        ask_price: int,
        position: int,
        buy_order_volume: int,  # Volume already committed to buying this step (takes/clears)
        sell_order_volume: int, # Volume already committed to selling this step (takes/clears)
    ) -> (int, int):
        """ Places the passive bid and ask orders. """
        position_limit = self.PRODUCT_PARAMS[product]["limit"]

        # Calculate remaining capacity *after* considering takes/clears
        buy_quantity_allowed = position_limit - (position + buy_order_volume)
        if buy_quantity_allowed > 0:
            orders.append(Order(product, bid_price, buy_quantity_allowed)) # Buy order

        sell_quantity_allowed = position_limit + (position - sell_order_volume)
        if sell_quantity_allowed > 0:
            orders.append(Order(product, ask_price, -sell_quantity_allowed)) # Sell order

        # Note: We don't increment buy/sell_order_volume here because these are passive orders
        # that haven't filled yet. The tracking variables are for immediate fills (takes/clears).
        return buy_order_volume, sell_order_volume


    def make_orders(
        self,
        product: str,
        order_depth: OrderDepth,
        fair_value: float,
        position: int,
        buy_order_volume: int,  # Volume from takes/clears
        sell_order_volume: int, # Volume from takes/clears
        params: Dict[str, Any], # Pass specific product params
    ):
        """ Determines bid/ask prices and places passive making orders. """
        orders: List[Order] = []
        disregard_edge = params["disregard_edge"]
        join_edge = params["join_edge"]
        default_edge = params["default_edge"]
        manage_position = params.get("manage_position", False) # Use .get for optional params
        soft_position_limit = params.get("soft_position_limit", 0)

        # Find relevant existing orders to potentially penny or join
        asks_above_fair = [
            price for price in order_depth.sell_orders.keys()
            if price > fair_value + disregard_edge
        ]
        bids_below_fair = [
            price for price in order_depth.buy_orders.keys()
            if price < fair_value - disregard_edge
        ]

        best_ask_above_fair = min(asks_above_fair) if asks_above_fair else None
        best_bid_below_fair = max(bids_below_fair) if bids_below_fair else None

        # Determine Ask Price
        ask_price = round(fair_value + default_edge)
        if best_ask_above_fair is not None:
            if best_ask_above_fair <= fair_value + join_edge: # Use <= for join edge
                ask_price = best_ask_above_fair  # Join
            else:
                ask_price = best_ask_above_fair - 1  # Penny

        # Determine Bid Price
        bid_price = round(fair_value - default_edge)
        if best_bid_below_fair is not None:
            if best_bid_below_fair >= fair_value - join_edge: # Use >= for join edge
                 bid_price = best_bid_below_fair # Join
            else:
                 bid_price = best_bid_below_fair + 1 # Penny

        # Adjust for inventory skew if managing position
        effective_position = position + buy_order_volume - sell_order_volume
        if manage_position and soft_position_limit > 0:
            if effective_position > soft_position_limit:
                # Too long, make selling more attractive (lower ask) / buying less (lower bid - careful not to cross)
                ask_price -= 1
                # Maybe also lower bid slightly: bid_price -=1
            elif effective_position < -soft_position_limit:
                 # Too short, make buying more attractive (higher bid) / selling less (higher ask)
                bid_price += 1
                # Maybe also raise ask slightly: ask_price += 1

        # Ensure bid < ask
        bid_price = min(bid_price, ask_price - 1)

        # Place the market making orders
        buy_order_volume, sell_order_volume = self.market_make(
            product,
            orders, # Pass the local list for make orders
            bid_price,
            ask_price,
            position,
            buy_order_volume, # Pass volumes from takes/clears
            sell_order_volume,
        )

        return orders, buy_order_volume, sell_order_volume

    # --- Main Run Method ---
    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        """ Main trading logic entry point. """
        result = {}
        conversions = 0 # Example conversion value, adjust as needed
        traderObject = {} # Dictionary to store persistent state

        # Decode traderData if it exists
        if state.traderData is not None and state.traderData != "":
            try:
                traderObject = jsonpickle.decode(state.traderData)
                if not isinstance(traderObject, dict): # Ensure it's a dict
                    traderObject = {}
            except Exception as e:
                # print(f"Error decoding traderData: {e}") # Optional logging
                traderObject = {} # Reset if decoding fails

        for symbol in self.active_products:
            if symbol not in state.order_depths:
                continue # Skip if no market data for this product

            order_depth = state.order_depths[symbol]
            orders: List[Order] = []
            position = state.position.get(symbol, 0)
            params = self.PRODUCT_PARAMS.get(symbol, {})
            limit = params.get("limit", 0) # Get limit safely

            if not params or limit == 0: # Skip if no params or limit
                # print(f"Warning: No parameters or limit defined for {symbol}") # Optional logging
                continue

            # Track volume filled by takes/clears in this step for position management
            buy_volume_this_step = 0
            sell_volume_this_step = 0

            # --- Strategy Execution ---
            if symbol == Product.RAINFOREST_RESIN:
                # Use existing logic (assuming it's similar or replace with take/clear/make)
                # For consistency, let's use the take/clear/make pattern here too
                fair_value = params["fair_value"] # Static fair value for Resin

                # 1. Take Orders
                buy_volume_this_step, sell_volume_this_step = self.take_best_orders(
                     symbol, fair_value, params["take_width"], orders, order_depth, position,
                     buy_volume_this_step, sell_volume_this_step,
                     params.get("prevent_adverse", False), params.get("adverse_volume", 0) # Add adverse params if needed for Resin
                )
                # 2. Clear Orders
                buy_volume_this_step, sell_volume_this_step = self.clear_position_order(
                    symbol, fair_value, params["clear_width"], orders, order_depth, position,
                    buy_volume_this_step, sell_volume_this_step
                )
                # 3. Make Orders
                make_orders_list, _, _ = self.make_orders( # Buy/Sell volume already tracked
                    symbol, order_depth, fair_value, position,
                    buy_volume_this_step, sell_volume_this_step,
                    params # Pass all Resin params
                )
                orders.extend(make_orders_list)


            elif symbol == Product.KELP or symbol == Product.SQUID_INK:
                # Use dynamic fair value calculation and take/clear/make strategy
                fair_value = self.calculate_dynamic_fair_value(symbol, order_depth, traderObject)

                if fair_value is None:
                    # print(f"Could not calculate fair value for {symbol}, skipping trades.") # Optional logging
                    result[symbol] = [] # Send no orders if fair value is unavailable
                    continue # Move to next product

                # 1. Take Orders
                buy_volume_this_step, sell_volume_this_step = self.take_best_orders(
                    symbol, fair_value, params["take_width"], orders, order_depth, position,
                    buy_volume_this_step, sell_volume_this_step,
                    params["prevent_adverse"], params["adverse_volume"]
                )
                # 2. Clear Orders
                buy_volume_this_step, sell_volume_this_step = self.clear_position_order(
                    symbol, fair_value, params["clear_width"], orders, order_depth, position,
                    buy_volume_this_step, sell_volume_this_step
                )
                # 3. Make Orders
                make_orders_list, _, _ = self.make_orders( # Buy/Sell volume already tracked
                    symbol, order_depth, fair_value, position,
                    buy_volume_this_step, sell_volume_this_step,
                    params # Pass all params for KELP/INK
                )
                orders.extend(make_orders_list)

            else:
                # Placeholder for other potential products
                pass

            result[symbol] = orders

        # Encode the updated state back into traderData
        traderData = jsonpickle.encode(traderObject, unpicklable=False) # Make it simpler JSON if needed

        self.logger.flush(state, result, conversions, traderData) # If using logger

        return result, conversions, traderData