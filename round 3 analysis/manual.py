import numpy as np

def simulate_trades(num_simulations=10_000_000, b1=200, b2=285, sale_price=320):
    """
    Simulate sea turtle trades:
      - Turtles in the lower group (reserve ∈ [160,200]) are attempted using first bid b1.
      - Turtles in the upper group (reserve ∈ [250,320]) are attempted with second bid b2.
      
    Parameters:
      num_simulations: number of turtles to simulate
      b1: first bid (expected to target the lower group)
      b2: second bid (expected to target the upper group)
      sale_price: The price at which you can sell the flipper (320 SeaShells)
    
    Returns:
      expected_profit: average profit per turtle encountered,
      details: dictionary with breakdown by group.
    """
    # Total measure over two intervals: lower = 40, upper = 70, so total = 110.
    # The probability of turtle coming from lower group is 40/110,
    # and from the upper group is 70/110.
    lower_prob = 40/110
    upper_prob = 70/110

    # Generate random numbers to select group and then sample reserve prices accordingly.
    groups = np.random.choice(['lower', 'upper'], size=num_simulations, p=[lower_prob, upper_prob])
    
    # Preallocate profit array
    profits = np.zeros(num_simulations)
    
    # Process lower group: reserve price uniform between 160 and 200.
    lower_mask = groups == 'lower'
    # Draw reserves for lower group.
    reserves_lower = np.random.uniform(160, 200, size=lower_mask.sum())
    # First bid is applied: if b1 > reserve then trade happens.
    trade_lower = b1 > reserves_lower  # note: if reserve equals exactly b1 this occurs with probability zero in continuous uniform.
    profits_lower = np.where(trade_lower, sale_price - b1, 0)
    profits[lower_mask] = profits_lower
    
    # Process upper group: reserve price uniform between 250 and 320.
    upper_mask = groups == 'upper'
    reserves_upper = np.random.uniform(250, 320, size=upper_mask.sum())
    # For these, first bid (200) is always too low, so we use the second bid.
    trade_upper = b2 > reserves_upper
    # In equilibrium, b2 is set equal to the average among traders so p=1.
    profits_upper = np.where(trade_upper, sale_price - b2, 0)
    profits[upper_mask] = profits_upper

    overall_profit = np.mean(profits)
    
    # Break down expected profit by group:
    avg_profit_lower = profits_lower.mean() if len(profits_lower) > 0 else 0
    avg_profit_upper = profits_upper.mean() if len(profits_upper) > 0 else 0

    details = {
        'lower_group_fraction': lower_prob,
        'upper_group_fraction': upper_prob,
        'avg_profit_lower': avg_profit_lower,
        'avg_profit_upper': avg_profit_upper,
    }
    return overall_profit, details

def main():
    # Set the equilibrium bids as derived: b1=200, b2=285
    b1 = 200
    b2 = 285
    sale_price = 320
    num_simulations = 10_000_000
    expected_profit, details = simulate_trades(num_simulations, b1, b2, sale_price)
    print(f"Simulation with b1 = {b1} and b2 = {b2}:")
    print(f"  Expected profit per turtle: {expected_profit:.3f} SeaShells")
    print("Breakdown:")
    for k, v in details.items():
        print(f"  {k}: {v}")

    # Optionally, perform a grid search for the second bid for the upper group (only)
    # to verify that b2 = 285 maximizes the expected pnl for turtles in the upper group.
    b2_vals = np.linspace(250, 320, 71)
    pnl_second = []
    for bid in b2_vals:
        # For turtles with reserve uniformly in [250,320]:
        # probability = (bid - 250) / 70, profit = 320 - bid
        # so expected profit = ((bid - 250)/70) * (320 - bid)
        pnl_second.append(((bid - 250)/70) * (320 - bid))
    pnl_second = np.array(pnl_second)
    optimal_index = np.argmax(pnl_second)
    optimal_b2 = b2_vals[optimal_index]
    optimal_pnl = pnl_second[optimal_index]
    print("\nGrid search for optimal second bid (upper group):")
    print(f"  Optimal second bid is approximately {optimal_b2:.1f} with expected pnl: {optimal_pnl:.3f} SeaShells")
    
if __name__ == "__main__":
    main()
