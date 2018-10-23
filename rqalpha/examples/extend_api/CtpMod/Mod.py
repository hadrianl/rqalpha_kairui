#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/7/23 0023 15:53
# @Author  : Hadrianl 
# @File    : Mod.py
# @License : (C) Copyright 2013-2017, 凯瑞投资

from rqalpha.interface import AbstractMod
from .DataSource import CTPDataSource
from .ctp_event_source import CtpEventSource
from rqalpha.events import EventBus, EVENT
from .TdxData import Future
from rqalpha.environment import Environment

__config__ = {'host': '192.168.2.226',
              'db': 'Future',
              'port': 27017,
              'user': None,
              'pwd': None}


class CTPDataMod(AbstractMod):
    def __init__(self):
        self._inject_extend_api()

    def start_up(self, env, mod_config):
        self._config = mod_config
        self._env = env
        env.set_event_source(CtpEventSource(env))
        env.set_data_source(CTPDataSource(mod_config.host, mod_config.db, mod_config.port, mod_config.user, mod_config.pwd))

    def _inject_extend_api(self):
        from rqalpha import export_as_api
        from rqalpha.execution_context import ExecutionContext
        from rqalpha.const import EXECUTION_PHASE
        mod_config = Environment.get_instance().config.mod.extend_data_source_mod
        self._data_fetcher = Future(mod_config.host, mod_config.port, mod_config.db)
        @export_as_api
        @ExecutionContext.enforce_phase(
                                EXECUTION_PHASE.ON_INIT,
                                EXECUTION_PHASE.BEFORE_TRADING,
                                EXECUTION_PHASE.ON_BAR,
                                EXECUTION_PHASE.AFTER_TRADING,
                                EXECUTION_PHASE.SCHEDULED)
        def get_bar(code, fields=None, start=None, end=None, ktype='1m'):
            return self._data_fetcher.get_bar(code, fields, start, end, ktype)

    def tear_down(self, code, exception=None):
        ...
