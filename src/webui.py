import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import json
import os
import sys
import io
import datetime
from contextlib import redirect_stdout, redirect_stderr

# Ensure src is in the python path so it can import our core modules correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from trading_signal import generate_signal
from core.portfolio_allocator import PortfolioAllocator
from core.grid_generator import GridGenerator

# ==========================================
# 页面初始化与赛博朋克 CSS 注入 (Phase 13 & 16)
# ==========================================
st.set_page_config(page_title="Kronos Alpha V2 控制台", layout="wide", page_icon="📟")

def inject_cyberpunk_css():
    st.markdown("""
        <style>
        /* 深色底纹与全局字体 */
        .stApp {
            background-color: #0b0f19;
            color: #00ffcc;
            font-family: 'Courier New', Courier, monospace;
        }
        
        /* 标题霓虹化 */
        h1, h2, h3 {
            color: #00ffcc !important;
            text-shadow: 0 0 5px #00ffcc, 0 0 10px #00ffcc;
        }
        
        /* Metric 数值面板发光边框 */
        [data-testid="stMetricValue"] {
            color: #ff0055 !important;
            font-weight: 900;
            text-shadow: 0 0 5px #ff0055;
        }
        
        /* Sidebar 暗黑金属质感 */
        [data-testid="stSidebar"] {
            background-color: #050812;
            border-right: 1px solid #00ffcc;
        }
        
        /* 运行按钮变身赛博核爆键 */
        .stButton>button {
            background: linear-gradient(45deg, #ff0055, #220022);
            color: white;
            border: 1px solid #ff0055;
            box-shadow: 0 0 10px #ff0055;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            box-shadow: 0 0 20px #ff0055, 0 0 40px #ff0055;
            border-color: #ffffff;
        }
        
        /* Tab 控制栏炫光 */
        .stTabs [data-baseweb="tab-list"] {
            background-color: #0b0f19;
        }
        .stTabs [data-baseweb="tab"] {
            color: #888888;
        }
        .stTabs [aria-selected="true"] {
            color: #00ffcc !important;
            border-bottom: 2px solid #00ffcc !important;
            text-shadow: 0 0 5px #00ffcc;
        }
        </style>
    """, unsafe_allow_html=True)

inject_cyberpunk_css()

# ==========================================
# 侧边栏与模式导航
# ==========================================
st.sidebar.image("https://img.icons8.com/nolan/256/brain.png", width=100) # 赛博大脑图标
st.sidebar.title("终端导航模式")
app_mode = st.sidebar.radio("选择进入的战术界面", ["🦅 单股全息扫描", "💼 AI 投资组合配资", "🧊 震荡网格计算机"])

st.sidebar.markdown("---")
st.sidebar.header("⚙️ 全局超参设定")
target_date = st.sidebar.text_input("推演时间切片 (YYYY-MM-DD)", value="", help="留空则执行实时全模态扫描。此值对所有模式生效。")
as_of_date = target_date if target_date else None

# ==========================================
# 模式一: 单股全息扫描 (原 WebUI)
# ==========================================
if app_mode == "🦅 单股全息扫描":
    st.title("📟 Kronos Alpha V2: 全息战损与量化干预终端")
    st.markdown("欢迎接入深网量化中枢。该网段由 `Kronos引擎`、`多因子O-Score` 与 `NLP舆情` 三轨防线共同守卫。")
    
    with st.sidebar:
        st.subheader("模式专属参数")
        ticker = st.text_input("目标代号 (Ticker)", value="AAPL", placeholder="例如: AAPL, MSFT", help="输入需要扫描的美股或A股代码").upper()
        ext_sentiment = st.slider("强制注入狂热/恐慌指数 (Sentiment)", -1.0, 1.0, 0.0, 0.1, help="模拟极端市场情绪对模型判断的干预，范围 [-1.0, 1.0]")
        ext_risk = st.slider("强制黑天鹅过载熔断率 (Risk)", 0.0, 1.0, 0.3, 0.1, help="设定不可预见性风险的惩罚系数，值越高防范性越强")

        is_disabled = not bool(ticker.strip())
        btn_help = "请输入目标代号以启动扫描" if is_disabled else "执行深度扫描并生成战损区报告"
        run_btn = st.button("☢️ 启动高维量化穿透扫描", use_container_width=True, disabled=is_disabled, help=btn_help)

    if run_btn:
        log_stream = io.StringIO()
        with st.spinner(f"正在建立 {ticker} 的高维波段共振..."):
            try:
                with redirect_stdout(log_stream), redirect_stderr(log_stream):
                    signal_pack = generate_signal(ticker, as_of_date=as_of_date, ext_sentiment=ext_sentiment, ext_risk=ext_risk)
                
                logs = log_stream.getvalue()
                meta = signal_pack["metadata"]
                
                if meta.get("fundamental_bust_triggered", False):
                    st.error("🚨 致命级系统干预：探测到严重的资产负债表恶化或流动性枯萎风险，强制截断所有顺势交易额度！ O-Score 防线已启动一票否决。", icon="⛔")
                    
                st.markdown("---")
                tab1, tab2, tab3, tab4 = st.tabs(["🖲️ 全息战情室", "🕸️ 多因子雷达", "📉 极限推演图谱", "🛠️ 底层暗网日志"])
                
                with tab1:
                    st.subheader(f"🎯 最终行动指标: {ticker}")
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("战略界限 (Regime)", signal_pack["regime"])
                    col2.metric(" Kronos 波段动能 (Z-Score)", f"{signal_pack['regime_strength']:.2f}")
                    
                    direction_color = "normal" if signal_pack["direction"] == "BUY" else "inverse"
                    if signal_pack["direction"] == "HOLD": direction_color = "off"
                    col3.metric("纯量化推荐指向", signal_pack["direction"], delta=f"Base: {meta['base_strength']:.2f}", delta_color=direction_color)
                    col4.metric("双规避险后最终配仓", f"{signal_pack['adjusted_position_strength']*100:.1f}%")
                    
                    st.markdown("---")
                    st.subheader("⚠️ 致命压测折损项 (Penalty Factors)")
                    pcol1, pcol2, pcol3 = st.columns(3)
                    pcol1.metric("波动率深渊折扣", f"{meta['volatility_discount']:.2f}x", help="动荡过大时的硬性削减。")
                    pcol2.metric("O-Score 多因子乘数", f"{meta.get('multi_factor_multiplier', 1.0):.2f}x", help="根据其优质性赋予的额外筹码倾斜。")
                    pcol3.metric("外部惊惧指数", f"{meta['risk_factor']:.2f} 扣减", help="由 NLP 或外部注入的主观干预。")

                with tab2:
                    st.subheader("🕸️ Fama-French 多维度财务透析仪")
                    factors = meta.get("factor_scores", {})
                    if factors:
                        score = meta.get("multi_factor_o_score", 50.0)
                        if score > 75:
                            st.success(f"💎 顶尖优良资产认证 [O-Score: {score:.2f} 分]")
                        elif score < 40:
                            st.warning(f"🗑️ 金玉其外的高危筹码 [O-Score: {score:.2f} 分]")
                        else:
                            st.info(f"⚖️ 普通公允资产 [O-Score: {score:.2f} 分]")
                            
                        categories = ['价值 (Value)', '质量 (Quality)', '规模 (Size)', '动量 (Momentum)', '抗跌低波 (Volatility)']
                        fig_radar = go.Figure()
                        fig_radar.add_trace(go.Scatterpolar(
                            r=[factors.get('value_score', 0), factors.get('quality_score', 0), factors.get('size_score', 0), factors.get('momentum_score', 0), factors.get('volatility_score', 0)],
                            theta=categories, fill='toself', fillcolor='rgba(0, 255, 204, 0.2)', line=dict(color='#00ffcc', width=2), name=f'{ticker} 因子画像'
                        ))
                        fig_radar.update_layout(
                            polar=dict(radialaxis=dict(visible=True, range=[0, 100], color='#888', gridcolor='#333'), angularaxis=dict(color='#00ffcc', gridcolor='#333')),
                            showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="#00ffcc", family="Courier New"),
                            title=dict(text="5维雷达穿透评分 (0-100)", font=dict(color="#00ffcc"))
                        )
                        st.plotly_chart(fig_radar, use_container_width=True, key=f"radar_chart_{ticker}")
                    else:
                        st.error("未能在此次演算中获取到多因子雷达回传。")

                with tab3:
                    st.subheader("📉 量化置信区间推演 (Kronos 30-Day Outlook)")
                    vcol1, vcol2, vcol3 = st.columns(3)
                    vcol1.metric("未来均值预期 (Mean Ret)", f"{signal_pack['mean_return']*100:.2f}%")
                    vcol2.metric("预测标准差裂口 (Uncertainty)", f"{signal_pack['uncertainty']*100:.2f}%")
                    vcol3.metric("预测极值收缩极径 (Range)", f"{signal_pack['predicted_range_pct']*100:.2f}%")
                    
                    end_arg = as_of_date if as_of_date else datetime.datetime.now().strftime("%Y-%m-%d")
                    end_dt = datetime.datetime.strptime(end_arg, "%Y-%m-%d")
                    start_dt = end_dt - datetime.timedelta(days=180)
                    
                    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                        hist = yf.Ticker(ticker).history(start=start_dt.strftime("%Y-%m-%d"), end=(end_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d"))
                    
                    if not hist.empty:
                        fig_price = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name="Historical Price")])
                        last_close = hist['Close'].iloc[-1]
                        pred_max_price = last_close * (1 + signal_pack['predicted_max'])
                        pred_min_price = last_close * (1 + signal_pack['predicted_min'])
                        
                        fig_price.add_hline(y=pred_max_price, line_dash="solid", line_color="#00ffcc", annotation_text="🚀 预测分布穹顶 (Predicted High)")
                        fig_price.add_hline(y=pred_min_price, line_dash="solid", line_color="#ff0055", annotation_text="💥 预测分布绝崖 (Predicted Low)")
                        
                        fig_price.update_layout(title=f"{ticker} 战损区边界防御图", xaxis_rangeslider_visible=False, template="plotly_dark",
                                          paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(11, 15, 25, 0.8)', height=600)
                        st.plotly_chart(fig_price, use_container_width=True, key=f"kronos_candlestick_{ticker}")
                    else:
                        st.warning("⚠️ 没有获取到支撑该时空节点的弹道数据。")

                with tab4:
                    st.subheader("🛠️ 底层计算网路追踪 (Runtime Logs)")
                    st.code(logs, language="text")
                    st.subheader("🗃️ RAW JSON 核弹射控信令包")
                    st.json(signal_pack)
                    
            except Exception as e:
                st.error(f"引擎执行遭受毁灭性打击: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

# ==========================================
# 模式二: AI 投资组合配资
# ==========================================
elif app_mode == "💼 AI 投资组合配资":
    st.title("💼 AI 组合管家: 基于风险平价与护城河评分的最优配比")
    st.markdown("输入一组股票代码，系统将并发测算它们的 **多因子 O-Score** 和 **Kronos 预测波动率**，为您分配最抗跌防雷的建仓比例。")
    
    with st.sidebar:
        st.subheader("模式专属参数")
        pool_input = st.text_area("股票群落代码 (以逗号或空格分隔)", value="AAPL, MSFT, NVDA, TSLA, 600519.SS", placeholder="AAPL, MSFT...", help="多支股票代码，系统将进行横向比对和配比测算")

        is_port_disabled = not bool(pool_input.strip())
        btn_port_help = "请输入至少一个股票代码" if is_port_disabled else "基于 O-Score 进行资金组合最优配比测算"
        run_port_btn = st.button("⚖️ 启动资金天平配平", use_container_width=True, disabled=is_port_disabled, help=btn_port_help)
        
    if run_port_btn:
        tickers = [x.strip() for x in pool_input.replace(',', ' ').split() if x.strip()]
        if not tickers:
            st.warning("股票群落代码不能为空。")
        else:
            with st.spinner(f"正在分析 {len(tickers)} 支股票的质量与波动防线..."):
                try:
                    out = PortfolioAllocator.allocate(tickers, as_of_date=as_of_date)
                    alloc_data = out["allocation"]
                    
                    valid_labels = []
                    valid_values = []
                    
                    # 报告卡显示
                    cols = st.columns(len(tickers))
                    for i, t in enumerate(tickers):
                        d = alloc_data.get(t, {})
                        with cols[i % len(cols)]:
                            if d.get("status") == "BUST":
                                st.error(f"**{t}**\n\n已被基本面一票否决墙击毙！\n\n仓位锁定 0%")
                            elif d.get("status") == "OK":
                                st.success(f"**{t}**\n\n建议配比: **{d['weight']*100:.1f}%**\n\nO-Score: {d['o_score']:.1f}\n\n风险值: {d['uncertainty']*100:.1f}%")
                                if d['weight'] > 0:
                                    valid_labels.append(t)
                                    valid_values.append(d['weight'])
                            else:
                                st.warning(f"**{t}**\n\n解析失败。")
                                
                    if valid_labels:
                        st.markdown("---")
                        st.subheader("🥧 零风险暴露资金切分饼图")
                        fig_pie = go.Figure(data=[go.Pie(labels=valid_labels, values=valid_values, hole=.3)])
                        fig_pie.update_traces(hoverinfo='label+percent', textinfo='value', textfont_size=16,
                                              marker=dict(colors=['#00ffcc', '#ff0055', '#bb86fc', '#03dac6', '#cf6679'], line=dict(color='#000000', width=2)))
                        fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(color="#00ffcc", family="Courier New"))
                        st.plotly_chart(fig_pie, use_container_width=True, key="portfolio_pie_chart")
                        
                except Exception as e:
                    st.error(f"配资过程异常崩溃: {str(e)}")

# ==========================================
# 模式三: 震荡网格计算机
# ==========================================
elif app_mode == "🧊 震荡网格计算机":
    st.title("🧊 全天候智能网格引擎: 高抛低吸矩阵")
    st.markdown("当系统判定这只股票陷入垃圾时间（均值回归的震荡市）时，借助 Kronos 精准的顶底预测区间，直接生成可挂到券商的机械网格单库。")
    
    with st.sidebar:
        st.subheader("模式专属参数")
        grid_ticker = st.text_input("震荡目标代号", value="TSLA", placeholder="例如: TSLA, BABA", help="输入震荡市标的以生成网格").upper()
        grid_lines = st.slider("切分步长网格级数", 3, 20, 8, help="网格分割的数量，层数越多交易频率越高")

        is_grid_disabled = not bool(grid_ticker.strip())
        btn_grid_help = "请输入震荡目标代号" if is_grid_disabled else "生成网格阶梯并测算挂单区间"
        run_grid_btn = st.button("🧊 构建全矩阵高开低走截断网", use_container_width=True, disabled=is_grid_disabled, help=btn_grid_help)
        
    if run_grid_btn:
        with st.spinner(f"正在用 Kronos 收缩极径倒推 {grid_ticker} 阶梯挂单线..."):
            try:
                out = GridGenerator.generate_grid(grid_ticker, grid_lines=grid_lines, as_of_date=as_of_date)
                
                if "error" in out:
                    st.error(f"提取失败: {out['error']}")
                else:
                    if out["is_suitable_for_grid"]:
                        st.success(f"✅ 系统认证：当前标的处于 **{out['regime']}** 或动能匮乏，极度适合网格套利策略！")
                    else:
                        st.warning(f"⚠️ 风险警告：标的当前处于 **{out['regime']}**，具有强单边趋势，执行震荡网格可能会导致踏空或深度套牢！")
                        
                    st.markdown("---")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("中枢现货价 (p0)", f"{out['base_price']}")
                    col2.metric("Kronos 顶界抛压线 (Max)", f"{out['predicted_high']}", "阻力天花板")
                    col3.metric("Kronos 底部容差线 (Min)", f"{out['predicted_low']}", "买盘铁皮地", delta_color="inverse")
                    
                    df = pd.DataFrame(out["grid_levels"])
                    # 为了展示美观，调整一下列顺序和名称
                    df = df[['level_index', 'price', 'distance_from_p0', 'action']]
                    df.columns = ["网格层级", "触达现价", "距离当前震幅 (%)", "执行动作"]
                    
                    st.subheader(f"📊 {grid_lines} 级机械化挂单表")
                    st.dataframe(df, use_container_width=True, key="grid_dataframe")
                    
            except Exception as e:
                 st.error(f"网格构建毁灭性中止: {str(e)}")
