import os
import json
import time
import datetime
import numpy as np
import pandas as pd
from rich.console import Console
from rich.table import Table
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# 初始化
console = Console()
TICKER = "AAPL"
ITERATIONS = 100
RESULTS_DIR = "tests/kronos_bench"
TIMESTAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE = os.path.join(RESULTS_DIR, f"signal_strength_study_{TIMESTAMP}.json")

CONFIG = DEFAULT_CONFIG.copy()
CONFIG["llm_provider"] = "ollama"
CONFIG["backend_url"] = "http://localhost:11434"
CONFIG["deep_think_llm"] = "qwen2.5:3b"
CONFIG["quick_think_llm"] = "qwen2.5:3b"

def run_distribution_study():
    console.print(f"[bold yellow]🔍 开始 Kronos 信号强度深度研究 ({TICKER}, {ITERATIONS} 次)...[/bold yellow]")
    
    returns = []
    confidences = []
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    # 初始化一次图，减少循环开销
    ta = TradingAgentsGraph(debug=False, config=CONFIG, test_mode=True)

    for i in range(1, ITERATIONS + 1):
        if i % 20 == 0:
            console.print(f"进度: [cyan]{i}/{ITERATIONS}[/cyan]...")
            
        try:
            # 执行预测
            final_state, _ = ta.propagate(TICKER, today)
            
            # 手动提取原始数据
            reports = final_state.get("structured_reports", {})
            kronos_data = reports.get("kronos_solo", {})
            
            # 提取收益率
            ret_str = kronos_data.get("key_metrics", {}).get("expected_return", "0.00%")
            ret_val = float(ret_str.replace('%', '')) / 100.0
            returns.append(ret_val)
            
            # 提取置信度
            conf_val = kronos_data.get("confidence", 0.0)
            confidences.append(conf_val)
            
        except Exception as e:
            console.print(f"❌ 第 {i} 次运行故障: {str(e)}", style="bold red")

    if not returns:
        console.print("[red]没有获取到有效数据。[/red]")
        return

    # 统计分析
    returns = np.array(returns)
    confidences = np.array(confidences)
    
    mean_ret = np.mean(returns)
    std_ret = np.std(returns)
    mean_conf = np.mean(confidences)
    
    # 核心指标：Signal Strength = abs(r) / std
    # 如果 std 为 0 则设为 0
    signal_strengths = np.abs(returns) / std_ret if std_ret > 0 else np.zeros_like(returns)
    
    # 统计强度分布
    s_gt_1 = np.sum(signal_strengths > 1.0)
    s_gt_1_5 = np.sum(signal_strengths > 1.5)
    s_gt_2 = np.sum(signal_strengths > 2.0)

    # 统计偏向信号 (维持原阈值供参考)
    buy_signals = np.sum(returns > 0.03)
    sell_signals = np.sum(returns < -0.03)

    # 输出报告
    console.print("\n" + "="*50)
    console.print(f"🧪 [bold]V10.0 信号强度研究报告 - {TICKER}[/bold]")
    console.print(f"样本总数: {len(returns)}")
    console.print(f"内部噪声水平 (StdDev): [bold magenta]{std_ret:.4f}[/bold magenta]")
    console.print(f"收益率均值 (Mean): [bold cyan]{mean_ret:.2%}[/bold cyan]")
    console.print("-"*50)
    console.print(f"信号强度分布 (Signal Strength = |r|/std):")
    console.print(f" - 强度 > 1.0 (显著信号): [green]{s_gt_1}[/green] ({s_gt_1/len(returns):.1%})")
    console.print(f" - 强度 > 1.5 (极显著信号): [yellow]{s_gt_1_5}[/yellow] ({s_gt_1_5/len(returns):.1%})")
    console.print(f" - 强度 > 2.0 (突变信号): [bold red]{s_gt_2}[/bold red] ({s_gt_2/len(returns):.1%})")
    console.print(f" 强度平均值: {np.mean(signal_strengths):.2f}")
    console.print("="*50 + "\n")

    # 保存 JSON
    study_data = {
        "ticker": TICKER,
        "iterations": ITERATIONS,
        "stats": {
            "mean_ret": float(mean_ret),
            "std_ret": float(std_ret),
            "mean_conf": float(mean_conf),
            "avg_signal_strength": float(np.mean(signal_strengths))
        },
        "distribution": {
            "gt_1_0": int(s_gt_1),
            "gt_1_5": int(s_gt_1_5),
            "gt_2_0": int(s_gt_2)
        },
        "raw_returns": returns.tolist(),
        "raw_strengths": signal_strengths.tolist()
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(study_data, f, indent=4)
        
    console.print(f"详细研究数据已保存至: [dim]{OUTPUT_FILE}[/dim]")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(study_data, f, indent=4)
        
    console.print(f"详细研究数据已保存至: [dim]{OUTPUT_FILE}[/dim]")

if __name__ == "__main__":
    run_distribution_study()
