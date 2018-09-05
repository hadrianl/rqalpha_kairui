#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/7/16 0016 10:39
# @Author  : Hadrianl 
# @File    : DataSource.py
# @License : (C) Copyright 2013-2017, 凯瑞投资


from rqalpha.interface import AbstractDataSource
from rqalpha.const import COMMISSION_TYPE
from .util import FUTURE_INFO
from rqalpha.api import logger
from rqalpha.model.instrument import Instrument
from rqalpha.model.snapshot import SnapshotObject
import pandas as pd
import numpy as np
import pymongo
import datetime
from functools import lru_cache
import re
# from .DataFetch import Future

'''
参数	类型	说明
order_book_id	str	期货代码，期货的独特的标识符（郑商所期货合约数字部分进行了补齐。例如原有代码'ZC609'补齐之后变为'ZC1609'）。主力连续合约UnderlyingSymbol+88，例如'IF88' ；指数连续合约命名规则为UnderlyingSymbol+99
symbol	str	期货的简称，例如'沪深1005'
margin_rate	float	期货合约最低保证金率
abbrev_symbol	str	期货的名称缩写，例如'HS1005'。主力连续合约与指数连续合约都为'null'
round_lot	float	期货全部为1.0
listed_date	str	期货的上市日期。主力连续合约与指数连续合约都为'0000-00-00'
type	str	合约类型，'Future'
contract_multiplier	float	合约乘数，例如沪深300股指期货的乘数为300.0
underlying_order_book_id	str	合约标的代码，目前除股指期货(IH, IF, IC)之外的期货合约，这一字段全部为'null'
underlying_symbol	str	合约标的名称，例如IF1005的合约标的名称为'IF'
maturity_date	str	期货到期日。主力连续合约与指数连续合约都为'0000-00-00'
settlement_method	str	交割方式，'CashSettlementRequired' - 现金交割, 'PhysicalSettlementRequired' - 实物交割
product	str	产品类型，'Index' - 股指期货, 'Commodity' - 商品期货, 'Government' - 国债期货
exchange	str	交易所，'DCE' - 大连商品交易所, 'SHFE' - 上海期货交易所，'CFFEX' - 中国金融期货交易所, 'CZCE'- 郑州商品交易所

0.0y	1.9096
0.08y	1.9877
0.17y	2.08
0.25y	2.1451
0.5y	2.6733
0.75y	2.8057
1.0y	2.8593
3.0y	3.3028
5.0y	3.4022
7.0y	3.594
10.0y	3.6101
15.0y	3.8934
20.0y	3.9346
30.0y	4.1951
40.0y	4.197
50.0y	4.199
'''
commission={}
margin={}

YIELD = {
'0S': 1.9096,
'1M': 1.9877,
'2M': 2.08,
'3M': 2.1451,
'6M': 2.6733,
'9M': 2.8057,
'1Y': 2.8593,
'2Y': 3.1084,
'3Y': 3.3028,
'4Y': 3.3737,
'5Y': 3.4022,
'6Y': 3.5223,
'7Y': 3.594,
'8Y': 3.605,
'9Y': 3.6089,
'10Y': 3.6101,
'15Y': 3.8934,
'20Y': 3.9346,
'30Y': 4.1951,
'40Y': 4.197,
'50Y': 4.199,
}


class CTPDataSource(AbstractDataSource):
    def __init__(self, host, db, port=27017):
        self._conn = pymongo.MongoClient(f'mongodb://{host}:{port}/')
        self._db = self._conn.get_database(db)
        # self._data_fetcher = Future(host, port, db)

    def available_data_range(self, frequency):
        self.frequency = frequency
        Collection = self._db.future_1min
        _start = Collection.find_one(projection=['datetime'], sort=[('datetime', pymongo.ASCENDING)])['datetime']
        _end = Collection.find_one(projection=['datetime'], sort=[('datetime', pymongo.DESCENDING)])['datetime']
        return ((_start + datetime.timedelta(days=1)).date(), (_end - datetime.timedelta(days=1)).date())

    def current_snapshot(self, instrument, frequency, dt):
        order_book_id = instrument.order_book_id
        Collection = self._db.future_1min
        cursor = Collection.find({'code': order_book_id,
                                'datetime':{'$gte': datetime.datetime(dt.year, dt.month, dt.day, 0, 0),
                                            '$lte': datetime.datetime(dt.year, dt.month, dt.day, 23, 59)}},
                               sort=[('datetime', pymongo.ASCENDING)])
        _d1=[]
        _d2=[]
        sep_time = datetime.time(18, 0)
        for d in cursor:
            if d['dateime'].time() <= sep_time:
                _d1.append(d)
            else:
                _d2.append(d)
        data =_d1 + _d2

        df = pd.DataFrame(data)
        if not df.empty:
            _datetime = datetime.datetime.strptime(df['datetime'].iloc[-1], '%Y-%m-%d %H:%M:%S').timestamp()
            _open = df['open'].iloc[0]
            _high = df['high'].max()
            _low = df['low'].min()
            _last = df['close'].iloc[-1]
            _volume = df['trade'].sum()
        else:
            _datetime = dt.timestamp()
            _open, _high, _low, _last, _volume = 0, 0, 0, 0, 0
        #
        pre_close_raw = Collection.find_one({'code': order_book_id,
                                             'datetime': {'$lt': datetime.datetime(dt.year, dt.month, dt.day, 0, 0)},
                                             'hour':{'$lt': 18}},
                                            sort = [('datetime', pymongo.DESCENDING)])
        _pre_close = pre_close_raw['close']
        _data = {'datetime': _datetime, 'open': _open, 'high': _high, 'low': _low, 'last': _last, 'volume': _volume, 'pre_close': _pre_close}

        return SnapshotObject(instrument, _data, dt)

    @lru_cache(maxsize=1)
    def get_all_instruments(self):
        Collection = self._db.future_1min
        code_list = Collection.distinct('code')
        inst_list = []
        for c in code_list:
            market = Collection.find_one({'code': c}, {'market': 1})['market']
            # _listed_date =  Collection.find_one({'code': c}, {'datetime': 1}, sort=[('datetime', pymongo.ASCENDING)])['datetime'].date()
            # _maturity_date = Collection.find_one({'code': c}, {'datetime': 1}, sort=[('datetime', pymongo.DESCENDING)])['datetime'].date()
            _listed_date = '0000-00-00'
            _maturity_date = '0000-00-00'
            underlying_symbol, contract = re.findall(r'([A-Z]+?)(L*\d+)', c)[0]
            if c[-2] == 'L':
                is_continuous = True
            else:
                is_continuous = False

            if market == 47:
                _p = 'Index' if c[0] == 'I' else 'Government'
            else:
                _p = 'Commodity'

            instructment =  {
                'order_book_id': c,
                'symbol': c,
                'margin_rate': FUTURE_INFO[underlying_symbol]['margin_rate'],
                'abbrev_symbol': 'null' if is_continuous else c,
                'round_lot': 1.0,
                'listed_date': '0000-00-00' if is_continuous else str(_listed_date),
                'de_listed_date': '0000-00-00',
                'type': 'Future',
                'contract_multiplier': FUTURE_INFO[underlying_symbol]['contract_multiplier'],
                'underlying_order_book_id': 'null' if underlying_symbol not in ('IF', 'IH', 'IC') else underlying_symbol,
                'underlying_symbol': underlying_symbol,
                'maturity_date':  '0000-00-00' if is_continuous else str(_maturity_date),
                'settlement_method': 'CashSettlementRequired',
                'product': _p,
                'exchange': {28: 'CZCE', 29: 'DCE', 30: 'SHFE', 47: 'CFFEX'}[market],
                # 'trading_unit': '5'
            }
            inst_list.append(Instrument(instructment))
        return inst_list

    def get_bar(self, instrument, dt, frequency):
        order_book_id = instrument.order_book_id
        Collection = self._db.future_1min
        if frequency in ['1m', '1min']:
            data = Collection.find_one(
                {'code': order_book_id, "datetime": dt})
        else:
            data = None

        if data is None:
            # print(order_book_id, dt)
            # return super(SPDataSource, self).get_bar(instrument, dt, frequency)
            # with open('missing_data.csv','a') as f:
            #     f.write(f'{frequency}, {order_book_id}, {dt}\n')
            # logger.info(f'<Data Missing>lack of {frequency} data --- {order_book_id}@{dt} ')
            return {'code': order_book_id, 'datetime': dt.strftime('%Y-%m-%d %H:%M:%S'), 'open': np.nan, 'high': np.nan, 'low': np.nan, 'close': np.nan, 'volume': np.nan}
        else:
            data['datetime'] = data['datetime'].strftime('%Y-%m-%d %H:%M:%S')
            data.setdefault('volume', data.pop('trade'))
            return data

    def get_commission_info(self, instrument):
        commission_info = FUTURE_INFO[instrument.underlying_symbol]['commission']
        return commission_info

    def get_margin_info(self, instrument):
        margin_info = {'long_margin_ratio': instrument.margin_rate, 'short_margin_ratio': instrument.margin_rate}
        return margin_info

    def get_merge_ticks(self, order_book_id_list, trading_date, last_dt=None):
        ...

    def get_settle_price(self, instrument, date):
        order_book_id = instrument.order_book_id
        Collection = self._db.future_1min
        _d = datetime.datetime(date.year, date.month, date.day, 18, 00)
        data = Collection.find_one({'code': order_book_id, 'datetime': {'$lte': _d}}, ['close'], sort=[('datetime', pymongo.DESCENDING)])
        _close = data['close']
        return _close

    def get_trading_calendar(self):
        import tushare as ts
        Collection = self._db.future_1min
        _start_date = Collection.find_one(sort=[('datetime', pymongo.ASCENDING)])[
                          'datetime'].date() + datetime.timedelta(days=1)
        _end_date = Collection.find_one(sort=[('datetime', pymongo.DESCENDING)])[
                        'datetime'].date() - datetime.timedelta(days=1)
        _all_trade_date = ts.trade_cal()
        _trade_date = _all_trade_date.loc[(_all_trade_date.isOpen == 1)&(str(_start_date) <= _all_trade_date.calendarDate)&(_all_trade_date.calendarDate<= str(_end_date)), 'calendarDate']
        trading_calendar = [pd.Timestamp(t) for t in _trade_date]
        trading_calendar.sort(key=lambda x: x.timestamp())
        return np.array(trading_calendar)

    def get_trading_minutes_for(self, instrument, trading_dt):
        order_book_id = instrument.order_book_id
        # trading_minutes = self._data_fetcher.get_trading_minutes(order_book_id, trading_dt, self.frequency)
        Collection = self._db.future_1min
        cursor = Collection.find({'code': order_book_id,
                                'datetime':{'$gte': datetime.datetime(trading_dt.year, trading_dt.month, trading_dt.day, 0, 0),
                                            '$lte': datetime.datetime(trading_dt.year, trading_dt.month, trading_dt.day, 23, 59)}},
                               sort=[('datetime', pymongo.ASCENDING)])
        _d1=[]
        _d2=[]
        sep_time = datetime.time(18, 0)
        for d in cursor:
            if d['datetime'].time() <= sep_time:
                _d1.append(d)
            else:
                _d2.append(d)
        data = _d2 + _d1
        trading_minutes = [d['datetime'] for d in data]

        return trading_minutes

    def get_yield_curve(self, start_date, end_date, tenor=None):
        _base = {}
        for t in YIELD:
            if t in tenor:
                _base[t] = YIELD[t]

        date_range = pd.date_range(start_date, end_date)
        df = pd.DataFrame(_base, index=date_range)
        return df

    def history_bars(self, instrument, bar_count, frequency, fields, dt, skip_suspended=True,
                     include_now=False, adjust_type='pre', adjust_orig=None):
        order_book_id = instrument.order_book_id
        Collection = self._db.future_1min
        data = []
        _dt = dt
        while True:  # 核心部分，排序
            if datetime.time(0, 0) < _dt.time() <= datetime.time(18, 0):
                _earliest_dt = datetime.datetime(_dt.year, _dt.month, _dt.day, 0, 0)
                _latest_dt = datetime.datetime(_dt.year, _dt.month, _dt.day, 18, 0) if _dt != dt else _dt
                _d = Collection.find({'code': order_book_id, 'datetime':{'$gt': _earliest_dt, '$lte': _latest_dt}}, sort=[('datetime', pymongo.DESCENDING)])
                _dt = _earliest_dt
                data.extend(d for d in _d)
            else:
                _earliest_dt = datetime.datetime(_dt.year, _dt.month, _dt.day, 18, 0)
                _latest_dt = datetime.datetime(_dt.year, _dt.month, _dt.day, 0, 0) + datetime.timedelta(days=1) if _dt != dt else _dt
                _d = Collection.find({'code': order_book_id, 'datetime':{'$gt':_earliest_dt, '$lte': _latest_dt}}, sort=[('datetime', pymongo.DESCENDING)])
                _dt = _earliest_dt - datetime.timedelta(days=1)
                data.extend(d for d in _d)

            if len(data) >= bar_count + 1:
                data = data[:bar_count] if include_now else data[1: bar_count + 1]
                data.reverse()
                # print(data)
                break

        _d = pd.DataFrame(data)
        _d = _d.rename(columns={'vol': 'trade'})
        _d['datetime'] = _d['datetime'].apply(lambda x: x.timestamp())
        fields = [field for field in fields if field in _d.columns]
        return  _d.loc[:, fields].T.as_matrix()

    def get_risk_free_rate(self, start_date, end_date):
        return 0.028











