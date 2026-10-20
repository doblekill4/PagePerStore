# 模块7：定时任务模块（新版 - 每小时运行，智能判断）
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
from 邮件通知 import 邮件通知器  # 新增

版本号 = "v3.0.2"


class 订单调度器GUI:
    def __init__(self):
        self.调度器 = BackgroundScheduler()
        self._强制保持DPI设置()
        self.当前分辨率 = self._获取系统分辨率()
        self.邮件通知器 = 邮件通知器()  # 新增
        self.任务执行器 = 任务执行器(self.获取日志器(), self.更新状态, self.邮件通知器)  # 传入邮件通知器

        try:
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
        self.窗口.geometry("550x650")
        self.窗口.resizable(False, False)
        self.窗口.minsize(550, 650)
        self.窗口.maxsize(550, 650)

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

        # ========== 定时设置区域 ==========
        time_frame = ttk.LabelFrame(main_frame, text="定时任务设置（每小时运行）", padding="10")
        time_frame.pack(fill=tk.X, pady=(0, 15))

        minute_frame = ttk.Frame(time_frame)
        minute_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(minute_frame, text="每小时的第几分钟执行 (0-59):").pack(side=tk.LEFT, padx=(0, 5))
        self.分钟变量 = tk.StringVar(value="5")  # 默认每小时的第5分钟执行
        minute_spinbox = ttk.Spinbox(minute_frame, from_=0, to=59, width=8, textvariable=self.分钟变量)
        minute_spinbox.pack(side=tk.LEFT)

        # 提示标签
        info_label = ttk.Label(time_frame, text="💡 程序会自动判断：17点后导出次日订单，其他时间更新当日订单",
                               style='Info.TLabel')
        info_label.pack(pady=(5, 0))

        # ========== 按钮区域 ==========
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
                                       command=lambda: threading.Thread(target=self._执行智能订单导出,
                                                                        daemon=True).start(),
                                       width=15)
        self.导出次日按钮.pack(side=tk.LEFT, padx=(0, 10))

        self.更新今日按钮 = ttk.Button(button_frame2, text="更新今日订单",
                                       command=lambda: threading.Thread(target=self._执行智能订单导出,
                                                                        daemon=True).start(),
                                       width=15)
        self.更新今日按钮.pack(side=tk.LEFT)

        # 手动检查订单按钮
        button_frame3 = ttk.Frame(main_frame)
        button_frame3.pack(fill=tk.X, pady=(0, 10))
        self.检查订单按钮 = ttk.Button(button_frame3, text="手动检查订单", command=self.手动检查订单, width=15)
        self.检查订单按钮.pack(side=tk.LEFT, padx=(0, 10))

        self.测试邮件按钮 = ttk.Button(button_frame3, text="测试邮件通知", command=self.测试邮件, width=15)
        self.测试邮件按钮.pack(side=tk.LEFT)


        # 账号信息
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        info_text = "管理界面登录账号：01900406 登录密码：Aa123456"
        info_label = ttk.Label(info_frame, text=info_text, style='Info.TLabel')
        info_label.pack()

        # 状态信息区域
        status_frame = ttk.LabelFrame(main_frame, text="状态信息", padding="10")
        status_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 0))
        text_frame = ttk.Frame(status_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        self.状态文本 = tk.Text(text_frame, height=12, width=50, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.状态文本.yview)
        self.状态文本.configure(yscrollcommand=scrollbar.set)
        self.状态文本.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.更新状态("就绪，请设置分钟并启动定时任务")

    def 智能执行任务(self):
        """智能任务：根据当前时间判断执行今日还是次日订单（自动运行，静默，发邮件）"""
        try:
            now = datetime.now()
            current_hour = now.hour

            # 17点后（>=17）执行次日订单，否则执行今日订单
            if current_hour >= 17:
                self.更新状态(f"当前时间 {now.strftime('%H:%M')}，17点后，执行次日订单导出")
                return self._执行完整流程(是次日订单=True, 是否手动=False, 是否静默=True)
            else:
                self.更新状态(f"当前时间 {now.strftime('%H:%M')}，17点前，执行今日订单导出")
                return self._执行完整流程(是次日订单=False, 是否手动=False, 是否静默=True)

        except Exception as e:
            self.更新状态(f"❌ 智能任务执行失败: {e}")
            return False

    def _执行完整流程(self, 是次日订单=True, 是否手动=False, 是否静默=True):
        """执行完整的导出+同步流程
        :param 是次日订单: True=次日订单, False=今日订单
        :param 是否手动: True=手动执行, False=自动执行
        :param 是否静默: True=不弹窗, False=弹窗
        """
        try:
            self._禁用所有按钮()
            订单类型 = "次日" if 是次日订单 else "今日"
            self.更新状态(f"开始执行{订单类型}订单任务...")

            # 1. 导出订单到剪贴板
            订单导出成功 = self.任务执行器.执行日期订单导出(使用今日日期=not 是次日订单)

            if not 订单导出成功:
                self.更新状态(f"❌ {订单类型}订单导出失败")
                # 自动运行时发送失败邮件
                if not 是否手动 and self.邮件通知器:
                    self.邮件通知器.发送失败通知(f"{订单类型}订单导出失败")
                return False

            # 2. 同步到WPS
            self.更新状态(f"开始同步{订单类型}订单到顺丰表格...")
            同步成功 = self.任务执行器.执行顺丰同步(
                是今日订单=not 是次日订单,
                是否手动=是否手动,
                是否静默=是否静默
            )

            if 同步成功:
                self.更新状态(f"✅ {订单类型}订单已同步到顺丰表格")
                return True
            else:
                self.更新状态(f"❌ {订单类型}订单同步失败")
                return False

        except Exception as e:
            self.更新状态(f"❌ 执行流程失败: {e}")
            if not 是否手动 and self.邮件通知器:
                self.邮件通知器.发送失败通知(f"执行流程异常: {str(e)}")
            return False
        finally:
            self._启用所有按钮()

    def _执行智能订单导出(self):
        """手动执行智能订单导出（根据当前时间判断，手动运行，弹窗，不发邮件）"""
        try:
            now = datetime.now()
            current_hour = now.hour

            if current_hour >= 17:
                self.更新状态(f"当前时间 {now.strftime('%H:%M')}，17点后，手动执行次日订单导出")
                return self._执行完整流程(是次日订单=True, 是否手动=True, 是否静默=False)
            else:
                self.更新状态(f"当前时间 {now.strftime('%H:%M')}，17点前，手动执行今日订单导出")
                return self._执行完整流程(是次日订单=False, 是否手动=True, 是否静默=False)

        except Exception as e:
            self.更新状态(f"❌ 手动执行失败: {e}")
            return False

    def 测试邮件(self):
        """测试邮件通知"""
        try:
            self.更新状态("正在发送测试邮件...")
            result = self.邮件通知器.发送测试邮件()
            if result:
                self.更新状态("✅ 测试邮件发送成功，请检查邮箱")
            else:
                self.更新状态("❌ 测试邮件发送失败，请检查配置")
        except Exception as e:
            self.更新状态(f"❌ 测试邮件异常: {e}")

    def _禁用所有按钮(self):
        """禁用所有操作按钮（任务执行时）"""
        self.导出次日按钮.config(state=tk.DISABLED)
        self.更新今日按钮.config(state=tk.DISABLED)
        self.检查订单按钮.config(state=tk.DISABLED)
        self.测试邮件按钮.config(state=tk.DISABLED)
        # 注意：启动/停止按钮不禁用，因为可能需要停止调度器

    def _启用所有按钮(self):
        """启用所有操作按钮（任务完成后）"""
        self.导出次日按钮.config(state=tk.NORMAL)
        self.更新今日按钮.config(state=tk.NORMAL)
        self.检查订单按钮.config(state=tk.NORMAL)
        self.测试邮件按钮.config(state=tk.NORMAL)

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
        """启动定时调度器"""
        try:
            分钟 = self.分钟变量.get()
            if not 分钟.isdigit():
                messagebox.showerror("错误", "请输入有效数字")
                return
            分钟 = int(分钟)
            if 分钟 < 0 or 分钟 > 59:
                messagebox.showerror("错误", "分钟范围错误 (0-59)")
                return

            self.调度器.remove_all_jobs()
            self.调度器.add_job(
                self._调度器执行包装,  # 使用包装方法
                trigger=CronTrigger(minute=分钟),
                id='智能订单任务',
                misfire_grace_time=300
            )
            self.调度器.start()
            self.更新状态(f"已启动：每小时的第 {分钟:02d} 分钟执行")
            self.更新状态(f"提示：17点后执行次日订单，17点前执行今日订单")
            self.启动按钮.config(state=tk.DISABLED)
            self.停止按钮.config(state=tk.NORMAL)
        except Exception as e:
            self.更新状态(f"启动失败: {e}")

    def _调度器执行包装(self):
        """调度器执行的包装方法，确保UI更新在正确线程"""
        # 调度器在后台线程运行，需要确保UI更新在主线程
        # 但任务执行器内部会处理好线程安全
        self.智能执行任务()
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