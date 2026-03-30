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
        """WPS在线表格同步（修复版：正确解析TSV）"""
        try:
            self._更新状态("开始WPS在线表格后台同步...")
            self._更新状态(f"订单类型: {'今日订单' if 是今日订单 else '次日订单'}")

            import win32clipboard
            win32clipboard.OpenClipboard()
            clipboard_data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()

            # ✅ 修复点1：定义包含 J列 和 L列 的完整表头
            # 顺序必须与主程序导出的顺序完全一致 (A 到 L)
            col_order = [
                '订单序号',  # A
                '商品名称',  # B
                '配送方式',  # C
                '配送或自提时间',  # D
                '收货人姓名',  # E
                '收货人手机号',  # F
                '收货地址',  # G
                '购买人手机号',  # H
                '客户留言',  # I
                '烘焙',  # J (新增)
                '门店签字',  # K
                '手机号'  # L (新增)
            ]

            # ✅ 修复点2：使用 pandas 正确解析 TSV
            # pandas 会自动处理被双引号包裹的换行符（即商品名称里的换行）
            import pandas as pd
            import io

            # 读取剪贴板数据
            # sep='\t': 制表符分隔
            # header=None: 没有表头
            # quoting=1: 识别引号内的内容为一个整体
            df = pd.read_csv(
                io.StringIO(clipboard_data),
                sep='\t',
                header=None,
                quoting=1,
                dtype=str  # 全部读为字符串，防止手机号变科学计数法
            )

            # 填充空值为 空字符串
            df = df.fillna('')

            # ✅ 修复点3：确保列数匹配
            # 如果实际列数多于预期，只取前 len(col_order) 列
            # 如果实际列数少于预期，后面补空列
            if len(df.columns) > len(col_order):
                df = df.iloc[:, :len(col_order)]

            # 重命名列
            df.columns = col_order[:len(df.columns)]

            # 转换为字典列表
            data_list = df.to_dict('records')

            self._更新状态(f"✅ 成功解析 {len(data_list)} 条订单数据")

            # ✅ 修复点4：传入 data_list
            from wps_playwright import wps_append_data
            # 使用旧版粘贴行为（一次性将 TSV 放入剪贴板并 Ctrl+V）以保持与旧客户端一致的粘贴效果
            # Use standard Ctrl+V for legacy paste (many web editors ignore Ctrl+Shift+V)
            sync_success = wps_append_data(data_list, is_today_order=是今日订单, use_legacy_paste=True, paste_as_values=False)

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