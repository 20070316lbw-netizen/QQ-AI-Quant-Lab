from langchain_core.messages import AIMessage
import time
import json


def create_bear_researcher(llm, memory):
    def bear_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bear_history = investment_debate_state.get("bear_history", "")

        current_response = investment_debate_state.get("current_response", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        # 动态瘦身：如果辩论已经进行，减小背景资料的权重
        is_rebuttal = investment_debate_state["count"] > 0
        
        if not is_rebuttal:
            context_str = f"市场研究报告：{market_research_report}\n社交媒体情绪报告：{sentiment_report}\n最新全球事务新闻：{news_report}\n公司基本面报告：{fundamentals_report}"
        else:
            context_str = "参考资料已在首轮提供。请重点针对以下最新辩论历史进行反驳。"

        # 历史记录修剪：仅保留最近 3 轮
        history_lines = history.split("\n")
        if len(history_lines) > 6:
            trimmed_history = "...(早期辩论已省略)...\n" + "\n".join(history_lines[-6:])
        else:
            trimmed_history = history

        prompt = f"""你是一名看空分析师 (Bear Analyst)。你的任务是提出反对投资该股票的论点。
        
        {context_str}
        
        辩论历史记录 (精简版):
        {trimmed_history}
        
        上一个看多论点：{current_response}
        来自类似情况的教训：{past_memory_str}
        
        请发表一段短小精悍、直击要害的中文看空论辩。严禁输出英文，严禁重复废话。
        
        **特别指令：**
        在辩论内容结束后，必须附带一个以 ```json 开启的结构化 JSON 块，包含：
        {
          "decision": "SELL",
          "confidence": 0.0到1.0之间的浮点数 (请评估看空逻辑的强度),
          "risk_score": 0.0到1.0之间的浮点数 (请评估潜在风险)
        }"""
        

        response = llm.invoke(prompt)

        argument = f"看空分析师: {response.content}"
        structured_reports = state.get("structured_reports", {})
        
        # 尝试提取结构化 JSON
        import re
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response.content, re.DOTALL)
        if json_match:
            try:
                report_data = json.loads(json_match.group(1))
                report_data["analyst_name"] = "Bear Analyst"
                structured_reports["bear_researcher"] = report_data
            except Exception as e:
                print(f"Failed to parse structured JSON from Bear Researcher: {e}")

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bear_history": bear_history + "\n" + argument,
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
        }

        return {
            "investment_debate_state": new_investment_debate_state,
            "structured_reports": structured_reports,
            "messages": [AIMessage(content=argument, name="BearResearcher")]
        }

    return bear_node
