import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statistics

all_prices_df=pd.read_csv("round_1_data/prices_round_1_day_-2.csv")

ink_prices_df=all_prices_df[all_prices_df["product"]=="SQUID_INK"]

ink_prices=list(ink_prices_df["bid_price_1"])



import seaborn as sns

def delta_heatmap_half_integer(data):
    # First-order differences
    deltas = np.diff(data)

    # X = Δ[i], Y = Δ[i+1]
    x = deltas[:-1]
    y = deltas[1:]

    # Define bin edges for half-integer steps from -5 to 5
    bin_edges = np.arange(-5.25, 5.75, 0.5)  # Covers -5 to 5 with center bins

    # Create 2D histogram
    heatmap, xedges, yedges = np.histogram2d(x, y, bins=[bin_edges, bin_edges])

    # Plot heatmap
    plt.figure(figsize=(8, 6))
    sns.heatmap(
        heatmap.T,
        xticklabels=np.round(xedges[:-1] + 0.25, 2),  # center of each bin
        yticklabels=np.round(yedges[:-1] + 0.25, 2),
        cmap='coolwarm',
        cbar_kws={'label': 'Frequency'},
        square=True
    )
    plt.title('Heatmap of Δ[i] vs Δ[i+1]')
    plt.xlabel('Δ[i] (in 0.5 steps)')
    plt.ylabel('Δ[i+1] (in 0.5 steps)')
    plt.xticks(rotation=45)
    plt.yticks(rotation=0)
    plt.xlim(0, len(bin_edges)-1)
    plt.ylim(0, len(bin_edges)-1)
    plt.tight_layout()
    plt.show()

def conditional_mean_delta_with_error(data):

    deltas = np.diff(data)
    x = deltas[:-1]      # Δ[i]
    y = deltas[1:]       # Δ[i+1]

    # Define possible delta values: from -5.0 to 5.0 in 0.5 steps
    delta_vals = np.arange(-5.0, 5.1, 0.5)
    mean_next_delta = []
    std_next_delta = []

    for d in delta_vals:
        # Select indices where Δ[i] ≈ d (using tolerance for float matching)
        indices = np.where(np.isclose(x, d, atol=0.25))[0]
        if len(indices) > 0:
            mean = np.mean(y[indices])
            std = np.std(y[indices])
        else:
            mean = np.nan
            std = np.nan
        mean_next_delta.append(mean)
        std_next_delta.append(std)

    # Plot
    plt.figure(figsize=(10, 6))
    plt.errorbar(
        delta_vals,
        mean_next_delta,
        yerr=std_next_delta,
        fmt='o',
        capsize=4,
        color='purple',
        ecolor='gray',
        label='Mean ± Std Dev'
    )
    plt.axhline(0, linestyle='--', color='black', linewidth=0.8)
    plt.axvline(0, linestyle='--', color='black', linewidth=0.8)
    plt.title('Mean of Δ[i+1] Given Δ[i] (with Std Dev)')
    plt.xlabel('Δ[i]')
    plt.ylabel('E[Δ[i+1] | Δ[i]] ± Std Dev')
    plt.grid(True)
    plt.xticks(delta_vals, rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.show()
def first_difference_correlation(values, max_j=100, delta_t=1):
    """
    Computes correlation between (values[i + delta_t] - values[i]) and 
    (values[i + j + delta_t] - values[i + j]) for j from 1 to max_j.

    Parameters:
    - values: list or array of numeric values
    - max_j: maximum lag to evaluate
    - delta_t: step size for computing deltas (e.g., 1st diff, 2nd diff, etc.)
    """
    n = len(values)
    correlations = []

    for j in range(1, max_j + 1):
        diffs_1 = []
        diffs_2 = []
        for i in range(n - j - delta_t):
            diff1 = values[i + delta_t] - values[i]
            diff2 = values[i + j + delta_t] - values[i + j]
            diffs_1.append(diff1)
            diffs_2.append(diff2)
        if len(diffs_1) > 1:
            corr = np.corrcoef(diffs_1, diffs_2)[0, 1]
        else:
            corr = np.nan
        correlations.append(corr)

    # Plot
    plt.figure(figsize=(10, 5))
    plt.plot(range(1, max_j + 1), correlations, marker='o', linestyle='-', color='darkgreen')
    plt.title(f'Correlation between Δ[i] and Δ[i + j] (Δt = {delta_t})')
    plt.xlabel('j (lag)')
    plt.ylabel('Correlation Coefficient')
    plt.axhline(0, color='black', linestyle='--', linewidth=1)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    return correlations
# Example data

def plot_multiple_delta_correlations(values, max_j=100, delta_ts=range(1, 21)):
    """
    Computes and plots correlations for multiple delta_t values on the same graph,
    excluding cases where j < delta_t.
    
    Parameters:
    - values: list or array of numeric values
    - max_j: maximum lag to evaluate
    - delta_ts: list of delta_t values to plot
    """
    plt.figure(figsize=(12, 6))
    
    for delta_t in delta_ts:
        correlations = []
        valid_js = []  # To keep track of which j's we actually calculated
        
        for j in range(1, max_j + 1):
            # Skip cases where j < delta_t
            if j < delta_t:
                continue
                
            diffs_1 = []
            diffs_2 = []
            for i in range(len(values) - j - delta_t):
                diff1 = values[i + delta_t] - values[i]
                diff2 = values[i + j + delta_t] - values[i + j]
                diffs_1.append(diff1)
                diffs_2.append(diff2)
            
            if len(diffs_1) > 1:
                corr = np.corrcoef(diffs_1, diffs_2)[0, 1]
            else:
                corr = np.nan
                
            correlations.append(corr)
            valid_js.append(j)
        
        # Plot only the valid j values for this delta_t
        plt.plot(valid_js, correlations, marker='', linestyle='-', 
                label=f'Δt = {delta_t}')
    
    plt.title('Correlation between Δ[i] and Δ[i + j] (excluding j < Δt)')
    plt.xlabel('j (lag)')
    plt.ylabel('Correlation Coefficient')
    plt.axhline(0, color='black', linestyle='--', linewidth=1)
    plt.grid(True)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.show()
# Example usage:
# values = your_time_series_data
# plot_multiple_delta_correlations(values, max_j=100, delta_ts=range(1, 21))

def delta_distribution(values):
    v_array=np.array(values)
    delta=v_array[1:]-v_array[:-1]
    plt.hist(delta)
    plt.show()


data = ink_prices
# Generate heatmap
delta_distribution(data)