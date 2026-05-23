# 模块7：定时任务模块（精简版）- 只保留图形界面
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from 月度微信订单筛选 import select_date_range, 执行完整订单查询
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import webbrowser

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from 锁定管理 import 输入锁定管理器
from 任务执行器 import 任务执行器

版本号 = "v2.5"  # 更新版本号

# v1.1增加导出顺丰在线表格功能
# v1.2精简日志，去掉桌面生成的空白日志文件，必要日志文件输出至D:\一店一页
# v1.3增加锁定用户操作模块，保证顺丰在线表格同步成功率
# v1.4拆分定时任务结构到任务执行器和文件清理器，细化图形面板日志信息，优化无用代码
# v1.5优化顺丰表格同步流程，基于测试完整流程重构
# v1.5a针对烘焙电脑1600*900修改图片使得匹配成功
# v1.5b区分当日订单和次日订单按钮
# v1.6服务新电脑适配
# v1.7清除冗余代码，去掉垃圾清理模块
# v1.8增加配置和通用模块
# v2.0增加3种分辨率：2k、1080p、768p分辨率识别，适应需求，修复界面大小异常，增加完成后截图
# v2.1修复wps客户端shift兼容问题，修复搜索框输入问题，修复解锁时机错误问题
# v2.2更新订单筛选逻辑为支付时间（原为自提/配送时间）
# v2.3更新烘焙打印操作，先清楚查询单元格内容再粘贴，保证粘贴相同内容也可触发格式修改
# v2.4适配同仁堂健康好生活新平台
# v2.5 修复丢失自提订单收货人和手机号的问题

class 订单调度器GUI:
    def __init__(self):
        self.调度器 = BackgroundScheduler()
        self.锁定管理器 = 输入锁定管理器()
        self._强制保持DPI设置()
        self.调度器 = BackgroundScheduler()
        self.当前分辨率 = self._获取系统分辨率()
        self.任务执行器 = 任务执行器(self.获取日志器(), self.锁定管理器, self.更新状态)
        self.设置日志()
        self.创建界面()
        self.设置窗口图标()

    def 设置窗口图标(self):
        """设置窗口图标"""
        try:
            # 首先尝试从当前目录加载
            icon_path = "icon.ico"
            if os.path.exists(icon_path):
                self.窗口.iconbitmap(icon_path)
                print(f"✅ 已加载图标: {icon_path}")
            else:
                # 如果不在当前目录，尝试从打包后的资源加载
                try:
                    # 对于打包后的程序，图标会作为资源包含
                    import sys
                    if getattr(sys, 'frozen', False):
                        # 打包后的程序
                        base_path = sys._MEIPASS
                        icon_path = os.path.join(base_path, "icon.ico")
                        if os.path.exists(icon_path):
                            self.窗口.iconbitmap(icon_path)
                            print(f"✅ 已加载打包后的图标: {icon_path}")
                except:
                    pass
        except Exception as e:
            print(f"⚠️ 加载图标失败: {e}")
    def _强制保持DPI设置(self):
        """强制保持当前的DPI设置"""
        try:
            import ctypes

            # 使用系统DPI感知
            try:
                # Windows 8.1及以上
                ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
                print("已设置每监视器DPI感知")
            except:
                # Windows Vista及以上
                ctypes.windll.user32.SetProcessDPIAware()
                print("已设置系统DPI感知")

        except Exception as e:
            print(f"设置DPI感知失败: {e}")
    def _获取系统分辨率(self):
        """获取当前系统分辨率"""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            宽度 = user32.GetSystemMetrics(0)
            高度 = user32.GetSystemMetrics(1)
            return f"{宽度}x{高度}"
        except:
            return "未知分辨率"
    def 获取日志器(self):
        """获取日志记录器"""
        return self.日志 if hasattr(self, '日志') else logging.getLogger(__name__)

    def 设置日志(self):
        """设置日志记录"""
        log_dir = r"D:\一店一页"
        os.makedirs(log_dir, exist_ok=True)

        # 确保日志器是单例的
        self.日志 = logging.getLogger('订单调度器')
        if not self.日志.handlers:  # 避免重复添加处理器
            self.日志.setLevel(logging.INFO)

            # 清除可能存在的旧处理器
            for handler in self.日志.handlers[:]:
                self.日志.removeHandler(handler)

            # 文件处理器
            file_handler = logging.FileHandler(os.path.join(log_dir, "订单调度器.log"), encoding='utf-8')
            # 控制台处理器
            console_handler = logging.StreamHandler()

            # 设置格式
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            # 添加处理器
            self.日志.addHandler(file_handler)
            self.日志.addHandler(console_handler)

    # 在定时任务.py中，修改创建界面方法
    # 修改定时任务.py中的创建界面方法，恢复简单布局
    def 创建界面(self):
        """创建GUI界面 - 简化版，避免显示不全"""
        self.窗口 = tk.Tk()
        self.窗口.title(f"订单导出调度器 {版本号}")


        # 设置窗口大小，增加高度确保所有内容可见
        self.窗口.geometry("500x600")  # 增加高度到600
        self.窗口.resizable(False, False)  # 禁止调整大小

        # 设置窗口最小和最大尺寸
        self.窗口.minsize(500, 600)
        self.窗口.maxsize(500, 600)

        # 设置样式
        style = ttk.Style()
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TLabel', background='#f0f0f0', font=('Arial', 10))
        style.configure('TButton', font=('Arial', 10))
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Info.TLabel', font=('Arial', 9), foreground='blue')

        # 主框架 - 使用简单的pack布局
        main_frame = ttk.Frame(self.窗口, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(main_frame, text=f"订单导出调度器 {版本号}", style='Header.TLabel')
        title_label.pack(pady=(0, 15))
        # 在标题之后添加分辨率信息
        分辨率标签 = ttk.Label(main_frame, text=f"当前分辨率: {self.当前分辨率}",
                               style='Info.TLabel')
        分辨率标签.pack(pady=(0, 10))

        # 时间设置框架
        time_frame = ttk.LabelFrame(main_frame, text="定时导出次日订单设置", padding="10")
        time_frame.pack(fill=tk.X, pady=(0, 15))

        # 时间设置行1：小时
        hour_frame = ttk.Frame(time_frame)
        hour_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(hour_frame, text="小时 (0-23):").pack(side=tk.LEFT, padx=(0, 5))
        self.小时变量 = tk.StringVar(value="17")
        hour_spinbox = ttk.Spinbox(hour_frame, from_=0, to=23, width=8, textvariable=self.小时变量)
        hour_spinbox.pack(side=tk.LEFT)

        # 时间设置行2：分钟
        minute_frame = ttk.Frame(time_frame)
        minute_frame.pack(fill=tk.X)
        ttk.Label(minute_frame, text="分钟 (0-59):").pack(side=tk.LEFT, padx=(0, 5))
        self.分钟变量 = tk.StringVar(value="00")
        minute_spinbox = ttk.Spinbox(minute_frame, from_=0, to=59, width=8, textvariable=self.分钟变量)
        minute_spinbox.pack(side=tk.LEFT)

        # 第一行按钮 - 启动/停止按钮
        button_frame1 = ttk.Frame(main_frame)
        button_frame1.pack(fill=tk.X, pady=(0, 10))

        self.启动按钮 = ttk.Button(button_frame1, text="启动定时任务", command=self.启动调度器, width=15)
        self.启动按钮.pack(side=tk.LEFT, padx=(0, 10))

        self.停止按钮 = ttk.Button(button_frame1, text="停止定时任务", command=self.停止调度器,
                                   state=tk.DISABLED, width=15)
        self.停止按钮.pack(side=tk.LEFT)

        # 第二行按钮 - 今日/次日按钮
        button_frame2 = ttk.Frame(main_frame)
        button_frame2.pack(fill=tk.X, pady=(0, 10))

        self.导出次日按钮 = ttk.Button(button_frame2, text="导出次日订单",
                                       command=lambda: threading.Thread(
                                           target=self._执行导出次日订单,
                                           daemon=True
                                       ).start(),
                                       width=15)
        self.导出次日按钮.pack(side=tk.LEFT, padx=(0, 10))

        self.更新今日按钮 = ttk.Button(button_frame2, text="更新今日订单",
                                       command=lambda: threading.Thread(
                                           target=self._执行更新今日订单,
                                           daemon=True
                                       ).start(),
                                       width=15)
        self.更新今日按钮.pack(side=tk.LEFT)

        # 第三行按钮 - 月度微信订单筛选和检查订单
        button_frame3 = ttk.Frame(main_frame)
        button_frame3.pack(fill=tk.X, pady=(0, 10))

        self.月度微信订单按钮 = ttk.Button(button_frame3, text="月度微信订单筛选",
                                           command=lambda: threading.Thread(
                                               target=self._执行月度微信订单筛选,
                                               daemon=True
                                           ).start(),
                                           width=15)
        self.月度微信订单按钮.pack(side=tk.LEFT, padx=(0, 10))

        self.检查订单按钮 = ttk.Button(button_frame3, text="手动检查订单",
                                       command=self.手动检查订单, width=15)
        self.检查订单按钮.pack(side=tk.LEFT)

        # 提示信息
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        # 更新为新平台的登录账号
        info_text = "管理界面登录账号：01900406 登录密码：Aa123456"
        info_label = ttk.Label(info_frame, text=info_text, style='Info.TLabel')
        info_label.pack()

        # 状态框架 - 放在底部，使用fill和expand确保占用剩余空间
        status_frame = ttk.LabelFrame(main_frame, text="状态信息", padding="10")
        status_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 0))

        # 状态文本框和滚动条
        text_frame = ttk.Frame(status_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.状态文本 = tk.Text(text_frame, height=12, width=50, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.状态文本.yview)
        self.状态文本.configure(yscrollcommand=scrollbar.set)

        self.状态文本.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 初始状态
        self.更新状态("就绪，请设置时间并启动定时任务")

        # 绑定事件，防止窗口尺寸变化
        def 保持窗口大小(event=None):
            # 保持窗口固定大小
            if self.窗口.winfo_width() != 500 or self.窗口.winfo_height() != 600:
                self.窗口.geometry("500x600")

        # 延迟绑定，避免初始化时触发
        self.窗口.after(100, lambda: self.窗口.bind("<Configure>", 保持窗口大小))

    def _执行月度微信订单筛选(self):
        """执行月度微信订单筛选任务 - 按支付时间查询版本"""
        try:
            # 禁用所有按钮
            self._禁用所有按钮()
            self.更新状态("开始月度微信订单筛选（按支付时间）...")

            # 在主线程中弹出日期窗口
            from 月度微信订单筛选 import select_date_range
            日期范围 = select_date_range(self.窗口)

            if 日期范围:
                start_date_str, end_date_str = 日期范围

                self.更新状态(f"选择支付时间范围: {start_date_str} 到 {end_date_str}")
                self.更新状态("开始查询订单数据...")

                # 存储导出结果的变量
                self.月度导出结果 = {
                    '成功': False,
                    '文件路径': None,
                    '订单统计': None,
                    '错误信息': None
                }

                # 在新线程中执行查询
                def 执行查询():
                    try:
                        from 月度微信订单筛选 import 执行完整订单查询

                        # 执行查询并获取结果
                        结果 = 执行完整订单查询(start_date_str, end_date_str)

                        if 结果:
                            # 保存结果
                            self.月度导出结果 = 结果

                            # 在主线程中显示完成信息
                            self.窗口.after(0, self._显示月度完成信息)
                        else:
                            self.更新状态("❌ 月度微信订单筛选失败：无返回结果")
                            self._启用所有按钮()

                    except Exception as e:
                        self.更新状态(f"❌ 查询执行失败: {e}")
                        import traceback
                        traceback.print_exc()
                        self._启用所有按钮()

                # 启动查询线程
                threading.Thread(target=执行查询, daemon=True).start()
            else:
                self.更新状态("取消日期选择")
                self._启用所有按钮()

        except Exception as e:
            self.更新状态(f"❌ 月度微信订单筛选任务启动失败: {e}")
            self._启用所有按钮()

    def _显示月度完成信息(self):
        """显示月度导出完成信息并询问是否打开文件夹"""
        try:
            if self.月度导出结果 and self.月度导出结果.get('成功', False):
                文件路径 = self.月度导出结果.get('文件路径')
                订单统计 = self.月度导出结果.get('订单统计', {})

                # 构建消息
                消息 = f"✅ 月度微信订单筛选完成！\n\n"

                if 订单统计:
                    消息 += f"订单统计:\n"
                    消息 += f"总订单数: {订单统计.get('总订单数', 0)}条\n"
                    消消息 += f"入补差订单: {订单统计.get('入补差订单数', 0)}条\n"
                    消息 += f"入单品订单: {订单统计.get('入单品订单数', 0)}条\n"
                    消息 += f"微信支付总额: ¥{订单统计.get('微信支付总额', 0):.2f}\n"

                    # 添加补贴信息（如果有）
                    补贴订单数量 = 订单统计.get('补贴订单数量', 0)
                    if 补贴订单数量 > 0:
                        消息 += f"\n补贴处理统计:\n"
                        消息 += f"处理补贴/差异订单: {补贴订单数量}笔\n"
                        消息 += f"补贴/差异调整总额: ¥{订单统计.get('补贴总金额', 0):.2f}\n"
                        消息 += f"入单品补贴订单: {订单统计.get('入单品补贴订单', 0)}笔\n"
                        消息 += f"入补差补贴订单: {订单统计.get('入补差补贴订单', 0)}笔\n"

                消息 += f"\n文件已保存到:\n{文件路径}\n\n"
                消息 += "是否打开导出文件夹？"

                # 显示询问对话框
                import tkinter.messagebox as messagebox
                回答 = messagebox.askyesno("导出完成", 消息)

                if 回答:
                    import webbrowser
                    import os
                    # 打开文件所在目录
                    目录路径 = os.path.dirname(文件路径)
                    webbrowser.open(f"file:///{目录路径}")

                self.更新状态("✅ 月度微信订单筛选完成")
            else:
                self.更新状态("❌ 月度微信订单筛选失败")
                # 显示错误信息
                错误信息 = self.月度导出结果.get('错误信息', '未知错误') if self.月度导出结果 else '未知错误'
                messagebox.showerror("导出失败", f"导出失败：{错误信息}")

            self._启用所有按钮()

        except Exception as e:
            self.更新状态(f"显示完成信息失败: {e}")
            self._启用所有按钮()


    def _执行更新今日订单(self):
        """执行更新今日订单任务"""
        try:
            # 禁用所有按钮，防止重复点击
            self._禁用所有按钮()

            # 开始锁定系统
            self.更新状态("开始锁定系统...")
            if not self.锁定管理器.开始锁定():
                self.更新状态("❌ 锁定失败，任务终止")
                self._启用所有按钮()
                return False

            self.更新状态("开始更新今日订单...")

            # 变量用于跟踪整体成功状态
            整体成功 = False

            try:
                # 使用任务执行器处理
                订单导出成功 = self.任务执行器.执行日期订单导出(使用今日日期=True)

                if 订单导出成功:
                    # 执行顺丰同步，传入今日订单参数
                    self.更新状态("开始同步到顺丰表格...")
                    同步成功 = self.任务执行器.执行顺丰同步(是今日订单=True)

                    if 同步成功:
                        self.更新状态("✅ 今日订单已同步到顺丰表格")
                        整体成功 = True
                    else:
                        self.更新状态("❌ 同步到顺丰表格失败")
                        整体成功 = False
                else:
                    self.更新状态("❌ 更新今日订单失败")
                    整体成功 = False

            except Exception as e:
                self.更新状态(f"❌ 任务执行异常: {e}")
                整体成功 = False

            finally:
                # 无论成功与否都解锁 - 但现在会在顺丰同步完成后才解锁
                self.锁定管理器.结束锁定()
                self.更新状态("✅ 系统已解锁")
                self._启用所有按钮()

            return 整体成功

        except Exception as e:
            self.更新状态(f"❌ 更新今日订单任务失败: {e}")
            # 异常时强制解锁
            self.锁定管理器.强制解锁()
            self._启用所有按钮()
            return False

    def _执行导出次日订单(self):
        """执行导出次日订单任务"""
        try:
            # 禁用所有按钮，防止重复点击
            self._禁用所有按钮()

            # 开始锁定系统
            self.更新状态("开始锁定系统...")
            if not self.锁定管理器.开始锁定():
                self.更新状态("❌ 锁定失败，任务终止")
                self._启用所有按钮()
                return False

            self.更新状态("开始导出次日订单...")

            # 变量用于跟踪整体成功状态
            整体成功 = False

            try:
                # 使用任务执行器处理
                订单导出成功 = self.任务执行器.执行日期订单导出(使用今日日期=False)

                if 订单导出成功:
                    # 执行顺丰同步，传入次日订单参数
                    self.更新状态("开始同步到顺丰表格...")
                    同步成功 = self.任务执行器.执行顺丰同步(是今日订单=False)

                    if 同步成功:
                        self.更新状态("✅ 次日订单已同步到顺丰表格")
                        整体成功 = True
                    else:
                        self.更新状态("❌ 同步到顺丰表格失败")
                        整体成功 = False
                else:
                    self.更新状态("❌ 导出次日订单失败")
                    整体成功 = False

            except Exception as e:
                self.更新状态(f"❌ 任务执行异常: {e}")
                整体成功 = False

            finally:
                # 无论成功与否都解锁 - 但现在会在顺丰同步完成后才解锁
                self.锁定管理器.结束锁定()
                self.更新状态("✅ 系统已解锁")
                self._启用所有按钮()

            return 整体成功

        except Exception as e:
            self.更新状态(f"❌ 导出次日订单任务失败: {e}")
            # 异常时强制解锁
            self.锁定管理器.强制解锁()
            self._启用所有按钮()
            return False

    def _禁用所有按钮(self):
        """禁用所有操作按钮"""
        self.导出次日按钮.config(state=tk.DISABLED)
        self.更新今日按钮.config(state=tk.DISABLED)
        self.月度微信订单按钮.config(state=tk.DISABLED)  # 新增这一行
        self.检查订单按钮.config(state=tk.DISABLED)
        self.启动按钮.config(state=tk.DISABLED)
        self.停止按钮.config(state=tk.DISABLED)

    def _启用所有按钮(self):
        """启用所有操作按钮"""
        self.导出次日按钮.config(state=tk.NORMAL)
        self.更新今日按钮.config(state=tk.NORMAL)
        self.月度微信订单按钮.config(state=tk.NORMAL)  # 新增这一行
        self.检查订单按钮.config(state=tk.NORMAL)
        self.启动按钮.config(state=tk.NORMAL)
        self.停止按钮.config(state=tk.NORMAL)


    def 更新状态(self, 消息):
        """更新状态文本框"""
        self.状态文本.config(state=tk.NORMAL)
        self.状态文本.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')} - {消息}\n")
        self.状态文本.see(tk.END)
        self.状态文本.config(state=tk.DISABLED)

    def 手动检查订单(self):
        """使用浏览器打开订单管理页面 - 新平台地址"""
        try:
            self.更新状态("正在打开新平台订单管理页面...")
            # 更新为新平台地址
            url = "https://wxapp.trtjkmall.com/"
            webbrowser.open(url)
            self.更新状态(f"已使用默认浏览器打开新平台: {url}")
            self.更新状态("管理界面登录账号：01900406 登录密码：Aa123456")
        except Exception as e:
            self.更新状态(f"打开浏览器失败: {e}")

    def 启动调度器(self):
        """启动定时调度器"""
        try:
            # 获取用户设置的时间
            小时 = self.小时变量.get()
            分钟 = self.分钟变量.get()

            # 验证输入
            if not 小时.isdigit() or not 分钟.isdigit():
                messagebox.showerror("错误", "请输入有效的时间数字")
                return

            小时 = int(小时)
            分钟 = int(分钟)

            if 小时 < 0 or 小时 > 23 or 分钟 < 0 or 分钟 > 59:
                messagebox.showerror("错误", "请输入有效的时间（小时0-23，分钟0-59）")
                return

            # 添加每日指定时间执行的任务
            self.调度器.add_job(
                self.任务执行器.执行导出任务,  # 直接调用任务执行器
                trigger=CronTrigger(hour=小时, minute=分钟),
                id='每日订单导出',
                name='每日订单导出任务',
                misfire_grace_time=300
            )

            # 启动调度器
            self.调度器.start()

            self.更新状态(f"定时任务已启动，每天 {小时:02d}:{分钟:02d} 执行")
            self.启动按钮.config(state=tk.DISABLED)
            self.停止按钮.config(state=tk.NORMAL)
            self.小时变量.set(str(小时))
            self.分钟变量.set(str(分钟))

        except Exception as e:
            self.日志.error(f"🚨 调度器启动失败: {e}")
            self.更新状态(f"调度器启动失败: {e}")
            import traceback
            self.日志.error(f"🚨 详细错误信息:\n{traceback.format_exc()}")

    def 运行导出任务(self):
        """执行订单导出任务 - 直接使用任务执行器"""
        try:
            self.日志.info("=" * 60)
            self.日志.info("🕔 定时任务启动：开始执行每日订单导出")
            self.日志.info("=" * 60)

            # 在任务开始时锁定系统
            self.更新状态("开始锁定系统...")
            if not self.锁定管理器.开始锁定():
                self.更新状态("❌ 锁定失败，任务终止")
                return

            # 启动任务执行线程 - 直接使用任务执行器的导出任务
            thread = threading.Thread(
                target=self.任务执行器.执行导出任务,  # 直接调用任务执行器
                daemon=True
            )
            thread.start()

        except Exception as e:
            self.更新状态(f"❌ 启动任务失败: {e}")
            self.锁定管理器.强制解锁()

    def 停止调度器(self):
        """停止定时调度器"""
        try:
            self.调度器.shutdown()
            self.更新状态("定时任务已停止")
            self.启动按钮.config(state=tk.NORMAL)
            self.停止按钮.config(state=tk.DISABLED)
        except Exception as e:
            self.日志.error(f"停止调度器失败: {e}")
            self.更新状态(f"停止调度器失败: {e}")

    def 运行(self):
        """运行GUI主循环"""
        self.窗口.protocol("WM_DELETE_WINDOW", self.退出程序)
        self.窗口.mainloop()

    def 退出程序(self):
        """退出程序前的清理工作"""
        try:
            self.更新状态("程序退出，清理资源...")
            # 强制解锁
            self.锁定管理器.强制解锁()
        except Exception as e:
            self.更新状态(f"清理资源时出错: {e}")
        finally:
            if self.调度器.running:
                self.调度器.shutdown()
            self.窗口.destroy()


def 主函数():
    """主函数"""
    调度器 = 订单调度器GUI()
    调度器.运行()


if __name__ == "__main__":
    # 添加当前目录到Python路径
    import sys
    import os

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

    # 直接运行GUI
    try:
        主函数()
    except Exception as e:
        import traceback

        with open("startup_error.log", "w", encoding="utf-8") as f:
            f.write(f"启动错误: {e}\n")
            f.write(traceback.format_exc())
        # 显示错误对话框
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("启动错误", f"程序启动失败:\n{e}")
            root.destroy()
        except:
            pass