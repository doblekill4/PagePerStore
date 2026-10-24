# 配置.py - 精简版
#
# 说明：账号、密码、门店ID 等敏感信息不再硬编码在本文件中（避免随代码泄露），
#       改为从「程序同目录」的 config.json 读取。
#       打包成 exe 后，exe 会读取与自身同级的 config.json。
#       配置文件模板见 config.example.json。
import os
from datetime import datetime

from 本地配置 import 加载配置, 取值, 获取程序目录

_本地配置 = 加载配置()


class 配置:
    # 登录信息（必须来自 config.json）
    用户名 = 取值(_本地配置, "平台.用户名", "")
    密码 = 取值(_本地配置, "平台.密码", "")

    # API配置（可在 config.json 的 平台.BASE_URL 覆盖）
    BASE_URL = 取值(_本地配置, "平台.BASE_URL", "https://wxapp.trtjkmall.com")
    LOGIN_API = "/tec/portal/api/manage/user/shopLogin"
    ORDER_API = "/tec/trade_order/manager/order/query"

    # HEADERS
    HEADERS = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'client': 'secms-busi',
        'content-type': 'application/json;charset=UTF-8',
        'origin': 'https://wxapp.trtjkmall.com',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'referer': 'https://wxapp.trtjkmall.com/',
    }

    # 门店ID（必须来自 config.json）
    门店ID = 取值(_本地配置, "平台.门店ID", "")

    # 订单状态
    待发货状态 = 20
    待收货状态 = 50
    取消状态 = 90

    # 页面大小
    页面大小 = 100

    # 日期格式
    日期格式 = '%Y-%m-%d'
    导出日期格式 = '%Y.%m.%d'

    # 日志目录
    @staticmethod
    def 获取日志目录():
        # config.json 可指定；未指定时默认放在程序目录下的「日志」文件夹（便携 exe 友好）
        日志目录 = 取值(_本地配置, "路径.日志目录", "") or os.path.join(获取程序目录(), "日志")
        os.makedirs(日志目录, exist_ok=True)
        return 日志目录

    # 配置自检
    @staticmethod
    def 缺少必要配置():
        """返回缺失的必填配置项列表，空列表表示配置完整"""
        from 本地配置 import 缺少必要配置
        return 缺少必要配置(_本地配置, ["平台.用户名", "平台.密码", "平台.门店ID"])

    # 重新加载配置（首次运行向导写入 config.json 后调用，就地更新类属性）
    @staticmethod
    def 重新加载():
        global _本地配置
        _本地配置 = 加载配置()
        配置.用户名 = 取值(_本地配置, "平台.用户名", "")
        配置.密码 = 取值(_本地配置, "平台.密码", "")
        配置.BASE_URL = 取值(_本地配置, "平台.BASE_URL", "https://wxapp.trtjkmall.com")
        配置.门店ID = 取值(_本地配置, "平台.门店ID", "")
        return 配置.缺少必要配置()

    # 日期转时间戳
    @staticmethod
    def 日期转时间戳(日期字符串):
        try:
            dt = datetime.strptime(日期字符串, '%Y-%m-%d')
            return int(dt.timestamp() * 1000)
        except:
            return None
