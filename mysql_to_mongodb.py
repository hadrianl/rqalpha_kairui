#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/7/17 0017 16:42
# @Author  : Hadrianl 
# @File    : mysql_to_mongodb.py
# @License : (C) Copyright 2013-2017, 凯瑞投资

import pymongo
import pymysql
import pandas as pd
import datetime as dt
import json

MongoDB_client = pymongo.MongoClient('mongodb://localhost:27017/')
MysqlDB = pymysql.connect(input('Host:>'), input('User:>'), input('Password:>'), charset='utf8')
sp = MongoDB_client.SP
sp_future_min = sp.get_collection('sp_future_min')
last_date_stamp = sp_future_min.find_one(projection=['date_stamp'], sort=[('date_stamp', pymongo.DESCENDING)])['date_stamp']
last_date = dt.datetime.fromtimestamp(last_date_stamp).strftime('%Y-%m-%d 00:00:00')

cursor = MysqlDB.cursor(pymysql.cursors.DictCursor)
cursor.execute(f'SELECT * FROM carry_investment.wh_same_month_min where datetime >= "{last_date}"')
data = cursor.fetchall()
d = pd.DataFrame(data)
d.loc[:, 'type'] = '1min'
d.loc[:, 'datetime'] = d.loc[:, 'datetime'].apply(str)
d.loc[:, 'time_stamp'] = d.datetime.apply(lambda x: dt.datetime.strptime(x, '%Y-%m-%d %H:%M:%S').timestamp())
d.loc[:, 'date_stamp'] = d.time_stamp.apply(lambda x: dt.datetime.fromordinal(dt.datetime.fromtimestamp(x).date().toordinal()).timestamp())
d = d.rename(columns={'prodcode':'code'})
d = json.loads(d.to_json(orient='records'))

# sp_future_min.update_many({'code': d['code']})
for _d in d:
    sp_future_min.replace_one({'code':_d['code'], 'time_stamp': _d['time_stamp'], 'date_stamp': _d['date_stamp']}, _d, upsert=True)
sp_future_min.create_index([('code', pymongo.ASCENDING), ('time_stamp', pymongo.ASCENDING), ('date_stamp', pymongo.ASCENDING)])