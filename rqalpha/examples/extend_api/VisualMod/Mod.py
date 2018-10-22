#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/7/27 0027 9:08
# @Author  : Hadrianl 
# @File    : Mod.py
# @License : (C) Copyright 2013-2017, 凯瑞投资

from rqalpha.interface import AbstractMod
from rqalpha.events import EVENT
from rqalpha.api import logger
from rqalpha.environment import Environment
from rqalpha.utils.repr import  properties
import websockets
from queue import Queue
import asyncio
from threading import Thread
import json
import http
import subprocess
import os
import numpy as np




__config__ = {
              'webbrower': None,
              'host': 'localhost',
              'port': 8050,
              'localvisualize': False}


class DataVisualMod(AbstractMod):
    def __init__(self):
        self._inject_api()

    def start_up(self, env, mod_config):
        self._webbrower = mod_config.webbrower
        self._host = mod_config.host
        self._port = mod_config.port
        self.CLI = set()
        self._data_queue = Queue()

        # env.event_bus.add_listener(EVENT.POST_BAR, self._pub_bar)
        env.event_bus.add_listener(EVENT.POST_BAR, self._pub_account)
        # env.event_bus.add_listener(EVENT.POST_BAR, self._pub_position)
        env.event_bus.add_listener(EVENT.TRADE, self._pub_trade)
        env.event_bus.add_listener(EVENT.SETTLEMENT, self._pub_settlement)
        self._init_websocket_server()
        self.ps = subprocess.Popen(f'python {os.path.join(os.path.dirname(__file__), "VisualApp.py")} {self._host} {self._port}')


        if mod_config.localvisualize:
            env.event_bus.add_listener(EVENT.POST_SYSTEM_INIT, self._init_local_visualization)

    def tear_down(self, code, exception=None):
        self.ps.terminate()

    def _pub_bar(self, POST_BAR):
        for code, bar in POST_BAR.bar_dict.items():
            _data = bar._data
            if '_id' in _data:
                _data.pop('_id')
            _data['topic'] = 'bar'
            has_data = all([_data['open'] is not np.nan,
                            _data['high'] is not np.nan,
                            _data['low'] is not np.nan,
                            _data['close'] is not np.nan
                            ])
            if has_data:
                _data = json.dumps(_data)
                self._data_queue.put(_data)

    def _pub_account(self, POST_BAR):
        account = Environment.get_instance().portfolio.accounts['FUTURE']
        positions = account.positions
        _data = {
                'datetime': str(POST_BAR.bar_dict.dt),
                'total_value': account.total_value,
                'margin': account.margin,
                'buy_margin': account.buy_margin,
                'sell_margin': account.sell_margin,
                'daily_pnl': account.daily_pnl,
                'holding_pnl': account.holding_pnl,
                'realized_pnl': account.realized_pnl,
                'frozen_cash': account.frozen_cash,
                'cash': account.cash,
                'market_value': account.market_value,
                'transaction_cost': account.transaction_cost}
        _data['topic'] = 'account'
        _data = json.dumps(_data)
        self._data_queue.put(_data)

        for p in positions:
            _pos = properties(positions[p])  # todo:性能优化
            _pos['topic'] = 'position'
            for i, op in enumerate(_pos['open_orders']):
                op = properties(op)
                op['trading_datetime'] = str(op['trading_datetime'])
                op['datetime'] = str(op['datetime'])
                op['side'] = str(op['side'])
                op['position_effect'] = str(op['position_effect'])
                op['status'] = str(op['status'])
                op['type'] = str(op['type'])
                _pos['open_orders'][i] = op
            _pos = json.dumps(_pos)
            self._data_queue.put(_pos)

    def _pub_settlement(self, event):
        account = Environment.get_instance().portfolio.accounts['FUTURE']
        settlement_dt = event.trading_dt
        _data = {'topic': 'settlement',
                 'datetime': str(settlement_dt.date()),
                 'total_value': account.total_value,
                 'daily_pnl': account.daily_pnl,
                 'transaction_cost': account.transaction_cost}
        _data = json.dumps(_data)
        self._data_queue.put(_data)

    # def _pub_position(self, POST_BAR):
    #     account = Environment.get_instance().portfolio.accounts['FUTURE']
    #     print(account.position)
    #     _data = {
    #             'datetime': str(POST_BAR.bar_dict.dt),
    #             'total_value': account.total_value,
    #             'margin': account.margin,
    #             'buy_margin': account.buy_margin,
    #             'sell_margin': account.sell_margin,
    #             'daily_pnl': account.daily_pnl,
    #             'holding_pnl': account.holding_pnl,
    #             'realized_pnl': account.realized_pnl,
    #             'frozen_cash': account.frozen_cash,
    #             'cash': account.cash,
    #             'market_value': account.market_value,
    #             'transaction_cost': account.transaction_cost}
    #     _data['topic'] = 'account'
    #     _data = json.dumps(_data)
    #     self._data_queue.put(_data)

    async def backtest_visual(self, websocket, path):
        self.register(websocket)

        while websocket.open:
            _data = self._data_queue.get()
            await asyncio.ensure_future(self.send_data(_data))

        self.unregister(websocket)

    async def send_data(self, d):
        for cli in self.CLI:
            try:
                await cli.send(d)
            except websockets.ConnectionClosed:
                cli.close()

    def register(self, websocket):
        logger.debug(f'注册{websocket}')
        self.CLI.add(websocket)

    def unregister(self, websocket):
        logger.debug(f'注销{websocket}')
        self.CLI.remove(websocket)

    def _pub_trade(self, Trade):
        trade_dict = properties(Trade.trade)
        trade_dict['topic'] = 'trade'
        trade_dict['datetime'] = str(trade_dict['datetime'])
        trade_dict['trading_datetime'] = str(trade_dict['trading_datetime'])
        trade_dict['side'] = trade_dict['side'].value
        trade_dict['position_effect'] = trade_dict['position_effect'].value
        _data = json.dumps(trade_dict)
        self._data_queue.put(_data)

    def _inject_api(self):
        from rqalpha import export_as_api
        from rqalpha.execution_context import ExecutionContext
        from rqalpha.const import EXECUTION_PHASE

        @export_as_api
        @ExecutionContext.enforce_phase(EXECUTION_PHASE.ON_INIT,
                                        EXECUTION_PHASE.BEFORE_TRADING,
                                        EXECUTION_PHASE.ON_BAR,
                                        EXECUTION_PHASE.AFTER_TRADING,
                                        EXECUTION_PHASE.SCHEDULED)
        def pub_data(dt, order_book_id, topic_vals):
            data = {}
            data['datetime'] = str(dt)
            data['code'] = order_book_id
            data['topic_vals'] = topic_vals
            data['topic'] = 'extra'
            _data = json.dumps(data)
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
            webbrowser.get('brower').open(f'{self._host}:{self._port}', new=1, autoraise=True)

class ServerProtocol(websockets.WebSocketServerProtocol):
    async def process_request(self, path, request_headers):
        if path == '/health/':
            return http.HTTPStatus.OK, [], b'OK\n'




