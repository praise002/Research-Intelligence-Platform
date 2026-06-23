"""
Postgres index naming convention — applied to every SQLModel table's metadata
so generated index/constraint names are predictable and consistent in
Alembic migrations, instead of SQLAlchemy's default auto-generated hashes.

USAGE:
    All models inherit metadata from this shared object rather than
    letting SQLModel create its own default MetaData per file.

    from src.db.db_naming import metadata
    from sqlmodel import SQLModel

    SQLModel.metadata = metadata
"""

from sqlalchemy import MetaData

POSTGRES_INDEXES_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}

metadata = MetaData(naming_convention=POSTGRES_INDEXES_NAMING_CONVENTION)