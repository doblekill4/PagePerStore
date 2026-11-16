# -*- coding: utf-8 -*-
"""统一日志：同一目录、按天分文件、滚动保留近 N 天。

命名：{名称}_{YYYYMMDD}.log，例如 主程序_20261116.log。
目录：config.json 的「路径.日志目录」，未配置时默认程序同目录的「日志」文件夹。
保留：config.json 的「路径.日志保留天数」，默认 30 天；每次获取日志器时清理过期文件。

设计要点：
- 各业务模块只管调 获取日志器(名称)，不再各自硬编码路径/文件名。
- 用 FileHandler 默认追加模式，绝不用 'w' 覆盖；同一天多次运行追加到同一文件。
- 清理只删本模块按约定命名的旧日志，不动其他文件。
"""

import glob
import logging
import os
import re
from datetime import datetime, timedelta

from 配置 import 配置
from 本地配置 import 加载配置, 取值

默认保留天数 = 30
日志器缓存 = {}


def 获取日志目录():
    return 配置.获取日志目录()


def 获取保留天数():
    try:
        天数 = int(取值(加载配置(), "路径.日志保留天数", 默认保留天数))
        return max(1, 天数)
    except (TypeError, ValueError):
        return 默认保留天数


def 清理旧日志(目录=None, 保留天数=None, 日志器=None):
    """删除超过保留天数的 {名称}_{YYYYMMDD}.log，返回删除的文件名列表。"""
    目录 = 目录 or 获取日志目录()
    保留天数 = 保留天数 if 保留天数 is not None else 获取保留天数()
    截止 = datetime.now() - timedelta(days=保留天数)
    删除 = []
    模式 = re.compile(r"^.+_(\d{8})\.log$")
    for 路径 in glob.glob(os.path.join(目录, "*.log")):
        匹配 = 模式.match(os.path.basename(路径))
        if not 匹配:
            continue
        try:
            日期 = datetime.strptime(匹配.group(1), "%Y%m%d")
        except ValueError:
            continue
        if 日期 < 截止:
            try:
                os.remove(路径)
                删除.append(os.path.basename(路径))
            except OSError:
                pass
    if 删除 and 日志器:
        日志器.info(f"已清理 {len(删除)} 个超过 {保留天数} 天的旧日志: {', '.join(删除[:5])}")
    return 删除


def 获取日志器(名称, 保留天数=None, 级别=logging.INFO, 自动清理=False):
    """返回按天写文件的日志器（同名同配置复用，不重复挂 handler）。

    自动清理默认关闭：避免在任何调用场景（包括测试）意外删除历史日志。
    需要清理时由维护流程显式调用 清理旧日志()。
    """
    键 = (名称, 保留天数)
    if 键 in 日志器缓存:
        return 日志器缓存[键]

    目录 = 获取日志目录()
    日志器 = logging.getLogger(f"PPS.{名称}")
    日志器.setLevel(级别)
    日志器.propagate = False
    for 处理器 in list(日志器.handlers):
        日志器.removeHandler(处理器)
        处理器.close()

    格式 = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    文件名 = f"{名称}_{datetime.now().strftime('%Y%m%d')}.log"
    文件处理器 = logging.FileHandler(os.path.join(目录, 文件名), encoding='utf-8')
    文件处理器.setFormatter(格式)
    日志器.addHandler(文件处理器)

    控制台 = logging.StreamHandler()
    控制台.setFormatter(格式)
    日志器.addHandler(控制台)

    if 自动清理:
        清理旧日志(目录, 保留天数, 日志器)
    日志器缓存[键] = 日志器
    return 日志器


def 当前日志文件(名称):
    """供 UI 提示当前日志文件路径用。"""
    return os.path.join(获取日志目录(), f"{名称}_{datetime.now().strftime('%Y%m%d')}.log")
