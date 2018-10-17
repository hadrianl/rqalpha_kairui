#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/10/17 0017 10:26
# @Author  : Hadrianl 
# @File    : ctp_event_source
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


# -*- coding: utf-8 -*-
#
# Copyright 2017 Ricequant, Inc
#
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

import datetime

from rqalpha.interface import AbstractEventSource
from rqalpha.events import Event, EVENT
from rqalpha.utils import get_account_type
from rqalpha.utils.exception import CustomException, CustomError, patch_user_exc
from rqalpha.utils.datetime_func import convert_int_to_datetime
from rqalpha.const import DEFAULT_ACCOUNT_TYPE
from rqalpha.utils.i18n import gettext as _


ONE_MINUTE = datetime.timedelta(minutes=1)


class CtpEventSource(AbstractEventSource):
    def __init__(self, env):
        self._env = env
        self._config = env.config
        self._universe_changed = False
        self._env.event_bus.add_listener(EVENT.POST_UNIVERSE_CHANGED, self._on_universe_changed)

    def _on_universe_changed(self, event):
        self._universe_changed = True

    def _get_universe(self):
        universe = self._env.get_universe()
        if len(universe) == 0 and DEFAULT_ACCOUNT_TYPE.STOCK.name not in self._config.base.accounts:
            raise patch_user_exc(RuntimeError(_("Current universe is empty. Please use subscribe function before trade")), force=True)
        return universe

    def _get_future_trading_minutes(self, trading_date):
        trading_minutes = set()
        universe = self._get_universe()
        for order_book_id in universe:
            if get_account_type(order_book_id) == DEFAULT_ACCOUNT_TYPE.STOCK.name:
                continue
            trading_minutes.update(self._env.data_proxy.get_trading_minutes_for(order_book_id, trading_date))
        return set([minute for minute in trading_minutes])

    def _get_trading_minutes(self, trading_date):
        import datetime as dt
        trading_minutes = set()
        _m = []
        _n = []
        for account_type in self._config.base.accounts:
            if account_type == DEFAULT_ACCOUNT_TYPE.FUTURE.name:
                trading_minutes = trading_minutes.union(self._get_future_trading_minutes(trading_date))
        for t in sorted(list(trading_minutes)):
            if t.time() <= dt.time(18, 0):
                _m.append(t)
            else:
                _n.append(t)
        return _n + _m

    def events(self, start_date, end_date, frequency):
        if frequency == "1d":
            # 根据起始日期和结束日期，获取所有的交易日，然后再循环获取每一个交易日
            for day in self._env.data_proxy.get_trading_dates(start_date, end_date):
                date = day.to_pydatetime()
                dt_before_trading = date.replace(hour=0, minute=0)
                dt_bar = date.replace(hour=15, minute=0)
                dt_after_trading = date.replace(hour=15, minute=30)
                dt_settlement = date.replace(hour=17, minute=0)
                yield Event(EVENT.BEFORE_TRADING, calendar_dt=dt_before_trading, trading_dt=dt_before_trading)
                yield Event(EVENT.BAR, calendar_dt=dt_bar, trading_dt=dt_bar)

                yield Event(EVENT.AFTER_TRADING, calendar_dt=dt_after_trading, trading_dt=dt_after_trading)
                yield Event(EVENT.SETTLEMENT, calendar_dt=dt_settlement, trading_dt=dt_settlement)
        elif frequency == '1m':
            for day in self._env.data_proxy.get_trading_dates(start_date, end_date):
                before_trading_flag = True
                date = day.to_pydatetime()
                last_dt = None
                done = False

                trading_minutes = self._get_trading_minutes(date)

                if len(trading_minutes) == 0:
                    print(f'交易日{day}无交易数据！')
                    continue
                trading_start_time = trading_minutes[0]
                trading_end_time = trading_minutes[-1]
                # dt_before_day_trading = date.replace(hour=8, minute=45)
                # dt_before_day_trading = trading_start_time.replace(hour=20, minute=0)

                while True:
                    if done:
                        break
                    exit_loop = True
                    # trading_minutes = self._get_trading_minutes(date)
                    for trading_dt in trading_minutes:
                        calendar_dt = trading_dt - datetime.timedelta(days=1) if trading_dt.time() > datetime.time(20, 0) else trading_dt
                        if last_dt is not None and calendar_dt < last_dt:
                            #
                            continue

                        if before_trading_flag:
                            before_trading_flag = False
                            yield Event(EVENT.BEFORE_TRADING,
                                        calendar_dt=trading_dt - datetime.timedelta(minutes=15),
                                        trading_dt=trading_dt - datetime.timedelta(minutes=15))

                        if self._universe_changed:
                            self._universe_changed = False
                            last_dt = calendar_dt
                            exit_loop = False
                            break
                        # yield handle bar
                        yield Event(EVENT.BAR, calendar_dt=trading_dt, trading_dt=trading_dt)
                    if exit_loop:
                        done = True

                dt = trading_end_time.replace(hour=15, minute=30)
                # dt = trading_end_time.replace(hour=16, minute=30)
                yield Event(EVENT.AFTER_TRADING, calendar_dt=dt, trading_dt=dt)

                dt = trading_end_time.replace(hour=17, minute=0)
                # dt = trading_end_time.replace(hour=16, minute=45)
                yield Event(EVENT.SETTLEMENT, calendar_dt=dt, trading_dt=dt)
        elif frequency == "tick":
            data_proxy = self._env.data_proxy
            for day in data_proxy.get_trading_dates(start_date, end_date):
                date = day.to_pydatetime()
                last_tick = None
                last_dt = None
                dt_before_day_trading = date.replace(hour=8, minute=30)
                while True:
                    for tick in data_proxy.get_merge_ticks(self._get_universe(), date, last_dt):
                        # find before trading time

                        calendar_dt = tick.datetime

                        if calendar_dt < dt_before_day_trading:
                            trading_dt = calendar_dt.replace(year=date.year, month=date.month, day=date.day)
                        else:
                            trading_dt = calendar_dt

                        if last_tick is None:
                            last_tick = tick
                            yield Event(EVENT.BEFORE_TRADING,
                                        calendar_dt=calendar_dt - datetime.timedelta(minutes=30),
                                        trading_dt=trading_dt - datetime.timedelta(minutes=30))

                        yield Event(EVENT.TICK, calendar_dt=calendar_dt, trading_dt=trading_dt, tick=tick)

                        if self._universe_changed:
                            self._universe_changed = False
                            last_dt = calendar_dt
                            break
                    else:
                        break

                dt = date.replace(hour=15, minute=30)
                yield Event(EVENT.AFTER_TRADING, calendar_dt=dt, trading_dt=dt)

                dt = date.replace(hour=17, minute=0)
                yield Event(EVENT.SETTLEMENT, calendar_dt=dt, trading_dt=dt)
        else:
            raise NotImplementedError(_("Frequency {} is not support.").format(frequency))
