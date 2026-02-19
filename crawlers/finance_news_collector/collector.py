# -*- coding: utf-8 -*-
"""
新闻搜集器模块 - News Collector Module
=======================================

整合搜索引擎和LLM分析器，提供完整的新闻搜集功能

使用方式:
--------
from collector import FinanceNewsCollector

# 创建搜集器
collector = FinanceNewsCollector()

# 搜集新闻
news = collector.search_topic("股市")

# 保存结果
collector.save_to_json(news, "output.json")
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from .config import (
    FINANCE_TOPICS,
    DEFAULT_OUTPUT_DIR,
    FILENAME_TEMPLATES,
    JSON_INDENT,
    NEWS_DISPLAY_LIMIT
)
from .models import (
    NewsItem,
    NewsItemWithAnalysis,
    SearchResult,
    BatchSearchResult,
    AnalysisResult,
    SentimentType
)
from .searcher import SearchEngine
from .llm_analyzer import LLMAnalyzer, create_analyzer, BaseAnalyzer


class FinanceNewsCollector:
    """
    财经新闻搜集器
    
    主要功能:
    - 按主题搜集新闻
    - 按关键词搜集新闻
    - 批量搜集多个主题
    - LLM智能分析 (可选)
    - 结果保存为JSON
    """
    
    def __init__(
        self, 
        output_dir: str = DEFAULT_OUTPUT_DIR,
        enable_llm: bool = False
    ):
        """
        初始化搜集器
        
        Args:
            output_dir: 输出目录路径
            enable_llm: 是否启用LLM分析
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化搜索引擎
        self.searcher = SearchEngine()
        
        # 初始化分析器
        self.analyzer = create_analyzer("llm")
        if enable_llm:
            self.analyzer.enable()
    
    # ============================================================
    # 搜索方法
    # ============================================================
    
    def search_news(
        self, 
        keyword: str, 
        num_results: int = 10,
        recency_days: Optional[int] = None,
        with_analysis: bool = False
    ) -> SearchResult:
        """
        搜集指定关键词的新闻
        
        Args:
            keyword: 搜索关键词
            num_results: 返回结果数量
            recency_days: 最近N天内的结果
            with_analysis: 是否进行LLM分析
            
        Returns:
            搜索结果对象
        """
        print(f"[Collector] 正在搜索: {keyword}")
        
        # 执行搜索
        raw_results = self.searcher.search(keyword, num_results, recency_days)
        
        # 转换为NewsItem对象
        news_items = [NewsItem.from_dict(item) for item in raw_results]
        
        # 可选：LLM分析
        if with_analysis and self.analyzer.is_enabled():
            news_items = self._analyze_news(news_items)
        
        print(f"[Collector] 找到 {len(news_items)} 条新闻")
        
        return SearchResult(
            query=keyword,
            total_count=len(news_items),
            news_items=news_items
        )
    
    def search_topic(
        self, 
        topic: str, 
        num_results: int = 10,
        recency_days: Optional[int] = None,
        with_analysis: bool = False
    ) -> SearchResult:
        """
        搜集预定义主题的新闻
        
        Args:
            topic: 主题名称
            num_results: 返回结果数量
            recency_days: 时间范围
            with_analysis: 是否进行LLM分析
            
        Returns:
            搜索结果对象
        """
        if topic not in FINANCE_TOPICS:
            print(f"[Collector] 未知主题: {topic}")
            print(f"[Collector] 可用主题: {', '.join(FINANCE_TOPICS.keys())}")
            return SearchResult(query=topic, total_count=0, news_items=[])
        
        keywords = FINANCE_TOPICS[topic]
        result = self.search_news(keywords, num_results, recency_days, with_analysis)
        result.query = topic  # 替换为主题名
        
        return result
    
    def search_all_topics(
        self, 
        num_per_topic: int = 5,
        recency_days: Optional[int] = None,
        with_analysis: bool = False
    ) -> BatchSearchResult:
        """
        搜集所有预定义主题的新闻
        
        Args:
            num_per_topic: 每个主题的结果数量
            recency_days: 时间范围
            with_analysis: 是否进行LLM分析
            
        Returns:
            批量搜索结果对象
        """
        print("=" * 50)
        print("[Collector] 开始搜集所有财经主题新闻")
        print("=" * 50)
        
        batch_result = BatchSearchResult()
        
        for topic in FINANCE_TOPICS:
            print(f"\n>>> 搜集主题: {topic}")
            result = self.search_topic(topic, num_per_topic, recency_days, with_analysis)
            batch_result.results[topic] = result
        
        print("\n" + "=" * 50)
        print(f"[Collector] 所有主题搜集完成! 共 {batch_result.total_count} 条新闻")
        print("=" * 50)
        
        return batch_result
    
    # ============================================================
    # 分析方法
    # ============================================================
    
    def _analyze_news(self, news_items: List[NewsItem]) -> List[NewsItem]:
        """
        对新闻进行LLM分析
        
        Args:
            news_items: 新闻列表
            
        Returns:
            带分析结果的新闻列表
        """
        print("[Collector] 正在进行LLM分析...")
        analyzed = []
        
        for news in news_items:
            analysis = self.analyzer.analyze(news)
            analyzed.append(NewsItemWithAnalysis(news=news, analysis=analysis))
        
        return analyzed
    
    def enable_llm(self):
        """启用LLM分析"""
        self.analyzer.enable()
        print("[Collector] LLM分析已启用")
    
    def disable_llm(self):
        """禁用LLM分析"""
        self.analyzer.disable()
        print("[Collector] LLM分析已禁用")
    
    # ============================================================
    # 保存方法
    # ============================================================
    
    def save_to_json(
        self, 
        result: SearchResult, 
        filename: Optional[str] = None
    ) -> str:
        """
        将搜索结果保存为JSON文件
        
        Args:
            result: 搜索结果
            filename: 文件名
            
        Returns:
            保存的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = FILENAME_TEMPLATES["default"].format(timestamp=timestamp)
        
        filepath = self.output_dir / filename
        
        # 构建保存数据
        data = result.to_dict()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=JSON_INDENT)
        
        print(f"[Collector] 新闻已保存到: {filepath}")
        return str(filepath)
    
    def save_batch_to_json(
        self, 
        batch_result: BatchSearchResult,
        filename: Optional[str] = None
    ) -> str:
        """
        将批量搜索结果保存为JSON文件
        
        Args:
            batch_result: 批量搜索结果
            filename: 文件名
            
        Returns:
            保存的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = FILENAME_TEMPLATES["all_topics"].format(timestamp=timestamp)
        
        filepath = self.output_dir / filename
        
        data = batch_result.to_dict()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=JSON_INDENT)
        
        print(f"[Collector] 所有新闻已保存到: {filepath}")
        return str(filepath)
    
    # ============================================================
    # 显示方法
    # ============================================================
    
    def print_news(self, result: SearchResult, limit: int = NEWS_DISPLAY_LIMIT):
        """
        打印新闻摘要
        
        Args:
            result: 搜索结果
            limit: 显示数量限制
        """
        print("\n" + "=" * 60)
        print(f"财经新闻摘要 - {result.query} (共 {result.total_count} 条)")
        print("=" * 60)
        
        for i, news in enumerate(result.news_items[:limit], 1):
            # 处理带分析和不带分析两种情况
            if isinstance(news, NewsItemWithAnalysis):
                item = news.news
                analysis = news.analysis
            else:
                item = news
                analysis = None
            
            print(f"\n【{i}】{item.title}")
            print(f"    来源: {item.source}")
            if item.date:
                print(f"    日期: {item.date}")
            
            snippet = item.snippet[:100] + "..." if len(item.snippet) > 100 else item.snippet
            print(f"    摘要: {snippet}")
            
            # 显示LLM分析结果
            if analysis and analysis.summary:
                print(f"    AI摘要: {analysis.summary}")
            if analysis and analysis.sentiment != SentimentType.UNKNOWN:
                print(f"    情感: {analysis.sentiment.value}")
            
            print(f"    链接: {item.url}")
        
        if result.total_count > limit:
            print(f"\n... 还有 {result.total_count - limit} 条新闻未显示")
        
        print("\n" + "=" * 60)
    
    # ============================================================
    # 便捷属性
    # ============================================================
    
    @property
    def available_topics(self) -> List[str]:
        """获取可用的主题列表"""
        return list(FINANCE_TOPICS.keys())
