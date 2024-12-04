import os
import sys
import logging
from main import bot

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('discord_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    try:
        logger.info("Starting Discord bot...")
        bot.run()
    except Exception as e:
        logger.error(f"Error in bot: {str(e)}", exc_info=True)
        
if __name__ == "__main__":
    main()
