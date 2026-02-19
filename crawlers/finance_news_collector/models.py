# -*- coding: utf-8 -*-
"""
数据模型模块 - Data Models Module
==================================

定义所有数据结构，包括新闻条目、搜索结果、LLM分析结果等

模块结构:
- NewsItem: 新闻条目基础模型
- NewsItemWithAnalysis: 带LLM分析结果的新闻模型
- SearchResult: 搜索结果封装
- AnalysisResult: LLM分析结果模型
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


# ============================================================
# 枚举类型
# ============================================================

class SentimentType(Enum):
    """情感类型枚举"""
    POSITIVE = "positive"      # 正面
    NEGATIVE = "negative"      # 负面
    NEUTRAL = "neutral"        # 中性
    UNKNOWN = "unknown"        # 未知


class ImportanceLevel(Enum):
    """重要性级别枚举"""
    HIGH = "high"              # 高重要性
    MEDIUM = "medium"          # 中等重要性
    LOW = "low"                # 低重要性
    UNKNOWN = "unknown"        # 未知


# ============================================================
# 基础数据模型
# ============================================================

@dataclass
class NewsItem:
    """
    新闻条目基础模型
    
    Attributes:
        title: 新闻标题
        url: 新闻链接
        snippet: 内容摘要
        source: 来源网站
        date: 发布日期
        rank: 搜索排名
    """
    title: str
    url: str
    snippet: str
    source: str
    date: str = ""
    rank: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NewsItem":
        """从字典创建实例"""
        return cls(
            title=data.get("name", data.get("title", "")),
            url=data.get("url", ""),
            snippet=data.get("snippet", ""),
            source=data.get("host_name", data.get("source", "")),
            date=data.get("date", ""),
            rank=data.get("rank", 0)
        )


@dataclass
class AnalysisResult:
    """
    LLM分析结果模型
    
    预留字段，用于存储LLM分析结果
    
    Attributes:
        summary: 新闻摘要
        sentiment: 情感倾向
        sentiment_score: 情感分数 (-1 到 1)
        keywords: 关键词列表
        category: 分类
        importance: 重要性级别
        importance_score: 重要性分数 (0 到 1)
        entities: 实体识别结果 (公司、人物等)
        raw_response: LLM原始响应
    """
    summary: str = ""
    sentiment: SentimentType = SentimentType.UNKNOWN
    sentiment_score: float = 0.0
    keywords: List[str] = field(default_factory=list)
    category: str = ""
    importance: ImportanceLevel = ImportanceLevel.UNKNOWN
    importance_score: float = 0.0
    entities: Dict[str, List[str]] = field(default_factory=dict)
    raw_response: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "summary": self.summary,
            "sentiment": self.sentiment.value,
            "sentiment_score": self.sentiment_score,
            "keywords": self.keywords,
            "category": self.category,
            "importance": self.importance.value,
            "importance_score": self.importance_score,
            "entities": self.entities,
            "raw_response": self.raw_response
        }


@dataclass
class NewsItemWithAnalysis:
    """
    带LLM分析结果的新闻模型
    
    继承NewsItem的所有属性，并添加分析结果
    """
    news: NewsItem
    analysis: Optional[AnalysisResult] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = self.news.to_dict()
        if self.analysis:
            result["analysis"] = self.analysis.to_dict()
        return result


# ============================================================
# 搜索结果模型
# ============================================================

@dataclass
class SearchResult:
    """
    搜索结果封装
    
    Attributes:
        query: 搜索关键词
        total_count: 结果总数
        news_items: 新闻列表
        collect_time: 搜集时间
        error: 错误信息
    """
    query: str
    total_count: int
    news_items: List[NewsItem]
    collect_time: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "query": self.query,
            "total_count": self.total_count,
            "collect_time": self.collect_time,
            "error": self.error,
            "news": [item.to_dict() for item in self.news_items]
        }


# ============================================================
# 批量结果模型
# ============================================================

@dataclass
class BatchSearchResult:
    """
    批量搜索结果
    
    用于存储多个主题或关键词的搜索结果
    """
    results: Dict[str, SearchResult] = field(default_factory=dict)
    collect_time: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def total_count(self) -> int:
        """获取所有新闻总数"""
        return sum(r.total_count for r in self.results.values())
    
    @property
    def topics_count(self) -> int:
        """获取主题数量"""
        return len(self.results)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "collect_time": self.collect_time,
            "topics_count": self.topics_count,
            "total_news_count": self.total_count,
            "news_by_topic": {
                topic: result.to_dict() 
                for topic, result in self.results.items()
            }
        }
