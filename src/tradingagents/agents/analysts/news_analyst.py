from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from tradingagents.agents.utils.agent_utils import get_news, get_global_news
from tradingagents.agent_config import get_config


def create_news_analyst(llm):
    def news_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        tools = [
            get_news,
            get_global_news,
        ]

        # 动态瘦身：如果已经执行过工具，进入汇总阶段，则移除详细工具指令
        has_data = len(state.get("messages", [])) > 2
        if not has_data:
            system_message = (
                "你是一名资深的新闻研究员。请使用提供的工具：`get_news` (个股) 或 `get_global_news` (全球宏观) 抓取关键资讯。严禁空谈，必须基于事实。"
            )
        else:
            system_message = "数据已获取。请结合上下文，撰写详尽的中文新闻与宏观分析报告。末尾必须附带摘要表格。全程严禁输出英文段落。"

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是一个专业的 AI 投资补手的成员，正在与其他成员协作。"
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

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "news_report": report,
        }

    return news_analyst_node
