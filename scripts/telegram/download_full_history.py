"""
Download FULL history of Telegram group and build threads
Organizes messages into conversation threads based on reply chains
"""

import sys
import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from telethon import TelegramClient
from telethon.tl.types import Message
from app.config.settings import settings


class ThreadBuilder:
    """Build conversation threads from messages"""
    
    def __init__(self):
        self.messages: Dict[int, dict] = {}  # message_id -> message_data
        self.threads: List[dict] = []
    
    def add_message(self, msg_data: dict):
        """Add message to the collection"""
        self.messages[msg_data['id']] = msg_data
    
    def build_threads(self):
        """Build threads by following reply chains"""
        print("\nBuilding threads from messages...")
        
        # Find all root messages (no reply_to or reply_to not in our messages)
        root_messages = []
        for msg_id, msg in self.messages.items():
            if not msg['reply_to'] or msg['reply_to'] not in self.messages:
                root_messages.append(msg_id)
        
        print(f"Found {len(root_messages)} root messages")
        
        # Build thread for each root
        for root_id in root_messages:
            thread = self._build_thread_recursive(root_id)
            if thread:
                self.threads.append(thread)
        
        print(f"✅ Built {len(self.threads)} threads")
        
        return self.threads
    
    def _build_thread_recursive(self, msg_id: int, collected_ids: Optional[set] = None) -> Optional[dict]:
        """Recursively build a thread starting from a root message"""
        if collected_ids is None:
            collected_ids = set()
        
        if msg_id not in self.messages or msg_id in collected_ids:
            return None
        
        collected_ids.add(msg_id)
        root_msg = self.messages[msg_id]
        
        # Find all direct replies to this message
        replies = []
        for other_id, other_msg in self.messages.items():
            if other_msg['reply_to'] == msg_id and other_id not in collected_ids:
                reply_thread = self._build_thread_recursive(other_id, collected_ids)
                if reply_thread:
                    replies.append(reply_thread)
        
        # Build thread structure
        thread = {
            'id': msg_id,
            'date': root_msg['date'],
            'text': root_msg['text'],
            'sender_id': root_msg['sender_id'],
            'replies': replies
        }
        
        return thread
    
    def flatten_thread(self, thread: dict) -> dict:
        """Convert nested thread to flat structure with metadata"""
        messages = []
        
        def collect_messages(node, depth=0):
            messages.append({
                'id': node['id'],
                'date': node['date'],
                'text': node['text'],
                'sender_id': node['sender_id'],
                'depth': depth
            })
            for reply in node.get('replies', []):
                collect_messages(reply, depth + 1)
        
        collect_messages(thread)
        
        # Calculate thread metadata
        dates = [msg['date'] for msg in messages]
        
        return {
            'thread_id': thread['id'],  # Root message ID
            'first_message_date': min(dates),
            'last_updated': max(dates),
            'message_count': len(messages),
            'max_depth': max(msg['depth'] for msg in messages),
            'messages': messages
        }
    
    def get_flat_threads(self) -> List[dict]:
        """Get all threads in flat format, sorted by last update"""
        flat = [self.flatten_thread(t) for t in self.threads]
        # Sort by last_updated (most recent first)
        flat.sort(key=lambda t: t['last_updated'], reverse=True)
        return flat


class FullHistoryDownloader:
    """Download full history of a Telegram group"""
    
    def __init__(self):
        """Initialize Telegram client"""
        self.api_id = settings.TELEGRAM_API_ID
        self.api_hash = settings.TELEGRAM_API_HASH
        self.phone = settings.TELEGRAM_PHONE
        
        if not self.api_id or not self.api_hash:
            raise ValueError("Missing Telegram API credentials in .env")
        
        self.client = TelegramClient('telegram_session', int(self.api_id), self.api_hash)
    
    async def download_full_history(
        self,
        group_username: str,
        output_file: str
    ) -> List[dict]:
        """
        Download ALL messages from a group and build threads
        
        Args:
            group_username: Group username
            output_file: Output JSON file for threads
            
        Returns:
            List of thread dictionaries
        """
        all_messages = []
        
        try:
            await self.client.start(phone=self.phone)
            print(f"✅ Connected to Telegram as {self.phone}")
            
            # Get the group entity
            try:
                entity = await self.client.get_entity(group_username)
                print(f"✅ Found group: {entity.title}")
            except Exception as e:
                print(f"❌ Failed to find group '{group_username}': {e}")
                return []
            
            print(f"📥 Downloading FULL history (this may take a while)...")
            
            # Fetch ALL messages (no limit)
            message_count = 0
            async for message in self.client.iter_messages(entity):
                # Only process text messages
                if not isinstance(message, Message) or not message.text:
                    continue
                
                message_count += 1
                
                # Extract message data
                msg_data = {
                    'id': message.id,
                    'date': message.date.isoformat(),
                    'text': message.text,
                    'sender_id': message.sender_id,
                    'reply_to': message.reply_to_msg_id if message.reply_to else None,
                }
                
                all_messages.append(msg_data)
                
                # Progress indicator
                if message_count % 500 == 0:
                    print(f"  Downloaded {message_count} messages...")
            
            print(f"✅ Downloaded {len(all_messages)} messages")
            
            # Build threads
            print("\n" + "="*60)
            thread_builder = ThreadBuilder()
            
            for msg in all_messages:
                thread_builder.add_message(msg)
            
            threads = thread_builder.build_threads()
            flat_threads = thread_builder.get_flat_threads()
            
            # Stats after flattening
            single_msg_threads = sum(1 for t in flat_threads if t['message_count'] == 1)
            multi_msg_threads = len(flat_threads) - single_msg_threads
            print(f"  - Single message threads: {single_msg_threads}")
            print(f"  - Multi-message threads: {multi_msg_threads}")
            
            # Save to JSON
            output_data = {
                'group': group_username,
                'group_title': entity.title,
                'downloaded_at': datetime.now().isoformat(),
                'total_messages': len(all_messages),
                'total_threads': len(flat_threads),
                'threads': flat_threads
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Saved threads to {output_file}")
            
            return flat_threads
            
        except Exception as e:
            print(f"❌ Error downloading history: {e}")
            import traceback
            traceback.print_exc()
            return []
        
        finally:
            await self.client.disconnect()


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Download FULL history of Telegram group and build threads"
    )
    parser.add_argument(
        'group',
        help='Group username (e.g., it_autonomos_spain)'
    )
    parser.add_argument(
        '--output',
        default='telegram_threads_full.json',
        help='Output JSON file (default: telegram_threads_full.json)'
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("TuExpertoFiscal NAIL - Full History Downloader")
    print("="*60)
    print(f"Group: {args.group}")
    print(f"Output: {args.output}")
    print("="*60)
    print()
    print("⚠️  WARNING: This will download ENTIRE chat history!")
    print("This may take several minutes for large groups.")
    print()
    
    # Download and build threads
    downloader = FullHistoryDownloader()
    threads = await downloader.download_full_history(
        group_username=args.group,
        output_file=args.output
    )
    
    if threads:
        print()
        print("="*60)
        print("THREAD STATISTICS")
        print("="*60)
        
        # Show some stats
        total_messages = sum(t['message_count'] for t in threads)
        avg_thread_size = total_messages / len(threads) if threads else 0
        max_thread = max(threads, key=lambda t: t['message_count'])
        deepest_thread = max(threads, key=lambda t: t['max_depth'])
        
        print(f"Total threads: {len(threads)}")
        print(f"Total messages: {total_messages}")
        print(f"Average thread size: {avg_thread_size:.1f} messages")
        print(f"Largest thread: {max_thread['message_count']} messages (ID: {max_thread['thread_id']})")
        print(f"Deepest thread: {deepest_thread['max_depth']} levels (ID: {deepest_thread['thread_id']})")
        
        # Show sample thread
        if threads:
            sample = threads[0]
            print()
            print("Sample thread (most recent):")
            print("-" * 60)
            print(f"Thread ID: {sample['thread_id']}")
            print(f"Messages: {sample['message_count']}")
            print(f"Last updated: {sample['last_updated']}")
            print(f"First message: {sample['messages'][0]['text'][:100]}...")
            print("-" * 60)
        
        print("="*60)


if __name__ == "__main__":
    asyncio.run(main())

