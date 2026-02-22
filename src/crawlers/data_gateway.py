"""
统一数据网关 (Data Gateway)
===========================
作为整个量化实验室的底层数据吞吐口，接受来自 Agent 层的请求，
并调度对应的 Provider (如 YFinance, WebCrawler 等) 获取数据。

设计原则：
1. Agent 不与具体网站协议打交道，只向 Gateway 提出 "What I need"。
2. Gateway 封装所有的重试、网络格式转换细节。
"""
from typing import Optional, Dict
from crawlers.providers.yfinance_provider import (
    get_YFin_data_online,
    get_stock_stats_indicators_window,
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
    get_insider_transactions
)
from crawlers.providers.yfinance_news_provider import (
    get_news_yfinance,
    get_global_news_yfinance
)

class DataGateway:
    """提供全套行情、财报与新闻接口的单例门面 (Facade)"""
    
    @staticmethod
    def get_stock_data(symbol: str, start_date: str, end_date: str) -> str:
        """获取股票 OHLCV 数据"""
        return get_YFin_data_online(symbol, start_date, end_date)
        
    @staticmethod
    def get_indicators(symbol: str, indicator: str, curr_date: str, look_back_days: int) -> str:
        """获取技术指标序列"""
        return get_stock_stats_indicators_window(symbol, indicator, curr_date, look_back_days)
        
    @staticmethod
    def get_fundamentals(ticker: str, curr_date: Optional[str] = None) -> str:
        """获取公司基本面概要"""
        return get_fundamentals(ticker, curr_date)
        
    @staticmethod
    def get_balance_sheet(ticker: str, freq: str = "quarterly", curr_date: Optional[str] = None) -> str:
        """获取资产负债表"""
        return get_balance_sheet(ticker, freq, curr_date)

    @staticmethod
    def get_cashflow(ticker: str, freq: str = "quarterly", curr_date: Optional[str] = None) -> str:
        """获取现金流量表"""
        return get_cashflow(ticker, freq, curr_date)
        
    @staticmethod
    def get_income_statement(ticker: str, freq: str = "quarterly", curr_date: Optional[str] = None) -> str:
        """获取利润表"""
        return get_income_statement(ticker, freq, curr_date)

    @staticmethod
    def get_insider_transactions(ticker: str) -> str:
        """获取内幕交易记录"""
        return get_insider_transactions(ticker)
        
    @staticmethod
    def get_stock_news(ticker: str, start_date: str, end_date: str) -> str:
        """获取按股票代码查询的新闻"""
        return get_news_yfinance(ticker, start_date, end_date)
        
    @staticmethod
    def get_global_news(curr_date: str, look_back_days: int = 7, limit: int = 5) -> str:
        """获取宏观全局新闻"""
        return get_global_news_yfinance(curr_date, look_back_days, limit)

# 初始化一个全局实例便于调用
gateway = DataGateway()
