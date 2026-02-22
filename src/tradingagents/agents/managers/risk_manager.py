import time
import json


def create_risk_manager(llm, memory):
    def risk_manager_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        structured_reports = state.get("structured_reports", {})
        kronos_prediction = state.get("kronos_report", "暂无 Kronos 预测数据。")

        # 1. 纯量化风险聚合引擎 (V6.0 Parametric Engine)
        decision_map = {"BUY": 1, "BULLISH": 1, "SELL": -1, "BEARISH": -1, "HOLD": 0, "NEUTRAL": 0}
        bias_weight_map = {"aggressive": 1.2, "neutral": 1.0, "conservative": 0.8}
        
        scores = []
        confidences = []
        risks = []
        biases = []
        valid_reports = 0
        
        details = []

        for key, report in structured_reports.items():
            dec = str(report.get("decision", "")).upper()
            bias = str(report.get("risk_bias", "neutral")).lower()
            if dec in decision_map:
                s = decision_map[dec]
                c = report.get("confidence", 0.5)
                r = report.get("risk_score", 0.5)
                
                # 记录核心因子
                scores.append(s)
                confidences.append(c)
                risks.append(r)
                biases.append(bias)
                valid_reports += 1
                details.append(f"- {report.get('analyst_name', key)}: {dec} (C:{c:.2f}, R:{r:.2f}, B:{bias})")

        # 初始化量化指标
        divergence_index = 0.0
        final_numeric_score = 0.0
        avg_risk = 0.5
        quant_decision = "HOLD"
        final_confidence = 0.0
        compression_factor = 1.0 # 仓位压缩系数

        if valid_reports > 0:
            # 计算基础平均值
            avg_score = sum(scores) / valid_reports
            avg_conf = sum(confidences) / valid_reports
            avg_risk = sum(risks) / valid_reports
            
            # 计算分歧指数 (标准差/方差)
            variance = sum((s - avg_score) ** 2 for s in scores) / valid_reports
            divergence_index = min(variance, 1.0)
            
            # 核心业务逻辑：计算仓位压缩系数 (Compression Factor)
            # 1. 基础惩罚：分歧越大，压缩越狠
            base_compression = 1.0 - (divergence_index * 0.5)
            
            # 2. 偏向惩罚：如果全队偏向 conservative 且风险分数高，额外压缩
            cons_count = sum(1 for b in biases if b == "conservative")
            cons_ratio = cons_count / valid_reports
            bias_penalty = (cons_ratio * avg_risk * 0.4)
            
            compression_factor = max(base_compression - bias_penalty, 0.1)
            
            # 核心加权得分 (结合了置信度均值)
            final_numeric_score = avg_score * avg_conf
            
            # 决策判定
            if final_numeric_score > 0.15:
                quant_decision = "BUY"
            elif final_numeric_score < -0.15:
                quant_decision = "SELL"
            else:
                quant_decision = "HOLD"
                
            # 最终置信度：受分歧指数、平均风险与压缩系数共同制约
            final_confidence = avg_conf * (1 - divergence_index * 0.3) * (1 - avg_risk * 0.2) * compression_factor

        # 2. 生成量化审查报告
        details_str = "\n".join(details)
        prompt = f"""作为风险管理判官 (V6.0 参数化引擎)，你已执行以下数学聚合方案：
        
        底层因子明细 (含 Risk Bias):
        {details_str}
        
        数学推导结果 (Parametric Results):
        - 标准差分歧指数 (DI): {divergence_index:.2f}
        - 综合风险水平: {avg_risk:.2f}
        - 仓位压缩系数 (Compression Factor): {compression_factor:.2f}
        - 最终量化结论: {quant_decision}
        - 最终计算置信度: {final_confidence:.2f}
        
        Kronos 走势预测参考:
        {kronos_prediction[:100]}...
        
        任务：撰写一份专业的中文量化风控报告。
        **特别指令**：
        1. 必须解释为什么 DI 和 Compression Factor 是当前值的逻辑（如：观点高度对立导致压缩）。
        2. 严禁改动 quant_decision 和 final_confidence。
        3. 必须在结尾输出：'FINAL TRANSACTION PROPOSAL: **{quant_decision} (Confidence: {final_confidence:.2f})**'"""

        response = llm.invoke(prompt)

        return {
            "final_trade_decision": response.content,
            "structured_reports": structured_reports, # 同步回传
        }

    return risk_manager_node
