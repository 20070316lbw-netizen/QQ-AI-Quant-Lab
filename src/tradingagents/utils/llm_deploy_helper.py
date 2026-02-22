import subprocess
import shutil
import platform
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

def check_ollama_installed():
    return shutil.which("ollama") is not None

def get_ollama_version():
    try:
        result = subprocess.run(["ollama", "--version"], capture_output=True, text=True)
        return result.stdout.strip()
    except:
        return "未知"

def list_local_models():
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        return result.stdout
    except:
        return "无法获取模型列表"

def deploy_assistant_ui():
    console.print(Panel.fit("[bold green]🛠️ AI-Quant-Lab: LLM 部署助手[/bold green]", border_style="green"))
    
    # 状态检测
    is_installed = check_ollama_installed()
    
    table = Table(title="系统环境检测", show_header=False)
    table.add_row("操作系统", platform.system())
    table.add_row("Ollama 安装状态", "[green]已安装[/green]" if is_installed else "[red]未找到 (请访问 ollama.com 安装)[/red]")
    if is_installed:
        table.add_row("Ollama 版本", get_ollama_version())
    
    console.print(table)
    
    if not is_installed:
        console.print("\n[bold yellow]⚠️ 请先安装 Ollama 服务以激活本地智能体集群。[/bold yellow]")
        console.print("下载地址: [blue]https://ollama.com/download[/blue]")
        return

    console.print("\n[bold cyan]推荐模型库 (适合量化分析):[/bold cyan]")
    rec_table = Table(show_header=True, header_style="bold magenta")
    rec_table.add_column("模型名称", style="dim")
    rec_table.add_column("用途", width=40)
    rec_table.add_column("资源消耗")
    
    rec_table.add_row("qwen2.5:3b", "极力推荐：速度极快，中文理解出色，适合分析报告生成", "低 (4G显存)")
    rec_table.add_row("qwen2.5-coder:7b", "推荐：逻辑更强，代码和格式处理更精准", "中 (8G显存)")
    rec_table.add_row("deepseek-v2:16b", "高级：深度推理首选 (适合快速思考 LLM 角色)", "高 (16G+显存)")
    
    console.print(rec_table)
    
    console.print("\n[italic gray]当前已下载的本地模型:[/italic gray]")
    console.print(list_local_models())
    
    console.print("\n[bold yellow]提示:[/bold yellow] 如需下载模型，请在命令行执行: [bold cyan]ollama run <模型名>[/bold cyan]")
    
if __name__ == "__main__":
    deploy_assistant_ui()
