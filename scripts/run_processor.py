"""
Run the job processor workflow.

This script processes unanalyzed jobs using LLM analysis.
"""

import logging
import sys
import asyncio

from jobly.db import JobDatabase
from jobly.analyzers import JobAnalyzer
from jobly.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("RunProcessor")


async def process_jobs_async(batch_size: int):
    """Process jobs asynchronously."""
    db = JobDatabase()
    analyzer = JobAnalyzer()
    
    logger.info(f"Starting Job Processor (Batch Size: {batch_size})...")
    
    while True:
        try:
            # Fetch unanalyzed jobs
            response = db.supabase.table("job_postings") \
                .select("*") \
                .is_("llm_analysis", "null") \
                .limit(batch_size) \
                .execute()
            
            jobs = response.data
            
            if not jobs:
                logger.info("No unanalyzed jobs found.")
                break
                
            logger.info(f"Found {len(jobs)} unanalyzed jobs. Processing batch...")
            
            tasks = []
            for job in jobs:
                tasks.append(process_single_job(db, analyzer, job))
            
            # Run batch concurrently
            await asyncio.gather(*tasks)
            
            # Brief sleep to avoid hammering if loop continues immediately
            await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error in processing loop: {e}", exc_info=True)
            break

    logger.info("Job Processor Finished.")


async def process_single_job(db, analyzer, job):
    """Process a single job."""
    job_id = job['id']
    description = job.get('description', '')
    
    if not description:
        logger.warning(f"Job {job_id} has no description. Skipping.")
        return
        
    logger.info(f"Analyzing Job: {job.get('job_title')} ({job_id})")
    
    try:
        analysis = await analyzer.analyze_job_description_async(description)
        if analysis:
            logger.info(f"Generated analysis of {len(str(analysis))} characters for job {job_id}")
            db.update_llm_analysis(job_id, analysis)
            logger.info(f"Successfully analyzed and updated job {job_id}")
        else:
            logger.warning(f"Analysis returned empty for job {job_id}")

    except Exception as e:
        logger.error(f"Failed to analyze job {job_id}: {e}")


def main():
    """Main entry point for running the processor."""
    logger.info("--- Starting Job Processor ---")
    
    try:
        batch_size = settings.processor.batch_size
        asyncio.run(process_jobs_async(batch_size))
        logger.info("Processor completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Processor failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
