#!/usr/bin/env python3
"""
Ingestion script for tax calendar data to Supabase using REST API.
Loads structured deadlines into calendar_deadlines table.
"""

import sys
import json
import requests
from pathlib import Path
from typing import List, Dict, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config.settings import settings


class CalendarRestAPIIngestor:
    """Ingestor for tax calendar data via Supabase REST API"""
    
    def __init__(self):
        self.base_url = settings.SUPABASE_URL
        self.api_key = settings.SUPABASE_KEY
        self.headers = {
            "apikey": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        self.source_id = None
    
    def test_connection(self) -> bool:
        """Test REST API connection"""
        try:
            response = requests.get(
                f"{self.base_url}/rest/v1/",
                headers={"apikey": self.api_key}
            )
            if response.status_code == 200:
                print("✅ Connected to Supabase REST API")
                return True
            else:
                print(f"❌ API responded with status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False
    
    def get_or_create_source(self) -> Optional[str]:
        """Get or create knowledge_sources entry for AEAT calendar"""
        try:
            # Try to find existing source
            response = requests.get(
                f"{self.base_url}/rest/v1/knowledge_sources",
                headers=self.headers,
                params={
                    "source_type": "eq.calendar",
                    "source_name": "eq.AEAT Tax Calendar",
                    "select": "id",
                    "limit": 1
                }
            )
            
            if response.status_code == 200 and response.json():
                source_id = response.json()[0]["id"]
                print(f"📍 Found existing source: {source_id}")
                return source_id
            
            # Create new source
            new_source = {
                "source_type": "calendar",
                "source_name": "AEAT Tax Calendar",
                "source_url": "https://sede.agenciatributaria.gob.es/Sede/calendario-contribuyente.html",
                "description": "Official AEAT tax calendar",
                "sync_frequency": "monthly",
                "is_active": True
            }
            
            response = requests.post(
                f"{self.base_url}/rest/v1/knowledge_sources",
                headers=self.headers,
                json=new_source
            )
            
            if response.status_code in [200, 201]:
                source_id = response.json()[0]["id"]
                print(f"✅ Created new source: {source_id}")
                return source_id
            else:
                print(f"❌ Failed to create source: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting/creating source: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def load_deadlines_from_json(self, json_path: Path) -> List[Dict]:
        """Load deadlines from JSON file"""
        try:
            with json_path.open('r', encoding='utf-8') as f:
                data = json.load(f)
            
            deadlines = data.get('deadlines', [])
            print(f"📄 Loaded {len(deadlines)} deadlines from JSON")
            return deadlines
            
        except Exception as e:
            print(f"❌ Error loading JSON: {e}")
            return []
    
    def clear_existing_deadlines(self, year: int) -> bool:
        """Clear existing deadlines for the specified year"""
        try:
            response = requests.delete(
                f"{self.base_url}/rest/v1/calendar_deadlines",
                headers=self.headers,
                params={
                    "year": f"eq.{year}",
                    "source_id": f"eq.{self.source_id}"
                }
            )
            
            if response.status_code in [200, 204]:
                print(f"🗑️  Cleared existing deadlines for year {year}")
                return True
            else:
                print(f"⚠️  Could not clear deadlines: {response.status_code}")
                return True  # Continue anyway
                
        except Exception as e:
            print(f"⚠️  Error clearing deadlines: {e}")
            return True  # Continue anyway
    
    def insert_deadlines(self, deadlines: List[Dict]) -> bool:
        """Insert deadlines into calendar_deadlines table via upsert"""
        try:
            # Prepare data for insert
            insert_data = []
            for deadline in deadlines:
                insert_data.append({
                    "source_id": self.source_id,
                    "deadline_date": deadline.get('deadline_date'),
                    "year": deadline.get('year'),
                    "quarter": deadline.get('quarter'),
                    "month": deadline.get('month'),
                    "tax_type": deadline.get('tax_type'),
                    "tax_model": deadline.get('tax_model'),
                    "description": deadline.get('description'),
                    "applies_to": deadline.get('applies_to', []),
                    "region": deadline.get('region', 'national'),
                    "payment_required": deadline.get('payment_required', True),
                    "declaration_required": deadline.get('declaration_required', True),
                    "penalty_for_late": deadline.get('penalty_for_late'),
                    "indexed_in_elasticsearch": False,
                    "elasticsearch_doc_id": None,
                    "metadata": None
                })
            
            # Upsert with conflict resolution
            upsert_headers = self.headers.copy()
            upsert_headers["Prefer"] = "resolution=merge-duplicates"
            
            response = requests.post(
                f"{self.base_url}/rest/v1/calendar_deadlines",
                headers=upsert_headers,
                json=insert_data
            )
            
            if response.status_code in [200, 201]:
                print(f"✅ Inserted/updated {len(deadlines)} deadlines")
                return True
            else:
                print(f"❌ Failed to insert deadlines: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error inserting deadlines: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def update_source_sync_time(self):
        """Update last_synced_at for the source"""
        try:
            from datetime import datetime
            
            response = requests.patch(
                f"{self.base_url}/rest/v1/knowledge_sources",
                headers=self.headers,
                params={"id": f"eq.{self.source_id}"},
                json={"last_synced_at": datetime.utcnow().isoformat()}
            )
            
            if response.status_code in [200, 204]:
                print("✅ Updated source sync time")
            else:
                print(f"⚠️  Could not update sync time: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️  Error updating sync time: {e}")
    
    def process_json(self, json_path: Path) -> bool:
        """Complete processing pipeline"""
        print("=" * 60)
        print("TAX CALENDAR INGESTION TO SUPABASE (REST API)")
        print("=" * 60)
        print(f"📄 Processing: {json_path}")
        
        # Test connection
        if not self.test_connection():
            return False
        
        # Get or create source
        self.source_id = self.get_or_create_source()
        if not self.source_id:
            return False
        
        # Load deadlines
        deadlines = self.load_deadlines_from_json(json_path)
        if not deadlines:
            print("⚠️  No deadlines to process")
            return False
        
        # Get year from first deadline
        year = deadlines[0].get('year')
        if not year:
            print("❌ Could not determine year from deadlines")
            return False
        
        print(f"\n📅 Processing year: {year}")
        
        # Clear existing for this year
        self.clear_existing_deadlines(year)
        
        # Insert new deadlines
        success = self.insert_deadlines(deadlines)
        
        if success:
            self.update_source_sync_time()
            print("\n✅ Calendar ingestion completed successfully!")
            print(f"   Total deadlines: {len(deadlines)}")
            return True
        else:
            return False


def main():
    json_path = project_root / "data" / "tax_calendar.json"
    
    if not json_path.exists():
        print(f"❌ Error: Calendar file not found at {json_path}")
        print("Please run scrape_tax_calendar.py first!")
        return False
    
    ingestor = CalendarRestAPIIngestor()
    success = ingestor.process_json(json_path)
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

