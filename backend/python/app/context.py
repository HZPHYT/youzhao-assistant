import time
import uuid
from collections import defaultdict
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

class ConversationManager:
    def __init__(self, max_history=10):
        self.max_history = max_history
        self.sessions = defaultdict(lambda: {
            "history": [],
            "created_at": time.time(),
            "updated_at": time.time(),
            "title": ""
        })
    
    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        return session_id
    
    def add_message(self, session_id: str, role: str, content: str):
        self.sessions[session_id]["history"].append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        self.sessions[session_id]["updated_at"] = time.time()
        if role == "user" and not self.sessions[session_id]["title"]:
            self.sessions[session_id]["title"] = content[:20]
        if len(self.sessions[session_id]["history"]) > self.max_history:
            self.sessions[session_id]["history"] = self.sessions[session_id]["history"][-self.max_history:]
    
    def get_history(self, session_id: str) -> List[Dict]:
        return self.sessions[session_id]["history"]
    
    def get_all_sessions(self) -> List[Dict]:
        sessions = []
        for session_id, data in self.sessions.items():
            sessions.append({
                "id": session_id,
                "title": data.get("title", ""),
                "created_at": data.get("created_at", 0),
                "updated_at": data.get("updated_at", 0)
            })
        sessions.sort(key=lambda x: x["updated_at"], reverse=True)
        return sessions
    
    def delete_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def get_context_prompt(self, session_id: str) -> str:
        history = self.get_history(session_id)
        if not history:
            return ""
        
        context = "对话历史：\n"
        for msg in history:
            role = "用户" if msg["role"] == "user" else "助手"
            context += f"{role}: {msg['content']}\n"
        return context
    
    def clear_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]

conversation_manager = ConversationManager(max_history=10)
