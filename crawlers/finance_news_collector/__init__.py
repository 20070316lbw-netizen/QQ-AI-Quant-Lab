# -*- coding: utf-8 -*-
"""
财经新闻自动搜集器 - Finance News Collector
============================================

一个模块化的财经新闻自动搜集程序

功能特点:
---------
- 自动搜集最新财经新闻
- 支持12种预定义财经主题
- 支持自定义关键词搜索
- 支持按时间范围筛选
- 结果保存为JSON格式
- 预留LLM智能分析接口

模块结构:
---------
- config.py     : 配置常量和主题定义
- models.py     : 数据模型定义
- searcher.py   : 搜索引擎封装
- llm_analyzer.py: LLM分析器 (预留)
- collector.py  : 新闻搜集器主类
- utils.py      : 工具函数
- main.py       : 命令行入口

快速开始:
---------
# 命令行使用
python -m finance_news_collector --topic 股市 --save

# 作为模块使用
from finance_news_collector import FinanceNewsCollector

collector = FinanceNewsCollector()
result = collector.search_topic("股市")
collector.print_news(result)
collector.save_to_json(result, "output.json")

实现原理:
---------
本程序通过调用 z-ai CLI 工具执行网络搜索:
1. Python构造搜索参数(JSON格式)
2. subprocess调用 z-ai function web_search
3. z-ai返回结构化搜索结果
4. Python解析并处理结果

后续LLM扩展:
------------
z-ai 同样支持 LLM chat completions，可用于:
- 新闻摘要生成
- 情感分析
- 关键信息提取
- 智能分类
"""

__version__ = "1.0.0"
__author__ = "Liu Bowei ,ChatGPT and Qingyan Agent"

# 导出主要类和函数
from .config import (
    FINANCE_TOPICS,
    LLM_CONFIG,
    LLM_FEATURES,
    DEFAULT_OUTPUT_DIR
)

from .models import (
    NewsItem,
    NewsItemWithAnalysis,
    SearchResult,
    BatchSearchResult,
    AnalysisResult,
    SentimentType,
    ImportanceLevel
)

from .searcher import SearchEngine

from .llm_analyzer import (
    LLMAnalyzer,
    MockAnalyzer,
    create_analyzer
)

from .collector import FinanceNewsCollector

from .utils import (
    format_datetime,
    safe_filename,
    load_json_file,
    save_json_file,
    truncate_text,
    print_banner,
    print_section
)

# 定义公开API
__all__ = [
    # 版本信息
    "__version__",
    "__author__",
    
    # 主要类
    "FinanceNewsCollector",
    "SearchEngine",
    "LLMAnalyzer",
    "MockAnalyzer",
    
    # 数据模型
    "NewsItem",
    "NewsItemWithAnalysis", 
    "SearchResult",
    "BatchSearchResult",
    "AnalysisResult",
    "SentimentType",
    "ImportanceLevel",
    
    # 配置
    "FINANCE_TOPICS",
    "LLM_CONFIG",
    "LLM_FEATURES",
    
    # 工具函数
    "create_analyzer",
    "format_datetime",
    "safe_filename",
    "load_json_file",
    "save_json_file",
    "truncate_text",
    "print_banner",
    "print_section"
]
