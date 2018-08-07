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
import pandas as pd
import numpy as np
import pymongo
import datetime
from functools import lru_cache


instructment_HSI =  {'abbrev_symbol': 'null',
  'contract_multiplier': 50,
  'de_listed_date': '0000-00-00',
  'exchange': 'SHFE',
  'listed_date': '0000-00-00',
  'margin_rate': 0.05,
  'maturity_date': '0000-00-00',
  'order_book_id': 'HSI',
  'product': 'Index',
  'round_lot': 1.0,
  'settlement_method': 'CashSettlementRequired',
  'symbol': '恒指主力合约',
  'trading_unit': '5',
  'type': 'Future',
  'underlying_order_book_id': 'HSI',
  'underlying_symbol': 'HSI'}


class SPDataSource(AbstractDataSource):
    def __init__(self, host, db, port=27017):
        self._conn = pymongo.MongoClient(f'mongodb://{host}:{port}/')
        self._db = self._conn.get_database(db)

    def available_data_range(self, frequency):
        if frequency == '1m':
            Collection = self._db.sp_future_min
            _end_stamp = Collection.find_one({'type': '1min'}, projection=['date_stamp'], sort=[('time_stamp', pymongo.DESCENDING)])['date_stamp']
            return (datetime.date(2018, 7, 3), datetime.date.fromtimestamp(_end_stamp) - datetime.timedelta(days=1))

    def current_snapshot(self, instrument, frequency, dt):
        order_book_id = instrument.order_book_id
        Collection = self._db.sp_future_min
        ds = datetime.datetime(dt.year, dt.month, dt.day, 9, 14).timestamp()
        _d = Collection.find_one({'code': order_book_id, 'type': '1min', 'time_stamp':{'$lt': ds}}, projection=['date_stamp'], sort=[('time_stamp', pymongo.DESCENDING)])
        yes_o = (datetime.datetime.fromtimestamp(_d['date_stamp'])
                 - datetime.timedelta(days=1)
                 + datetime.timedelta(hours=17, minutes=15)).timestamp()
        now = dt.timestamp()
        cursor = Collection.find({'code': order_book_id, "time_stamp": {'$gte': yes_o, '$lte': now}, 'type': '1min'},
                                 ['datetime', 'open', 'high', 'low', 'close', 'vol'],
                                 sort=[('time_stamp', pymongo.ASCENDING)])
        data = [d for d in cursor]
        df = pd.DataFrame(data)
        if not df.empty:
            _datetime = datetime.datetime.strptime(df['datetime'].iloc[-1], '%Y-%m-%d %H:%M:%S').timestamp()
            _open = df['open'].iloc[0]
            _high = df['high'].max()
            _low = df['low'].min()
            _last = df['close'].iloc[-1]
            _volume = df['vol'].sum()
        else:
            _datetime = dt.timestamp()
            _open, _high, _low, _last, _volume = 0, 0, 0, 0, 0

        pre_close_raw = Collection.find_one({'code': order_book_id, 'type': '1min', 'time_stamp': {'$lt': yes_o}},
                                                 projection=['close', 'datetime'], sort=[('time_stamp', pymongo.DESCENDING)])
        _pre_close = pre_close_raw['close']
        _data = {'datetime': _datetime, 'open': _open, 'high': _high, 'low': _low, 'last': _last, 'volume': _volume, 'pre_close': _pre_close}

        return SnapshotObject(instrument, _data, dt)

    @lru_cache(maxsize=1)
    def get_all_instruments(self):
        inst_list = [Instrument(instructment_HSI)]
        return inst_list

    def get_bar(self, instrument, dt, frequency):
        order_book_id = instrument.order_book_id
        Collection = self._db.sp_future_min
        if frequency in ['1m', '1min']:
            data = Collection.find_one(
                {'code': order_book_id, "datetime": dt.strftime('%Y-%m-%d %H:%M:%S'), 'type': '1min'})
        else:
            data = None

        if data is None:
            # return super(SPDataSource, self).get_bar(instrument, dt, frequency)
            with open('missing_data.csv','a') as f:
                f.write(f'{frequency}, {order_book_id}, {dt}\n')
            logger.info(f'<Data Missing>lack of {frequency} data --- {order_book_id}@{dt} ')
            return {'code': order_book_id, 'datetime': dt.strftime('%Y-%m-%d %H:%M:%S'), 'open': np.nan, 'high': np.nan, 'low': np.nan, 'close': np.nan, 'volume': np.nan}
        else:
            data.setdefault('volume', data.pop('vol'))
            return data

    def get_commission_info(self, instrument):
        order_book_id = instrument.order_book_id
        if order_book_id == 'HSI':
            commission_info = {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 33.54, 'close_commission_ratio': 33.54, 'close_commission_today_ratio': 33.54}
        elif order_book_id == 'MHI':
            commission_info = {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 13.6,
                               'close_commission_ratio': 13.6, 'close_commission_today_ratio': 13.6}
        else:
            commission_info = super(SPDataSource, self).get_commission_info(instrument)
        return commission_info

    def get_margin_info(self, instrument):
        return {'long_margin_ratio': 0.08, 'short_margin_ratio': 0.08}


    def get_merge_ticks(self, order_book_id_list, trading_date, last_dt=None):
        ...

    def get_settle_price(self, instrument, date):
        order_book_id = instrument.order_book_id
        Collection = self._db.sp_future_min
        _d = datetime.datetime(date.year, date.month, date.day, 16, 29).timestamp()
        data = Collection.find_one({'code': order_book_id, 'time_stamp': {'$lte': _d}}, ['close'])
        _close = data['close']
        return _close

    def get_trading_calendar(self):
        Collection = self._db.sp_future_min
        cursor = Collection.find({'code': 'HSI'}, ['date_stamp', 'time_stamp'])
        _datetime = set(d['date_stamp'] for d in cursor if datetime.datetime.fromtimestamp(d['time_stamp']).time() == datetime.time(9, 15))
        trading_calendar = [pd.Timestamp.fromtimestamp(t) for t in _datetime]
        trading_calendar.sort(key=lambda x: x.timestamp())
        return np.array(trading_calendar)



    def get_trading_minutes_for(self, instrument, trading_dt):
        order_book_id = instrument.order_book_id
        Collection = self._db.sp_future_min
        ds = (trading_dt + datetime.timedelta(hours=9, minutes=15)).timestamp()
        if Collection.find_one({'code': order_book_id, 'type': '1min', 'time_stamp': ds}) is None:
            return []
        _d = Collection.find_one({'code': order_book_id, 'type': '1min', 'time_stamp':{'$lt': ds}}, projection=['date_stamp', 'time_stamp'], sort=[('time_stamp', pymongo.DESCENDING)])  # 查找上一夜盘的时间
        yes_1 = datetime.datetime.fromtimestamp(_d['date_stamp']).strftime('%Y-%m-%d')  # 夜盘结束的日期
        yes = (datetime.datetime.fromtimestamp(_d['date_stamp']) - datetime.timedelta(days=1)).strftime('%Y-%m-%d')  # 夜盘开始的日期
        day = trading_dt.strftime('%Y-%m-%d')  # 当日
        date1 = pd.date_range(start=yes + ' 17:15:00', end=yes_1 + ' 00:59:00', freq='T').to_pydatetime() # 夜盘时间
        date2 = pd.date_range(start=day + ' 09:15:00', end=day + ' 11:59:00', freq='T').to_pydatetime()
        date3 = pd.date_range(start=day + ' 13:00:00', end=day + ' 16:29:00', freq='T').to_pydatetime()
        return date1.tolist() + date2.tolist() + date3.tolist()

    def get_yield_curve(self, start_date, end_date, tenor=None):
        ...

    def history_bars(self, instrument, bar_count, frequency, fields, dt, skip_suspended=True,
                     include_now=False, adjust_type='pre', adjust_orig=None):
        order_book_id = instrument.order_book_id
        Collection = self._db.sp_future_min
        query_type = '$lte' if include_now else '$lt'
        frequency = '1min' if frequency in ['1m', '1min'] else frequency
        _time = dt.timestamp()
        data = Collection.find({'code': order_book_id, 'type': frequency, 'time_stamp':{query_type: _time}}, limit=bar_count, sort=[('time_stamp', pymongo.DESCENDING)])
        data = [d for d in data]
        data.reverse()
        _d = pd.DataFrame(data)
        _d = _d.rename(columns={'vol': 'volume'})
        _d['datetime'] = _d['time_stamp']
        fields = [field for field in fields if field in _d.columns]
        return _d.loc[:, fields].T.as_matrix()

    def get_risk_free_rate(self, start_date, end_date):
        return 0.028











