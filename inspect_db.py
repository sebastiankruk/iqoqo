import os
from sqlalchemy import create_engine, inspect

database_url = os.environ.get("DATABASE_URL", "postgresql://sebastiankruk@localhost/iqoqo")
engine = create_engine(database_url)
inspector = inspect(engine)

print("Columns for inventory.llm_telemetry:")
for column in inspector.get_columns("llm_telemetry", schema="inventory"):
    print(f"  {column['name']}: {column['type']} (Nullable: {column['nullable']}, Default: {column['default']})")
