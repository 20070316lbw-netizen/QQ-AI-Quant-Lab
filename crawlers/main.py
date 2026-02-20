#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财经新闻自动搜集程序 - 主入口
==============================

命令行接口入口点

使用方法:
---------
# 首先确保在 crawlers 目录下
cd c:/Users/lbw15/Desktop/Dev_Workspace/crawlers

# 直接运行主程序
python main.py --topic 股市

# 如果上述命令报错,支持使用虚拟环境绝对路径
../Dev_Workspace_env/Scripts/python.exe main.py --all --save
"""

import sys
import argparse

from finance_news_collector.config import FINANCE_TOPICS, DEFAULT_OUTPUT_DIR
from finance_news_collector.collector import FinanceNewsCollector
from finance_news_collector.utils import print_banner, print_section


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="财经新闻自动搜集程序",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 在 crawlers 目录下运行:
  python main.py --topic 股市
  
  # 如果遇到 SSL 错误或环境识别问题,请使用完整路径:
  ../Dev_Workspace_env/Scripts/python.exe main.py --topic 基金 --days 7
  
  # 启用保存功能
  python main.py --topic 股市 --save
        """
    )
    
    # 搜索目标参数 (互斥组)
    target_group = parser.add_mutually_exclusive_group()
    target_group.add_argument(
        "--topic", "-t",
        type=str,
        help=f"预定义主题: {', '.join(FINANCE_TOPICS.keys())}"
    )
    target_group.add_argument(
        "--keyword", "-k",
        type=str,
        help="自定义搜索关键词"
    )
    target_group.add_argument(
        "--all", "-a",
        action="store_true",
        help="搜集所有预定义主题的新闻"
    )
    
    # 搜索参数
    parser.add_argument(
        "--num", "-n",
        type=int,
        default=10,
        help="每个主题/关键词返回的新闻数量 (默认: 10)"
    )
    parser.add_argument(
        "--days", "-d",
        type=int,
        help="只搜集最近N天内的新闻"
    )
    
    # 输出参数
    parser.add_argument(
        "--save", "-s",
        action="store_true",
        help="将结果保存为JSON文件"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f"输出目录路径 (默认: {DEFAULT_OUTPUT_DIR})"
    )
    
    # LLM参数 (预留)
    parser.add_argument(
        "--llm",
        action="store_true",
        help="启用LLM智能分析 (预留功能)"
    )
    
    return parser


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    # 创建搜集器
    collector = FinanceNewsCollector(
        output_dir=args.output,
        enable_llm=args.llm
    )
    
    print_banner("财经新闻自动搜集程序")
    
    # 根据参数执行不同的搜集任务
    if args.all:
        # 搜集所有主题
        batch_result = collector.search_all_topics(
            num_per_topic=args.num,
            recency_days=args.days,
            with_analysis=args.llm
        )
        
        if args.save:
            collector.save_batch_to_json(batch_result)
        
        # 打印各主题摘要
        for topic, result in batch_result.results.items():
            print_section(f"主题: {topic}")
            collector.print_news(result, limit=3)
            
    elif args.topic:
        # 搜集指定主题
        result = collector.search_topic(
            args.topic,
            num_results=args.num,
            recency_days=args.days,
            with_analysis=args.llm
        )
        
        if args.save:
            filename = f"{args.topic}_news.json"
            collector.save_to_json(result, filename)
        
        collector.print_news(result)
        
    elif args.keyword:
        # 使用自定义关键词搜索
        result = collector.search_news(
            args.keyword,
            num_results=args.num,
            recency_days=args.days,
            with_analysis=args.llm
        )
        
        if args.save:
            from finance_news_collector.utils import safe_filename
            filename = f"{safe_filename(args.keyword)}_news.json"
            collector.save_to_json(result, filename)
        
        collector.print_news(result)
        
    else:
        # 默认搜集今日财经头条
        print("未指定搜索条件，搜集今日财经头条...")
        result = collector.search_news(
            "财经新闻 今日头条",
            num_results=args.num,
            recency_days=args.days or 1,
            with_analysis=args.llm
        )
        
        if args.save:
            collector.save_to_json(result, "today_headlines.json")
        
        collector.print_news(result)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
