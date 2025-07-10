# check_model_enum.py
"""
Check how SQLAlchemy sees the enum
"""

import sys
sys.path.insert(0, '.')

from sqlalchemy import inspect
from app.db.base_class import Base
from app.models.user import User, UserRole

print("=== Python Model Check ===")
print(f"\nUserRole enum values in Python:")
for role in UserRole:
    print(f"  {role.name} = '{role.value}'")

print(f"\nSQLAlchemy Column Type:")
role_column = User.__table__.columns['role']
print(f"  Type: {role_column.type}")

# Check if it's an Enum type
if hasattr(role_column.type, 'enums'):
    print(f"  Enum values: {role_column.type.enums}")

# Check the enum name
if hasattr(role_column.type, 'name'):
    print(f"  Enum name: {role_column.type.name}")
    
if hasattr(role_column.type, 'schema'):
    print(f"  Schema: {role_column.type.schema}")