from langchain_core.messages import HumanMessage, RemoveMessage

# Import tools from separate utility files
from tradingagents.agents.utils.core_stock_tools import (
    get_stock_data
)
from tradingagents.agents.utils.technical_indicators_tools import (
    get_indicators
)
from tradingagents.agents.utils.fundamental_data_tools import (
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement
)
from tradingagents.agents.utils.news_data_tools import (
    get_news,
    get_insider_transactions,
    get_global_news
)

from langchain_core.messages import HumanMessage, RemoveMessage, SystemMessage

def create_msg_delete():
    def delete_messages(state):
        """Clean intermediate noise while preserving structured traceability"""
        messages = state.get("messages", [])
        structured_reports = state.get("structured_reports", {})
        
        # 移除当前所有中间消息
        removal_operations = [RemoveMessage(id=m.id) for m in messages if hasattr(m, "id") and m.id]

        # 提炼已完成环节的结构化摘要，为下一环节提供“上帝视角”
        context_parts = []
        for key, report in structured_reports.items():
            name = report.get("analyst_name", key)
            summary = report.get("summary", "无摘要")
            conclusion = report.get("conclusion", "未知")
            context_parts.append(f"【{name}】 核心结论: {conclusion}\n摘要: {summary}")
        
        if context_parts:
            traceable_context = "### 上一环节研究成果汇总（去噪版）\n\n" + "\n\n".join(context_parts)
            # 使用 SystemMessage 注入高度浓缩的上下文
            placeholder = SystemMessage(content=traceable_context)
        else:
            placeholder = HumanMessage(content="初始化完成，请开始分析。")

        return {"messages": removal_operations + [placeholder]}

    return delete_messages


        