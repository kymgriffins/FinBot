"""
Multi-Source Data Validator for Gr8 Agent
Validates data across multiple sources and provides consensus
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging
from dataclasses import dataclass
from enum import Enum
from ..adapters.base_adapter import BaseDataAdapter, ValidationResult, DataQuality

logger = logging.getLogger(__name__)

class ConsensusMethod(Enum):
    """Methods for reaching consensus across data sources"""
    MAJORITY = "majority"
    WEIGHTED_AVERAGE = "weighted_average"
    HIGHEST_QUALITY = "highest_quality"
    MEDIAN = "median"

@dataclass
class DataSourceResult:
    """Result from a single data source"""
    adapter: BaseDataAdapter
    data: pd.DataFrame
    validation_result: ValidationResult
    weight: float = 1.0

@dataclass
class ConsensusResult:
    """Result of multi-source consensus"""
    consensus_data: pd.DataFrame
    confidence_score: float  # 0-1
    source_agreement: Dict[str, float]  # Agreement percentage per source
    anomalies: List[Dict[str, Any]]
    metadata: Dict[str, Any]

class MultiSourceValidator:
    """Validates data across multiple sources and provides consensus"""

    def __init__(self, adapters: List[BaseDataAdapter],
                 consensus_method: ConsensusMethod = ConsensusMethod.WEIGHTED_AVERAGE):
        self.adapters = adapters
        self.consensus_method = consensus_method
        self.anomaly_threshold = 0.1  # 10% deviation threshold
        self.min_sources = 2  # Minimum sources for consensus

    def get_consensus_data(self, symbol: str, start_date: datetime, end_date: datetime,
                          interval: str = '1d') -> ConsensusResult:
        """Get consensus data from multiple sources"""
        try:
            # Fetch data from all sources
            source_results = []
            for adapter in self.adapters:
                try:
                    if not adapter.is_available():
                        logger.warning(f"Adapter {adapter.__class__.__name__} not available")
                        continue

                    data = adapter.fetch_data(symbol, start_date, end_date, interval)
                    if data.empty:
                        continue

                    validation_result = adapter.validate_data(data)
                    weight = adapter.get_source_reliability()

                    source_results.append(DataSourceResult(
                        adapter=adapter,
                        data=data,
                        validation_result=validation_result,
                        weight=weight
                    ))

                except Exception as e:
                    logger.error(f"Error fetching data from {adapter.__class__.__name__}: {e}")
                    continue

            if len(source_results) < self.min_sources:
                logger.warning(f"Insufficient data sources for consensus: {len(source_results)}")
                return self._create_fallback_result(source_results)

            # Create consensus
            consensus_data = self._create_consensus(source_results)

            # Calculate confidence and agreement
            confidence_score = self._calculate_confidence(source_results, consensus_data)
            source_agreement = self._calculate_source_agreement(source_results, consensus_data)

            # Detect anomalies
            anomalies = self._detect_anomalies(source_results, consensus_data)

            return ConsensusResult(
                consensus_data=consensus_data,
                confidence_score=confidence_score,
                source_agreement=source_agreement,
                anomalies=anomalies,
                metadata={
                    'sources_used': len(source_results),
                    'consensus_method': self.consensus_method.value,
                    'symbol': symbol,
                    'date_range': f"{start_date.date()} to {end_date.date()}",
                    'interval': interval
                }
            )

        except Exception as e:
            logger.error(f"Error in multi-source validation: {e}")
            return self._create_error_result(str(e))

    def _create_consensus(self, source_results: List[DataSourceResult]) -> pd.DataFrame:
        """Create consensus data from multiple sources"""
        if not source_results:
            return pd.DataFrame()

        if len(source_results) == 1:
            return source_results[0].data.copy()

        # Align all data on common index
        aligned_data = self._align_data_sources(source_results)

        if aligned_data.empty:
            return pd.DataFrame()

        # Apply consensus method
        if self.consensus_method == ConsensusMethod.WEIGHTED_AVERAGE:
            return self._weighted_average_consensus(aligned_data, source_results)
        elif self.consensus_method == ConsensusMethod.MAJORITY:
            return self._majority_consensus(aligned_data, source_results)
        elif self.consensus_method == ConsensusMethod.HIGHEST_QUALITY:
            return self._highest_quality_consensus(aligned_data, source_results)
        elif self.consensus_method == ConsensusMethod.MEDIAN:
            return self._median_consensus(aligned_data, source_results)
        else:
            return self._weighted_average_consensus(aligned_data, source_results)

    def _align_data_sources(self, source_results: List[DataSourceResult]) -> Dict[str, pd.DataFrame]:
        """Align data from multiple sources on common index"""
        # Find common date range
        all_dates = set()
        for result in source_results:
            all_dates.update(result.data.index)

        if not all_dates:
            return {}

        common_dates = sorted(all_dates)

        # Align each source to common dates
        aligned_data = {}
        for i, result in enumerate(source_results):
            source_name = result.adapter.__class__.__name__
            aligned_df = result.data.reindex(common_dates)
            aligned_data[source_name] = aligned_df

        return aligned_data

    def _weighted_average_consensus(self, aligned_data: Dict[str, pd.DataFrame],
                                  source_results: List[DataSourceResult]) -> pd.DataFrame:
        """Create consensus using weighted average"""
        if not aligned_data:
            return pd.DataFrame()

        # Get weights
        weights = {result.adapter.__class__.__name__: result.weight for result in source_results}
        total_weight = sum(weights.values())

        # Normalize weights
        normalized_weights = {k: v / total_weight for k, v in weights.items()}

        # Create consensus DataFrame
        consensus_df = pd.DataFrame(index=aligned_data[list(aligned_data.keys())[0]].index)

        for column in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if column in aligned_data[list(aligned_data.keys())[0]].columns:
                weighted_values = []
                for source_name, df in aligned_data.items():
                    if column in df.columns:
                        weight = normalized_weights[source_name]
                        weighted_values.append(df[column] * weight)

                if weighted_values:
                    consensus_df[column] = sum(weighted_values)

        return consensus_df.dropna()

    def _majority_consensus(self, aligned_data: Dict[str, pd.DataFrame],
                          source_results: List[DataSourceResult]) -> pd.DataFrame:
        """Create consensus using majority vote"""
        if not aligned_data:
            return pd.DataFrame()

        consensus_df = pd.DataFrame(index=aligned_data[list(aligned_data.keys())[0]].index)

        for column in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if column in aligned_data[list(aligned_data.keys())[0]].columns:
                # For each date, find the median value
                column_data = []
                for df in aligned_data.values():
                    if column in df.columns:
                        column_data.append(df[column])

                if column_data:
                    # Use median as majority consensus
                    consensus_df[column] = pd.concat(column_data, axis=1).median(axis=1)

        return consensus_df.dropna()

    def _highest_quality_consensus(self, aligned_data: Dict[str, pd.DataFrame],
                                 source_results: List[DataSourceResult]) -> pd.DataFrame:
        """Create consensus using highest quality source"""
        if not source_results:
            return pd.DataFrame()

        # Find source with highest quality score
        best_source = max(source_results, key=lambda x: x.validation_result.quality_score)
        return best_source.data.copy()

    def _median_consensus(self, aligned_data: Dict[str, pd.DataFrame],
                        source_results: List[DataSourceResult]) -> pd.DataFrame:
        """Create consensus using median values"""
        return self._majority_consensus(aligned_data, source_results)  # Same as majority

    def _calculate_confidence(self, source_results: List[DataSourceResult],
                            consensus_data: pd.DataFrame) -> float:
        """Calculate confidence score for consensus"""
        if not source_results or consensus_data.empty:
            return 0.0

        # Base confidence on number of sources and their quality
        num_sources = len(source_results)
        avg_quality = np.mean([r.validation_result.quality_score for r in source_results])

        # Calculate agreement between sources
        agreement_scores = []
        for result in source_results:
            if not result.data.empty:
                # Calculate correlation with consensus
                common_dates = consensus_data.index.intersection(result.data.index)
                if len(common_dates) > 1:
                    consensus_close = consensus_data.loc[common_dates, 'Close']
                    source_close = result.data.loc[common_dates, 'Close']
                    correlation = consensus_close.corr(source_close)
                    if not np.isnan(correlation):
                        agreement_scores.append(abs(correlation))

        avg_agreement = np.mean(agreement_scores) if agreement_scores else 0.0

        # Combine factors
        confidence = (num_sources / 5.0) * 0.3 + avg_quality * 0.4 + avg_agreement * 0.3
        return min(1.0, max(0.0, confidence))

    def _calculate_source_agreement(self, source_results: List[DataSourceResult],
                                  consensus_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate agreement percentage for each source"""
        agreement = {}

        for result in source_results:
            source_name = result.adapter.__class__.__name__
            if result.data.empty:
                agreement[source_name] = 0.0
                continue

            # Calculate correlation with consensus
            common_dates = consensus_data.index.intersection(result.data.index)
            if len(common_dates) > 1:
                consensus_close = consensus_data.loc[common_dates, 'Close']
                source_close = result.data.loc[common_dates, 'Close']
                correlation = consensus_close.corr(source_close)
                agreement[source_name] = abs(correlation) if not np.isnan(correlation) else 0.0
            else:
                agreement[source_name] = 0.0

        return agreement

    def _detect_anomalies(self, source_results: List[DataSourceResult],
                         consensus_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect anomalies in source data"""
        anomalies = []

        for result in source_results:
            source_name = result.adapter.__class__.__name__
            if result.data.empty:
                continue

            # Check for price deviations
            common_dates = consensus_data.index.intersection(result.data.index)
            if len(common_dates) > 0:
                consensus_close = consensus_data.loc[common_dates, 'Close']
                source_close = result.data.loc[common_dates, 'Close']

                # Calculate percentage deviation
                deviation = abs((source_close - consensus_close) / consensus_close)
                high_deviation = deviation > self.anomaly_threshold

                if high_deviation.any():
                    anomaly_dates = common_dates[high_deviation]
                    for date in anomaly_dates:
                        anomalies.append({
                            'source': source_name,
                            'date': date,
                            'consensus_price': consensus_close[date],
                            'source_price': source_close[date],
                            'deviation_pct': deviation[date] * 100,
                            'type': 'price_deviation'
                        })

        return anomalies

    def _create_fallback_result(self, source_results: List[DataSourceResult]) -> ConsensusResult:
        """Create fallback result when insufficient sources"""
        if source_results:
            best_source = max(source_results, key=lambda x: x.validation_result.quality_score)
            return ConsensusResult(
                consensus_data=best_source.data,
                confidence_score=best_source.validation_result.quality_score * 0.5,  # Lower confidence
                source_agreement={best_source.adapter.__class__.__name__: 1.0},
                anomalies=[],
                metadata={'fallback': True, 'reason': 'insufficient_sources'}
            )
        else:
            return ConsensusResult(
                consensus_data=pd.DataFrame(),
                confidence_score=0.0,
                source_agreement={},
                anomalies=[],
                metadata={'fallback': True, 'reason': 'no_sources'}
            )

    def _create_error_result(self, error_message: str) -> ConsensusResult:
        """Create error result"""
        return ConsensusResult(
            consensus_data=pd.DataFrame(),
            confidence_score=0.0,
            source_agreement={},
            anomalies=[],
            metadata={'error': True, 'message': error_message}
        )
