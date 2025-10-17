import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///codeforces.db')

# Codeforces API settings
CODEFORCES_API_URL = "https://codeforces.com/api"
UPDATE_INTERVAL_HOURS = 1

# Bot settings
PROBLEMS_PER_PAGE = 10