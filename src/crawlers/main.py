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

from crawlers.finance_news_collector.base import FINANCE_TOPICS, DEFAULT_OUTPUT_DIR, print_banner, print_section
from crawlers.finance_news_collector.collector import FinanceNewsCollector


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
    
    # 无参数运行则进入交互式界面
    if len(sys.argv) == 1:
        from cli.app import run_cli
        run_cli()
        return 0

    parser = create_parser()
    args = parser.parse_args()
    
    # 创建搜集器
    collector = FinanceNewsCollector(
        output_dir=args.output
    )
    
    print_banner("财经新闻自动搜集程序")
    
    # 根据参数执行不同的搜集任务
    if args.all:
        # 搜集所有主题
        batch_result = collector.search_all_topics(
            num_per_topic=args.num,
            recency_days=args.days
        )
        
        if args.save:
            collector.save_batch_to_json(batch_result)
        
        # 打印各主题摘要
        for topic, result in batch_result.items():
            print_section(f"主题: {topic}")
            collector.print_news(result, limit=3)
            
    elif args.topic:
        # 搜集指定主题
        result = collector.search_topic(
            args.topic,
            num_results=args.num,
            recency_days=args.days
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
            recency_days=args.days
        )
        
        if args.save:
            from crawlers.finance_news_collector.base import safe_filename
            filename = f"{safe_filename(args.keyword)}_news.json"
            collector.save_to_json(result, filename)
        
        collector.print_news(result)
        
    else:
        # 如果未带必要参数，打印帮助信息
        parser.print_help()
        
    return 0


if __name__ == "__main__":
    sys.exit(main())
