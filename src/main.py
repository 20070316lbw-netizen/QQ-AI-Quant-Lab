import sys
import os
import json

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import questionary
from questionary import Style
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich import box

from crawlers.data_gateway import gateway
from core.kronos_engine import KronosEngine
from trading_signal import generate_signal

console = Console()

MENU_STYLE = Style([
    ('qmark',       'fg:#00e5ff bold'),
    ('question',    'fg:#f0f0f0 bold'),
    ('answer',      'fg:#00e5ff bold'),
    ('pointer',     'fg:#00e5ff bold'),
    ('highlighted', 'fg:#00e5ff bold'),
    ('selected',    'fg:#00e5ff'),
])

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    clear_screen()
    console.print(Panel(
        "\n  [bold cyan]ECHO[/bold cyan]  Quantitative Intelligence System\n"
        "  [dim]Interactive Terminal  v2.4  |  Module Dispatch Mode[/dim]\n",
        border_style="cyan"
    ))

def ask_ticker(prompt_text="输入目标标的代码 (如 AAPL)"):
    return questionary.text(
        prompt_text,
        style=MENU_STYLE,
        validate=lambda t: True if t.strip() else "代码不能为空"
    ).ask()

def action_data_flow():
    """数据流观测器"""
    ticker = ask_ticker()
    if not ticker: return
    ticker = ticker.strip().upper()

    console.print(f"\n[dim]Fetching live data stream for {ticker}...[/dim]")
    try:
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=10)

        raw_csv = gateway.get_stock_data(
            ticker,
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
        console.rule("[bold cyan]O H L C V   D A T A   S T R E A M")
        lines = raw_csv.strip().split("\n")
        preview = "\n".join(lines[:7]) + ("\n... (truncated)" if len(lines) > 7 else "")
        console.print(preview)

        console.rule("[bold magenta]F U N D A M E N T A L   R I S K   M E T R I C S")
        fun = gateway.get_fundamental_risk_metrics(ticker)
        tbl = Table(box=box.MINIMAL_DOUBLE_HEAD)
        for k in fun:
            tbl.add_column(k, justify="right")
        tbl.add_row(*[str(v) for v in fun.values()])
        console.print(tbl)

    except Exception as e:
        console.print(f"[bold red]❌ 数据流异常: {e}[/]")

    questionary.press_any_key_to_continue("按任意键返回主菜单...").ask()

def action_kronos_raw():
    """时序引擎直连"""
    ticker = ask_ticker("输入推演目标标的 (如 NVDA)")
    if not ticker: return
    ticker = ticker.strip().upper()

    console.print(f"\n[dim]Routing to Kronos-Mini Transformer for {ticker}...[/dim]")
    try:
        from datetime import datetime
        raw_pred = KronosEngine.get_raw_prediction(ticker, datetime.now().strftime("%Y-%m-%d"))

        tbl = Table(title=f"Kronos Raw Output  —  {ticker}", box=box.ROUNDED)
        tbl.add_column("指标", style="cyan")
        tbl.add_column("数值", style="bold green")
        tbl.add_row("期望收益率 (Mean Return)",    f"{raw_pred['expected_return']:.4%}")
        tbl.add_row("预测波动迷茫度 (Uncertainty)", f"{raw_pred['uncertainty']:.4%}")
        tbl.add_row("趋势强度 / Z-Score",           f"{raw_pred['z_score']:.4f}")
        console.print(tbl)
        console.print("[dim]以上为数学内核纯输出，尚未叠加 O-Score 与基本面修正。[/dim]")

    except Exception as e:
        console.print(f"[bold red]❌ 引擎调度失败: {e}[/]")

    questionary.press_any_key_to_continue("按任意键返回主菜单...").ask()

def action_full_pipeline():
    """全景综合策略裁定"""
    ticker = ask_ticker("输入待裁决资产代码")
    if not ticker: return
    ticker = ticker.strip().upper()

    with console.status(f"[bold green]联合审查 {ticker} 全架构流向..."):
        try:
            signal = generate_signal(ticker)
            json_str = json.dumps(signal, indent=2, ensure_ascii=False)

            console.rule(f"[bold white]FINAL VERDICT  —  {ticker}")
            if "CRASH_SELL" in json_str or "FUNDAMENTAL_BUST_OVERRIDE" in json_str:
                console.print(f"[bold red]{json_str}[/]")
            elif '"direction": "BUY"' in json_str:
                console.print(f"[bold green]{json_str}[/]")
            else:
                console.print(f"[white]{json_str}[/]")

            console.print("\n[bold cyan]>> 决策流路径说明[/]")
            console.print("  [dim]1. Kronos Transformer → Z-Score 趋势强度裁决[/]")
            console.print("  [dim]2. Volatility Discount → 模型迷茫度越高, 仓位指数衰减[/]")
            console.print("  [dim]3. Multi-Factor O-Score → 财务护城河加权修正[/]")
            console.print("  [dim]4. Fundamental Bust Override → 异常杠杆一票否决所有方向[/]")

        except Exception as e:
            console.print(f"[bold red]❌ 全景拼合失败: {e}[/]")
            import traceback
            traceback.print_exc()

    questionary.press_any_key_to_continue("按任意键返回主菜单...").ask()

def interactive_loop():
    CHOICES = {
        "  1.  数据流观测器      [Data Stream Inspection]":  action_data_flow,
        "  2.  时序引擎直连      [Kronos Engine Testing]":   action_kronos_raw,
        "  3.  全景策略综合裁定  [Full Pipeline Verdict]":   action_full_pipeline,
        "  ─────────────────────────────────────────────":  None,
        "  0.  退出系统          [Exit]":                   None,
    }

    while True:
        print_header()
        selection = questionary.select(
            "使用方向键 ↑/↓ 选择模块，回车确认",
            choices=list(CHOICES.keys()),
            style=MENU_STYLE,
            use_indicator=True,
        ).ask()

        if selection is None or selection.strip().startswith("0"):
            console.print("\n[dim]Disconnecting... Goodbye.[/dim]")
            break
        
        fn = CHOICES.get(selection)
        if fn:
            fn()

if __name__ == "__main__":
    try:
        interactive_loop()
    except KeyboardInterrupt:
        sys.exit(0)
