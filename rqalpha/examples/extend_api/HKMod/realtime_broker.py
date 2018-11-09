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
from rqalpha.model.portfolio import Portfolio
from rqalpha.const import DEFAULT_ACCOUNT_TYPE
from rqalpha.model.base_account import BaseAccount
from .util import _convert_from_ctype
from rqalpha.environment import Environment
from rqalpha.model.base_position import Positions
from rqalpha.events import EVENT
from rqalpha.events import Event
import datetime as dt
from rqalpha.utils.i18n import gettext as _
from rqalpha.const import ORDER_STATUS, ORDER_TYPE, SIDE, POSITION_EFFECT
from rqalpha.model.order import Order
from rqalpha.model.trade import Trade
from .model import RealtimePortfolio, RealtimePosition, RealtimeAccount
import time
import six


class RealtimeBroker(AbstractBroker):
    def __init__(self, env, sp_info):
        self._env = env
        self._cache = DataCache()
        initialize()
        set_login_info(sp_info.host, sp_info.port, sp_info.License, sp_info.app_id, sp_info.user_id, sp_info.password)
        self._init_callback()
        self._env.event_bus.add_listener(EVENT.POST_SYSTEM_INIT, self._init_info_push)
        instruments = self._env.data_source.get_all_instruments()
        self._cache.cache_ins({ins.order_book_id: ins for ins in instruments})

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

        self.login_reply = login_reply
        self.account_info_push = account_info_push

        login()
        time.sleep(5)

    def _init_info_push(self, event):
        # print('init_info_push')
        @on_trade_report  # 登入后，登入前已存的成交信息推送
        def trade_ready_push(rec_no, trade):
            self.on_trade(trade)
            api_logger.info('<成交>'+
                        f'历史成交记录--NO:{rec_no}--{trade.OpenClose.decode()}成交@{trade.ProdCode.decode()}--{trade.BuySell.decode()}--Price:{trade.AvgPrice}--Qty:{trade.Qty}')
        #
        # @on_updated_account_balance_push

        @on_updated_account_position_push
        def updated_account_position_push(pos):
            self.on_position(pos)
            api_logger.info('<持仓>'+
                        f'历史持仓信息--ProdCode:{pos.ProdCode.decode()}-PLBaseCcy:{pos.PLBaseCcy}-PL:{pos.PL}-Qty:{pos.Qty}-DepQty:{pos.DepQty}')

        @on_account_position_push  # 普通客户登入后返回登入前的已存在持仓信息
        def account_position_push(pos):
            self.on_position(pos)
            api_logger.info('<持仓>'+
                        f'历史持仓信息--ProdCode:{pos.ProdCode.decode()}-PLBaseCcy:{pos.PLBaseCcy}-PL:{pos.PL}-Qty:{pos.Qty}-DepQty:{pos.DepQty}')

        @on_order_report
        def order_report(rec_no, order):
            self.on_order(order, 1)
            api_logger.info(f'<订单>--编号:{rec_no}-ProdCode:{order.ProdCode.decode()}-Status:{ORDER_STATUS[order.Status]}')

        @on_order_request_failed  # 订单请求失败时候调用
        def order_request_failed(action, order, err_code, err_msg):
            self.on_order(order, -1)
            api_logger.info(
                f'订单请求失败--ACTION:{action}-ProdCode:{order.ProdCode.decode()}-Price:{order.Price}-errcode;{err_code}-errmsg:{err_msg.decode()}')

        @on_order_before_send_report  # 订单发送前调用
        def order_before_send_report(order):
            self.on_order(order, 0)
            api_logger.info(
                f'即将发送订单请求--ProdCode:{order.ProdCode.decode()}-Price:{order.Price}-Qty:{order.Qty}-BuySell:{order.BuySell.decode()}')

        self.trade_ready_push = trade_ready_push
        self.account_position_push = account_position_push
        self.updated_account_position_push = updated_account_position_push
        self.order_report = order_report
        self.order_request_failed = order_request_failed
        self.order_before_send_report = order_before_send_report

        orders = get_orders_by_array()
        for order in orders:
            self.on_order(order)

        trades = get_all_trades_by_array()
        for trade in trades:
            self.on_trade(trade)

        pos = get_all_pos_by_array()
        for p in pos:
            self.on_position(p)

        print(self._cache.orders, self._cache.trades, self._cache.pos)


    def get_portfolio(self):
        acc_info = get_acc_info()
        _acc_info = _convert_from_ctype(acc_info)

        FuturePosition = RealtimePosition
        FutureAccount = RealtimeAccount
        self._cache.set_models(FutureAccount, FuturePosition)
        future_account = self._cache.account
        positions = self._cache.positions
        start_date = self._env.config.base.start_date
        future_starting_cash = self._env.config.base.future_starting_cash
        accounts = {
            DEFAULT_ACCOUNT_TYPE.FUTURE.name: future_account
        }
        # return Portfolio(start_date, static_value / future_starting_cash, future_starting_cash, accounts)
        return RealtimePortfolio(start_date, future_account.total_value / future_starting_cash,  future_starting_cash, accounts)

    def get_ins_dict(self, order_book_id=None):
        if order_book_id is not None:
            return self._cache.ins.get(order_book_id)
        else:
            return self._cache.ins

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
        prod_code = self.get_ins_dict(order['order_book_id']).underlying_order_book_id
        bs = 'B' if order['side'] == SIDE.BUY or str.upper(order['side']) == 'B'else 'S'
        if order['style'] == ORDER_TYPE.MARKET:
            add_normal_order(prod_code, bs, order['quantity'])
        elif order['style'] == ORDER_TYPE.LIMIT:
            add_normal_order(prod_code, bs, order['quantity'], order['price'])

    def cancel_order(self, order):
        accOrderNo = order.order_id
        productCode =order.order_book_id
        # delete_order_by(accOrderNo, productCode)
        print(order)

    def update_account(self, acc_info):
        self._cache.cache_account(acc_info)

    def on_order(self, order, p):
        self._cache.cache_order(order)
        # order = self._cache.get_cached_order(_order)

        # account = Environment.get_instance().get_account(order.order_book_id)
        # account, _ = self._cache.account
        #
        # if p == 1:
        #     if order.status == ORDER_STATUS.PENDING_NEW:
        #         self._env.event_bus.publish_event(Event(EVENT.ORDER_PENDING_NEW, account=account, order=order))
        #
        #     elif order.status == 2:
        #         self._env.event_bus.publish_event(Event(EVENT.ORDER_CREATION_PASS, account=account, order=order))
        #
        #     elif order.status ==  ORDER_STATUS.ACTIVE:
        #         order.active()
        #
        #     # elif order.status == ORDER_STATUS.FILLED:
        #     #     order.fill()
        #
        #     elif order.status == ORDER_STATUS.CANCELLED:
        #         order.mark_cancelled("%d order has been cancelled." % order.order_id)
        #         self._env.event_bus.publish_event(Event(EVENT.ORDER_CANCELLATION_PASS, account=account, order=order))
        #         self._cache.remove_open_order(order)
        # elif p == -1:
        #     self._env.publish_event(Event(EVENT.ORDER_CREATION_REJECT, account=account, order=order))
        #     self._cache.remove_open_order(order)
        # elif p == 0:
        #     self._env.event_bus.publish_event(Event(EVENT.ORDER_PENDING_NEW, account=account, order=order))


    def on_trade(self, trade):
        self._cache.cache_trade(trade)

        # # account = Environment.get_instance().get_account(_trade['ProdCode'])
        # account, _ = self._cache.account
        #
        # if _trade['RecNO'] in account._backward_trade_set:
        #     return
        #
        # order = self._cache.get_cached_order(_trade)
        # # commission = cal_commission(trade_dict, order.position_effect)
        # trade = Trade.__from_create__(
        #     _trade['ExtOrderNo'], _trade['AvgPrice'], _trade['Qty'],
        #     SIDE.BUY if _trade['BuySell'] == 'B' else SIDE.SELL, _trade['OpenClose'], _trade['ProdCode'], trade_id=_trade['RecNO'],
        #      frozen_price=_trade['OrderPrice'])
        # trade._calendar_dt = dt.datetime.fromtimestamp(_trade['TradeDate'])
        # trade._trading_dt = dt.datetime.fromtimestamp(_trade['TradeTime'])
        #
        # order.fill(trade)
        # self._cache.cache_trade(_trade)
        # self._env.event_bus.publish_event(Event(EVENT.TRADE, account=account,trade=trade))


    def on_position(self, pos):
        _pos = _convert_from_ctype(pos)
        account = self._cache.account
        print('on_position')
        self._env.event_bus.publish_event(Event('position', account=account, pos=_pos))
        self._cache.cache_position(pos)


class DataCache(object):
    def __init__(self):
        self.ins = {}
        self.future_info = {}

        self.orders = {}
        self.open_orders = {}
        self.trades = {}

        self.pos = {}
        self.snapshot = {}

        self._account_dict = None
        self._qry_order_cache = {}
        self._account_model = None
        self._position_model = None

    def cache_ins(self, ins_cache):
        self.ins = ins_cache
        # self.future_info = {ins_dict.underlying_symbol: {'speculation': {
        #         'long_margin_ratio': ins_dict.long_margin_ratio,
        #         'short_margin_ratio': ins_dict.short_margin_ratio,
        #         'margin_type': ins_dict.margin_type,
        #     }} for ins_dict in self.ins.values()}

    def cache_commission(self, underlying_symbol, commission_dict):
        self.future_info[underlying_symbol]['speculation'].update({
            'open_commission_ratio': commission_dict.open_ratio,
            'close_commission_ratio': commission_dict.close_ratio,
            'close_commission_today_ratio': commission_dict.close_today_ratio,
            'commission_type': commission_dict.commission_type,
        })

    def cache_open_order(self, order):
        self.open_orders[order['ExtOrderNo']] = order

    def remove_open_order(self, order):
        self.open_orders.pop(order['ExtOrderNo'])

    def cache_position(self, pos):
        _pos = _convert_from_ctype(pos)
        self.pos[_pos['ProdCode']] = _pos

    def cache_account(self, account):
        _account = _convert_from_ctype(account)
        self._account_dict = _account

    def cache_qry_order(self, order_cache):
        self._qry_order_cache = order_cache

    def cache_trade(self, trade):
        _trade = _convert_from_ctype(trade)
        td = self.trades.setdefault(_trade['ProdCode'], [])
        td.append(_trade)

    def get_cached_order(self, obj):
        try:
            order = self.orders[obj['ExtOrderNo']]
        except KeyError:
            # if obj['OrderType'] == 6:
            #     style = ORDER_TYPE.MARKET
            # elif obj['OrderType'] == 0:
            #     style = ORDER_TYPE.LIMIT
            # order = Order.__from_create__(obj['ProdCode'], obj['Qty'], SIDE.BUY if obj['BuySell'] == 'B' else SIDE.SELL, style, obj['OpenClose'])
            self.cache_order(obj)
            order = self.orders[obj['ExtOrderNo']]
        return order

    def cache_order(self, order):
        _order = _convert_from_ctype(order)
        self.orders[_order['ExtOrderNo']] = _order

    @property
    def positions(self):
        PositionModel = self._position_model
        ps = Positions(PositionModel)
        for order_book_id, pos_dict in self.pos.items():
            position = RealtimePosition(order_book_id)
            position.set_state(pos_dict)
            ps[order_book_id] = position
        return ps

    def process_today_holding_list(self, today_quantity, holding_list):
        # check if list is empty
        if not holding_list:
            return
        cum_quantity = sum(quantity for price, quantity in holding_list)
        left_quantity = cum_quantity - today_quantity
        while left_quantity > 0:
            oldest_price, oldest_quantity = holding_list.pop()
            if oldest_quantity > left_quantity:
                consumed_quantity = left_quantity
                holding_list.append((oldest_price, oldest_quantity - left_quantity))
            else:
                consumed_quantity = oldest_quantity
            left_quantity -= consumed_quantity

    @property
    def account(self):
        static_value = self._account_dict['NAV']
        ps = self.positions

        AccountModel = self._account_model
        account = AccountModel(static_value, self._account_dict, ps)

        return account

    def set_models(self, account_model, position_model):
        self._account_model = account_model
        self._position_model = position_model


def add_normal_order(ProdCode, BuySell, Qty, Price=None, AO=False, OrderOption=0, ClOrderId='', ):
    CondType = 0
    price_map = {0: Price, 2: 0x7fffffff, 6: 0}
    if Price:
        assert isinstance(Price, (int, float))
        OrderType = 0
        Price = price_map[OrderType]
    elif AO:
        OrderType = 2
        Price = price_map[OrderType]
    else:
        OrderType = 6
        Price = price_map[OrderType]
    kwargs={'ProdCode': ProdCode,
            'BuySell': BuySell,
            'Qty': Qty,
            'Price': Price,
            'CondType': CondType,
            'OrderType': OrderType,
            'OrderOption': OrderOption,
            'ClOrderId': ClOrderId,
            'DecInPrice': 0}
    print(kwargs)
    add_order(**kwargs)

ORDER_TYPE_MAP = {0: ORDER_STATUS.PENDING_NEW,
                  1: ORDER_STATUS.ACTIVE,
                  2: 2,
                  3: 3,
                  4: ORDER_STATUS.PENDING_NEW,
                  5: 5,
                  6: ORDER_STATUS.PENDING_CANCEL,
                  7: 7,
                  8: ORDER_STATUS.ACTIVE,
                  9: ORDER_STATUS.FILLED,
                  10: ORDER_STATUS.CANCELLED,
                  28: ORDER_STATUS.CANCELLED
                  }
