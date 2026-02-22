import time
import json


def create_risk_manager(llm, memory):
    def risk_manager_node(state) -> dict:

        company_name = state["company_of_interest"]

        history = state["risk_debate_state"]["history"]
        risk_debate_state = state["risk_debate_state"]
        market_research_report = state["market_report"]
        news_report = state.get("news_report", "No news available.")
        fundamentals_report = state.get("fundamentals_report", "No fundamentals available.")
        sentiment_report = state["sentiment_report"]
        trader_plan = state["investment_plan"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = f"""作为风险管理法官，请评估以下辩论并确定最终决策：买入 (Buy)、卖出 (Sell) 或持有 (Hold)。
        
        决策依据：
        - 交易员计划：{trader_plan}
        - 历史教训：{past_memory_str}
        
        风险分析师辩论历史：
        {history}
        
        任务：
        1. 总结各方最强逻辑。
        2. 给出最终建议并说明修正理由（基于交易员原计划）。
        请务必直奔主题，使用中文，且在末尾包含 'FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**'。"""

        response = llm.invoke(prompt)

        new_risk_debate_state = {
            "judge_decision": response.content,
            "history": risk_debate_state["history"],
            "aggressive_history": risk_debate_state["aggressive_history"],
            "conservative_history": risk_debate_state["conservative_history"],
            "neutral_history": risk_debate_state["neutral_history"],
            "latest_speaker": "Judge",
            "current_aggressive_response": risk_debate_state["current_aggressive_response"],
            "current_conservative_response": risk_debate_state["current_conservative_response"],
            "current_neutral_response": risk_debate_state["current_neutral_response"],
            "count": risk_debate_state["count"],
        }

        return {
            "risk_debate_state": new_risk_debate_state,
            "final_trade_decision": response.content,
        }

    return risk_manager_node
