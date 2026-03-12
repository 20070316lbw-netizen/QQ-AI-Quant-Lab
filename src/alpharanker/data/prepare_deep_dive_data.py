import baostock as bs
import pandas as pd
import os

def main():
    print(">> Logging in to Baostock...")
    lg = bs.login()
    if lg.error_code != '0':
        print(f"Login failed: {lg.error_msg}")
        return

    # 1. HS300 Constituents
    print(">> Fetching HS300 constituents...")
    rs_hs300 = bs.query_hs300_stocks()
    hs_list = []
    while rs_hs300.next():
        hs_list.append(rs_hs300.get_row_data())
    df_hs = pd.DataFrame(hs_list, columns=rs_hs300.fields)
    df_hs['index_group'] = 'HS300'

    # 2. ZZ500 (CSI500) Constituents
    print(">> Fetching CSI500 constituents...")
    rs_zz500 = bs.query_zz500_stocks()
    zz_list = []
    while rs_zz500.next():
        zz_list.append(rs_zz500.get_row_data())
    df_zz = pd.DataFrame(zz_list, columns=rs_zz500.fields)
    df_zz['index_group'] = 'ZZ500'

    bs.logout()

    # Merge and Cleanup
    df = pd.concat([df_hs, df_zz], ignore_index=True)
    # Baostock code is sh.600000, we need to handle format if necessary
    # Our features use standard codes or the index-map might need conversion
    # Let's see our feature file ticker format
    
    output_path = r'C:\Data\Market\cn\index_map.parquet'
    df.to_parquet(output_path)
    print(f">> Index map saved to {output_path}")

if __name__ == "__main__":
    main()
