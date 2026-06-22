"""Test helpers for creating SQLite-compatible tables from SQLAlchemy models.

SQLite doesn't support PostgreSQL-specific column types like ARRAY and Vector.
This module provides a safe way to create model tables on SQLite by adapting
those column types to Text during table creation, then restoring them after.
"""

from sqlalchemy import Text as SAText
from sqlalchemy.types import ARRAY


def create_table_safe(model_cls, engine):
    """Create a model's table on SQLite, replacing PG-specific types with Text.

    This temporarily swaps ARRAY and Vector columns to Text, creates the table,
    and restores the original types on the model.  Safe to call from test
    modules that need tables with PG-only column types.
    """
    table = model_cls.__table__
    replacements = {}

    for col in table.columns:
        coltype = col.type
        # Detect types that SQLite can't render
        if isinstance(coltype, ARRAY) or type(coltype).__name__ == "Vector":
            replacements[col.name] = coltype
            col.type = SAText()

    table.create(bind=engine, checkfirst=True)

    # Restore original types so the model isn't corrupted for other uses
    for name, orig in replacements.items():
        table.columns[name].type = orig
