from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
from typing import List, Dict, Any
import numpy as np
from logger import Logger

class TradeHistory:
    """Tracks trading history and market trends for a specific product."""
    
    def __init__(self, max_length: int = 10) -> None:
        self.ask_list: List[float] = []
        self.bid_list: List[float] = []
        self.max_length: int = max_length
        self.trade_state: str = "H"  # H: Hold, B: Buy, S: Sell
        self.buy_low: float = -1
        self.sell_high: float = 1e10
        self.position: int = 0
        self.current_ask: float = 0
        self.current_bid: float = 0

    def push_ask(self, ask: float) -> None:
        """Update ask history and check for trends."""
        self._update_list(self.ask_list, ask)
        self.current_ask = ask
        self._check_trends()

    def push_bid(self, bid: float) -> None:
        """Update bid history and check for trends."""
        self._update_list(self.bid_list, bid)
        self.current_bid = bid
        self._check_trends()

    def push_both(self, ask: float, bid: float) -> None:
        """Convenience method to update both ask and bid."""
        self.push_ask(ask)
        self.push_bid(bid)

    def _update_list(self, lst: List[float], value: float) -> None:
        """Maintain a rolling window of historical prices."""
        if len(lst) == self.max_length:
            lst.pop(0)
        lst.append(value)

    def _check_trends(self) -> None:
        """Check for rising or falling market conditions."""
        self._is_falling()
        self._is_rising()

    def _is_falling(self) -> None:
        """Detect falling market conditions."""
        if len(self.bid_list) == self.max_length:
            avg_bid = np.mean(self.bid_list[:-1])
            if self.current_ask < avg_bid:
                if self.trade_state == "H":
                    self.trade_state = "B"
                    self.buy_low = avg_bid
                elif self.trade_state == "S":
                    self.trade_state = "H"

    def _is_rising(self) -> None:
        """Detect rising market conditions."""
        if len(self.ask_list) == self.max_length:
            avg_ask = np.mean(self.ask_list[:-1])
            if self.current_bid > avg_ask:
                if self.trade_state == "H":
                    self.trade_state = "S"
                    self.sell_high = avg_ask
                elif self.trade_state == "B":
                    self.trade_state = "H"

    def update_position(self, delta: int) -> None:
        """Update the current position."""
        self.position -= delta


class Trader:
    """Main trading class implementing different strategies for different products."""
    
    PRODUCT_PARAMS = {
        "RAINFOREST_RESIN": {"buy_low": 10000, "sell_high": 9999},
        "KELP": {"buy_low": 2015, "sell_high": 2020},
        "AMETHYSTS": {"buy_low": 10000, "sell_high": 9999},
        "STARFRUIT": {"buy_low": 2015, "sell_high": 2020}
    }
    
    def __init__(self):
        self.history: Dict[str, TradeHistory] = {}
        self.logger = Logger()
        self.active_products = ["AMETHYSTS", "STARFRUIT"]  # Default active products

    def _resin_strategy(self, history: TradeHistory, buy_low: int, sell_high: int, 
                       order_depth: OrderDepth, orders: List[Order], symbol: str) -> None:
        """Strategy for resin-like products (AMETHYSTS)."""
        if order_depth.sell_orders:
            for ask, ask_amount in order_depth.sell_orders.items():
                if int(ask) < buy_low:
                    orders.append(Order(symbol, ask, -ask_amount))
                    history.update_position(ask_amount)

        if order_depth.buy_orders:
            for bid, bid_amount in order_depth.buy_orders.items():
                if int(bid) > sell_high:
                    orders.append(Order(symbol, bid, -bid_amount))
                    history.update_position(bid_amount)

    def _kelp_strategy(self, history: TradeHistory, order_depth: OrderDepth, 
                      orders: List[Order], symbol: str) -> None:
        """Strategy for kelp-like products (STARFRUIT)."""
        if history.trade_state == "B" and order_depth.sell_orders:
            for ask, ask_amount in order_depth.sell_orders.items():
                if int(ask) < history.buy_low:
                    real_amount = min(-ask_amount, 5)
                    orders.append(Order(symbol, ask, real_amount))
                    history.update_position(real_amount)

        if history.trade_state == "S" and order_depth.buy_orders:
            for bid, bid_amount in order_depth.buy_orders.items():
                if int(bid) > history.sell_high:
                    real_amount = min(bid_amount, 5)
                    orders.append(Order(symbol, bid, -real_amount))
                    history.update_position(-real_amount)

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        """Main trading method called each timestamp."""
        self.logger.print("traderData:", state.traderData)
        self.logger.print("Observations:", str(state.observations))

        # Initialize history on first run
        if state.timestamp == 0:
            for symbol in state.order_depths:
                self.history[symbol] = TradeHistory()

        result = {}
        
        for symbol, order_depth in state.order_depths.items():
            if symbol not in self.history:
                self.history[symbol] = TradeHistory()

            orders = []
            history = self.history[symbol]

            # Update market data
            if order_depth.sell_orders:
                best_ask = next(iter(order_depth.sell_orders))
                history.push_ask(best_ask)
                
            if order_depth.buy_orders:
                best_bid = next(iter(order_depth.buy_orders))
                history.push_bid(best_bid)

            # Log current trade state
            if history.trade_state in ["S", "B"]:
                self.logger.print(f"{history.trade_state}_STATE", symbol)

            # Apply appropriate strategy
            params = self.PRODUCT_PARAMS.get(symbol, {})
            if symbol == self.active_products[1]:  # STARFRUIT/KELP
                self._kelp_strategy(history, order_depth, orders, symbol)
            elif symbol == self.active_products[0]:  # AMETHYSTS/RESIN
                self._resin_strategy(history, params.get("buy_low", 0), 
                                   params.get("sell_high", 0), order_depth, 
                                   orders, symbol)

            result[symbol] = orders
        self.logger.flush(state, result, 1, "SAMPLE")
        return result, 1, "SAMPLE"
    