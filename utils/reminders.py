import json
import os
from datetime import datetime, timedelta
from config import REMINDERS_DATA_PATH

class ReminderSystem:
    def __init__(self):
        self.reminders = {}
        self.load_reminders()
    
    def load_reminders(self):
        if os.path.exists(REMINDERS_DATA_PATH):
            with open(REMINDERS_DATA_PATH, 'r', encoding='utf-8') as f:
                self.reminders = json.load(f)
    
    def save_reminders(self):
        with open(REMINDERS_DATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.reminders, f, ensure_ascii=False, indent=2)
    
    def add_reminder(self, user_id, channel_id, message, minutes):
        reminder_time = datetime.now() + timedelta(minutes=minutes)
        reminder_id = str(len(self.reminders) + 1)
        
        self.reminders[reminder_id] = {
            "user_id": user_id,
            "channel_id": channel_id,
            "message": message,
            "time": reminder_time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.save_reminders()
        return reminder_time
    
    def check_reminders(self, bot):
        current_time = datetime.now()
        to_remove = []
        
        for reminder_id, reminder in self.reminders.items():
            reminder_time = datetime.strptime(reminder["time"], "%Y-%m-%d %H:%M:%S")
            if current_time >= reminder_time:
                channel = bot.get_channel(int(reminder["channel_id"]))
                if channel:
                    asyncio.create_task(
                        channel.send(f"<@{reminder['user_id']}> 提醒：{reminder['message']}")
                    )
                to_remove.append(reminder_id)
        
        for reminder_id in to_remove:
            del self.reminders[reminder_id]
        
        if to_remove:
            self.save_reminders()
