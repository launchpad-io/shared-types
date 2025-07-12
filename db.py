#!/usr/bin/env python3
"""
Fix the datetime issue in demographics
"""

from pathlib import Path
from colorama import Fore, init
import asyncio
import asyncpg

init(autoreset=True)

def fix_schema():
    """Fix the DemographicsResponse schema to handle nullable datetime"""
    
    schema_path = Path(r"D:\ByteCraftSoft\Projects\13 - Launchpad.ai\Main\backend\shared-types\app\schemas\demographics.py")
    
    print(f"{Fore.CYAN}=== Fixing DemographicsResponse Schema ===")
    
    if not schema_path.exists():
        print(f"{Fore.RED}Schema file not found!")
        return
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find DemographicsResponse class
    if 'class DemographicsResponse' in content:
        print(f"{Fore.YELLOW}Found DemographicsResponse class")
        
        # Check if updated_at is Optional
        if 'updated_at: datetime' in content and 'Optional[datetime]' not in content:
            print(f"{Fore.RED}updated_at is not marked as Optional!")
            print(f"\n{Fore.YELLOW}Fix: Change")
            print(f"{Fore.WHITE}    updated_at: datetime")
            print(f"{Fore.YELLOW}To:")
            print(f"{Fore.WHITE}    updated_at: Optional[datetime]")
            
            # Create fixed version
            fixed_content = content.replace(
                'updated_at: datetime',
                'updated_at: Optional[datetime]'
            )
            
            # Make sure Optional is imported
            if 'from typing import' in fixed_content and 'Optional' not in fixed_content:
                fixed_content = fixed_content.replace(
                    'from typing import',
                    'from typing import Optional,'
                )
            
            # Save fixed version
            with open('demographics_schema_fixed.py', 'w', encoding='utf-8') as f:
                f.write(fixed_content)
                
            print(f"\n{Fore.GREEN}Created fixed schema: demographics_schema_fixed.py")
            print(f"{Fore.YELLOW}Copy this to your schemas directory")
        else:
            print(f"{Fore.GREEN}updated_at is already Optional or not found")
    else:
        print(f"{Fore.RED}DemographicsResponse class not found!")

async def fix_database_nulls():
    """Update NULL updated_at values in database"""
    
    DB_URL = "postgresql://postgres:admin@localhost:5432/crm_campaigns_db"
    
    print(f"\n{Fore.CYAN}=== Fixing NULL updated_at values ===")
    
    try:
        conn = await asyncpg.connect(DB_URL)
        
        # Check for NULL values
        count = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM users.creator_audience_demographics 
            WHERE updated_at IS NULL
        """)
        
        if count > 0:
            print(f"{Fore.YELLOW}Found {count} records with NULL updated_at")
            
            # Update them
            await conn.execute("""
                UPDATE users.creator_audience_demographics 
                SET updated_at = CURRENT_TIMESTAMP 
                WHERE updated_at IS NULL
            """)
            
            print(f"{Fore.GREEN}✓ Updated all NULL values to current timestamp")
        else:
            print(f"{Fore.GREEN}No NULL updated_at values found")
            
        await conn.close()
        
    except Exception as e:
        print(f"{Fore.RED}Database error: {e}")

def create_complete_fix():
    """Create a complete fixed schema file"""
    
    fixed_schema = '''from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
import uuid
from enum import Enum


class AgeGroup(str, Enum):
    """Age group enum"""
    AGE_13_17 = "13-17"
    AGE_18_24 = "18-24"
    AGE_25_34 = "25-34"
    AGE_35_44 = "35-44"
    AGE_45_54 = "45-54"
    AGE_55_PLUS = "55+"


class Gender(str, Enum):
    """Gender enum"""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    NOT_SPECIFIED = "not_specified"


class DemographicsBase(BaseModel):
    """Base demographics schema"""
    age_group: AgeGroup
    gender: Gender
    percentage: Decimal = Field(..., ge=0, le=100)
    country: Optional[str] = Field(None, max_length=100)

    @field_validator('percentage', mode='before')
    @classmethod
    def round_percentage(cls, v):
        if v is not None:
            return round(Decimal(str(v)), 2)
        return v

    @field_validator('country')
    @classmethod
    def clean_country(cls, v):
        if v is not None and v.strip() == '':
            return None
        return v

    model_config = ConfigDict(
        json_encoders={
            Decimal: lambda v: float(v)
        }
    )


class DemographicsCreate(DemographicsBase):
    """Schema for creating demographics - no creator_id needed"""
    pass


class DemographicsUpdate(BaseModel):
    """Schema for updating demographics"""
    age_group: Optional[AgeGroup] = None
    gender: Optional[Gender] = None
    percentage: Optional[Decimal] = Field(None, ge=0, le=100)
    country: Optional[str] = Field(None, max_length=100)

    @field_validator('percentage', mode='before')
    @classmethod
    def round_percentage(cls, v):
        if v is not None:
            return round(Decimal(str(v)), 2)
        return v

    model_config = ConfigDict(
        json_encoders={
            Decimal: lambda v: float(v)
        }
    )


class DemographicsResponse(DemographicsBase):
    """Response schema for demographics"""
    id: uuid.UUID
    creator_id: uuid.UUID
    updated_at: Optional[datetime]  # Make this Optional to handle NULL values

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat() if v else None,
            uuid.UUID: lambda v: str(v)
        }
    )
'''
    
    with open('demographics_schema_complete.py', 'w', encoding='utf-8') as f:
        f.write(fixed_schema)
    
    print(f"\n{Fore.GREEN}Created complete fixed schema: demographics_schema_complete.py")

def quick_fix_instructions():
    """Show quick fix instructions"""
    
    print(f"\n{Fore.CYAN}=== Quick Fix Instructions ===")
    
    print(f"\n{Fore.YELLOW}Option 1 - Fix Schema (Recommended):")
    print(f"1. Open app/schemas/demographics.py")
    print(f"2. Find DemographicsResponse class")
    print(f"3. Change: updated_at: datetime")
    print(f"4. To: updated_at: Optional[datetime]")
    print(f"5. Save and let server reload")
    
    print(f"\n{Fore.YELLOW}Option 2 - Update Database:")
    print(f"Run this SQL to fix NULL values:")
    print(f"{Fore.WHITE}UPDATE users.creator_audience_demographics")
    print(f"SET updated_at = CURRENT_TIMESTAMP")
    print(f"WHERE updated_at IS NULL;")
    
    print(f"\n{Fore.YELLOW}Option 3 - Use the complete fixed schema:")
    print(f"Copy demographics_schema_complete.py to app/schemas/demographics.py")

async def main():
    print(f"{Fore.MAGENTA}{'*' * 60}")
    print(f"{Fore.MAGENTA}DateTime Fix Tool")
    print(f"{Fore.MAGENTA}{'*' * 60}\n")
    
    # Fix schema
    fix_schema()
    
    # Create complete fix
    create_complete_fix()
    
    # Fix database
    await fix_database_nulls()
    
    # Show instructions
    quick_fix_instructions()
    
    print(f"\n{Fore.GREEN}After fixing, your GET endpoint should work!")
    print(f"{Fore.YELLOW}The server should auto-reload if you're using --reload")

if __name__ == "__main__":
    asyncio.run(main())