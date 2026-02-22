from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from tradingagents.agents.utils.agent_utils import get_fundamentals, get_balance_sheet, get_cashflow, get_income_statement, get_insider_transactions
from tradingagents.agent_config import get_config


def create_fundamentals_analyst(llm):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        tools = [
            get_fundamentals,
            get_balance_sheet,
            get_cashflow,
            get_income_statement,
        ]

        # 动态瘦身：如果数据已获取，切换至简效汇报模式
        has_data = len(state.get("messages", [])) > 2
        if not has_data:
            system_message = (
                "你是一名资深的基本面分析师。请使用 `get_fundamentals`, `get_balance_sheet`, `get_cashflow` 等工具获取财报现状。严禁主观臆断。"
            )
        else:
            system_message = """财报数据已获取。请撰写一份全方位的中文基本面深度报告，并附带核心要点表格。全程严禁输出英文。
            
            **特别指令：**
            在报告正文结束后，请必须附带一个以 ```json 开启的结构化 JSON 块，包含以下字段：
            {
              "summary": "简短的中文财报总结",
              "key_metrics": {"营收增长": "值", "净利润": "值", "自由现金流": "值"},
              "decision": "BULLISH/BEARISH/NEUTRAL",
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
                    " 参考信息：当前日期是 {current_date}。我们要分析的公司标的是 {ticker}"
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
                    report_data["analyst_name"] = "Fundamentals Analyst"
                    if "conclusion" in report_data and "decision" not in report_data:
                        report_data["decision"] = report_data.pop("conclusion")
                    structured_reports["fundamentals"] = report_data
                except Exception as e:
                    print(f"Failed to parse structured JSON from Fundamentals Analyst: {e}")

        return {
            "messages": [result],
            "fundamentals_report": report,
            "structured_reports": structured_reports,
        }

    return fundamentals_analyst_node
