import sys
import os
import json
from datetime import datetime
from rich.console import Console
from rich.panel import Panel

# Ensure src is in the python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(current_dir, ".."))
if src_dir not in sys.path:
    sys.path.append(src_dir)

from crawlers.data_gateway import DataGateway
from trading_signal import generate_signal
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

console = Console()

def run_stress_test(event_name: str, target_dates: list, ticker: str):
    """
    运行极端黑天鹅脱机抗压测试 (轻量直达核心测算法)
    """
    console.print(Panel(f"[bold red]🚨 BLACK SWAN ISOLATION TEST 🚨[/bold red]\n[yellow]Engaging Event: {event_name} | Ticker: {ticker}[/yellow]", border_style="red"))
    
    # 强制开启系统的物理级离线旁路模式
    DataGateway.offline_mode = True
    DataGateway.offline_data_dir = os.path.join(src_dir, "backtest", "extreme_data")
    DataGateway.offline_event_name = event_name

    results = []
    
    for date in target_dates:
        console.print(f"\n[bold cyan]▶ 模拟时间坐标跃迁至恐慌回溯点: {date}[/bold cyan]")
        console.print("[dim]隔离舱启用：系统直接捕获黑天鹅新闻情绪因子并将历史 K 线导入数学分析器...[/dim]")
        
        try:
            # 绕过重型的本地 LLM 图谱推理，因为在 OOM 环境下可能被强退
            # 直接由底层获取客观历史指标，并注入“测试桩(Mock)”性质的极端情感数据：极度悲观 (-0.9) 与 强黑天鹅风险警戒 (0.8)
            signal_pack = generate_signal(ticker, as_of_date=date, ext_sentiment=-0.9, ext_risk=0.8)
            
            console.print("\n[bold green]✅ 量化风控熔断器计算完毕，引擎底层拦截判断如下：[/bold green]")
            
            risk_info = signal_pack['metadata']
            
            console.print(f"- [客观推演] 预测 30 步波动率 (Uncertainty):   => {signal_pack['uncertainty']*100:.2f}%")
            console.print(f"- [安全壁垒] 波动率巨震惩罚 (Volatility Discount): => {risk_info.get('volatility_discount', 1.0):.4f}x")
            console.print(f"- [状态裁定] Regime 判定结果:                    => {signal_pack['regime']} (Z={signal_pack['z_score']})")
            console.print(f"- [NLP反向] 研报综合黑天鹅风险因子 (Risk):       => 0.80 (Mocked)")
            
            # 终极拷问：系统是否管住了手？
            final_pos = signal_pack['adjusted_position_strength']
            color = "red" if final_pos > 0.5 else "green"
            warning = "⚠️ 系统失控准备重仓抄底！" if final_pos > 0.5 else "🛡️ 系统成功熔断，拦住逆势加仓头寸。"
            
            console.print(f"👉 [bold {color}]【最终执行命令】建议持仓比例：{final_pos*100:.2f}% ({warning})[/bold {color}]")
            
            results.append({
                "date": date,
                "final_pos": final_pos
            })
            
        except Exception as e:
            console.print(f"[bold red]测试过程崩溃: {e}[/bold red]")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("\n--- 启动 2008 雷曼次贷危机熔断测试舱 ---")
    run_stress_test("2008_Subprime_Crisis", ["2008-09-17", "2008-10-15"], "AAPL")
    
    print("\n\n--- 启动 2020 新冠大熔断测试舱 ---")
    run_stress_test("2020_Covid_Crash", ["2020-03-09", "2020-03-16"], "KO")
