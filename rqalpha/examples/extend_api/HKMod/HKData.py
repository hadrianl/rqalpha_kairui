#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/9/21 0021 12:49
# @Author  : Hadrianl 
# @File    : HKData


import pandas as pd
from dateutil import parser
import datetime as dt
from .util import _check_ktype, CODE_SUFFIX
import pymongo as pmg


class BaseData:
    def __init__(self, host, port, db):
        self._mongodb_host = host
        self._mongodb_port = port
        self._conn = pmg.MongoClient(f'mongodb://{host}:{port}/')
        self._db = self._conn.get_database(db)
        self._col = self._db.get_collection('future_1min')

    def get_all_codes(self):   # 获取本地合约列表
        code_list = self._col.distinct('code')
        return code_list

    def get_bars(self, code, fields=None, start=None, end=None, ktype='1m'):
        raise NotImplementedError

class HKFuture(BaseData):
    def __init__(self, host='192.168.2.226', port=27017, db='HKFuture'):
        super(HKFuture, self).__init__(host, port, db)

    def get_bars(self, code, fields=None, start=None, end=None, ktype='1m'):
        '''
        获取k线数据，按天提取
        :param code: 代码
        :param start: None为从最开始查询
        :param end: None为查询到最新的bar
        :param ktype: [1, 5, 15, 30, 60]分钟m或者min,或者1D
        :return:
        '''
        if isinstance(start, str):
            start = parser.parse(start)

        if isinstance(end, str):
            end = parser.parse(end)

        code = code.upper()
        trade_date = self.get_trading_dates(start, end, code=code)

        ktype = _check_ktype(ktype)

        data = []
        for td in trade_date:
            data.extend(self.__get_whole_date_trade(code, td))
        df = self.__format_data(data, fields, ktype)[start:end]


        if isinstance(df.index, pd.MultiIndex):
            df.reset_index(0, drop=True, inplace=True)

        resampled_df = df.rename(columns={'volume': 'vol'})
        if fields is None:
            fields = [field for field in resampled_df.columns]

        return resampled_df.loc[:, fields].T.as_matrix()

    def get_available_contracts(self, underlying:str, date):
        if isinstance(date, str):
            _date = parser.parse(date).replace(hour=0, minute=0, second=0)
        elif isinstance(date, dt.datetime):
            _date = date.replace(hour=0, minute=0, second=0)
        else:
            raise ValueError('请输入str或者datetime类型')

        underlying = underlying.upper()

        contract_info = pd.DataFrame([ci for ci in self._db.get_collection('future_contract_info').find({'CLASS_CODE': underlying, 'DATE': _date})])

        return contract_info

    def get_trading_dates(self, start, end, code=None, underlying=None):
        """
        填写code或者underlying参数，优先使用code
        :param start:
        :param end:
        :param code:
        :param underlying:
        :return:
        """
        if isinstance(start, str):
            start = parser.parse(start)

        if isinstance(end, str):
            end = parser.parse(end)

        start = start.replace(hour=0, minute=0, second=0) if start is not None else dt.datetime(1970, 1, 1)
        end = end.replace(hour=0, minute=0, second=0) if end is not None else dt.datetime(2050, 1, 1)

        if isinstance(code, str):
            trade_date = list(
                set(td['DATE'] for td in self._db.get_collection('future_contract_info').find({'CODE': code,
                                                                                               'DATE': {'$gte': start,
                                                                                                        '$lte': end}},
                                                                                              ['DATE'])))
            trade_date.sort()
            return trade_date
        elif isinstance(underlying, str):
            trade_date = list(
                set(td['DATE'] for td in self._db.get_collection('future_contract_info').find({'CLASS_CODE': underlying,
                                                                                               'DATE': {'$gte': start,
                                                                                                        '$lte': end}},
                                                                                              ['DATE'])))
            trade_date.sort()
            return trade_date
        else:
            raise Exception('请输入正确的code或者underlying')

    def get_main_contract_bars(self, underlying, fields=None, start=None, end=None, ktype='1m'):
        if isinstance(start, str):
            start = parser.parse(start)

        if isinstance(end, str):
            end = parser.parse(end)

        underlying = underlying.upper()
        trade_date = self.get_trading_dates(start, end, underlying=underlying)
        ktype = _check_ktype(ktype)

        data = []
        for i, td in enumerate(trade_date):
            _c_info = self.get_available_contracts(underlying, td)

            if _c_info.loc[0, 'EXPIRY_DATE'] not in [trade_date[i:i+2]]:
                code = _c_info.loc[0, 'CODE']
            else:
                code = _c_info.loc[1, 'CODE']

            data.extend(self.__get_whole_date_trade(code, td))

        df = self.__format_data(data, fields, ktype)

        return df

    @staticmethod
    def draw_klines(df:pd.DataFrame):
        import matplotlib.pyplot as plt
        import matplotlib.finance as mpf
        from matplotlib import ticker
        import matplotlib.dates as mdates
        columns = ['datetime', 'open', 'close', 'high', 'low', 'volume']
        if not set(df.columns).issuperset(columns):
            raise Exception(f'请包含{columns}字段')

        data = df.loc[:, columns]

        data_mat = data.as_matrix().T

        xdate = data['datetime'].tolist()

        def mydate(x, pos):
            try:
                return xdate[int(x)]
            except IndexError:
                return ''


        fig, ax1,  = plt.subplots(figsize=(1200 / 72, 480 / 72))
        plt.title('KLine', fontsize='large',fontweight = 'bold')
        mpf.candlestick2_ochl(ax1, data_mat[1], data_mat[2], data_mat[3], data_mat[4], colordown='#53c156', colorup='#ff1717', width=0.3, alpha=1)
        ax1.grid(True)
        ax1.xaxis.set_major_formatter(ticker.FuncFormatter(mydate))
        ax1.xaxis.set_major_locator(mdates.HourLocator())
        ax1.xaxis.set_major_locator(mdates.MinuteLocator(byminute=[0, 15, 30, 45],
                                                        interval=1))
        ax1.xaxis.set_major_locator(ticker.MaxNLocator(8))

    def __get_whole_date_trade(self, code, trade_date):  # 获取某一天夜盘+早盘的全部数据
        _fields = ['datetime', 'code', 'open', 'high', 'low', 'close', 'volume', 'date_stamp']
        td = trade_date
        d = [ret for ret in self._col.find(
            {'code': code, 'datetime': {'$gte': td.replace(hour=9, minute=14, second=0),
                                        '$lt': td.replace(hour=17, minute=0, second=0)}}, _fields,
            sort=[('datetime', pmg.DESCENDING)])]

        _bar_before_d = self._col.find_one({'code': code, 'datetime': {'$lt': td.replace(hour=9, minute=14, second=0)}},
                                           _fields,
                                           sort=[('datetime', pmg.DESCENDING)])

        if _bar_before_d is not None:
            if dt.time(17, 14) < _bar_before_d['datetime'].time() <= dt.time(23, 59):
                _d_aht = self._col.find({'code': code, 'type': '1min',
                                         'datetime': {'$gte': dt.datetime.fromtimestamp(
                                             _bar_before_d['date_stamp']) + dt.timedelta(hours=17,
                                                                                         minutes=14),
                                                      '$lte': dt.datetime.fromtimestamp(
                                                          _bar_before_d['date_stamp']) + dt.timedelta(
                                                          hours=23, minutes=59)}},
                                        _fields,
                                        sort=[('datetime', pmg.DESCENDING)])
                d_aht = [i for i in _d_aht]
                d = d + d_aht
            elif dt.time(0, 0) < _bar_before_d['datetime'].time() <= dt.time(2, 0):
                _d_aht = self._col.find({'code': code, 'type': '1min',
                                         'datetime': {'$gte': dt.datetime.fromtimestamp(
                                             _bar_before_d['date_stamp']) - dt.timedelta(hours=6,
                                                                                         minutes=46),
                                                      '$lte': dt.datetime.fromtimestamp(
                                                          _bar_before_d['date_stamp']) + dt.timedelta(
                                                          hours=2, minutes=0)}},
                                        _fields,
                                        sort=[('datetime', pmg.DESCENDING)])
                d_aht = [i for i in _d_aht]
                d = d + d_aht
        d.reverse()
        for _d in d:
            _d['trade_date'] = td
        return d

    def __format_data(self, data, fields, ktype):  # 格式整理
        df = pd.DataFrame(data, columns=['datetime', 'code', 'open', 'high', 'low', 'close', 'volume', 'date_stamp', 'trade_date'])
        df.set_index('datetime', drop=False, inplace=True)
        apply_func_dict = {'datetime': 'last',
                           'code': 'first',
                           'open': 'first',
                           'high': 'max',
                           'low': 'min',
                           'close': 'last',
                           'volume': 'sum',
                           'trade_date': 'first'
                           }

        resampled_df = df.resample(ktype).apply(apply_func_dict)
        resampled_df.dropna(how='all', inplace=True)
        if fields is None:
            fields = [field for field in resampled_df.columns]
        else:
            fields = [field for field in fields if field in resampled_df.columns]

        return resampled_df.loc[:, fields]