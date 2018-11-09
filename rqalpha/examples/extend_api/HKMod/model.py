#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/11/6 0006 12:28
# @Author  : Hadrianl 
# @File    : model
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

import six
import jsonpickle

from rqalpha.environment import Environment
from rqalpha.const import DAYS_CNT, DEFAULT_ACCOUNT_TYPE
from rqalpha.utils import get_account_type, merge_dicts
from rqalpha.utils.repr import property_repr
from rqalpha.events import EVENT, Event
from rqalpha.interface import AbstractPosition, AbstractAccount



class RealtimePortfolio(object):
    __repr__ = property_repr

    def __init__(self, start_date, static_unit_net_value, units, accounts, register_event=True):
        self._start_date = start_date
        self._static_unit_net_value = static_unit_net_value
        self._units = units
        self._accounts = accounts
        if register_event:
            self.register_event()

    def register_event(self):
        """
        注册事件
        """
        event_bus = Environment.get_instance().event_bus
        event_bus.prepend_listener(EVENT.PRE_BEFORE_TRADING, self._pre_before_trading)

    def _pre_before_trading(self, event):
        self._static_unit_net_value = self.unit_net_value

    @property
    def accounts(self):
        """
        [dict] 账户字典
        """
        return self._accounts

    @property
    def positions(self):
        """
        [dict] 持仓
        """
        return self._accounts['FUTURE']._positions

    @property
    def units(self):
        return self._units

    @property
    def unit_net_value(self):
        """
        [float] 实时净值
        """
        return self.total_value / self._units

    @property
    def static_unit_net_value(self):
        return self._static_unit_net_value

    @property
    def total_value(self):
        """
        [float]总权益
        """
        return sum(acc.total_value for _, acc in self._accounts.items())

    @property
    def daily_returns(self):
        """
        [float] 当前最新一天的日收益
        """
        return 0 if self._static_unit_net_value == 0 else self.unit_net_value / self._static_unit_net_value - 1

    @property
    def cash(self):
        return sum(acc.cash for _, acc in self._accounts.items())

    @property
    def market_value(self):
        return sum(acc.market_value for _, acc in self._accounts.items())

class RealtimeAccount(AbstractAccount):
    def __init__(self, total, account_dict, positions, backward_trade_set=set(), register_event=True):
        self._account_dict = account_dict
        self._positions = positions
        self._total_cash = total
        self._backward_trade_set = backward_trade_set
        if register_event:
            self.register_event()


    def register_event(self):
        event_bus = Environment.get_instance().event_bus
        event_bus.add_listener(EVENT.SETTLEMENT, self._settlement)
        event_bus.add_listener(EVENT.ORDER_PENDING_NEW, self._on_order_pending_new)
        event_bus.add_listener(EVENT.ORDER_CREATION_REJECT, self._on_order_creation_reject)
        event_bus.add_listener(EVENT.ORDER_CANCELLATION_PASS, self._on_order_unsolicited_update)
        event_bus.add_listener(EVENT.ORDER_UNSOLICITED_UPDATE, self._on_order_unsolicited_update)
        event_bus.add_listener(EVENT.TRADE, self._on_trade)
        # if self.AGGRESSIVE_UPDATE_LAST_PRICE:
        #     event_bus.add_listener(EVENT.BAR, self._on_bar)
        #     event_bus.add_listener(EVENT.TICK, self._on_tick)

    def fast_forward(self, orders, trades=list()):
        # 计算 Positions
        for trade in trades:
            if trade.exec_id in self._backward_trade_set:
                continue
            self._apply_trade(trade)
        # 计算 Frozen Cash
        self._frozen_cash = sum(self._frozen_cash_of_order(order) for order in orders if order.is_active())

    def order(self, order_book_id, quantity, style, target=False):
        position = self.positions[order_book_id]
        if target:
            # For order_to
            quantity = quantity - position.buy_quantity + position.sell_quantity
        orders = []
        if quantity > 0:
            # 平昨仓
            if position.sell_old_quantity > 0:
                soq = position.sell_old_quantity
                orders.append(order(
                    order_book_id,
                    min(quantity, position.sell_old_quantity),
                    SIDE.BUY,
                    POSITION_EFFECT.CLOSE,
                    style
                ))
                quantity -= soq
            if quantity <= 0:
                return orders
            # 平今仓
            if position.sell_today_quantity > 0:
                stq = position.sell_today_quantity
                orders.append(order(
                    order_book_id,
                    min(quantity, position.sell_today_quantity),
                    SIDE.BUY,
                    POSITION_EFFECT.CLOSE_TODAY,
                    style
                ))
                quantity -= stq
            if quantity <= 0:
                return orders
            # 开多仓
            orders.append(order(
                order_book_id,
                quantity,
                SIDE.BUY,
                POSITION_EFFECT.OPEN,
                style
            ))
            return orders
        else:
            # 平昨仓
            quantity *= -1
            if position.buy_old_quantity > 0:
                boq = position.buy_old_quantity
                orders.append(order(
                    order_book_id,
                    min(quantity, position.buy_old_quantity),
                    SIDE.SELL,
                    POSITION_EFFECT.CLOSE,
                    style
                ))
                quantity -= boq
            if quantity <= 0:
                return orders
            # 平今仓
            if position.buy_today_quantity > 0:
                btq = position.buy_today_quantity
                orders.append(order(
                    order_book_id,
                    min(quantity, position.buy_today_quantity),
                    SIDE.SELL,
                    POSITION_EFFECT.CLOSE_TODAY,
                    style
                ))
                quantity -= btq
            if quantity <= 0:
                return orders
            # 开空仓
            orders.append(order(
                order_book_id,
                quantity,
                SIDE.SELL,
                POSITION_EFFECT.OPEN,
                style
            ))
            return orders

    def get_state(self):
        return {
            'positions': {
                order_book_id: position.get_state()
                for order_book_id, position in six.iteritems(self._positions)
            },
            'frozen_cash': self._frozen_cash,
            'total_cash': self._total_cash,
            'backward_trade_set': list(self._backward_trade_set),
            'transaction_cost': self._transaction_cost,
        }

    def set_state(self, state):
        self._frozen_cash = state['frozen_cash']
        self._backward_trade_set = set(state['backward_trade_set'])
        self._transaction_cost = state['transaction_cost']

        margin_changed = 0
        self._positions.clear()
        for order_book_id, v in six.iteritems(state['positions']):
            position = self._positions.get_or_create(order_book_id)
            position.set_state(v)
            if 'margin_rate' in v and abs(v['margin_rate'] - position.margin_rate) > 1e-6:
                margin_changed += position.margin * (v['margin_rate'] - position.margin_rate) / position.margin_rate

        self._total_cash = state['total_cash'] + margin_changed


    @property
    def type(self):
        return DEFAULT_ACCOUNT_TYPE.FUTURE.name

    @staticmethod
    def _frozen_cash_of_order(order):
        if order.position_effect == POSITION_EFFECT.OPEN:
            return margin_of(order.order_book_id, order.unfilled_quantity, order.frozen_price)
        else:
            return 0

    @staticmethod
    def _frozen_cash_of_trade(trade):
        if trade.position_effect == POSITION_EFFECT.OPEN:
            return margin_of(trade.order_book_id, trade.last_quantity, trade.frozen_price)
        else:
            return 0

    @property
    def total_value(self):
        return self._account_dict['NAV']


    # -- Margin 相关
    @property
    def margin(self):
        """
        [float] 总保证金
        """
        return sum(position.margin for position in six.itervalues(self._positions))

    @property
    def buy_margin(self):
        """
        [float] 买方向保证金
        """
        return sum(position.buy_margin for position in six.itervalues(self._positions))

    @property
    def sell_margin(self):
        """
        [float] 卖方向保证金
        """
        return sum(position.sell_margin for position in six.itervalues(self._positions))

    # -- PNL 相关
    @property
    def daily_pnl(self):
        """
        [float] 当日盈亏
        """
        return self.realized_pnl + self.holding_pnl - self.transaction_cost

    @property
    def holding_pnl(self):
        """
        [float] 浮动盈亏
        """
        return sum(position.holding_pnl for position in six.itervalues(self._positions))

    @property
    def realized_pnl(self):
        """
        [float] 平仓盈亏
        """
        return sum(position.realized_pnl for position in six.itervalues(self._positions))

    def _settlement(self, event):
        total_value = self.total_value

        for position in list(self._positions.values()):
            order_book_id = position.order_book_id
            if position.is_de_listed() and position.buy_quantity + position.sell_quantity != 0:
                user_system_log.warn(
                    _(u"{order_book_id} is expired, close all positions by system").format(order_book_id=order_book_id))
                del self._positions[order_book_id]
            elif position.buy_quantity == 0 and position.sell_quantity == 0:
                del self._positions[order_book_id]
            else:
                position.apply_settlement()
        self._total_cash = total_value - self.margin - self.holding_pnl
        self._transaction_cost = 0  # todo:修改settlement

        # 如果 total_value <= 0 则认为已爆仓，清空仓位，资金归0
        if total_value <= 0:
            self._positions.clear()
            self._total_cash = 0

        self._backward_trade_set.clear()

    def _on_bar(self, event):
        for position in self._positions.values():
            position.update_last_price()

    def _on_tick(self, event):
        for position in self._positions.values():
            position.update_last_price()

    def _on_order_pending_new(self, event):
        if self != event.account:
            return
        self._frozen_cash += self._frozen_cash_of_order(event.order)

    def _on_order_creation_reject(self, event):
        if self != event.account:
            return
        self._frozen_cash -= self._frozen_cash_of_order(event.order)

    def _on_order_unsolicited_update(self, event):
        if self != event.account:
            return
        self._frozen_cash -= self._frozen_cash_of_order(event.order)

    def _on_trade(self, event):
        if self != event.account:
            return
        self._apply_trade(event.trade)

    def _apply_trade(self, trade):
        if trade.exec_id in self._backward_trade_set:
            return
        order_book_id = trade.order_book_id
        position = self._positions.get_or_create(order_book_id)
        delta_cash = position.apply_trade(trade)

        self._transaction_cost += trade.transaction_cost
        self._total_cash -= trade.transaction_cost
        self._total_cash += delta_cash
        self._frozen_cash -= self._frozen_cash_of_trade(trade)
        self._backward_trade_set.add(trade.exec_id)

    @property
    def frozen_cash(self):
        """
        [Required]

        返回当前账户的冻结资金
        """
        return self._account_dict['LockupAmt']

    @property
    def market_value(self):
        """
        [Required]

        返回当前账户的市值
        """
        return self._account_dict['NAV']

    @property
    def transaction_cost(self):
        """
        [Required]

        返回当前账户的当日交易费用
        """
        return self._account_dict['TotalFee']

    @property
    def positions(self):
        """
        [Required]

        返回当前账户的持仓数据

        :return: Positions(PositionModel)
        """
        return self._positions

    @property
    def cash(self):
        """
        [Required]

        返回当前账户的可用资金
        """
        return self._account_dict['CashBal']




class RealtimePosition(AbstractPosition):
    def __init__(self, order_book_id):
        self._order_book_id = order_book_id
        self._Qty = 0
        self._DepQty = 0
        self._LongQty = 0
        self._ShortQty = 0
        self._TotalAmt = 0.
        self._DepTotalAmt = 0.
        self._LongTotalAmt = 0.
        self._ShortTotalAmt = 0.

        self._PLBaseCcy = 0.
        self._LongShort = None



    def __repr__(self):
        return 'FuturePosition({})'.format(self.__dict__)

    def get_state(self):
        return {
            'order_book_id': self._order_book_id,
            'Qty': self._Qty,
            'DepQty': self._DepQty,
            'LongQty': self._LongQty,
            'ShortQty': self._ShortQty,
            'TotalAmt': self._TotalAmt,
            'DepTotalAmt': self._DepTotalAmt,
            'LongTotalAmt': self._LongTotalAmt,
            'ShortTotalAmt': self._ShortTotalAmt,
            'PLBaseCcy': self._PLBaseCcy,
            'LongShort': self._LongShort,
            # margin rate may change
            'margin_rate': self.margin_rate,
        }

    def set_state(self, state):
        assert self._order_book_id == state['ProdCode']
        self._order_book_id == state['Qty']
        self._Qty = state['DepQty']
        self._LongQty = state['LongQty']
        self._ShortQty = state['ShortQty']
        self._TotalAmt = state['TotalAmt']
        self._DepTotalAmt = state['DepTotalAmt']
        self._LongTotalAmt = state['LongTotalAmt']
        self._ShortTotalAmt = state['ShortTotalAmt']
        self._PLBaseCcy = state['PLBaseCcy']
        self._LongShort = state['LongShort']

    @property
    def type(self):
        return DEFAULT_ACCOUNT_TYPE.FUTURE.name

    @property
    def order_book_id(self):
        return self._order_book_id

    @property
    def transaction_cost(self):
        return (self._LongQty + self._ShortQty) * 33.54

    @property
    def margin_rate(self):
        env = Environment.get_instance()
        margin_info = env.data_proxy.get_margin_info(self.order_book_id)
        margin_multiplier = env.config.base.margin_multiplier
        return margin_info['long_margin_ratio'] * margin_multiplier

    @property
    def market_value(self):
        return (self._LongTotalAmt - self._ShortTotalAmt) * self.contract_multiplier

    @property
    def buy_market_value(self):
        return self._LongTotalAmt * self.contract_multiplier

    @property
    def sell_market_value(self):
        return self._ShortTotalAmt * self.contract_multiplier

    # -- PNL 相关
    @property
    def contract_multiplier(self):
        return Environment.get_instance().get_instrument(self.order_book_id).contract_multiplier

    @property
    def open_orders(self):
        return Environment.get_instance().broker.get_open_orders(self.order_book_id)

    @property
    def holding_pnl(self):
        """
        [float] 当日持仓盈亏
        """
        return self.buy_holding_pnl + self.sell_holding_pnl

    @property
    def realized_pnl(self):
        """
        [float] 当日平仓盈亏
        """
        return self.buy_realized_pnl + self.sell_realized_pnl

    @property
    def daily_pnl(self):
        """
        [float] 当日盈亏
        """
        return self._PLBaseCcy

    @property
    def pnl(self):
        """
        [float] 累计盈亏
        """
        return self.buy_pnl + self.sell_pnl

    # -- Quantity 相关

    @property
    def buy_today_quantity(self):
        """
        [int] 买方向今仓
        """
        return self._LongQty

    @property
    def sell_today_quantity(self):
        """
        [int] 卖方向今仓
        """
        return self._ShortQty

    @property
    def today_quantity(self):

        return self._LongQty - self._ShortQty

    # -- Margin 相关
    @property
    def buy_margin(self):
        """
        [float] 买方向持仓保证金
        """
        return self._LongTotalAmt * self.margin_rate

    @property
    def sell_margin(self):
        """
        [float] 卖方向持仓保证金
        """
        return self._ShortTotalAmt * self.margin_rate

    @property
    def margin(self):
        """
        [float] 保证金
        """
        # TODO: 需要添加单向大边相关的处理逻辑
        return self.buy_margin + self.sell_margin

    @property
    def buy_avg_open_price(self):
        return self._LongTotalAmt / self._LongQty

    @property
    def sell_avg_open_price(self):
        return self._ShortTotalAmt / self._ShortQty

    # -- Function

    def apply_settlement(self):
        env = Environment.get_instance()
        data_proxy = env.data_proxy
        trading_date = env.trading_dt.date()
        settle_price = data_proxy.get_settle_price(self.order_book_id, trading_date)
        self._buy_old_holding_list = [(settle_price, self.buy_quantity)]
        self._sell_old_holding_list = [(settle_price, self.sell_quantity)]
        self._buy_today_holding_list = []
        self._sell_today_holding_list = []

        self._buy_transaction_cost = 0.
        self._sell_transaction_cost = 0.
        self._buy_realized_pnl = 0.
        self._sell_realized_pnl = 0.

    def _margin_of(self, quantity, price):
        env = Environment.get_instance()
        instrument = env.data_proxy.instruments(self.order_book_id)
        return quantity * instrument.contract_multiplier * price * self.margin_rate

    def apply_trade(self, trade):
        trade_quantity = trade.last_quantity
        if trade.side == SIDE.BUY:
            if trade.position_effect == POSITION_EFFECT.OPEN:
                self._buy_avg_open_price = (self._buy_avg_open_price * self.buy_quantity +
                                            trade_quantity * trade.last_price) / (self.buy_quantity + trade_quantity)
                self._buy_transaction_cost += trade.transaction_cost
                self._buy_today_holding_list.insert(0, (trade.last_price, trade_quantity))
                return -1 * self._margin_of(trade_quantity, trade.last_price)
            else:
                old_margin = self.margin
                self._sell_transaction_cost += trade.transaction_cost
                delta_realized_pnl = self._close_holding(trade)
                self._sell_realized_pnl += delta_realized_pnl
                return old_margin - self.margin + delta_realized_pnl
        else:
            if trade.position_effect == POSITION_EFFECT.OPEN:
                self._sell_avg_open_price = (self._sell_avg_open_price * self.sell_quantity +
                                             trade_quantity * trade.last_price) / (self.sell_quantity + trade_quantity)
                self._sell_transaction_cost += trade.transaction_cost
                self._sell_today_holding_list.insert(0, (trade.last_price, trade_quantity))
                return -1 * self._margin_of(trade_quantity, trade.last_price)
            else:
                old_margin = self.margin
                self._buy_transaction_cost += trade.transaction_cost
                delta_realized_pnl = self._close_holding(trade)
                self._buy_realized_pnl += delta_realized_pnl
                return old_margin - self.margin + delta_realized_pnl

    def _close_holding(self, trade):
        left_quantity = trade.last_quantity
        delta = 0
        if trade.side == SIDE.BUY:
            # 先平昨仓
            if len(self._sell_old_holding_list) != 0:
                old_price, old_quantity = self._sell_old_holding_list.pop()

                if old_quantity > left_quantity:
                    consumed_quantity = left_quantity
                    self._sell_old_holding_list = [(old_price, old_quantity - left_quantity)]
                else:
                    consumed_quantity = old_quantity
                left_quantity -= consumed_quantity
                delta += self._cal_realized_pnl(old_price, trade.last_price, trade.side, consumed_quantity)
            # 再平进仓
            while True:
                if left_quantity <= 0:
                    break
                oldest_price, oldest_quantity = self._sell_today_holding_list.pop()
                if oldest_quantity > left_quantity:
                    consumed_quantity = left_quantity
                    self._sell_today_holding_list.append((oldest_price, oldest_quantity - left_quantity))
                else:
                    consumed_quantity = oldest_quantity
                left_quantity -= consumed_quantity
                delta += self._cal_realized_pnl(oldest_price, trade.last_price, trade.side, consumed_quantity)
        else:
            # 先平昨仓
            if len(self._buy_old_holding_list) != 0:
                old_price, old_quantity = self._buy_old_holding_list.pop()
                if old_quantity > left_quantity:
                    consumed_quantity = left_quantity
                    self._buy_old_holding_list = [(old_price, old_quantity - left_quantity)]
                else:
                    consumed_quantity = old_quantity
                left_quantity -= consumed_quantity
                delta += self._cal_realized_pnl(old_price, trade.last_price, trade.side, consumed_quantity)
            # 再平今仓
            while True:
                if left_quantity <= 0:
                    break
                oldest_price, oldest_quantity = self._buy_today_holding_list.pop()
                if oldest_quantity > left_quantity:
                    consumed_quantity = left_quantity
                    self._buy_today_holding_list.append((oldest_price, oldest_quantity - left_quantity))
                    left_quantity = 0
                else:
                    consumed_quantity = oldest_quantity
                left_quantity -= consumed_quantity
                delta += self._cal_realized_pnl(oldest_price, trade.last_price, trade.side, consumed_quantity)
        return delta

    def _cal_realized_pnl(self, cost_price, trade_price, side, consumed_quantity):
        if side == SIDE.BUY:
            return (cost_price - trade_price) * consumed_quantity * self.contract_multiplier
        else:
            return (trade_price - cost_price) * consumed_quantity * self.contract_multiplier
