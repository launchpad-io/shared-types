"""
Demographics Validator
Validation logic for demographic data integrity
"""

from typing import List, Dict, Any, Optional, Set
from decimal import Decimal
from collections import defaultdict

from pydantic import BaseModel, Field

from app.schemas.creator import AudienceDemographicCreate
from app.models.creator import AgeGroup, GenderType
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ValidationResult(BaseModel):
    """Result of validation check"""
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    class Config:
        arbitrary_types_allowed = True


class DemographicsValidator:
    """Validator for demographic data"""
    
    # Tolerance for percentage sum validation
    PERCENTAGE_TOLERANCE = 0.5  # 0.5% tolerance
    
    # Valid enum values
    VALID_AGE_GROUPS = {item.value for item in AgeGroup}
    VALID_GENDERS = {item.value for item in GenderType}
    
    # ISO country code patterns
    COUNTRY_CODE_LENGTH = {2, 3}  # ISO 2 or 3 letter codes
    
    def validate_single_demographic(
        self,
        demographic: AudienceDemographicCreate
    ) -> ValidationResult:
        """
        Validate a single demographic entry
        
        Args:
            demographic: Single demographic entry
            
        Returns:
            Validation result
        """
        result = ValidationResult(is_valid=True)
        
        # Validate age group
        if demographic.age_group not in self.VALID_AGE_GROUPS:
            result.is_valid = False
            result.errors.append(
                f"Invalid age group: {demographic.age_group}. "
                f"Valid options: {', '.join(sorted(self.VALID_AGE_GROUPS))}"
            )
        
        # Validate gender
        if demographic.gender not in self.VALID_GENDERS:
            result.is_valid = False
            result.errors.append(
                f"Invalid gender: {demographic.gender}. "
                f"Valid options: {', '.join(sorted(self.VALID_GENDERS))}"
            )
        
        # Validate percentage
        if demographic.percentage < 0 or demographic.percentage > 100:
            result.is_valid = False
            result.errors.append(
                f"Percentage must be between 0 and 100, got {demographic.percentage}"
            )
        elif demographic.percentage == 0:
            result.warnings.append(
                "Percentage is 0, this demographic will have no impact"
            )
        
        # Validate country code if provided
        if demographic.country:
            if not self._is_valid_country_code(demographic.country):
                result.is_valid = False
                result.errors.append(
                    f"Invalid country code: {demographic.country}. "
                    "Use ISO 2 or 3 letter country codes"
                )
        
        return result
    
    def validate_bulk_demographics(
        self,
        demographics: List[AudienceDemographicCreate]
    ) -> ValidationResult:
        """
        Validate a list of demographics for consistency
        
        Args:
            demographics: List of demographic entries
            
        Returns:
            Validation result
        """
        result = ValidationResult(is_valid=True)
        
        if not demographics:
            result.is_valid = False
            result.errors.append("At least one demographic entry is required")
            return result
        
        # Validate each entry
        for i, demo in enumerate(demographics):
            single_result = self.validate_single_demographic(demo)
            if not single_result.is_valid:
                result.is_valid = False
                for error in single_result.errors:
                    result.errors.append(f"Row {i+1}: {error}")
            result.warnings.extend(single_result.warnings)
        
        # Validate duplicates
        duplicate_check = self._check_duplicates(demographics)
        if duplicate_check:
            result.is_valid = False
            result.errors.extend(duplicate_check)
        
        # Validate percentage sums
        percentage_check = self._validate_percentage_sums(demographics)
        if not percentage_check.is_valid:
            result.is_valid = False
            result.errors.extend(percentage_check.errors)
        result.warnings.extend(percentage_check.warnings)
        
        # Validate completeness
        completeness_check = self._check_completeness(demographics)
        result.warnings.extend(completeness_check)
        
        return result
    
    def _check_duplicates(
        self,
        demographics: List[AudienceDemographicCreate]
    ) -> List[str]:
        """Check for duplicate entries"""
        errors = []
        seen = set()
        
        for i, demo in enumerate(demographics):
            # Create unique key
            key = (demo.age_group, demo.gender, demo.country or 'GLOBAL')
            
            if key in seen:
                errors.append(
                    f"Duplicate entry found at row {i+1}: "
                    f"{demo.age_group}, {demo.gender}, {demo.country or 'Global'}"
                )
            seen.add(key)
        
        return errors
    
    def _validate_percentage_sums(
        self,
        demographics: List[AudienceDemographicCreate]
    ) -> ValidationResult:
        """Validate that percentages sum correctly"""
        result = ValidationResult(is_valid=True)
        
        # Group by country (None = global)
        country_groups = defaultdict(lambda: defaultdict(Decimal))
        
        for demo in demographics:
            country = demo.country or 'GLOBAL'
            country_groups[country][demo.gender] += Decimal(str(demo.percentage))
        
        # Check each country/gender combination
        for country, gender_totals in country_groups.items():
            for gender, total in gender_totals.items():
                # Allow some tolerance for rounding
                if abs(total - Decimal('100')) > Decimal(str(self.PERCENTAGE_TOLERANCE)):
                    country_display = country if country != 'GLOBAL' else 'Global'
                    
                    if total > Decimal('100'):
                        result.is_valid = False
                        result.errors.append(
                            f"{country_display} - {gender}: "
                            f"Percentages sum to {total}%, exceeds 100%"
                        )
                    else:
                        # Under 100% is a warning, not an error
                        result.warnings.append(
                            f"{country_display} - {gender}: "
                            f"Percentages sum to {total}%, should total 100%"
                        )
        
        return result
    
    def _check_completeness(
        self,
        demographics: List[AudienceDemographicCreate]
    ) -> List[str]:
        """Check for missing demographic combinations"""
        warnings = []
        
        # Get all countries in the data
        countries = set(demo.country for demo in demographics if demo.country)
        if any(demo.country is None for demo in demographics):
            countries.add(None)  # Global
        
        # Check each country
        for country in countries:
            country_demos = [d for d in demographics if d.country == country]
            
            # Check if all genders are represented
            genders_present = set(d.gender for d in country_demos)
            missing_genders = set(['male', 'female']) - genders_present
            
            if missing_genders:
                country_display = country or 'Global'
                warnings.append(
                    f"{country_display}: Missing data for {', '.join(missing_genders)}"
                )
            
            # Check if major age groups are represented
            age_groups_present = set(d.age_group for d in country_demos)
            major_age_groups = {'18-24', '25-34', '35-44'}
            missing_age_groups = major_age_groups - age_groups_present
            
            if len(missing_age_groups) == len(major_age_groups):
                country_display = country or 'Global'
                warnings.append(
                    f"{country_display}: No data for major age groups (18-44)"
                )
        
        return warnings
    
    def _is_valid_country_code(self, code: str) -> bool:
        """Check if country code is valid format"""
        if not code:
            return False
        
        # Check length
        if len(code) not in self.COUNTRY_CODE_LENGTH:
            return False
        
        # Check if all uppercase letters
        if not code.isupper() or not code.isalpha():
            return False
        
        return True
    
    def validate_percentage_update(
        self,
        existing_demographics: List[Any],
        new_demographic: AudienceDemographicCreate,
        exclude_id: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate that updating/adding a demographic maintains valid percentages
        
        Args:
            existing_demographics: Current demographics in database
            new_demographic: New or updated demographic
            exclude_id: ID to exclude (for updates)
            
        Returns:
            Validation result
        """
        result = ValidationResult(is_valid=True)
        
        # Calculate new total for the gender/country combination
        total = Decimal(str(new_demographic.percentage))
        
        for demo in existing_demographics:
            # Skip if this is the one being updated
            if exclude_id and str(demo.id) == exclude_id:
                continue
            
            # Only sum matching gender and country
            if (demo.gender == new_demographic.gender and 
                demo.country == new_demographic.country):
                total += Decimal(str(demo.percentage))
        
        # Check if total exceeds 100%
        if total > Decimal('100') + Decimal(str(self.PERCENTAGE_TOLERANCE)):
            country_display = new_demographic.country or 'Global'
            result.is_valid = False
            result.errors.append(
                f"Adding this demographic would cause {new_demographic.gender} "
                f"in {country_display} to exceed 100% (total: {total}%)"
            )
        
        return result