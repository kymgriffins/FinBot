import os
import logging
from typing import Dict, Optional

from .data_adapters.fmp_adapter import FMPAdapter
from .data_adapters.yfinance_adapter import YFinanceAdapter
from .data_adapters.polygon_adapter import PolygonAdapter

logger = logging.getLogger(__name__)

# Minimal provider registry. Add more adapters (TwelveData, Binance, CME) when implemented.
AVAILABLE_PROVIDERS = ['yfinance', 'fmp', 'polygon']

# Canonical -> provider-specific symbol map
CANONICAL_SYMBOL_MAP: Dict[str, Dict[str, str]] = {
    'GOLD': {'yfinance': 'GC=F', 'fmp': 'GOLD', 'polygon': 'GC'},
    'SILVER': {'yfinance': 'SI=F', 'fmp': 'SILVER', 'polygon': 'SI'},
    'BTC': {'yfinance': 'BTC-USD', 'fmp': 'BTCUSD', 'polygon': 'BTCUSD'},
    # extend as needed
}


def get_adapter(name: str):
    key = (name or '').lower()
    if key == 'fmp':
        return FMPAdapter()
    if key == 'yfinance' or key == 'yf':
        return YFinanceAdapter()
    if key == 'polygon':
        return PolygonAdapter()
    logger.warning(f"Requested unknown provider '{name}', falling back to yfinance")
    return YFinanceAdapter()


def map_symbol_to_provider(input_symbol: str, provider: str) -> Optional[str]:
    if not input_symbol:
        return None
    s = input_symbol.strip().upper()

    # direct canonical match
    if s in CANONICAL_SYMBOL_MAP:
        return CANONICAL_SYMBOL_MAP[s].get(provider) or s

    # check if input already matches a provider-specific value
    for canon, mapping in CANONICAL_SYMBOL_MAP.items():
        for prov, sym in mapping.items():
            if sym and sym.upper() == s:
                # return provider-specific symbol for desired provider
                return mapping.get(provider) or s

    # fallback to input
    return input_symbol
