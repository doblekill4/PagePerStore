# 日期工具.py
from datetime import datetime, timedelta


class 日期工具:
    @staticmethod
    def 获取今天日期():
        return datetime.now().strftime('%Y-%m-%d')

    @staticmethod
    def 获取明天日期():
        return (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    @staticmethod
    def 获取格式化日期(偏移天数=0):
        return (datetime.now() + timedelta(days=偏移天数)).strftime('%Y.%m.%d')