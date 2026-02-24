import time
import json


def create_risk_manager(llm, memory):
    def risk_manager_node(state) -> dict:
        risk_debate_state = state.get("risk_debate_state", {})
        structured_reports = state.get("structured_reports", {})
        kronos_prediction = state.get("kronos_report", "暂无 Kronos 预测数据。")

        # 1. 纯量化风险聚合引擎 (V7.0 Sentiment & Risk)
        sentiments = []
        risks = []
        valid_reports = 0
        
        details = []

        for key, report in structured_reports.items():
            if key == "system_metrics": continue
            senti = float(report.get("market_sentiment", 0.0))
            risk = float(report.get("risk_factor", 0.5))
            
            # 记录核心因子
            sentiments.append(senti)
            risks.append(risk)
            valid_reports += 1
            details.append(f"- {report.get('analyst_name', key)}: (Senti:{senti:.2f}, Risk:{risk:.2f})")

        # 初始化量化指标
        divergence_index = 0.0
        avg_sentiment = 0.0
        avg_risk = 0.5
        final_risk = 0.5

        if valid_reports > 0:
            # 计算基础平均值
            avg_sentiment = sum(sentiments) / valid_reports
            avg_risk = sum(risks) / valid_reports
            
            # 计算情绪分歧指数 (方差)
            variance = sum((s - avg_sentiment) ** 2 for s in sentiments) / valid_reports
            divergence_index = min(variance, 1.0)
            
            # 核心业务逻辑：分歧越大，增加系统的不可抗力风险
            final_risk = min(avg_risk + (divergence_index * 0.4), 1.0)

        # 缓存给 trader 的全系统通用度量
        structured_reports["system_metrics"] = {
            "analyst_name": "System Metrics",
            "summary": "最终全局情绪和风险参数",
            "key_metrics": {},
            "market_sentiment": float(avg_sentiment),
            "risk_factor": float(final_risk)
        }

        # 2. 生成量化审查报告
        details_str = "\n".join(details)
        prompt = f"""作为风险管理判官 (V7.0 参数化引擎)，你已执行以下数学聚合方案：
        
        底层因子明细:
        {details_str}
        
        数学推导结果 (Parametric Results):
        - 情绪分歧指数 (DI, 越高代表内部共识越差): {divergence_index:.2f}
        - 综合情绪水平: {avg_sentiment:.2f}
        - 基础平均风险: {avg_risk:.2f}
        - 最终全局环境风险 (融合分歧惩罚): {final_risk:.2f}
        
        Kronos 走势预测参考:
        {kronos_prediction[:100]}...
        
        任务：撰写一份专业的中文量化风控报告。
        **特别指令**：
        1. 必须解释为什么 DI 和最终风险值是当前值的逻辑（如：观点高度对立导致系统风险拉升）。
        2. 严禁改动最终推导的数值，这是底层量化的硬性规定。
        3. 严禁在报告中直接下达 BUY/SELL/HOLD 的决策。
        4. 必须在结尾输出：'FINAL RISK ASSESSMENT COMPILED'。"""

        response = llm.invoke(prompt)

        return {
            "final_trade_decision": response.content,
            "structured_reports": structured_reports, # 同步回传
        }

    return risk_manager_node
