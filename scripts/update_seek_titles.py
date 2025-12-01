"""
Migration script to clean job titles for existing Seek job postings.

This script:
1. Fetches all job postings with 'seek' in the platforms array
2. Cleans the job_title field using extract_job_role()
3. Regenerates the fingerprint with the cleaned title
4. Updates both fields in the database

Usage:
    python scripts/update_seek_titles.py --dry-run  # Preview changes
    python scripts/update_seek_titles.py            # Apply changes
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
from typing import Dict, List, Tuple
from jobly.db.base_database import BaseDatabase
from jobly.db.job_database import JobDatabase
from jobly.utils.scraper_utils import extract_job_role


class SeekTitleUpdater:
    """Handles updating Seek job titles and fingerprints."""
    
    def __init__(self, dry_run: bool = False):
        self.db = JobDatabase()
        self.dry_run = dry_run
        self.stats = {
            'total_jobs': 0,
            'titles_changed': 0,
            'titles_unchanged': 0,
            'errors': 0
        }
        self.examples: List[Tuple[str, str, str]] = []  # (company, old_title, new_title)
    
    def fetch_seek_jobs(self) -> List[Dict]:
        """Fetch all jobs with 'seek' in platforms array."""
        try:
            # Query jobs where 'seek' is in the platforms array
            response = self.db.supabase.table('job_postings').select('*').contains('platforms', ['seek']).execute()
            return response.data
        except Exception as e:
            print(f"❌ Error fetching Seek jobs: {e}")
            return []
    
    def clean_title(self, raw_title: str) -> str:
        """Clean a job title using extract_job_role."""
        if not raw_title or raw_title == "Unknown Title":
            return raw_title
        return extract_job_role(raw_title)
    
    def generate_fingerprint(self, company: str, title: str) -> str:
        """Generate fingerprint using the same logic as JobDatabase."""
        return JobDatabase._generate_fingerprint(company, title)
    
    def update_job(self, job_id: str, new_title: str) -> bool:
        """Update a job's title in the database (fingerprint remains unchanged)."""
        if self.dry_run:
            return True  # Simulate success in dry-run mode
        
        try:
            self.db.supabase.table('job_postings').update({
                'job_title': new_title
            }).eq('id', job_id).execute()
            return True
        except Exception as e:
            print(f"❌ Error updating job {job_id}: {e}")
            return False
    
    def process_jobs(self):
        """Main processing logic."""
        print("🔍 Fetching Seek job postings...")
        jobs = self.fetch_seek_jobs()
        self.stats['total_jobs'] = len(jobs)
        
        if not jobs:
            print("⚠️  No Seek jobs found in database.")
            return
        
        print(f"📊 Found {len(jobs)} Seek job postings")
        print(f"{'🔥 DRY RUN MODE - No changes will be applied' if self.dry_run else '✅ LIVE MODE - Changes will be applied'}")
        print("-" * 80)
        
        for job in jobs:
            job_id = job.get('id')
            company = job.get('company', '')
            old_title = job.get('job_title', '')
            
            # Clean the title
            new_title = self.clean_title(old_title)
            
            # Check if title changed
            if new_title != old_title:
                # Store example for display (first 10 only)
                if len(self.examples) < 10:
                    self.examples.append((company, old_title, new_title))
                
                # Update only the job_title in database (fingerprint stays the same)
                if self.update_job(job_id, new_title):
                    self.stats['titles_changed'] += 1
                    print(f"✏️  Changed: '{old_title}' → '{new_title}' ({company})")
                else:
                    self.stats['errors'] += 1
            else:
                self.stats['titles_unchanged'] += 1
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print summary statistics."""
        print("\n" + "=" * 80)
        print("📈 SUMMARY")
        print("=" * 80)
        print(f"Total Seek jobs processed: {self.stats['total_jobs']}")
        print(f"Titles changed: {self.stats['titles_changed']}")
        print(f"Titles unchanged: {self.stats['titles_unchanged']}")
        print(f"Errors: {self.stats['errors']}")
        
        if self.examples:
            print("\n" + "=" * 80)
            print("📝 EXAMPLE CHANGES (first 10)")
            print("=" * 80)
            for company, old_title, new_title in self.examples:
                print(f"\n🏢 Company: {company}")
                print(f"   Before: {old_title}")
                print(f"   After:  {new_title}")
        
        if self.dry_run:
            print("\n" + "=" * 80)
            print("🔥 DRY RUN MODE - No changes were applied to the database")
            print("=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Clean job titles for existing Seek job postings'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without applying them'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🧹 SEEK JOB TITLE CLEANUP SCRIPT")
    print("=" * 80)
    print()
    
    updater = SeekTitleUpdater(dry_run=args.dry_run)
    updater.process_jobs()
    
    print("\n✅ Script completed!")


if __name__ == '__main__':
    main()
