import time
import json


def create_research_manager(llm, memory):
    def research_manager_node(state) -> dict:
        history = state["investment_debate_state"].get("history", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        investment_debate_state = state["investment_debate_state"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = f"""作为投资组合经理和辩论主持人，你的职责是批判性地评估本轮辩论并做出最终决定：选择支持看空分析师、看多分析师，或者在有强有力理由的情况下选择“持有”。

请简明扼要地总结双方的核心观点，关注最具说服力的证据或逻辑。你的建议——买入 (Buy)、卖出 (Sell) 或持有 (Hold)——必须清晰且具有可操作性。不要仅仅因为双方都有理就默认选择“持有”；必须根据辩论中最有力的论据做出决断。

此外，请为交易员制定一份详细的中文投资计划，包括：
1. 你的建议：一个由最具说服力的论据支持的决定性立场。
2. 理由：解释为什么这些论据会导致你的结论。
3. 战略行动：实施该建议的具体步骤。

请考虑你过去在类似情况下的错误。利用这些洞察来改进你的决策，并确保你在不断学习和进步。请以对话的形式、自然地陈述你的分析，不要使用特殊的格式（如特殊的 Markdown 标题等）。

以下是你过去对错误的思考：
\"{past_memory_str}\"

以下是辩论过程：
辩论历史：
{history}

请务必全程使用中文进行总结和计划制定。"""
        response = llm.invoke(prompt)

        new_investment_debate_state = {
            "judge_decision": response.content,
            "history": investment_debate_state.get("history", ""),
            "bear_history": investment_debate_state.get("bear_history", ""),
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": response.content,
            "count": investment_debate_state["count"],
        }

        return {
            "investment_debate_state": new_investment_debate_state,
            "investment_plan": response.content,
        }

    return research_manager_node
