import numpy as np

def expected_pnl(b1, b2, avg):
    e1 = 0.0
    e2 = 0.0

    # First interval [160, 200]
    prob_interval = 4 / 11
    a_low, b_low = 160, 200

    # Contribution to E1
    if b1 <= a_low:
        p_b1_gt_low = 0.0
    elif b1 >= b_low:
        p_b1_gt_low = 1.0
    else:
        p_b1_gt_low = (b1 - a_low) / (b_low - a_low)
    e1 += prob_interval * p_b1_gt_low * (320 - b1)

    # Contribution to E2 from first interval
    res_low_low = max(b1, a_low)
    res_low_high = b_low
    if res_low_low >= res_low_high:
        p_b2_gt_low = 0.0
    else:
        if b2 <= res_low_low:
            p_b2_gt_low = 0.0
        elif b2 >= res_low_high:
            p_b2_gt_low = 1.0
        else:
            p_b2_gt_low = (b2 - res_low_low) / (res_low_high - res_low_low)
    if b2 > avg:
        term_low = (320 - b2) * p_b2_gt_low
    else:
        if b2 >= 320:
            p_factor = 0.0
        else:
            p_factor = ((320 - avg) / (320 - b2)) ** 3
        term_low = (320 - b2) * p_factor * p_b2_gt_low
    e2 += prob_interval * (1 - p_b1_gt_low) * term_low

    # Second interval [250, 320]
    prob_interval = 7 / 11
    a_high, b_high = 250, 320

    # Contribution to E1
    if b1 <= a_high:
        p_b1_gt_high = 0.0
    elif b1 >= b_high:
        p_b1_gt_high = 1.0
    else:
        p_b1_gt_high = (b1 - a_high) / (b_high - a_high)
    e1 += prob_interval * p_b1_gt_high * (320 - b1)

    # Contribution to E2 from second interval
    res_high_low = max(b1, a_high)
    res_high_high = b_high
    if res_high_low >= res_high_high:
        p_b2_gt_high = 0.0
    else:
        if b2 <= res_high_low:
            p_b2_gt_high = 0.0
        elif b2 >= res_high_high:
            p_b2_gt_high = 1.0
        else:
            p_b2_gt_high = (b2 - res_high_low) / (res_high_high - res_high_low)
    if b2 > avg:
        term_high = (320 - b2) * p_b2_gt_high
    else:
        if b2 >= 320:
            p_factor = 0.0
        else:
            p_factor = ((320 - avg) / (320 - b2)) ** 3
        term_high = (320 - b2) * p_factor * p_b2_gt_high
    e2 += prob_interval * (1 - p_b1_gt_high) * term_high

    return e1 + e2

def find_optimal_bids(avg_second_bid, b1_min=160, b1_max=320, b2_min=160, b2_max=320, step=1):
    # Generate possible bids, avoiding the gap between 200 and 250 for bids
    # Bids can technically be in the gap, but since reserves are not in the gap, it's irrelevant
    b1_candidates = []
    for b in range(b1_min, b1_max + 1, step):
        if not (200 < b < 250):
            b1_candidates.append(b)
    b2_candidates = []
    for b in range(b2_min, b2_max + 1, step):
        if not (200 < b < 250):
            b2_candidates.append(b)

    max_pnl = -np.inf
    best_b1 = None
    best_b2 = None

    for b1 in b1_candidates:
        for b2 in b2_candidates:
            current_pnl = expected_pnl(b1, b2, avg_second_bid)
            if current_pnl > max_pnl:
                max_pnl = current_pnl
                best_b1 = b1
                best_b2 = b2
    return best_b1, best_b2, max_pnl

# Example usage with an assumed average_second_bid
average_second_bid = 280  # Assumed value for demonstration
optimal_b1, optimal_b2, max_epnl = find_optimal_bids(average_second_bid)
print(f"Optimal first bid: {optimal_b1}, Optimal second bid: {optimal_b2}, Max expected PNL: {max_epnl:.2f}")