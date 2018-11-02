#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/10/30 0030 9:43
# @Author  : Hadrianl 
# @File    : realtime_data_source
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


import os
import six
import numpy as np

from rqalpha.interface import AbstractDataSource
from rqalpha.const import MARGIN_TYPE
from rqalpha.utils.py2 import lru_cache
from rqalpha.utils.datetime_func import convert_date_to_int, convert_int_to_date
from rqalpha.utils.i18n import gettext as _

from rqalpha.data.future_info_cn import CN_FUTURE_INFO
from rqalpha.data.adjust import adjust_bars, FIELDS_REQUIRE_ADJUSTMENT
from rqalpha.data.public_fund_commission import PUBLIC_FUND_COMMISSION
from rqalpha.const import COMMISSION_TYPE
from spapi.spAPI import *
from spapi.sp_struct import *
import datetime as dt
from rqalpha.api import logger
from queue import Queue, Empty
import pymongo as pmg
from threading import Thread
from collections import deque
import pandas as pd
from rqalpha.events import EVENT
import time
from rqalpha.environment import Environment
from rqalpha.model.instrument import Instrument
from .util import _convert_from_ctype

class RealtimeDataSource(AbstractDataSource):
    def __init__(self, db_user=None, db_pwd=None, db='HKFuture',db_host='192.168.2.226', server_host='localhost', server_port=6868):
        mongo_cli = pmg.MongoClient(db_host)
        if db_user and db_pwd:
            admin_db = mongo_cli.get_database('admin')
            admin_db.authenticate(db_user, db_pwd)
        self._db = mongo_cli.get_database(db)
        self._col = self._db.get_collection('realtime_future_1min_')
        self._col.create_index([('datetime', pmg.DESCENDING), ('code', pmg.ASCENDING)], unique=True)
        self._col.create_index([('code', pmg.ASCENDING)])
        self.bar_trigger_thread = Thread(target=self.trigger_bar_from_server, args=(server_host, server_port))
        self.bar_trigger_thread.setDaemon(True)

    def trigger_bar_from_server(self, host, port):
        import zmq
        ctx = zmq.Context()
        self.trigger_socket = ctx.socket(zmq.SUB)
        self.trigger_socket.set_string(zmq.SUBSCRIBE, '')
        self.trigger_socket.setsockopt(zmq.RCVTIMEO, 5000)
        addr = f'tcp://{host}:{port}'
        self.trigger_socket.connect(addr)
        env = Environment.get_instance()
        event_queue = env.event_source.event_queue
        while True:
            try:
                d = self.trigger_socket.recv_pyobj()
                event_queue.put((d, EVENT.BAR))
            except zmq.ZMQError:
                ...

    def get_trading_minutes_for(self, order_book_id, trading_dt):
        raise NotImplementedError

    def get_trading_calendar(self):
        Collection = self._db.future_contract_info
        trading_calendar = [pd.Timestamp(td) for td in Collection.distinct('DATE')]
        trading_calendar.sort(key=lambda x: x.timestamp())
        return np.array(trading_calendar)

    def get_all_instruments(self):
        con_col = self._db.realtime_future_contract_info
        prod_col = self._db.realtime_future_product_info
        code_list = con_col.distinct('CODE')
        inst_list = []

        for c in code_list:
            con_info = con_col.find_one({'CODE': c}, sort=[('DATE', pmg.DESCENDING)])
            prod_info = prod_col.find_one({'CLASS_CODE': con_info['CLASS_CODE']}, sort=[('DATE', pmg.DESCENDING)])
            inst = {
                # 'abbrev_symbol': 'null',
                'contract_multiplier': con_info['CON_SIZE'],
                'de_listed_date': con_info['DATE_TO'].strftime('%Y-%m-%d'),
                'exchange': 'HKEX',
                'listed_date': con_info['DATE_FROM'].strftime('%Y-%m-%d'),
                'margin_rate': 0.05,
                'maturity_date': con_info['EXPIRY_DATE'].strftime('%Y-%m-%d'),
                'order_book_id': con_info['CODE'],
                'product': 'Index',
                'round_lot': 1.0,
                'settlement_method': 'CashSettlementRequired',
                'symbol': prod_info['PROD_NAME'],
                # 'trading_unit': '5',
                'type': 'Future',
                'underlying_order_book_id': con_info['Filler'],
                'underlying_symbol': con_info['CLASS_CODE']}
            inst_list.append(Instrument(inst))
        return inst_list


    # INSTRUMENT_TYPE_MAP = {
    #     'CS': 0,
    #     'INDX': 1,
    #     'Future': 2,
    #     'ETF': 3,
    #     'LOF': 3,
    #     'FenjiA': 3,
    #     'FenjiB': 3,
    #     'FenjiMu': 3,
    #     'PublicFund': 4
    # }

    def get_bar(self, instrument, dt, frequency):

        if frequency in ['1m', '1min']:
            frequency = '1min'
        order_book_id = instrument.order_book_id
        Collection = self._db.get_collection(f'realtime_future_{frequency}_')
        if frequency in ['1m', '1min']:
            data = Collection.find_one(
                {'code': order_book_id, "datetime": dt})
        else:
            data = None

        if data is None:
            return {'code': order_book_id, 'datetime': dt.strftime('%Y-%m-%d %H:%M:%S'), 'open': np.nan, 'high': np.nan,
                    'low': np.nan, 'close': np.nan, 'volume': np.nan}
        else:
            data['datetime'] = data['datetime'].strftime('%Y-%m-%d %H:%M:%S')
            return data

    def get_settle_price(self, instrument, date):
        order_book_id = instrument.order_book_id
        Collection = self._db.realtime_future_1min_
        _d = dt.datetime(date.year, date.month, date.day, 16, 29)
        data = Collection.find_one({'code': order_book_id, 'datetime': {'$lte': _d}}, ['close'])
        _close = data['close']
        return _close

    def history_bars(self, instrument, bar_count, frequency, fields, dt,
                     skip_suspended=True, include_now=False,
                     adjust_type='pre', adjust_orig=None):
        order_book_id = instrument.order_book_id
        Collection = self._db.get_collection(f'realtime_future_{frequency}_')
        query_type = '$lte' if include_now else '$lt'
        cur = Collection.find({'code': order_book_id, 'datetime':{query_type: dt}}, limit=bar_count, sort=[('datetime', pmg.DESCENDING)])
        data = deque()
        for c in cur:
            c['datetime'] = c['datetime'].timestamp()
            data.appendleft(c)

        _d = pd.DataFrame(list(data))
        # _d['datetime'] = _d['datetime'].apply(lambda x: x.timestamp())
        fields = [field for field in fields if field in _d.columns]
        return _d.loc[:, fields].T.as_matrix()

    def get_yield_curve(self, start_date, end_date, tenor=None):
        ...

    def get_risk_free_rate(self, start_date, end_date):
        return 0.028

    def current_snapshot(self, instrument, frequency, dt):
        raise NotImplementedError

    def available_data_range(self, frequency):
        if frequency == '1m':
            return (dt.date(2011, 1, 1), dt.date.today() + dt.timedelta(days=1))

    def get_margin_info(self, instrument):
        return {
            'margin_type': MARGIN_TYPE.BY_MONEY,
            'long_margin_ratio': instrument.margin_rate,
            'short_margin_ratio': instrument.margin_rate,
        }

    def get_commission_info(self, instrument):
        order_book_id = instrument.order_book_id
        if 'HSI' in order_book_id:
            commission_info = {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 33.54, 'close_commission_ratio': 33.54, 'close_commission_today_ratio': 33.54}
        elif  'MHI' in order_book_id:
            commission_info = {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 13.6,
                               'close_commission_ratio': 13.6, 'close_commission_today_ratio': 13.6}
        else:
            commission_info = super(RealtimeDataSource, self).get_commission_info(instrument)
        return commission_info

    def get_ticks(self, order_book_id, date):
        raise NotImplementedError

