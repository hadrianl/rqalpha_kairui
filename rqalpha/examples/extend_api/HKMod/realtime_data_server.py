#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/10/31 0031 18:55
# @Author  : Hadrianl 
# @File    : realtime_data_server
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

from rqalpha.const import COMMISSION_TYPE
from spapi.spAPI import *
from spapi.sp_struct import *
import zmq
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

class RealtimeDataServer:
    def __init__(self, sp_info, db_info, socket_info):
        mongo_cli = pmg.MongoClient(db_info['host'])
        admin_db = mongo_cli.get_database('admin')
        admin_db.authenticate(db_info['user'], db_info['pwd'])
        self._db = mongo_cli.get_database(db_info['db'])
        self._col = self._db.get_collection('realtime_future_1min_')
        self._col.create_index([('datetime', pmg.DESCENDING), ('code', pmg.ASCENDING)], unique=True)
        self._col.create_index([('code', pmg.ASCENDING)])
        self.ctx = zmq.Context()
        self.trigger_socket = self.ctx.socket(zmq.PUB)
        self.trigger_socket.bind(f'tcp://*: {socket_info["trigger_port"]}')
        self.prod_codes = {}
        initialize()
        set_login_info(**sp_info)
        self._init_callback()
        login()
        time.sleep(3)
        self._init_subscribe()

    def _init_callback(self):
        self._ticker_queues = {}
        self._price_queues = {}
        self._trigger_queue = Queue()
        self._resample_thread = {}

        @on_login_reply  # 登录成功时候调用
        def login_reply(user_id, ret_code, ret_msg):
            if ret_code == 0:
                api_logger.info(f'@{user_id.decode()}登录成功')
                self._init_subscribe()
            else:
                api_logger.error(f'@{user_id.decode()}登录失败--errcode:{ret_code}--errmsg:{ret_msg.decode()}')

        @on_instrument_list_reply  # 产品系列信息的回调推送，用load_instrument_list()触发
        def inst_list_reply(req_id, is_ready, ret_msg):
            if is_ready:
                api_logger.info('<产品>' + f'信息加载成功      req_id:{req_id}-msg:{ret_msg.decode()}')
            else:
                api_logger.error('<产品>' + f'信息正在加载......req_id{req_id}-msg:{ret_msg.decode()}')

        @on_product_list_by_code_reply  # 根据产品系列名返回合约信息
        def product_list_by_code_reply(req_id, inst_code, is_ready, ret_msg):
            if is_ready:
                if inst_code == '':
                    api_logger.info('<合约>' + f'该产品系列没有合约信息      req_id:{req_id}-msg:{ret_msg.decode()}')
                else:
                    api_logger.info('<合约>' + f'产品:{inst_code.decode()}合约信息加载成功      req_id:{req_id}-msg:{ret_msg.decode()}')
            else:
                api_logger.error('<合约>' + f'产品:{inst_code.decode()}合约信息正在加载......req_id:{req_id}-msg:{ret_msg.decode()}')

        #
        @on_business_date_reply  # 登录成功后会返回一个交易日期
        def business_date_reply(business_date):
            self.trade_date = dt.datetime.fromtimestamp(business_date)
            api_logger.info('<日期>' + f'当前交易日--{self.trade_date}')

        @on_ticker_update  # ticker数据推送
        def ticker_update(ticker: SPApiTicker):
            ticker_dict = _convert_from_ctype(ticker)
            self._ticker_queues[ticker_dict['ProdCode']].put(ticker_dict)
            api_logger.info(f'{ticker_dict}')

        @on_api_price_update  # price数据推送
        def price_update(price: SPApiPrice):
            price_dict = _convert_from_ctype(price)
            self._price_queues[price_dict['ProdCode']].append(price_dict)
            api_logger.info(f'{price_dict}')

        self.on_login_reply = login_reply
        self.inst_list_reply = inst_list_reply
        self.product_list_by_code_reply = product_list_by_code_reply
        self.business_date_reply = business_date_reply
        self.ticker_update = ticker_update
        self.price_update = price_update

    def _init_subscribe(self):
        contract_col = self._db.get_collection('realtime_future_contract_info')
        code = contract_col.find()
        self.prod_codes = {c['Filler']: c['CODE'] for c in code}

        for p in self.prod_codes:
            self.subscribe_ticker(p)
        for p in self.prod_codes:
            self.subscribe_price(p)

    def _resample_ticker(self, prod_code):
        tickers = []
        q = self._ticker_queues[prod_code]
        code = self.prod_codes[prod_code]
        time_diff = 0
        while True:
            try:
                tick = q.get(timeout=1)
                time_diff = tick['TickerTime'] - time.time()
                print(time_diff)
            except Empty:
                if tickers and time.time() % (tickers[-1]['TickerTime'] // 60) >= 61 + time_diff:  # 在没有新的一分钟tick数据时，跨过下分钟超过3秒会自动生成bar
                    price_list = []
                    vol_list = []
                    d = dt.datetime.fromtimestamp(tickers[-1]['TickerTime']).replace(second=0)
                    for t in tickers:
                        price_list.append(t['Price'])
                        vol_list.append(t['Qty'])
                    o, h, l, c, v = price_list[0], max(price_list), min(price_list), price_list[-1], sum(vol_list)
                    self._col.update_one({'datetime': d, 'code': code},
                                         {'$set': {'datetime': d, 'code': code, 'open': o,
                                                   'high': h, 'low': l, 'close': c, 'volume': v,
                                                   'trade_date': self.trade_date}}, upsert=True)
                    self._trigger_queue.put(d)
                    tickers.clear()
                continue

            if tick is None:
                break

            if tickers and tickers[-1]['TickerTime'] // 60 != tick['TickerTime'] // 60:
                price_list = []
                vol_list = []
                d = dt.datetime.fromtimestamp(tickers[-1]['TickerTime']).replace(second=0)
                for t in tickers:
                    price_list.append(t['Price'])
                    vol_list.append(t['Qty'])
                o, h, l, c, v = price_list[0], max(price_list), min(price_list), price_list[-1], sum(vol_list)
                self._col.update_one({'datetime': d, 'code': code}, {'$set': {'datetime': d, 'code': code, 'open': o,
                                                                                   'high': h, 'low': l, 'close': c, 'volume': v,
                                                                                   'trade_date': self.trade_date}}, upsert=True)
                self._trigger_queue.put(d)
                tickers.clear()

            tickers.append(tick)


    def subscribe_ticker(self, prod_code):
        self._ticker_queues.setdefault(prod_code, Queue())
        subscribe_ticker(prod_code, 1)
        t = self._resample_thread.setdefault(prod_code, Thread(target=self._resample_ticker, args=(prod_code, )))
        if not t.isAlive():
            t.setDaemon(True)
            t.start()

    def unsubscribe_ticker(self, prod_code):
        subscribe_ticker(prod_code, 0)
        q = self._ticker_queues.pop(prod_code)
        t = self._resample_thread.pop(prod_code)
        q.put(None)
        t.join()

    def subscribe_price(self, prod_code):
        self._price_queues.setdefault(prod_code, deque(maxlen=1))
        subscribe_price(prod_code, 1)

    def unsubscribe_price(self, prod_code):
        try:
            self._price_queues.pop(prod_code)
        finally:
            subscribe_price(prod_code, 0)

    def publish_bar_signal(self):
        dt_list = []
        while True:
            d = self._trigger_queue.get()
            dt_list.append(d)
            print(d)
            if len(dt_list) >= len(self._resample_thread) or dt.datetime.now() > d + dt.timedelta(seconds=2):
                self.trigger_socket.send_pyobj(d)
                dt_list.clear()


def add_contract(db_info, code):
    mongo_cli = pmg.MongoClient(db_info['host'])
    admin_db = mongo_cli.get_database('admin')
    admin_db.authenticate(db_info['user'], db_info['pwd'])
    db = mongo_cli.get_database(db_info['db'])
    contract_col = db.get_collection('realtime_future_contract_info')
    product_info = db.get_collection('realtime_future_product_info')
    contract_col.create_index([('DATE', pmg.DESCENDING), ('CODE', pmg.ASCENDING)], unique=True)
    contract_col.create_index([('CODE', pmg.ASCENDING)])
    product_info.create_index([('DATE', pmg.DESCENDING), ('CLASS_CODE', pmg.ASCENDING)], unique=True)
    product_info.create_index([('CLASS_CODE', pmg.ASCENDING)])


