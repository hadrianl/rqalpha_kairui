#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/8/29 0029 11:27
# @Author  : Hadrianl 
# @File    : util
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

FUTURE_INFO = {
    'AP': {'contract_multiplier': 10, 'margin_rate': 0.14,
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 20,
                          'close_commission_ratio': 20, 'close_commission_today_ratio': 20}},
    'MA': {'contract_multiplier': 10, 'margin_rate': 0.11,
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 2,
                          'close_commission_ratio': 2, 'close_commission_today_ratio': 6}},
    'SM': {'contract_multiplier': 5, 'margin_rate': 0.11,
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 3,
                          'close_commission_ratio': 3, 'close_commission_today_ratio': 6}},
    'SF': {'contract_multiplier': 5, 'margin_rate': 0.11,
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 3,
                          'close_commission_ratio': 3, 'close_commission_today_ratio': 9}},
    'FG': {'contract_multiplier': 20, 'margin_rate': 0.11,
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 3,
                          'close_commission_ratio': 3, 'close_commission_today_ratio': 24}},
    'CF': {'contract_multiplier': 5, 'margin_rate': 0.1,
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 4.3,
                          'close_commission_ratio': 4.3, 'close_commission_today_ratio': 0}},
    'CY': {'contract_multiplier': 5, 'margin_rate': 0.08,
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 4,
                          'close_commission_ratio': 4, 'close_commission_today_ratio': 0}},
    'OI': {'contract_multiplier': 10, 'margin_rate': 0.1,
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 2,
                          'close_commission_ratio': 2, 'close_commission_today_ratio': 0}},
    'SR': {'contract_multiplier': 10, 'margin_rate': 0.09,
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 3,
                          'close_commission_ratio': 3, 'close_commission_today_ratio': 0}},
    'PTA': {'contract_multiplier': 5, 'margin_rate': 0.1,
            'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 3,
                           'close_commission_ratio': 3, 'close_commission_today_ratio': 0}},
    'TA': {'contract_multiplier': 5, 'margin_rate': 0.1,
            'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 3,
                           'close_commission_ratio': 3, 'close_commission_today_ratio': 0}},
    'RM': {'contract_multiplier': 10, 'margin_rate': 0.09,
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 1.5,
                          'close_commission_ratio': 1.5, 'close_commission_today_ratio': 0}},
    'ZC': {'contract_multiplier': 100, 'margin_rate': 0.12,
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 4,
                          'close_commission_ratio': 4, 'close_commission_today_ratio': 4}},
    'JR': {'contract_multiplier': 100, 'margin_rate': 0.08, ###
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 0,
                          'close_commission_ratio': 0, 'close_commission_today_ratio': 0}},
    'LR': {'contract_multiplier': 100, 'margin_rate': 0.07,  ###
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 0,
                          'close_commission_ratio': 0, 'close_commission_today_ratio': 0}},
    'PM': {'contract_multiplier': 100, 'margin_rate': 0.09,  ###
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 0,
                          'close_commission_ratio': 0, 'close_commission_today_ratio': 0}},
    'RI': {'contract_multiplier': 100, 'margin_rate': 0.07,  ###
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 0,
                          'close_commission_ratio': 0, 'close_commission_today_ratio': 0}},
    'RS': {'contract_multiplier': 100, 'margin_rate': 0.23,  ###
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 0,
                          'close_commission_ratio': 0, 'close_commission_today_ratio': 0}},
    'WH': {'contract_multiplier': 100, 'margin_rate': 0.22,  ###
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 0,
                          'close_commission_ratio': 0, 'close_commission_today_ratio': 0}},

    'JM': {'contract_multiplier': 60, 'margin_rate': 0.13,
           'commission': {'commission_type': COMMISSION_TYPE.BY_MONEY, 'open_commission_ratio': 0.00006,
                          'close_commission_ratio': 0.00018, 'close_commission_today_ratio': 0.00018}},
    'J': {'contract_multiplier': 100, 'margin_rate': 0.13,
          'commission': {'commission_type': COMMISSION_TYPE.BY_MONEY, 'open_commission_ratio': 0.00006,
                         'close_commission_ratio': 0.00018, 'close_commission_today_ratio': 0.00018}},
    'I': {'contract_multiplier': 100, 'margin_rate': 0.12,
          'commission': {'commission_type': COMMISSION_TYPE.BY_MONEY, 'open_commission_ratio': 0.00006,
                         'close_commission_ratio': 0.00012, 'close_commission_today_ratio': 0.00012}},
    'C': {'contract_multiplier': 10, 'margin_rate': 0.08,
          'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 1.2,
                         'close_commission_ratio': 2, 'close_commission_today_ratio': 0}},
    'V': {'contract_multiplier': 5, 'margin_rate': 0.1,
          'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 2,
                         'close_commission_ratio': 2, 'close_commission_today_ratio': 0}},
    'B': {'contract_multiplier': 10, 'margin_rate': 0.11,
          'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 2,
                         'close_commission_ratio': 2, 'close_commission_today_ratio': 2}},
    'M': {'contract_multiplier': 10, 'margin_rate': 0.11,
          'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 1.5,
                         'close_commission_ratio': 1.5, 'close_commission_today_ratio': 1.5}},
    'P': {'contract_multiplier': 10, 'margin_rate': 0.09,
          'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 2.5,
                         'close_commission_ratio': 2.5, 'close_commission_today_ratio': 2.5}},
    'PP': {'contract_multiplier': 5, 'margin_rate': 0.01,
           'commission': {'commission_type': COMMISSION_TYPE.BY_MONEY, 'open_commission_ratio': 0.00006,
                          'close_commission_ratio': 0.00006, 'close_commission_today_ratio': 0.00006}},
    'Y': {'contract_multiplier': 10, 'margin_rate': 0.09,
          'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 2.5,
                         'close_commission_ratio': 2.5, 'close_commission_today_ratio': 2.5}},
    'A': {'contract_multiplier': 10, 'margin_rate': 0.1,
          'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 2,
                         'close_commission_ratio': 2, 'close_commission_today_ratio': 2}},
    'CS': {'contract_multiplier': 10, 'margin_rate': 0.08,
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 1.5,
                          'close_commission_ratio': 1.5, 'close_commission_today_ratio': 1.5}},
    'L': {'contract_multiplier': 5, 'margin_rate': 0.1,
          'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 2,
                         'close_commission_ratio': 2, 'close_commission_today_ratio': 2}},
    'JD': {'contract_multiplier': 10, 'margin_rate': 0.12,
           'commission': {'commission_type': COMMISSION_TYPE.BY_MONEY, 'open_commission_ratio': 0.00015,
                          'close_commission_ratio': 0.00015, 'close_commission_today_ratio': 0.00015}},
    'BB': {'contract_multiplier': 10, 'margin_rate': 0.22, ###
           'commission': {'commission_type': COMMISSION_TYPE.BY_MONEY, 'open_commission_ratio': 0.0,
                          'close_commission_ratio': 0.0, 'close_commission_today_ratio': 0.0}},
    'FB': {'contract_multiplier': 10, 'margin_rate': 0.22, ###
           'commission': {'commission_type': COMMISSION_TYPE.BY_MONEY, 'open_commission_ratio': 0.0,
                          'close_commission_ratio': 0.0, 'close_commission_today_ratio': 0.0}},

    'SN': {'contract_multiplier': 1, 'margin_rate': 0.1,
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 3,
                          'close_commission_ratio': 3, 'close_commission_today_ratio': 0}},
    'AL': {'contract_multiplier': 5, 'margin_rate': 0.11,
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 3,
                          'close_commission_ratio': 3, 'close_commission_today_ratio': 0}},
    'AU': {'contract_multiplier': 1000, 'margin_rate': 0.09,
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 10,
                          'close_commission_ratio': 10, 'close_commission_today_ratio': 0}},
    'ZN': {'contract_multiplier': 5, 'margin_rate': 0.11,
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 3,
                          'close_commission_ratio': 3, 'close_commission_today_ratio': 0}},
    'CU': {'contract_multiplier': 5, 'margin_rate': 0.11,
           'commission': {'commission_type': COMMISSION_TYPE.BY_MONEY, 'open_commission_ratio': 0.00005,
                          'close_commission_ratio': 0.00005, 'close_commission_today_ratio': 0}},
    'SC': {'contract_multiplier': 1000, 'margin_rate': 0.11,
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 20,
                          'close_commission_ratio': 20, 'close_commission_today_ratio': 0}},
    'PB': {'contract_multiplier': 5, 'margin_rate': 0.11,
           'commission': {'commission_type': COMMISSION_TYPE.BY_MONEY, 'open_commission_ratio': 0.00004,
                          'close_commission_ratio': 0.00004, 'close_commission_today_ratio': 0}},
    'BU': {'contract_multiplier': 10, 'margin_rate': 0.12,
           'commission': {'commission_type': COMMISSION_TYPE.BY_MONEY, 'open_commission_ratio': 0.0001,
                          'close_commission_ratio': 0.0001, 'close_commission_today_ratio': 0.0001}},
    'HC': {'contract_multiplier': 10, 'margin_rate': 0.12,
           'commission': {'commission_type': COMMISSION_TYPE.BY_MONEY, 'open_commission_ratio': 0.0001,
                          'close_commission_ratio': 0.0001, 'close_commission_today_ratio': 0.0001}},
    'NI': {'contract_multiplier': 1, 'margin_rate': 0.01,
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 6,
                          'close_commission_ratio': 6, 'close_commission_today_ratio': 6}},
    'RB': {'contract_multiplier': 10, 'margin_rate': 0.13,
           'commission': {'commission_type': COMMISSION_TYPE.BY_MONEY, 'open_commission_ratio': 0.0001,
                          'close_commission_ratio': 0.0001, 'close_commission_today_ratio': 0.0001}},
    'RU': {'contract_multiplier': 10, 'margin_rate': 0.14,
           'commission': {'commission_type': COMMISSION_TYPE.BY_MONEY, 'open_commission_ratio': 0.000045,
                          'close_commission_ratio': 0.000045, 'close_commission_today_ratio': 0.000045}},
    'AG': {'contract_multiplier': 15, 'margin_rate': 0.1,
           'commission': {'commission_type': COMMISSION_TYPE.BY_MONEY, 'open_commission_ratio': 0.00005,
                          'close_commission_ratio': 0.00005, 'close_commission_today_ratio': 0.00005}},
    'FU': {'contract_multiplier': 10, 'margin_rate': 0.14, ###
           'commission': {'commission_type': COMMISSION_TYPE.BY_MONEY, 'open_commission_ratio': 0.0,
                          'close_commission_ratio': 0.0, 'close_commission_today_ratio': 0.0}},
    'WR': {'contract_multiplier': 10, 'margin_rate': 0.22,  ###
           'commission': {'commission_type': COMMISSION_TYPE.BY_MONEY, 'open_commission_ratio': 0.0,
                          'close_commission_ratio': 0.0, 'close_commission_today_ratio': 0.0}},

    'IC': {'contract_multiplier': 200, 'margin_rate': 0.3,
           'commission': {'commission_type': COMMISSION_TYPE.BY_MONEY, 'open_commission_ratio': 0.000023,
                          'close_commission_ratio': 0.000023, 'close_commission_today_ratio': 0.000069}},
    'IF': {'contract_multiplier': 300, 'margin_rate': 0.16,
           'commission': {'commission_type': COMMISSION_TYPE.BY_MONEY, 'open_commission_ratio': 0.000023,
                          'close_commission_ratio': 0.000023, 'close_commission_today_ratio': 0.000069}},
    'IH': {'contract_multiplier': 300, 'margin_rate': 0.16,
           'commission': {'commission_type': COMMISSION_TYPE.BY_MONEY, 'open_commission_ratio': 0.000023,
                          'close_commission_ratio': 0.000023, 'close_commission_today_ratio': 0.000069}},
    'T': {'contract_multiplier': 10000, 'margin_rate': 0.03,
          'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 3,
                         'close_commission_ratio': 3, 'close_commission_today_ratio': 0}},
    'TF': {'contract_multiplier': 10000, 'margin_rate': 0.022,
           'commission': {'commission_type': COMMISSION_TYPE.BY_VOLUME, 'open_commission_ratio': 3,
                          'close_commission_ratio': 3, 'close_commission_today_ratio': 0}},
}
