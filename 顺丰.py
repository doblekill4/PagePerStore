# 顺丰.py - 基于图片识别的版本（支持多分辨率）
import pandas as pd
import logging
import time
import os
import win32com.client as win32
import pythoncom
import psutil
import win32gui
import win32process
import win32com.client
import pyautogui
import pydirectinput
import cv2
import numpy as np
from PIL import ImageGrab
import win32clipboard
import ctypes


class 顺丰同步器:
    def __init__(self, logger=None, 状态回调=None, 是今日订单=True):
        """初始化顺丰同步器"""
        self.sheet_name = "服务一店一页"
        self.logger = logger
        self.状态回调 = 状态回调
        self._已记录的消息 = set()
        self.项目根目录 = os.path.dirname(os.path.abspath(__file__))
        self.是今日订单 = 是今日订单  # 新增参数

        # 图片备份目录
        self.图片备份目录 = os.path.join(self.项目根目录, "图片备份")

        # 获取系统分辨率
        self.系统分辨率 = self._获取系统分辨率()

        # 根据分辨率选择图片目录
        self.图片目录 = self._选择图片目录()

        # 图片路径
        self.左上角图标路径 = os.path.join(self.图片目录, "左上角图标.png")
        self.搜索框路径 = os.path.join(self.图片目录, "搜索框.png")
        self.文档图片路径 = os.path.join(self.图片目录, "文档图片.png")

        # 配置pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.5

        # 记录当前分辨率信息
        self._更新状态(f"📏 检测到系统分辨率: {self.系统分辨率}")
        self._更新状态(f"📁 使用图片目录: {os.path.basename(self.图片目录)}")

    def _获取系统分辨率(self):
        """获取当前系统分辨率"""
        try:
            user32 = ctypes.windll.user32
            宽度 = user32.GetSystemMetrics(0)  # SM_CXSCREEN
            高度 = user32.GetSystemMetrics(1)  # SM_CYSCREEN
            return f"{宽度}x{高度}"
        except Exception as e:
            if self.logger:
                self.logger.warning(f"获取分辨率失败: {e}")
            return "未知分辨率"

    def _选择图片目录(self):
        """根据分辨率选择合适的图片目录"""
        try:
            宽度, 高度 = map(int, self.系统分辨率.split('x'))

            # 分辨率分类
            if 宽度 >= 2560 or 高度 >= 1440:  # 2K分辨率
                目标目录 = "2k"
            elif 宽度 >= 1920 or 高度 >= 1080:  # 1080p分辨率
                目标目录 = "1080"
            else:  # 768p或其他低分辨率
                目标目录 = "768"

            完整路径 = os.path.join(self.图片备份目录, 目标目录)

            # 检查目录是否存在
            if not os.path.exists(完整路径):
                self._更新状态(f"⚠️ 警告: {目标目录}目录不存在，尝试使用备用目录")
                # 尝试其他目录
                for 备选目录 in ["1080", "2k", "768"]:
                    备选路径 = os.path.join(self.图片备份目录, 备选目录)
                    if os.path.exists(备选路径):
                        self._更新状态(f"使用备用目录: {备选目录}")
                        return 备选路径

                # 如果所有目录都不存在，使用项目根目录（兼容旧版本）
                self._更新状态("⚠️ 所有图片目录都不存在，使用项目根目录")
                return self.项目根目录

            return 完整路径

        except Exception as e:
            self._更新状态(f"选择图片目录失败: {e}")
            # 默认使用项目根目录
            return self.项目根目录

    def _更新状态(self, 消息):
        """更新状态到GUI和控制台"""
        if self.状态回调:
            self.状态回调(消息)

        if self.logger:
            if not hasattr(self, '_last_message') or self._last_message != 消息:
                self.logger.info(消息)
                self._last_message = 消息

    def _关闭所有WPS窗口(self):
        """关闭所有WPS窗口"""
        try:
            target_processes = ['et.exe', 'wps.exe', 'wpscloudsvr.exe', 'wpscenter.exe']
            closed_count = 0

            for proc_name in target_processes:
                try:
                    import subprocess
                    result = subprocess.run(
                        ['taskkill', '/F', '/IM', proc_name],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0 or 'SUCCESS' in result.stdout or '成功' in result.stdout:
                        closed_count += 1
                        self._更新状态(f"已关闭 {proc_name}")
                except subprocess.TimeoutExpired:
                    self._更新状态(f"关闭 {proc_name} 超时")
                except Exception as e:
                    self._更新状态(f"关闭 {proc_name} 失败: {e}")

            if closed_count > 0:
                self._更新状态(f"✅ 总共关闭了 {closed_count} 个WPS相关进程")
            else:
                self._更新状态("⚠️ 未找到需要关闭的WPS进程")

            time.sleep(2)
            return True

        except Exception as e:
            self._更新状态(f"关闭WPS窗口失败: {e}")
            return False

    def _通过快捷方式启动WPS(self):
        """通过桌面快捷方式启动WPS，先关闭现有进程"""
        try:
            import subprocess

            self._更新状态("关闭现有WPS进程...")
            self._关闭所有WPS窗口()
            time.sleep(2)

            桌面路径 = os.path.join(os.path.expanduser("~"), "Desktop")
            快捷方式名称列表 = [
                "WPS Office.lnk",
                "WPS Office 2019.lnk",
                "WPS.lnk",
                "金山文档.lnk"
            ]

            找到快捷方式 = False
            for 快捷方式名称 in 快捷方式名称列表:
                快捷方式路径 = os.path.join(桌面路径, 快捷方式名称)
                if os.path.exists(快捷方式路径):
                    self._更新状态(f"找到快捷方式: {快捷方式名称}")
                    找到快捷方式 = True

                    try:
                        subprocess.Popen(f'start "" "{快捷方式路径}"', shell=True)
                        self._更新状态("✅ 已启动WPS")
                        time.sleep(4)

                        if self._检查WPS是否在运行():
                            self._更新状态("✅ WPS启动成功")
                            return True
                        else:
                            self._更新状态("❌ WPS启动失败，尝试下一个快捷方式")
                            continue

                    except Exception as e:
                        self._更新状态(f"启动失败: {e}")
                        continue

            if not 找到快捷方式:
                self._更新状态("未找到快捷方式，尝试直接启动et.exe...")

            self._更新状态("尝试直接启动et.exe...")
            try:
                self._关闭所有WPS窗口()
                time.sleep(1)

                subprocess.Popen('start et.exe', shell=True)
                time.sleep(4)

                if self._检查WPS是否在运行():
                    self._更新状态("✅ et.exe启动成功")
                    return True
                else:
                    self._更新状态("❌ et.exe启动失败")
                    return False
            except:
                return False

            return False

        except Exception as e:
            self._更新状态(f"启动WPS失败: {e}")
            return False

    def _识别图片并点击(self, 图片路径, 超时时间=10, 置信度=0.8):
        """识别屏幕上的图片并点击中心位置 - 从上往下搜索"""
        try:
            self._更新状态(f"正在从上往下识别图片: {os.path.basename(图片路径)}")

            if not os.path.exists(图片路径):
                self._更新状态(f"❌ 图片文件不存在: {图片路径}")
                return False

            from PIL import Image
            import numpy as np
            import cv2

            pil_img = Image.open(图片路径)
            if pil_img.mode != 'L':
                pil_img = pil_img.convert('L')
            模板图片 = np.array(pil_img).astype(np.uint8)

            if 模板图片 is None:
                self._更新状态(f"❌ 无法读取图片: {图片路径}")
                return False

            模板高, 模板宽 = 模板图片.shape

            开始时间 = time.time()
            尝试次数 = 0

            while time.time() - 开始时间 < 超时时间:
                尝试次数 += 1
                self._更新状态(f"第{尝试次数}次搜索...")

                import pyautogui
                屏幕截图 = pyautogui.screenshot()
                屏幕图片 = cv2.cvtColor(np.array(屏幕截图), cv2.COLOR_RGB2GRAY)
                屏幕图片 = 屏幕图片.astype(np.uint8)

                匹配结果 = cv2.matchTemplate(屏幕图片, 模板图片, cv2.TM_CCOEFF_NORMED)
                匹配位置 = np.where(匹配结果 >= 置信度)

                if len(匹配位置[0]) > 0:
                    所有位置 = list(zip(匹配位置[1], 匹配位置[0]))
                    所有位置.sort(key=lambda pos: pos[1])

                    最上位置 = 所有位置[0]
                    最大相似度 = 匹配结果[最上位置[1], 最上位置[0]]

                    中心x = 最上位置[0] + 模板宽 // 2
                    中心y = 最上位置[1] + 模板高 // 2

                    self._更新状态(f"✅ 找到{len(所有位置)}个匹配，选择最上面的 (相似度: {最大相似度:.2f})")
                    self._更新状态(f"点击位置: ({中心x}, {中心y})")

                    pyautogui.moveTo(中心x, 中心y, duration=0.3)
                    time.sleep(0.2)
                    pyautogui.click()
                    time.sleep(0.5)

                    return True

                time.sleep(0.5)

            self._更新状态(f"❌ 超时未找到图片: {os.path.basename(图片路径)}")
            return False

        except Exception as e:
            self._更新状态(f"❌ 图片识别失败: {e}")
            import traceback
            self._更新状态(f"详细错误: {traceback.format_exc()}")
            return False

    def _等待图片出现(self, 图片路径, 超时时间=15):
        """等待指定图片出现在屏幕上"""
        return self._识别图片并点击(图片路径, 超时时间, 置信度=0.8)

    def _最大化窗口(self):
        """最大化WPS窗口 - 精确查找WPS窗口"""
        try:
            self._更新状态("正在精确查找WPS窗口...")
            import win32gui
            import win32con

            time.sleep(1)

            def 查找WPS窗口(hwnd, 结果):
                if win32gui.IsWindowVisible(hwnd):
                    标题 = win32gui.GetWindowText(hwnd)
                    if 标题:
                        if any(keyword in 标题 for keyword in ['WPS', 'ET', '表格', 'Spreadsheets', '工作簿']):
                            结果.append(hwnd)
                return True

            窗口列表 = []
            win32gui.EnumWindows(查找WPS窗口, 窗口列表)

            if not 窗口列表:
                self._更新状态("⚠️ 未找到WPS窗口，尝试查找所有窗口")

                def 查找所有窗口(hwnd, 结果):
                    if win32gui.IsWindowVisible(hwnd):
                        标题 = win32gui.GetWindowText(hwnd)
                        if 标题:
                            结果.append(hwnd)
                    return True

                窗口列表 = []
                win32gui.EnumWindows(查找所有窗口, 窗口列表)

            if not 窗口列表:
                self._更新状态("⚠️ 未找到任何窗口，跳过最大化")
                return True

            目标窗口 = None
            for hwnd in 窗口列表:
                标题 = win32gui.GetWindowText(hwnd)
                if any(keyword in 标题 for keyword in ['WPS', 'ET', '表格', 'Spreadsheets']):
                    目标窗口 = hwnd
                    self._更新状态(f"✅ 找到WPS窗口: {标题}")
                    break

            if not 目标窗口:
                目标窗口 = 窗口列表[0]
                标题 = win32gui.GetWindowText(目标窗口)
                self._更新状态(f"⚠️ 使用非WPS窗口: {标题}")

            try:
                win32gui.SetForegroundWindow(目标窗口)
                time.sleep(0.3)

                状态 = win32gui.GetWindowPlacement(目标窗口)[1]
                if 状态 == win32con.SW_SHOWMINIMIZED:
                    win32gui.ShowWindow(目标窗口, win32con.SW_RESTORE)
                    self._更新状态("✅ 窗口已从最小化恢复")
                    time.sleep(0.5)

                win32gui.ShowWindow(目标窗口, win32con.SW_MAXIMIZE)
                time.sleep(0.3)

                win32gui.SetForegroundWindow(目标窗口)

                self._更新状态("✅ 窗口最大化完成")
                time.sleep(0.5)
                return True

            except Exception as e:
                self._更新状态(f"最大化失败: {e}")
                try:
                    win32gui.SetForegroundWindow(目标窗口)
                except:
                    pass
                return True

        except Exception as e:
            self._更新状态(f"最大化窗口失败: {e}")
            return True

    def _图片识别打开文档(self):
        """通过图片识别方式打开文档 - 只使用剪贴板"""
        try:
            self._更新状态("🔄 开始打开文档流程")

            # 1. 最大化窗口
            self._最大化窗口()
            time.sleep(1)

            # 2. 等待WPS完全加载
            self._更新状态("等待WPS界面加载...")
            time.sleep(2)

            # 3. 查找搜索框
            self._更新状态("查找搜索框...")
            if not self._搜索框模板匹配():
                self._更新状态("❌ 搜索框识别失败，无法继续")
                return False

            # 4. 只使用剪贴板粘贴文件名
            self._更新状态("准备输入文件名...")
            time.sleep(0.5)

            if not self._通过剪贴板粘贴文件名():
                self._更新状态("❌ 文件名输入失败，流程终止")
                return False

            # 5. 识别并点击文档图片
            self._更新状态("查找文档...")
            if not self._搜索结果模板匹配():
                self._更新状态("❌ 文档识别失败")
                return False

            # 6. 等待文档完全打开
            self._更新状态("等待文档完全打开...")
            time.sleep(3)

            self._更新状态("✅ 文档打开流程完成")
            return True

        except Exception as e:
            self._更新状态(f"❌ 打开文档失败: {e}")
            return False

    def _通过剪贴板粘贴文件名(self):
        """通过剪贴板粘贴文件名 - 简化版本但保留备份"""
        try:
            import win32clipboard
            import win32con
            import pyautogui

            self._更新状态("开始剪贴板文件名输入...")

            # 1. 备份当前剪贴板内容
            旧剪贴板内容 = None
            try:
                win32clipboard.OpenClipboard()
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                    旧剪贴板内容 = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                    self._更新状态("✅ 剪贴板内容已备份")
                win32clipboard.CloseClipboard()
            except Exception as e:
                self._更新状态(f"备份剪贴板失败: {e}")
                # 继续执行，即使备份失败

            # 2. 设置文件名到剪贴板
            文件名 = "顺丰-零号店配送订单"
            self._更新状态(f"准备设置文件名到剪贴板: {文件名}")

            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(文件名, win32con.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()

            self._更新状态(f"✅ 文件名已复制到剪贴板")
            time.sleep(0.5)

            # 3. 直接粘贴
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(1.5)

            # 5. 恢复旧剪贴板内容
            if 旧剪贴板内容 is not None:
                try:
                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardText(旧剪贴板内容, win32con.CF_UNICODETEXT)
                    win32clipboard.CloseClipboard()
                    self._更新状态("✅ 原始剪贴板内容已恢复")
                except Exception as e:
                    self._更新状态(f"恢复剪贴板失败: {e}")

            return True

        except Exception as e:
            self._更新状态(f"❌ 剪贴板文件名输入失败: {e}")

            # 尝试恢复剪贴板（错误处理）
            if '旧剪贴板内容' in locals() and 旧剪贴板内容 is not None:
                try:
                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardText(旧剪贴板内容, win32con.CF_UNICODETEXT)
                    win32clipboard.CloseClipboard()
                    self._更新状态("已尝试恢复剪贴板")
                except:
                    pass

            return False

    def _搜索结果模板匹配(self):
        """改进的文档识别 - 简化检查"""
        try:
            self._更新状态("正在识别搜索结果...")
            time.sleep(3)

            if not os.path.exists(self.文档图片路径):
                self._更新状态(f"❌ 文档图片文件不存在: {self.文档图片路径}")
                return False

            self._更新状态("使用文档图片模板匹配...")

            识别成功 = False
            for i in range(3):
                self._更新状态(f"第{i + 1}次尝试识别文档图片...")

                if self._改进模板匹配(self.文档图片路径, 置信度=0.6, 双击=True):
                    识别成功 = True
                    time.sleep(2)
                    break
                else:
                    time.sleep(1)

            if 识别成功:
                self._更新状态("✅ 文档图片识别成功")
                time.sleep(3)

                self._可靠检查文档是否打开()

                return True
            else:
                self._更新状态("❌ 文档识别失败")
                self._更新状态("尝试检查是否已有文档打开...")
                if self._可靠检查文档是否打开():
                    self._更新状态("⚠️ 图片识别失败，但检测到文档已打开")
                    return True
                return False

        except Exception as e:
            self._更新状态(f"文档识别异常: {e}")
            return False

    def _搜索框模板匹配(self):
        """改进的搜索框识别 - 点击后直接等待粘贴"""
        try:
            self._更新状态("正在识别搜索框...")

            if not os.path.exists(self.搜索框路径):
                self._更新状态(f"❌ 搜索框图片不存在: {self.搜索框路径}")
                return False

            for i in range(8):
                self._更新状态(f"第{i + 1}次尝试识别搜索框...")

                import pyautogui
                pyautogui.screenshot()

                if self._模板匹配点击(self.搜索框路径, 置信度=0.6):
                    self._更新状态("✅ 搜索框识别成功")
                    # 简化：点击后等待一下，不做其他操作
                    time.sleep(1)
                    return True

                time.sleep(2)

            self._更新状态("❌ 搜索框识别失败")
            return False

        except Exception as e:
            self._更新状态(f"搜索框识别异常: {e}")
            return False

    def _模板匹配点击(self, 图片路径, 置信度=0.7, 双击=False):
        """改进的模板匹配方法 - 只点击，不做其他操作"""
        try:
            import cv2
            import numpy as np
            from PIL import Image
            import pyautogui

            if not os.path.exists(图片路径):
                self._更新状态(f"图片文件不存在: {图片路径}")
                return False

            模板pil = Image.open(图片路径)
            if 模板pil.mode != 'L':
                模板pil = 模板pil.convert('L')
            模板图片 = np.array(模板pil).astype(np.uint8)

            screenshot = pyautogui.screenshot()
            屏幕图片 = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
            屏幕图片 = 屏幕图片.astype(np.uint8)

            最佳匹配 = None
            最佳相似度 = 0
            最佳位置 = None

            scales = [0.8, 0.9, 1.0, 1.1, 1.2]
            for scale in scales:
                if scale != 1.0:
                    新宽度 = int(模板图片.shape[1] * scale)
                    新高度 = int(模板图片.shape[0] * scale)
                    调整后模板 = cv2.resize(模板图片, (新宽度, 新高度))
                else:
                    调整后模板 = 模板图片

                if 调整后模板.shape[0] > 屏幕图片.shape[0] or 调整后模板.shape[1] > 屏幕图片.shape[1]:
                    continue

                匹配结果 = cv2.matchTemplate(屏幕图片, 调整后模板, cv2.TM_CCOEFF_NORMED)
                _, 最大相似度, _, 最大位置 = cv2.minMaxLoc(匹配结果)

                if 最大相似度 > 置信度 and 最大相似度 > 最佳相似度:
                    最佳相似度 = 最大相似度
                    最佳位置 = 最大位置
                    最佳模板 = 调整后模板

            if 最佳位置:
                模板高, 模板宽 = 最佳模板.shape
                中心x = 最佳位置[0] + 模板宽 // 2
                中心y = 最佳位置[1] + 模板高 // 2

                self._更新状态(f"✅ 模板匹配成功 (相似度: {最佳相似度:.2f}, 位置: {中心x},{中心y})")

                # 简化：只做点击操作
                pyautogui.moveTo(中心x, 中心y, duration=0.5)
                time.sleep(0.5)

                if 双击:
                    pyautogui.doubleClick()
                else:
                    pyautogui.click()

                # 简化：点击后直接返回，不添加额外延迟
                return True
            else:
                self._更新状态(f"❌ 模板匹配失败 (最高相似度: {最佳相似度:.2f})")
                return False

        except Exception as e:
            self._更新状态(f"模板匹配异常: {e}")
            return False

    def _可靠检查文档是否打开(self):
        """更可靠的文档打开检查方法"""
        try:
            self._更新状态("检查文档是否打开...")

            import win32gui

            def 枚举WPS窗口(句柄, 结果):
                标题 = win32gui.GetWindowText(句柄)
                if 标题:
                    if "WPS" in 标题 or "ET" in 标题 or "表格" in 标题 or "Spreadsheets" in 标题:
                        结果.append((句柄, 标题))
                return True

            窗口列表 = []
            win32gui.EnumWindows(枚举WPS窗口, 窗口列表)

            if 窗口列表:
                for 句柄, 标题 in 窗口列表:
                    self._更新状态(f"检测到WPS窗口: {标题}")

                    if "顺丰" in 标题 or "零号店" in 标题 or "配送订单" in 标题:
                        if win32gui.IsWindowVisible(句柄):
                            放置状态 = win32gui.GetWindowPlacement(句柄)[1]
                            if 放置状态 != 2:
                                self._更新状态(f"✅ 找到目标文档窗口: {标题}")

                                try:
                                    win32gui.SetForegroundWindow(句柄)
                                    time.sleep(0.5)
                                except:
                                    pass

                                return True
                        else:
                            self._更新状态(f"⚠️ 窗口不可见: {标题}")
                    else:
                        self._更新状态(f"⚠️ 非目标文档窗口: {标题}")

                if 窗口列表:
                    self._更新状态(f"找到{len(窗口列表)}个WPS相关窗口，尝试使用第一个")
                    for 句柄, 标题 in 窗口列表:
                        if win32gui.IsWindowVisible(句柄):
                            self._更新状态(f"✅ 使用窗口: {标题}")
                            try:
                                win32gui.SetForegroundWindow(句柄)
                                time.sleep(0.5)
                            except:
                                pass
                            return True

            try:
                import win32com.client
                wps_app = win32com.client.GetActiveObject("Ket.Application")

                for i in range(3):
                    try:
                        active_workbook = wps_app.ActiveWorkbook
                        if active_workbook:
                            doc_name = active_workbook.Name
                            self._更新状态(f"✅ 通过COM检测到活动文档: {doc_name}")
                            return True
                    except:
                        time.sleep(1)

                self._更新状态("⚠️ COM连接成功，但没有活动文档")

            except Exception as com_error:
                self._更新状态(f"COM连接失败: {com_error}")

            if 窗口列表:
                self._更新状态("⚠️ 未精确匹配文档窗口，但存在WPS窗口，假设文档已打开")
                return True

            self._更新状态("❌ 所有文档检查方法都失败")
            return False

        except Exception as e:
            self._更新状态(f"文档检查异常: {e}")
            return True

    def _改进模板匹配(self, 图片路径, 置信度=0.7, 双击=False):
        """改进的模板匹配方法 - 增加容错"""
        try:
            import cv2
            import numpy as np
            from PIL import Image
            import pyautogui

            if not os.path.exists(图片路径):
                self._更新状态(f"图片文件不存在: {图片路径}")
                return False

            try:
                模板pil = Image.open(图片路径)
                if 模板pil.mode != 'L':
                    模板pil = 模板pil.convert('L')
                模板图片 = np.array(模板pil).astype(np.uint8)
            except:
                self._更新状态(f"无法读取图片: {图片路径}")
                return False

            scales = [0.7, 0.8, 0.9, 1.0, 1.1, 1.2]
            最佳相似度 = 0
            最佳位置 = None

            screenshot = pyautogui.screenshot()
            屏幕图片 = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)
            屏幕图片 = 屏幕图片.astype(np.uint8)

            for scale in scales:
                新宽度 = int(模板图片.shape[1] * scale)
                新高度 = int(模板图片.shape[0] * scale)

                if 新高度 > 屏幕图片.shape[0] or 新宽度 > 屏幕图片.shape[1]:
                    continue

                调整后模板 = cv2.resize(模板图片, (新宽度, 新高度))

                匹配结果 = cv2.matchTemplate(屏幕图片, 调整后模板, cv2.TM_CCOEFF_NORMED)
                _, 最大相似度, _, 最大位置 = cv2.minMaxLoc(匹配结果)

                if 最大相似度 > 置信度 and 最大相似度 > 最佳相似度:
                    最佳相似度 = 最大相似度
                    最佳位置 = 最大位置
                    最佳模板 = 调整后模板

            if 最佳位置:
                模板高, 模板宽 = 最佳模板.shape
                中心x = 最佳位置[0] + 模板宽 // 2
                中心y = 最佳位置[1] + 模板高 // 2

                self._更新状态(f"✅ 模板匹配成功 (相似度: {最佳相似度:.2f}, 位置: {中心x},{中心y})")

                pyautogui.moveTo(中心x, 中心y, duration=0.3)
                time.sleep(0.2)

                if 双击:
                    pyautogui.doubleClick()
                else:
                    pyautogui.click()

                time.sleep(1)
                return True
            else:
                self._更新状态(f"❌ 模板匹配失败 (最高相似度: {最佳相似度:.2f})")
                return False

        except Exception as e:
            self._更新状态(f"模板匹配异常: {e}")
            return False

    # 在顺丰.py的_execute_table_operations方法中添加新功能：

    def _执行表格操作(self, 是今日订单=True):
        """执行表格数据粘贴等操作 - 调整解锁时机"""
        try:
            self._更新状态("📋 执行表格操作...")

            time.sleep(2)

            self._更新状态("切换到正确的工作表...")

            import pyautogui
            import win32clipboard
            import win32con

            # 1. 先完成原来的粘贴操作
            for i in range(10):
                pyautogui.hotkey('ctrl', 'pgup')
                time.sleep(0.2)

            for i in range(2):
                pyautogui.hotkey('ctrl', 'pgdn')
                time.sleep(0.2)

            pyautogui.hotkey('ctrl', 'home')
            time.sleep(1)
            pyautogui.hotkey('ctrl', 'down')
            time.sleep(1)
            pyautogui.press('down')
            time.sleep(1)

            self._更新状态("执行粘贴操作...")
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(3)

            # 2. 新增功能：转到烘焙打印表格
            self._更新状态("转到烘焙打印表格...")
            time.sleep(2)

            # Ctrl+PageDown 10次
            for i in range(10):
                pyautogui.hotkey('ctrl', 'pgdn')
                time.sleep(0.3)
                self._更新状态(f"切换工作表 {i + 1}/10")

            time.sleep(1)

            # Ctrl+Home 1次
            self._更新状态("焦点到表头...")
            pyautogui.hotkey('ctrl', 'home')
            time.sleep(1)

            # Tab 3次（移动到日期输入框）
            self._更新状态("移动到日期输入框...")
            pyautogui.press('tab')
            pyautogui.press('tab')
            pyautogui.press('tab')
            time.sleep(0.5)
            pyautogui.press('backspace')
            time.sleep(0.5)

            # 4. 根据是今日订单还是次日订单准备日期
            import datetime
            today = datetime.date.today()

            if 是今日订单:
                # 今日订单：输入今天日期
                目标日期 = today
            else:
                # 次日订单：输入明天日期
                目标日期 = today + datetime.timedelta(days=1)

            # 格式化日期为 YYYY/MM/DD
            日期文本 = 目标日期.strftime("%Y/%m/%d")
            self._更新状态(f"准备输入日期: {日期文本}")

            # 5. 通过剪贴板粘贴日期
            try:
                # 保存当前剪贴板内容（备份）
                旧剪贴板内容 = None
                try:
                    win32clipboard.OpenClipboard()
                    if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                        旧剪贴板内容 = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                    win32clipboard.CloseClipboard()
                except:
                    pass

                # 设置日期到剪贴板
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(日期文本, win32con.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()

                # 等待剪贴板操作完成
                time.sleep(0.5)

                # 粘贴日期
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.5)

                # 恢复旧剪贴板内容（如果需要的话）
                if 旧剪贴板内容 is not None:
                    try:
                        win32clipboard.OpenClipboard()
                        win32clipboard.EmptyClipboard()
                        win32clipboard.SetClipboardText(旧剪贴板内容, win32con.CF_UNICODETEXT)
                        win32clipboard.CloseClipboard()
                    except:
                        pass

            except Exception as e:
                self._更新状态(f"剪贴板操作失败: {e}")
                # 回退到直接输入
                pyautogui.write(日期文本)

            time.sleep(3)

            # 7. 再次 Ctrl+Home 回到表头
            self._更新状态("焦点回到表头...")
            pyautogui.hotkey('ctrl', 'home')
            time.sleep(3)
            self._更新状态("选取数据区域...")
            pydirectinput.keyDown('ctrl')
            pydirectinput.keyDown('shift')
            pydirectinput.press('down')
            pydirectinput.keyUp('shift')
            pydirectinput.keyUp('ctrl')
            time.sleep(1)

            # 测试2: Shift+Ctrl+Right

            pydirectinput.keyDown('ctrl')
            pydirectinput.keyDown('shift')
            pydirectinput.press('right')
            pydirectinput.keyUp('shift')
            pydirectinput.keyUp('ctrl')
            time.sleep(15)

            # 9. Shift+F10 打开右键菜单
            self._更新状态("打开右键菜单...")
            pyautogui.hotkey('shift', 'f10')
            time.sleep(2)

            # 10. 方向键下5次
            self._更新状态("选择菜单项...")
            for i in range(5):
                pyautogui.press('down')
                time.sleep(0.3)

            # 11. 回车确认
            pyautogui.press('enter')
            time.sleep(3)

            # 关键修改：现在解锁系统
            self._更新状态("✅ 表格操作完成，准备解锁系统")

            # 注意：这里不显示提示框，提示框由调用方在解锁后显示
            return True

        except Exception as e:
            self._更新状态(f"❌ 表格操作失败: {e}")
            return False

    def _显示复制成功提示(self):
        """显示图片复制成功提示窗口 - 在显示前确保系统已解锁"""
        try:
            # 关键：这个方法被调用时，应该已经解锁了
            self._更新状态("准备显示复制成功提示框...")
            self._更新状态("系统应该已经解锁，请点击确定按钮")

            import tkinter as tk
            from tkinter import messagebox
            import threading
            import time

            # 使用单独的线程显示消息框
            def 显示消息框():
                try:
                    # 创建根窗口但不显示
                    root = tk.Tk()
                    root.withdraw()  # 隐藏主窗口

                    # 确保窗口置顶
                    root.attributes('-topmost', True)

                    # 显示消息框
                    messagebox.showinfo(
                        "复制成功",
                        "✅ 图片已复制到剪贴板\n✅ 系统已解锁\n✅ 可粘贴到微信发送\n\n点击确定关闭",
                        parent=root
                    )

                    # 销毁窗口
                    root.destroy()
                    self._更新状态("✅ 用户已确认提示框")

                except Exception as e:
                    self._更新状态(f"提示框显示异常: {e}")

            # 在新线程中显示消息框
            提示线程 = threading.Thread(target=显示消息框, daemon=True)
            提示线程.start()

            # 等待线程启动
            time.sleep(0.5)

            self._更新状态("✅ 已弹出复制成功提示框")
            self._更新状态("提示：请点击'确定'按钮关闭提示框")

            return True

        except Exception as e:
            self._更新状态(f"❌ 显示提示窗口失败: {e}")
            return True

    def _WPS自动化同步(self) -> bool:
        """WPS自动化同步 - 简化版本"""
        try:
            self._更新状态("🔄 开始WPS同步流程")
            self._更新状态(f"订单类型: {'今日订单' if self.是今日订单 else '次日订单'}")
            self._更新状态(f"📏 当前系统分辨率: {self.系统分辨率}")

            # 移除多余的关闭进程调用
            # 直接启动WPS，让启动方法处理关闭
            if not self._通过快捷方式启动WPS():
                self._更新状态("❌ 启动WPS失败")
                return False

            if not self._图片识别打开文档():
                self._更新状态("❌ 文档打开失败")
                return False

            self._更新状态("等待文档完全打开...")
            time.sleep(3)

            self._更新状态("开始执行表格数据粘贴...")
            if not self._执行表格操作(self.是今日订单):
                self._更新状态("⚠️ 表格操作部分失败")

            self._更新状态("✅ WPS同步流程完成")
            return True

        except Exception as e:
            self._更新状态(f"❌ WPS同步失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _检查WPS是否在运行(self):
        """检查WPS是否正在运行"""
        try:
            import psutil
            wps_processes = ['et.exe', 'wps.exe']

            for proc in psutil.process_iter(['name']):
                proc_name = proc.info['name']
                if proc_name and proc_name.lower() in wps_processes:
                    return True
            return False
        except Exception as e:
            self._更新状态(f"检查WPS进程失败: {e}")
            return False