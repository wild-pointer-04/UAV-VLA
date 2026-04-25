import streamlit as st
import folium
from streamlit_folium import st_folium
import db_manager
import service_layer
import os
import json

# 1. 初始化
db_manager.init_db()
st.set_page_config(page_title="UAV-VLA 任务控制台", layout="wide")

# --- 新增：注入全局 CSS 样式，让你的自定义 class 完美生效 ---
st.markdown("""
<style>
    /* 页面顶部间距微调 */
    div.block-container { padding-top: 2rem; }
    
    /* 导航条样式 */
    .topbar {
        display: flex; align-items: center; justify-content: space-between;
        padding: 16px 24px; background: #ffffff; border-radius: 12px;
        border: 1px solid #E2E8F0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 24px;
    }
    .topbar-left { display: flex; align-items: center; gap: 16px; }
    .topbar-logo { font-size: 36px; color: #2563EB; line-height: 1;}
    .topbar-title { font-size: 22px; font-weight: 800; color: #0F172A; line-height: 1.2;}
    .topbar-sub { font-size: 13px; color: #64748B; font-weight: 500;}
    .topbar-badge {
        display: flex; align-items: center; background: #ECFDF5;
        padding: 6px 14px; border-radius: 20px; border: 1px solid #A7F3D0;
        font-size: 13px; color: #059669; font-weight: 600; gap: 6px;
    }
    .dot { height: 8px; width: 8px; background-color: #10B981; border-radius: 50%; }

    /* 标签与识别目标样式 */
    .field-label {
        font-size: 14px; font-weight: 700; color: #475569; margin-right: 12px;
        display: inline-flex; align-items: center;
    }
    .chip {
        display: inline-block; background: #EFF6FF; color: #1D4ED8;
        padding: 4px 14px; border-radius: 20px; font-size: 13px;
        font-weight: 600; margin-right: 8px; border: 1px solid #BFDBFE;
    }

    /* 数据卡片样式 */
    .stat-card {
        padding: 16px; border-radius: 12px; border: 1px solid;
        text-align: center; transition: all 0.2s ease;
    }
    .stat-card:hover { transform: translateY(-2px); }
    
    /* 空状态样式 */
    .empty-wrap {
        text-align: center; padding: 60px 20px; margin-top: 10px;
        background: #ffffff; border-radius: 16px; border: 1px dashed #CBD5E1;
    }
    .gap { height: 20px; }
</style>
""", unsafe_allow_html=True)
# -----------------------------------------------------------

if 'mission_result' not in st.session_state:
    st.session_state.mission_result = None

# ── 顶部导航条 ─────────────────────────────────────────────────────────────────
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

# 2. 侧边栏：历史任务模块
with st.sidebar:
    st.header("📋 历史任务记录")
    try:
        history_tasks = db_manager.get_all_tasks()
    except:
        history_tasks = []
        
    if not history_tasks:
        st.info("暂无历史任务数据")
    else:
        for record in history_tasks:
            # 点击历史任务按钮
            btn_label = f"任务 #{record['id']} - {record['create_time'][11:16]}"
            if st.button(btn_label, key=f"hist_{record['id']}", use_container_width=True):
                
                # --- 核心：解析数据库中的 JSON 字符串 ---
                raw_wps = record.get('waypoints', [])
                raw_targets = record.get('targets', "[]")
                
                try:
                    parsed_wps = json.loads(raw_wps) if isinstance(raw_wps, str) else raw_wps
                    parsed_targets = json.loads(raw_targets) if isinstance(raw_targets, str) else raw_targets
                except:
                    parsed_wps = []
                    parsed_targets = []

                # 更新状态
                st.session_state.mission_result = {
                    'parsed_targets': parsed_targets,
                    'mission_code': record.get('mission_code', ""),
                    'vlm_image_result': record.get('image_path', ""),
                    'waypoints': parsed_wps
                }
                st.rerun()

# 3. 主界面布局
col1, col2 = st.columns([1, 2], gap="large") # 增加了列之间的间距(gap)

with col1:
    st.subheader("任务下发")
    instruction = st.text_area("输入自然语言指令：", "Create a flight plan for the quadcopter to fly around each of the building at the height 100m.", height=120)
    uploaded_file = st.file_uploader("上传卫星图像地图", type=['jpg', 'png'])

    if st.button("🚀 开始生成飞行计划", use_container_width=True, type="primary"): # 加深了主按钮的颜色
        if not uploaded_file:
            st.error("请先上传卫星图！")
        else:
            os.makedirs("images", exist_ok=True)
            img_path = f"images/temp_{uploaded_file.name}"
            with open(img_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            with st.spinner("系统正在进行分析..."):
                success, result = service_layer.process_flight_mission(instruction, img_path)
                
                if success:
                    # 存入数据库
                    db_manager.insert_task(
                        task_name=f"任务_{uploaded_file.name}",
                        command=instruction,
                        targets=result['parsed_targets'],
                        mission_code=result['mission_code'],
                        image_path=result['vlm_image_result'],
                        waypoints=result['waypoints']
                    )
                    st.session_state.mission_result = result
                    st.success("任务生成并保存成功！")
                else:
                    st.error(f"执行失败: {result}")

with col2:
    if st.session_state.mission_result is not None:
        res = st.session_state.mission_result
        tab1, tab2, tab3 = st.tabs(["🎯 视觉识别结果", "💻 飞行指令代码", "🗺️ 航线轨迹预览"])
 
        with tab1:
            targets = res.get("parsed_targets", [])
            if targets:
                chips = "".join(
                    f'<span class="chip">{t}</span>'
                    for t in (targets if isinstance(targets, list) else [targets])
                )
                st.markdown(
                    f'<div style="margin-bottom:18px;">'
                    f'<span class="field-label">识别目标：</span>{chips}</div>',
                    unsafe_allow_html=True,
                )
            img_p = res.get("vlm_image_result", "")
            if img_p and os.path.exists(img_p):
                st.image(img_p, use_container_width=True)
            else:
                st.markdown("""
                <div style="background:#F8FAFD;border:1.5px dashed #DDE3F0;border-radius:12px;
                            padding:56px;text-align:center;color:#C4CFE6;">
                    <div style="font-size:34px;margin-bottom:10px;">🖼️</div>
                    <div style="font-size:14px; font-weight: 500; color: #94A3B8;">暂无图像结果</div>
                </div>""", unsafe_allow_html=True)
 
        with tab2:
            code = res.get("mission_code", "")
            if code:
                st.code(code, language="bash")
            else:
                st.markdown("""
                <div style="text-align:center;padding:56px;color:#94A3B8; background:#F8FAFD; border:1.5px dashed #DDE3F0; border-radius:12px;">
                    <div style="font-size:34px;margin-bottom:10px;">📄</div>
                    <div style="font-size:14px; font-weight: 500;">暂无生成代码</div>
                </div>""", unsafe_allow_html=True)
 
        with tab3:
            waypoints = res.get("waypoints", [])
            if waypoints:
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(
                        f'<div class="stat-card" style="background:#EFF6FF;border-color:#DBEAFE;">'
                        f'<div style="font-size:11px;font-weight:700;color:#64748B;letter-spacing:0.5px;">航点数量</div>'
                        f'<div style="font-size:20px;font-weight:700;color:#2563EB;margin-top:4px;">{len(waypoints)}</div>'
                        f'</div>', unsafe_allow_html=True)
                with c2:
                    st.markdown(
                        f'<div class="stat-card" style="background:#F0FDF4;border-color:#DCFCE7;">'
                        f'<div style="font-size:11px;font-weight:700;color:#64748B;letter-spacing:0.5px;">起点纬度</div>'
                        f'<div style="font-size:20px;font-weight:700;color:#16A34A;margin-top:4px;">{waypoints[0][0]:.4f}°</div>'
                        f'</div>', unsafe_allow_html=True)
                with c3:
                    st.markdown(
                        f'<div class="stat-card" style="background:#FFF7ED;border-color:#FED7AA;">'
                        f'<div style="font-size:11px;font-weight:700;color:#64748B;letter-spacing:0.5px;">起点经度</div>'
                        f'<div style="font-size:20px;font-weight:700;color:#EA580C;margin-top:4px;">{waypoints[0][1]:.4f}°</div>'
                        f'</div>', unsafe_allow_html=True)
 
                st.markdown('<div class="gap"></div>', unsafe_allow_html=True)
                m = folium.Map(location=waypoints[0], zoom_start=18, tiles="CartoDB positron")
                folium.PolyLine(waypoints, color="#2563EB", weight=2.5, opacity=0.85).add_to(m)
                for i, wp in enumerate(waypoints):
                    fill = "#16A34A" if i == 0 else ("#EF4444" if i == len(waypoints)-1 else "#2563EB")
                    folium.CircleMarker(
                        location=wp, radius=6, color="#FFFFFF",
                        fill=True, fill_color=fill, fill_opacity=1,
                        popup=folium.Popup(f"<b>P{i+1}</b><br>({wp[0]:.5f}, {wp[1]:.5f})", max_width=160),
                        tooltip=f"P{i+1}",
                    ).add_to(m)
                st_folium(m, width="100%", height=420, key=f"map_{len(waypoints)}")
            else:
                st.markdown("""
                <div style="text-align:center;padding:56px;color:#94A3B8; background:#F8FAFD; border:1.5px dashed #DDE3F0; border-radius:12px;">
                    <div style="font-size:34px;margin-bottom:10px;">🗺️</div>
                    <div style="font-size:14px;font-weight:600; color: #64748B;">暂无轨迹数据</div>
                    <div style="font-size:12px;color:#94A3B8;margin-top:6px;">当前任务记录不含经纬度坐标</div>
                </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="empty-wrap">
            <div style="font-size:54px;margin-bottom:18px;">✈️</div>
            <div style="font-size:20px;font-weight:800;color:#0F172A;margin-bottom:10px;letter-spacing:-0.3px;">
                等待任务下发
            </div>
            <div style="font-size:14px;color:#64748B;line-height:1.7;max-width:340px;margin:0 auto;">
                在左侧输入飞行指令并上传卫星图<br>
                系统将自动解析目标区域并生成可执行的飞行计划
            </div>
            <div style="margin-top:36px;display:flex;justify-content:center;gap:16px;flex-wrap:wrap;">
                <div style="background:#F8FAFD;border:1px solid #E2E8F0;border-radius:10px;
                            padding:12px 20px;font-size:13px;color:#475569;font-weight:600;">
                    🤖&nbsp; VLM 视觉识别
                </div>
                <div style="background:#F8FAFD;border:1px solid #E2E8F0;border-radius:10px;
                            padding:12px 20px;font-size:13px;color:#475569;font-weight:600;">
                    📡&nbsp; 自动航点规划
                </div>
                <div style="background:#F8FAFD;border:1px solid #E2E8F0;border-radius:10px;
                            padding:12px 20px;font-size:13px;color:#475569;font-weight:600;">
                    🗺️&nbsp; 实时轨迹预览
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)