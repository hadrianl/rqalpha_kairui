#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/7/23 0023 16:46
# @Author  : Hadrianl 
# @File    : __init__.py.py
# @License : (C) Copyright 2013-2017, 凯瑞投资

import click
from rqalpha import cli



# @cli.command()
# @click.argument('config_path', required=True)

def load_mod():
    from .Mod import HKDataMod
    return HKDataMod()
