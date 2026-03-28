# 模块7：定时任务模块（精简版）- 只保留图形界面
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import webbrowser

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from 任务执行器 import 任务执行器

版本号 = "v2.5"


class 订单调度器GUI:
    def __init__(self):
        self.调度器 = BackgroundScheduler()
        self._强制保持DPI设置()
        self.当前分辨率 = self._获取系统分辨率()
        self.任务执行器 = 任务执行器(self.获取日志器(), self.更新状态)

        try:
            # 修复：放到子线程，不卡GUI
            threading.Thread(target=self._启动_wps服务, daemon=True).start()
        except:
            pass

        self.设置日志()
        self.创建界面()
        self.设置窗口图标()

    def _启动_wps服务(self):
        try:
            from wps_playwright import start_wps_keep_alive
            start_wps_keep_alive()
        except Exception as e:
            print("WPS 启动异常：", e)
    def 设置窗口图标(self):
        try:
            icon_path = "icon.ico"
            if os.path.exists(icon_path):
                self.窗口.iconbitmap(icon_path)
        except:
            pass

    def _强制保持DPI设置(self):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except:
            try:
                import ctypes
                ctypes.windll.user32.SetProcessDPIAware()
            except:
                pass

    def _获取系统分辨率(self):
        try:
            import ctypes
            user32 = ctypes.windll.user32
            宽度 = user32.GetSystemMetrics(0)
            高度 = user32.GetSystemMetrics(1)
            return f"{宽度}x{高度}"
        except:
            return "未知分辨率"

    def 获取日志器(self):
        return self.日志 if hasattr(self, '日志') else logging.getLogger(__name__)

    def 设置日志(self):
        log_dir = r"D:\一店一页"
        os.makedirs(log_dir, exist_ok=True)
        self.日志 = logging.getLogger('订单调度器')
        if not self.日志.handlers:
            self.日志.setLevel(logging.INFO)
            file_handler = logging.FileHandler(os.path.join(log_dir, "订单调度器.log"), encoding='utf-8')
            console_handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            self.日志.addHandler(file_handler)
            self.日志.addHandler(console_handler)

    def 创建界面(self):
        self.窗口 = tk.Tk()
        self.窗口.title(f"订单导出调度器 {版本号}")
        self.窗口.geometry("500x600")
        self.窗口.resizable(False, False)
        self.窗口.minsize(500, 600)
        self.窗口.maxsize(500, 600)

        style = ttk.Style()
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TLabel', background='#f0f0f0', font=('Arial', 10))
        style.configure('TButton', font=('Arial', 10))
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Info.TLabel', font=('Arial', 9), foreground='blue')

        main_frame = ttk.Frame(self.窗口, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(main_frame, text=f"订单导出调度器 {版本号}", style='Header.TLabel')
        title_label.pack(pady=(0, 15))

        分辨率标签 = ttk.Label(main_frame, text=f"当前分辨率: {self.当前分辨率}", style='Info.TLabel')
        分辨率标签.pack(pady=(0, 10))

        time_frame = ttk.LabelFrame(main_frame, text="定时导出次日订单设置", padding="10")
        time_frame.pack(fill=tk.X, pady=(0, 15))

        hour_frame = ttk.Frame(time_frame)
        hour_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(hour_frame, text="小时 (0-23):").pack(side=tk.LEFT, padx=(0, 5))
        self.小时变量 = tk.StringVar(value="17")
        hour_spinbox = ttk.Spinbox(hour_frame, from_=0, to=23, width=8, textvariable=self.小时变量)
        hour_spinbox.pack(side=tk.LEFT)

        minute_frame = ttk.Frame(time_frame)
        minute_frame.pack(fill=tk.X)
        ttk.Label(minute_frame, text="分钟 (0-59):").pack(side=tk.LEFT, padx=(0, 5))
        self.分钟变量 = tk.StringVar(value="00")
        minute_spinbox = ttk.Spinbox(minute_frame, from_=0, to=59, width=8, textvariable=self.分钟变量)
        minute_spinbox.pack(side=tk.LEFT)

        button_frame1 = ttk.Frame(main_frame)
        button_frame1.pack(fill=tk.X, pady=(0, 10))
        self.启动按钮 = ttk.Button(button_frame1, text="启动定时任务", command=self.启动调度器, width=15)
        self.启动按钮.pack(side=tk.LEFT, padx=(0, 10))
        self.停止按钮 = ttk.Button(button_frame1, text="停止定时任务", command=self.停止调度器, state=tk.DISABLED,
                                   width=15)
        self.停止按钮.pack(side=tk.LEFT)

        button_frame2 = ttk.Frame(main_frame)
        button_frame2.pack(fill=tk.X, pady=(0, 10))
        self.导出次日按钮 = ttk.Button(button_frame2, text="导出次日订单",
                                       command=lambda: threading.Thread(target=self._执行导出次日订单,
                                                                        daemon=True).start(),
                                       width=15)
        self.导出次日按钮.pack(side=tk.LEFT, padx=(0, 10))

        self.更新今日按钮 = ttk.Button(button_frame2, text="更新今日订单",
                                       command=lambda: threading.Thread(target=self._执行更新今日订单,
                                                                        daemon=True).start(),
                                       width=15)
        self.更新今日按钮.pack(side=tk.LEFT)

        # 修复：手动检查订单按钮
        button_frame3 = ttk.Frame(main_frame)
        button_frame3.pack(fill=tk.X, pady=(0, 10))
        self.检查订单按钮 = ttk.Button(button_frame3, text="手动检查订单", command=self.手动检查订单, width=15)
        self.检查订单按钮.pack(side=tk.LEFT)

        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        info_text = "管理界面登录账号：01900406 登录密码：Aa123456"
        info_label = ttk.Label(info_frame, text=info_text, style='Info.TLabel')
        info_label.pack()

        status_frame = ttk.LabelFrame(main_frame, text="状态信息", padding="10")
        status_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 0))
        text_frame = ttk.Frame(status_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        self.状态文本 = tk.Text(text_frame, height=12, width=50, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.状态文本.yview)
        self.状态文本.configure(yscrollcommand=scrollbar.set)
        self.状态文本.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.更新状态("就绪，请设置时间并启动定时任务")

    def _执行更新今日订单(self):
        try:
            self._禁用所有按钮()
            self.更新状态("开始更新今日订单...")
            整体成功 = False

            try:
                订单导出成功 = self.任务执行器.执行日期订单导出(使用今日日期=True)
                if 订单导出成功:
                    self.更新状态("开始同步到顺丰表格...")
                    同步成功 = self.任务执行器.执行顺丰同步(是今日订单=True)
                    if 同步成功:
                        self.更新状态("✅ 今日订单已同步到顺丰表格")
                        整体成功 = True
                    else:
                        self.更新状态("❌ 同步到顺丰表格失败")
            except Exception as e:
                self.更新状态(f"❌ 任务执行异常: {e}")
            finally:
                self._启用所有按钮()
            return 整体成功
        except Exception as e:
            self.更新状态(f"❌ 更新今日订单任务失败: {e}")
            self._启用所有按钮()
            return False

    def _执行导出次日订单(self):
        try:
            self._禁用所有按钮()
            self.更新状态("开始导出次日订单...")
            整体成功 = False

            try:
                订单导出成功 = self.任务执行器.执行日期订单导出(使用今日日期=False)
                if 订单导出成功:
                    self.更新状态("开始同步到顺丰表格...")
                    同步成功 = self.任务执行器.执行顺丰同步(是今日订单=False)
                    if 同步成功:
                        self.更新状态("✅ 次日订单已同步到顺丰表格")
                        整体成功 = True
                    else:
                        self.更新状态("❌ 同步到顺丰表格失败")
            except Exception as e:
                self.更新状态(f"❌ 任务执行异常: {e}")
            finally:
                self._启用所有按钮()
            return 整体成功
        except Exception as e:
            self.更新状态(f"❌ 导出次日订单任务失败: {e}")
            self._启用所有按钮()
            return False

    def _禁用所有按钮(self):
        self.导出次日按钮.config(state=tk.DISABLED)
        self.更新今日按钮.config(state=tk.DISABLED)
        self.检查订单按钮.config(state=tk.DISABLED)
        self.启动按钮.config(state=tk.DISABLED)
        self.停止按钮.config(state=tk.DISABLED)

    def _启用所有按钮(self):
        self.导出次日按钮.config(state=tk.NORMAL)
        self.更新今日按钮.config(state=tk.NORMAL)
        self.检查订单按钮.config(state=tk.NORMAL)
        self.启动按钮.config(state=tk.NORMAL)
        self.停止按钮.config(state=tk.NORMAL)

    def 更新状态(self, 消息):
        self.状态文本.config(state=tk.NORMAL)
        self.状态文本.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')} - {消息}\n")
        self.状态文本.see(tk.END)
        self.状态文本.config(state=tk.DISABLED)

    def 手动检查订单(self):
        try:
            self.更新状态("正在打开新平台订单管理页面...")
            url = "https://wxapp.trtjkmall.com/"
            webbrowser.open(url)
            self.更新状态(f"已打开: {url}")
        except Exception as e:
            self.更新状态(f"打开失败: {e}")

    def 启动调度器(self):
        try:
            小时 = self.小时变量.get()
            分钟 = self.分钟变量.get()
            if not 小时.isdigit() or not 分钟.isdigit():
                messagebox.showerror("错误", "请输入有效数字")
                return
            小时 = int(小时)
            分钟 = int(分钟)
            if 小时 < 0 or 小时 > 23 or 分钟 < 0 or 分钟 > 59:
                messagebox.showerror("错误", "时间范围错误")
                return

            self.调度器.remove_all_jobs()
            self.调度器.add_job(
                self.任务执行器.执行导出任务,
                trigger=CronTrigger(hour=小时, minute=分钟),
                id='每日订单导出',
                misfire_grace_time=300
            )
            self.调度器.start()
            self.更新状态(f"已启动：每日 {小时:02d}:{分钟:02d} 执行")
            self.启动按钮.config(state=tk.DISABLED)
            self.停止按钮.config(state=tk.NORMAL)
        except Exception as e:
            self.更新状态(f"启动失败: {e}")

    def 停止调度器(self):
        try:
            self.调度器.pause()
            self.更新状态("定时任务已停止")
            self.启动按钮.config(state=tk.NORMAL)
            self.停止按钮.config(state=tk.DISABLED)
        except:
            pass

    def 退出程序(self):
        try:
            from wps_playwright import stop_wps_keep_alive
            stop_wps_keep_alive()
        except:
            pass
        try:
            if self.调度器.running:
                self.调度器.shutdown()
        except:
            pass
        self.窗口.destroy()

    def 运行(self):
        self.窗口.protocol("WM_DELETE_WINDOW", self.退出程序)
        self.窗口.mainloop()


def 主函数():
    调度器 = 订单调度器GUI()
    调度器.运行()


if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    try:
        主函数()
    except Exception as e:
        import traceback

        with open("启动错误.log", "w", encoding="utf-8") as f:
            f.write(f"{e}\n{traceback.format_exc()}")