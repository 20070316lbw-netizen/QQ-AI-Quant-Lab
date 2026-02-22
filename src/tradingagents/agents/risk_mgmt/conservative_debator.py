from langchain_core.messages import AIMessage
import time
import json


def create_conservative_debator(llm):
    def conservative_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        conservative_history = risk_debate_state.get("conservative_history", "")

        current_aggressive_response = risk_debate_state.get("current_aggressive_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")

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
            context_str = "参考资料已在首轮提供。请针对辩论历史进行反击。"

        history_lines = history.split("\n")
        if len(history_lines) > 8:
            trimmed_history = "...(历史片段已省略)...\n" + "\n".join(history_lines[-8:])
        else:
            trimmed_history = history

        prompt = f"""你是一名‘保守型风险分析师’。核心职责：识别潜在风险，强调资本保护和极端情况下的生存。

        背景与交易计划：
        {trader_decision}

        补充资源：
        {context_str}

        辩论历史板：
        {trimmed_history}

        对手最新观点：
        激进型：{current_aggressive_response}
        中立型：{current_neutral_response}

        任务：请结合数据，用中文发表一段审慎的辩论。指出激进观点的盲点，强调下行风险。言简意赅。
重点是辩论和批评，以展示低风险策略相对于他们方法的优势。请以对话的形式自然陈述，不要使用特殊的格式。"""

        response = llm.invoke(prompt)

        argument = f"保守型分析师: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "aggressive_history": risk_debate_state.get("aggressive_history", ""),
            "conservative_history": conservative_history + "\n" + argument,
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Conservative",
            "current_aggressive_response": risk_debate_state.get(
                "current_aggressive_response", ""
            ),
            "current_conservative_response": argument,
            "current_neutral_response": risk_debate_state.get(
                "current_neutral_response", ""
            ),
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return conservative_node
