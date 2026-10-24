# 本地配置.py - 本地配置读取（不参与版本控制的敏感配置）
#
# 设计目标：
#   1) 账号、密码、邮箱授权码等敏感信息不再写在源码里，避免随代码泄露；
#   2) 打包成 exe 后，把 config.json 放在 exe 同目录即可运行（便携，无需配环境变量）。
#
# 查找顺序：
#   1) 环境变量 PAGEPERSTORE_CONFIG 指定的文件路径
#   2) 程序目录（打包后 = exe 所在目录；源码运行 = 本文件所在目录）下的 config.json
#
import json
import os
import sys

配置文件名 = "config.json"


def 获取程序目录():
    """返回程序所在目录：打包后为 exe 所在目录，源码运行为本文件所在目录"""
    if getattr(sys, 'frozen', False):
        # 打包成 exe 后，sys.executable 指向 exe 本身
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def 获取配置文件路径():
    """定位实际使用的配置文件路径"""
    指定路径 = os.environ.get("PAGEPERSTORE_CONFIG")
    if 指定路径 and os.path.isfile(指定路径):
        return 指定路径

    目录 = 获取程序目录()
    return os.path.join(目录, 配置文件名)


def 加载配置():
    """读取配置文件，返回 dict；文件不存在或格式错误时返回空 dict（不抛异常，避免程序起不来）"""
    路径 = 获取配置文件路径()
    if not os.path.isfile(路径):
        return {}
    try:
        with open(路径, 'r', encoding='utf-8-sig') as f:
            数据 = json.load(f)
        return 数据 if isinstance(数据, dict) else {}
    except Exception:
        return {}


def 取值(配置字典, 键路径, 默认值=None):
    """按 '平台.用户名' 这样的点分路径取值，取不到返回默认值"""
    当前 = 配置字典
    for 段 in str(键路径).split('.'):
        if not isinstance(当前, dict) or 段 not in 当前:
            return 默认值
        当前 = 当前[段]
    return 当前


def 缺少必要配置(配置字典, 必填项):
    """检查必填项是否缺失，返回缺失项列表"""
    缺失 = []
    for 项 in 必填项:
        值 = 取值(配置字典, 项)
        if 值 is None or 值 == '' or 值 == [] or 值 == {}:
            缺失.append(项)
    return 缺失
