# -*- coding: utf-8 -*-
"""统一日志模块测试：按天分文件、追加不覆盖、保留近 N 天。"""

import logging
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import 日志管理


class 日志管理测试(unittest.TestCase):

    def test_按天命名与追加不覆盖(self):
        with tempfile.TemporaryDirectory() as 目录:
            # 同时 patch 目录与保留天数，确保清理绝不触及真实日志目录
            with patch.object(日志管理, "获取日志目录", return_value=目录), \
                 patch.object(日志管理, "获取保留天数", return_value=365), \
                 patch.object(日志管理, "日志器缓存", {}):
                日志器 = 日志管理.获取日志器("测试按天")
                日志器.info("第一条")
                日志器.info("第二条")
                文件 = Path(目录) / f"测试按天_{datetime.now().strftime('%Y%m%d')}.log"
                内容 = 文件.read_text(encoding="utf-8")
                for 处理器 in list(日志器.handlers):
                    日志器.removeHandler(处理器)
                    处理器.close()
        self.assertIn("第一条", 内容)
        self.assertIn("第二条", 内容)
        self.assertLess(内容.index("第一条"), 内容.index("第二条"))

    def test_清理旧日志只删过期文件(self):
        with tempfile.TemporaryDirectory() as 目录:
            今天 = datetime.now()
            近期 = 今天.strftime("%Y%m%d")
            过期 = (今天 - timedelta(days=40)).strftime("%Y%m%d")
            保留文件 = Path(目录) / f"订单调度器_{近期}.log"
            删除文件 = Path(目录) / f"订单调度器_{过期}.log"
            其他文件 = Path(目录) / "readme.txt"
            for f in (保留文件, 删除文件, 其他文件):
                f.write_text("x", encoding="utf-8")
            删除列表 = 日志管理.清理旧日志(目录, 保留天数=30)
            保留存在 = 保留文件.exists()
            删除存在 = 删除文件.exists()
            其他存在 = 其他文件.exists()
        self.assertIn(删除文件.name, 删除列表)
        self.assertTrue(保留存在)
        self.assertTrue(删除存在 is False)
        self.assertTrue(其他存在)

    def test_保留天数来自配置(self):
        with patch.object(日志管理, "加载配置", return_value={"路径": {"日志保留天数": 7}}):
            self.assertEqual(日志管理.获取保留天数(), 7)
        with patch.object(日志管理, "加载配置", return_value={}):
            self.assertEqual(日志管理.获取保留天数(), 30)


if __name__ == "__main__":
    unittest.main(verbosity=2)
