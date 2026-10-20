# 配置.py - 精简版
import os
from datetime import datetime


class 配置:
    # 登录信息
    用户名 = "01900406"
    密码 = "Aa123456"

    # API配置
    BASE_URL = "https://wxapp.trtjkmall.com"
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

    # 门店ID
    门店ID = "3845488196700708928"

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
        日志目录 = r"D:\一店一页\日志"
        os.makedirs(日志目录, exist_ok=True)
        return 日志目录

    # 日期转时间戳
    @staticmethod
    def 日期转时间戳(日期字符串):
        try:
            dt = datetime.strptime(日期字符串, '%Y-%m-%d')
            return int(dt.timestamp() * 1000)
        except:
            return None