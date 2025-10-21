from typing import List, Dict


def compute_simple_momentum(data: List[Dict[str, float]], window: int = 5) -> float:
    """Return simple momentum: last close minus close N periods ago."""
    if not data or len(data) < window + 1:
        return 0.0
    return float(data[-1]['close']) - float(data[-1 - window]['close'])


