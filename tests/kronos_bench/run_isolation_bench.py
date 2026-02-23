import os
import json
import time
import datetime
import pandas as pd
from rich.console import Console
from rich.table import Table
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# 初始化配置
console = Console()
TICKER = "AAPL"
ITERATIONS = 20
RESULTS_DIR = "tests/kronos_bench"
TIMESTAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = os.path.join(RESULTS_DIR, f"bench_results_{TIMESTAMP}.json")

# 使用系统默认配置并覆盖 LLM 部分
CONFIG = DEFAULT_CONFIG.copy()
CONFIG["llm_provider"] = "ollama"
CONFIG["backend_url"] = "http://localhost:11434"
CONFIG["deep_think_llm"] = "qwen2.5:3b"
CONFIG["quick_think_llm"] = "qwen2.5:3b"

def run_benchmark():
    console.print(f"[bold magenta]🚀 开始 Kronos 稳定性基准测试 ({ITERATIONS} 次循环)...[/bold magenta]")
    console.print(f"标的: {TICKER} | 保存路径: {OUTPUT_FILE}\n")

    results = []
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    # 预先初始化图对象
    ta = TradingAgentsGraph(debug=False, config=CONFIG, test_mode=True)

    for i in range(1, ITERATIONS + 1):
        console.print(f"正在执行第 [bold cyan]{i}/{ITERATIONS}[/bold cyan] 次预测...")
        start_time = time.time()
        
        try:
            # 执行孤立测试预测
            final_state, decision_raw = ta.propagate(TICKER, today)
            elapsed = time.time() - start_time
            
            # 从状态中提取结构化报告
            reports = final_state.get("structured_reports", {})
            kronos_data = reports.get("kronos_solo", {})
            key_metrics = kronos_data.get("key_metrics", {})
            
            # V11.0 支持更长的分级标签
            full_decision = kronos_data.get("decision", "UNKNOWN")
            
            metrics = {
                "iteration": i,
                "timestamp": datetime.datetime.now().isoformat(),
                "elapsed_seconds": round(elapsed, 2),
                "decision": full_decision,
                "confidence": kronos_data.get("confidence", 0.0),
                "expected_return": key_metrics.get("expected_return", "0.0%"),
                "uncertainty": key_metrics.get("uncertainty", 0.0),
                "z_score": key_metrics.get("z_score", 0.0),
                "raw_decision_text": str(decision_raw)
            }
            results.append(metrics)
            console.print(f"  ✅ 完成: {metrics['decision']} (C={metrics['confidence']:.2f}, Time={elapsed:.2f}s)")
            
        except Exception as e:
            console.print(f"  ❌ 第 {i} 次运行故障: {str(e)}", style="bold red")
            results.append({"iteration": i, "error": str(e)})

    # 保存 JSON 结果
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            "ticker": TICKER,
            "iterations": ITERATIONS,
            "total_runs": len(results),
            "summary_timestamp": TIMESTAMP,
            "data": results
        }, f, indent=4, ensure_ascii=False)

    console.print(f"\n[bold green]📊 基准测试完成！[/bold green] 结果已保存至: {OUTPUT_FILE}")
    
    # 输出简易统计分析表
    render_summary(results)

def render_summary(results):
    table = Table(title=f"Kronos 稳定性测试摘要 ({TICKER})")
    table.add_column("轮次", justify="center")
    table.add_column("决策", justify="center")
    table.add_column("置信度", justify="right")
    table.add_column("预期收益", justify="right")
    table.add_column("波动 (Std)", justify="right")
    table.add_column("Z-Score", justify="right")
    table.add_column("耗时 (s)", justify="right")

    for r in results:
        if "error" in r: continue
        table.add_row(
            str(r["iteration"]), 
            r["decision"], 
            f"{r['confidence']:.2f}", 
            r["expected_return"],
            f"{r.get('uncertainty', 0.0):.2%}",
            f"{r.get('z_score', 0.0):.2f}",
            f"{r['elapsed_seconds']:.2f}"
        )
    
    console.print(table)

if __name__ == "__main__":
    run_benchmark()
