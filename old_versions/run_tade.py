from example import TradeHistory, Trader

from datamodel import Listing, OrderDepth, Trade, TradingState

timestamp = 1000

listings = {
	"KELP": Listing(
		symbol="KELP", 
		product="KELP", 
		denomination= "SEASHELLS"
	),
	"RAINFOREST_RESIN": Listing(
		symbol="RAINFOREST_RESIN", 
		product="RAINFOREST_RESIN", 
		denomination= "SEASHELLS"
	),
}

order_depths = {
	"KELP": OrderDepth(
	),
	"RAINFOREST_RESIN": OrderDepth(
	),	
}

order_depths["KELP"].buy_orders = {10: 7, 9: 5}
order_depths["KELP"].sell_orders = {11: -4, 12: -8}

order_depths["RAINFOREST_RESIN"].buy_orders = {142: 3, 141: 5}
order_depths["RAINFOREST_RESIN"].sell_orders = {144: -5, 145: -8}

own_trades = {
	"KELP": [],
	"RAINFOREST_RESIN": []
}

market_trades = {
	"KELP": [
		Trade(
			symbol="KELP",
			price=11,
			quantity=4,
			buyer="",
			seller="",
			timestamp=900
		)
	],
	"RAINFOREST_RESIN": []
}

position = {
	"KELP": 3,
	"RAINFOREST_RESIN": -5
}

observations = {}
traderData = ""

state = TradingState(
	traderData,
	timestamp,
  listings,
	order_depths,
	own_trades,
	market_trades,
	position,
	observations
)

hello=Trader()

print(hello.run(state))