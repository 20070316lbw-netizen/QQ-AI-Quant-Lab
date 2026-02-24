import time
import json


def create_research_manager(llm, memory):
    def research_manager_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        structured_reports = state.get("structured_reports", {})

        # 1. 核心数学聚合逻辑 (取代主观直觉)
        
        # 权重分配：研究员权重稍高，分析师权重基础化
        # 'bull_researcher', 'bear_researcher', 'market', 'social', 'news', 'fundamentals'
        weights = {
            "bull_researcher": 1.5,
            "bear_researcher": 1.5,
            "market": 1.0,
            "social": 0.8,
            "news": 1.0,
            "fundamentals": 1.2
        }
        
        total_sentiment = 0.0
        total_risk = 0.0
        total_weight = 0.0
        
        calculation_details = []

        for key, weight in weights.items():
            report = structured_reports.get(key)
            if report:
                senti = float(report.get("market_sentiment", 0.0))
                risk = float(report.get("risk_factor", 0.5))
                
                weighted_senti = senti * weight
                weighted_risk = risk * weight
                
                total_sentiment += weighted_senti
                total_risk += weighted_risk
                total_weight += weight
                
                calculation_details.append(f"- {report.get('analyst_name', key)}: 情绪={senti:.2f}, 风险={risk:.2f}, 权重={weight}")

        # 计算最终数字指标
        avg_sentiment = total_sentiment / total_weight if total_weight > 0 else 0.0
        avg_risk = total_risk / total_weight if total_weight > 0 else 0.5
        
        # 决定情绪偏向
        if avg_sentiment > 0.2:
            sentiment_label = "偏多 (BULLISH)"
        elif avg_sentiment < -0.2:
            sentiment_label = "偏空 (BEARISH)"
        else:
            sentiment_label = "中性 (NEUTRAL)"

        # 2. 调用 LLM 仅进行结果的“中文话术整理”，严禁其改变计算出的结论
        details_str = "\n".join(calculation_details)
        summary_prompt = f"""作为研究经理，你已完成多方因素的加权计算：
        
        各方贡献明细：
        {details_str}
        
        最终数学推导结果：
        - 综合情绪分: {avg_sentiment:.2f} (范围 -1 到 1)
        - 建议情绪偏向: {sentiment_label}
        - 平均风险评估: {avg_risk:.2f}
        
        请根据以上硬性数字指标，撰写一份简洁的中文投资情况摘要。
        注意：你**必须**维持数学推导出的结论，严禁自行发挥，也不要直接给出买卖方向指令。
        报告中必须包含：汇总理由、情绪与风险的加权得分拆解。"""
        
        response = llm.invoke(summary_prompt)

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
            "investment_plan": f"### 数字情绪偏向: {sentiment_label} (Sentiment: {avg_sentiment:.2f}, Risk: {avg_risk:.2f})\n\n" + response.content,
        }

    return research_manager_node
