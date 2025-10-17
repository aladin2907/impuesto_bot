"""
Simple Telegram parser for testing
Downloads messages from specified group for the last week and saves to JSON
"""

import sys
import os
import json
import asyncio
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from telethon import TelegramClient
from telethon.tl.types import Message
from app.config.settings import settings


class TelegramTestParser:
    """Simple parser for testing Telegram group parsing"""
    
    def __init__(self):
        """Initialize Telegram client"""
        self.api_id = settings.TELEGRAM_API_ID
        self.api_hash = settings.TELEGRAM_API_HASH
        self.phone = settings.TELEGRAM_PHONE
        
        if not self.api_id or not self.api_hash:
            raise ValueError(
                "Missing Telegram API credentials!\n"
                "Get them from https://my.telegram.org and add to .env:\n"
                "TELEGRAM_API_ID=your_api_id\n"
                "TELEGRAM_API_HASH=your_api_hash\n"
                "TELEGRAM_PHONE=+34xxxxxxxxx"
            )
        
        # Create client (session will be saved to telegram.session file)
        self.client = TelegramClient('telegram_session', int(self.api_id), self.api_hash)
    
    async def parse_group(
        self,
        group_username: str,
        days_back: int = 7,
        limit: int = 1000
    ) -> list:
        """
        Parse messages from a Telegram group
        
        Args:
            group_username: Group username (e.g., 'it_autonomos_spain')
            days_back: How many days back to fetch (default: 7)
            limit: Maximum number of messages to fetch (default: 1000)
            
        Returns:
            List of message dictionaries
        """
        messages_data = []
        
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
            
            # Calculate date threshold (timezone-aware)
            from datetime import timezone
            date_threshold = datetime.now(timezone.utc) - timedelta(days=days_back)
            print(f"📅 Fetching messages from {date_threshold.strftime('%Y-%m-%d')} to now...")
            
            # Fetch messages
            message_count = 0
            async for message in self.client.iter_messages(entity, limit=limit):
                # Stop if message is older than threshold
                if message.date < date_threshold:
                    break
                
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
                    'views': message.views if hasattr(message, 'views') else None,
                    'forwards': message.forwards if hasattr(message, 'forwards') else None,
                }
                
                messages_data.append(msg_data)
                
                # Progress indicator
                if message_count % 50 == 0:
                    print(f"  Fetched {message_count} messages...")
            
            print(f"✅ Total messages fetched: {len(messages_data)}")
            
        except Exception as e:
            print(f"❌ Error parsing group: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await self.client.disconnect()
        
        return messages_data
    
    def save_to_json(self, messages: list, output_file: str):
        """Save messages to JSON file"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
            print(f"✅ Saved {len(messages)} messages to {output_file}")
        except Exception as e:
            print(f"❌ Failed to save JSON: {e}")


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test Telegram group parser - download messages to JSON"
    )
    parser.add_argument(
        'group',
        help='Group username (e.g., it_autonomos_spain or chatfornomads)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days back to fetch (default: 7)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=1000,
        help='Maximum number of messages (default: 1000)'
    )
    parser.add_argument(
        '--output',
        default='telegram_messages.json',
        help='Output JSON file (default: telegram_messages.json)'
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("TuExpertoFiscal NAIL - Telegram Test Parser")
    print("="*60)
    print(f"Group: {args.group}")
    print(f"Period: Last {args.days} days")
    print(f"Limit: {args.limit} messages")
    print(f"Output: {args.output}")
    print("="*60)
    print()
    
    # Create parser
    telegram_parser = TelegramTestParser()
    
    # Parse messages
    messages = await telegram_parser.parse_group(
        group_username=args.group,
        days_back=args.days,
        limit=args.limit
    )
    
    if messages:
        # Save to JSON
        telegram_parser.save_to_json(messages, args.output)
        
        # Show stats
        print()
        print("="*60)
        print("STATISTICS")
        print("="*60)
        print(f"Total messages: {len(messages)}")
        
        # Show first and last message dates
        if messages:
            first_date = datetime.fromisoformat(messages[-1]['date'])
            last_date = datetime.fromisoformat(messages[0]['date'])
            print(f"Date range: {first_date.strftime('%Y-%m-%d')} to {last_date.strftime('%Y-%m-%d')}")
            
            # Calculate average message length
            avg_length = sum(len(msg['text']) for msg in messages) / len(messages)
            print(f"Average message length: {avg_length:.0f} characters")
            
            # Show sample message
            print()
            print("Sample message:")
            print("-" * 60)
            print(f"Date: {messages[0]['date']}")
            print(f"Text: {messages[0]['text'][:200]}...")
            print("-" * 60)
        
        print("="*60)
    else:
        print("❌ No messages fetched")


if __name__ == "__main__":
    asyncio.run(main())
