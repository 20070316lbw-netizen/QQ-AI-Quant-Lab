#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财经新闻自动搜集程序
Finance News Auto Collector

功能特点:
- 自动搜集最新财经新闻
- 支持多种财经主题分类
- 支持按时间范围筛选
- 结果保存为JSON格式
- 支持命令行和模块化调用

作者: liu bowei ,ChatGPT and Qingyan Agent
日期: 2026-02-18
"""

import subprocess
import json
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class NewsItem:
    """新闻条目数据类"""
    title: str
    url: str
    snippet: str
    source: str
    date: str
    rank: int
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)


class FinanceNewsCollector:
    """财经新闻搜集器"""
    
    # 预定义的财经新闻主题
    FINANCE_TOPICS = {
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
    
    def __init__(self, output_dir: str = "./news_data"):
        """
        初始化新闻搜集器
        
        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _execute_search(self, query: str, num_results: int = 10, 
                        recency_days: Optional[int] = None) -> List[Dict]:
        """
        执行网络搜索
        
        Args:
            query: 搜索关键词
            num_results: 返回结果数量
            recency_days: 最近N天内的结果
            
        Returns:
            搜索结果列表
        """
        args = {
            "query": query,
            "num": num_results
        }
        
        if recency_days:
            args["recency_days"] = recency_days
        
        args_json = json.dumps(args, ensure_ascii=False)
        
        try:
            # 使用z-ai CLI工具执行搜索
            result = subprocess.run(
                ["z-ai", "function", "-n", "web_search", "-a", args_json],
                capture_output=True,
                text=True,
                timeout=90
            )
            
            if result.returncode != 0:
                print(f"搜索错误: {result.stderr}")
                return []
            
            # CLI输出包含日志信息，需要提取JSON部分
            output = result.stdout
            
            # 查找JSON数组开始和结束位置
            json_start = output.find('[')
            json_end = output.rfind(']') + 1
            
            if json_start == -1 or json_end == 0:
                print("未找到有效的JSON数据")
                return []
            
            json_str = output[json_start:json_end]
            search_results = json.loads(json_str)
            
            return search_results if isinstance(search_results, list) else []
            
        except subprocess.TimeoutExpired:
            print("搜索超时，请稍后重试")
            return []
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            return []
        except Exception as e:
            print(f"执行搜索时发生错误: {e}")
            return []
    
    def _parse_results(self, results: List[Dict]) -> List[NewsItem]:
        """
        解析搜索结果为新闻条目
        
        Args:
            results: 原始搜索结果
            
        Returns:
            新闻条目列表
        """
        news_items = []
        
        for item in results:
            try:
                news = NewsItem(
                    title=item.get("name", "无标题"),
                    url=item.get("url", ""),
                    snippet=item.get("snippet", ""),
                    source=item.get("host_name", "未知来源"),
                    date=item.get("date", "未知日期"),
                    rank=item.get("rank", 0)
                )
                news_items.append(news)
            except Exception as e:
                print(f"解析新闻条目时出错: {e}")
                continue
        
        return news_items
    
    def search_news(self, keyword: str, num_results: int = 10,
                    recency_days: Optional[int] = None) -> List[NewsItem]:
        """
        搜集指定关键词的财经新闻
        
        Args:
            keyword: 搜索关键词
            num_results: 返回结果数量
            recency_days: 最近N天内的结果
            
        Returns:
            新闻条目列表
        """
        print(f"正在搜索: {keyword}")
        
        results = self._execute_search(keyword, num_results, recency_days)
        news_items = self._parse_results(results)
        
        print(f"找到 {len(news_items)} 条新闻")
        return news_items
    
    def search_topic(self, topic: str, num_results: int = 10,
                     recency_days: Optional[int] = None) -> List[NewsItem]:
        """
        搜集预定义主题的财经新闻
        
        Args:
            topic: 主题名称（如"股市"、"基金"等）
            num_results: 返回结果数量
            recency_days: 最近N天内的结果
            
        Returns:
            新闻条目列表
        """
        if topic not in self.FINANCE_TOPICS:
            print(f"未知主题: {topic}")
            print(f"可用主题: {', '.join(self.FINANCE_TOPICS.keys())}")
            return []
        
        keywords = self.FINANCE_TOPICS[topic]
        return self.search_news(keywords, num_results, recency_days)
    
    def search_all_topics(self, num_per_topic: int = 5,
                          recency_days: Optional[int] = None) -> Dict[str, List[NewsItem]]:
        """
        搜集所有预定义主题的财经新闻
        
        Args:
            num_per_topic: 每个主题返回的结果数量
            recency_days: 最近N天内的结果
            
        Returns:
            按主题分类的新闻字典
        """
        all_news = {}
        
        print("=" * 50)
        print("开始搜集所有财经主题新闻")
        print("=" * 50)
        
        for topic in self.FINANCE_TOPICS:
            print(f"\n>>> 搜集主题: {topic}")
            news = self.search_topic(topic, num_per_topic, recency_days)
            all_news[topic] = news
        
        print("\n" + "=" * 50)
        print("所有主题搜集完成!")
        print("=" * 50)
        
        return all_news
    
    def save_to_json(self, news_items: List[NewsItem], 
                     filename: str = None) -> str:
        """
        将新闻保存为JSON文件
        
        Args:
            news_items: 新闻条目列表
            filename: 文件名（不含路径）
            
        Returns:
            保存的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"finance_news_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        data = {
            "collect_time": datetime.now().isoformat(),
            "total_count": len(news_items),
            "news": [item.to_dict() for item in news_items]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"新闻已保存到: {filepath}")
        return str(filepath)
    
    def save_topics_to_json(self, all_news: Dict[str, List[NewsItem]],
                            filename: str = None) -> str:
        """
        将所有主题新闻保存为JSON文件
        
        Args:
            all_news: 按主题分类的新闻字典
            filename: 文件名
            
        Returns:
            保存的文件路径
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"all_finance_news_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        data = {
            "collect_time": datetime.now().isoformat(),
            "topics_count": len(all_news),
            "total_news_count": sum(len(v) for v in all_news.values()),
            "news_by_topic": {
                topic: [item.to_dict() for item in items]
                for topic, items in all_news.items()
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"所有新闻已保存到: {filepath}")
        return str(filepath)
    
    def print_news(self, news_items: List[NewsItem], limit: int = 10):
        """
        打印新闻摘要
        
        Args:
            news_items: 新闻条目列表
            limit: 打印数量限制
        """
        print("\n" + "=" * 60)
        print(f"财经新闻摘要 (共 {len(news_items)} 条)")
        print("=" * 60)
        
        for i, news in enumerate(news_items[:limit], 1):
            print(f"\n【{i}】{news.title}")
            print(f"    来源: {news.source}")
            print(f"    日期: {news.date}")
            print(f"    摘要: {news.snippet[:100]}..." if len(news.snippet) > 100 else f"    摘要: {news.snippet}")
            print(f"    链接: {news.url}")
        
        if len(news_items) > limit:
            print(f"\n... 还有 {len(news_items) - limit} 条新闻未显示")
        
        print("\n" + "=" * 60)


def main():
    """主函数 - 命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="财经新闻自动搜集程序",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 推荐使用模块化运行 (在 crawlers 目录下):
  python -m finance_news_collector --topic 股市

  # 如果 python 命令报错,请使用虚拟环境绝对路径:
  ../Dev_Workspace_env/Scripts/python.exe -m finance_news_collector --topic 股市
        """
    )
    
    parser.add_argument(
        "--topic", "-t",
        type=str,
        help=f"预定义主题名称: {', '.join(FinanceNewsCollector.FINANCE_TOPICS.keys())}"
    )
    
    parser.add_argument(
        "--keyword", "-k",
        type=str,
        help="自定义搜索关键词"
    )
    
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="搜集所有预定义主题的新闻"
    )
    
    parser.add_argument(
        "--num", "-n",
        type=int,
        default=10,
        help="每个主题/关键词返回的新闻数量（默认: 10）"
    )
    
    parser.add_argument(
        "--days", "-d",
        type=int,
        help="只搜集最近N天内的新闻"
    )
    
    parser.add_argument(
        "--save", "-s",
        action="store_true",
        help="将结果保存为JSON文件"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="./news_data",
        help="输出目录路径（默认: ./news_data）"
    )
    
    args = parser.parse_args()
    
    # 创建搜集器实例
    collector = FinanceNewsCollector(output_dir=args.output)
    
    # 根据参数执行不同的搜集任务
    if args.all:
        # 搜集所有主题
        all_news = collector.search_all_topics(
            num_per_topic=args.num,
            recency_days=args.days
        )
        
        if args.save:
            collector.save_topics_to_json(all_news)
        
        # 打印摘要
        for topic, news in all_news.items():
            print(f"\n{'='*40}")
            print(f"主题: {topic}")
            collector.print_news(news, limit=3)
            
    elif args.topic:
        # 搜集指定主题
        news = collector.search_topic(
            args.topic,
            num_results=args.num,
            recency_days=args.days
        )
        
        if args.save:
            collector.save_to_json(news, filename=f"{args.topic}_news.json")
        
        collector.print_news(news)
        
    elif args.keyword:
        # 使用自定义关键词搜索
        news = collector.search_news(
            args.keyword,
            num_results=args.num,
            recency_days=args.days
        )
        
        if args.save:
            safe_keyword = args.keyword.replace(" ", "_")[:20]
            collector.save_to_json(news, filename=f"{safe_keyword}_news.json")
        
        collector.print_news(news)
        
    else:
        # 默认搜集今日财经头条
        print("未指定搜索条件，搜集今日财经头条...")
        news = collector.search_news(
            "财经新闻 今日头条",
            num_results=args.num,
            recency_days=args.days or 1
        )
        
        if args.save:
            collector.save_to_json(news, filename="today_headlines.json")
        
        collector.print_news(news)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
