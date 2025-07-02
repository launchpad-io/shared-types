"""
Demographics Constants
Centralized constants for demographics validation and display
"""

from typing import Dict, List, Tuple, Any
from enum import Enum


class DemographicsDefaults:
    """Default values for demographics"""
    PERCENTAGE_TOLERANCE = 0.5  # Allow 0.5% tolerance for sum validation
    MAX_IMPORT_ROWS = 1000  # Maximum rows in a single import
    CACHE_TTL_SECONDS = 300  # 5 minutes cache
    MAX_COMPARISON_CREATORS = 5
    DEFAULT_TOP_COUNTRIES = 10


# Age group definitions with display names and order
AGE_GROUP_CONFIG = [
    {
        "value": "13-17",
        "display": "13-17",
        "order": 1,
        "color": "#F59E0B",  # Amber
        "is_youth": True
    },
    {
        "value": "18-24",
        "display": "18-24",
        "order": 2,
        "color": "#3B82F6",  # Blue
        "is_youth": True
    },
    {
        "value": "25-34",
        "display": "25-34",
        "order": 3,
        "color": "#10B981",  # Green
        "is_youth": False
    },
    {
        "value": "35-44",
        "display": "35-44",
        "order": 4,
        "color": "#8B5CF6",  # Purple
        "is_youth": False
    },
    {
        "value": "45-54",
        "display": "45-54",
        "order": 5,
        "color": "#EF4444",  # Red
        "is_youth": False
    },
    {
        "value": "55+",
        "display": "55+",
        "order": 6,
        "color": "#6B7280",  # Gray
        "is_youth": False
    }
]

# Gender definitions with display names and colors
GENDER_CONFIG = [
    {
        "value": "male",
        "display": "Male",
        "color": "#3B82F6",  # Blue
        "icon": "mars"
    },
    {
        "value": "female",
        "display": "Female",
        "color": "#EC4899",  # Pink
        "icon": "venus"
    },
    {
        "value": "non_binary",
        "display": "Non-Binary",
        "color": "#8B5CF6",  # Purple
        "icon": "genderless"
    },
    {
        "value": "prefer_not_to_say",
        "display": "Prefer Not to Say",
        "color": "#6B7280",  # Gray
        "icon": "question"
    }
]

# Common country codes with full names
COUNTRY_MAPPING = {
    # North America
    "US": "United States",
    "CA": "Canada",
    "MX": "Mexico",
    
    # Europe
    "GB": "United Kingdom",
    "DE": "Germany",
    "FR": "France",
    "IT": "Italy",
    "ES": "Spain",
    "NL": "Netherlands",
    "BE": "Belgium",
    "CH": "Switzerland",
    "AT": "Austria",
    "SE": "Sweden",
    "NO": "Norway",
    "DK": "Denmark",
    "FI": "Finland",
    "IE": "Ireland",
    "PT": "Portugal",
    "PL": "Poland",
    "CZ": "Czech Republic",
    "GR": "Greece",
    "RO": "Romania",
    "HU": "Hungary",
    
    # Asia Pacific
    "JP": "Japan",
    "CN": "China",
    "IN": "India",
    "KR": "South Korea",
    "AU": "Australia",
    "NZ": "New Zealand",
    "SG": "Singapore",
    "MY": "Malaysia",
    "TH": "Thailand",
    "ID": "Indonesia",
    "PH": "Philippines",
    "VN": "Vietnam",
    "HK": "Hong Kong",
    "TW": "Taiwan",
    
    # Middle East
    "AE": "United Arab Emirates",
    "SA": "Saudi Arabia",
    "IL": "Israel",
    "TR": "Turkey",
    
    # Latin America
    "BR": "Brazil",
    "AR": "Argentina",
    "CL": "Chile",
    "CO": "Colombia",
    "PE": "Peru",
    "VE": "Venezuela",
    "EC": "Ecuador",
    "UY": "Uruguay",
    "PY": "Paraguay",
    "BO": "Bolivia",
    
    # Africa
    "ZA": "South Africa",
    "NG": "Nigeria",
    "EG": "Egypt",
    "KE": "Kenya",
    "MA": "Morocco",
    
    # Others
    "RU": "Russia",
    "UA": "Ukraine",
    "PK": "Pakistan",
    "BD": "Bangladesh"
}

# TikTok's primary markets (for validation and suggestions)
TIKTOK_PRIMARY_MARKETS = [
    "US", "GB", "BR", "ID", "MX", "JP", "DE", "FR", 
    "ES", "IT", "CA", "AU", "IN", "KR", "TH", "VN",
    "PH", "MY", "SG", "SA", "AE", "EG", "PK"
]

# Import file column mappings
IMPORT_COLUMN_MAPPINGS = {
    'age_group': [
        'age_group', 'age', 'age_range', 'age group', 
        'age range', 'age_bracket', 'age bracket'
    ],
    'gender': [
        'gender', 'sex', 'gender_type', 'gender type'
    ],
    'percentage': [
        'percentage', 'percent', '%', 'share', 'pct',
        'proportion', 'ratio'
    ],
    'country': [
        'country', 'location', 'country_code', 'country code',
        'geo', 'geography', 'region', 'market'
    ]
}

# Error messages for validation
ERROR_MESSAGES = {
    "invalid_age_group": "Invalid age group. Valid options: {options}",
    "invalid_gender": "Invalid gender. Valid options: {options}",
    "invalid_percentage": "Percentage must be between 0 and 100",
    "invalid_country": "Invalid country code. Use ISO 2 or 3 letter codes",
    "percentage_exceeds": "{location} - {gender}: Percentages sum to {total}%, exceeds 100%",
    "percentage_under": "{location} - {gender}: Percentages sum to {total}%, should total 100%",
    "duplicate_entry": "Duplicate entry found: {details}",
    "missing_required": "Missing required column: {column}",
    "file_too_large": "File contains too many rows. Maximum allowed: {max_rows}",
    "invalid_file_format": "Invalid file format. Supported formats: {formats}"
}

# Success messages
SUCCESS_MESSAGES = {
    "import_complete": "Successfully imported {count} demographic entries",
    "validation_passed": "All demographics data is valid",
    "update_complete": "Demographics updated successfully",
    "export_complete": "Demographics exported successfully"
}


# Helper functions
def get_age_group_display(value: str) -> str:
    """Get display name for age group"""
    config = next((c for c in AGE_GROUP_CONFIG if c["value"] == value), None)
    return config["display"] if config else value


def get_gender_display(value: str) -> str:
    """Get display name for gender"""
    config = next((c for c in GENDER_CONFIG if c["value"] == value), None)
    return config["display"] if config else value.title()


def get_country_name(code: str) -> str:
    """Get country name from code"""
    return COUNTRY_MAPPING.get(code, code)


def get_age_group_color(value: str) -> str:
    """Get color for age group"""
    config = next((c for c in AGE_GROUP_CONFIG if c["value"] == value), None)
    return config["color"] if config else "#6B7280"


def get_gender_color(value: str) -> str:
    """Get color for gender"""
    config = next((c for c in GENDER_CONFIG if c["value"] == value), None)
    return config["color"] if config else "#6B7280"


def is_youth_age_group(value: str) -> bool:
    """Check if age group is considered youth"""
    config = next((c for c in AGE_GROUP_CONFIG if c["value"] == value), None)
    return config["is_youth"] if config else False


def get_valid_age_groups() -> List[str]:
    """Get list of valid age group values"""
    return [config["value"] for config in AGE_GROUP_CONFIG]


def get_valid_genders() -> List[str]:
    """Get list of valid gender values"""
    return [config["value"] for config in GENDER_CONFIG]


def format_percentage(value: float) -> str:
    """Format percentage for display"""
    return f"{value:.1f}%"


def validate_country_code(code: str) -> bool:
    """Validate if country code is in correct format"""
    if not code:
        return False
    
    # Check length (ISO 2 or 3)
    if len(code) not in [2, 3]:
        return False
    
    # Check if uppercase letters
    if not code.isupper() or not code.isalpha():
        return False
    
    return True


# Export lists for use in other modules
VALID_AGE_GROUPS = get_valid_age_groups()
VALID_GENDERS = get_valid_genders()


# Analytics aggregation helpers
def calculate_youth_percentage(age_distribution: Dict[str, float]) -> float:
    """Calculate total youth percentage from age distribution"""
    youth_total = 0.0
    for config in AGE_GROUP_CONFIG:
        if config["is_youth"] and config["value"] in age_distribution:
            youth_total += age_distribution[config["value"]]
    return youth_total


def get_primary_demographic(demographics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Find the primary (largest) demographic segment"""
    if not demographics:
        return {}
    
    primary = max(demographics, key=lambda d: d.get("percentage", 0))
    return {
        "age_group": primary.get("age_group"),
        "gender": primary.get("gender"),
        "percentage": primary.get("percentage"),
        "display": f"{get_gender_display(primary.get('gender', ''))} {primary.get('age_group', '')}"
    }