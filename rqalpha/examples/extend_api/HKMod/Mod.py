#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/7/23 0023 15:53
# @Author  : Hadrianl 
# @File    : Mod.py
# @License : (C) Copyright 2013-2017, 凯瑞投资

from rqalpha.interface import AbstractMod
from .DataSource import HKDataSource
from .hkfuture_event_source import HKFutureEventSource
from rqalpha.events import EventBus, EVENT
from rqalpha.environment import Environment
from rqalpha.api import *

__config__ = {'host': 'localhost',
              'db': 'HKFuture',
              'port': 27017,
              'user': None,
              'pwd': None}


class HKDataMod(AbstractMod):
    def __init__(self):
        self._inject_api()

    def start_up(self, env, mod_config):
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


    def tear_down(self, code, exception=None):
        ...
