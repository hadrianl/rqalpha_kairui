#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/7/23 0023 15:53
# @Author  : Hadrianl 
# @File    : Mod.py
# @License : (C) Copyright 2013-2017, 凯瑞投资

from rqalpha.interface import AbstractMod

from rqalpha.events import EventBus, EVENT
from rqalpha.environment import Environment
from rqalpha.const import ORDER_TYPE, SIDE
from rqalpha.api import *

__config__ = {'host': 'localhost',
              'db': 'HKFuture',
              'port': 27017,
              'user': None,
              'pwd': None}


class HKDataMod(AbstractMod):
    def __init__(self):
        env = Environment.get_instance()
        if env.config.base.run_type in (RUN_TYPE.PAPER_TRADING, RUN_TYPE.LIVE_TRADING):
            self._inject_realtime_api()
        else:
            self._inject_api()


    def start_up(self, env, mod_config):
        if env.config.base.run_type in (RUN_TYPE.PAPER_TRADING, RUN_TYPE.LIVE_TRADING):
            from .realtime_event_source import RealtimeEventSource
            from .realtime_data_source import RealtimeDataSource
            from .realtime_broker import RealtimeBroker
            env.set_event_source(RealtimeEventSource(mod_config))
            env.set_data_source(RealtimeDataSource(mod_config.db_info, mod_config.server_info))
            env.data_source.bar_trigger_thread.start()
            env.set_broker(RealtimeBroker(env, mod_config.sp_info))
        else:
            from .DataSource import HKDataSource
            from .hkfuture_event_source import HKFutureEventSource
            env.set_event_source(HKFutureEventSource(env))
            env.set_data_source(HKDataSource(mod_config.host, mod_config.db, mod_config.port, mod_config.user, mod_config.pwd))


    def _inject_api(self):
        from rqalpha import export_as_api
        from rqalpha.execution_context import ExecutionContext
        from rqalpha.const import EXECUTION_PHASE

        @export_as_api
        @ExecutionContext.enforce_phase(EXECUTION_PHASE.ON_INIT,
                                        EXECUTION_PHASE.BEFORE_TRADING,
                                        EXECUTION_PHASE.ON_BAR,
                                        EXECUTION_PHASE.AFTER_TRADING,
                                        EXECUTION_PHASE.SCHEDULED)
        def get_main_contract(underlying):  # 更新主力合约
            contracts = get_future_contracts(underlying)
            env = Environment.get_instance()
            date_left = get_trading_dates(env.trading_dt, instruments(contracts[0]).maturity_date)

            if len(date_left) <= 1:
                CurrentMon_Contract = contracts[1]
            else:
                CurrentMon_Contract = contracts[0]

            return CurrentMon_Contract

        @export_as_api
        @ExecutionContext.enforce_phase(EXECUTION_PHASE.BEFORE_TRADING)
        def get_trading_minutes(date):
            env = Environment.get_instance()
            trading_minutes = env.event_source._get_trading_minutes(date)
            return trading_minutes

    def _inject_realtime_api(self):
        from rqalpha import export_as_api
        from rqalpha.execution_context import ExecutionContext
        from rqalpha.const import EXECUTION_PHASE

        @export_as_api
        @ExecutionContext.enforce_phase(EXECUTION_PHASE.ON_BAR,
                                        EXECUTION_PHASE.ON_TICK,
                                        EXECUTION_PHASE.SCHEDULED,
                                        EXECUTION_PHASE.GLOBAL)
        def realtime_order(id_or_ins, quantity, side, price=0, style=ORDER_TYPE.MARKET):
            order = {'order_book_id': id_or_ins, 'quantity': quantity, 'side': side, 'price': price, 'style': style}
            env = Environment.get_instance()
            env.broker.submit_order(order)

        @export_as_api
        @ExecutionContext.enforce_phase(EXECUTION_PHASE.ON_BAR,
                                        EXECUTION_PHASE.ON_TICK,
                                        EXECUTION_PHASE.SCHEDULED,
                                        EXECUTION_PHASE.GLOBAL)
        def realtime_buy(id_or_ins, quantity, price=0, style=ORDER_TYPE.MARKET):
            realtime_order(id_or_ins, quantity, SIDE.BUY, price, style)

        @export_as_api
        @ExecutionContext.enforce_phase(EXECUTION_PHASE.ON_BAR,
                                        EXECUTION_PHASE.ON_TICK,
                                        EXECUTION_PHASE.SCHEDULED,
                                        EXECUTION_PHASE.GLOBAL)
        def realtime_sell(id_or_ins, quantity, price=0, style=ORDER_TYPE.MARKET):
            realtime_order(id_or_ins, quantity, SIDE.SELL, price, style)


    def tear_down(self, code, exception=None):
        ...
