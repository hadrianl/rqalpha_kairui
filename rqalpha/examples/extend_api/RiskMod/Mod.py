#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/7/27 0027 11:40
# @Author  : Hadrianl 
# @File    : Mod.py
# @License : (C) Copyright 2013-2017, 凯瑞投资

from rqalpha.interface import AbstractMod
from rqalpha.events import EventBus, EVENT
from rqalpha.api import cancel_order

__config__ = {}


class RiskManagementMod(AbstractMod):
    def __init__(self):
        ...

    def start_up(self, env, mod_config):
        env.event_bus.add_listener(EVENT.ORDER_PENDING_NEW, self._order_verify)

    def tear_down(self, code, exception=None):
        ...

    def _order_verify(self, event):
        account = event.account
        order = event.order

        if not self._order_condition(account, order):
            cancel_order(order)

    def _order_condition(self, account, order):  # 下单前做验证
        return True