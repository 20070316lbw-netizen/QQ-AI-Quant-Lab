import os
import shutil

BRAIN_DIR = r'C:\Users\lbw15\.gemini\antigravity\brain\88d8f421-374e-42de-aea5-14e30065f5a5'
TARGET_DIR = r'c:\Users\lbw15\Desktop\Dev_Workspace\research_logs_repo\QQ-AI-Quant-Lab\reports'

mapping = {
    "project_progress_summary.md": "00_AlphaRanker_项目全景进展与未来路线图.md",
    "research_notes_us.md": "01_AlphaRanker_美股基础量价因子单维检验_A.md",
    "research_notes_fundamental_alpha.md": "01_AlphaRanker_美股基本面因子单维检验_B.md",
    "research_notes_neutral.md": "02_AlphaRanker_因子正交化与纯真波动率(VolRes)的提取.md",
    "research_notes_regime_switch.md": "03_AlphaRanker_状态机模型_A.md",
    "research_notes_moe.md": "03_AlphaRanker_MoE架构设想_B.md",
    "research_notes_alpha_genome.md": "04_AlphaRanker_AlphaGenome基因序列(M+V+L)的诞生.md",
    "research_notes_ablation_final.md": "05_AlphaRanker_消融实验报告_A.md",
    "placebo_test_report.md": "05_AlphaRanker_安慰剂测试报告_B.md",
    "research_notes_cn_realtime.md": "06_AlphaRanker_跨市场验证：A股最新10天极限截面实证.md",
    "research_notes_cn_longterm.md": "07_AlphaRanker_A股长周期全状态基因评估报告.md",
    "research_notes_cn_deep_dive.md": "08_AlphaRanker_A股基因深度科学实证与统计审计.md",
    "research_notes_cn_ic_decay.md": "09_AlphaRanker_A股核心基因时序衰减与持有期评测报告.md",
    "notebooklm_index.md": "notebooklm_index.md"
}

def sync_reports():
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)
        
    for src_name, target_name in mapping.items():
        src_path = os.path.join(BRAIN_DIR, src_name)
        target_path = os.path.join(TARGET_DIR, target_name)
        
        if os.path.exists(src_path):
            print(f"Syncing: {src_name} -> {target_name}")
            shutil.copy2(src_path, target_path)
        else:
            print(f"Skip: {src_name} (not found)")

if __name__ == "__main__":
    sync_reports()
