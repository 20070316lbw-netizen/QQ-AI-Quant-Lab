def compute_base_signal(z_score: float, threshold: float = 0.5) -> str:
    """
    负责最核心、最底层的方向仲裁。这是系统唯一能决定资金多空暴露的地方。
    """
    if z_score > threshold:
        return "BUY"
    elif z_score < -threshold:
        return "SELL"
    else:
        return "HOLD"
