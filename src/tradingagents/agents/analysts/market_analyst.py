from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from tradingagents.agents.utils.agent_utils import get_stock_data, get_indicators
from tradingagents.agents.utils.kronos_tools import get_market_prediction
from tradingagents.agent_config import get_config


def create_market_analyst(llm):

    def market_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        tools = [
            get_stock_data,
            get_indicators,
            get_market_prediction,
        ]

        # 动态精简提示词：如果已经有报告内容，说明进入了总结阶段，移除冗余的工具列表
        has_data = len(state.get("messages", [])) > 2 # 粗略判断是否已执行过工具调用
        
        if not has_data:
            system_message = (
                """你是一名资深的证券交易助手。你的任务是从以下列表中选择最多 **8 个** 互补指标进行深度剖析：
                移动平均线: close_50_sma, close_200_sma, close_10_ema
                MACD 相关: macd, macds, macdh
                动量指标: rsi
                波动率指标: boll, boll_ub, boll_lb, atr
                成交量指标: vwma
                重要：**OHLCV 价格数据通过 `get_stock_data` 获取，严禁通过 `get_indicators` 重复查询 close/open 等基础价格字段。**
                你还可以调用 `get_market_prediction` 工具进行趋势预测。"""
            )
        else:
            system_message = """数据已获取。请结合上下文中的工具执行结果，撰写一篇专业详尽的中文分析报告。全程严禁输出英文段落。
            
            **特别指令：**
            在报告正文结束后，请必须附带一个以 ```json 开启的结构化 JSON 块，包含以下字段：
            {
              "summary": "简短的中文结论总结",
              "key_metrics": {"指标名": "值"},
              "decision": "BUY/SELL/HOLD",
              "confidence": 0.0到1.0之间的浮点数,
              "risk_score": 0.0到1.0之间的浮点数 (1.0表示极高风险)
            }"""

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是一个专业的 AI 投资助手的成员，正在与其他成员协作。"
                    " 请使用提供的工具逐步解决问题。"
                    " 如果你无法完全回答，也没关系；拥有不同工具的其他助手会接手你的工作。"
                    " 尽量执行你能做的部分来推进进度。"
                    " 如果你或其他助手得出了【最终交易建议：买入/持有/卖出】，请在响应开头明确标注"
                    " 'FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**'，以便团队停止工作。"
                    " 你拥有的工具: {tool_names}。\n{system_message}"
                    " 参考信息：当前日期是 {current_date}。我们要分析的公司是 {ticker} (标的代码)"
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        report = ""
        structured_reports = state.get("structured_reports", {})

        if len(result.tool_calls) == 0:
            report = result.content
            # 尝试从正文中提取 JSON 结构化块
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', report, re.DOTALL)
            if json_match:
                try:
                    report_data = json.loads(json_match.group(1))
                    report_data["analyst_name"] = "Market Analyst"
                    # 确保字段名称对齐
                    if "conclusion" in report_data and "decision" not in report_data:
                        report_data["decision"] = report_data.pop("conclusion")
                    
                    structured_reports["market"] = report_data
                except Exception as e:
                    print(f"Failed to parse structured JSON from Market Analyst: {e}")

        # 提取 Kronos 预测结果并持久化到 state 中
        kronos_report = state.get("kronos_report", "")
        # ... (check messages in state)
        for msg in reversed(state.get("messages", [])):
            if getattr(msg, "type", "") == "tool" and "### Kronos AI Prediction" in (getattr(msg, "content", "") or ""):
                kronos_report = msg.content
                break
        
        # 如果当前结果就是最终报告，也要检查它是否包含预测信息（以防万一）
        if report and "### Kronos AI Prediction" in report:
            kronos_report = report

        return {
            "messages": [result],
            "market_report": report,
            "kronos_report": kronos_report,
            "structured_reports": structured_reports,
        }

    return market_analyst_node
