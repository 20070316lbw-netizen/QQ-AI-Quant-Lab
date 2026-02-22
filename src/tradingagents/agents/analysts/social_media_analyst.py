from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from tradingagents.agents.utils.agent_utils import get_news
from tradingagents.agent_config import get_config


def create_social_media_analyst(llm):
    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        tools = [
            get_news,
        ]

        # 动态瘦身：进入汇总阶段后移除冗余指令
        has_data = len(state.get("messages", [])) > 2
        if not has_data:
            system_message = (
                "你是一名舆情监控分析师。请使用 `get_news` 工具搜索社媒讨论、情绪波动及最新动态。请搜集多方证据，不要泛泛而谈。"
            )
        else:
            system_message = """社媒与舆情数据已获取。请撰写一份详尽的中文情绪分析报告并附带核心要点表。全程严禁输出英文。
            
            **特别指令：**
            在报告正文结束后，请必须附带一个以 ```json 开启的结构化 JSON 块，包含以下字段：
            {
              "summary": "简短的中文情绪总结",
              "key_metrics": {"情绪分": "值", "热门话题": "..."},
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
                    " 参考信息：当前日期是 {current_date}。我们要分析的公司是 {ticker}"
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
                    report_data["analyst_name"] = "Social Media Analyst"
                    if "conclusion" in report_data and "decision" not in report_data:
                        report_data["decision"] = report_data.pop("conclusion")
                    structured_reports["social"] = report_data
                except Exception as e:
                    print(f"Failed to parse structured JSON from Social Media Analyst: {e}")

        return {
            "messages": [result],
            "sentiment_report": report,
            "structured_reports": structured_reports,
        }

    return social_media_analyst_node
