import sqlite3
import json
from typing import List, Dict

DB_NAME = "uav_tasks.db"

def init_db():
    """初始化数据库架构"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT NOT NULL,
            command TEXT NOT NULL,
            targets TEXT,
            mission_code TEXT,
            image_path TEXT,
            waypoints TEXT,
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def insert_task(task_name: str, command: str, targets: list, mission_code: str, image_path: str, waypoints: list):
    """持久化存储任务数据"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # 序列化列表为 JSON 字符串
    targets_str = json.dumps(targets)
    waypoints_str = json.dumps(waypoints)
    
    cursor.execute('''
        INSERT INTO history_tasks (task_name, command, targets, mission_code, image_path, waypoints)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (task_name, command, targets_str, mission_code, image_path, waypoints_str))
    conn.commit()
    conn.close()

def get_all_tasks() -> List[Dict]:
    """获取所有记录"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM history_tasks ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        result.append({
            "id": row["id"],
            "task_name": row["task_name"],
            "command": row["command"],
            "targets": row["targets"],
            "mission_code": row["mission_code"],
            "image_path": row["image_path"],
            "waypoints": row["waypoints"],
            "create_time": row["create_time"]
        })
    return result

# 模块导入时自动执行
init_db()