import time
import json


def create_risk_manager(llm, memory):
    def risk_manager_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        structured_reports = state.get("structured_reports", {})
        kronos_prediction = state.get("kronos_report", "暂无 Kronos 预测数据。")

        # 1. 深度量化决策引擎 (DI & Consensus Integration)
        decision_map = {"BUY": 1, "BULLISH": 1, "SELL": -1, "BEARISH": -1, "HOLD": 0, "NEUTRAL": 0}
        
        scores = []
        confidences = []
        risks = []
        valid_reports = 0
        
        details = []

        for key, report in structured_reports.items():
            dec = str(report.get("decision", "")).upper()
            if dec in decision_map:
                s = decision_map[dec]
                c = report.get("confidence", 0.5)
                r = report.get("risk_score", 0.5)
                scores.append(s)
                confidences.append(c)
                risks.append(r)
                valid_reports += 1
                details.append(f"- {report.get('analyst_name', key)}: {dec} (C:{c:.2f}, R:{r:.2f})")

        # 初始化默认值
        divergence_index = 0.0
        buy_ratio = 0.0
        final_numeric_score = 0.0
        avg_risk = 0.5
        quant_decision = "HOLD"
        final_confidence = 0.0

        if valid_reports > 0:
            avg_score = sum(scores) / valid_reports
            variance = sum((s - avg_score) ** 2 for s in scores) / valid_reports
            divergence_index = min(variance, 1.0)
            
            buy_count = sum(1 for s in scores if s > 0)
            buy_ratio = buy_count / valid_reports
            
            avg_risk = sum(risks) / valid_reports
            avg_conf = sum(confidences) / valid_reports
            
            # 核心加权得分 (结合了置信度均值)
            final_numeric_score = avg_score * avg_conf
            
            # 根据数学结果直接锁定决策方向
            if final_numeric_score > 0.15:
                quant_decision = "BUY"
            elif final_numeric_score < -0.15:
                quant_decision = "SELL"
            else:
                quant_decision = "HOLD"
                
            # 置信度下修：分歧越大、风险越高，置_信度越低
            final_confidence = avg_conf * (1 - divergence_index * 0.4) * (1 - avg_risk * 0.3)

        # 2. 生成最终报告（LLM 仅负责话术编排）
        details_str = "\n".join(details)
        prompt = f"""作为风险管理判官，你已执行以下数学聚合方案：
        
        底层因子明细：
        {details_str}
        
        数学推导结果：
        - 全队分歧指数 (DI): {divergence_index:.2f}
        - 方向一致性 (买方占比): {buy_ratio*100:.0f}%
        - 综合风险评级: {avg_risk:.2f}
        - 最终量化结论: {quant_decision} (最终计算出的置信度: {final_confidence:.2f})
        
        参考预测数据：
        {kronos_prediction[:100]}...
        
        请撰写一份最终的中文风控审查报告。
        **硬性限制**：
        - 你**必须**在结尾输出：'FINAL TRANSACTION PROPOSAL: **{quant_decision} (Confidence: {final_confidence:.2f})**'
        - 你严禁修改上述计算得出的 {quant_decision} 结论。
        报告内容应着重于解释这些数字所反映的市场实质。"""

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
