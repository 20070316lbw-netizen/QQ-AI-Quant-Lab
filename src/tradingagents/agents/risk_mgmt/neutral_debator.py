from langchain_core.messages import AIMessage
import time


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
        
        任务：请结合数据，用中文发表一段客观中立的风险分析。识别各方逻辑中的合理性与盲点。
        
        **特别指令：**
        必须在辩论内容结束后，附带一个以 ```json 开启的结构化 JSON 块：
        ```json
        {{
          "decision": "BUY/SELL/HOLD",
          "confidence": 0.0到1.0之间的浮点数,
          "risk_score": 0.0到1.0之间的浮点数
        }}
        ```
言简意赅。
        重点在于辩论而非仅仅呈现数据，你的目标是证明平衡的视角能带来最可靠的结果。请以对话的形式自然陈述，不要使用特殊的格式。"""

        response = llm.invoke(prompt)

        argument = f"中立型分析师: {response.content}"
        structured_reports = state.get("structured_reports", {})
        
        # 尝试提取结构化 JSON
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response.content, re.DOTALL)
        if json_match:
            try:
                report_data = json.loads(json_match.group(1))
                report_data["analyst_name"] = "Neutral Risk Analyst"
                structured_reports["neutral_analyst"] = report_data
            except Exception as e:
                print(f"Failed to parse structured JSON from Neutral Analyst: {e}")

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "neutral_history": neutral_history + "\n" + argument,
            "aggressive_history": risk_debate_state.get("aggressive_history", ""),
            "conservative_history": risk_debate_state.get("conservative_history", ""),
            "latest_speaker": "Neutral",
            "current_neutral_response": argument,
            "current_aggressive_response": risk_debate_state.get(
                "current_aggressive_response", ""
            ),
            "current_conservative_response": risk_debate_state.get(
                "current_conservative_response", ""
            ),
            "count": risk_debate_state["count"] + 1,
        }

        return {
            "risk_debate_state": new_risk_debate_state,
            "structured_reports": structured_reports,
            "messages": [AIMessage(content=argument, name="NeutralAnalyst")]
        }

    return neutral_node
