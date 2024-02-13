from lumibot.tools import CcxtCacheDB
import pytest
import duckdb
from datetime import datetime
import os


# PYTHONWARNINGS="ignore::DeprecationWarning"; pytest test/test_ccxt_cache.py

@pytest.mark.parametrize("exchange_id,symbol,timeframe,start,end",
                         [ ("binance","BTC/USDT","1m",datetime(2023, 3, 2),datetime(2023, 3, 4))
                         ])
def test_cache_download_data(exchange_id:str, symbol:str, timeframe:str, start:datetime, end:datetime)->None:
    cache = CcxtCacheDB(exchange_id)
    cache_file_path = cache.get_cache_file_name(symbol,timeframe)

    # Remove cache file if exists.
    if os.path.exists(cache_file_path):
        os.remove(cache_file_path)

    # Download data and store in cache.
    df1 = cache.download_ohlcv(symbol,timeframe,start,end)

    assert os.path.exists(cache_file_path)

    # Counting data for the requested time period.
    dt = end - start
    if timeframe == "1d":
        request_data_length = dt.days
    else:
        request_data_length = dt.total_seconds() / 60

    # The cached data must be greater than or equal to the requested data.
    assert len(df1) >= request_data_length
    # The last time of the cached data must be equal to or greater than the requested time.
    assert df1.index.max() >= end
    # The first time of the cached data must be equal to or less than the requested time.
    assert df1.index.min() <= start

    # Fetch data stored in cache.
    df2 = cache.get_data_from_cache(symbol,timeframe,start,end)
    assert len(df2) >= request_data_length
    assert df2.index.max() >= end
    assert df2.index.min() <= start



@pytest.mark.parametrize("exchange_id,symbol,timeframe,start,end",
                         [ ("binance","BTC/USDT","1m",datetime(2023, 3, 3),datetime(2023, 3, 6))
                         ])
def test_cache_download_data_without_overap(exchange_id:str, symbol:str, timeframe:str, start:datetime, end:datetime)->None:
    """Test for cases where the requested time range is partially covered by cache, but not partially covered by cache, if cache already exists.
    In this case, you need to combine the data in the cache with the newly downloaded data to create the data for the requested time range.
    Therefore, the existing start range must be larger than the requested start range and the existing end range must be smaller than the requested end range.
    The final range of updated data should be from the existing start range to the requested end range.
    """

    cache = CcxtCacheDB(exchange_id)
    cache_file_path = cache.get_cache_file_name(symbol,timeframe)

    # Read the cache_dt_ranges table before caching new data to duckdb
    with duckdb.connect(cache_file_path) as con:
        df_down_range = con.execute("SELECT * from cache_dt_ranges").fetch_df()
    prev_start_dt = df_down_range.iloc[0].start_dt
    prev_end_dt = df_down_range.iloc[0].end_dt

    # Download data and store in cache.
    df_cache = cache.download_ohlcv(symbol,timeframe,start,end)

    # Read the cache_dt_ranges table after caching new data to duckdb
    with duckdb.connect(cache_file_path) as con:
        df_down_range = con.execute("SELECT * from cache_dt_ranges").fetch_df()

    # 기존 데이터 범위가 새로운 데이터 범위로 업데이트 되었는지 확인
    # 데이터 범위의 개수는 1개여야 한다.
    assert len(df_down_range) == 1

    cur_start_dt = df_down_range.iloc[0].start_dt
    cur_end_dt = df_down_range.iloc[0].end_dt

    # 새로운 데이터 범위는 기존 데이터 범위보다 커야 한다.
    assert cur_start_dt <= prev_start_dt
    assert cur_end_dt >= prev_end_dt

    # 새로운 데이터 범위는 요청한 데이터 범위보다 커야 한다.
    assert cur_end_dt >= end
    assert cur_start_dt <= start

    # Counting data for the requested time period.
    dt = end - start
    if timeframe == "1d":
        request_data_length = dt.days
    else:
        request_data_length = dt.total_seconds() / 60

    # The cached data must be greater than or equal to the requested data.
    assert len(df_cache) >= request_data_length
    # The last time of the cached data must be equal to or greater than the requested time.
    assert df_cache.index.max() >= end
    # The first time of the cached data must be equal to or less than the requested time.
    assert df_cache.index.min() <= start

    # Remove cache file if exists.
    if os.path.exists(cache_file_path):
        os.remove(cache_file_path)