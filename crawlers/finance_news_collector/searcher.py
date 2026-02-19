# -*- coding: utf-8 -*-
"""
搜索引擎模块 - Search Engine Module
====================================

负责调用 z-ai CLI 执行网络搜索

实现原理:
---------
通过 Python 的 subprocess 模块调用 z-ai CLI 命令行工具。

z-ai CLI 命令格式:
    z-ai function -n web_search -a '{"query": "关键词", "num": 10}'

返回结果格式 (JSON数组):
    [
        {
            "url": "https://example.com/news",
            "name": "新闻标题",
            "snippet": "新闻摘要内容...",
            "host_name": "example.com",
            "rank": 0,
            "date": "",
            "favicon": ""
        },
        ...
    ]

为什么用 CLI 而不是直接 HTTP 请求:
---------------------------------
1. z-ai CLI 封装了复杂的认证和请求逻辑
2. 自动处理错误重试
3. 返回结构化数据，无需解析HTML
4. 支持多种搜索参数
"""

import subprocess
import json
from typing import List, Dict, Optional

from .config import (
    SEARCH_SOURCE,
    CLI_COMMAND,
    CLI_FUNCTION_NAME,
    DEFAULT_TIMEOUT,
    DEFAULT_NUM_RESULTS
)


class SearchEngine:
    """
    搜索引擎类
    
    封装 z-ai CLI 的 web_search 功能
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
        """使用 duckduckgo-search 库执行搜索"""
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
            with DDGS() as ddgs:
                ddgs_results = ddgs.text(
                    query, 
                    max_results=num_results,
                    timelimit=timelimit
                )
                
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
