#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/11/2 0002 15:11
# @Author  : Hadrianl 
# @File    : DataServer
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


def data_server(config_path):
    """
    [sys_stock_realtime] quotation service, download market data into redis

    Multiple RQAlpha instance can use single market data service.
    """

    from rqalpha.examples.extend_api.HKMod.realtime_data_server import RealtimeDataServer
    import configparser

    conf = configparser.ConfigParser()
    conf.read(config_path)

    sp_config = {'host': conf.get('SP_ID', 'host'),
                 'port': conf.getint('SP_ID', 'port'),
                 'License': conf.get('SP_ID', 'License'),
                 'app_id': conf.get('SP_ID', 'app_id'),
                 'user_id': conf.get('SP_ID', 'user_id'),
                 'password': conf.get('SP_ID', 'password')}

    db_config = {'host': conf.get('MONGODB', 'host'),
                 'port': conf.getint('MONGODB', 'port'),
                 'user': conf.get('MONGODB', 'username'),
                 'pwd': conf.get('MONGODB', 'password'),
                 'db': conf.get('MONGODB', 'db'),
                 }

    socket_info = {'trigger_port': conf.get('SOCKET', 'trigger_port')}

    server = RealtimeDataServer(sp_config, db_config, socket_info)

    server.publish_bar_signal()

if __name__ == '__main__':
    import sys
    path = sys.argv[1]
    data_server(path)