"""Verify database schema includes new optional task fields."""
from app.database import engine
from sqlalchemy import inspect

inspector = inspect(engine)
columns = inspector.get_columns('tasks')

print("\n✅ Tasks table columns:")
for col in columns:
    print(f"  - {col['name']}: {col['type']}")

# Check for new columns
column_names = [col['name'] for col in columns]
has_is_optional = 'is_optional' in column_names
has_conditions = 'conditions' in column_names

print("\n🔍 New Column Verification:")
print(f"  - is_optional: {'✅ Present' if has_is_optional else '❌ Missing'}")
print(f"  - conditions: {'✅ Present' if has_conditions else '❌ Missing'}")

if has_is_optional and has_conditions:
    print("\n🎉 Phase 1 schema changes successfully applied!")
else:
    print("\n⚠️ Schema update incomplete - columns will be created on next table access")
