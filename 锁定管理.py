# 锁定管理.py - 简化版

import ctypes
import time
import tkinter as tk
import os


class 输入锁定管理器:
    def __init__(self, logger=None):
        self.logger = logger
        self.锁定中 = False
        self.用户32 = ctypes.windll.user32
        self.提示窗口 = None

    def 开始锁定(self):
        """开始锁定 - 简化版本"""
        try:
            if self.锁定中:
                if self.logger:
                    self.logger.warning("系统已在锁定状态")
                return True

            # 先尝试解锁，确保系统是解锁状态
            self.用户32.BlockInput(False)
            time.sleep(0.1)

            # 创建提示窗口（简化版）
            self._创建简单提示窗口()

            # 等待窗口创建完成
            time.sleep(0.3)

            # 尝试多次锁定
            max_attempts = 3
            for attempt in range(max_attempts):
                try:
                    # 启用锁定
                    result = self.用户32.BlockInput(True)
                    if result:
                        self.锁定中 = True
                        if self.logger:
                            self.logger.info(f"✅ 用户输入已屏蔽 (第{attempt + 1}次尝试成功)")
                        return True
                    else:
                        if attempt < max_attempts - 1:
                            time.sleep(0.5)
                            continue

                except Exception as e:
                    if self.logger:
                        self.logger.error(f"第{attempt + 1}次锁定尝试失败: {e}")
                    if attempt < max_attempts - 1:
                        time.sleep(0.5)
                        continue

            # 所有尝试都失败
            if self.logger:
                self.logger.error("❌ 所有锁定尝试都失败")

            # 关闭提示窗口
            if self.提示窗口:
                try:
                    self.提示窗口.destroy()
                except:
                    pass
                self.提示窗口 = None

            return False

        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ 锁定失败: {e}")

            # 确保解除锁定状态
            self.锁定中 = False
            return False

    def _创建简单提示窗口(self):
        """创建简单的提示窗口 - 放在右上角"""
        try:
            # 如果已有提示窗口，先关闭
            if self.提示窗口:
                try:
                    self.提示窗口.destroy()
                except:
                    pass

            self.提示窗口 = tk.Toplevel()
            self.提示窗口.title("系统锁定中")

            # 简化设置
            self.提示窗口.attributes('-topmost', True)  # 始终置顶
            self.提示窗口.overrideredirect(True)  # 无标题栏
            self.提示窗口.configure(bg='red')

            # 禁用窗口的关闭按钮
            self.提示窗口.protocol("WM_DELETE_WINDOW", lambda: None)

            # 设置窗口位置和大小 - 放在右上角
            屏幕宽度 = self.提示窗口.winfo_screenwidth()
            屏幕高度 = self.提示窗口.winfo_screenheight()
            窗口宽度 = 200  # 小窗口
            窗口高度 = 60  # 小窗口

            x = 屏幕宽度 - 窗口宽度 - 20  # 离右边20像素
            y = 20  # 离顶部20像素

            self.提示窗口.geometry(f"{窗口宽度}x{窗口高度}+{x}+{y}")
            self.提示窗口.resizable(False, False)

            # 简化的内容
            tk.Label(
                self.提示窗口,
                text="🚫 系统锁定中\n请勿操作",
                font=("Arial", 10),
                bg='red',
                fg='white',
                justify='center'
            ).pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

            # 立即显示并更新
            self.提示窗口.update()

        except Exception as e:
            if self.logger:
                self.logger.error(f"创建提示窗口失败: {e}")

    def 结束锁定(self):
        """结束锁定 - 确保完全解锁"""
        try:
            if not self.锁定中:
                return True

            # 先解除锁定状态
            self.锁定中 = False

            # 解锁输入
            max_attempts = 5
            for attempt in range(max_attempts):
                try:
                    result = self.用户32.BlockInput(False)
                    if result:
                        if self.logger:
                            self.logger.info(f"✅ 用户输入已恢复 (第{attempt + 1}次尝试成功)")
                        break
                    else:
                        if attempt < max_attempts - 1:
                            time.sleep(0.3)
                            continue
                except Exception as e:
                    if attempt < max_attempts - 1:
                        time.sleep(0.3)
                        continue

            # 关闭提示窗口
            if self.提示窗口:
                try:
                    self.提示窗口.destroy()
                except:
                    pass
                self.提示窗口 = None

            return True

        except Exception as e:
            if self.logger:
                self.logger.error(f"解锁失败: {e}")
            self.锁定中 = False
            return True

    def 强制解锁(self):
        """强制解锁"""
        try:
            # 关闭窗口
            if self.提示窗口:
                try:
                    self.提示窗口.destroy()
                except:
                    pass
                self.提示窗口 = None

            # 强制解锁
            for i in range(10):
                try:
                    self.用户32.BlockInput(False)
                except:
                    pass

            self.锁定中 = False
            return True

        except Exception as e:
            self.锁定中 = False
            return True