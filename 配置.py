# 配置.py - 根据新平台信息更新
import os
from datetime import datetime


class 配置:
    # 登录信息
    用户名 = "01900406"
    密码 = "Aa123456"

    # API配置 - 根据网络请求更新
    BASE_URL = "https://wxapp.trtjkmall.com"
    LOGIN_API = "/tec/portal/api/manage/user/shopLogin"  # 登录端点
    ORDER_API = "/tec/trade_order/manager/order/query"  # 订单查询端点

    # 根据网络请求更新HEADERS
    HEADERS = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'client': 'secms-busi',
        'content-type': 'application/json;charset=UTF-8',
        'origin': 'https://wxapp.trtjkmall.com',
        'priority': 'u=1, i',
        'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Microsoft Edge";v="144"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0',
        'referer': 'https://wxapp.trtjkmall.com/',
    }

    # 门店ID - 注意：从请求看到shopId是 "3845488196700708928"
    门店ID = "3845488196700708928"  # 新平台零号店的ID

    # 订单状态配置（保持和旧平台一致）
    待发货状态 = 20
    待收货状态 = 50
    取消状态 = 90

    # 页面大小
    页面大小 = 100

    # 日期格式
    日期格式 = '%Y-%m-%d'
    导出日期格式 = '%Y.%m.%d'

    # 文件路径配置
    @staticmethod
    def 获取日志目录():
        日志目录 = r"D:\一店一页\日志"
        os.makedirs(日志目录, exist_ok=True)
        return 日志目录

    @staticmethod
    def 获取今日日志文件():
        日志目录 = 配置.获取日志目录()
        今日日期 = datetime.now().strftime('%Y%m%d')
        return os.path.join(日志目录, f"订单导出_{今日日期}.log")

    # 顺丰表格配置
    顺丰表格名称 = "顺丰-零号店配送订单"

    # 图片路径
    @staticmethod
    def 获取图片路径(图片文件名):
        当前目录 = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(当前目录, 图片文件名)

    @staticmethod
    def 日期转时间戳(日期字符串):
        """将日期字符串转换为时间戳（毫秒）"""
        try:
            dt = datetime.strptime(日期字符串, '%Y-%m-%d')
            # 转换为时间戳（毫秒）
            时间戳 = int(dt.timestamp() * 1000)
            return 时间戳
        except:
            return None