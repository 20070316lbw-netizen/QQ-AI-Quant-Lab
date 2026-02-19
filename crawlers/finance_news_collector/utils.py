# -*- coding: utf-8 -*-
"""
工具函数模块 - Utility Functions Module
=======================================

提供各种辅助工具函数
"""

import json
from datetime import datetime
from typing import Any, Dict, List
from pathlib import Path


def format_datetime(dt: datetime = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化日期时间
    
    Args:
        dt: datetime对象，None则使用当前时间
        fmt: 格式字符串
        
    Returns:
        格式化后的时间字符串
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(fmt)


def safe_filename(name: str, max_length: int = 50) -> str:
    """
    生成安全的文件名
    
    移除或替换不安全的字符
    
    Args:
        name: 原始名称
        max_length: 最大长度
        
    Returns:
        安全的文件名
    """
    # 替换不安全字符
    unsafe_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', ' ']
    result = name
    for char in unsafe_chars:
        result = result.replace(char, '_')
    
    # 截断长度
    if len(result) > max_length:
        result = result[:max_length]
    
    return result


def load_json_file(filepath: str) -> Dict[str, Any]:
    """
    加载JSON文件
    
    Args:
        filepath: 文件路径
        
    Returns:
        解析后的字典
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_file(data: Any, filepath: str, indent: int = 2) -> None:
    """
    保存数据到JSON文件
    
    Args:
        data: 要保存的数据
        filepath: 文件路径
        indent: 缩进空格数
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断文本
    
    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def print_banner(title: str, width: int = 60, char: str = "="):
    """
    打印标题横幅
    
    Args:
        title: 标题文本
        width: 总宽度
        char: 边框字符
    """
    print(char * width)
    print(f" {title} ".center(width))
    print(char * width)


def print_section(title: str, width: int = 40, char: str = "-"):
    """
    打印小节标题
    
    Args:
        title: 标题文本
        width: 总宽度
        char: 边框字符
    """
    print(f"\n{char * width}")
    print(f" {title}")
    print(char * width)


def count_news_by_source(news_list: List[Dict]) -> Dict[str, int]:
    """
    统计各来源的新闻数量
    
    Args:
        news_list: 新闻列表
        
    Returns:
        来源统计字典
    """
    counts = {}
    for news in news_list:
        source = news.get("source", news.get("host_name", "未知"))
        counts[source] = counts.get(source, 0) + 1
    return counts


def merge_news_lists(*lists: List[Dict], remove_duplicates: bool = True) -> List[Dict]:
    """
    合并多个新闻列表
    
    Args:
        *lists: 多个新闻列表
        remove_duplicates: 是否去重
        
    Returns:
        合并后的列表
    """
    merged = []
    seen_urls = set()
    
    for lst in lists:
        for news in lst:
            if remove_duplicates:
                url = news.get("url", "")
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)
            merged.append(news)
    
    return merged
