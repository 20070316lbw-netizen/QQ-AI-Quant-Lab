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
            
            # 自动获取系统代理 (支持 Windows 注册表代理与通过环境变量注入的代理)
            import urllib.request
            import os
            
            system_proxies = urllib.request.getproxies()
            proxy_url = system_proxies.get("https") or system_proxies.get("http") or system_proxies.get("all")
            proxy_config = proxy_url if proxy_url else None
            
            # 用于保存获取到的原始结果
            raw_ddgs_results = None
            
            # 策略：如果找到了系统代理，先走代理。如果失败，回退到无代理（直连）。
            # 如果一开始就没有代理，直接走直连。
            if proxy_config:
                print(f"[SearchEngine] 发现系统代理: {proxy_config}，正在尝试挂载...")
                try:
                    with DDGS(proxy=proxy_config, timeout=self.timeout) as ddgs:
                        raw_ddgs_results = list(ddgs.text(query, max_results=num_results, timelimit=timelimit))
                except Exception as proxy_err:
                    print(f"[SearchEngine] ⚠️ 代理连接失败 ({proxy_err})，正在启动直连保护机制...")
                    raw_ddgs_results = None
            
            # 如果因为一开始没代理，或者使用代理发生了失败，尝试执行无代理模式的强制直连
            if raw_ddgs_results is None:
                # 尝试通过环境变量屏蔽影响底层的 HTTP_PROXY
                original_http = os.environ.get("HTTP_PROXY")
                original_https = os.environ.get("HTTPS_PROXY")
                if "HTTP_PROXY" in os.environ: del os.environ["HTTP_PROXY"]
                if "HTTPS_PROXY" in os.environ: del os.environ["HTTPS_PROXY"]
                
                try:
                    with DDGS(proxy=None, timeout=self.timeout) as ddgs:
                        raw_ddgs_results = list(ddgs.text(query, max_results=num_results, timelimit=timelimit))
                except Exception as direct_err:
                    print(f"[SearchEngine] ❌ 直连搜索也失败了: {direct_err}")
                finally:
                    # 恢复全局环境变量，避免污染 Agent 其他层的调用逻辑
                    if original_http is not None: os.environ["HTTP_PROXY"] = original_http
                    if original_https is not None: os.environ["HTTPS_PROXY"] = original_https

            if raw_ddgs_results:
                for i, r in enumerate(raw_ddgs_results):
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
