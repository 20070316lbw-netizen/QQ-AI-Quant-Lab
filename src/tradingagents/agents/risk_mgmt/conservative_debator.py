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

        prompt = f"""你是一名‘保守型风险分析师’。核心职责：发现潜在风险，质疑过度乐观的预期。
        
        背景与交易计划：
        {trader_decision}
        
        补充资源：
        {context_str}
        
        辩论历史板：
        {trimmed_history}
        
        对手最新观点：
        激进型：{current_aggressive_response}
        中立型：{current_neutral_response}
        
        任务：请结合数据，用中文发表一段保守谨慎的风控建议。针对现有的看多逻辑，寻找隐藏的风险死角。
        
        **特别指令：**
        必须在辩论内容结束后，附带一个以 ```json 开启的结构化 JSON 块：
        {{
          "decision": "BUY/SELL/HOLD",
          "confidence": 0.0到1.0之间的浮点数,
          "risk_score": 0.0到1.0之间的浮点数
        }}"""

        response = llm.invoke(prompt)

        argument = f"保守型分析师: {response.content}"
        structured_reports = state.get("structured_reports", {})
        
        # 尝试提取结构化 JSON
        import re
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response.content, re.DOTALL)
        if json_match:
            try:
                report_data = json.loads(json_match.group(1))
                report_data["analyst_name"] = "Conservative Risk Analyst"
                structured_reports["conservative_analyst"] = report_data
            except Exception as e:
                print(f"Failed to parse structured JSON from Conservative Analyst: {e}")

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

        return {
            "risk_debate_state": new_risk_debate_state,
            "structured_reports": structured_reports,
            "messages": [AIMessage(content=argument, name="ConservativeAnalyst")]
        }

    return conservative_node
