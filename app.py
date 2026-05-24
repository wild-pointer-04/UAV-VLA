"""
app.py  ——  SkyOps UAV-VLA 任务控制台（含工业格式导出功能）
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import db_manager
import service_layer
import os
import json

# ── 工业格式导出引擎 ──────────────────────────────────────────────────────────
from flight_exporter import (
    generate_ros2_script,
    generate_qgc_plan,
    save_export_files,
    DEFAULT_ALTITUDE,
    DEFAULT_SPEED,
)

# ── 1. 初始化 ─────────────────────────────────────────────────────────────────
db_manager.init_db()
st.set_page_config(page_title="UAV-VLA 任务控制台", layout="wide")

# ── 全局 CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    div.block-container { padding-top: 2rem; }
    .topbar {
        display: flex; align-items: center; justify-content: space-between;
        padding: 16px 24px; background: #ffffff; border-radius: 12px;
        border: 1px solid #E2E8F0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        margin-bottom: 24px;
    }
    .topbar-left  { display: flex; align-items: center; gap: 16px; }
    .topbar-logo  { font-size: 36px; color: #2563EB; line-height: 1; }
    .topbar-title { font-size: 22px; font-weight: 800; color: #0F172A; line-height: 1.2; }
    .topbar-sub   { font-size: 13px; color: #64748B; font-weight: 500; }
    .topbar-badge {
        display: flex; align-items: center; background: #ECFDF5;
        padding: 6px 14px; border-radius: 20px; border: 1px solid #A7F3D0;
        font-size: 13px; color: #059669; font-weight: 600; gap: 6px;
    }
    .dot { height: 8px; width: 8px; background-color: #10B981; border-radius: 50%; }
    .field-label {
        font-size: 14px; font-weight: 700; color: #475569; margin-right: 12px;
        display: inline-flex; align-items: center;
    }
    .chip {
        display: inline-block; background: #EFF6FF; color: #1D4ED8;
        padding: 4px 14px; border-radius: 20px; font-size: 13px;
        font-weight: 600; margin-right: 8px; border: 1px solid #BFDBFE;
    }
    .stat-card {
        padding: 16px; border-radius: 12px; border: 1px solid;
        text-align: center; transition: all 0.2s ease;
    }
    .stat-card:hover { transform: translateY(-2px); }
    .empty-wrap {
        text-align: center; padding: 60px 20px; margin-top: 10px;
        background: #ffffff; border-radius: 16px; border: 1px dashed #CBD5E1;
    }
    .export-box {
        background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px;
        padding: 20px; margin-top: 8px;
    }
    .export-header {
        font-size: 15px; font-weight: 700; color: #0F172A; margin-bottom: 14px;
        display: flex; align-items: center; gap: 8px;
    }
    .export-desc {
        font-size: 12px; color: #64748B; margin-bottom: 10px; line-height: 1.6;
    }
    .gap { height: 20px; }
</style>
""", unsafe_allow_html=True)

# ── Session State 初始化 ──────────────────────────────────────────────────────
if 'mission_result' not in st.session_state:
    st.session_state.mission_result = None
if 'current_task_id' not in st.session_state:
    st.session_state.current_task_id = None

# ── 顶部导航条 ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="topbar">
    <div class="topbar-left">
        <div class="topbar-logo">✈️</div>
        <div>
            <div class="topbar-title">SkyOps</div>
            <div class="topbar-sub">无人机视觉语言任务控制台</div>
        </div>
    </div>
    <div class="topbar-badge"><span class="dot"></span>系统在线</div>
</div>
""", unsafe_allow_html=True)


# ── 2. 侧边栏：历史任务 ───────────────────────────────────────────────────────
with st.sidebar:
    st.header("📋 历史任务记录")
    try:
        history_tasks = db_manager.get_all_tasks()
    except Exception:
        history_tasks = []

    if not history_tasks:
        st.info("暂无历史任务数据")
    else:
        for record in history_tasks:
            btn_label = f"任务 #{record['id']} - {record['create_time'][11:16]}"
            if st.button(btn_label, key=f"hist_{record['id']}", width="stretch"):
                try:
                    parsed_wps     = json.loads(record['waypoints'])  if isinstance(record['waypoints'], str)  else record['waypoints']
                    parsed_targets = json.loads(record['targets'])     if isinstance(record['targets'],   str)  else record['targets']
                except Exception:
                    parsed_wps, parsed_targets = [], []

                st.session_state.mission_result = {
                    'parsed_targets':    parsed_targets,
                    'mission_code':      record.get('mission_code', ''),
                    'vlm_image_result':  record.get('image_path', ''),
                    'waypoints':         parsed_wps,
                    'ros2_script_path':  record.get('ros2_script_path', ''),
                    'plan_file_path':    record.get('plan_file_path', ''),
                }
                st.session_state.current_task_id = record['id']
                st.rerun()


# ── 3. 主界面 ─────────────────────────────────────────────────────────────────
col1, col2 = st.columns([3, 4], gap="large")

# ── 左栏：任务下发 ────────────────────────────────────────────────────────────
with col1:
    st.subheader("任务下发")
    instruction = st.text_area(
        "输入自然语言指令：",
        "Create a flight plan for the quadcopter to fly around each of the building.",
        height=120,
    )
    uploaded_file = st.file_uploader("上传卫星图像地图", type=['jpg', 'png'])

    # 自定义坐标
    custom_coords = None
    with st.expander("🌐 自定义地图经纬度 (可选)"):
        st.info("如果不填写，系统将自动从预设 CSV 文件中匹配。")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**西北角**")
            nw_lat = st.number_input("纬度 (NW Lat)", value=0.0, format="%.6f")
            nw_lon = st.number_input("经度 (NW Lon)", value=0.0, format="%.6f")
        with c2:
            st.markdown("**东南角**")
            se_lat = st.number_input("纬度 (SE Lat)", value=0.0, format="%.6f")
            se_lon = st.number_input("经度 (SE Lon)", value=0.0, format="%.6f")
        if any([nw_lat, nw_lon, se_lat, se_lon]):
            custom_coords = {"nw": (nw_lat, nw_lon), "se": (se_lat, se_lon)}

    # 导出参数
    with st.expander("⚙️ 工业导出参数 (可选)"):
        export_altitude = st.slider("飞行高度 (m)", min_value=5, max_value=120, value=int(DEFAULT_ALTITUDE), step=5)
        export_speed    = st.slider("巡航速度 (m/s)", min_value=1, max_value=20, value=int(DEFAULT_SPEED), step=1)

    if st.button("🚀 开始生成飞行计划", width="stretch", type="primary"):
        if not uploaded_file:
            st.error("请先上传卫星图！")
        else:
            os.makedirs("images", exist_ok=True)
            img_path = f"images/temp_{uploaded_file.name}"
            with open(img_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            with st.spinner("系统正在进行 VLM 分析与路径规划..."):
                success, result = service_layer.process_flight_mission(
                    instruction, img_path, custom_coords=custom_coords
                )

            if success:
                waypoints = result.get('waypoints', [])

                # ── 生成双路工业格式文件 ──────────────────────────────────
                ros2_path, plan_path = "", ""
                if waypoints:
                    try:
                        with st.spinner("正在生成 ROS2 控制脚本与 QGC 飞行计划..."):
                            ros2_path, plan_path = save_export_files(
                                waypoints=waypoints,
                                task_id=0,  # 先占位，入库后用 update 补写
                                task_name=uploaded_file.name.split('.')[0],
                                altitude=float(export_altitude),
                                speed=float(export_speed),
                            )
                    except Exception as e:
                        st.warning(f"工业格式导出生成异常（不影响主流程）：{e}")

                # ── 写入数据库 ────────────────────────────────────────────
                task_id = db_manager.insert_task(
                    task_name=f"任务_{uploaded_file.name}",
                    command=instruction,
                    targets=result['parsed_targets'],
                    mission_code=result['mission_code'],
                    image_path=result['vlm_image_result'],
                    waypoints=waypoints,
                    ros2_script_path=ros2_path,
                    plan_file_path=plan_path,
                )

                # 如果文件已生成，用真实 task_id 重命名（可选：保持文件名含 id）
                # 此处直接将路径写库已够用，不再二次重命名。

                result['ros2_script_path'] = ros2_path
                result['plan_file_path']   = plan_path
                st.session_state.mission_result = result
                st.session_state.current_task_id = task_id
                st.success("✅ 任务生成并保存成功！")
            else:
                st.error(f"执行失败: {result}")


# ── 右栏：结果展示 ────────────────────────────────────────────────────────────
with col2:
    if st.session_state.mission_result is not None:
        res = st.session_state.mission_result

        tab1, tab2, tab3, tab4 = st.tabs([
            "🎯 视觉识别结果",
            "💻 飞行指令代码",
            "🗺️ 航线轨迹预览",
            "📦 工业格式导出",   # ← 新增 Tab
        ])

        # ── Tab 1: 视觉识别 ───────────────────────────────────────────────
        with tab1:
            targets = res.get("parsed_targets", [])
            if targets:
                chips = "".join(
                    f'<span class="chip">{t}</span>'
                    for t in (targets if isinstance(targets, list) else [targets])
                )
                st.markdown(
                    f'<div style="margin-bottom:18px;"><span class="field-label">识别目标：</span>{chips}</div>',
                    unsafe_allow_html=True,
                )
            img_p = res.get("vlm_image_result", "")
            if img_p and os.path.exists(img_p):
                st.image(img_p, width=520)
            else:
                st.markdown('<div class="empty-wrap">暂无图像结果</div>', unsafe_allow_html=True)

        # ── Tab 2: MAVProxy 指令代码 ──────────────────────────────────────
        with tab2:
            code = res.get("mission_code", "")
            if code:
                st.code(code, language="bash")
            else:
                st.markdown('<div class="empty-wrap">暂无生成代码</div>', unsafe_allow_html=True)

        # ── Tab 3: 航线地图 ───────────────────────────────────────────────
        with tab3:
            waypoints = res.get("waypoints", [])
            if waypoints:
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(
                        f'<div class="stat-card" style="background:#EFF6FF;border-color:#DBEAFE;">'
                        f'<div style="font-size:11px;font-weight:700;color:#64748B;">航点数量</div>'
                        f'<div style="font-size:20px;font-weight:700;color:#2563EB;">{len(waypoints)}</div></div>',
                        unsafe_allow_html=True,
                    )
                with c2:
                    st.markdown(
                        f'<div class="stat-card" style="background:#F0FDF4;border-color:#DCFCE7;">'
                        f'<div style="font-size:11px;font-weight:700;color:#64748B;">起点纬度</div>'
                        f'<div style="font-size:20px;font-weight:700;color:#16A34A;">{waypoints[0][0]:.4f}°</div></div>',
                        unsafe_allow_html=True,
                    )
                with c3:
                    st.markdown(
                        f'<div class="stat-card" style="background:#FFF7ED;border-color:#FED7AA;">'
                        f'<div style="font-size:11px;font-weight:700;color:#64748B;">起点经度</div>'
                        f'<div style="font-size:20px;font-weight:700;color:#EA580C;">{waypoints[0][1]:.4f}°</div></div>',
                        unsafe_allow_html=True,
                    )

                st.markdown('<div class="gap"></div>', unsafe_allow_html=True)
                m = folium.Map(location=waypoints[0], zoom_start=18, tiles="CartoDB positron")
                folium.PolyLine(waypoints, color="#2563EB", weight=2.5, opacity=0.85).add_to(m)
                for i, wp in enumerate(waypoints):
                    fill = "#16A34A" if i == 0 else ("#EF4444" if i == len(waypoints) - 1 else "#2563EB")
                    folium.CircleMarker(
                        location=wp, radius=6, color="#FFFFFF",
                        fill=True, fill_color=fill, fill_opacity=1,
                        tooltip=f"P{i+1}",
                    ).add_to(m)
                st_folium(m, width="100%", height=420, key=f"map_{len(waypoints)}")
            else:
                st.markdown('<div class="empty-wrap">暂无轨迹数据</div>', unsafe_allow_html=True)

        # ── Tab 4: 工业格式导出 ────────────────────────────────────────────
        with tab4:
            waypoints = res.get("waypoints", [])

            if not waypoints:
                st.markdown('<div class="empty-wrap">暂无航点数据，请先完成任务规划。</div>', unsafe_allow_html=True)
            else:
                st.markdown(
                    '<p style="font-size:13px;color:#64748B;margin-bottom:20px;">'
                    '基于模板注入（Template Injection）策略，将 GPS 航点坐标序列动态注入工业标准代码模板，'
                    '输出两类可直接执行的工业格式文件。</p>',
                    unsafe_allow_html=True,
                )

                # ── 导出参数（仅在 Tab 内二次调整，不影响已生成文件）
                col_a, col_b = st.columns(2)
                with col_a:
                    dl_altitude = st.number_input(
                        "飞行高度 (m)", value=float(export_altitude) if 'export_altitude' in dir() else DEFAULT_ALTITUDE,
                        min_value=5.0, max_value=200.0, step=5.0, key="dl_alt"
                    )
                with col_b:
                    dl_speed = st.number_input(
                        "巡航速度 (m/s)", value=float(export_speed) if 'export_speed' in dir() else DEFAULT_SPEED,
                        min_value=1.0, max_value=30.0, step=1.0, key="dl_spd"
                    )

                st.markdown('<div class="gap"></div>', unsafe_allow_html=True)

                # ══════════════════════════════════════════════════════════
                #  路 一：ROS 2 控制脚本
                # ══════════════════════════════════════════════════════════
                st.markdown("""
                <div class="export-box">
                    <div class="export-header">🤖 路一 &nbsp;ROS 2 控制节点脚本 (.py)</div>
                    <div class="export-desc">
                        基于 <b>rclpy</b> 通信库与 <b>mavros</b> 话题接口，通过发布
                        <code>geometry_msgs/PoseStamped</code> 消息实现航点导航。
                        包含节点初始化、ARM/DISARM、Takeoff、多航点顺序导航、RTL 完整指令序列。
                        可直接在配置有 ROS 2 + mavros 环境的机载计算机或 Gazebo 仿真中运行。
                    </div>
                </div>
                """, unsafe_allow_html=True)

                ros2_code = generate_ros2_script(waypoints, "SkyOps_Mission", dl_altitude, dl_speed)

                with st.expander("👁️ 预览 ROS2 脚本内容"):
                    st.code(ros2_code, language="python")

                st.download_button(
                    label="⬇️ 下载 ROS2 控制脚本 (.py)",
                    data=ros2_code.encode("utf-8"),
                    file_name=f"uav_mission_ros2_{st.session_state.current_task_id or 'latest'}.py",
                    mime="text/x-python",
                    width="stretch",
                    key="dl_ros2",
                )

                st.markdown('<div class="gap"></div>', unsafe_allow_html=True)

                # ══════════════════════════════════════════════════════════
                #  路 二：QGC .plan 文件
                # ══════════════════════════════════════════════════════════
                st.markdown("""
                <div class="export-box">
                    <div class="export-header">🛰️ 路二 &nbsp;QGroundControl 飞行计划文件 (.plan)</div>
                    <div class="export-desc">
                        严格遵循 QGroundControl 官方 <b>.plan</b> JSON Schema 规范，
                        自动填充协议版本号、firmwareType (PX4=12)、vehicleType (Quadrotor=2)、
                        MAV_CMD_NAV_TAKEOFF / WAYPOINT / RETURN_TO_LAUNCH 全部指令字段。
                        可直接通过 QGC 地面站导入并上传至 PX4 飞控执行，实现"规划即部署"。
                    </div>
                </div>
                """, unsafe_allow_html=True)

                plan_json = generate_qgc_plan(waypoints, "SkyOps_Mission", dl_altitude, dl_speed)

                with st.expander("👁️ 预览 QGC Plan JSON"):
                    st.code(plan_json, language="json")

                st.download_button(
                    label="⬇️ 下载 QGC 飞行计划 (.plan)",
                    data=plan_json.encode("utf-8"),
                    file_name=f"uav_mission_{st.session_state.current_task_id or 'latest'}.plan",
                    mime="application/json",
                    width="stretch",
                    key="dl_plan",
                )

                st.markdown('<div class="gap"></div>', unsafe_allow_html=True)

                # ── 历史文件状态（如已有保存到磁盘的版本）──────────────
                ros2_path = res.get("ros2_script_path", "")
                plan_path = res.get("plan_file_path",   "")
                if ros2_path or plan_path:
                    st.markdown("**📁 本次任务已保存的磁盘导出文件：**")
                    if ros2_path and os.path.exists(ros2_path):
                        st.success(f"ROS2 脚本：`{ros2_path}`")
                    if plan_path and os.path.exists(plan_path):
                        st.success(f"QGC Plan：`{plan_path}`")

    else:
        st.markdown("""
        <div class="empty-wrap">
            <div style="font-size:54px;margin-bottom:18px;">✈️</div>
            <div style="font-size:20px;font-weight:800;color:#0F172A;margin-bottom:10px;">等待任务下发</div>
            <div style="font-size:14px;color:#64748B;">
                在左侧输入飞行指令并上传卫星图，系统将自动解析目标区域并生成工业部署格式文件。
            </div>
        </div>
        """, unsafe_allow_html=True)