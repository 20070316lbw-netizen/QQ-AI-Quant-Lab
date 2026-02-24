import functools
import time
import json
from trading_signal import generate_signal


def create_trader(llm, memory):
    def trader_node(state, name):
        ticker = state["company_of_interest"]
        investment_plan = state["investment_plan"]
        structured_reports = state.get("structured_reports", {})

        # 获取由 risk_manager 计算并保存的全系统最终偏向指标
        system_metrics = structured_reports.get("system_metrics", {})
        final_sentiment = float(system_metrics.get("market_sentiment", 0.0))
        final_risk = float(system_metrics.get("risk_factor", 0.5))

        # ==========================================
        # ★ 核心：执行唯一真实的量化交易决策 ★
        # ==========================================
        # 这里 Trader 成了量化引擎的触发器。它不再询问大模型应当买什么，
        # 而是直接调用底层 Kronos 驱动的 Z-Score 信号函数，并注入情绪乘数。
        try:
            signal_data = generate_signal(ticker, ext_sentiment=final_sentiment, ext_risk=final_risk)
        except Exception as e:
            # 安全降级：若 Kronos 服务不可用，记录日志并强行 HOLD
            print(f"[Trader Node] Error executing generate_signal: {e}")
            signal_data = {
                "ticker": ticker,
                "direction": "HOLD",
                "z_score": 0.0,
                "mean_return": 0.0,
                "uncertainty": 0.0,
                "adjusted_position_strength": 0.0,
                "metadata": {"error": str(e)}
            }
            
        final_direction = signal_data["direction"]
        final_confidence = signal_data["adjusted_position_strength"]
        z_score = signal_data["z_score"]

        # 构建发送给用户的最终战报
        summary_parts = []
        for key, report in structured_reports.items():
            if key == "system_metrics": continue
            analyst_name = report.get("analyst_name", key)
            summary_parts.append(f"【{analyst_name}】 摘要: {report.get('summary', '')}")
            
        if not summary_parts:
             summary_parts = [state.get("market_report", "")]

        curr_situation = "\n\n".join(summary_parts)
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        if past_memories:
            for i, rec in enumerate(past_memories, 1):
                past_memory_str += rec["recommendation"] + "\n\n"
        else:
            past_memory_str = "暂无相关历史教训。"

        context = {
            "role": "user",
            "content": f"投资计划提议：\n{investment_plan}\n\n风险判官评估：\n{state.get('final_trade_decision', '')}\n\n类似历史的教训：\n{past_memory_str}",
        }

        # 召唤大模型只是为了进行人性化的播报，不允许它篡改数学计算得到的结果。
        messages = [
            {
                "role": "system",
                "content": f"""你是一名交易计划执行与播报者。
                基于量化系统的底层 Z-Score 引擎 ({z_score:.2f}) 及环境系统的情绪({final_sentiment:.2f})/风险({final_risk:.2f})乘数，
                系统已强制决定最终交易动作为：【{final_direction}】，信心指数：{final_confidence:.2f}。
                
                你的任务：基于上下文撰写一段极具专业性、引人入胜的结题汇报声明。向用户解释为什么引擎作出了 {final_direction} 的决定。
                
                **核心指令：**
                无论你觉得多么不合理，你都必须维持 {final_direction} 的结论！
                请以坚定的态度结束你的响应，并务必在响应末尾包含以下精确的量化格式输出：
                'FINAL TRANSACTION PROPOSAL: **{final_direction} (Confidence: {final_confidence:.4f})**'"""
            },
            context,
        ]

        result = llm.invoke(messages)

        return {
            "messages": [result],
            "trader_investment_plan": result.content,  # 这里的 content 会带上最终提案字符串
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")
