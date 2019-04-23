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
from rqalpha.examples.extend_api.CtpMod.TdxData import Future
from rqalpha.examples.extend_api.HKMod.HKData import HKFuture
from pyecharts_javascripthon.dom import alert, console, Math
from pyecharts import Kline, Page, Line, Overlap, HeatMap, Grid, Bar
import talib
import datetime as dt


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
        self._settlement_temp = []

        # env.event_bus.add_listener(EVENT.POST_BAR, self._pub_bar)
        env.event_bus.add_listener(EVENT.POST_BAR, self._pub_account)
        # env.event_bus.add_listener(EVENT.POST_BAR, self._pub_position)
        # env.event_bus.add_listener(EVENT.TRADE, self._pub_trade)
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
        self._settlement_temp.append(_data)
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
        print(path)
        self.register(websocket)

        for _d in self._settlement_temp:
            await websocket.send(_d)

        async def send():
            while websocket.open:
                _data = self._data_queue.get()
                await asyncio.ensure_future(self.send_data(_data))

        async def recv():
            while websocket.open:
                data = await websocket.recv()
                chart = {'topic': 'trade', 'html': f'{data}tesing!!!!!!!!!!!'}
                _data = json.dumps(chart)
                await self.send_data(_data)

        await asyncio.wait([send(), recv()])

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
        # self._trade_temp.append(_data)
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

        if path == '/bars/':
            print(request_headers)



def get_bars(code):
    _id = request.args.get('id', None)

    trade = Session.trades[code]

    trade.loc[:, 'datetime'] = pd.to_datetime(trade.loc[:, 'datetime'], format='%Y-%m-%d %H:%M:%S')
    _match_trade = []
    _match = []
    _match_vol = 0
    for i, v in trade.iterrows():
        _match.append(v)
        _match_vol += (v.last_quantity if v.side == "BUY" else -v.last_quantity)
        if _match_vol == 0:
            _match_trade.append(_match)
            _match = []
    else:
        if _match_vol != 0:
            _match_trade.append(_match)

    for m in _match_trade:
        for t in m:
            if t.exec_id == int(_id):
                trade_points_raw = m
                break

    profit = 0
    for tpr in trade_points_raw:
        profit += tpr.last_price *  (tpr.last_quantity if tpr.side =='SELL' else - tpr.last_quantity)

    trade_lines_raw = []
    pos = 0
    p_pos = 0
    for i in range(len(trade_points_raw)):
        tpr1 = trade_points_raw[i]
        pos += (tpr1.last_quantity if tpr1.side == 'BUY' else -tpr1.last_quantity)
        for j in range(i + 1, len(trade_points_raw)):
            tpr2 = trade_points_raw[j]
            if tpr1.side != tpr2.side:
                p_pos += (tpr2.last_quantity if tpr2.side == 'BUY' else -tpr2.last_quantity)
                if abs(pos) > abs(p_pos):
                    continue
                trade_lines_raw.append([tpr1, tpr2])
                p_pos = 0
                break



    trade_points = [{'coord': [str(tpr.datetime), tpr.last_price, tpr.last_quantity],
                     'name': 'trade',
                     'label': {'show': True, 'formatter': label_tooltip, 'offset': [0, -30], 'fontSize': 15,
                               'fontFamily': 'monospace', 'color': 'black'},
                     'symbol': 'triangle',
                     'symbolSize': 8 + 3*tpr.last_quantity,
                     'symbolKeepAspect': False,
                     'itemStyle': {'color': 'blue' if tpr.side == 'BUY' else 'green'},
                     'emphasis': {'label': {'show': True, 'formatter': label_tooltip, 'offset': [0, -30], 'fontSize': 30, 'fontFamily': 'monospace', 'color': 'black', 'fontWeight': 'bolder'},
                                  'itemStyle': {'color': 'black'}},
                     'symbolRotate': 0 if tpr.side == 'BUY' else 180} for tpr in trade_points_raw]

    trade_lines = [[{ 'coord':[str(tpr1.datetime), tpr1.last_price],
                    'lineStyle':{'type': 'dashed',
                                 'color': 'red' if ((tpr2.last_price - tpr1.last_price) if tpr2.side == 'SELL'
                                 else (tpr1.last_price - tpr2.last_price)) >= 0 else 'green'},

                    'emphasis': {'lineStyle':{'type': 'dashed',
                                              'color': 'red' if ((tpr2.last_price - tpr1.last_price) if tpr2.side == 'SELL'
                                                                 else (tpr1.last_price - tpr2.last_price)) >= 0 else 'green',
                                              'width': 2 + 0.1 * abs(tpr2.last_price - tpr1.last_price) * abs(tpr1.last_quantity)},
                                 'label': {'show': True,
                                           'formatter': f'{abs(tpr2.last_price - tpr1.last_price)*abs(tpr1.last_quantity)}',
                                           'position': 'middle', 'fontSize': 25,}},
                     },
                   {'coord': [str(tpr2.datetime), tpr2.last_price],
                    'lineStyle': {'type': 'dashed',
                                  'color': 'red' if ((tpr2.last_price - tpr1.last_price) if tpr2.side == 'SELL'
                                                     else (tpr1.last_price - tpr2.last_price)) >= 0 else 'green',},

                    'emphasis': {'lineStyle': {'type': 'dashed',
                                               'color': 'red' if ((tpr2.last_price - tpr1.last_price) if tpr2.side == 'SELL'
                                                                  else (tpr1.last_price - tpr2.last_price)) >= 0 else 'green',
                                               'width': 2 + 0.1 * abs(tpr2.last_price - tpr1.last_price) * abs(tpr1.last_quantity)},
                                 'label': {'show': True,
                                           'formatter': f'{abs(tpr2.last_price - tpr1.last_price)*abs(tpr1.last_quantity)}',
                                           'position': 'middle', 'fontSize': 25,}
                                 },
                    }] for tpr1, tpr2 in trade_lines_raw]

    _from = trade_points_raw[0].datetime - dt.timedelta(minutes=60)
    _to = trade_points_raw[-1].datetime + dt.timedelta(minutes=60)

    f = Future(user='krdata', pwd='kairuitouzi') if code[:3] not in ['HSI', 'MHI', 'HHI'] else HKFuture(user='krdata', pwd='kairuitouzi')
    _bars = f.get_bars(code, fields=['datetime', 'open', 'close', 'low', 'high'],
                        start=_from, end=_to)

    x_axis = _bars[0].astype(str)
    kline = Kline(f'{code}-1min KLine    Profit:{profit}')
    kline.add(
        f'{code}',
        x_axis,
        _bars[1:].T,
        mark_point_raw=trade_points,
        mark_line_raw=trade_lines,
        # label_formatter=label_tooltip,
        # xaxis_type='category',
        tooltip_trigger='axis',
        tooltip_formatter=kline_tooltip,
        is_datazoom_show=True,
        datazoom_range=[0, 100],
        datazoom_type='horizontal',
        is_more_utils=True)

    overlap_kline = Overlap('KLine',  width='1500px', height='600px')
    overlap_kline.add(kline)

    _close = _bars[2].astype(float)
    MA = {}
    for w in [5, 10, 30, 60]:
        ma = talib.MA(_close, timeperiod=w)
        MA[w] = Line(f'MA{w}')
        MA[w].add(f'MA{w}',
                  x_axis,
                  np.round(ma, 2),
                  is_symbol_show=False,
                  is_smooth=True
                  )
        overlap_kline.add(MA[w])

    macdDIFF, macdDEA, macd = talib.MACDEXT(_close, fastperiod=12, fastmatype=1,
                                            slowperiod=26, slowmatype=1,
                                            signalperiod=9, signalmatype=1)
    diff_line = Line('diff')
    dea_line = Line('dea')
    macd_bar = Bar('macd')
    diff_line.add('diff', x_axis, macdDIFF, line_color='yellow', is_symbol_show=False, is_smooth=True)
    dea_line.add('diff', x_axis, macdDEA,  line_color='blue', is_symbol_show=False, is_smooth=True)
    macd_bar.add('macd', x_axis, macd, is_visualmap=True, visual_type='color', is_piecewise=True, pieces=[{max: 0},{min: 0}])

    overlap_macd = Overlap('MACD',  width='1500px', height='200px')
    overlap_macd.add(diff_line)
    overlap_macd.add(dea_line)
    overlap_macd.add(macd_bar)

    grid = Grid('Anlysis',  width='1500px', height='800px')

    grid.add(overlap_kline, grid_top='0%')
    grid.add(overlap_macd, grid_top='80%')
    return grid.render_embed()


def kline_tooltip(params):
    # s = params[0].seriesName + '</br>'
    d = params[0].name + '</br>'
    o = '开: ' + params[0].data[1] + '</br>'
    h = '高: ' + params[0].data[2] + '</br>'
    l = '低: ' + params[0].data[3] +  '</br>'
    c = '收: ' + params[0].data[4] + '</br>'
    text = d + o + h + l + c
    return text

def label_tooltip(params):
    text = params.data.coord[2] + '@[' + params.data.coord[1] + ']'
    return text