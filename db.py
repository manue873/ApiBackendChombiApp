# db.py
import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session

# ======================================================
# Configuración DB
# ======================================================
# Usa PostgreSQL por defecto; puedes sobreescribir con CHOMBI_DB_URL
# Ejemplo: postgresql+psycopg2://postgres:1234@localhost:5432/chombi
DB_URL = os.environ.get(
    "CHOMBI_DB_URL",
    "postgresql+psycopg://postgres:1234@localhost:5432/chombi"
)

engine = create_engine(DB_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    # Importa modelos aquí para que Base conozca las clases
    from models import Line, LineShape, Driver, Vehicle, Assignment, Location
    Base.metadata.create_all(bind=engine)
