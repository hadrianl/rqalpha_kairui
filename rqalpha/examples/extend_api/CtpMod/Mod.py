#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/7/23 0023 15:53
# @Author  : Hadrianl 
# @File    : Mod.py
# @License : (C) Copyright 2013-2017, 凯瑞投资

from rqalpha.interface import AbstractMod
from .DataSource import CTPDataSource
from rqalpha.events import EventBus, EVENT

__config__ = {'host': '192.168.2.226',
              'db': 'Future',
              'port': 27017}


class CTPDataMod(AbstractMod):
    def __init__(self):
        ...

    def start_up(self, env, mod_config):
        env.set_data_source(CTPDataSource(mod_config.host, mod_config.db, mod_config.port))


    def tear_down(self, code, exception=None):
        ...
