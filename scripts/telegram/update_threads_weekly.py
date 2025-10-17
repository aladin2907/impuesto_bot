"""
Weekly update script - downloads new messages and updates existing threads
Run this script weekly via cron to keep threads up-to-date
"""

import sys
import os
import json
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from telethon import TelegramClient
from telethon.tl.types import Message
from app.config.settings import settings
from scripts.telegram.download_full_history import ThreadBuilder


class ThreadUpdater:
    """Update existing threads with new messages"""
    
    def __init__(self):
        self.api_id = settings.TELEGRAM_API_ID
        self.api_hash = settings.TELEGRAM_API_HASH
        self.phone = settings.TELEGRAM_PHONE
        
        if not self.api_id or not self.api_hash:
            raise ValueError("Missing Telegram API credentials in .env")
        
        self.client = TelegramClient('telegram_session', int(self.api_id), self.api_hash)
    
    def load_existing_threads(self, file_path: str) -> dict:
        """Load existing threads from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️  File {file_path} not found. Run download_full_history.py first!")
            return None
        except Exception as e:
            print(f"❌ Error loading threads: {e}")
            return None
    
    async def fetch_new_messages(
        self,
        group_username: str,
        since_date: datetime,
        limit: int = 1000
    ) -> List[dict]:
        """Fetch new messages since a specific date"""
        new_messages = []
        
        try:
            await self.client.start(phone=self.phone)
            print(f"✅ Connected to Telegram")
            
            entity = await self.client.get_entity(group_username)
            print(f"✅ Found group: {entity.title}")
            print(f"📥 Fetching messages since {since_date.strftime('%Y-%m-%d %H:%M')}...")
            
            message_count = 0
            async for message in self.client.iter_messages(entity, limit=limit):
                # Stop if message is older than threshold
                if message.date < since_date:
                    break
                
                if not isinstance(message, Message) or not message.text:
                    continue
                
                message_count += 1
                
                msg_data = {
                    'id': message.id,
                    'date': message.date.isoformat(),
                    'text': message.text,
                    'sender_id': message.sender_id,
                    'reply_to': message.reply_to_msg_id if message.reply_to else None,
                }
                
                new_messages.append(msg_data)
                
                if message_count % 50 == 0:
                    print(f"  Fetched {message_count} new messages...")
            
            print(f"✅ Fetched {len(new_messages)} new messages")
            
        except Exception as e:
            print(f"❌ Error fetching messages: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await self.client.disconnect()
        
        return new_messages
    
    def merge_messages_and_rebuild(
        self,
        existing_data: dict,
        new_messages: List[dict]
    ) -> dict:
        """Merge new messages with existing and rebuild all threads"""
        
        if not new_messages:
            print("ℹ️  No new messages to add")
            return existing_data
        
        print("\n" + "="*60)
        print("Merging new messages with existing threads...")
        
        # Extract all messages from existing threads
        all_messages = {}
        for thread in existing_data['threads']:
            for msg in thread['messages']:
                all_messages[msg['id']] = {
                    'id': msg['id'],
                    'date': msg['date'],
                    'text': msg['text'],
                    'sender_id': msg['sender_id'],
                    'reply_to': None  # Will be reconstructed
                }
        
        # Add new messages
        added_count = 0
        for msg in new_messages:
            if msg['id'] not in all_messages:
                all_messages[msg['id']] = msg
                added_count += 1
        
        print(f"✅ Added {added_count} new messages")
        print(f"Total messages: {len(all_messages)}")
        
        # Rebuild reply_to relationships from original messages
        # (we need to preserve this from new_messages)
        for msg in new_messages:
            if msg['id'] in all_messages:
                all_messages[msg['id']]['reply_to'] = msg.get('reply_to')
        
        # Rebuild all threads
        thread_builder = ThreadBuilder()
        for msg in all_messages.values():
            thread_builder.add_message(msg)
        
        threads = thread_builder.build_threads()
        flat_threads = thread_builder.get_flat_threads()
        
        # Update metadata
        updated_data = {
            'group': existing_data['group'],
            'group_title': existing_data['group_title'],
            'downloaded_at': existing_data['downloaded_at'],
            'last_updated': datetime.now().isoformat(),
            'total_messages': len(all_messages),
            'total_threads': len(flat_threads),
            'threads': flat_threads
        }
        
        print(f"✅ Rebuilt {len(flat_threads)} threads")
        
        return updated_data
    
    async def update_threads(
        self,
        group_username: str,
        threads_file: str,
        days_back: int = 7
    ) -> bool:
        """
        Update existing threads with new messages from the last N days
        
        Args:
            group_username: Group username
            threads_file: Path to existing threads JSON file
            days_back: How many days back to check (default: 7)
        """
        # Load existing threads
        existing_data = self.load_existing_threads(threads_file)
        if not existing_data:
            return False
        
        # Calculate since date
        since_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        # Fetch new messages
        new_messages = await self.fetch_new_messages(
            group_username,
            since_date,
            limit=1000
        )
        
        # Merge and rebuild
        updated_data = self.merge_messages_and_rebuild(existing_data, new_messages)
        
        # Save updated threads
        backup_file = threads_file.replace('.json', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        
        # Create backup
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
        print(f"✅ Backup saved to {backup_file}")
        
        # Save updated version
        with open(threads_file, 'w', encoding='utf-8') as f:
            json.dump(updated_data, f, ensure_ascii=False, indent=2)
        print(f"✅ Updated threads saved to {threads_file}")
        
        return True


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Update existing Telegram threads with new messages (weekly update)"
    )
    parser.add_argument(
        'group',
        help='Group username (e.g., it_autonomos_spain)'
    )
    parser.add_argument(
        '--file',
        default='telegram_threads_full.json',
        help='Existing threads JSON file (default: telegram_threads_full.json)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Check messages from last N days (default: 7)'
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("TuExpertoFiscal NAIL - Weekly Thread Updater")
    print("="*60)
    print(f"Group: {args.group}")
    print(f"Threads file: {args.file}")
    print(f"Period: Last {args.days} days")
    print("="*60)
    print()
    
    updater = ThreadUpdater()
    success = await updater.update_threads(
        group_username=args.group,
        threads_file=args.file,
        days_back=args.days
    )
    
    if success:
        print()
        print("="*60)
        print("✅ WEEKLY UPDATE COMPLETED SUCCESSFULLY!")
        print("="*60)
    else:
        print()
        print("="*60)
        print("❌ UPDATE FAILED")
        print("="*60)


if __name__ == "__main__":
    asyncio.run(main())

