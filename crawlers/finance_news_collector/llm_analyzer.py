# -*- coding: utf-8 -*-
"""
LLM分析器模块 - LLM Analyzer Module
====================================

预留LLM分析接口，后续可接入 z-ai 的 chat completions 功能

实现原理:
---------
z-ai CLI 同样支持 LLM 调用:
    z-ai chat -m "模型名" -p "提示词"

或通过 SDK:
    zai.chat.completions.create({
        messages: [...],
        model: "..."
    })

可用于的分析功能:
----------------
1. 新闻摘要生成 - 将长新闻压缩为简短摘要
2. 情感分析 - 判断新闻正面/负面/中性
3. 关键词提取 - 提取新闻中的关键信息
4. 智能分类 - 自动归类到预定义主题
5. 重要性评估 - 评估新闻的市场影响力
6. 实体识别 - 识别公司、人物、地点等
"""

import subprocess
import json
from typing import List, Optional, Dict, Any
from abc import ABC, abstractmethod

from .config import LLM_CONFIG, LLM_FEATURES, TOPIC_CATEGORIES
from .models import (
    NewsItem, 
    AnalysisResult, 
    SentimentType, 
    ImportanceLevel
)


class BaseAnalyzer(ABC):
    """
    分析器基类
    
    定义分析器接口，方便后续扩展不同的分析实现
    """
    
    @abstractmethod
    def analyze(self, news: NewsItem) -> AnalysisResult:
        """分析单条新闻"""
        pass
    
    @abstractmethod
    def batch_analyze(self, news_list: List[NewsItem]) -> List[AnalysisResult]:
        """批量分析新闻"""
        pass


class LLMAnalyzer(BaseAnalyzer):
    """
    LLM分析器
    
    使用大语言模型对新闻进行智能分析
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化分析器
        
        Args:
            config: LLM配置，None则使用默认配置
        """
        self.config = config or LLM_CONFIG.copy()
        self.features = LLM_FEATURES.copy()
    
    def is_enabled(self) -> bool:
        """检查LLM是否启用"""
        return self.config.get("enabled", False)
    
    def enable(self):
        """启用LLM分析"""
        self.config["enabled"] = True
    
    def disable(self):
        """禁用LLM分析"""
        self.config["enabled"] = False
    
    def analyze(self, news: NewsItem) -> AnalysisResult:
        """
        分析单条新闻
        
        Args:
            news: 新闻条目
            
        Returns:
            分析结果
        """
        if not self.is_enabled():
            return AnalysisResult()
        
        # TODO: 实现实际的LLM调用
        # 当前返回空结果，后续实现
        result = AnalysisResult()
        
        # 各分析功能
        if self.features.get("summarize"):
            result.summary = self._generate_summary(news)
        
        if self.features.get("sentiment"):
            sentiment, score = self._analyze_sentiment(news)
            result.sentiment = sentiment
            result.sentiment_score = score
        
        if self.features.get("keywords"):
            result.keywords = self._extract_keywords(news)
        
        if self.features.get("category"):
            result.category = self._classify_news(news)
        
        if self.features.get("importance"):
            level, score = self._assess_importance(news)
            result.importance = level
            result.importance_score = score
        
        return result
    
    def batch_analyze(self, news_list: List[NewsItem]) -> List[AnalysisResult]:
        """
        批量分析新闻
        
        Args:
            news_list: 新闻列表
            
        Returns:
            分析结果列表
        """
        return [self.analyze(news) for news in news_list]
    
    # ============================================================
    # 以下为预留的分析方法，后续实现
    # ============================================================
    
    def _generate_summary(self, news: NewsItem) -> str:
        """
        生成新闻摘要
        
        TODO: 调用LLM生成摘要
        提示词示例:
        "请将以下新闻内容压缩为50字以内的摘要：{news.snippet}"
        """
        # 当前返回原标题
        return news.title
    
    def _analyze_sentiment(self, news: NewsItem) -> tuple:
        """
        情感分析
        
        TODO: 调用LLM判断情感
        提示词示例:
        "请分析以下财经新闻的情感倾向(正面/负面/中性)，并给出-1到1的分数：{news.title} {news.snippet}"
        """
        return SentimentType.NEUTRAL, 0.0
    
    def _extract_keywords(self, news: NewsItem) -> List[str]:
        """
        提取关键词
        
        TODO: 调用LLM提取关键词
        提示词示例:
        "请从以下新闻中提取5个关键词：{news.title} {news.snippet}"
        """
        return []
    
    def _classify_news(self, news: NewsItem) -> str:
        """
        新闻分类
        
        TODO: 调用LLM进行分类
        提示词示例:
        "请将以下新闻归类到以下类别之一：{TOPIC_CATEGORIES}。新闻：{news.title}"
        """
        return ""
    
    def _assess_importance(self, news: NewsItem) -> tuple:
        """
        评估重要性
        
        TODO: 调用LLM评估新闻对市场的影响程度
        """
        return ImportanceLevel.UNKNOWN, 0.0


class MockAnalyzer(BaseAnalyzer):
    """
    模拟分析器
    
    用于测试，不调用实际LLM
    """
    
    def analyze(self, news: NewsItem) -> AnalysisResult:
        """返回模拟分析结果"""
        return AnalysisResult(
            summary=f"[模拟摘要] {news.title[:30]}...",
            sentiment=SentimentType.NEUTRAL,
            sentiment_score=0.0,
            keywords=["财经", "市场"],
            category="未分类",
            importance=ImportanceLevel.MEDIUM,
            importance_score=0.5
        )
    
    def batch_analyze(self, news_list: List[NewsItem]) -> List[AnalysisResult]:
        """批量返回模拟结果"""
        return [self.analyze(news) for news in news_list]


# ============================================================
# 工厂函数
# ============================================================

def create_analyzer(analyzer_type: str = "llm", **kwargs) -> BaseAnalyzer:
    """
    创建分析器实例
    
    Args:
        analyzer_type: 分析器类型 ("llm" 或 "mock")
        **kwargs: 传递给分析器的参数
        
    Returns:
        分析器实例
    """
    if analyzer_type == "mock":
        return MockAnalyzer()
    else:
        return LLMAnalyzer(**kwargs)
