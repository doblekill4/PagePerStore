# -*- coding: utf-8 -*-
"""
配置文件 - 一店一页表格截图发送自动化
"""

import os

# ========== 路径配置 ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WPS_USER_DATA_DIR = os.path.join(BASE_DIR, "wps_profile")

# ========== WPS在线文档配置 ==========
WPS_URL = "https://www.kdocs.cn/l/ceIalhfmfGZ6"

# 目标工作表名称
TARGET_SHEET_NAME = "烘焙打印专用"

# ========== 截图对比配置 ==========
# 截图保存目录
SCREENSHOT_DIR = os.path.join(BASE_DIR, "screenshots")
# MD5缓存文件
MD5_CACHE_FILE = os.path.join(BASE_DIR, "last_md5.txt")
# 临时图片路径
TEMP_SCREENSHOT = os.path.join(SCREENSHOT_DIR, "temp_table.png")

# 确保目录存在
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ========== Playwright配置 ==========
HEADLESS_MODE = False  # 调试模式用非无头
BROWSER_VIEWPORT = {'width': 2560, 'height': 1440}  # 增大视口以容纳大字号表格

# 浏览器路径（优先使用用户目录下的Chrome）
CHROME_PATH = r"C:\Users\swear\AppData\Local\Google\Chrome\Application\chrome.exe"

# ========== 微信发送配置 ==========
WECHAT_TARGET_GROUP = "顺丰派送"
WECHAT_GROUP_PINYIN = "sfps"  # 拼音首字母

# 测试模式目标群聊（文件传输助手）
WECHAT_TEST_GROUP = "文件传输助手"
WECHAT_TEST_PINYIN = "wjcszs"

# ========== 日志配置 ==========
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "automation.log")

os.makedirs(LOG_DIR, exist_ok=True)

# ========== 截图方式 ==========
# "playwright": Playwright截图（精准定位）
# "wps": WPS内置复制为图片
# "auto": 自动选择（优先playwright，失败后尝试wps）
SCREENSHOT_METHOD = "auto"
