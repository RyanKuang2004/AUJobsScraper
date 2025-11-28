"""
Scheduler for automated job scraping and processing.

Runs the scraper and processor at scheduled intervals.
"""

import schedule
import time
import subprocess
import logging
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Scheduler")

# Get the project root directory (parent of scripts/)
PROJECT_ROOT = Path(__file__).parent.parent


def run_process_and_stream_output(command, env):
    """
    Runs a subprocess and streams its stdout/stderr to the logger in real-time.
    """
    process = subprocess.Popen(
        command,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Merge stderr into stdout
        text=True,
        bufsize=1,  # Line buffered
        universal_newlines=True,
        cwd=PROJECT_ROOT  # Ensure we run from project root
    )
    
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            logger.info(f"[{command[-1]}] {output.strip()}")
            
    return process.poll()


def run_workflow():
    """Run the complete scraping and processing workflow."""
    logger.info("Starting scheduled workflow...")
    try:
        env = os.environ.copy()
        
        # Run scraper
        logger.info("Launching Scraper...")
        scraper_path = PROJECT_ROOT / "scripts" / "run_scraper.py"
        return_code = run_process_and_stream_output(
            [sys.executable, str(scraper_path)],
            env=env
        )
        
        if return_code == 0:
            logger.info("Scraper finished successfully.")
            
            # Run processor
            logger.info("Starting Job Processor...")
            processor_path = PROJECT_ROOT / "scripts" / "run_processor.py"
            processor_return_code = run_process_and_stream_output(
                [sys.executable, str(processor_path)],
                env=env
            )
            
            if processor_return_code == 0:
                logger.info("Job Processor finished successfully.")
            else:
                logger.error(f"Job Processor failed with return code {processor_return_code}.")
                
        else:
            logger.error(f"Scraper failed with return code {return_code}.")
            
    except Exception as e:
        logger.error(f"Error running workflow: {e}", exc_info=True)


def main():
    """Main scheduler entry point."""
    logger.info("Scheduler started. Job scheduled for 06:00 daily...")
    
    # Schedule the job every day at 06:00
    schedule.every().day.at("06:00").do(run_workflow)
    
    # Also run immediately on startup if requested (useful for testing)
    if os.getenv("RUN_ON_STARTUP", "false").lower() == "true":
        logger.info("Running on startup...")
        run_workflow()

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
