#!/usr/bin/env python3
"""
Complete pipeline for tax calendar:
1. Scrape calendar from AEAT
2. Load into Supabase

Usage:
    python scripts/sync_tax_calendar.py --year 2025
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.data_collection.scrape_tax_calendar import AEATCalendarScraper
from scripts.ingestion.ingest_calendar_rest_api import CalendarRestAPIIngestor


def main():
    parser = argparse.ArgumentParser(description='Sync tax calendar from AEAT to Supabase')
    parser.add_argument('--years', type=int, nargs='+', help='Specific years to scrape (e.g., --years 2025 2026)')
    parser.add_argument('--output-dir', default='data', help='Directory for temporary JSON files')
    
    args = parser.parse_args()
    
    # Default: current year and next year
    if not args.years:
        from datetime import datetime
        current_year = datetime.now().year
        args.years = [current_year, current_year + 1]
    
    print("=" * 70)
    print("TAX CALENDAR SYNC PIPELINE")
    print("=" * 70)
    print(f"Years: {', '.join(map(str, args.years))}")
    print(f"Output directory: {args.output_dir}")
    print()
    
    import os
    os.makedirs(args.output_dir, exist_ok=True)
    
    scraper = AEATCalendarScraper()
    ingestor = CalendarRestAPIIngestor()
    
    total_deadlines = 0
    all_success = True
    
    for year in args.years:
        print("=" * 70)
        print(f"PROCESSING YEAR: {year}")
        print("=" * 70)
        
        # Step 1: Scrape calendar
        print(f"\nSTEP 1: Scraping AEAT tax calendar for {year}...")
        print("-" * 70)
        
        deadlines = scraper.scrape_calendar(year)
        
        if not deadlines:
            print(f"❌ No deadlines scraped for {year}!")
            all_success = False
            continue
        
        # Save to JSON
        output_file = os.path.join(args.output_dir, f'tax_calendar_{year}.json')
        scraper.save_to_json(deadlines, output_file)
        
        print()
        
        # Step 2: Load into Supabase
        print(f"STEP 2: Loading {year} calendar into Supabase...")
        print("-" * 70)
        
        json_path = Path(output_file)
        success = ingestor.process_json(json_path)
        
        if success:
            total_deadlines += len(deadlines)
            print(f"✅ Year {year} completed: {len(deadlines)} deadlines")
        else:
            print(f"❌ Year {year} failed!")
            all_success = False
        
        print()
    
    # Final summary
    print("=" * 70)
    if all_success:
        print("✅ TAX CALENDAR SYNC COMPLETED SUCCESSFULLY!")
        print(f"   Years processed: {', '.join(map(str, args.years))}")
        print(f"   Total deadlines: {total_deadlines}")
    else:
        print("⚠️  TAX CALENDAR SYNC COMPLETED WITH ERRORS")
        print(f"   Check logs above for details")
    print("=" * 70)
    
    return all_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

