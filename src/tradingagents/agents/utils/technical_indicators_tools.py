from langchain_core.tools import tool
from typing import Annotated
from crawlers.data_gateway import gateway

@tool
def get_indicators(
    symbol: Annotated[str, "ticker symbol of the company"],
    indicator: Annotated[str, "technical indicator(s) to get, can be comma-separated like 'rsi,macd'"],
    curr_date: Annotated[str, "The current trading date, YYYY-mm-dd. Optional, defaults to today."] = None,
    look_back_days: Annotated[int, "how many days to look back"] = 30,
) -> str:
    """
    Retrieve technical indicators for a given ticker symbol.
    Uses the configured technical_indicators vendor.
    Args:
        symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
        indicator (str): Technical indicator to get the analysis and report of
        curr_date (str): The current trading date you are trading on, YYYY-mm-dd
        look_back_days (int): How many days to look back, default is 30
    Returns:
        str: A formatted dataframe containing the technical indicators for the specified ticker symbol and indicator.
    """
    return gateway.get_indicators(symbol, indicator, curr_date, look_back_days)