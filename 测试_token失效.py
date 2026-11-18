# -*- coding: utf-8 -*-
"""token 失效行为测试：验证失败时不会自动拉起浏览器重登，而是明确报错/发邮件。

运行：python 测试_token失效.py
"""

import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

import kdocs_auth
import wps_kdocs


class Token失效测试(unittest.TestCase):

    def test_write_failure_does_not_trigger_login(self):
        """写入链路遇到 400006 时只返回失败，不调用 auth login。"""
        配置 = wps_kdocs.读配置()
        配置["file_id"] = "fake-file-id"
        响应 = {"code": 400006, "message": "token expired"}
        with patch.object(wps_kdocs, "读配置", return_value=配置), \
             patch.object(wps_kdocs, "_cli", return_value=响应), \
             patch.object(kdocs_auth, "检查并告警", return_value=(True, "测试跳过")), \
             patch.object(wps_kdocs.subprocess, "run") as 模拟执行:
            结果 = wps_kdocs.追加订单(tsv_text="商品\t日期\n测试\t2026-11-16", dry_run=True)
        self.assertFalse(结果["ok"])
        for 调用 in 模拟执行.call_args_list:
            命令 = 调用.args[0] if 调用.args else []
            self.assertNotIn("login", 命令)

    def test_check_alert_does_not_auto_login(self):
        """认证失效时发邮件报警、立即重置计数，但绝不自动拉起浏览器重登。"""
        with tempfile.TemporaryDirectory() as 目录:
            元数据 = Path(目录) / "meta.json"
            元数据.write_text(json.dumps({
                "issued_at": time.time(), "expires_at": time.time() + 86400,
                "expires_in": 31536000, "issued_date": "2026-11-16 00:00:00",
            }, ensure_ascii=False), encoding="utf-8")
            with patch.object(kdocs_auth, "元数据路径", 元数据), \
                 patch.object(kdocs_auth, "认证状态", return_value=(False, "bad token")), \
                 patch.object(kdocs_auth, "登录") as 模拟登录, \
                 patch.object(kdocs_auth, "_发邮件", return_value=True) as 模拟邮件:
                可用, 说明 = kdocs_auth.检查并告警(发邮件=True)
                数据 = json.loads(元数据.read_text(encoding="utf-8"))
        self.assertFalse(可用)
        self.assertIn("重新登录", 说明)
        self.assertIn("计数已重置", 说明)
        self.assertNotIn("expires_at", 数据)
        self.assertIn("invalidated_at", 数据)
        模拟登录.assert_not_called()
        模拟邮件.assert_called_once()

    def test_expiry_warning_once_per_day(self):
        """临期（<7 天）只记日志、不发邮件；每天只写一次标记。"""
        with tempfile.TemporaryDirectory() as 目录:
            元数据 = Path(目录) / "meta.json"
            数据 = {
                "issued_at": time.time() - (360 * 86400),
                "expires_at": time.time() + (3 * 86400),
                "expires_in": 31536000,
                "issued_date": "2026-11-16 00:00:00",
            }
            元数据.write_text(json.dumps(数据, ensure_ascii=False), encoding="utf-8")
            with patch.object(kdocs_auth, "元数据路径", 元数据), \
                 patch.object(kdocs_auth, "认证状态", return_value=(True, "ok")), \
                 patch.object(kdocs_auth, "_发邮件", return_value=True) as 模拟邮件:
                可用1, 说明1 = kdocs_auth.检查并告警(发邮件=True)
                可用2, 说明2 = kdocs_auth.检查并告警(发邮件=True)
        self.assertTrue(可用1)
        self.assertTrue(可用2)
        self.assertIn("到期预警", 说明1)
        self.assertIn("仅日志", 说明1)
        self.assertIn("3.0", 说明1)
        模拟邮件.assert_not_called()

    def test_cli_400006_resets_counter(self):
        """服务端提前失效（400006）时，旧有效期计数立即作废。"""
        with tempfile.TemporaryDirectory() as 目录:
            元数据 = Path(目录) / "meta.json"
            元数据.write_text(json.dumps({
                "issued_at": time.time(), "expires_at": time.time() + (300 * 86400),
                "expires_in": 31536000, "issued_date": "2026-11-16 00:00:00",
            }, ensure_ascii=False), encoding="utf-8")
            假响应 = wps_kdocs.subprocess.CompletedProcess(
                [], 0, '{"code":400006,"message":"token expired"}')
            with patch.object(kdocs_auth, "元数据路径", 元数据), \
                 patch.object(wps_kdocs.subprocess, "run", return_value=假响应):
                响应 = wps_kdocs._cli(wps_kdocs.读配置(), "drive", "search-files", {"keyword": "x"})
            数据 = json.loads(元数据.read_text(encoding="utf-8"))
        self.assertEqual(响应["code"], 400006)
        self.assertNotIn("expires_at", 数据)
        self.assertIn("400006", 数据["invalid_reason"])

    def test_manual_check_launches_login(self):
        """手动触发：失效时拉起登录、不发邮件，成功后复查通过。"""
        with tempfile.TemporaryDirectory() as 目录:
            元数据 = Path(目录) / "meta.json"
            元数据.write_text(json.dumps({
                "issued_at": time.time(), "expires_at": time.time() + 86400,
                "expires_in": 31536000, "issued_date": "2026-11-16 00:00:00",
            }, ensure_ascii=False), encoding="utf-8")
            with patch.object(kdocs_auth, "元数据路径", 元数据), \
                 patch.object(kdocs_auth, "认证状态", side_effect=[(False, "bad"), (True, "ok")]), \
                 patch.object(kdocs_auth, "登录", return_value=(True, "登录成功")) as 模拟登录, \
                 patch.object(kdocs_auth, "_发邮件") as 模拟邮件:
                可用, 说明 = kdocs_auth.检查并告警(发邮件=False, 失败时登录=True)
        self.assertTrue(可用)
        self.assertIn("已自动重新登录", 说明)
        模拟登录.assert_called_once()
        模拟邮件.assert_not_called()

    def test_wps_append_data_exposes_failure_reason(self):
        """写入失败时兼容入口把详细 message 留供 UI 状态栏读取。"""
        原因 = "kdocs-cli 登录态失效，需要重新登录；旧有效期计数已重置"
        with patch.object(wps_kdocs, "追加订单", return_value={"ok": False, "message": 原因}):
            结果 = wps_kdocs.wps_append_data(df=None)
        self.assertFalse(结果)
        self.assertEqual(wps_kdocs.最后失败原因, 原因)

    def test_wps_append_data_forwards_manual_flag(self):
        """兼容入口把是否手动透传到写入层。"""
        with patch.object(wps_kdocs, "追加订单", return_value={"ok": True, "message": "ok"}) as 模拟追加:
            wps_kdocs.wps_append_data(df=None, 是否手动=True)
            手动参数 = 模拟追加.call_args.kwargs["是否手动"]
            wps_kdocs.wps_append_data(df=None)
            定时参数 = 模拟追加.call_args.kwargs["是否手动"]
        self.assertTrue(手动参数)
        self.assertFalse(定时参数)

    def test_scheduled_flow_passes_flag_to_kdocs(self):
        """统一流程把是否手动传下去：手动 True、定时 False。"""
        import 主程序 as 主程序模块
        import 定时任务 as 定时任务模块

        class 假界面:
            def __init__(self):
                self.邮件通知器 = None
                self.状态 = []
            def _禁用所有按钮(self): pass
            def _启用所有按钮(self): pass
            def 更新状态(self, 文本): self.状态.append(文本)
            def 获取日志器(self): return None

        假df = object()
        假主程序 = type("假主程序", (), {"执行": lambda self, **kw: {"df": 假df}})()
        for 手动, 期望 in ((True, True), (False, False)):
            界面 = 假界面()
            with patch.object(主程序模块, "主程序", return_value=假主程序), \
                 patch.object(wps_kdocs, "配置就绪", return_value=True), \
                 patch.object(wps_kdocs, "wps_append_data", return_value=True) as 模拟追加:
                定时任务模块.订单调度器GUI._执行完整流程(界面, 是否手动=手动)
            self.assertEqual(模拟追加.call_args.kwargs["是否手动"], 期望)

    def test_ui_status_shows_failure_reason(self):
        """kdocs 写入失败时，UI 状态栏包含具体原因而不是笼统的「同步失败」。"""
        import 主程序 as 主程序模块
        import 定时任务 as 定时任务模块

        class 假界面:
            def __init__(self):
                self.邮件通知器 = None
                self.状态 = []
            def _禁用所有按钮(self): pass
            def _启用所有按钮(self): pass
            def 更新状态(self, 文本): self.状态.append(文本)
            def 获取日志器(self): return None

        原因 = "kdocs-cli 登录态失效，需要重新登录；旧有效期计数已重置"
        假df = object()
        假主程序 = type("假主程序", (), {"执行": lambda self, **kw: {"df": 假df}})()

        def 假追加(**kw):
            wps_kdocs.最后失败原因 = 原因
            return False

        with patch.object(主程序模块, "主程序", return_value=假主程序), \
             patch.object(wps_kdocs, "配置就绪", return_value=True), \
             patch.object(wps_kdocs, "wps_append_data", side_effect=假追加):
            界面 = 假界面()
            成功 = 定时任务模块.订单调度器GUI._执行完整流程(界面, 是否手动=True)
        self.assertFalse(成功)
        self.assertTrue(any(原因 in 文本 and "同步失败" in 文本 for 文本 in 界面.状态),
                        f"状态栏未显示失败原因: {界面.状态}")

    def test_ui_status_shows_export_failure_reason(self):
        """通信失败导致导出失败时，状态栏显示主程序带出的具体原因并发邮件。"""
        import 主程序 as 主程序模块
        import 定时任务 as 定时任务模块

        class 假邮件通知器:
            def __init__(self): self.发送 = []
            def 发送失败通知(self, 文本): self.发送.append(文本)
        class 假界面:
            def __init__(self):
                self.邮件通知器 = 假邮件通知器()
                self.状态 = []
            def _禁用所有按钮(self): pass
            def _启用所有按钮(self): pass
            def 更新状态(self, 文本): self.状态.append(文本)
            def 获取日志器(self): return None

        原因 = "订单查询通信失败（API 请求失败/重试耗尽），未获取到订单数据"
        假主程序 = type("假主程序", (), {
            "执行": lambda self, **kw: None,
            "最后失败原因": 原因,
        })()
        with patch.object(主程序模块, "主程序", return_value=假主程序), \
             patch.object(wps_kdocs, "配置就绪", return_value=True):
            界面 = 假界面()
            成功 = 定时任务模块.订单调度器GUI._执行完整流程(界面, 是否手动=False)
        self.assertFalse(成功)
        self.assertTrue(any(原因 in 文本 and "导出失败" in 文本 for 文本 in 界面.状态),
                        f"状态栏未显示导出失败原因: {界面.状态}")
        self.assertEqual(len(界面.邮件通知器.发送), 1, "通信失败应发一封邮件")

    def test_no_orders_normal_does_not_send_mail(self):
        """通信正常但当日 0 单：不算失败、不发邮件、跳过同步。"""
        import 主程序 as 主程序模块
        import 定时任务 as 定时任务模块

        class 假邮件通知器:
            def __init__(self): self.发送 = []
            def 发送失败通知(self, 文本): self.发送.append(文本)
        class 假界面:
            def __init__(self):
                self.邮件通知器 = 假邮件通知器()
                self.状态 = []
            def _禁用所有按钮(self): pass
            def _启用所有按钮(self): pass
            def 更新状态(self, 文本): self.状态.append(文本)
            def 获取日志器(self): return None

        空单结果 = {"空单正常": True, "orders": [], "df": None}
        假主程序 = type("假主程序", (), {"执行": lambda self, **kw: 空单结果})()
        with patch.object(主程序模块, "主程序", return_value=假主程序), \
             patch.object(wps_kdocs, "配置就绪", return_value=True), \
             patch.object(wps_kdocs, "wps_append_data") as 模拟追加:
            界面 = 假界面()
            成功 = 定时任务模块.订单调度器GUI._执行完整流程(界面, 是否手动=False)
        self.assertTrue(成功, "正常 0 单不算失败")
        self.assertEqual(len(界面.邮件通知器.发送), 0, "正常 0 单不应发邮件")
        模拟追加.assert_not_called()
        self.assertTrue(any("无订单" in 文本 and "通信正常" in 文本 for 文本 in 界面.状态),
                        f"状态栏未提示无订单: {界面.状态}")

    def test_main_program_zero_orders_vs_comm_failure(self):
        """主程序：通信正常 0 单返回空单正常；通信失败返回 None 并带原因。"""
        import 主程序 as 主程序模块

        def 造实例(通信正常):
            实例 = 主程序模块.主程序(日志器=Mock())
            实例.登录系统 = Mock(return_value=True)
            实例.获取订单数据 = Mock(return_value=[])
            实例.订单查询通信正常 = 通信正常
            return 实例

        正常实例 = 造实例(True)
        结果 = 正常实例.执行()
        self.assertTrue(结果.get('空单正常'))
        self.assertEqual(正常实例.最后失败原因, "")

        失败实例 = 造实例(False)
        结果2 = 失败实例.执行()
        self.assertIsNone(结果2)
        self.assertIn("通信失败", 失败实例.最后失败原因)

    def test_relogin_restores_counter(self):
        """重登记录新有效期后，失效标记清除、计数重新开始。"""
        with tempfile.TemporaryDirectory() as 目录:
            元数据 = Path(目录) / "meta.json"
            with patch.object(kdocs_auth, "元数据路径", 元数据):
                kdocs_auth.重置有效期("测试失效")
                self.assertIsNone(kdocs_auth.剩余有效期秒())
                新数据 = kdocs_auth.记录有效期(7200)
                剩余 = kdocs_auth.剩余有效期秒()
        self.assertNotIn("invalidated_at", 新数据)
        self.assertNotIn("invalid_reason", 新数据)
        self.assertAlmostEqual(剩余, 7200, delta=5)

    def test_all_cli_calls_hide_console_window(self):
        """所有 kdocs-cli 子进程调用都带隐藏窗口标志，避免运行时闪出命令提示符。"""
        import subprocess
        import kdocs_auth
        import wps_kdocs

        期望标志 = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.assertEqual(wps_kdocs._无窗口标志, 期望标志)
        self.assertEqual(kdocs_auth._无窗口标志, 期望标志)

        # wps_kdocs._cli
        配置 = wps_kdocs.读配置()
        with patch.object(wps_kdocs, "_cli路径", return_value="fake-cli.exe"), \
             patch.object(wps_kdocs.subprocess, "run", return_value=Mock(
                 returncode=0, stdout='{"code":0}', stderr="")) as 模拟运行:
            wps_kdocs._cli(配置, "drive", "search-files")
        self.assertEqual(模拟运行.call_args.kwargs.get("creationflags"), 期望标志)

        # kdocs_auth.认证状态
        with patch.object(kdocs_auth, "cli路径", return_value="fake-cli.exe"), \
             patch.object(kdocs_auth.subprocess, "run", return_value=Mock(
                 returncode=0, stdout='{"authenticated":true}', stderr="")) as 模拟运行:
            kdocs_auth.认证状态()
        self.assertEqual(模拟运行.call_args.kwargs.get("creationflags"), 期望标志)

        # kdocs_auth._写入密钥链
        with patch.object(kdocs_auth, "cli路径", return_value="fake-cli.exe"), \
             patch.object(kdocs_auth.subprocess, "run", return_value=Mock(
                 returncode=0, stdout="", stderr="")) as 模拟运行:
            kdocs_auth._写入密钥链("fake-token")
        self.assertEqual(模拟运行.call_args.kwargs.get("creationflags"), 期望标志)


if __name__ == "__main__":
    unittest.main(verbosity=2)
