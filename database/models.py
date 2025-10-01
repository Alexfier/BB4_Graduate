from database.config import Base, engine
from sqlalchemy import  Column, Integer, String


# Модель для таблицы last_fetched
class LastFetched(Base):
    __tablename__ = 'last_fetched'
    id = Column(Integer, primary_key=True, autoincrement=True)
    last_contest_id = Column(Integer)
    last_index = Column(String)


# Модель для таблицы problems
class Problem(Base):
    __tablename__ = 'problems'
    id = Column(Integer, primary_key=True, autoincrement=True)
    contest_id = Column(Integer)
    index = Column(String)
    name = Column(String)
    rating = Column(Integer)
    solved_count = Column(Integer)
    tags = Column(String)
    link = Column(String)

