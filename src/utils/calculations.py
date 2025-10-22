"""
Financial calculations for Gr8 Agent
"""

from typing import Dict, Any, Optional
import math

def calculate_pnl(trade_type: str, entry_price: float, exit_price: float,
                 position_size: float, fees: float = 0.0) -> float:
    """
    Calculate profit and loss for a trade

    Args:
        trade_type: 'long' or 'short'
        entry_price: Entry price of the trade
        exit_price: Exit price of the trade
        position_size: Size of the position
        fees: Trading fees

    Returns:
        P&L amount
    """
    try:
        if trade_type.lower() == 'long':
            pnl = (exit_price - entry_price) * position_size - fees
        elif trade_type.lower() == 'short':
            pnl = (entry_price - exit_price) * position_size - fees
        else:
            raise ValueError(f"Invalid trade type: {trade_type}")

        return round(pnl, 2)

    except Exception as e:
        raise ValueError(f"Error calculating P&L: {e}")

def calculate_risk_metrics(trade_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate risk metrics for a trade

    Args:
        trade_data: Dictionary containing trade information

    Returns:
        Dictionary with risk metrics
    """
    try:
        entry_price = float(trade_data.get('entry_price', 0))
        position_size = float(trade_data.get('position_size', 0))
        trade_type = trade_data.get('trade_type', 'long')

        if entry_price <= 0 or position_size <= 0:
            return {}

        # Calculate position value
        position_value = entry_price * position_size

        # Calculate risk per share (2% of entry price)
        risk_per_share = entry_price * 0.02

        # Calculate stop loss levels
        if trade_type.lower() == 'long':
            stop_loss = entry_price * 0.98  # 2% below entry
            take_profit = entry_price * 1.06  # 6% above entry (1:3 risk-reward)
        else:
            stop_loss = entry_price * 1.02  # 2% above entry
            take_profit = entry_price * 0.94  # 6% below entry (1:3 risk-reward)

        # Calculate risk-reward ratio
        if trade_type.lower() == 'long':
            risk_amount = entry_price - stop_loss
            reward_amount = take_profit - entry_price
        else:
            risk_amount = stop_loss - entry_price
            reward_amount = entry_price - take_profit

        risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0

        return {
            'position_value': round(position_value, 2),
            'risk_per_share': round(risk_per_share, 2),
            'stop_loss': round(stop_loss, 2),
            'take_profit': round(take_profit, 2),
            'risk_reward_ratio': round(risk_reward_ratio, 2),
            'risk_amount': round(risk_amount, 2),
            'reward_amount': round(reward_amount, 2),
            'position_size_pct': 0.0,  # Would need portfolio value
            'calculated_at': trade_data.get('created_at', '')
        }

    except Exception as e:
        return {'error': str(e)}

def calculate_sharpe_ratio(returns: list, risk_free_rate: float = 0.02) -> float:
    """
    Calculate Sharpe ratio

    Args:
        returns: List of returns
        risk_free_rate: Risk-free rate (annual)

    Returns:
        Sharpe ratio
    """
    try:
        if not returns or len(returns) < 2:
            return 0.0

        # Calculate mean return
        mean_return = sum(returns) / len(returns)

        # Calculate standard deviation
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = math.sqrt(variance)

        if std_dev == 0:
            return 0.0

        # Annualize if needed (assuming daily returns)
        annualized_return = mean_return * 252  # 252 trading days
        annualized_std = std_dev * math.sqrt(252)

        # Calculate Sharpe ratio
        sharpe_ratio = (annualized_return - risk_free_rate) / annualized_std

        return round(sharpe_ratio, 4)

    except Exception as e:
        return 0.0

def calculate_max_drawdown(equity_curve: list) -> float:
    """
    Calculate maximum drawdown

    Args:
        equity_curve: List of equity values over time

    Returns:
        Maximum drawdown as a percentage
    """
    try:
        if not equity_curve or len(equity_curve) < 2:
            return 0.0

        peak = equity_curve[0]
        max_drawdown = 0.0

        for value in equity_curve:
            if value > peak:
                peak = value

            drawdown = (peak - value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        return round(max_drawdown * 100, 2)  # Return as percentage

    except Exception as e:
        return 0.0

def calculate_win_rate(returns: list) -> float:
    """
    Calculate win rate

    Args:
        returns: List of returns

    Returns:
        Win rate as a percentage
    """
    try:
        if not returns:
            return 0.0

        winning_trades = sum(1 for r in returns if r > 0)
        total_trades = len(returns)

        win_rate = (winning_trades / total_trades) * 100

        return round(win_rate, 2)

    except Exception as e:
        return 0.0

def calculate_profit_factor(gross_profit: float, gross_loss: float) -> float:
    """
    Calculate profit factor

    Args:
        gross_profit: Total gross profit
        gross_loss: Total gross loss (positive number)

    Returns:
        Profit factor
    """
    try:
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0

        profit_factor = gross_profit / gross_loss

        return round(profit_factor, 2)

    except Exception as e:
        return 0.0

def calculate_position_size(account_balance: float, risk_per_trade: float,
                          entry_price: float, stop_loss: float) -> float:
    """
    Calculate position size based on risk management

    Args:
        account_balance: Total account balance
        risk_per_trade: Risk percentage per trade (e.g., 0.02 for 2%)
        entry_price: Entry price
        stop_loss: Stop loss price

    Returns:
        Position size
    """
    try:
        # Calculate risk amount
        risk_amount = account_balance * risk_per_trade

        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss)

        if risk_per_share == 0:
            return 0.0

        # Calculate position size
        position_size = risk_amount / risk_per_share

        return round(position_size, 2)

    except Exception as e:
        return 0.0
