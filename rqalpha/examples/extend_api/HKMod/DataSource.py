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


class HKDataSource(AbstractDataSource):
    def __init__(self, host, db, port=27017):
        self._conn = pymongo.MongoClient(f'mongodb://{host}:{port}/')
        self._db = self._conn.get_database(db)

    def available_data_range(self, frequency):
        if frequency == '1m':
            Collection = self._db.future_1min
            _end_stamp = Collection.find_one({'type': '1min'}, projection=['date_stamp'], sort=[('datetime', pymongo.DESCENDING)])['date_stamp']
            return (datetime.date(2011, 1, 1), datetime.date.fromtimestamp(_end_stamp) - datetime.timedelta(days=1))

    def current_snapshot(self, instrument, frequency, dt):
        order_book_id = instrument.order_book_id
        Collection = self._db.future_1min
        _from = self.get_trading_minutes_for(instrument, datetime.datetime(dt.year, dt.month, dt.day))[0]
        cursor = Collection.find({'code': order_book_id, "datetime": {'$gte': _from , '$lte': dt}, 'type': '1min'},
                                 ['datetime', 'open', 'high', 'low', 'close', 'volume'],
                                 sort=[('datetime', pymongo.ASCENDING)])
        data = [d for d in cursor]
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

        pre_close_raw = Collection.find_one({'code': order_book_id, 'type': '1min', 'datetime': {'$lt': _from}},
                                                 projection=['close', 'datetime'], sort=[('datetime', pymongo.DESCENDING)])
        _pre_close = pre_close_raw['close']
        _data = {'datetime': _datetime, 'open': _open, 'high': _high, 'low': _low, 'last': _last, 'volume': _volume, 'pre_close': _pre_close}

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
        Collection = self._db.future_1min
        if frequency in ['1m', '1min']:
            data = Collection.find_one(
                {'code': order_book_id, "datetime": dt, 'type': '1min'})
        else:
            data = None

        if data is None:
            # return super(SPDataSource, self).get_bar(instrument, dt, frequency)
            with open('missing_data.csv','a') as f:
                f.write(f'{frequency}, {order_book_id}, {dt}\n')
            logger.info(f'<Data Missing>lack of {frequency} data --- {order_book_id}@{dt} ')
            return {'code': order_book_id, 'datetime': dt.strftime('%Y-%m-%d %H:%M:%S'), 'open': np.nan, 'high': np.nan, 'low': np.nan, 'close': np.nan, 'volume': np.nan}
        else:
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
        Collection = self._db.future_1min
        ds = trading_dt + datetime.timedelta(hours=9, minutes=14)
        de = trading_dt + datetime.timedelta(hours=16, minutes=30)
        if Collection.find_one({'code': order_book_id, 'type': '1min', 'datetime': {'$gte': ds, '$lte': de}}) is None:
            return []
        else:
            _d = Collection.find({'code': order_book_id, 'type': '1min', 'datetime':{'$gte': ds, '$lte': de}}, projection=['date_stamp', 'datetime'], sort=[('datetime', pymongo.DESCENDING)])
            d = [i['datetime'] for i in _d]
            _bar_before_d = Collection.find_one({'code': order_book_id, 'type': '1min', 'datetime':{'$lt': ds}}, projection=['date_stamp', 'datetime'], sort=[('datetime', pymongo.DESCENDING)])

            if _bar_before_d is not None:
                if datetime.time(17, 14) < _bar_before_d['datetime'].time() <= datetime.time(23, 59):
                    _d_aht = Collection.find({'code': order_book_id, 'type': '1min',
                                              'datetime':{'$gte': datetime.datetime.fromtimestamp(_bar_before_d['date_stamp']) + datetime.timedelta(hours=17, minutes=14),
                                                          '$lte': datetime.datetime.fromtimestamp(_bar_before_d['date_stamp']) + datetime.timedelta(hours=23, minutes=59)}}, projection=['date_stamp', 'datetime'], sort=[('datetime', pymongo.DESCENDING)])
                    d_aht = [i['datetime'] for i in _d_aht]
                    d = d + d_aht
                elif datetime.time(0, 0) < _bar_before_d['datetime'].time() <= datetime.time(2, 0):
                    _d_aht = Collection.find({'code': order_book_id, 'type': '1min',
                                              'datetime':{'$gte': datetime.datetime.fromtimestamp(_bar_before_d['date_stamp']) - datetime.timedelta(hours=6, minutes=46),
                                                          '$lte': datetime.datetime.fromtimestamp(_bar_before_d['date_stamp']) + datetime.timedelta(hours=2, minutes=0)}}, projection=['date_stamp', 'datetime'], sort=[('datetime', pymongo.DESCENDING)])
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
        Collection = self._db.future_1min
        query_type = '$lte' if include_now else '$lt'
        frequency = '1min' if frequency in ['1m', '1min'] else frequency
        data = Collection.find({'code': order_book_id, 'type': frequency, 'datetime':{query_type: dt}}, limit=bar_count, sort=[('datetime', pymongo.DESCENDING)])
        data = [d for d in data]
        data.reverse()
        _d = pd.DataFrame(data)
        _d['datetime'] = _d['datetime'].apply(lambda x: x.timestamp())
        fields = [field for field in fields if field in _d.columns]
        return _d.loc[:, fields].T.as_matrix()

    def get_risk_free_rate(self, start_date, end_date):
        return 0.028











