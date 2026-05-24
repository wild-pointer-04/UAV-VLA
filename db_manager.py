# import sqlite3
# import json
# from typing import List, Dict

# DB_NAME = "uav_tasks.db"

# def init_db():
#     """初始化数据库架构"""
#     conn = sqlite3.connect(DB_NAME)
#     cursor = conn.cursor()
#     cursor.execute('''
#         CREATE TABLE IF NOT EXISTS history_tasks (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             task_name TEXT NOT NULL,
#             command TEXT NOT NULL,
#             targets TEXT,
#             mission_code TEXT,
#             image_path TEXT,
#             waypoints TEXT,
#             create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         )
#     ''')
#     conn.commit()
#     conn.close()

# def insert_task(task_name: str, command: str, targets: list, mission_code: str, image_path: str, waypoints: list):
#     """持久化存储任务数据"""
#     conn = sqlite3.connect(DB_NAME)
#     cursor = conn.cursor()
#     # 序列化列表为 JSON 字符串
#     targets_str = json.dumps(targets)
#     waypoints_str = json.dumps(waypoints)
    
#     cursor.execute('''
#         INSERT INTO history_tasks (task_name, command, targets, mission_code, image_path, waypoints)
#         VALUES (?, ?, ?, ?, ?, ?)
#     ''', (task_name, command, targets_str, mission_code, image_path, waypoints_str))
#     conn.commit()
#     conn.close()

# def get_all_tasks() -> List[Dict]:
#     """获取所有记录"""
#     conn = sqlite3.connect(DB_NAME)
#     conn.row_factory = sqlite3.Row 
#     cursor = conn.cursor()
#     cursor.execute('SELECT * FROM history_tasks ORDER BY id DESC')
#     rows = cursor.fetchall()
#     conn.close()
    
#     result = []
#     for row in rows:
#         result.append({
#             "id": row["id"],
#             "task_name": row["task_name"],
#             "command": row["command"],
#             "targets": row["targets"],
#             "mission_code": row["mission_code"],
#             "image_path": row["image_path"],
#             "waypoints": row["waypoints"],
#             "create_time": row["create_time"]
#         })
#     return result

# # 模块导入时自动执行
# init_db()

"""
db_manager.py
=============
数据库管理模块（扩展版）

相比原版新增：
  - history_tasks 表增加两列：
      ros2_script_path TEXT   —— 生成的 ROS2 控制脚本文件路径
      plan_file_path   TEXT   —— 生成的 QGC .plan 文件路径
  - 新增 update_task_export_paths()：在任务生成后补写导出路径
  - 使用 ALTER TABLE 兼容旧数据库（已存在的库自动升级，无需删库重建）
"""

import sqlite3
import json
from typing import List, Dict, Optional

DB_NAME = "uav_tasks.db"


# ──────────────────────────────────────────────────────────────────────────────
#  初 始 化 / 升 级
# ──────────────────────────────────────────────────────────────────────────────

def init_db():
    """初始化数据库并自动升级旧表结构（新增导出路径两列）。"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 建表（首次运行）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history_tasks (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name        TEXT    NOT NULL,
            command          TEXT    NOT NULL,
            targets          TEXT,
            mission_code     TEXT,
            image_path       TEXT,
            waypoints        TEXT,
            ros2_script_path TEXT,
            plan_file_path   TEXT,
            create_time      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 兼容旧数据库：字段不存在时自动 ALTER TABLE 添加
    existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(history_tasks)")}
    for col, col_type in [
        ("ros2_script_path", "TEXT"),
        ("plan_file_path",   "TEXT"),
    ]:
        if col not in existing_cols:
            cursor.execute(f"ALTER TABLE history_tasks ADD COLUMN {col} {col_type}")

    conn.commit()
    conn.close()


# ──────────────────────────────────────────────────────────────────────────────
#  写 入
# ──────────────────────────────────────────────────────────────────────────────

def insert_task(
    task_name: str,
    command: str,
    targets: list,
    mission_code: str,
    image_path: str,
    waypoints: list,
    ros2_script_path: str = "",
    plan_file_path: str = "",
) -> int:
    """
    持久化存储任务数据，返回新插入记录的 id。

    Parameters
    ----------
    ros2_script_path : 生成的 ROS2 脚本文件路径（可选，事后通过 update 写入）
    plan_file_path   : 生成的 QGC .plan 文件路径（可选，事后通过 update 写入）
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    targets_str   = json.dumps(targets,   ensure_ascii=False)
    waypoints_str = json.dumps(waypoints, ensure_ascii=False)

    cursor.execute('''
        INSERT INTO history_tasks
            (task_name, command, targets, mission_code, image_path, waypoints,
             ros2_script_path, plan_file_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (task_name, command, targets_str, mission_code, image_path,
          waypoints_str, ros2_script_path, plan_file_path))

    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def update_task_export_paths(
    task_id: int,
    ros2_script_path: str,
    plan_file_path: str,
) -> None:
    """任务生成后，补写两类导出文件的磁盘路径。"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE history_tasks
           SET ros2_script_path = ?,
               plan_file_path   = ?
         WHERE id = ?
    ''', (ros2_script_path, plan_file_path, task_id))
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────────────────────────────────────
#  读 取
# ──────────────────────────────────────────────────────────────────────────────

def get_all_tasks() -> List[Dict]:
    """获取全部历史任务（按 id 倒序）。"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM history_tasks ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append({
            "id":               row["id"],
            "task_name":        row["task_name"],
            "command":          row["command"],
            "targets":          row["targets"],
            "mission_code":     row["mission_code"],
            "image_path":       row["image_path"],
            "waypoints":        row["waypoints"],
            "ros2_script_path": row["ros2_script_path"] or "",
            "plan_file_path":   row["plan_file_path"]   or "",
            "create_time":      row["create_time"],
        })
    return result


def get_task_by_id(task_id: int) -> Optional[Dict]:
    """按 id 获取单条任务记录。"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM history_tasks WHERE id = ?', (task_id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None
    return {
        "id":               row["id"],
        "task_name":        row["task_name"],
        "command":          row["command"],
        "targets":          row["targets"],
        "mission_code":     row["mission_code"],
        "image_path":       row["image_path"],
        "waypoints":        row["waypoints"],
        "ros2_script_path": row["ros2_script_path"] or "",
        "plan_file_path":   row["plan_file_path"]   or "",
        "create_time":      row["create_time"],
    }


# 模块导入时自动执行
init_db()