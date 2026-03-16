import sqlite3
import time
import uuid
from typing import Optional, List, Dict
from dotenv import load_dotenv
import os

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "./customer_data.db")

def init_feedback_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            question TEXT,
            answer TEXT,
            rating INTEGER,
            feedback_type TEXT,
            comment TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_feedback(session_id: str, question: str, answer: str, rating: int, 
                 feedback_type: str = "helpful", comment: str = "") -> str:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    feedback_id = str(uuid.uuid4())
    created_at = time.strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute(
        "INSERT INTO feedback VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (feedback_id, session_id, question, answer, rating, feedback_type, comment, created_at)
    )
    
    conn.commit()
    conn.close()
    
    return feedback_id

def get_feedback_list(limit: int = 50) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, session_id, question, answer, rating, feedback_type, comment, created_at FROM feedback ORDER BY created_at DESC LIMIT ?",
        (limit,)
    )
    
    results = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": r[0],
            "session_id": r[1],
            "question": r[2],
            "answer": r[3],
            "rating": r[4],
            "feedback_type": r[5],
            "comment": r[6],
            "created_at": r[7]
        }
        for r in results
    ]

def get_negative_feedback(limit: int = 20) -> List[Dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, session_id, question, answer, rating, feedback_type, comment, created_at FROM feedback WHERE rating <= 1 ORDER BY created_at DESC LIMIT ?",
        (limit,)
    )
    
    results = cursor.fetchall()
    conn.close()
    
    return [
        {
            "id": r[0],
            "session_id": r[1],
            "question": r[2],
            "answer": r[3],
            "rating": r[4],
            "feedback_type": r[5],
            "comment": r[6],
            "created_at": r[7]
        }
        for r in results
    ]

init_feedback_db()
