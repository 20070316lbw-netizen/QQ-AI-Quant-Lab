import time
import json


def create_aggressive_debator(llm):
    def aggressive_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        aggressive_history = risk_debate_state.get("aggressive_history", "")

        current_conservative_response = risk_debate_state.get("current_conservative_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")

        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        trader_decision = state["trader_investment_plan"]

        # 动态瘦身：仅在首轮完整展示报告
        is_rebuttal = risk_debate_state["count"] > 0
        if not is_rebuttal:
            context_str = f"市场报告：{market_research_report}\n基本面：{fundamentals_report}\n新闻：{news_report}\n情绪：{sentiment_report}"
        else:
            context_str = "参考资料已在首轮提供。请针对辩论历史进行反击。"

        # 历史记录修剪
        history_lines = history.split("\n")
        if len(history_lines) > 8:
            trimmed_history = "...(历史片段已省略)...\n" + "\n".join(history_lines[-8:])
        else:
            trimmed_history = history

        prompt = f"""你是一名‘激进型风险分析师’。核心职责：捍卫高回报机会，挑战保守意见。
        
        背景与交易计划：
        {trader_decision}
        
        补充资源：
        {context_str}
        
        辩论历史板：
        {trimmed_history}
        
        对手最新观点：
        保守型：{current_conservative_response}
        中立型：{current_neutral_response}
        
        任务：请结合数据，用中文发表一段具有攻击性的辩论。反驳他们的保守逻辑，重申高风险策略的价值。言简意赅，直击要害。"""

        response = llm.invoke(prompt)

        argument = f"激进型分析师: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "aggressive_history": aggressive_history + "\n" + argument,
            "conservative_history": risk_debate_state.get("conservative_history", ""),
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Aggressive",
            "current_aggressive_response": argument,
            "current_conservative_response": risk_debate_state.get("current_conservative_response", ""),
            "current_neutral_response": risk_debate_state.get(
                "current_neutral_response", ""
            ),
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return aggressive_node
