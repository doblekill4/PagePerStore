# 模块8：任务执行器模块
# 接口定义：
#   功能: 执行具体的订单导出和顺丰同步任务
#   依赖: 主程序, 顺丰, 锁定管理
#   输入: 日志记录器
#   输出: 执行状态和日志信息

import os  # 添加这一行
import traceback  # 添加这一行


class 任务执行器:
    def __init__(self, 日志, 锁定管理器, 状态回调=None):
        self.日志 = 日志
        self.锁定管理器 = 锁定管理器
        self.状态回调 = 状态回调  # 添加状态回调
        self._已记录的消息 = set()  # 添加去重机制

    def _更新状态(self, 消息):
        """更新状态到GUI和控制台 - 避免重复记录"""
        # 优先更新GUI
        if self.状态回调:
            self.状态回调(消息)

        # 避免重复记录到日志
        if not hasattr(self, '_last_message') or self._last_message != 消息:
            self.日志.info(消息)
            self._last_message = 消息

    def 执行导出任务(self):
        """执行完整的订单导出任务 - 确保包含清理"""
        try:
            # 开始锁定
            self._更新状态("开始锁定系统...")
            if not self.锁定管理器.开始锁定():
                self._更新状态("❌ 锁定失败，任务终止")
                return False

            self._更新状态("开始执行每日订单导出")

            # 直接调用主程序 - 获取订单数据
            self._更新状态("正在执行主程序...")
            from 主程序 import main
            result = main()  # 获取主程序返回的数据

            if result:
                self._更新状态("订单导出任务完成")

                # 自动执行顺丰同步
                self._更新状态("准备同步到顺丰表格...")
                self.执行顺丰同步()

                self._更新状态("定时任务执行完成")
                return True
            else:
                self._更新状态("❌ 订单导出失败")
                return False

        except Exception as e:
            self._更新状态(f"❌ 导出任务执行失败: {e}")
            return False
        finally:
            self.锁定管理器.结束锁定()
            self._更新状态("系统已解锁")

    # 任务执行器.py - 最终修改版本
    # 简化任务执行器.py中的执行日期订单导出方法：

    def 执行日期订单导出(self, 使用今日日期=False):
        """执行指定日期的订单导出任务 - 不生成文件，只处理数据到剪贴板"""
        try:
            self._更新状态("开始执行指定日期订单导出")

            from 配置 import 配置
            import requests
            from 认证管理 import AuthManager
            from 订单获取 import OrderFetcher
            from 数据处理 import DataProcessor

            session = requests.Session()
            base_url = 配置.BASE_URL
            headers = 配置.HEADERS.copy()

            auth_manager = AuthManager(session, base_url, headers)
            order_fetcher = OrderFetcher(session, base_url, headers, auth_manager, auth_manager.logger)
            data_processor = DataProcessor(auth_manager.logger)

            if auth_manager.login(配置.用户名, 配置.密码):
                self._更新状态("登录成功")

                if 使用今日日期:
                    查询日期 = auth_manager.get_today_date()
                    日期标签 = "今日"
                else:
                    查询日期 = auth_manager.get_tomorrow_date()
                    日期标签 = "次日"

                self._更新状态(f"正在获取{日期标签}订单数据，日期: {查询日期}")

                # 获取配送订单
                self._更新状态(f"获取{日期标签}配送订单...")
                配送订单 = order_fetcher.get_delivery_orders(
                    status=[20, 50],  # 待发货和待收货
                    delivery_date=查询日期
                )

                # 获取自提订单
                self._更新状态(f"获取{日期标签}自提订单...")
                自提订单 = order_fetcher.get_pickup_orders(
                    status=[20, 50],
                    pickup_date=查询日期
                )

                # 简单合并
                all_orders = []
                if 配送订单:
                    all_orders.extend(配送订单)
                if 自提订单:
                    all_orders.extend(自提订单)

                self._更新状态(
                    f"获取结果：{len(配送订单 or [])}条配送订单 + {len(自提订单 or [])}条自提订单 = {len(all_orders)}条总订单")

                if not all_orders:
                    self._更新状态(f"❌ 未获取到{日期标签}订单数据")
                    return False

                self._更新状态(f"成功获取 {len(all_orders)} 条{日期标签}订单数据")

                # 处理数据
                self._更新状态("正在处理订单数据...")
                processed_data = data_processor.process_orders_for_export(all_orders)
                df = data_processor.create_dataframe(processed_data)

                # 将数据复制到剪贴板
                self._更新状态(f"正在准备剪贴板数据用于顺丰同步...")
                if self._复制数据到剪贴板_无表头(df):
                    self._更新状态(f"✅ {日期标签}订单数据已准备就绪")
                    self._更新状态(f"已复制 {len(df)} 行数据到剪贴板（不含表头）")
                    return True
                else:
                    self._更新状态(f"❌ 剪贴板数据准备失败")
                    return False
            else:
                self._更新状态("❌ 登录失败")
                return False

        except Exception as e:
            self._更新状态(f"❌ 指定日期订单导出失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        # 重要：移除 finally 块中的解锁代码，由调用方统一管理锁定

    # 在 任务执行器.py 的 执行顺丰同步 方法中修改：
    def 执行顺丰同步(self, 是今日订单=True):
        """执行顺丰表格同步 - 在同步成功后显示提示"""
        try:
            self._更新状态("开始顺丰表格同步...")

            # 创建同步器
            from 顺丰 import 顺丰同步器

            def 状态回调(消息):
                self._更新状态(消息)

            同步器 = 顺丰同步器(logger=None, 状态回调=状态回调, 是今日订单=是今日订单)

            # 执行同步 - 这里只需要调用一次
            success = 同步器._WPS自动化同步()

            if success:
                self._更新状态("✅ 顺丰表格同步完成")
                # 关键：在这里调用显示提示的方法
                self._显示解锁成功提示()
                return True
            else:
                self._更新状态("❌ 顺丰表格同步失败")
                return False

        except Exception as e:
            self._更新状态(f"❌ 同步任务执行失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _显示解锁成功提示(self):
        """显示解锁成功的提示框"""
        try:
            import tkinter as tk
            from tkinter import messagebox
            import threading

            def 显示消息框():
                root = tk.Tk()
                root.withdraw()
                root.attributes('-topmost', True)

                messagebox.showinfo(
                    "任务完成",
                    "✅ 订单数据已同步到顺丰表格\n"
                    "✅ 图片已复制到剪贴板\n"
                    "✅ 系统已解锁\n\n"
                    "可以将图片粘贴到微信发送\n"
                    "点击确定关闭"
                )
                root.destroy()

            提示线程 = threading.Thread(target=显示消息框, daemon=True)
            提示线程.start()

            self._更新状态("✅ 已显示完成提示框")

        except Exception as e:
            self._更新状态(f"显示提示框失败: {e}")

    def _复制数据到剪贴板_无表头(self, df):
        """将DataFrame数据复制到剪贴板（不含表头）"""
        try:
            import win32clipboard
            import io

            # 使用StringIO创建TSV格式的文本（不含表头）
            output = io.StringIO()

            # 关键：index=False, header=False - 不包含表头和索引
            df.to_csv(output, index=False, sep='\t', header=False)
            纯数据文本 = output.getvalue()

            # 复制到剪贴板
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(纯数据文本, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()

            self._更新状态(f"✅ 已复制 {len(df)} 行数据到剪贴板（不含表头）")
            self._更新状态(f"数据大小: {len(纯数据文本)} 字符")

            # 验证剪贴板内容
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                    剪贴板内容 = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                    行数 = 剪贴板内容.count('\n')
                    self._更新状态(f"验证: 剪贴板中有 {行数} 行数据")
            finally:
                win32clipboard.CloseClipboard()

            return True

        except Exception as e:
            self._更新状态(f"❌ 复制数据到剪贴板失败: {e}")
            return False