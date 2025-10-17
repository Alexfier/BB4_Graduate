from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy.exc import SQLAlchemyError
from models import Base, Problem, Tag, Contest
from codeforces_api import CodeforcesAPI
import logging
from typing import List, Tuple, Optional
from config import DATABASE_URL
import asyncio

class DatabaseManager:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.Session = sessionmaker(bind=self.engine)
        
    def init_db(self):
        """Инициализация базы данных"""
        Base.metadata.create_all(self.engine)
        
    async def update_problems(self):
        """Обновление данных о задачах"""
        async with CodeforcesAPI() as api:
            data = await api.get_problems()
            
            if not data:
                logging.error("Failed to fetch problems from API")
                return
                
            problems_data = data.get('problems', [])
            problem_statistics = data.get('problemStatistics', [])
            
            session = self.Session()
            try:
                # Создаем словарь статистики для быстрого доступа
                stats_dict = {}
                for stat in problem_statistics:
                    key = (stat.get('contestId'), stat.get('index'))
                    stats_dict[key] = stat.get('solvedCount', 0)
                
                # Обрабатываем задачи
                for problem_data in problems_data:
                    contest_id = problem_data.get('contestId')
                    index = problem_data.get('index')
                    
                    if not contest_id or not index:
                        continue
                        
                    # Проверяем существование задачи
                    existing_problem = session.query(Problem).filter(
                        and_(
                            Problem.contest_id == contest_id,
                            Problem.index == index
                        )
                    ).first()
                    
                    solved_count = stats_dict.get((contest_id, index), 0)
                    rating = problem_data.get('rating')
                    
                    if existing_problem:
                        # Обновляем существующую задачу
                        existing_problem.name = problem_data.get('name')
                        existing_problem.rating = rating
                        existing_problem.solved_count = solved_count
                        current_problem = existing_problem
                    else:
                        # Создаем новую задачу
                        current_problem = Problem(
                            contest_id=contest_id,
                            index=index,
                            name=problem_data.get('name'),
                            rating=rating,
                            solved_count=solved_count
                        )
                        session.add(current_problem)
                    
                    session.flush()  # Получаем ID для новой задачи
                    
                    # Очищаем старые теги и добавляем новые
                    current_problem.tags.clear()
                    
                    # Добавляем теги
                    tags = problem_data.get('tags', [])
                    for tag_name in tags:
                        tag = session.query(Tag).filter(Tag.name == tag_name).first()
                        if not tag:
                            tag = Tag(name=tag_name)
                            session.add(tag)
                            session.flush()
                        current_problem.tags.append(tag)
                
                session.commit()
                logging.info("Database updated successfully")
                
            except SQLAlchemyError as e:
                session.rollback()
                logging.error(f"Database error: {e}")
            finally:
                session.close()
    
    def get_problems_by_filters(self, rating: Optional[int] = None, 
                               tags: Optional[List[str]] = None, 
                               limit: int = 10) -> List[Problem]:
        """Получить задачи по фильтрам с уникальными контестами"""
        session = self.Session()
        try:
            # Используем joinedload для предзагрузки тегов
            query = session.query(Problem).options(joinedload(Problem.tags))
            
            if rating:
                query = query.filter(Problem.rating == rating)
                
            if tags:
                for tag in tags:
                    query = query.filter(Problem.tags.any(name=tag))
            
            # Получаем все задачи, удовлетворяющие фильтрам
            all_problems = query.all()
            
            # Обеспечиваем уникальность контестов
            unique_contest_problems = []
            used_contests = set()
            
            for problem in all_problems:
                if problem.contest_id not in used_contests:
                    unique_contest_problems.append(problem)
                    used_contests.add(problem.contest_id)
                
                if len(unique_contest_problems) >= limit:
                    break
            
            return unique_contest_problems
            
        finally:
            session.close()
    
    def get_available_ratings(self) -> List[int]:
        """Получить список доступных сложностей"""
        session = self.Session()
        try:
            ratings = session.query(Problem.rating).filter(
                Problem.rating.isnot(None)
            ).distinct().order_by(Problem.rating).all()
            return [r[0] for r in ratings if r[0] is not None]
        finally:
            session.close()
    
    def get_available_tags(self) -> List[str]:
        """Получить список доступных тегов"""
        session = self.Session()
        try:
            tags = session.query(Tag.name).order_by(Tag.name).all()
            return [t[0] for t in tags]
        finally:
            session.close()
    
    def get_random_problem(self, rating: Optional[int] = None, 
                          tags: Optional[List[str]] = None) -> Optional[Problem]:
        """Получить случайную задачу"""
        problems = self.get_problems_by_filters(rating, tags, limit=100)
        import random
        return random.choice(problems) if problems else None