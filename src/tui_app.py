from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, DataTable, TabbedContent, TabPane
from textual.containers import Container, Horizontal, Vertical
from textual.binding import Binding

class AlphaGenomeApp(App):
    """Alpha Genome CLI 交易战情室 (TUI)"""
    
    TITLE = "Alpha Genome CLI v1.0"
    SUB_TITLE = "基因驱动量化研究终端"
    CSS = """
    Screen {
        background: #0f172a;
    }
    
    #active-regime {
        background: #1e293b;
        color: #38bdf8;
        padding: 1;
        text-align: center;
        border: solid #0ea5e9;
    }
    
    #sidebar {
        width: 30;
        background: #1e293b;
        border-left: solid #334155;
        padding: 1;
    }
    
    .status-bear {
        color: #f87171;
        text-style: bold;
    }
    
    .status-bull {
        color: #4ade80;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "退出", show=True),
        Binding("r", "refresh", "刷新数据", show=True),
        Binding("1", "switch_tab('signals')", "今日信号"),
        Binding("2", "switch_tab('health')", "因子体检"),
        Binding("3", "switch_tab('hologram')", "截面全息"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        
        with Container():
            with Horizontal():
                with TabbedContent(id="tabs"):
                    with TabPane("今日信号", id="signals"):
                        yield Static("🐻 当前状态：[span class=status-bear]熊市 (MA250 Below)[/span]", id="active-regime")
                        yield DataTable(id="signal-table")
                    with TabPane("因子体检", id="health"):
                        yield Static("因子 IC 稳定性与衰减监控 (加载中...)", id="health-viewer")
                    with TabPane("横截面全息图", id="hologram"):
                        yield Static("Alpha 基因空间分布图 (ASCII 渲染中...)", id="hologram-canvas")
                
                with Vertical(id="sidebar"):
                    yield Static("[bold cyan]500元小助手[/bold cyan]")
                    yield Static("-" * 25)
                    yield Static("推荐: 600008.SS")
                    yield Static("价格: 3.08元")
                    yield Static("建议: 买入100股")
                    yield Static("-" * 25)
                    yield Static("Alpha评价: 1.20")

        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#signal-table", DataTable)
        table.add_columns("排名", "股票名称", "代码", "Alpha评分", "主驱动因子", "价格")
        table.cursor_type = "row"
        self.action_refresh()

    def action_refresh(self) -> None:
        """刷新全量数据并更新 UI"""
        try:
            import os
            import pandas as pd
            import sys
            sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
            from config import CN_DIR
            from alpharanker.configs.cap_aware_weights import get_weights
            
            FEATURES_PATH = os.path.join(CN_DIR, 'cn_features_enhanced.parquet')
            MACRO_PATH = os.path.join(CN_DIR, 'macro_regime.parquet')
            
            if not os.path.exists(FEATURES_PATH):
                self.notify("⚠️ 特征库未找到", severity="error")
                return

            df = pd.read_parquet(FEATURES_PATH)
            latest_date = df['date'].max()
            latest_df = df[df['date'] == latest_date].copy()
            
            # 1. 更新信号表格 (基于 ZZ500 示例)
            weights = get_weights("ZZ500", horizon_days=20)
            latest_df['alpha_score'] = 0
            for f, w in weights.items():
                if f in latest_df.columns:
                    latest_df['alpha_score'] += latest_df[f] * w
            
            top_20 = latest_df.sort_values('alpha_score', ascending=False).head(20)
            table = self.query_one("#signal-table", DataTable)
            table.clear()
            for i, (_, row) in enumerate(top_20.iterrows()):
                # 简单判定主驱动因子
                main_driver = "价值 (V)" if row.get('sp_ratio_rank', 0) > 0.8 else "动量 (M)"
                table.add_row(
                    str(i+1), 
                    row['ticker'], 
                    row['ticker'], 
                    f"{row['alpha_score']:.4f}", 
                    main_driver,
                    f"{row['raw_close']:.2f}"
                )

            # 2. 更新状态栏
            regime_text = "🐻 当前状态：[span class=status-bear]熊市 (MA250 Below)[/span]"
            if os.path.exists(MACRO_PATH):
                m_df = pd.read_parquet(MACRO_PATH)
                latest_m = m_df[m_df['date'] <= latest_date].tail(1)
                if not latest_m.empty and latest_m['regime'].iloc[0] == 1:
                    regime_text = "🐂 当前状态：[span class=status-bull]牛市 (MA250 Above)[/span]"
            self.query_one("#active-regime").update(regime_text)
            self.update_health_dashboard(latest_df)
            self.update_hologram(latest_df)

            # 3. 更新侧边栏 (500元助手)
            low_price = latest_df[latest_df['raw_close'] <= 4.8].sort_values('alpha_score', ascending=False).head(1)
            if not low_price.empty:
                pick = low_price.iloc[0]
                sidebar = self.query_one("#sidebar")
                sidebar.remove_children()
                from textual.widgets import Static
                sidebar.mount(Static("[bold cyan]500元小助手[/bold cyan]"))
                sidebar.mount(Static("-" * 25))
                sidebar.mount(Static(f"推荐: [yellow]{pick['ticker']}[/yellow]"))
                sidebar.mount(Static(f"价格: {pick['raw_close']:.2f}元"))
                sidebar.mount(Static(f"建议: 买入 100 股"))
                sidebar.mount(Static(f"预计成本: {pick['raw_close']*100:.1f}元"))
                sidebar.mount(Static("-" * 25))
                sidebar.mount(Static(f"Alpha评分: {pick['alpha_score']:.4f}"))
                sidebar.mount(Static(f"\n[dim]最后更新: {latest_date.date()}[/dim]"))

            self.notify("✅ 数据刷新成功")
        except Exception as e:
            self.notify(f"❌ 刷新失败: {str(e)}", severity="error")

    def update_hologram(self, latest_df: pd.DataFrame) -> None:
        """渲染 ASCII 横截面全息图 (Value vs VolRes)"""
        width, height = 50, 20
        canvas = [[" " for _ in range(width)] for _ in range(height)]
        
        # 过滤有效点
        pts = latest_df.dropna(subset=['sp_ratio_rank', 'vol_60d_res_rank', 'label_next_month'])
        if pts.empty:
            return
            
        for _, row in pts.iterrows():
            x = int(row['sp_ratio_rank'] * (width - 1))
            y = int((1 - row['vol_60d_res_rank']) * (height - 1)) # Y轴反转
            
            color = "red" if row['label_next_month'] > 0 else "green"
            char = f"[bold {color}]·[/]"
            canvas[y][x] = char
            
        output = [f"vol_res ▲"]
        for row in canvas:
            output.append("   │ " + "".join(row))
        output.append("   └" + "─" * width + "▶ sp_ratio")
        
        self.query_one("#hologram-canvas").update("\n".join(output))

    def update_health_dashboard(self, latest_df: pd.DataFrame) -> None:
        """更新因子体检页面的柱状图"""
        from rich.table import Table
        from rich.bar import Bar
        from rich.panel import Panel
        from rich.columns import Columns
        
        # 定义核心监控因子
        mon_factors = {
            "sp_ratio_rank": "价值基因 (V)",
            "mom_60d_rank": "动量反转 (M)",
            "vol_60d_res_rank": "低波残差 (L)"
        }
        
        table = Table(title="Alpha 基因健康体检 (最近截面)", box=None)
        table.add_column("基因因子", justify="right")
        table.add_column("IC 强度/暴露", width=30)
        table.add_column("分值", justify="left")
        
        for f, name in mon_factors.items():
            if f in latest_df.columns:
                val = latest_df[f].mean()  # 简单用均值代表截面热度
                color = "green" if val > 0.5 else "red"
                table.add_row(
                    name,
                    Bar(1.0, 0, val, color=color),
                    f"{val:.2f}"
                )
        
        self.query_one("#health-viewer").update(table)

    def action_switch_tab(self, tab_id: str) -> None:
        self.query_one("#tabs", TabbedContent).active = tab_id

if __name__ == "__main__":
    app = AlphaGenomeApp()
    app.run()
