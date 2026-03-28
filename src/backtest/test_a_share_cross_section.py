"""
A 股结构化横截面测试 — 四维风格压力测试
=========================================
测试组别:
  [G1] 白马权重  茅台 / 招商银行 / 中国平安
  [G2] 科技成长  中际旭创 / 寒武纪 / 宁德时代
  [G3] 周期资源  中国神华 / 紫金矿业 / 中国石油
  [G4] 高弹情绪  东方财富 / 科大讯飞 / 隆基绿能

输出:
  - Rich 终端表格（分组显示）
  - cross_section_result.json（完整原始数据存档）
"""

import sys
import os
import json
import multiprocessing
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from trading_signal import generate_signal
from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.text import Text

console = Console()

# 输出 JSON 路径
OUTPUT_JSON = os.path.join(os.path.dirname(__file__), "cross_section_result.json")

# ── 测试标的定义 ───────────────────────────────────────────────
GROUPS = [
    {
        "id": "G1",
        "name": "G1 · 白马权重  [低波动核心资产]",
        "color": "bold cyan",
        "tickers": [
            ("600519.SS", "贵州茅台"),
            ("600036.SS", "招商银行"),
            ("601318.SS", "中国平安"),
        ],
    },
    {
        "id": "G2",
        "name": "G2 · 科技成长  [高波动趋势]",
        "color": "bold magenta",
        "tickers": [
            ("300308.SZ", "中际旭创"),
            ("688256.SS", "寒武纪"),
            ("300750.SZ", "宁德时代"),
        ],
    },
    {
        "id": "G3",
        "name": "G3 · 周期资源  [宏观敏感]",
        "color": "bold yellow",
        "tickers": [
            ("601088.SS", "中国神华"),
            ("601899.SS", "紫金矿业"),
            ("601857.SS", "中国石油"),
        ],
    },
    {
        "id": "G4",
        "name": "G4 · 高弹情绪  [暴露模型真实水平]",
        "color": "bold red",
        "tickers": [
            ("300059.SZ", "东方财富"),
            ("002230.SZ", "科大讯飞"),
            ("601012.SS", "隆基绿能"),
        ],
    },
]


# ── 单标的执行函数（线程安全）─────────────────────────────────
def run_single(ticker: str, name: str, group_id: str) -> dict:
    result = {
        "ticker":   ticker,
        "name":     name,
        "group":    group_id,
        "signal":   None,
        "error":    None,
        "run_at":   datetime.now().isoformat(),
    }
    try:
        signal_raw = generate_signal(ticker)
        result["signal"] = json.loads(signal_raw) if isinstance(signal_raw, str) else signal_raw
    except Exception as e:
        result["error"] = str(e)
    return result


# ── 结果渲染 ─────────────────────────────────────────────────
def render_group(group: dict, results: list):
    table = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold white on grey23",
        min_width=90,
    )
    table.add_column("代码",       style="dim", width=14)
    table.add_column("名称",       style="bold", width=10)
    table.add_column("方向",       width=8)
    table.add_column("Z-Score",    justify="right", width=10)
    table.add_column("预期收益",   justify="right", width=10)
    table.add_column("不确定性",   justify="right", width=10)
    table.add_column("综合信号",   justify="center", width=10)

    for r in results:
        if r["error"]:
            table.add_row(r["ticker"], r["name"], "[red]ERROR[/red]",
                          "—", "—", "—", f"[dim]{r['error'][:30]}...[/dim]")
            continue

        s = r["signal"]
        direction    = s.get("direction", "HOLD")
        z            = s.get("z_score", 0.0)
        exp_ret      = s.get("expected_return", 0.0)
        uncertainty  = s.get("uncertainty", 0.0)
        final_signal = s.get("final_signal", direction)

        dir_style = "green" if "BUY" in direction else ("red" if "SELL" in direction else "yellow")
        sig_style = "green" if "BUY" in final_signal else ("red" if "SELL" in final_signal else "yellow")

        table.add_row(
            r["ticker"],
            r["name"],
            f"[{dir_style}]{direction}[/{dir_style}]",
            f"{z:+.3f}",
            f"{exp_ret*100:+.2f}%",
            f"{uncertainty*100:.2f}%",
            f"[{sig_style}]{final_signal}[/{sig_style}]",
        )

    console.print(Panel(table, title=f"[{group['color']}]{group['name']}[/{group['color']}]",
                        border_style="grey50"))


# ── 主入口 ────────────────────────────────────────────────────
def main():
    run_start = datetime.now().isoformat()

    console.print(Panel(
        Text("ECHO  A 股结构化横截面压力测试\n四组风格 × 三只标的  实时并发推演", justify="center"),
        style="bold cyan", border_style="cyan"
    ))

    all_tickers = [(t, n, g["id"]) for g in GROUPS for t, n in g["tickers"]]
    total = len(all_tickers)

    console.print(f"\n[bold]启动 ThreadPool (最大 4 线程) 并发推演 {total} 只标的...[/bold]\n")

    result_map = {}
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(run_single, t, n, gid): (t, n) for t, n, gid in all_tickers}
        done = 0
        for fut in as_completed(futures):
            ticker, name = futures[fut]
            res = fut.result()
            result_map[ticker] = res
            done += 1
            status = "[green]OK[/green]" if not res["error"] else "[red]ERR[/red]"
            console.print(f"  {status} [{done}/{total}] {ticker} ({name})", highlight=False)

    console.print()

    # ── 按组渲染 ──────────────────────────────────────────────
    for group in GROUPS:
        group_results = [result_map[t] for t, _ in group["tickers"]]
        render_group(group, group_results)

    # ── 汇总统计 ─────────────────────────────────────────────
    buys   = sum(1 for r in result_map.values() if not r["error"] and "BUY"  in str((r["signal"] or {}).get("final_signal", "")))
    sells  = sum(1 for r in result_map.values() if not r["error"] and "SELL" in str((r["signal"] or {}).get("final_signal", "")))
    holds  = sum(1 for r in result_map.values() if not r["error"] and "HOLD" in str((r["signal"] or {}).get("final_signal", "")))
    errors = sum(1 for r in result_map.values() if r["error"])

    console.print(Panel(
        f"[green]BUY {buys}[/green]  |  [yellow]HOLD {holds}[/yellow]  |  "
        f"[red]SELL {sells}[/red]  |  [dim]ERROR {errors}[/dim]"
        f"  —  完成时间 {datetime.now().strftime('%H:%M:%S')}",
        title="横截面汇总", border_style="cyan"
    ))

    # ── 输出完整 JSON 文件 ───────────────────────────────────
    output_payload = {
        "meta": {
            "run_start":   run_start,
            "run_end":     datetime.now().isoformat(),
            "total":       total,
            "success":     total - errors,
            "errors":      errors,
            "summary":     {"BUY": buys, "HOLD": holds, "SELL": sells},
        },
        "groups": [],
        "raw_results": list(result_map.values()),
    }

    for group in GROUPS:
        group_results = [result_map[t] for t, _ in group["tickers"]]
        output_payload["groups"].append({
            "id":      group["id"],
            "name":    group["name"],
            "results": group_results,
        })

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, ensure_ascii=False, indent=2, default=str)

    console.print(f"\n[bold green]完整结果已保存至:[/bold green] {OUTPUT_JSON}\n")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
