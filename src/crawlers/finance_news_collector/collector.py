# -*- coding: utf-8 -*-
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from .base import (
    FINANCE_TOPICS,
    DEFAULT_OUTPUT_DIR,
    JSON_INDENT,
    NEWS_DISPLAY_LIMIT,
    NewsItem,
    SearchResult,
    print_banner,
    print_section
)
from .searcher import SearchEngine

class FinanceNewsCollector:
    def __init__(self, output_dir: str = DEFAULT_OUTPUT_DIR, enable_llm: bool = False):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.searcher = SearchEngine()
        self.enable_llm = enable_llm
    
    def search_news(self, keyword: str, num_results: int = 10, recency_days: Optional[int] = None) -> SearchResult:
        print(f"[Collector] 正在搜索: {keyword}")
        raw_results = self.searcher.search(keyword, num_results, recency_days)
        news_items = [NewsItem.from_dict(item) for item in raw_results]
        print(f"[Collector] 找到 {len(news_items)} 条新闻")
        return SearchResult(query=keyword, total_count=len(news_items), news_items=news_items)
    
    def search_topic(self, topic: str, num_results: int = 10, recency_days: Optional[int] = None) -> SearchResult:
        if topic not in FINANCE_TOPICS:
            return SearchResult(query=topic, total_count=0, news_items=[])
        result = self.search_news(FINANCE_TOPICS[topic], num_results, recency_days)
        result.query = topic
        return result
    
    def search_all_topics(self, num_per_topic: int = 5, recency_days: Optional[int] = None) -> Dict[str, SearchResult]:
        print_banner("开始搜集所有财经主题新闻")
        results = {}
        for topic in FINANCE_TOPICS:
            results[topic] = self.search_topic(topic, num_per_topic, recency_days)
        return results
    
    def save_to_json(self, result: SearchResult, filename: str):
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=JSON_INDENT)
        print(f"[Collector] 新闻已保存到: {filepath}")
        return str(filepath)

    def save_batch_to_json(self, batch_result: Dict[str, SearchResult], filename: str = "batch_results.json"):
        output = {
            "collect_time": datetime.now().isoformat(),
            "results": {t: r.to_dict() for t, r in batch_result.items()}
        }
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=JSON_INDENT)
        print(f"[Collector] 批量结果已保存至: {filepath}")
        return str(filepath)

    def print_news(self, result: SearchResult, limit: int = NEWS_DISPLAY_LIMIT):
        print_section(f"财经新闻摘要 - {result.query} (共 {result.total_count} 条)")
        for i, item in enumerate(result.news_items[:limit], 1):
            print(f"\n【{i}】{item.title}")
            print(f"    来源: {item.source} | 日期: {item.date}")
            print(f"    摘要: {item.snippet[:100]}...")
            print(f"    链接: {item.url}")
