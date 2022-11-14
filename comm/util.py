import pandas as pd
import datetime
import time
import requests

#타임스템프에서 초 추출
def get_time_ss(mili_time):
    mili_time = float(mili_time)
    KST = datetime.timezone(datetime.timedelta(hours=9))
    dt = datetime.datetime.fromtimestamp(mili_time, tz=KST)
    timeline = str(dt.strftime('%S'))
    return timeline

#타임스템프에서 분 추출
def get_time_mm(mili_time):
    mili_time = float(mili_time)
    KST = datetime.timezone(datetime.timedelta(hours=9))
    dt = datetime.datetime.fromtimestamp(mili_time, tz=KST)
    timeline = str(dt.strftime('%M'))
    return timeline

#타임스템프에서 시간 추출
def get_time_hhmmss(mili_time):
    mili_time = float(mili_time)
    KST = datetime.timezone(datetime.timedelta(hours=9))
    dt = datetime.datetime.fromtimestamp(mili_time, tz=KST)
    timeline = str(dt.strftime('%D %H:%M:%S'))
    return timeline

#로그 기록
def log_info(message):
    print("{}".format(message))

#1분 데이터 가져오기
def get_web_1m_data(base_candle_url):
    df = pd.DataFrame()
    cols = ['timestamp', 'openingPrice', 'highPrice', 'lowPrice', 'tradePrice', 'candleAccTradeVolume']
    rename_columns = {'timestamp': 't', 'openingPrice': 'o', 'highPrice': 'h', 'lowPrice': 'l', 'tradePrice': 'c',
               'candleAccTradeVolume': 'v'}

    for i in range(0, 3):  # 오류가 난다면 최대 3번까지 반복하면서 데이터를 가져온다.
        try:
            webpage = requests.get(base_candle_url, timeout=3)
            df_temp = pd.read_json(webpage.content)
            df_candle_temp = df_temp[cols].sort_values(by='timestamp', ascending=True)
            df = df_candle_temp.rename(columns=rename_columns)
            break
        except:
            print("*pd.read_json(webpage.content) error !!! ")
        time.sleep(1) #오류 발생하면 1초 후 다시 시도
    return df

#오픈건수 계산
def check_open_cnt(check_data, amt_list):
    # [0.0, 4.5, 9.9, 16.38, 24.156, 33.4872, 44.6846, 58.1215]
    idx = 1
    for data in amt_list:
        if round(float(check_data),0) == round(float(data),0):
            return idx
        idx = idx + 1
    return idx

#단계별 구매 수량
def get_buy_amt_list(buy_amt_unit, buy_cnt_limit, increace_rate):
    buy_amt = 0
    buy_amt_list = [0.0]
    for idx in range(0, buy_cnt_limit):
        temp_amt = buy_amt_unit + buy_amt * increace_rate
        buy_amt = round(buy_amt + temp_amt, 4)
        buy_amt_list.append(buy_amt)
    return buy_amt_list

#손실 최소화 실현 금액 계산
def get_max_loss(close, buy_amt_unit, buy_cnt_limit, increace_rate, max_loss_rate):
    buy_amt = 0
    buy_price = 0
    for idx in range(0, buy_cnt_limit):
        temp_amt = buy_amt_unit + buy_amt * increace_rate
        buy_price = round(buy_price + close * temp_amt, 4)
        buy_amt = round(buy_amt + temp_amt, 4)
    return round(buy_price * max_loss_rate, 4)