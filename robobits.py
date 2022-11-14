import pyupbit
import time
import comm.config as conf
import comm.trade as trade
import comm.util as util
import comm.calc_indicators as calc

######(1) 변수 초기화 ######
access = conf.G_API_KEY
secret = conf.G_SECRET_KEY
coin_name = 'KRW-XRP'
up = pyupbit.Upbit(access, secret)
base_candle_url = "https://crix-api-cdn.upbit.com/v1/crix/candles/minutes/1?code=CRIX.UPBIT.{}&count=200".format(coin_name)

revenue_rate = 0.014  #익절 비율 0.014
max_loss_rate = 0.239 #손절 비율 0.239
increace_rate = 0.248
buy_cnt_limit = 7   #최대 오픈 건수 7
buy_amt_unit = 4.5     #최소 오픈 수량

buy_amt_list = []    #단계별 주문수량
buy_amt_list = util.get_buy_amt_list(buy_amt_unit, buy_cnt_limit, increace_rate)
max_loss = 0          #손절 가격(stop loss 주문시 계산)

trade_flag = 1              #0:trade not yet, 1:trade done
process_sleep_time = 0.2    #대시시간

order_uuid = ""        #매수 주문 아이디
profit_uuid = ""       #이익 실현 주문 아이디
stop_uuid = ""         #손실 최소화 주문 아이디

# revenue_rate = 0.002  #익절 비율 0.014
# max_loss_rate = 0.003 #손절 비율 0.239
# increace_rate = 0.0
# buy_cnt_limit = 2   #최대 오픈 건수 7
# buy_amt_unit = 4     #최소 오픈 수량

util.log_info("*********** start trading ***********")

######(2) 주문 초기화(미체결 주문 전체 취소)
message = trade.cancel_all_order(up, coin_name)
if message != "good":
    util.log_info("+[{}]cancel_wait_order error msg:{}".
                  format(util.get_time_hhmmss(time.time()), message))


while True:
    check_ss = util.get_time_ss(time.time()) #초단위 체크

    ######(3) 분데이터 가져오기, 분데이터는 1초후 생성 start ######
    if check_ss in ('01','02'):
        #데이터 가져오기
        df = util.get_web_1m_data(base_candle_url)
        time.sleep(process_sleep_time)

        #기술적 지표 생성
        df['wma7'] = calc.get_wma(df['c'], 7)
        df['wma99'] = calc.get_wma(df['c'], 99)
        df['vwap'] = calc.get_vwap(df['h'], df['l'], df['c'], df['v'], 14)  # vwap계산

        df_one = df.iloc[df.shape[0]-1:,] #마지막 한 건 가져오기
        wma7 = df_one['wma7'].values[0]
        wma99 = df_one['wma99'].values[0]
        vwap = df_one['vwap'].values[0]

        trade_flag = 0
    ###### 분데이터 가져오기 end ######

    ######(4) buy process start ######
    if trade_flag == 0 and check_ss in ('59', '00'):
        ###(4)-1 cancel before timestep start ###
        if order_uuid != "":
            message, status, price, amt = trade.get_order_status(up, coin_name, order_uuid)
            if message != "good":
                util.log_info("+[{}]cancel before timestep-get_order_state error msg:{} uuid:{}".
                              format(util.get_time_hhmmss(time.time()), message, order_uuid))
                continue

            if status == "done": # 주문체결
                order_uuid = ""

            if status == "wait": #미체결, 주문 취소
                message, result = trade.cancel_order(up, order_uuid)
                if message != "good":
                    util.log_info("+[{}]cancel before timestep-cancel_order error msg:{} uuid:{}".
                                  format(util.get_time_hhmmss(time.time()), message, order_uuid))
                    continue
                time.sleep(process_sleep_time)
        ### cancel before timestep end ###

        ###(4)-2 buy start ###
        #계좌조회
        message, buy_amt, buy_price = trade.get_balances(up, coin_name)
        if message != "good":
            util.log_info("+[{}]buy coin-get_balances error msg:{}".
                          format(util.get_time_hhmmss(time.time()), message))
            continue
        time.sleep(process_sleep_time)

        #현재가 조회
        message, result = trade.get_current_price(up, coin_name)
        if message != "good":
            util.log_info("+[{}]take profit-get_current_price error msg:{}".
                          format(util.get_time_hhmmss(time.time()), message))
            continue
        close = float(result)

        #매수 건수 조회
        buy_cnt = util.check_open_cnt(buy_amt, buy_amt_list)
        util.log_info("-[{}]close:{} vwap:{} wma7:{} wma99:{} bcnt:{} bcntl:{}"
                 .format(util.get_time_hhmmss(time.time()), round(close,4), round(vwap,4),
                         round(wma7,4), round(wma99,4), buy_cnt-1, buy_cnt_limit))
        time.sleep(process_sleep_time)

        #매수 시작
        if buy_cnt <= buy_cnt_limit and close < vwap and close < wma7 and wma7 > wma99:

            order_buy_amt = buy_amt_unit + float(buy_amt) * increace_rate

            # 현재가 조회
            message, result = trade.get_current_price(up, coin_name)
            if message != "good":
                util.log_info("+[{}]buy coin-get_current_price error msg:{}".
                              format(util.get_time_hhmmss(time.time()), message))
                continue

            # 거래 단위 조정
            trade_price = "{:0.0{}f}".format(float(result), 0) #정수
            trade_amt = "{:0.0{}f}".format(order_buy_amt, 4)  #소수점 넷째자리

            # order
            message, order_uuid = trade.buy_limit_order(up, coin_name, trade_price, trade_amt)
            if message != "good":
                util.log_info("+[{}]buy coin-buy_limit_order error msg:{}".
                              format(util.get_time_hhmmss(time.time()), message))
                order_uuid = ""
                continue
            trade_flag = 1
            trading_msg = "*[{}]buy coin uuid:{} v:{} c:{} p:{} a:{} m:{}".format(
                util.get_time_hhmmss(time.time()), order_uuid, round(vwap,4), close,
                trade_price, trade_amt, message)
            util.log_info(trading_msg)
            time.sleep(process_sleep_time)
        ### buy end ###
    ###### buy process end ######

    if check_ss in ('10', '20', '30', '40', '50'):
    ######(5) take profit start #####
        ###(5)-1 cancel before timestep start ###
        if profit_uuid != "":
            message, status, price, amt = trade.get_order_status(up, coin_name, profit_uuid)
            if message != "good":
                util.log_info("+[{}]profit cancel before timestep-get_order_state error msg:{} uuid:{}".
                              format(util.get_time_hhmmss(time.time()), message, profit_uuid))
                continue

            if status == "done":  # 주문체결
                profit_uuid = ""

            if status == "wait":  # 미체결, 주문 취소
                message, result = trade.cancel_order(up, profit_uuid)
                if message != "good":
                    util.log_info("+[{}]profit cancel before timestep-cancel_order error msg:{} uuid:{}".
                                  format(util.get_time_hhmmss(time.time()), message, profit_uuid))
                    continue
                time.sleep(process_sleep_time)
        ### cancel before timestep end ###

        ###(5)-2 take profit start###
        #계좌 조회
        message, buy_amt, buy_price = trade.get_balances(up, coin_name)
        if message != "good":
            util.log_info("+[{}]take profit-get_balances error msg:{}".
                          format(util.get_time_hhmmss(time.time()), message))
            continue
        time.sleep(process_sleep_time)

        if float(buy_amt) > 0:
            #현재가 조회
            message, result = trade.get_current_price(up, coin_name)
            if message != "good":
                util.log_info("+[{}]take profit-get_current_price error msg:{}".
                              format(util.get_time_hhmmss(time.time()), message))
                continue

            #이익실현 주문
            message, uuid = trade.take_profit(up, coin_name, buy_amt, buy_price, result, revenue_rate)

            if message == "good":
                profit_uuid = uuid
                util.log_info(
                    "*[{}]take profit uuid:{} buy_amt:{} buy_price:{} now_price:{} msg:{}".format(
                        util.get_time_hhmmss(time.time()), profit_uuid, buy_amt,
                        buy_price, result, message)
                )
            time.sleep(process_sleep_time)
        ###take profit end###
    ###### take profit end #####

    ######(6) stop loss start #####
        ###(6)-1 cancel before timestep start ###
        if stop_uuid != "":
            message, status, price, amt = trade.get_order_status(up, coin_name, stop_uuid)
            if message != "good":
                util.log_info("+[{}]stop cancel before timestep-get_order_state error msg:{} uuid:{}".
                              format(util.get_time_hhmmss(time.time()), message, stop_uuid))
                continue

            if status == "done":  # 주문체결
                stop_uuid = ""

            if status == "wait":  # 미체결, 주문 취소
                message, result = trade.cancel_order(up, stop_uuid)
                if message != "good":
                    util.log_info("+[{}]stop cancel before timestep-cancel_order error msg:{} uuid:{}".
                                  format(util.get_time_hhmmss(time.time()), message, stop_uuid))
                    continue
                time.sleep(process_sleep_time)
        ### cancel before timestep end ###

        ###(6)-2 stop loss start###
        #계좌조회
        message, buy_amt, buy_price = trade.get_balances(up, coin_name)
        if message != "good":
            util.log_info("+[{}]stop loss-get_balances error msg:{}".
                          format(util.get_time_hhmmss(time.time()), message))
            continue
        time.sleep(process_sleep_time)

        if float(buy_amt) > 0:
            #현재가 조회
            message, result = trade.get_current_price(up, coin_name)
            if message != "good":
                util.log_info("+[{}]stop loss-get_current_price error msg:{}".
                              format(util.get_time_hhmmss(time.time()), message))
                continue

            #손실최소화 주문
            message, uuid = trade.stop_loss(up, coin_name, buy_amt, buy_price, result, max_loss_rate)

            if message == "good":
                stop_uuid = uuid
                util.log_info(
                    "*[{}]stop loss id:{} buy_amt:{} buy_price:{} now_price:{} msg:{}".format(
                        util.get_time_hhmmss(time.time()), stop_uuid, buy_amt,
                        buy_price, result, message)
                )
            time.sleep(process_sleep_time)
        ###stop loss end###
    ###### stop loss end #####

    time.sleep(1) #2초후 다시 시도