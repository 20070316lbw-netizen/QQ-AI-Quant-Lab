# -*- coding: utf-8 -*-
"""
配置模块 - Configuration Module
================================

存放所有配置常量和预定义主题

实现原理说明:
-------------
本程序主要支持以下功能：
1. 默认使用 DuckDuckGo 原生搜索接口抓取新闻。
2. 同时兼容通过调用 z-ai CLI 命令行工具。
3. 获取搜索结果后解析为结构化的 JSON 数据以便后续处理。
"""

from typing import Dict, List

# ============================================================
# 搜索引擎配置
# ============================================================

# 搜索来源配置: "duckduckgo" (本地原生) 或 "z-ai" (外部CLI)
SEARCH_SOURCE = "duckduckgo"

# CLI命令配置 (仅当 SEARCH_SOURCE="z-ai" 时使用)
CLI_COMMAND = "z-ai"
CLI_FUNCTION_NAME = "web_search"
DEFAULT_TIMEOUT = 90  # 搜索超时时间(秒)
DEFAULT_NUM_RESULTS = 10  # 默认返回结果数量


# ============================================================
# LLM配置 (预留)
# ============================================================

LLM_CONFIG = {
    "enabled": False,  # 是否启用LLM分析
    "model": "default",  # 使用的模型
    "max_tokens": 2000,  # 最大token数
    "temperature": 0.7,  # 温度参数
}

# LLM分析功能开关
LLM_FEATURES = {
    "summarize": False,      # 新闻摘要
    "sentiment": False,      # 情感分析
    "keywords": False,       # 关键词提取
    "category": False,       # 智能分类
    "importance": False,     # 重要性评估
}


# ============================================================
# 财经新闻主题配置
# ============================================================

FINANCE_TOPICS: Dict[str, str] = {
    "股市": "股市行情 股票市场 A股 港股 美股",
    "基金": "基金投资 公募基金 私募基金 ETF基金",
    "债券": "债券市场 国债 企业债 债券基金",
    "外汇": "外汇市场 汇率 美元指数 人民币汇率",
    "期货": "期货市场 商品期货 股指期货 期货交易",
    "银行": "银行理财 银行动态 存款利率 贷款利率",
    "保险": "保险行业 保险产品 保险公司 保险理赔",
    "房产": "房地产市场 房价走势 楼市政策 房产投资",
    "科技": "科技财经 科技公司 互联网经济 数字经济",
    "宏观": "宏观经济 经济数据 GDP CPI PPI",
    "国际": "国际财经 全球经济 国际市场 贸易动态",
    "公司": "上市公司 公司财报 企业动态 并购重组"
}

# 主题分类 (用于LLM智能分类)
TOPIC_CATEGORIES: List[str] = list(FINANCE_TOPICS.keys())


# ============================================================
# 输出配置
# ============================================================

DEFAULT_OUTPUT_DIR = "./news_data"
JSON_INDENT = 2
NEWS_DISPLAY_LIMIT = 10


# ============================================================
# 文件名模板
# ============================================================

FILENAME_TEMPLATES = {
    "single_topic": "{topic}_news.json",
    "keyword": "{keyword}_news.json",
    "all_topics": "all_finance_news_{timestamp}.json",
    "today": "today_headlines_{timestamp}.json",
    "default": "finance_news_{timestamp}.json"
}
