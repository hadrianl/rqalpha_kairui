#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/7/23 0023 16:25
# @Author  : Hadrianl 
# @File    : basestrategy.py
# @License : (C) Copyright 2013-2017, 凯瑞投资

from rqalpha.api import *
import talib
import datetime


def close_all(context, bar_dict):
    logger.info('早盘收市前清仓')
    context.STD = 0
    order_to(context.HSI, 0)

def init(context):
    # context.HSI = 'HSI'
    # update_universe(context.HSI)
    # context.futures = [context.HSI]
    logger.info('SP-init')
    subscribe('HSI1811')
    # context.HSI = 'HSI'
    # subscribe(context.HSI)
    # context.SHORTPERIOD = 12
    # context.LONGPERIOD = 26
    # context.SMOOTHPERIOD = 9
    # context.OBSERVATION = 100
    # context.long_signal = 0
    # context.short_signal = 0
    #
    # scheduler.run_daily(close_all, time_rule=16*60+29)
    # update_universe(context.HSI)
    # unsubscribe('HSI')
    # scheduler.run_daily(func, time_rule=market_open(0, 0))  # 定期运行，time_rule来控制运行时间
    # scheduler.run_weekly

def before_trading(context):
    logger.info('SP-before_trading')

def handle_bar(context, bar_dict):
    logger.info(f'{bar_dict["HSI1811"]}')
    logger.info(f'{context.now}')
    buy_open('HSI1811', 1)
    # logger.info(f'{context.portfolio}')
    # logger.info(f'{context.future_account}')
    # logger.info(f'{context.run_info}')
    # _open, _close, _dt = history_bars(context.HSI, context.OBSERVATION, '1m', ['open', 'close', 'datetime'],
    #                                   include_now=True)
    # ma5 = talib.MA(_close, timeperiod=5)
    # ma10 = talib.MA(_close, timeperiod=10)
    # ma30 = talib.MA(_close, timeperiod=30)
    # ma60 = talib.MA(_close, timeperiod=60)
    # pub_data(context.now, {'MA5': ma5[-1], 'MA10': ma10[-1], 'MA30': ma30[-1], 'MA60': ma60[-1]})
    # pub_data(context.now, {'account': [context.future_account.total_value, context.future_account.margin, context.future_account.daily_pnl, context.future_account.holding_pnl,
    #                                    context.future_account.realized_pnl]})
    # if not datetime.time(9, 15) <= context.now.time() <= datetime.time(16, 29):
    #     # 只做早盘
    #     return
    #
    # macdDIFF, macdDEA, macd = talib.MACDEXT(_close, fastperiod=context.SHORTPERIOD, fastmatype=1, slowperiod=context.LONGPERIOD, slowmatype=1,
    #                                      signalperiod=context.SMOOTHPERIOD, signalmatype=1)
    # std = (_close - _open)[-1]/talib.STDDEV(_close - _open, timeperiod=60)[-1]
    #
    # macd = macd * 2
    #
    #
    # p = context.portfolio.positions[context.HSI]
    # long_con1 = _close[-1] < ma60[-1]
    # long_con2 = std < -1.5
    #
    # if long_con1&long_con2:
    #     context.long_signal += 1
    #     if context.long_signal >= 4:
    #         buy_open(context.HSI, 1)
    #         context.long_signal = 0
    #         return
    #
    # close_long_con1 = macd[-1] > 0
    # close_long_con2 = _close[-1] > ma60[-1]
    #
    # if close_long_con1&close_long_con2&(p.closable_buy_quantity != 0):
    #     sell_close(context.HSI, 1)
    #     context.long_signal = 0
    #     return
    #
    # short_con1 = _close[-1] > ma60[-1]
    # short_con2 = std > 1.5
    #
    # if short_con1&short_con2:
    #     context.short_signal += 1
    #     if context.short_signal >= 4:
    #         sell_open(context.HSI, 1)
    #         context.short_signal = 0
    #         return
    #
    # close_short_con1 = macd[-1] < 0
    # close_short_con2 = _close[-1] < ma60[-1]
    #
    # if close_short_con1&close_short_con2&(p.closable_sell_quantity != 0):
    #     buy_close(context.HSI, 1)
    #     context.short_signal = 0
    #     return



def after_trading(context):
    logger.info('SP-after_trading')


__config__ = {
    'base': {
        'start_date': '2018-07-04',
        'end_date': '2018-07-29',
        'frequency': '1m',
        'matching_type': MATCHING_TYPE.NEXT_BAR_OPEN,
        'run_type': RUN_TYPE.LIVE_TRADING,
        'future_starting_cash': 500000,
        'benchmark': None,
        'accounts': {
            'future': 5000000
        }
    },
    # 'extra':{
    #     'log_level': 'verbose'
    # },
    'mod':{
        'extend_data_source_mod':{
            'enabled': True,
            'lib': 'rqalpha.examples.extend_api.HKMod',   # 数据模块
            'db_user': 'KRdata',
            'db_pwd': 'f4615f68-ff8efbf0-5874824e-e1bd1',
            'db': 'HKFuture',
            'db_host': '192.168.2.226',
            'sp_info': {'host' :'demo.spsystem1.info',
                        'port':8080,
                        'License':'59493B8B4C09F',
                        'app_id' : 'SPDEMO',
                        'user_id' :'DEMO201706051A',
                        'password' :'1234'},
            'server': {'host': 'localhost',
                       'port': 6868}
        },

        'risk_mod':{
            'enabled': True,
            'lib': 'rqalpha.examples.extend_api.RiskMod',  #  风险控制模块
        }
    }
}