import functools
import time
import json


def create_trader(llm, memory):
    def trader_node(state, name):
        company_name = state["company_of_interest"]
        investment_plan = state["investment_plan"]
        structured_reports = state.get("structured_reports", {})

        # 构建结构化上下文摘要
        summary_parts = []
        for key, report in structured_reports.items():
            name = report.get("analyst_name", key)
            summary_parts.append(f"【{name}】 摘要: {report.get('summary', '')}")
            
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
            "content": f"基于分析师团队的全面评估，这里是为 {company_name} 量身定制的投资计划。该计划结合了当前市场技术趋势、宏观经济指标以及社交媒体情绪。请将此计划作为评估你下一步交易决策的基础。\n\n建议的投资计划：{investment_plan}\n\n请利用这些见解做出明智且具有战略意义的决策。",
        }

        messages = [
            {
                "role": "system",
                "content": f"""你是一名交易计划执行者，负责分析市场数据并做出最终投资决策。请根据你的分析，提供具体决策：买入 (Buy)、卖出 (Sell) 或持有 (Hold)。
                
                **核心指令：**
                请以坚定的态度结束你的响应，并务必在响应末尾包含以下量化格式的建议：
                'FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL (Confidence: 0.XX)**'
                其中 0.XX 是你对该决策的置信度（请参考风险判官给出的分歧指数进行微调）。
                
                别忘了利用过去决策中的经验教训，从错误中学习。以下是你在类似情况下交易时的一些反思和教训：{past_memory_str}""",
            },
            context,
        ]
        
        # 增加逻辑：确保输入的消息中包含判官的意见（辅助 LLM 参考置信度）
        if state.get("final_trade_decision"):
            messages.insert(1, {"role": "assistant", "content": f"风险判官建议与分歧评估：\n{state['final_trade_decision']}"})


        result = llm.invoke(messages)

        return {
            "messages": [result],
            "trader_investment_plan": result.content,
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")
