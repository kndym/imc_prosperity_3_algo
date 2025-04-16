import pandas as pd
import numpy as np

all_prices_df=pd.read_csv("round 3 analysis\prices_round_3_day_0.csv")

real_asset_data=all_prices_df[all_prices_df["product"]=="VOLCANIC_ROCK"]

underlying_price=real_asset_data["mid_price"]

voucher_data={}

vouch_strikes={}

for x in range(5):
    y=9500+x*250
    new_str="VOLCANIC_ROCK_VOUCHER_"+str(y)
    vouch_strikes[new_str]=y
    voucher_data[new_str]=all_prices_df[all_prices_df["product"]==new_str]



