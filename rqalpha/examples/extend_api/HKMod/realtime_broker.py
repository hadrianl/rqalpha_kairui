#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/10/31 0031 11:32
# @Author  : Hadrianl 
# @File    : realtime_broker
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from copy import copy

from rqalpha.interface import AbstractBroker
from spapi.spAPI import *
# from .decider import CommissionDecider, SlippageDecider, TaxDecider
# from .utils import init_portfolio
from .util import _convert_from_ctype
import time


class RealtimeBroker(AbstractBroker):
    def __init__(self, env, sp_info):
        self._env = env
        self.orders = {}
        self.trades = {}
        self.positions = {}
        initialize()
        set_login_info(sp_info.host, sp_info.port, sp_info.License, sp_info.app_id, sp_info.user_id, sp_info.password)
        self._init_callback()
        login()
        time.sleep(5)


    def _init_callback(self):
        @on_login_reply  # 登录成功时候调用
        def login_reply(user_id, ret_code, ret_msg):
            if ret_code == 0:
                api_logger.info(f'@{user_id.decode()}登录成功')
            else:
                api_logger.error(f'@{user_id.decode()}登录失败--errcode:{ret_code}--errmsg:{ret_msg.decode()}')

        @on_account_info_push  # 普通客户登入后返回登入前的户口信息
        def account_info_push(acc_info):
            self.update_account(acc_info)
            api_logger.info('<账户>'+
                        f'{acc_info.ClientId.decode()}信息--NAV:{acc_info.NAV}-BaseCcy:{acc_info.BaseCcy.decode()}-BuyingPower:{acc_info.BuyingPower}-CashBal:{acc_info.CashBal}')

        @on_load_trade_ready_push  # 登入后，登入前已存的成交信息推送
        def trade_ready_push(rec_no, trade):
            self.on_trade(trade)
            # self._env.event_bus.publish_event(Event(EVENT.TRADE, trade=trade))
            api_logger.info('<成交>'+
                        f'历史成交记录--NO:{rec_no}--{trade.OpenClose.decode()}成交@{trade.ProdCode.decode()}--{trade.BuySell.decode()}--Price:{trade.AvgPrice}--Qty:{trade.Qty}')
        #
        @on_account_position_push  # 普通客户登入后返回登入前的已存在持仓信息
        def account_position_push(pos):
            self.on_position(pos)
            # self._env.event_bus.publish_event(Event(EVENT.TRADE, pos=pos))
            api_logger.info('<持仓>'+
                        f'历史持仓信息--ProdCode:{pos.ProdCode.decode()}-PLBaseCcy:{pos.PLBaseCcy}-PL:{pos.PL}-Qty:{pos.Qty}-DepQty:{pos.DepQty}',
                        pos)

        @on_order_report
        def order_report(rec_no, order):
            self.on_order(order)
            api_logger.info(f'<订单>--编号:{rec_no}-ProdCode:{order.ProdCode.decode()}-Status:{ORDER_STATUS[order.Status]}')

        self.login_reply = login_reply
        self.account_info_push = account_info_push
        self.trade_ready_push = trade_ready_push
        self.account_position_push = account_position_push
        self.order_report = order_report

    def get_portfolio(self):
        acc_info = get_acc_info()
        _acc_info = _convert_from_ctype(acc_info)
        return _acc_info

    def get_open_orders(self, order_book_id=None):
        orders = get_orders_by_array()
        if order_book_id:
            open_orders = [o for o in orders if o.ProdCode == order_book_id]
        else:
            open_orders = orders
        return open_orders

    def submit_order(self, order):
        order_dict = {}
        # add_order(order_dict)
        print(order)

    def cancel_order(self, order):
        accOrderNo = order.order_id
        productCode =order.order_book_id
        # delete_order_by(accOrderNo, productCode)
        print(order)

    def update_account(self, acc_info):
        self.account = _convert_from_ctype(acc_info)

    def on_order(self, order):
        _order = _convert_from_ctype(order)
        print(_order)
        self.orders[_order['ExtOrderNo']] = _order

    def on_trade(self, trade):
        _trade = _convert_from_ctype(trade)
        print(_trade)
        self.trades[_trade['RecNO']] = _trade

    def on_position(self, pos):
        _pos = _convert_from_ctype(pos)
        print(_pos)
        self.positions[_pos['ProdCode']] = _pos



