#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/8/7 0007 10:33
# @Author  : Hadrianl 
# @File    : setup
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

import platform
from os.path import dirname, join
try:
    from pip._internal.req import parse_requirements
except ImportError:
    from pip.req import parse_requirements

from setuptools import find_packages, setup


def update_requirements(from_reqs, to_reqs):
    from_req_dict = {req.name: req for req in from_reqs}
    from_req_dict.update({req.name: req for req in to_reqs})
    return from_req_dict.values()


with open(join(dirname(__file__), 'rqalpha/VERSION.txt'), 'rb') as f:
    version = f.read().decode('ascii').strip()

requirements = parse_requirements("requirements.txt", session=False)

req_strs = [str(ir.req) for ir in requirements]


setup(
    name='rqalpha_KaiRui',
    version=version,
    description='Ricequant Algorithm Trading System Modified By KaiRui',
    packages=find_packages(exclude=[]),
    author='Hadrianl',
    author_email='137150224@qq.com',
    license='Apache License v2',
    package_data={'': ['*.*']},
    url='https://github.com/ricequant/rqalpha',
    install_requires=req_strs,
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "KRrqalpha = rqalpha.__main__:entry_point"
        ]
    },
    classifiers=[
        'Programming Language :: Python',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: Unix',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)