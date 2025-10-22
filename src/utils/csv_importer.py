"""
CSV Import System for Gr8 Agent
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging
import re
from io import StringIO

logger = logging.getLogger(__name__)

class CSVImporter:
    """Advanced CSV importer with auto-mapping and validation"""
    
    def __init__(self):
        self.supported_formats = ['.csv', '.tsv']
        self.column_mappings = {
            'symbol': ['symbol', 'ticker', 'instrument', 'pair', 'asset'],
            'trade_type': ['type', 'side', 'direction', 'trade_type', 'position'],
            'entry_price': ['entry_price', 'entry', 'open_price', 'open', 'price'],
            'exit_price': ['exit_price', 'exit', 'close_price', 'close', 'sell_price'],
            'position_size': ['size', 'quantity', 'shares', 'amount', 'volume', 'units'],
            'entry_time': ['entry_time', 'entry_date', 'open_time', 'date', 'timestamp'],
            'exit_time': ['exit_time', 'exit_date', 'close_time', 'close_date'],
            'fees': ['fees', 'commission', 'cost', 'spread'],
            'notes': ['notes', 'comment', 'description', 'memo']
        }
        
        # Common trade type mappings
        self.trade_type_mappings = {
            'long': ['long', 'buy', 'b', 'l', '1'],
            'short': ['short', 'sell', 's', 'sh', '-1']
        }
    
    def import_trades(self, file_path: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Import trades from CSV file
        
        Args:
            file_path: Path to CSV file
            user_id: User ID for audit trail
        
        Returns:
            Import result with trades and errors
        """
        try:
            # Read CSV file
            df = self._read_csv_file(file_path)
            
            if df.empty:
                return {
                    'success': False,
                    'error': 'CSV file is empty'
                }
            
            # Auto-detect column mapping
            mapping = self._detect_columns(df.columns)
            
            # Validate and clean data
            validated_trades = []
            errors = []
            
            for index, row in df.iterrows():
                try:
                    trade_data = self._map_row_to_trade(row, mapping)
                    validation_result = self._validate_trade_data(trade_data)
                    
                    if validation_result['is_valid']:
                        # Add metadata
                        trade_data['user_id'] = user_id
                        trade_data['imported_at'] = datetime.now().isoformat()
                        validated_trades.append(trade_data)
                    else:
                        errors.append({
                            'row': index + 1,
                            'errors': validation_result['errors'],
                            'data': trade_data
                        })
                        
                except Exception as e:
                    errors.append({
                        'row': index + 1,
                        'error': str(e),
                        'data': dict(row)
                    })
            
            return {
                'success': True,
                'imported_count': len(validated_trades),
                'error_count': len(errors),
                'trades': validated_trades,
                'errors': errors,
                'mapping': mapping,
                'total_rows': len(df)
            }
            
        except Exception as e:
            logger.error(f"Error importing CSV: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _read_csv_file(self, file_path: str) -> pd.DataFrame:
        """Read CSV file with multiple format support"""
        try:
            # Try different separators
            separators = [',', ';', '\t', '|']
            
            for sep in separators:
                try:
                    df = pd.read_csv(file_path, sep=sep, encoding='utf-8')
                    if len(df.columns) > 1:  # Valid CSV with multiple columns
                        return df
                except:
                    continue
            
            # Try with different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    if len(df.columns) > 1:
                        return df
                except:
                    continue
            
            raise ValueError("Could not read CSV file with any supported format")
            
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            return pd.DataFrame()
    
    def _detect_columns(self, columns: List[str]) -> Dict[str, str]:
        """Auto-detect column mapping"""
        mapping = {}
        columns_lower = [col.lower().strip() for col in columns]
        
        for field, possible_names in self.column_mappings.items():
            for col_name in columns_lower:
                for possible_name in possible_names:
                    if possible_name in col_name or col_name in possible_name:
                        # Find original column name
                        original_col = columns[columns_lower.index(col_name)]
                        mapping[field] = original_col
                        break
                if field in mapping:
                    break
        
        return mapping
    
    def _map_row_to_trade(self, row: pd.Series, mapping: Dict[str, str]) -> Dict[str, Any]:
        """Map CSV row to trade data"""
        trade_data = {}
        
        # Map basic fields
        for field, csv_column in mapping.items():
            if csv_column in row and pd.notna(row[csv_column]):
                value = row[csv_column]
                
                # Clean and convert values
                if field == 'trade_type':
                    trade_data[field] = self._normalize_trade_type(str(value).lower().strip())
                elif field in ['entry_price', 'exit_price', 'position_size', 'fees']:
                    trade_data[field] = self._convert_to_float(value)
                elif field in ['entry_time', 'exit_time']:
                    trade_data[field] = self._convert_to_datetime(value)
                else:
                    trade_data[field] = str(value).strip()
        
        # Set defaults
        trade_data.setdefault('status', 'open')
        trade_data.setdefault('fees', 0.0)
        
        # Generate ID if not present
        if 'id' not in trade_data:
            trade_data['id'] = f"trade_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(str(row)) % 10000}"
        
        return trade_data
    
    def _normalize_trade_type(self, value: str) -> str:
        """Normalize trade type to standard format"""
        value = value.lower().strip()
        
        for standard_type, variations in self.trade_type_mappings.items():
            if value in variations:
                return standard_type
        
        # Default to long if unclear
        return 'long'
    
    def _convert_to_float(self, value: Any) -> float:
        """Convert value to float"""
        try:
            if pd.isna(value):
                return 0.0
            
            # Remove common currency symbols and formatting
            if isinstance(value, str):
                value = re.sub(r'[^\d.-]', '', value)
            
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def _convert_to_datetime(self, value: Any) -> str:
        """Convert value to ISO datetime string"""
        try:
            if pd.isna(value):
                return datetime.now().isoformat()
            
            if isinstance(value, str):
                # Try common date formats
                date_formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d',
                    '%m/%d/%Y %H:%M:%S',
                    '%m/%d/%Y',
                    '%d/%m/%Y %H:%M:%S',
                    '%d/%m/%Y',
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%dT%H:%M:%SZ'
                ]
                
                for fmt in date_formats:
                    try:
                        dt = datetime.strptime(value, fmt)
                        return dt.isoformat()
                    except ValueError:
                        continue
                
                # Try pandas parsing
                dt = pd.to_datetime(value)
                return dt.isoformat()
            
            elif isinstance(value, datetime):
                return value.isoformat()
            
            return datetime.now().isoformat()
            
        except Exception as e:
            logger.warning(f"Could not parse datetime '{value}': {e}")
            return datetime.now().isoformat()
    
    def _validate_trade_data(self, trade_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate trade data"""
        errors = []
        
        # Required fields
        required_fields = ['symbol', 'trade_type', 'entry_price', 'position_size']
        for field in required_fields:
            if field not in trade_data or trade_data[field] is None:
                errors.append(f"Missing required field: {field}")
        
        # Validate trade type
        if 'trade_type' in trade_data:
            if trade_data['trade_type'] not in ['long', 'short']:
                errors.append("Invalid trade type. Must be 'long' or 'short'")
        
        # Validate prices
        for price_field in ['entry_price', 'exit_price']:
            if price_field in trade_data and trade_data[price_field] is not None:
                if not isinstance(trade_data[price_field], (int, float)) or trade_data[price_field] <= 0:
                    errors.append(f"Invalid {price_field}. Must be a positive number")
        
        # Validate position size
        if 'position_size' in trade_data:
            if not isinstance(trade_data['position_size'], (int, float)) or trade_data['position_size'] <= 0:
                errors.append("Invalid position size. Must be a positive number")
        
        # Validate fees
        if 'fees' in trade_data and trade_data['fees'] is not None:
            if not isinstance(trade_data['fees'], (int, float)) or trade_data['fees'] < 0:
                errors.append("Invalid fees. Must be a non-negative number")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    def get_sample_csv(self) -> str:
        """Generate sample CSV content"""
        sample_data = [
            ['symbol', 'trade_type', 'entry_price', 'exit_price', 'position_size', 'entry_time', 'fees', 'notes'],
            ['AAPL', 'long', '150.00', '155.00', '100', '2024-01-15 09:30:00', '1.50', 'Good trade'],
            ['GOOGL', 'short', '2800.00', '2750.00', '10', '2024-01-16 10:15:00', '2.00', 'Short position'],
            ['MSFT', 'long', '400.00', None, '50', '2024-01-17 11:00:00', '1.00', 'Open position']
        ]
        
        output = StringIO()
        for row in sample_data:
            output.write(','.join(str(cell) for cell in row) + '\n')
        
        return output.getvalue()
    
    def validate_csv_structure(self, file_path: str) -> Dict[str, Any]:
        """Validate CSV file structure before import"""
        try:
            df = self._read_csv_file(file_path)
            
            if df.empty:
                return {
                    'valid': False,
                    'error': 'File is empty'
                }
            
            # Detect columns
            mapping = self._detect_columns(df.columns)
            
            # Check for required fields
            required_fields = ['symbol', 'trade_type', 'entry_price', 'position_size']
            missing_fields = [field for field in required_fields if field not in mapping]
            
            return {
                'valid': len(missing_fields) == 0,
                'columns': list(df.columns),
                'mapping': mapping,
                'missing_fields': missing_fields,
                'row_count': len(df),
                'sample_data': df.head(3).to_dict('records') if not df.empty else []
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e)
            }
