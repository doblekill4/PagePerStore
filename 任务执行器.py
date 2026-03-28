# 模块8：任务执行器模块 - 正式生产版
import os
import traceback
from wps_playwright import wps_append_data


class 任务执行器:
    def __init__(self, 日志, 状态回调=None):
        self.日志 = 日志
        self.状态回调 = 状态回调
        self._last_message = ""

    def _更新状态(self, 消息):
        """更新状态到GUI和控制台"""
        if self.状态回调 and self._last_message != 消息:
            self.状态回调(消息)
        if self._last_message != 消息:
            self.日志.info(消息)
            self._last_message = 消息

    def 执行导出任务(self):
        """定时任务：执行完整订单导出"""
        try:
            self._更新状态("开始执行每日订单导出")
            from 主程序 import main
            result = main(获取次日=True)
            if result:
                self._更新状态("订单导出任务完成")
                self.执行顺丰同步(是今日订单=False)
                self._更新状态("定时任务执行完成")
                return True
            else:
                self._更新状态("❌ 订单导出失败")
                return False
        except Exception as e:
            self._更新状态(f"❌ 导出任务执行失败: {e}")
            return False

    def 执行日期订单导出(self, 使用今日日期=False):
        """GUI按钮核心：导出今日/次日订单（正式版）"""
        try:
            self._更新状态("开始执行指定日期订单导出")
            from 主程序 import main

            result = main(获取次日=not 使用今日日期)

            if result and result.get('df') is not None:
                日期标签 = "今日" if 使用今日日期 else "次日"
                self._更新状态(f"✅ {日期标签}订单数据已准备就绪")
                return True
            else:
                self._更新状态(f"❌ 未获取到订单数据")
                return False

        except Exception as e:
            self._更新状态(f"❌ 指定日期订单导出失败: {e}")
            traceback.print_exc()
            return False

    def 执行顺丰同步(self, 是今日订单=True):
        """WPS在线表格同步（正式版）"""
        try:
            self._更新状态("开始WPS在线表格后台同步...")
            self._更新状态(f"订单类型: {'今日订单' if 是今日订单 else '次日订单'}")

            import win32clipboard
            win32clipboard.OpenClipboard()
            clipboard_data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()

            data_lines = [line.strip() for line in clipboard_data.split('\n') if line.strip()]
            col_order = [
                '订单序号', '商品名称', '配送方式', '配送或自提时间',
                '收货人姓名', '收货人手机号', '收货地址', '购买人手机号',
                '客户留言', '门店签字', '取货人签字'
            ]
            data_list = [dict(zip(col_order, line.split('\t'))) for line in data_lines]

            self._更新状态(f"✅ 成功读取 {len(data_list)} 条订单数据")
            sync_success = wps_append_data(data_list, is_today_order=是今日订单)

            if sync_success:
                self._更新状态("✅ WPS在线表格同步完成")
                self._显示完成提示()
                return True
            else:
                self._更新状态("❌ WPS同步失败")
                return False
        except Exception as e:
            self._更新状态(f"❌ 同步任务执行失败: {e}")
            self.日志.error(f"同步失败详情: {e}", exc_info=True)
            return False

    def _显示完成提示(self):
        """正式版提示框"""
        try:
            import tkinter as tk
            from tkinter import messagebox
            import threading
            def 显示消息框():
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)
                messagebox.showinfo("任务完成", "✅ 订单数据已同步到顺丰表格")
                root.destroy()

            threading.Thread(target=显示消息框, daemon=True).start()
        except:
            pass