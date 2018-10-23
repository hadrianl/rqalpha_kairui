#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/9/3 0003 15:43
# @Author  : Hadrianl 
# @File    : TdxData
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


import pymongo as pmg
import pandas as pd
import re
from dateutil import parser
import datetime as dt

class Future:
    def __init__(self, host='192.168.2.226', port=27017, db='Future', user=None, pwd=None):
        self._mongodb_host = host
        self._mongodb_port = port
        self._conn = pmg.MongoClient(f'mongodb://{host}:{port}/')
        if user and pwd:
            self._user = user
            admin_db = self._conn.get_database('admin')
            admin_db.authenticate(user, pwd)
        self._db = self._conn.get_database(db)
        self._col = self._db.get_collection('future_1min')

    def get_local_code_list(self):   # 获取本地合约列表
        code_list = self._col.distinct('code')
        return code_list

    def get_bars(self, code, fields=None, start=None, end=None, ktype='1m'):
        '''
        获取k线数据，历史k线从数据库拿，当日从tdx服务器提取,按天提取数据
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

        start = dt.datetime(1970, 1, 2) if start is None else start
        end = dt.datetime(2999, 1, 1) if end is None else end
        _start = start - dt.timedelta(days=1)
        _end = end + dt.timedelta(days=1)


        ktype = self.__check_ktype(ktype)
        _fields = ['datetime', 'open', 'high', 'low', 'close', 'position', 'trade', 'price', 'code', 'market']
        cursor = self._col.find({'code': code, 'datetime':{'$gte': _start, '$lt': _end}}, _fields)
        history_bar = [d for d in cursor]   # 从本地服务器获取历史数据
        df = pd.DataFrame(history_bar, columns=_fields)
        df.set_index('datetime', drop=False, inplace=True)
        _t = df['datetime'].apply(self.__sort_bars)
        df['_t'] = _t
        df.sort_values('_t', inplace=True)
        def _resample(x):
            _dt = pd.date_range(x.index[0].date(), x.index[0].date() + dt.timedelta(days=1), freq='T')[:len(x)]
            x['_t_temp'] = _dt
            apply_func_dict = {'datetime': 'last',
                               'open': 'first',
                               'high': 'max',
                               'low': 'min',
                               'close': 'last',
                               'position': 'last',
                               'trade': 'sum',
                               'price': 'mean',
                               'code': 'first',
                               'market': 'first',
                               '_t': 'last'
                               }
            resampled = x.resample(ktype, on='_t_temp').apply(apply_func_dict)
            if ktype == '1D':
                resampled.index = resampled['datetime'].apply(lambda x: x.date())
                resampled['datetime'] = resampled['datetime'].apply(lambda x: pd.Timestamp(x.year, x.month, x.day))
            else:
                resampled.set_index('datetime', drop=False, inplace=True)
            return resampled

        resampled_df = df.groupby(by= lambda x: x.date()).apply(_resample)

        if isinstance(resampled_df.index, pd.MultiIndex):
            resampled_df.reset_index(0, drop=True, inplace=True)

        resampled_df = resampled_df.loc[(resampled_df._t>=self.__sort_bars(start))&(resampled_df._t <= self.__sort_bars(end))]
        resampled_df = resampled_df.rename(columns={'trade': 'vol'})
        if fields is None:
            fields = [field for field in resampled_df.columns]
        else:
            fields = [field for field in fields if field in resampled_df.columns]


        return resampled_df.loc[:, fields].T.as_matrix()

    @staticmethod
    def __sort_bars(_dt):
        if _dt.time() > dt.time(18, 0):
            _dt = _dt - dt.timedelta(days=1)
        return _dt.timestamp()

    @staticmethod
    def __check_ktype(ktype):
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