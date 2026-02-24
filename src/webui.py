import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import json
import os
import sys
import io
from contextlib import redirect_stdout, redirect_stderr

# Ensure src is in the python path so it can import our core modules correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from trading_signal import generate_signal

st.set_page_config(page_title="Kronos Alpha V2 控制台", layout="wide", page_icon="📈")

st.title("📈 Kronos Alpha V2: 量化状态与波动率引擎")
st.markdown("该面板展示基于双轨架构（底层数学仲裁 + NLP情绪调参）的最新回测管线。")

# Sidebar for inputs
with st.sidebar:
    st.header("⚙️ 引擎配置")
    ticker = st.text_input("股票/标的代码", value="AAPL").upper()
    target_date = st.text_input("预演锚定日期 (YYYY-MM-DD)", value="", help="留空则默认使用今天的市场数据进行推演。")
    ext_sentiment = st.slider("注入外部市场情绪 (Sentiment Override)", -1.0, 1.0, 0.0, 0.1)
    ext_risk = st.slider("注入外部黑天鹅风险 (Risk Override)", 0.0, 1.0, 0.3, 0.1)
    run_btn = st.button("🚀 启动量化生成", type="primary", use_container_width=True)

if run_btn:
    # Set up string buffers to capture print/log output
    log_stream = io.StringIO()
    
    with st.spinner(f"正在启动 Kronos 引擎计算 {ticker} 的量化特征... (这通常需要 10-30 秒)"):
        try:
            with redirect_stdout(log_stream), redirect_stderr(log_stream):
                # 1. Fetch signal
                as_of_date = target_date if target_date else None
                signal_pack = generate_signal(ticker, as_of_date=as_of_date, ext_sentiment=ext_sentiment, ext_risk=ext_risk)
            
            logs = log_stream.getvalue()
            
            # 2. Present high-level metrics
            st.subheader(f"🎯 {ticker} 最终量化评估结果")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("市场状态评估 (Regime)", signal_pack["regime"], 
                        delta="趋势追涨杀跌" if "STRONG" in signal_pack["regime"] else "均值回归模式",
                        delta_color="normal" if "STRONG" in signal_pack["regime"] else "off")
            col2.metric("趋势强度 Z-Score", f"{signal_pack['regime_strength']:.2f}",
                        delta="偏向做多" if signal_pack['regime_strength'] > 0 else "偏向做空")
            
            direction_color = "normal" if signal_pack["direction"] == "BUY" else "inverse"
            if signal_pack["direction"] == "HOLD": direction_color = "off"
            col3.metric("纯量化推荐方向", signal_pack["direction"], delta=f"基础置信度: {signal_pack['metadata']['base_strength']:.2f}", delta_color=direction_color)
            
            col4.metric("风控与波动调整后建议仓位", f"{signal_pack['adjusted_position_strength']*100:.1f}%")

            st.markdown("---")
            
            # 3. Present Prediction Matrix
            st.subheader("📊 V2 新增维度：分布与波动推演提取 (Phase 6)")
            vcol1, vcol2, vcol3, vcol4 = st.columns(4)
            vcol1.metric("未来30日均值预期收益", f"{signal_pack['mean_return']*100:.2f}%")
            vcol2.metric("预测未来标准差 (不确定性)", f"{signal_pack['uncertainty']*100:.2f}%")
            vcol3.metric("预测极值收缩区间 (Range)", f"{signal_pack['predicted_range_pct']*100:.2f}%", 
                         help="高度正相关于未来5天的真实极值振幅 (Correlation > 0.38)!")
            vcol4.metric("剧烈波动避险折扣系数", f"{signal_pack['metadata']['volatility_discount']:.2f}x",
                         help="当预测波动过大时，系统自动呈指数级削减当前仓位系数。")
            
            st.markdown("---")
            
            # Show System Execution Logs
            with st.expander("🛠️ 展开查看系统底层运行过程与计算流水日志"):
                st.code(logs, language="text")
                st.markdown("**最终落盘的量化信令 JSON 快照:**")
                st.json(signal_pack)
                
            # 5. Render historical context
            st.subheader("📉 量化置信区间推演落屏")
            # Fetch chart up to the target date if provided
            end_arg = target_date if target_date else None
            # Need to get somewhat accurate end date formatting for YF
            import datetime
            if not end_arg:
                end_arg = datetime.datetime.now().strftime("%Y-%m-%d")
            
            end_dt = datetime.datetime.strptime(end_arg, "%Y-%m-%d")
            start_dt = end_dt - datetime.timedelta(days=180)
            
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                hist = yf.Ticker(ticker).history(start=start_dt.strftime("%Y-%m-%d"), end=(end_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d"))
            
            if not hist.empty:
                fig = go.Figure(data=[go.Candlestick(x=hist.index,
                                open=hist['Open'], high=hist['High'],
                                low=hist['Low'], close=hist['Close'],
                                name="Historical Price")])
                
                # Annotate the prediction range limits as horizontal lines based on last close price
                last_close = hist['Close'].iloc[-1]
                pred_max_price = last_close * (1 + signal_pack['predicted_max'])
                pred_min_price = last_close * (1 + signal_pack['predicted_min'])
                
                fig.add_hline(y=pred_max_price, line_dash="dot", line_color="green", annotation_text="预测分布上限 (Predicted High Bounds)")
                fig.add_hline(y=pred_min_price, line_dash="dot", line_color="red", annotation_text="预测分布下限 (Predicted Low Bounds)")
                
                fig.update_layout(title=f"{ticker} - 过去半年走势与 Kronos 引擎预判波动防线边界", 
                                  xaxis_rangeslider_visible=False, 
                                  template="plotly_dark",
                                  height=600)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ 无法获取用于图形渲染的历史数据。")
                
        except Exception as e:
            st.error(f"引擎执行中断: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
