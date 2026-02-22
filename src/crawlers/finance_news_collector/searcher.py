# -*- coding: utf-8 -*-
"""
搜索引擎模块 - Search Engine Module
====================================

负责执行网络搜索以获取财经新闻

实现原理:
---------
支持多种搜索源，默认为 DuckDuckGo 原生搜索。

1. DuckDuckGo (推荐): 使用 duckduckgo-search 库执行原生 Python 搜索，无需外部依赖。
2. z-ai CLI (备选): 通过 subprocess 调用 z-ai 命令行工具执行搜索。

返回结果格式 (JSON数组):
    [
        {
            "url": "https://example.com/news",
            "name": "新闻标题",
            "snippet": "新闻摘要内容...",
            "host_name": "example.com",
            "rank": 0,
            "date": ""
        },
        ...
    ]
"""

import subprocess
import json
from typing import List, Dict, Optional

from .base import (
    SEARCH_SOURCE,
    DEFAULT_TIMEOUT,
    DEFAULT_NUM_RESULTS
)


class SearchEngine:
    """
    搜索引擎类
    
    统一封装多种搜索后端接口
    """
    
    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        """
        初始化搜索引擎
        
        Args:
            timeout: 搜索超时时间(秒)
        """
        self.timeout = timeout
    
    def search(
        self, 
        query: str, 
        num_results: int = DEFAULT_NUM_RESULTS,
        recency_days: Optional[int] = None
    ) -> List[Dict]:
        """
        执行网络搜索
        """
        if SEARCH_SOURCE == "duckduckgo":
            return self._search_duckduckgo(query, num_results, recency_days)
        else:
            return self._search_zai_cli(query, num_results, recency_days)

    def _search_duckduckgo(
        self, 
        query: str, 
        num_results: int,
        recency_days: Optional[int]
    ) -> List[Dict]:
        """使用 duckduckgo-search (ddgs) 执行搜索"""
        try:
            from duckduckgo_search import DDGS
            
            # 时间范围映射
            timelimit = None
            if recency_days:
                if recency_days <= 1: timelimit = 'd'
                elif recency_days <= 7: timelimit = 'w'
                elif recency_days <= 30: timelimit = 'm'
                else: timelimit = 'y'

            results = []
            # 尝试使用 DDGS 搜索，并在 SSL 失败时提供建议
            with DDGS() as ddgs:
                try:
                    ddgs_results = ddgs.text(
                        query, 
                        max_results=num_results,
                        timelimit=timelimit
                    )
                except Exception as ssl_err:
                    if "SSL" in str(ssl_err):
                        print(f"[SearchEngine] 检测到 SSL 异常，这通常是由于网络或代理设置引起的。")
                        # 如果环境允许，可以考虑在这里尝试无验证模式，但 DDGS 封装较深。
                        # 这里我们仅记录并返回空，避免崩溃。
                    raise ssl_err
                
                if ddgs_results:
                    for i, r in enumerate(ddgs_results):
                        results.append({
                            "url": r.get("href", ""),
                            "name": r.get("title", ""),
                            "snippet": r.get("body", ""),
                            "host_name": r.get("href", "").split("//")[-1].split("/")[0],
                            "rank": i,
                            "date": ""
                        })
            return results
        except Exception as e:
            print(f"[SearchEngine] DuckDuckGo 搜索异常: {e}")
            return []

    def _search_zai_cli(
        self, 
        query: str, 
        num_results: int,
        recency_days: Optional[int]
    ) -> List[Dict]:
        """调用 z-ai CLI 执行搜索 (原有逻辑)"""
        args = {"query": query, "num": num_results}
        if recency_days:
            args["recency_days"] = recency_days
        
        args_json = json.dumps(args, ensure_ascii=False)
        
        try:
            result = subprocess.run(
                [CLI_COMMAND, "function", "-n", CLI_FUNCTION_NAME, "-a", args_json],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode != 0:
                print(f"[SearchEngine] CLI 搜索错误: {result.stderr}")
                return []
            
            return self._parse_cli_output(result.stdout)
            
        except subprocess.TimeoutExpired:
            print("[SearchEngine] CLI 搜索超时")
            return []
        except FileNotFoundError:
            print("[SearchEngine] 未找到 z-ai 命令，且 SEARCH_SOURCE 设置为 z-ai")
            return []
        except Exception as e:
            print(f"[SearchEngine] CLI 搜索异常: {e}")
            return []
    
    def _parse_cli_output(self, output: str) -> List[Dict]:
        """
        解析CLI输出，提取JSON数据
        
        CLI输出格式:
        🚀 Initializing Z-AI SDK...
        🚀 Invoking function: web_search...
        [
            {...},
            {...}
        ]
        🎉 Function invocation completed!
        
        Args:
            output: CLI原始输出
            
        Returns:
            解析后的搜索结果列表
        """
        # 查找JSON数组边界
        json_start = output.find('[')
        json_end = output.rfind(']') + 1
        
        if json_start == -1 or json_end == 0:
            print("[SearchEngine] 未找到有效的JSON数据")
            return []
        
        json_str = output[json_start:json_end]
        results = json.loads(json_str)
        
        return results if isinstance(results, list) else []
    
    def search_multiple(
        self, 
        queries: List[str], 
        num_per_query: int = DEFAULT_NUM_RESULTS,
        recency_days: Optional[int] = None
    ) -> Dict[str, List[Dict]]:
        """
        批量搜索多个关键词
        
        Args:
            queries: 关键词列表
            num_per_query: 每个关键词的结果数量
            recency_days: 时间范围
            
        Returns:
            字典，key为关键词，value为搜索结果列表
        """
        results = {}
        for query in queries:
            print(f"[SearchEngine] 搜索: {query}")
            results[query] = self.search(query, num_per_query, recency_days)
        return results
