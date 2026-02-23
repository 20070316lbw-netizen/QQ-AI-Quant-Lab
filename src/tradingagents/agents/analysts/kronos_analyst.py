import re
import io
import pandas as pd
from datetime import datetime, timedelta
from tradingagents.agents.utils.kronos_tools import get_market_prediction
from tradingagents.agents.utils.agent_states import AnalystReport

def create_kronos_analyst(llm):
    def kronos_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        
        # 1. 直接获取 Kronos 时序预测数据 (预测未来 30 天)
        # 注意：这里我们模拟 LLM 的决策逻辑，但为了极致纯净，我们先获取原始数据
        # 实际上在全链路模式下，这是由 Market Analyst 触发的常用工具
        # 1. 动态回溯：仅获取最近 120 天的数据作为预测背景，提高抓取速度
        try:
            target_dt = datetime.strptime(current_date, "%Y-%m-%d")
            start_dt = target_dt - timedelta(days=120)
            start_date_str = start_dt.strftime("%Y-%m-%d")
        except:
            start_date_str = "2024-10-01" # 回退安全值
            
        prediction_result = get_market_prediction.invoke({
            "symbol": ticker,
            "start_date": start_date_str,
            "end_date": current_date,
            "pred_len": 30
        })
        
        # 2. 解析预测数据并计算收益率
        decision = "HOLD"
        confidence = 0.5
        expected_return = 0.0
        
        try:
            # 改进的 CSV 提取逻辑：寻找包含 'open,high,low,close' 的部分
            if "close" in prediction_result:
                csv_start = prediction_result.find("open,")
                if csv_start != -1:
                    csv_part = prediction_result[csv_start:]
                    df_pred = pd.read_csv(io.StringIO(csv_part))
                    
                    if not df_pred.empty:
                        start_price = df_pred.iloc[0]["close"]
                        end_price = df_pred.iloc[-1]["close"]
                        expected_return = (end_price / start_price) - 1.0
                        
                        # --- V13.4 5-Step Quant Backbone ---
                        # Step 1: 路径预测 (已由 api.py Ensemble 完成)
                        # Step 2 & 3: 从元数据中解析收益均值（Mean）与波动（Std）
                        m_ret = 0.0
                        s_ret = 0.0309 # 默认 fallback
                        
                        match_m = re.search(r"mean_return=([-\d.e]+)", prediction_result)
                        match_s = re.search(r"std_return=([-\d.e]+)", prediction_result)
                        
                        if match_m: m_ret = float(match_m.group(1))
                        if match_s: s_ret = float(match_s.group(1))
                        
                        expected_return = m_ret
                        # Step 4: z = mean / std (设定 0.5% 最小噪声底以防分母过小)
                        noise_floor = 0.005 
                        z_score = expected_return / max(s_ret, noise_floor)
                        abs_z = abs(z_score)
                        
                        # 方向判定改进 (V13.6)：基于 Z-Score 协同判定 (Threshold=0.5)
                        if z_score >= 0.5:
                            side = "BULLISH"
                            level = 1 if abs_z < 1.0 else 2 if abs_z < 1.5 else 3
                        elif z_score <= -0.5:
                            side = "BEARISH"
                            level = 1 if abs_z < 1.0 else 2 if abs_z < 1.5 else 3
                        else:
                            side = "NEUTRAL"
                            level = 0
                            
                        uncertainty = s_ret
                        
                        # Step 5: 根据等级映射决策标签
                        if level == 0:
                            decision = "HOLD"
                            confidence = 0.85 - (0.2 * (abs_z / 0.5))
                        elif level == 1:
                            decision = f"SMALL {side} POSITION"
                            confidence = 0.6 + (0.1 * (abs_z - 0.5) / 0.5)
                        elif level == 2:
                            decision = f"MEDIUM {side} POSITION"
                            confidence = 0.7 + (0.1 * (abs_z - 1.0) / 0.5)
                        else: # level == 3
                            decision = f"LARGE {side} POSITION"
                            confidence = min(0.8 + (0.15 * (abs_z - 1.5) / 1.0), 0.95)
                            
                        # decision 已由上方 if/elif/else 分支直接赋值，无需中间变量
                else:
                    print(f"[Analyst] Prediction data found but CSV header missing.")
            else:
                print(f"[Analyst] Prediction failed or returned non-data content.")
        except Exception as e:
            print(f"[Analyst] Critical parsing error: {e}")
            decision = "HOLD"
            confidence = 0.5

        # 3. 封装为结构化报告
        report_data: AnalystReport = {
            "analyst_name": "Kronos Quant Engine",
            "summary": (
                f"TICKER: {ticker}\n"
                f"DIRECTION: {'BUY' if side == 'BULLISH' else 'SELL' if side == 'BEARISH' else 'HOLD'}\n"
                f"Z_SCORE: {z_score:.2f}\n"
                f"EXPECTED_RETURN: {expected_return:.2%}\n"
                f"VOLATILITY: {uncertainty:.2%}\n"
                f"CONFIDENCE: {confidence:.2f}"
            ),
            "key_metrics": {
                "expected_return": f"{expected_return:.2%}",
                "pred_len": "30D",
                "model_version": "v1.0-foundation",
                "z_score": float(abs_z),
                "uncertainty": float(uncertainty)
            },
            "decision": decision,
            "confidence": confidence,
            "risk_score": 0.3 if decision == "HOLD" else 0.5,
            "risk_bias": "neutral"
        }
        
        structured_reports = state.get("structured_reports", {})
        structured_reports["kronos_solo"] = report_data
        
        return {
            "kronos_report": prediction_result,
            "structured_reports": structured_reports,
            "sender": "KronosAnalyst"
        }

    return kronos_analyst_node
