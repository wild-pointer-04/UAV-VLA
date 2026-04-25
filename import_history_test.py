# import_history.py
import db_manager
import os

# 假设你的 mission 都在 created_missions 文件夹下，名字是 mission1.txt 到 mission30.txt
for i in range(1, 31):
    file_path = f"created_missions/mission{i}.txt"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
            
        # 写入数据库
        db_manager.insert_task(
            task_name=f"验证任务 #{i}",
            command="寻找建筑物并环绕飞行100m", # 这里可以根据实际情况填
            targets=["building"],
            mission_code=code
        )
print("30 个历史任务已成功导入数据库！")