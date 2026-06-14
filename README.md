<div align="center">

# UAV-VLA：基于大模型的视觉无人机智能指令生成系统

**Visual UAV Intelligent Instruction Generation System Based on Large Vision-Language Models**

<p>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white">
  <img alt="Flask" src="https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white">
  <img alt="PyTorch" src="https://img.shields.io/badge/PyTorch-2.4-EE4C2C?logo=pytorch&logoColor=white">
  <img alt="ZhipuAI" src="https://img.shields.io/badge/ZhipuAI-GLM--4V-1A73E8">
  <img alt="ArduPilot" src="https://img.shields.io/badge/ArduPilot-MissionPlanner-FF6F00">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-green">
</p>

> 一句自然语言指令 + 一张卫星俯视图 → 可在 Mission Planner 中直接执行的无人机任务脚本

**作者**：吕鹤冉　|　**学校**：兰州理工大学　计算机与人工智能学院　软件工程二班
**毕业设计选题**：基于大模型的视觉无人机智能指令生成系统设计 (2026 届)
**仓库地址**：<https://github.com/wild-pointer-04/UAV-VLA>　|　**论文参考**：<https://arxiv.org/abs/2501.05014>

</div>

---

## 目录

- [1. 项目简介](#1-项目简介)
- [2. 核心特性](#2-核心特性)
- [3. 系统架构](#3-系统架构)
- [4. 技术栈](#4-技术栈)
- [5. 目录结构](#5-目录结构)
- [6. 快速开始](#6-快速开始)
- [7. 使用指南](#7-使用指南)
  - [7.1 Web 应用方式 (推荐)](#71-web-应用方式-推荐)
  - [7.2 命令行批量方式](#72-命令行批量方式)
  - [7.3 实验复现 (论文级评估)](#73-实验复现-论文级评估)
- [8. 数据集与基准 (Benchmark)](#8-数据集与基准-benchmark)
- [9. 核心算法流程](#9-核心算法流程)
- [10. 实验结果](#10-实验结果)
- [11. API 文档](#11-api-文档)
- [12. 配置说明](#12-配置说明)
- [13. 常见问题 (FAQ)](#13-常见问题-faq)
- [14. 致谢与引用](#14-致谢与引用)
- [15. 许可证](#15-许可证)

---

## 1. 项目简介

**UAV-VLA** (Vision-Language-Action) 是一套面向大尺度航空任务规划的视觉-语言-动作智能系统。它将**卫星图像理解**、**视觉语言大模型 (VLM)** 与**任务级大语言模型 (LLM)** 三者深度耦合，使得用户可以通过最朴素的中文/英文自然语言指令——

> *"为四旋翼无人机规划一条飞行路径，在 100m 高度环绕图中所有建筑物巡视一周后返航降落。"*

——配合一张卫星俯视图，**端到端**自动生成可直接被 ArduPilot Mission Planner 解析与执行的任务航迹脚本 (`.waypoint`)。整套系统将传统上需要资深操作员手动点选航点的工作流，压缩到约 **5 分 24 秒**完成，效率较人工提升 **6.5 倍**，并在 K-Nearest Neighbors 评估下保持了 **34.22 m** 的目标定位均值误差。

本项目同时是吕鹤冉同学 2026 届本科毕业设计的实现工程，在 UAV-VLA  的基础上构建了**软件工程层**——以 Flask + SQLite 为底座的 Web 应用，将算法管线封装为面向最终用户的可视化交互系统。

---

## 2. 核心特性

| 特性 | 说明 |
| :--- | :--- |
| 🧠 **多模态智能感知** | 集成智谱 GLM-4V-Plus 视觉大模型，可对卫星遥感图像中的建筑、村庄、机场、池塘、桥梁、道路等地物进行语义级目标检测 |
| 🗣️ **自然语言任务解析** | 通过 GLM-4 解析任务描述，自动抽取目标类型、动作约束 (高度、巡视方式、返航条件) 并生成结构化任务计划 |
| 🗺️ **像素-地理坐标映射** | 基于卫星图四角经纬度元数据，将 VLM 输出的归一化像素坐标精准映射到 WGS-84 经纬度 |
| 🛩️ **ArduPilot 脚本生成** | 输出符合 ArduPilot `arm throttle / takeoff / mode guided / mode rtl / disarm` 伪指令格式的任务文件 |
| 🌐 **Web 全栈应用** | Flask 后端 + Jinja2 模板前端，支持任务创建、上传、可视化、历史回溯与脚本下载 |
| 🗄️ **任务持久化** | SQLite 存储完整任务流水，含指令、图像、检测目标、航点序列、生成脚本与状态 |
| 🔬 **可复现的实验体系** | 提供 `experiments/main.py` 一键运行 KNN/DTW/插值 三种误差度量与轨迹长度对比 |
| 📊 **标准化基准** | 内置 30 张地理参考卫星图基准集 (UAV-VLPA-nano-30) 与 Mission Planner 人工标注真值 |

---

## 3. 系统架构

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              用户层 (Browser)                                  │
│            自然语言指令          +          卫星图像           +    基准 ID     │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │ HTTP POST /task/create
┌────────────────────────────────────▼─────────────────────────────────────────┐
│                        Web 应用层 (Flask · app.py)                           │
│   路由调度 · 文件接收 · 表单校验 · 模板渲染 · 任务编排 · 静态资源服务            │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │
┌────────────────────────────────────▼─────────────────────────────────────────┐
│                  算法服务层 (webapp/algorithm_service.py)                     │
│  ┌────────────────┐  ┌─────────────────┐  ┌────────────────┐  ┌───────────┐  │
│  │ parse_         │→ │ locate_         │→ │ transform_     │→ │ generate_ │  │
│  │ instruction()  │  │ objects()       │  │ coords()       │  │ script()  │  │
│  └────────────────┘  └─────────────────┘  └────────────────┘  └───────────┘  │
│       目标类型抽取        视觉目标检测           坐标映射          航迹脚本      │
└────────┬────────────────────┬──────────────────────┬──────────────┬─────────┘
         │                    │                      │              │
         ▼                    ▼                      ▼              ▼
┌──────────────┐    ┌──────────────────┐    ┌───────────────┐  ┌──────────┐
│  GLM-4       │    │  GLM-4V-Plus     │    │ recalculate_  │  │ draw_    │
│  (LLM 任务   │    │  (VLM 视觉        │    │ to_latlon.py  │  │ circles. │
│   规划)      │    │   检测)           │    │ (经纬换算)     │  │ py (可视)│
└──────────────┘    └──────────────────┘    └───────────────┘  └──────────┘
         │                    │                      │              │
         └────────────────────┴──────────────────────┴──────────────┘
                                     │
┌────────────────────────────────────▼─────────────────────────────────────────┐
│                        持久层 (webapp/db.py · SQLite)                         │
│        tasks 表: id · 时间 · 指令 · 原图 · 目标类型 · 航点 · 脚本路径 · 状态     │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
                ┌────────────────────────────────────────┐
                │  输出物: .waypoint 脚本  +  标注可视化图 │
                │  → ArduPilot Mission Planner 直接装载   │
                └────────────────────────────────────────┘
```

---

## 4. 技术栈

| 层次 | 技术 / 组件 | 版本 |
| :--- | :--- | :--- |
| **大模型** | ZhipuAI GLM-4V-Plus (视觉) · GLM-4 (语言) | API 2024 |
| **深度学习** | PyTorch · Transformers · Accelerate · BitsAndBytes | 2.4.1 / 4.45.2 |
| **Web 框架** | Flask · Werkzeug · Jinja2 | 3.0.3 |
| **LLM 编排** | LangChain · LangChain-OpenAI | 0.3.x |
| **图像处理** | Pillow · OpenCV (隐式经 Pillow) · Matplotlib | 10.4 / 3.10 |
| **数据科学** | NumPy · Pandas · SciPy · scikit-learn (KNN) | 1.26 / 2.2 |
| **距离度量** | FastDTW (Dynamic Time Warping) | 0.3.4 |
| **数据库** | SQLite (内置) · SQLAlchemy (备选 ORM) | 3.x / 2.0 |
| **HTTP 客户端** | Requests · HTTPX · aiohttp | 2.32 / 0.27 |
| **运行环境** | Python 3.10+ · CUDA 12.1 (GPU 加速可选) | — |
| **目标平台** | ArduPilot Mission Planner | 1.3+ |

> 完整依赖清单详见 [`requirements.txt`](./requirements.txt)。

---

## 5. 目录结构

```
UAV-VLA/
├── app.py                            # ★ Flask Web 应用入口
├── config.py                         # 全局配置 / Prompt 模板 / 路径常量
├── requirements.txt                  # Python 依赖锁
├── README.md                         # 本文件
├── LICENSE                           # MIT
├── UAV_VLA_Title_image.png           # 系统题图
│
├── run_vlm.py                        # ★ 调用 GLM-4V 对基准图批量检测建筑
├── run_vlm_yuan.py                   #  VLM 调用版本
├── generate_plans.py                 # ★ 调用 GLM-4 生成任务脚本
├── generate_plans_yuan.py            #  任务规划版本
│
├── parser_for_coordinates.py         # VLM 文本输出 → 坐标元组解析
├── recalculate_to_latlon.py          # 百分比坐标 → 经纬度坐标转换
├── draw_circles.py                   # 在原图上绘制目标点与航迹连线
├── draw_circles_yaun.py              # 原版可视化模块
├── hexindaim.py                      # 核心算法辅助脚本
├── test.py                           # 单元/集成测试入口
│
├── identified_points.txt             # VLM 检测结果缓存 (像素坐标)
│
├── webapp/                           # ───── Web 应用模块 ─────
│   ├── algorithm_service.py          # 4 大算法函数的薄封装
│   ├── db.py                         # SQLite 任务持久化
│   ├── tasks.db                      # SQLite 数据文件
│   ├── templates/
│   │   ├── new_task.html             # 任务创建页
│   │   ├── task_detail.html          # 任务详情/结果展示页
│   │   └── history.html              # 历史任务列表
│   ├── static/
│   │   ├── uploads/                  # 用户上传原图
│   │   └── annotated/                # 算法标注后的可视化图
│   └── generated_scripts/            # 生成的 .waypoint 脚本
│
├── benchmark-UAV-VLPA-nano-30/       # ───── 标准基准数据集 ─────
│   ├── images/                       # 30 张地理参考卫星图
│   ├── images_yuan/                  # 原始基准副本
│   ├── img_lat_long_data.txt         # 每张图四角经纬度
│   ├── parsed_coordinates.csv        # 角点坐标 (NW/SE) 结构化版
│   ├── mission_planner_data/         # Mission Planner 人工任务真值
│   ├── identified_images_mp/         # MP 真值可视化
│   └── ...
│
├── experiments/                      # ───── 论文实验流水线 ─────
│   ├── main.py                       # ★ 一键执行全部实验
│   ├── home_pose.py                  # 起飞点提取
│   ├── VLM_data.py                   # VLM 坐标转换为绝对经纬度
│   ├── mp_data.py                    # MP 真值数据预处理
│   ├── traj_calc.py                  # 轨迹长度计算
│   ├── rmse_data.py                  # KNN / DTW / Interpolation RMSE
│   ├── graphs.py                     # 实验图表绘制
│   ├── identified_images.py          # 标注图批量生成
│   └── results/                      # 实验输出
│
├── created_missions/                 # generate_plans.py 输出目录
├── identified_new_data/              # run_vlm.py 标注图输出目录
└── identified_new_data_1/            # 备用输出目录
```

---

## 6. 快速开始

### 6.1 环境要求

- Python **3.10+**
- 至少 **8 GB** 内存 (使用云端 API 模式)；若启用本地 VLM，则需 **12 GB+ VRAM** GPU
- 已注册 [智谱 AI 开放平台](https://open.bigmodel.cn/) 并获取 API Key

### 6.2 安装

```bash
# 1. 克隆仓库
git clone https://github.com/wild-pointer-04/UAV-VLA.git
cd UAV-VLA

# 2. 建议使用虚拟环境
python -m venv venv_uav
# Windows
venv_uav\Scripts\activate
# Linux / macOS
source venv_uav/bin/activate

# 3. 安装依赖
pip install -r requirements.txt
```

### 6.3 配置 API Key

> ⚠️ **安全提示**：请**勿**将 API Key 硬编码进源码或提交到 Git。

```bash
# Windows (cmd)
set ZHIPU_API_KEY=your_zhipu_api_key_here

# Windows (PowerShell)
$env:ZHIPU_API_KEY="your_zhipu_api_key_here"

# Linux / macOS
export ZHIPU_API_KEY="your_zhipu_api_key_here"
```

### 6.4 运行 Web 应用

```bash
python app.py
```

应用将启动于 <http://127.0.0.1:5000>。打开浏览器访问：

- **创建任务**：<http://127.0.0.1:5000/task/new>
- **历史任务**：<http://127.0.0.1:5000/history>

---

## 7. 使用指南

### 7.1 Web 应用方式 (推荐)

1. 浏览器访问 `/task/new`
2. 填写**任务指令** (中/英文皆可)，例如：
   > *巡视图中所有建筑物，巡视高度 80 米，巡视完毕后自动返航降落。*
3. 上传**一张俯视卫星图** (`.jpg` / `.png`，单文件 < 20 MB)
4. (可选) 填写**基准图编号**：若上传的是基准集 (`benchmark-UAV-VLPA-nano-30/images/`) 中的图，填写其编号 (如 `12`)，系统会使用该图的真实角点经纬度，输出**绝对**地理坐标的航迹；否则只输出归一化坐标
5. 提交后系统自动跳转到任务详情页，展示：
   - 解析出的目标类型
   - 标注后的可视化图
   - 航点经纬度列表
   - 可下载的 `.waypoint` 脚本

### 7.2 命令行批量方式

对基准集中的全部 30 张图进行视觉检测：

```bash
python run_vlm.py
# 输出 → identified_points.txt
```

读取检测结果并生成任务脚本：

```bash
python generate_plans.py
# 输出 → created_missions/mission{i}.txt
# 输出 → identified_new_data/identified{i}.jpg (标注图)
```

### 7.3 实验复现 (论文级评估)

```bash
cd experiments
python main.py
```

`experiments/main.py` 将按如下顺序自动执行：

| 步骤 | 模块 | 产出 |
| :--- | :--- | :--- |
| 1. 起飞点提取 | `home_pose.py` | `home_position.txt` |
| 2. VLM 坐标转换 | `VLM_data.py` | `VLM_coordinates.txt` |
| 3. MP 真值整理 | `mp_data.py` | `mp_coordinates.txt` |
| 4. 轨迹长度计算 | `traj_calc.py` | `traj_length.txt` |
| 5. RMSE 计算 (KNN/DTW/插值) | `rmse_data.py` | `rmse.txt` |
| 6. 绘图比较 | `graphs.py` | 轨迹柱状图 · RMSE 箱型图 |
| 7. VLM/MP 标注图批量生成 | `identified_images.py` | `identified_images_VLM/` · `identified_images_mp/` |

---

## 8. 数据集与基准 (Benchmark)

**UAV-VLPA-nano-30** 是本系统的标准评估基准，包含 30 张来自不同地理区域的高分辨率俯视卫星图。

| 项 | 内容 |
| :--- | :--- |
| 图像数量 | 30 张 |
| 图像规格 | 512 × 512 px (`.jpg`) |
| 地理元数据 | 每张图的 NW/SE 角点经纬度，存于 `parsed_coordinates.csv` |
| 真值任务 | 由经验丰富的 Mission Planner 操作员手工标注，存于 `mission_planner_data/waypoints/` |
| 目标类别 | building · village · airfield · stadium · pond · bridge · road · roundabout |

`parsed_coordinates.csv` 字段定义：

| 列名 | 含义 |
| :--- | :--- |
| `Image` | 图像文件名 (如 `1.jpg`) |
| `NW Corner Lat` / `NW Corner Long` | 西北角经纬度 |
| `SE Corner Lat` / `SE Corner Long` | 东南角经纬度 |

---

## 9. 核心算法流程

### 阶段 1 · 自然语言指令解析 (`parse_instruction`)

```python
# 输入: "巡视图中所有建筑物，巡视高度 80 米..."
# 输出: ["building"]   # 抽取的目标类型集合
```

通过关键词匹配 + GLM-4 LLM 协同从自然语言中抽取**目标类型**与**任务约束**。

### 阶段 2 · 视觉目标检测 (`locate_objects`)

```python
# 调用 GLM-4V-Plus，Prompt 触发 Grounding 模式
# 输入: 卫星图 + 目标类型 + 用户指令
# 输出: [(x1, y1), (x2, y2), ...]  # 像素坐标列表
```

关键技术：
- **Base64 图像编码** 直传云端 VLM
- **归一化坐标修正**：GLM-4V 输出 [0, 1000] 归一化坐标，自动按图像实际分辨率 (512) 反缩放
- **多正则容错解析**：兼容 `[x,y]`、`(x,y)`、`{"x":x,"y":y}` 三种返回格式

### 阶段 3 · 像素 → 经纬度映射 (`transform_coords`)

给定图像的角点经纬度 (NW, SE) 与目标的像素百分比 (x%, y%)：

### 阶段 4 · 任务脚本生成 (`generate_script`)

调用 GLM-4 LLM，注入 ArduPilot 命令集与示例 (Few-shot)，输出形如：

```
arm throttle
takeoff 30
mode guided 43.237763722 -85.792243144 100
mode guided 43.237765234 -85.792243142 100
mode circle
mode rtl
disarm
```

可直接被 Mission Planner 装载执行。

---

## 10. 实验结果

### 10.1 推理速度

| 系统 | 30 张图任务规划耗时 | 加速比 |
| :--- | :---: | :---: |
| 资深人工操作员 | ~35 min | 1.0× |
| **UAV-VLA (本系统)** | **5 min 24 s** | **6.5×** |

### 10.2 误差对比 (单位: 米)

| 度量方式 | Mean | Median | Max |
| :--- | :---: | :---: | :---: |
| **KNN Error** | **34.22** | 26.04 | 112.49 |
| DTW RMSE | 307.27 | 318.46 | 644.57 |
| Linear Interpolation RMSE | 409.54 | 395.59 | 727.94 |

> KNN 度量最为合理，因 VLM 生成航点为**离散目标点**而非连续轨迹采样，DTW/插值会引入轨迹起止对齐误差。

### 10.3 轨迹长度差异

UAV-VLA 生成轨迹与人工真值的平均长度差异为 **22%**，主要源于 VLM 检测顺序与人工巡视路径偏好不同。

---

## 11. API 文档

### Web API (Flask)

| Method | Endpoint | 说明 | 请求参数 |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | 首页，重定向至任务创建页 | — |
| `GET` | `/task/new` | 任务创建页面 (HTML) | — |
| `POST` | `/task/create` | 创建并执行任务 | `instruction` (str) · `image` (file) · `benchmark_image_id` (str, 可选) |
| `GET` | `/tasks` | 历史任务列表 (JSON) | — |
| `GET` | `/task/<id>` | 任务详情 (JSON) | — |
| `GET` | `/task/<id>/view` | 任务详情页面 (HTML) | — |
| `GET` | `/task/<id>/download` | 下载生成的 `.waypoint` 脚本 | — |
| `GET` | `/history` | 历史任务页面 (HTML) | — |

### 算法层 4 大核心函数

```python
from webapp.algorithm_service import (
    parse_instruction,    # str → List[str]    解析目标类型
    locate_objects,       # (image_path, targets, instruction) → List[(x, y)]  视觉检测
    transform_coords,     # (pixels, image_path, benchmark_id) → List[Waypoint]  坐标变换
    generate_script,      # (waypoints, output_dir) → str  脚本生成
)
```

---

## 12. 配置说明

**`config.py`** 中可调整的关键参数：

| 参数 | 默认值 | 含义 |
| :--- | :--- | :--- |
| `NUMBER_OF_SAMPLES` | `30` | 基准集图像数 |
| `BENCHMARK_DIR` | `benchmark-UAV-VLPA-nano-30` | 基准集根目录 |
| `IMAGES_DIR` | `{BENCHMARK_DIR}/images` | 基准图像目录 |
| `COORDINATES_FILE` | `{BENCHMARK_DIR}/parsed_coordinates.csv` | 角点经纬度 CSV |
| `MISSION_OUTPUT_DIR` | `created_missions` | 任务脚本输出目录 |
| `IDENTIFIED_DATA_DIR` | `identified_new_data` | 标注图输出目录 |
| `step_1_template` | — | LLM 目标抽取 Prompt 模板 |
| `step_3_template` | — | LLM 任务规划 Prompt 模板 |
| `command` | — | 默认任务指令 |

---

## 13. 常见问题 (FAQ)

<details>
<summary><b>Q1: 启动时报 <code>ZHIPU_API_KEY is not configured</code> 怎么办？</b></summary>

请按照 [6.3 配置 API Key](#63-配置-api-key) 章节设置环境变量，并**重启终端**让其生效。

</details>

<details>
<summary><b>Q2: VLM 返回坐标解析失败？</b></summary>

可能原因：
- API 限流或网络中断 → 重试
- Prompt 不够具体 → 调整 `run_vlm.py` 中的 `query` 模板
- 图像分辨率与模型默认归一化尺度不一致 → 修改 `_rescale_coordinates` 中的 `target_size`

</details>

<details>
<summary><b>Q3: 上传非基准集图像时航点是错的？</b></summary>

非基准图缺少四角经纬度元数据，系统会回退为**像素百分比**伪坐标用于展示。若需绝对经纬度，请提供：
1. 该图四角的真实 GPS 坐标，并追加到 `parsed_coordinates.csv`；
2. 或在前端 `benchmark_image_id` 字段填写已注册的图像编号。

</details>

<details>
<summary><b>Q4: 如何替换为其他大模型？</b></summary>

- 视觉模型：修改 `run_vlm.py::VLMRunner` 的 `self.model` 与 `client` 初始化
- 语言模型：修改 `generate_plans.py::ZhipuLLM` 替换为 OpenAI / Anthropic / 本地模型 (vLLM/Ollama) 即可

</details>

<details>
<summary><b>Q5: 生成的 .waypoint 文件如何在 Mission Planner 中加载？</b></summary>

Mission Planner → `FLIGHT PLAN` → `Load WP File` → 选择 `webapp/generated_scripts/mission_*.waypoint`，加载后即可看到航点序列叠加在地图上。

</details>

---

## 14. 致谢与引用

### 上游研究

本毕业设计在以下研究基础上完成，特此致谢：

```bibtex
@inproceedings{10.5555/3721488.3721725,
  author    = {Sautenkov, Oleg and Yaqoot, Yasheerah and Lykov, Artem and
               Mustafa, Muhammad Ahsan and Tadevosyan, Grik and Akhmetkazy, Aibek
               and Altamirano Cabrera, Miguel and Martynov, Mikhail and Karaf, Sausar
               and Tsetserukou, Dzmitry},
  title     = {UAV-VLA: Vision-Language-Action System for Large Scale Aerial Mission Generation},
  booktitle = {Proceedings of the 2025 ACM/IEEE International Conference on Human-Robot Interaction (HRI '25)},
  year      = {2025},
  pages     = {1588--1592},
  publisher = {IEEE Press},
  location  = {Melbourne, Australia},
  keywords  = {drone, llm-agents, navigation, path planning, uav, vla, vlm, vlm-agents}
}
```

### 引用本项目

```bibtex
@misc{lhr2026uavvla,
  author = {Lyu, Heran},
  title  = {基于大模型的视觉无人机智能指令生成系统设计},
  school = {兰州理工大学计算机与人工智能学院},
  year   = {2026},
  note   = {本科毕业设计},
  url    = {https://github.com/wild-pointer-04/UAV-VLA}
}
```

### 鸣谢

- **智谱 AI** 提供 GLM-4V-Plus / GLM-4 模型 API
- **ArduPilot** 开源飞控生态
- 兰州理工大学计算机与人工智能学院全体指导教师

---

## 15. 许可证

本项目基于 [MIT License](./LICENSE) 开源，允许商业与非商业使用，但**不对**使用本系统进行的任何无人机飞行行为的安全后果负责。请用户严格遵守所在国家/地区的无人机适航与空域管理法规。

---

<div align="center">

**🚁 一句话，让大模型理解地图，让无人机听懂世界。 🌍**

Made with ❤️ by **吕鹤冉** · Lanzhou University of Technology · Class of 2026

</div>
