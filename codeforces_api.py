import aiohttp
import asyncio
from typing import List, Dict, Optional
import logging
from config import CODEFORCES_API_URL

class CodeforcesAPI:
    def __init__(self):
        self.base_url = CODEFORCES_API_URL
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()
        
    async def make_request(self, method: str, params: Dict = None) -> Optional[Dict]:
        """Базовый метод для запросов к API"""
        url = f"{self.base_url}/{method}"
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data['status'] == 'OK':
                        return data['result']
                    else:
                        logging.error(f"API Error: {data.get('comment', 'Unknown error')}")
                else:
                    logging.error(f"HTTP Error: {response.status}")
        except Exception as e:
            logging.error(f"Request failed: {e}")
            
        return None
    
    async def get_problems(self) -> List[Dict]:
        """Получить все задачи"""
        return await self.make_request('problemset.problems')
    
    async def get_contests(self) -> List[Dict]:
        """Получить все контесты"""
        return await self.make_request('contest.list')
    
    async def search_problems(self, query: str) -> List[Dict]:
        """Поиск задач через API"""
        # Получаем все задачи и фильтруем локально
        data = await self.get_problems()
        if not data:
            return []
        
        problems = data.get('problems', [])
        problem_stats = data.get('problemStatistics', [])
        
        # Создаем словарь статистики для быстрого доступа
        stats_dict = {}
        for stat in problem_stats:
            key = (stat.get('contestId'), stat.get('index'))
            stats_dict[key] = stat.get('solvedCount', 0)
        
        # Фильтруем задачи по запросу
        query_lower = query.lower()
        filtered_problems = []
        
        for problem in problems:
            # Поиск по названию
            name = problem.get('name', '').lower()
            # Поиск по коду задачи (contestId + index)
            contest_id = problem.get('contestId')
            index = problem.get('index', '')
            full_code = f"{contest_id}{index}".lower()
            
            if (query_lower in name or 
                query_lower in full_code or
                query_lower == index.lower()):
                
                # Добавляем статистику к задаче
                problem_with_stats = problem.copy()
                problem_with_stats['solvedCount'] = stats_dict.get((contest_id, index), 0)
                filtered_problems.append(problem_with_stats)
        
        return filtered_problems[:10]  # Ограничиваем 10 результатами