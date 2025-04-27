import sqlite3
from typing import Optional, List, Dict, Any

DB_PATH = "chat_history.db"  

def init_db():
    """Инициализация базы данных и таблицы."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_tg_id INTEGER,
            message TEXT,
            decision TEXT,
            reasoning TEXT,           -- Reasoning от супервизора
            tx_reasoning TEXT,       -- Reasoning из транзакции
            to_address TEXT,
            value REAL,
            currency TEXT
        )
    ''')
    conn.commit()
    conn.close()


def save_message(
    user_tg_id: int,
    message: str,
    decision: str,
    reasoning: str,
    tx_reasoning: Optional[str] = None,
    to_address: Optional[str] = None,
    value: Optional[float] = None,
    currency: Optional[str] = None
):
    """Сохраняет сообщение пользователя и ответ супервизора."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO chat_history (user_tg_id, message, decision, reasoning, tx_reasoning, to_address, value, currency)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_tg_id, message, decision, reasoning, tx_reasoning, to_address, value, currency))
    conn.commit()
    conn.close()


def get_last_chat_history(user_tg_id: int, limit: int = 3) -> List[Dict[str, Any]]:
    """Получает последние сообщения для указанного user_tg_id."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT message, decision, reasoning, tx_reasoning, to_address, value, currency
        FROM chat_history
        WHERE user_tg_id = ?
        ORDER BY id DESC
        LIMIT ?
    ''', (user_tg_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "message": row[0],
            "decision": row[1],
            "reasoning": row[2],     # reasoning от супервизора
            "tx_reasoning": row[3],  # reasoning из транзакции
            "to_address": row[4],
            "value": row[5],
            "currency": row[6]
        }
        for row in rows
    ]
