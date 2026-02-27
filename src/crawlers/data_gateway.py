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
    
    # 【Phase 9 黑天鹅封闭测试引擎】物理隔离与旁路设定
    offline_mode: bool = False
    offline_data_dir: str = "src/backtest/extreme_data"
    offline_event_name: str = "2008_Subprime_Crisis" # or 2020_Covid_Crash
    
    @staticmethod
    def _log_fetch(msg):
        from rich.console import Console
        Console().print(f"[dim grey]   ↳ 🕸️ {msg}[/dim grey]")

    @staticmethod
    def get_stock_data(symbol: str, start_date: str, end_date: str) -> str:
        """获取股票 OHLCV 数据 (支持离线物理阻断模式)"""
        if DataGateway.offline_mode:
            import os
            import pandas as pd
            from datetime import datetime
            
            DataGateway._log_fetch(f"[OFFLINE] 正在从本地封闭舱 {DataGateway.offline_event_name} 提取 {symbol} 的重播数据...")
            file_path = os.path.join(DataGateway.offline_data_dir, DataGateway.offline_event_name, f"{symbol}_price.csv")
            if not os.path.exists(file_path):
                return f"No local data found for symbol '{symbol}' in event {DataGateway.offline_event_name}"
            
            try:
                # 读取本地保存的完整文件
                df = pd.read_csv(file_path, index_col='Date', parse_dates=True)
                # 按照 start_date 进行截断，而对于 end_date 则尽可能返回到切片最后，不强求对齐
                start_dt = pd.to_datetime(start_date)
                mask = (df.index >= start_dt) 
                
                # 如果模型传了 end_date，我们也尽力切断，防止穿越
                if end_date:
                    end_dt = pd.to_datetime(end_date)
                    mask = mask & (df.index <= end_dt)
                    
                sliced_df = df.loc[mask].copy()
                
                if sliced_df.empty:
                     # 极度宽容模式：如果由于模型生成的日期比样本池最新一条还晚，则直接返回全表，保活为主
                     sliced_df = df.copy()
                     
                csv_string = sliced_df.to_csv()
                header = f"# [OFFLINE MOCK] Stock data for {symbol.upper()} from {start_date} to {end_date}\n"
                header += f"# Total records: {len(sliced_df)}\n\n"
                return header + csv_string
            except Exception as e:
                return f"Error reading mock offline data: {e}"
        else:
            DataGateway._log_fetch(f"正在从 yfinance 抓取 {symbol} 历史行情 ({start_date} ~ {end_date})...")
            return get_YFin_data_online(symbol, start_date, end_date)
        
    @staticmethod
    def get_indicators(symbol: str, indicator: str, curr_date: str, look_back_days: int) -> str:
        """获取技术指标序列"""
        DataGateway._log_fetch(f"正在计算指标: {indicator} (回溯 {look_back_days} 天)...")
        return get_stock_stats_indicators_window(symbol, indicator, curr_date, look_back_days)
        
    @staticmethod
    def get_fundamentals(ticker: str, curr_date: Optional[str] = None) -> str:
        """获取公司基本面概要"""
        DataGateway._log_fetch(f"正在抓取 {ticker} 基本面核心指标...")
        return get_fundamentals(ticker, curr_date)
        
    @staticmethod
    def get_balance_sheet(ticker: str, freq: str = "quarterly", curr_date: Optional[str] = None) -> str:
        """获取资产负债表"""
        DataGateway._log_fetch(f"正在解析 {ticker} 资产负债表 ({freq})...")
        return get_balance_sheet(ticker, freq, curr_date)

    @staticmethod
    def get_cashflow(ticker: str, freq: str = "quarterly", curr_date: Optional[str] = None) -> str:
        """获取现金流量表"""
        DataGateway._log_fetch(f"正在解析 {ticker} 现金流量表 ({freq})...")
        return get_cashflow(ticker, freq, curr_date)
        
    @staticmethod
    def get_income_statement(ticker: str, freq: str = "quarterly", curr_date: Optional[str] = None) -> str:
        """获取利润表"""
        DataGateway._log_fetch(f"正在解析 {ticker} 利润表 ({freq})...")
        return get_income_statement(ticker, freq, curr_date)

    @staticmethod
    def get_insider_transactions(ticker: str) -> str:
        """获取内幕交易记录"""
        DataGateway._log_fetch(f"正在检查 {ticker} 的内幕交易信息...")
        return get_insider_transactions(ticker)
        
    @staticmethod
    def get_stock_news(ticker: str, start_date: str, end_date: str) -> str:
        """获取新闻 (支持黑天鹅恐慌假新闻播报)"""
        if DataGateway.offline_mode:
            import os
            import json
            DataGateway._log_fetch(f"[OFFLINE] 正在从避难所提取 {DataGateway.offline_event_name} 期间的恐慌性新闻快照...")
            news_file = os.path.join(DataGateway.offline_data_dir, DataGateway.offline_event_name, "news.json")
            if os.path.exists(news_file):
                try:
                    with open(news_file, "r", encoding='utf-8') as f:
                        news_data = json.load(f)
                        # 将 JSON 拼接为分析师可以读懂的字符串
                        output = f"# MOCK NEWS for {DataGateway.offline_event_name}\n"
                        for item in news_data:
                            output += f"- [{item['date']}] {item['title']} : {item['summary']}\n"
                        return output
                except Exception as e:
                    return f"Error reading offline news: {e}"
            else:
                return f"[OFFLINE] No panic news file found for {DataGateway.offline_event_name}"
        else:
            DataGateway._log_fetch(f"正在检索 {ticker} 相关媒体报道与社盟讨论...")
            return get_news_yfinance(ticker, start_date, end_date)
        
    @staticmethod
    def get_global_news(curr_date: str, look_back_days: int = 7, limit: int = 5) -> str:
        """获取宏观全局新闻"""
        DataGateway._log_fetch("正在同步全球宏观经济资讯...")
        return get_global_news_yfinance(curr_date, look_back_days, limit)

# 初始化一个全局实例便于调用
gateway = DataGateway()
