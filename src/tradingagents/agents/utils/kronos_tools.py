from langchain_core.tools import tool
from typing import Annotated
import pandas as pd
from crawlers.data_gateway import gateway
from kronos.api import predict_market_trend

@tool
def get_market_prediction(
    symbol: Annotated[str, "Ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format for historical context bounding"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format for historical context bounding"],
    pred_len: Annotated[int, "Number of days into the future to predict"] = 30,
) -> str:
    """
    Retrieve future market price predictions (open, high, low, close, volume) for a given ticker symbol.
    Powered by the Kronos local foundational model.
    Args:
        symbol (str): Ticker symbol
        start_date (str): Start date for pulling historical data (e.g. YYYY-MM-DD)
        end_date (str): End date. The model predicts starting from the day after this date.
        pred_len (int): How many days (business days) to predict into the future
    Returns:
        str: A formatted string of the predicted future dataframe.
    """
    
    # 1. Ask gateway for historical dataframe (must be parsed back to df)
    raw_data_str = gateway.get_stock_data(symbol, start_date, end_date)
    
    # The gateway returns a string with some header lines starting with '#'
    # We need to extract just the CSV part
    lines = raw_data_str.strip().split('\n')
    csv_lines = [line for line in lines if not line.startswith('#') and line.strip()]
    
    if not csv_lines or "Error" in raw_data_str or "No data" in raw_data_str:
        return f"Failed to fetch historical data for {symbol}, cannot run prediction. Details: {raw_data_str}"
        
    try:
        import io
        csv_str = '\n'.join(csv_lines)
        df = pd.read_csv(io.StringIO(csv_str), index_col="Date", parse_dates=True)
        
        # Ensure only columns expected by Kronos are kept and formatted lowercase
        df.rename(columns={
            "Open": "open", "High": "high", "Low": "low", 
            "Close": "close", "Volume": "volume"
        }, inplace=True)
        
        # 2. Run Kronos predict
        prediction_df = predict_market_trend(df, pred_len=pred_len)
        
        # 3. Format output
        header = f"### Kronos AI Prediction for {symbol.upper()} (Next {pred_len} Days)\n"
        header += f"*Based on historical data up to {end_date}*\n\n"
        
        # Round the values for nicer LLM reading
        prediction_df = prediction_df.round(2)
        
        return header + prediction_df.to_csv()
        
    except Exception as e:
        return f"Kronos prediction failed due to internal error: {str(e)}"
