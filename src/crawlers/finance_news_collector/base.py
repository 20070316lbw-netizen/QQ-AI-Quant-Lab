# -*- coding: utf-8 -*-
"""
基础组件模块 - Base Components Module
======================================

整合了原有的配置、数据模型和工具函数，减少碎片化代码。
"""

import json
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
from enum import Enum

# ============================================================
# 1. 配置常量 (原 config.py)
# ============================================================

SEARCH_SOURCE = "duckduckgo"
DEFAULT_TIMEOUT = 90
DEFAULT_NUM_RESULTS = 10

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

DEFAULT_OUTPUT_DIR = "./news_data"
JSON_INDENT = 2
NEWS_DISPLAY_LIMIT = 10

# ============================================================
# 2. 枚举与数据模型 (原 models.py)
# ============================================================

class SentimentType(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"

class ImportanceLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"

@dataclass
class NewsItem:
    title: str
    url: str
    snippet: str
    source: str
    date: str = ""
    rank: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NewsItem":
        return cls(
            title=data.get("name", data.get("title", "")),
            url=data.get("url", ""),
            snippet=data.get("snippet", ""),
            source=data.get("host_name", data.get("source", "")),
            date=data.get("date", ""),
            rank=data.get("rank", 0)
        )

@dataclass
class SearchResult:
    query: str
    total_count: int
    news_items: List[NewsItem]
    collect_time: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "total_count": self.total_count,
            "collect_time": self.collect_time,
            "error": self.error,
            "news": [item.to_dict() for item in self.news_items]
        }

# ============================================================
# 3. 工具函数 (原 utils.py)
# ============================================================

def safe_filename(name: str, max_length: int = 50) -> str:
    unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', ' ']
    result = name
    for char in unsafe_chars:
        result = result.replace(char, '_')
    return result[:max_length]

def print_banner(title: str, width: int = 60):
    print("=" * width)
    print(f" {title} ".center(width))
    print("=" * width)

def print_section(title: str, width: int = 40):
    print(f"\n{'-' * width}")
    print(f" {title}")
    print("-" * width)
