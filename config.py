import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Get token from environment variable
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in environment variables!")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
