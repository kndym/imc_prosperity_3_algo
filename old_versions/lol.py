import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

all_prices_df=pd.read_csv("round_1_data/prices_round_1_day_-2.csv")

ink_prices_df=all_prices_df[all_prices_df["product"]=="SQUID_INK"]

ink_prices=list(ink_prices_df["mid_price"])


# --- Simulate realistic KELP midprice data (replace later with your real data) ---
np.random.seed(42)
kelp_prices = np.array(ink_prices)

# --- Calculate indicators ---
velocity = np.diff(kelp_prices, prepend=kelp_prices[0])
acceleration = np.diff(velocity, prepend=velocity[0])
rolling_mean = pd.Series(kelp_prices).rolling(50).mean()
rolling_std = pd.Series(kelp_prices).rolling(50).std()
zscore = (pd.Series(kelp_prices) - rolling_mean) / rolling_std
zscore = zscore.fillna(0).values  # Replace NaN with 0

# --- Q-Learning Setup ---
n_price_bins = 10
n_zscore_bins = 5
n_actions = 3  # 0 = Hold, 1 = Buy, 2 = Sell
price_bins = np.linspace(min(kelp_prices), max(kelp_prices), n_price_bins)
zscore_bins = np.linspace(-3, 3, n_zscore_bins)

q_table = np.zeros((n_price_bins, n_zscore_bins, n_actions))

# --- Hyperparameters ---
alpha = 0.1
gamma = 0.95
epsilon = 1.0
epsilon_decay = 0.995
min_epsilon = 0.01
episodes = 100
position_size = 50

# --- Helper function to get state ---
def get_state(price, z):
    p_bin = min(np.digitize(price, price_bins) - 1, n_price_bins - 1)
    z_bin = min(np.digitize(z, zscore_bins) - 1, n_zscore_bins - 1)
    return p_bin, z_bin

# --- Training the agent ---
reward_history = []
profit_history = []

for ep in range(episodes):
    inventory = 0
    cash = 0
    total_reward = 0
    buy_price = 0

    for t in range(1, len(kelp_prices)):
        price = kelp_prices[t]
        state = get_state(price, zscore[t])

        # ε-greedy with indicator awareness
        if np.random.rand() < epsilon:
            action = np.random.randint(n_actions)
        else:
            if inventory > 0 and price - buy_price > 2:
                action = 0  # Hold after profit
            elif zscore[t] < -1 and velocity[t] > 0:
                action = 1  # Buy
            elif zscore[t] > 1 and velocity[t] < 0 and inventory > 0:
                action = 2  # Sell
            else:
                action = np.argmax(q_table[state])

        reward = 0

        # --- Trade Logic ---
        if action == 1 and inventory == 0:
            inventory = position_size
            buy_price = price
        elif action == 2 and inventory > 0:
            reward = (price - buy_price) * inventory
            cash += reward
            inventory = 0
        else:
            reward = -0.1  # small penalty to discourage doing nothing too long

        # --- Q-Table Update ---
        next_state = get_state(price, zscore[t])
        old_value = q_table[state][action]
        next_max = np.max(q_table[next_state])
        new_value = old_value + alpha * (reward + gamma * next_max - old_value)
        q_table[state][action] = new_value

        total_reward += reward

    epsilon = max(min_epsilon, epsilon * epsilon_decay)
    reward_history.append(total_reward)
    profit_history.append(cash)
    print(f"Episode {ep}, Total Reward: {total_reward:.2f}, Total Profit: {cash:.2f}")

# --- Plot Reward & Profit Over Episodes ---
plt.figure(figsize=(14, 5))

plt.subplot(1, 2, 1)
plt.plot(reward_history)
plt.title("Total Reward per Episode")
plt.xlabel("Episode")
plt.ylabel("Reward")
plt.grid(True)

plt.subplot(1, 2, 2)
plt.plot(profit_history)
plt.title("Cumulative Profit per Episode")
plt.xlabel("Episode")
plt.ylabel("Profit ($)")
plt.grid(True)

plt.tight_layout()
plt.show()

# --- Final Profit Summary ---
print("\nFinal 5 Episode Profits:")
print(profit_history[-5:])
print(f"💰 Final Total Profit: ${profit_history[-1]:.2f}")
