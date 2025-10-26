#!/usr/bin/env python3
"""
Index tax calendar data to Elasticsearch
Loads deadlines from JSON files into calendar_deadlines index
"""

import sys
import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.services.elasticsearch_service import elastic_service


class CalendarElasticsearchIndexer:
    """Index tax calendar data to Elasticsearch"""
    
    def __init__(self):
        self.index_name = "calendar_deadlines"
        self.elastic = elastic_service
        
    def create_index(self):
        """Create calendar_deadlines index with proper mapping"""
        mapping = {
            "mappings": {
                "properties": {
                    "deadline_id": {"type": "keyword"},
                    "deadline_date": {"type": "date"},
                    "year": {"type": "integer"},
                    "quarter": {"type": "keyword"},
                    "month": {"type": "integer"},
                    "tax_type": {"type": "keyword"},
                    "tax_model": {"type": "keyword"},
                    "description": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}}
                    },
                    "applies_to": {"type": "keyword"},
                    "region": {"type": "keyword"},
                    "payment_required": {"type": "boolean"},
                    "declaration_required": {"type": "boolean"},
                    "penalty_for_late": {"type": "text"},
                    "source": {"type": "keyword"},
                    "source_url": {"type": "keyword"},
                    "indexed_at": {"type": "date"}
                }
            }
        }
        
        try:
            # Delete index if exists
            if self.elastic.client.indices.exists(index=self.index_name):
                print(f"🗑️  Deleting existing index: {self.index_name}")
                self.elastic.client.indices.delete(index=self.index_name)
            
            # Create new index
            self.elastic.client.indices.create(
                index=self.index_name,
                body=mapping
            )
            print(f"✅ Created index: {self.index_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating index: {e}")
            return False
    
    def load_calendar_file(self, file_path: Path) -> Dict:
        """Load calendar JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading {file_path}: {e}")
            return None
    
    def prepare_deadline_for_indexing(self, deadline: Dict, source_info: Dict) -> Dict:
        """Prepare deadline document for Elasticsearch"""
        # Generate unique ID
        deadline_id = f"{deadline['deadline_date']}_{deadline['tax_model']}_{deadline.get('region', 'national')}"
        
        doc = {
            "deadline_id": deadline_id,
            "deadline_date": deadline["deadline_date"],
            "year": deadline["year"],
            "quarter": deadline.get("quarter"),
            "month": deadline["month"],
            "tax_type": deadline["tax_type"],
            "tax_model": deadline["tax_model"],
            "description": deadline["description"],
            "applies_to": deadline.get("applies_to", []),
            "region": deadline.get("region", "national"),
            "payment_required": deadline.get("payment_required", False),
            "declaration_required": deadline.get("declaration_required", False),
            "penalty_for_late": deadline.get("penalty_for_late", ""),
            "source": source_info.get("source", "AEAT"),
            "source_url": source_info.get("source_url", ""),
            "indexed_at": datetime.utcnow().isoformat()
        }
        
        return doc
    
    def index_deadlines(self, calendar_data: Dict) -> int:
        """Index all deadlines from calendar data"""
        deadlines = calendar_data.get("deadlines", [])
        source_info = {
            "source": calendar_data.get("source", "AEAT"),
            "source_url": calendar_data.get("source_url", "")
        }
        
        indexed_count = 0
        errors = []
        
        for deadline in deadlines:
            try:
                doc = self.prepare_deadline_for_indexing(deadline, source_info)
                
                # Index document
                self.elastic.client.index(
                    index=self.index_name,
                    id=doc["deadline_id"],
                    body=doc
                )
                indexed_count += 1
                
            except Exception as e:
                errors.append(f"Error indexing {deadline.get('deadline_date')}: {e}")
        
        if errors:
            print(f"⚠️  {len(errors)} errors occurred:")
            for error in errors[:5]:  # Show first 5 errors
                print(f"   - {error}")
        
        return indexed_count
    
    def run(self, calendar_files: List[Path]):
        """Main indexing process"""
        print("=" * 60)
        print("📅 Calendar Elasticsearch Indexer")
        print("=" * 60)
        
        # Connect to Elasticsearch
        if not self.elastic.connect():
            print("❌ Failed to connect to Elasticsearch")
            return False
        
        # Create index
        if not self.create_index():
            return False
        
        # Index all calendar files
        total_indexed = 0
        
        for file_path in calendar_files:
            print(f"\n📄 Processing: {file_path.name}")
            
            calendar_data = self.load_calendar_file(file_path)
            if not calendar_data:
                continue
            
            indexed_count = self.index_deadlines(calendar_data)
            total_indexed += indexed_count
            
            print(f"   ✅ Indexed {indexed_count} deadlines from {file_path.name}")
        
        print(f"\n{'=' * 60}")
        print(f"✅ Total indexed: {total_indexed} deadlines")
        print(f"{'=' * 60}")
        
        return True


def main():
    """Main entry point"""
    # Find calendar files
    data_dir = project_root / "data"
    calendar_files = list(data_dir.glob("tax_calendar_*.json"))
    
    if not calendar_files:
        print("❌ No calendar files found in data/")
        print("   Expected: data/tax_calendar_2025.json, etc.")
        return
    
    print(f"Found {len(calendar_files)} calendar files:")
    for f in calendar_files:
        print(f"  - {f.name}")
    print()
    
    # Run indexer
    indexer = CalendarElasticsearchIndexer()
    success = indexer.run(calendar_files)
    
    if success:
        print("\n🎉 Calendar indexing completed successfully!")
    else:
        print("\n❌ Calendar indexing failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

