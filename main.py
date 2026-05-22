import os
import logging
from typing import Final
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler

from core.engine import engine
from bot.handlers import (
    start_command, apy_command, rate_command, vix_command, 
    pe_command, countries_command, greed_command, thb_command, maxpain_command, poly_command,
    get_command, set_command, stop_command, start_job_command, 
    status_command, arbitrage_job, rate_job, vix_job, pe_job, 
    fng_job, thb_job, maxpain_job, apy_tracker_job, error_handler
)

# Load environment variables
load_dotenv()

TOKEN: Final = os.getenv("TELEGRAM_TOKEN")
CHAT_ID: Final = os.getenv("TELEGRAM_CHAT_ID")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    """Called after the bot is initialized — start the price engine."""
    engine.start()
    logger.info("Price engine started via post_init")


if __name__ == '__main__':
    if not TOKEN or not CHAT_ID:
        logger.error("Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID in .env file")
        exit(1)

    app = Application.builder().token(TOKEN).post_init(post_init).build()

    # ── User Commands ───────────────────────────────────────────
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('h', start_command))
    app.add_handler(CommandHandler('apy', apy_command))
    app.add_handler(CommandHandler('rate', rate_command))
    app.add_handler(CommandHandler('vix', vix_command))
    app.add_handler(CommandHandler('pe', pe_command))
    app.add_handler(CommandHandler('countries', countries_command))
    app.add_handler(CommandHandler('greed', greed_command))
    app.add_handler(CommandHandler('thb', thb_command))
    app.add_handler(CommandHandler('maxpain', maxpain_command))
    app.add_handler(CommandHandler('poly', poly_command))

    # ── Interactive Control Commands ────────────────────────────
    app.add_handler(CommandHandler('get', get_command))
    app.add_handler(CommandHandler('set', set_command))
    app.add_handler(CommandHandler('stop', stop_command))
    app.add_handler(CommandHandler('start_job', start_job_command))
    app.add_handler(CommandHandler('status', status_command))

    # ── Background Jobs ─────────────────────────────────────────
    job_queue = app.job_queue
    job_queue.run_repeating(arbitrage_job, interval=5, first=3)
    job_queue.run_repeating(rate_job, interval=10, first=5)
    job_queue.run_repeating(vix_job, interval=60, first=10)
    job_queue.run_repeating(pe_job, interval=3600, first=15)
    job_queue.run_repeating(fng_job, interval=3600, first=20)
    job_queue.run_repeating(thb_job, interval=60, first=25)        # 1 min for "real-time" THB
    job_queue.run_repeating(maxpain_job, interval=3600, first=30)  # Hourly Max Pain check
    job_queue.run_repeating(apy_tracker_job, interval=600, first=60) # 10 mins for better averages

    app.add_error_handler(error_handler)

    logger.info("MarketSentry started in modular mode...")
    app.run_polling()
