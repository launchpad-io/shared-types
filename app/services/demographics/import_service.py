"""
Demographics Import Service
Handles CSV and Excel file imports for bulk demographics updates
"""

import csv
import io
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from decimal import Decimal

import pandas as pd
from pydantic import ValidationError

from app.schemas.creator import AudienceDemographicCreate
from app.models.creator import AgeGroup, GenderType
from app.services.demographics.validator import DemographicsValidator
from app.utils.logging import get_logger
from app.core.exceptions import ValidationException, BusinessLogicException

logger = get_logger(__name__)


class DemographicsImportService:
    """Service for importing demographics from CSV/Excel files"""
    
    SUPPORTED_FORMATS = {'.csv', '.xlsx', '.xls'}
    
    # Column mappings for flexibility
    COLUMN_MAPPINGS = {
        'age_group': ['age_group', 'age', 'age_range', 'age group'],
        'gender': ['gender', 'sex', 'gender_type'],
        'percentage': ['percentage', 'percent', '%', 'share'],
        'country': ['country', 'location', 'country_code', 'geo']
    }
    
    def __init__(self):
        self.validator = DemographicsValidator()
    
    async def import_from_file(
        self,
        file_content: bytes,
        filename: str,
        file_type: Optional[str] = None
    ) -> Tuple[List[AudienceDemographicCreate], List[Dict[str, Any]]]:
        """
        Import demographics from file
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            file_type: MIME type (optional)
            
        Returns:
            Tuple of (valid demographics, errors list)
            
        Raises:
            ValidationException: If file format is invalid
        """
        # Determine file type
        file_ext = self._get_file_extension(filename)
        if file_ext not in self.SUPPORTED_FORMATS:
            raise ValidationException(
                f"Unsupported file format. Supported: {', '.join(self.SUPPORTED_FORMATS)}"
            )
        
        try:
            if file_ext == '.csv':
                return await self._import_csv(file_content)
            else:
                return await self._import_excel(file_content)
        except Exception as e:
            logger.error(f"Error importing file: {str(e)}")
            raise BusinessLogicException(f"Failed to import file: {str(e)}")
    
    async def _import_csv(
        self,
        file_content: bytes
    ) -> Tuple[List[AudienceDemographicCreate], List[Dict[str, Any]]]:
        """Import from CSV file"""
        valid_demographics = []
        errors = []
        
        try:
            # Decode and parse CSV
            text_content = file_content.decode('utf-8-sig')  # Handle BOM
            reader = csv.DictReader(io.StringIO(text_content))
            
            # Normalize column names
            if reader.fieldnames:
                normalized_fieldnames = [self._normalize_column_name(f) for f in reader.fieldnames]
                reader.fieldnames = normalized_fieldnames
            
            # Map columns
            column_map = self._detect_columns(reader.fieldnames or [])
            if not self._validate_required_columns(column_map):
                raise ValidationException(
                    "Missing required columns. Required: age_group, gender, percentage"
                )
            
            # Process rows
            for row_num, row in enumerate(reader, start=2):  # Start from 2 (header is 1)
                try:
                    demographic = self._parse_row(row, column_map)
                    valid_demographics.append(demographic)
                except ValidationError as e:
                    errors.append({
                        "row": row_num,
                        "data": row,
                        "errors": e.errors()
                    })
                except Exception as e:
                    errors.append({
                        "row": row_num,
                        "data": row,
                        "errors": [{"msg": str(e)}]
                    })
            
            return valid_demographics, errors
            
        except UnicodeDecodeError:
            raise ValidationException("File encoding not supported. Please use UTF-8")
    
    async def _import_excel(
        self,
        file_content: bytes
    ) -> Tuple[List[AudienceDemographicCreate], List[Dict[str, Any]]]:
        """Import from Excel file"""
        valid_demographics = []
        errors = []
        
        try:
            # Read Excel file
            df = pd.read_excel(io.BytesIO(file_content), engine='openpyxl')
            
            # Normalize column names
            df.columns = [self._normalize_column_name(col) for col in df.columns]
            
            # Map columns
            column_map = self._detect_columns(df.columns.tolist())
            if not self._validate_required_columns(column_map):
                raise ValidationException(
                    "Missing required columns. Required: age_group, gender, percentage"
                )
            
            # Process rows
            for idx, row in df.iterrows():
                row_num = idx + 2  # Excel rows start from 1, header is 1
                try:
                    row_dict = row.to_dict()
                    demographic = self._parse_row(row_dict, column_map)
                    valid_demographics.append(demographic)
                except ValidationError as e:
                    errors.append({
                        "row": row_num,
                        "data": row_dict,
                        "errors": e.errors()
                    })
                except Exception as e:
                    errors.append({
                        "row": row_num,
                        "data": row_dict,
                        "errors": [{"msg": str(e)}]
                    })
            
            return valid_demographics, errors
            
        except Exception as e:
            raise BusinessLogicException(f"Failed to read Excel file: {str(e)}")
    
    def _parse_row(
        self,
        row: Dict[str, Any],
        column_map: Dict[str, str]
    ) -> AudienceDemographicCreate:
        """Parse a single row into demographic data"""
        # Extract values using column mapping
        age_group_raw = str(row.get(column_map['age_group'], '')).strip()
        gender_raw = str(row.get(column_map['gender'], '')).strip().lower()
        percentage_raw = row.get(column_map['percentage'])
        country_raw = row.get(column_map.get('country', ''))
        
        # Normalize age group
        age_group = self._normalize_age_group(age_group_raw)
        if not age_group:
            raise ValueError(f"Invalid age group: {age_group_raw}")
        
        # Normalize gender
        gender = self._normalize_gender(gender_raw)
        if not gender:
            raise ValueError(f"Invalid gender: {gender_raw}")
        
        # Parse percentage
        percentage = self._parse_percentage(percentage_raw)
        if percentage is None or percentage < 0 or percentage > 100:
            raise ValueError(f"Invalid percentage: {percentage_raw}")
        
        # Normalize country
        country = None
        if country_raw and str(country_raw).strip():
            country = str(country_raw).strip().upper()
            if len(country) not in [2, 3]:  # ISO country codes
                country = self._map_country_name_to_code(country)
        
        return AudienceDemographicCreate(
            age_group=age_group,
            gender=gender,
            percentage=percentage,
            country=country
        )
    
    def _normalize_age_group(self, value: str) -> Optional[str]:
        """Normalize age group value to enum"""
        value = value.lower().replace(' ', '').replace('_', '-')
        
        # Direct mappings
        mappings = {
            '13-17': AgeGroup.AGE_13_17,
            '18-24': AgeGroup.AGE_18_24,
            '25-34': AgeGroup.AGE_25_34,
            '35-44': AgeGroup.AGE_35_44,
            '45-54': AgeGroup.AGE_45_54,
            '55+': AgeGroup.AGE_55_PLUS,
            '55plus': AgeGroup.AGE_55_PLUS,
            '55andabove': AgeGroup.AGE_55_PLUS,
            'over55': AgeGroup.AGE_55_PLUS
        }
        
        return mappings.get(value)
    
    def _normalize_gender(self, value: str) -> Optional[str]:
        """Normalize gender value to enum"""
        value = value.lower().strip()
        
        mappings = {
            'male': GenderType.male,
            'm': GenderType.male,
            'men': GenderType.male,
            'female': GenderType.female,
            'f': GenderType.female,
            'women': GenderType.female,
            'non_binary': GenderType.non_binary,
            'non-binary': GenderType.non_binary,
            'nonbinary': GenderType.non_binary,
            'nb': GenderType.non_binary,
            'other': GenderType.non_binary,
            'prefer_not_to_say': GenderType.prefer_not_to_say,
            'prefer not to say': GenderType.prefer_not_to_say,
            'not specified': GenderType.prefer_not_to_say
        }
        
        return mappings.get(value)
    
    def _parse_percentage(self, value: Any) -> Optional[float]:
        """Parse percentage value"""
        if value is None or str(value).strip() == '':
            return None
        
        try:
            # Handle string percentages
            if isinstance(value, str):
                value = value.strip().replace('%', '').replace(',', '.')
            
            percentage = float(value)
            
            # If value is > 1, assume it's already a percentage
            # If <= 1, assume it's a decimal and convert
            if percentage <= 1:
                percentage *= 100
            
            return round(percentage, 2)
            
        except (ValueError, TypeError):
            return None
    
    def _map_country_name_to_code(self, country_name: str) -> Optional[str]:
        """Map country names to ISO codes"""
        # Common mappings (extend as needed)
        country_mappings = {
            'united states': 'US',
            'usa': 'US',
            'america': 'US',
            'united kingdom': 'GB',
            'uk': 'GB',
            'england': 'GB',
            'canada': 'CA',
            'australia': 'AU',
            'germany': 'DE',
            'france': 'FR',
            'japan': 'JP',
            'china': 'CN',
            'india': 'IN',
            'brazil': 'BR',
            'mexico': 'MX'
        }
        
        return country_mappings.get(country_name.lower(), country_name[:2].upper())
    
    def _detect_columns(self, headers: List[str]) -> Dict[str, str]:
        """Detect which columns map to required fields"""
        column_map = {}
        normalized_headers = [h.lower().strip() for h in headers]
        
        for field, variations in self.COLUMN_MAPPINGS.items():
            for header_idx, header in enumerate(normalized_headers):
                if header in variations:
                    column_map[field] = headers[header_idx]
                    break
        
        return column_map
    
    def _validate_required_columns(self, column_map: Dict[str, str]) -> bool:
        """Check if all required columns are mapped"""
        required = {'age_group', 'gender', 'percentage'}
        return all(field in column_map for field in required)
    
    def _normalize_column_name(self, name: str) -> str:
        """Normalize column name"""
        return name.lower().strip().replace('_', ' ')
    
    def _get_file_extension(self, filename: str) -> str:
        """Get file extension"""
        return '.' + filename.lower().split('.')[-1]
    
    def generate_template(self, format: str = 'csv') -> bytes:
        """
        Generate a template file for demographics import
        
        Args:
            format: 'csv' or 'xlsx'
            
        Returns:
            File content as bytes
        """
        # Sample data
        sample_data = [
            {
                'age_group': '18-24',
                'gender': 'female',
                'percentage': 45.5,
                'country': 'US'
            },
            {
                'age_group': '18-24',
                'gender': 'male',
                'percentage': 25.3,
                'country': 'US'
            },
            {
                'age_group': '25-34',
                'gender': 'female',
                'percentage': 20.2,
                'country': 'US'
            },
            {
                'age_group': '25-34',
                'gender': 'male',
                'percentage': 9.0,
                'country': 'US'
            }
        ]
        
        if format == 'csv':
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=['age_group', 'gender', 'percentage', 'country'])
            writer.writeheader()
            writer.writerows(sample_data)
            return output.getvalue().encode('utf-8')
        
        elif format == 'xlsx':
            df = pd.DataFrame(sample_data)
            output = io.BytesIO()
            df.to_excel(output, index=False, engine='openpyxl')
            return output.getvalue()
        
        else:
            raise ValueError(f"Unsupported format: {format}")