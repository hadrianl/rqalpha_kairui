#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/7/16 0016 10:39
# @Author  : Hadrianl 
# @File    : DataSource.py
# @License : (C) Copyright 2013-2017, 凯瑞投资


from rqalpha.interface import AbstractDataSource
from rqalpha.const import COMMISSION_TYPE
from rqalpha.api import logger
from rqalpha.model.instrument import Instrument
from rqalpha.model.snapshot import SnapshotObject
from rqalpha.environment import Environment
import pandas as pd
import numpy as np
import pymongo
import datetime
from functools import lru_cache
from collections import deque
import re
import time



class HKDataSource(AbstractDataSource):
    def __init__(self, host, db, port=27017, user=None, pwd=None):
        self._conn = pymongo.MongoClient(f'mongodb://{host}:{port}/')
        if user and pwd:
            self._user = user
            admin_db = self._conn.get_database('admin')
            admin_db.authenticate(user, pwd)
        self._db = self._conn.get_database(db)

    def available_data_range(self, frequency):
        self.freq = frequency
        Collection = self._db.future_1min
        _end_stamp = Collection.find_one({'type': '1min'}, projection=['date_stamp'], sort=[('datetime', pymongo.DESCENDING)])['date_stamp']
        return (datetime.date(2011, 1, 1), datetime.date.fromtimestamp(_end_stamp) - datetime.timedelta(days=1))

    def current_snapshot(self, instrument, frequency, dt):
        order_book_id = instrument.order_book_id
        Collection = self._db.future_1min_
        cursor = Collection.find({'code': order_book_id, "datetime": {'$lte': dt}},
                                 ['datetime', 'open', 'high', 'low', 'close', 'volume', 'trade_date'],
                                 sort=[('datetime', pymongo.DESCENDING)]).batch_size(300)
        trade_date = None
        data = []
        for d in cursor:
            if trade_date is None:
                trade_date = d['trade_date']
            if d['trade_date'] == trade_date:
                data.append(d)
            else:
                pre_close = d
                cursor.close()
                data.reverse()
                break

        df = pd.DataFrame(data)


        if not df.empty:
            _datetime = df['datetime'].iloc[-1].timestamp()
            _open = df['open'].iloc[0]
            _high = df['high'].max()
            _low = df['low'].min()
            _last = df['close'].iloc[-1]
            _volume = df['volume'].sum()
        else:
            _datetime = dt.timestamp()
            _open, _high, _low, _last, _volume = 0, 0, 0, 0, 0

        _data = {'datetime': _datetime, 'open': _open, 'high': _high, 'low': _low, 'last': _last, 'volume': _volume, 'pre_close': pre_close['close']}
        return SnapshotObject(instrument, _data, dt)

    @lru_cache(maxsize=1)
    def get_all_instruments(self):
        con_col = self._db.future_contract_info
        prod_col = self._db.future_product_info
        code_list = con_col.distinct('CODE')
        inst_list = []

        for c in code_list:
            con_info = con_col.find_one({'CODE': c}, sort=[('DATE', pymongo.DESCENDING)])
            prod_info = prod_col.find_one({'CLASS_CODE': con_info['CLASS_CODE']}, sort=[('DATE', pymongo.DESCENDING)])
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

    def get_bar(self, instrument, dt, frequency):
        order_book_id = instrument.order_book_id
        Collection = self._db.get_collection(f'future_{frequency}_')
        # if frequency in ['1m', '1min']:
        data = Collection.find_one(
            {'code': order_book_id, "datetime": dt})
        # else:
        #     data = None

        if data is None:
            # return super(SPDataSource, self).get_bar(instrument, dt, frequency)
            with open('missing_data.csv','a') as f:
                f.write(f'{frequency}, {order_book_id}, {dt}\n')
            logger.info(f'<Data Missing>lack of {frequency} data --- {order_book_id}@{dt} ')
            return {'code': order_book_id, 'datetime': dt.strftime('%Y-%m-%d %H:%M:%S'), 'open': np.nan, 'high': np.nan, 'low': np.nan, 'close': np.nan, 'volume': np.nan}
        else:
            data['datetime'] = data['datetime'].strftime('%Y-%m-%d %H:%M:%S')
            return data

    def get_commission_info(self, instrument):
        order_book_id = instrument.order_book_id
        if 'HSI' in order_book_id:
            commission_info = {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 33.54, 'close_commission_ratio': 33.54, 'close_commission_today_ratio': 33.54}
        elif  'MHI' in order_book_id:
            commission_info = {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 13.6,
                               'close_commission_ratio': 13.6, 'close_commission_today_ratio': 13.6}
        else:
            commission_info = super(HKDataSource, self).get_commission_info(instrument)
        return commission_info

    def get_margin_info(self, instrument):
        return {'long_margin_ratio': 0.08, 'short_margin_ratio': 0.08}


    def get_merge_ticks(self, order_book_id_list, trading_date, last_dt=None):
        ...

    def get_settle_price(self, instrument, date):
        order_book_id = instrument.order_book_id
        Collection = self._db.future_1min
        _d = datetime.datetime(date.year, date.month, date.day, 16, 29)
        data = Collection.find_one({'code': order_book_id, 'datetime': {'$lte': _d}}, ['close'])
        _close = data['close']
        return _close

    def get_trading_calendar(self):
        # Collection = self._db.future_1min
        # cursor = Collection.find(projection=['date_stamp', 'time_stamp'])
        # _datetime = set(d['date_stamp'] for d in cursor if  datetime.time(9, 15) <=datetime.datetime.fromtimestamp(d['time_stamp']).time() <= datetime.time(16, 30))
        # trading_calendar = [pd.Timestamp.fromtimestamp(t) for t in _datetime]
        # trading_calendar.sort(key=lambda x: x.timestamp())
        Collection = self._db.future_contract_info
        trading_calendar = [pd.Timestamp(td) for td in Collection.distinct('DATE')]
        trading_calendar.sort(key=lambda x: x.timestamp())
        return np.array(trading_calendar)

    def get_trading_minutes_for(self, instrument, trading_dt):
        order_book_id = instrument.order_book_id
        Collection = self._db.get_collection(f'future_{self.freq}_')
        ds = trading_dt + datetime.timedelta(hours=9, minutes=14)
        de = trading_dt + datetime.timedelta(hours=16, minutes=30)
        if Collection.find_one({'code': order_book_id, 'datetime': {'$gte': ds, '$lte': de}}) is None:
            return []
        else:
            _d = Collection.find({'code': order_book_id, 'datetime':{'$gte': ds, '$lte': de}}, projection=['datetime'], sort=[('datetime', pymongo.DESCENDING)])
            d = [i['datetime'] for i in _d]
            _bar_before_d = Collection.find_one({'code': order_book_id, 'datetime':{'$lt': ds}}, projection=['datetime'], sort=[('datetime', pymongo.DESCENDING)])

            if _bar_before_d is not None:
                td = _bar_before_d['datetime']
                if datetime.time(17, 14) < td.time() <= datetime.time(23, 59):
                    _d_aht = Collection.find({'code': order_book_id,
                                              'datetime':{'$gte': td.replace(hour=17, minute=14),
                                                          '$lte': td.replace(hour=23, minute=59)}}, projection=['datetime'], sort=[('datetime', pymongo.DESCENDING)])
                    d_aht = [i['datetime'] for i in _d_aht]
                    d = d + d_aht
                elif datetime.time(0, 0) < td.time() <= datetime.time(2, 0):
                    _d_aht = Collection.find({'code': order_book_id,
                                              'datetime':{'$gte': td.replace(hour=0, minute=0) - datetime.timedelta(hours=6, minutes=46),
                                                          '$lte': td.replace(hour=2, minute=0)}}, projection=['datetime'], sort=[('datetime', pymongo.DESCENDING)])
                    d_aht = [i['datetime'] for i in _d_aht]
                    d = d + d_aht

            d.reverse()
            with open('trade_date.csv', 'a') as f:
                print(f'{trading_dt}-#{order_book_id}-{len(d)}', file=f)
            return d

    def get_yield_curve(self, start_date, end_date, tenor=None):
        ...

    def history_bars(self, instrument, bar_count, frequency, fields, dt, skip_suspended=True,
                     include_now=False, adjust_type='pre', adjust_orig=None):
        order_book_id = instrument.order_book_id
        Collection = self._db.get_collection(f'future_{frequency}_')
        query_type = '$lte' if include_now else '$lt'
        cur = Collection.find({'code': order_book_id, 'datetime':{query_type: dt}}, limit=bar_count, sort=[('datetime', pymongo.DESCENDING)])
        data = deque()
        for c in cur:
            c['datetime'] = c['datetime'].timestamp()
            data.appendleft(c)

        _d = pd.DataFrame(list(data))
        # _d['datetime'] = _d['datetime'].apply(lambda x: x.timestamp())
        fields = [field for field in fields if field in _d.columns]
        return _d.loc[:, fields].T.as_matrix()

    def get_risk_free_rate(self, start_date, end_date):
        return 0.028

    @staticmethod
    def _check_ktype(ktype):
        _ktype = re.findall(r'^(\d+)([a-zA-Z]+)$', ktype)[0]
        if _ktype:
            _n = int(_ktype[0])
            _t = _ktype[1].lower()
            if _t in ['m', 'min']:
                _t = 'T'
                if _n not in [1, 5, 15, 30, 60]:
                    raise Exception(f'不支持{ktype}类型, 请输入正确的ktype!')
            elif _t in ['d', 'day']:
                _t = 'D'
                if _n not in [1]:
                    raise Exception(f'不支持{ktype}类型, 请输入正确的ktype!')
            else:
                raise Exception(f'不支持{ktype}类型, 请输入正确的ktype!')
        else:
            raise Exception(f'不支持{ktype}类型, 请输入正确的ktype!')

        return f'{_n}{_t}'











