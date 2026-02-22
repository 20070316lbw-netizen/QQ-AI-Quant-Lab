import time
import json


def create_neutral_debator(llm):
    def neutral_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        neutral_history = risk_debate_state.get("neutral_history", "")

        current_aggressive_response = risk_debate_state.get("current_aggressive_response", "")
        current_conservative_response = risk_debate_state.get("current_conservative_response", "")

        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        trader_decision = state["trader_investment_plan"]

        # 动态瘦身
        is_rebuttal = risk_debate_state["count"] > 0
        if not is_rebuttal:
            context_str = f"市场报告：{market_research_report}\n基本面：{fundamentals_report}\n新闻：{news_report}\n情绪：{sentiment_report}"
        else:
            context_str = "参考资料已在首轮提供。请针对辩论历史进行协调。"

        history_lines = history.split("\n")
        if len(history_lines) > 8:
            trimmed_history = "...(历史片段已省略)...\n" + "\n".join(history_lines[-8:])
        else:
            trimmed_history = history

        prompt = f"""你是一名‘中立型风险分析师’。核心职责：平衡风险与回报，客观评估双方逻辑，寻找中间地带。
        
        背景与交易计划：
        {trader_decision}
        
        补充资源：
        {context_str}
        
        辩论历史板：
        {trimmed_history}
        
        各方最新观点：
        激进型：{current_aggressive_response}
        保守型：{current_conservative_response}
        
        任务：请以中立客观的角度，用中文对双方论点进行复盘和调和。指出双方各自的合理性与偏见。言简意赅。
        重点在于辩论而非仅仅呈现数据，你的目标是证明平衡的视角能带来最可靠的结果。请以对话的形式自然陈述，不要使用特殊的格式。"""

        response = llm.invoke(prompt)

        argument = f"中立型分析师: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "aggressive_history": risk_debate_state.get("aggressive_history", ""),
            "conservative_history": risk_debate_state.get("conservative_history", ""),
            "neutral_history": neutral_history + "\n" + argument,
            "latest_speaker": "Neutral",
            "current_aggressive_response": risk_debate_state.get(
                "current_aggressive_response", ""
            ),
            "current_conservative_response": risk_debate_state.get("current_conservative_response", ""),
            "current_neutral_response": argument,
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return neutral_node
