import time
import json


def create_research_manager(llm, memory):
    def research_manager_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        structured_reports = state.get("structured_reports", {})

        # 1. 核心数学聚合逻辑 (取代主观直觉)
        decision_map = {"BUY": 1, "BULLISH": 1, "SELL": -1, "BEARISH": -1, "HOLD": 0, "NEUTRAL": 0}
        
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
        
        total_score = 0
        total_weight = 0
        confidences = []
        risk_scores = []
        
        calculation_details = []

        for key, weight in weights.items():
            report = structured_reports.get(key)
            if report:
                dec = str(report.get("decision", "")).upper()
                conf = report.get("confidence", 0.5)
                risk = report.get("risk_score", 0.5)
                
                point = decision_map.get(dec, 0)
                weighted_point = point * conf * weight
                
                total_score += weighted_point
                total_weight += weight
                confidences.append(conf)
                risk_scores.append(risk)
                
                calculation_details.append(f"- {report.get('analyst_name', key)}: 决策={dec}, 置信度={conf:.2f}, 风险={risk:.2f}, 贡献分={weighted_point:.2f}")

        # 计算最终数字指标
        final_numeric_score = total_score / total_weight if total_weight > 0 else 0
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0.5
        
        # 决定方向
        if final_numeric_score > 0.2:
            final_decision = "BUY"
        elif final_numeric_score < -0.2:
            final_decision = "SELL"
        else:
            final_decision = "HOLD"

        # 2. 调用 LLM 仅进行结果的“中文话术整理”，严禁其改变计算出的结论
        details_str = "\n".join(calculation_details)
        summary_prompt = f"""作为研究经理，你已完成多方因素的加权计算：
        
        各方贡献明细：
        {details_str}
        
        最终数学推导结果：
        - 聚合得分: {final_numeric_score:.2f} (范围 -1 到 1)
        - 建议方向: {final_decision}
        - 平均置信度: {avg_confidence:.2f}
        - 综合风险值: {avg_risk:.2f}
        
        请根据以上硬性数字指标，撰写一份简洁的中文投资计划摘要。
        注意：你**必须**维持数学推导出的 {final_decision} 结论，严禁自行发挥。
        报告中必须包含：汇总理由、关键得分拆解。"""
        
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
            "investment_plan": f"### 数字聚合决策: {final_decision} (Score: {final_numeric_score:.2f})\n\n" + response.content,
        }

    return research_manager_node
