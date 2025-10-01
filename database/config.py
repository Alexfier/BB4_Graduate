import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv(encoding="utf-8")

# Настройка подключения к базе данных SQLite или POSTGRES
DATABASE_URL = os.getenv("DATABASE_POSTGRES")
# DATABASE_URL = os.getenv("DATABASE_SQLite")

engine = create_engine(DATABASE_URL, echo=True)
Session = sessionmaker(bind=engine)
Base = declarative_base()