#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/7/27 0027 9:08
# @Author  : Hadrianl 
# @File    : Mod.py
# @License : (C) Copyright 2013-2017, 凯瑞投资

from rqalpha.interface import AbstractMod
from rqalpha.events import EVENT
from rqalpha.api import logger
import websockets
from queue import Queue
import asyncio
from threading import Thread
import json
import http
import subprocess
import os
import socket




__config__ = {'order_book_id': 'HSI',
              'webbrower': None,
              'localvisualize': False}


class DataVisualMod(AbstractMod):
    def __init__(self):
        ...

    def start_up(self, env, mod_config):
        self._order_book_id = mod_config.order_book_id
        self._webbrower = mod_config.webbrower
        self.CLI = set()
        self._data_queue = Queue()

        env.event_bus.add_listener(EVENT.POST_BAR, self._pub_bar)
        env.event_bus.add_listener(EVENT.TRADE, self._pub_trade)
        self._init_websocket_server()
        self.ps = subprocess.Popen(f'python {os.path.join(os.path.dirname(__file__), "VisualApp.py")}')


        if mod_config.localvisualize:
            env.event_bus.add_listener(EVENT.POST_SYSTEM_INIT, self._init_local_visualization)

    def tear_down(self, code, exception=None):
        self.ps.terminate()

    def _pub_bar(self, POST_BAR):
        bar_dict = POST_BAR.bar_dict[self._order_book_id]
        _data = bar_dict._data
        if '_id' in _data:
            _data.pop('_id')
        _data['topic'] = 'bar'
        _data = json.dumps(_data)
        self._data_queue.put(_data)

    async def backtest_visual(self, websocket, path):
        await self.register(websocket)

        while websocket.open:
            _data = self._data_queue.get()
            await asyncio.ensure_future(self.send_data(_data))

        await self.unregister(websocket)

    async def send_data(self, d):
        for cli in self.CLI:
            try:
                await cli.send(d)
            except websockets.ConnectionClosed:
                cli.close()

    async def register(self, websocket):
        logger.debug(f'注册{websocket}')
        self.CLI.add(websocket)

    async def unregister(self, websocket):
        logger.debug(f'注销{websocket}')
        self.CLI.remove(websocket)

        
    def _pub_trade(self, Trade):
        _t = Trade.trade
        trade_dict = {}
        trade_dict['topic'] = 'trade'
        trade_dict['calendar_dt'] = str(_t._calendar_dt)
        trade_dict['trading_dt'] = str(_t._trading_dt)
        trade_dict['price'] = _t._price
        trade_dict['amount'] = _t._amount
        trade_dict['order_id'] = _t._order_id
        trade_dict['commission'] = _t._commission
        trade_dict['tax'] = _t._tax
        trade_dict['trade_id'] = _t._trade_id
        trade_dict['close_today_amount'] = _t._close_today_amount
        trade_dict['side'] = _t._side.value
        trade_dict['position_effect'] = _t._position_effect.value
        trade_dict['order_book_id'] = _t._order_book_id
        trade_dict['frozen_price'] = _t._frozen_price
        _data = json.dumps(trade_dict)
        self._data_queue.put(_data)

    def _init_websocket_server(self):
        loop = asyncio.get_event_loop()
        self._backtest_visual = websockets.serve(self.backtest_visual, '0.0.0.0', 7214, create_protocol=ServerProtocol)
        loop.run_until_complete(self._backtest_visual)

        self._websocket_thread = Thread(target=loop.run_forever)
        self._websocket_thread.setDaemon(True)
        self._websocket_thread.start()

    def _init_local_visualization(self, event):
        import webbrowser
        if self._webbrower is not None:
            webbrowser.register('brower', None, webbrowser.BackgroundBrowser(self._webbrower))
            webbrowser.get('brower').open(f'{socket.gethostbyname(socket.gethostname())}:5000', new=1, autoraise=True)

class ServerProtocol(websockets.WebSocketServerProtocol):
    async def process_request(self, path, request_headers):
        if path == '/health/':
            return http.HTTPStatus.OK, [], b'OK\n'




