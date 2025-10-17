from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Table, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

# Связь многие-ко-многим для задач и тегов
problem_tag_association = Table(
    'problem_tag_association',
    Base.metadata,
    Column('problem_id', Integer, ForeignKey('problems.id')),
    Column('tag_id', Integer, ForeignKey('tags.id'))
)

class Problem(Base):
    __tablename__ = 'problems'
    
    id = Column(Integer, primary_key=True)
    contest_id = Column(Integer, nullable=False)
    index = Column(String(10), nullable=False)
    name = Column(String(500), nullable=False)
    rating = Column(Integer)  # Сложность
    solved_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    tags = relationship("Tag", secondary=problem_tag_association, back_populates="problems")
    
    @property
    def full_code(self):
        return f"{self.contest_id}{self.index}"
    
    @property
    def url(self):
        return f"https://codeforces.com/problemset/problem/{self.contest_id}/{self.index}"

class Tag(Base):
    __tablename__ = 'tags'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    
    # Связи
    problems = relationship("Problem", secondary=problem_tag_association, back_populates="tags")

class Contest(Base):
    __tablename__ = 'contests'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(500), nullable=False)
    type = Column(String(100))
    phase = Column(String(100))
    duration_seconds = Column(Integer)
    start_time = Column(DateTime)