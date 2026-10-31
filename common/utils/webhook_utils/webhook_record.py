# common/webhook_storage.py
import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "webhook_data.db"


def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # 返回字典格式
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS webhook_events (
            event_id TEXT PRIMARY KEY,
            last_file_id TEXT,
            last_file_name TEXT,
            last_payload TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')

    conn.commit()
    conn.close()


def save_event(event_id: str, file_id: str, file_name: str, payload: dict):
    """保存或更新事件"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    payload_json = json.dumps(payload, ensure_ascii=False)

    # 检查是否存在
    cursor.execute("SELECT event_id FROM webhook_events WHERE event_id = ?", (event_id,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute('''
            UPDATE webhook_events 
            SET last_file_id = ?, last_file_name = ?, last_payload = ?, updated_at = ?
            WHERE event_id = ?
        ''', (file_id, file_name, payload_json, now, event_id))
    else:
        cursor.execute('''
            INSERT INTO webhook_events (event_id, last_file_id, last_file_name, last_payload, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (event_id, file_id, file_name, payload_json, now, now))

    conn.commit()
    conn.close()


def get_event(event_id: str):
    """获取事件记录"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM webhook_events WHERE event_id = ?", (event_id,))
    row = cursor.fetchone()

    conn.close()

    if row:
        return {
            'event_id': row['event_id'],
            'file_id': row['last_file_id'],
            'file_name': row['last_file_name'],
            'payload': json.loads(row['last_payload']),
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        }
    return None


def get_all_events():
    """获取所有事件"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT event_id, last_file_name, updated_at FROM webhook_events ORDER BY updated_at DESC")
    rows = cursor.fetchall()

    conn.close()

    return [{'event_id': row['event_id'], 'file_name': row['last_file_name'], 'updated_at': row['updated_at']} for row
            in rows]


def clear_all_events():
    """清空所有事件（测试用）"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM webhook_events")
    conn.commit()
    conn.close()


def delete_event(event_id: str):
    """删除指定事件"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM webhook_events WHERE event_id = ?", (event_id,))
    conn.commit()
    conn.close()


# 初始化数据库
init_db()