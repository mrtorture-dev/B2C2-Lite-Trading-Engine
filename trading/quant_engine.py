import numpy as np

class B2C2QuantEngine:
    """
    Ultra-HFT Alpha Engine.
    Dynamic sizing based on volatility and Z-Score alignment.
    """
    def __init__(self, skew_coefficient=0.5):
        self.gamma = float(skew_coefficient)

    def decide_live_action(self, current_price, trades_df, session_pos):
        prices = trades_df['price'].astype(float).values
        ma = np.mean(prices)
        std = np.std(prices) + 1e-9
        z_score = (current_price - ma) / std
        
        # 1. VOLATILITY SIZING
        # Calculate recent volatility (last 30 ticks)
        vol = std / (ma + 1e-9)
        # Sizing: base 10 BTC, increases with volatility and price deviation
        amount = 10.0 * (1 + (vol * 5000)) * (1 + abs(z_score))
        amount = round(amount * np.random.uniform(0.9, 1.1), 2)
        amount = np.clip(amount, 5.0, 500.0) # Move between 5 and 500 BTC

        # 2. AGGRESSIVE SIGNAL
        # Bias is purely based on price deviation.
        # We ignore total inventory to allow BUYING.
        if z_score < -0.5:
            return {'side': 'BUY', 'amount': amount, 'reason': f'DIP_HUNT_Z:{z_score:.2f}'}
        elif z_score > 0.5:
            return {'side': 'SELL', 'amount': amount, 'reason': f'PEAK_SELL_Z:{z_score:.2f}'}
        
        # In balance, we flip a coin for liquidity
        return {'side': 'BUY' if np.random.rand() > 0.5 else 'SELL', 'amount': round(amount/2, 2), 'reason': 'MARKET_MAKING'}

    def calculate_greeks(self, inventory_q, fair_price, last_price):
        return {'delta': inventory_q * fair_price, 'gamma': 0.0001, 'theta': -0.01}
    
    def run_adaptive_optimization(self, t, g, p):
        return {'new_gamma': g, 'regime': 'ALPHA_MAX'}
    
    def calculate_performance_metrics(self, t): return {'sharpe': 0, 'mdd': 0}
