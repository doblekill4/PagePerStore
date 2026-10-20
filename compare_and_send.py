# -*- coding: utf-8 -*-
"""
表格截图对比与发送主逻辑
用于一店一页自动化任务

使用方式:
    python compare_and_send.py          # 正式运行
    python compare_and_send.py --test  # 测试模式（跳过MD5对比）
"""

import time
import os
import sys
import hashlib
from config import (
    SCREENSHOT_DIR, MD5_CACHE_FILE, TEMP_SCREENSHOT,
    WECHAT_TARGET_GROUP, WECHAT_GROUP_PINYIN, LOG_FILE
)

# 技能脚本路径
SKILL_SCRIPT_DIR = r"C:\Users\swear\.workbuddy\skills\wechat-sender\scripts"
if SKILL_SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SKILL_SCRIPT_DIR)

# WPS原生截图模块（使用剪贴板获取"复制为图片"）
from wps_native_screenshot import capture_and_compare as wps_capture


def log(msg):
    """写入日志"""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        from datetime import datetime
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'ignore').decode('ascii'))


def load_last_md5():
    """读取上次的MD5"""
    try:
        if os.path.exists(MD5_CACHE_FILE):
            with open(MD5_CACHE_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
    except:
        pass
    return ""


def save_md5(md5_value):
    """保存本次MD5"""
    try:
        with open(MD5_CACHE_FILE, "w", encoding="utf-8") as f:
            f.write(md5_value)
        log(f"OK MD5已更新: {md5_value}")
    except Exception as e:
        log(f"X 保存MD5失败: {e}")


def calculate_md5(text):
    """计算MD5"""
    return hashlib.md5((text or "").encode('utf-8')).hexdigest()


def copy_image_to_clipboard(image_path):
    """将图片复制到剪贴板"""
    try:
        import win32clipboard
        from PIL import Image
        import io

        image = Image.open(image_path)
        output = io.BytesIO()
        image.convert('RGB').save(output, format='BMP')
        data = output.getvalue()[14:]

        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        finally:
            win32clipboard.CloseClipboard()

        log(f"OK 图片已复制到剪贴板 ({image.width}x{image.height})")
        return True

    except ImportError as e:
        log(f"X 缺少依赖库: {e}")
        return False
    except Exception as e:
        log(f"X 复制图片失败: {e}")
        return False


def send_image_to_wechat(group_pinyin):
    """发送剪贴板图片到微信群"""
    try:
        import win32gui
        import win32con
        import ctypes
        from pywinauto.keyboard import send_keys
        import win32process
        import psutil

        log(f"发送图片到群聊: {group_pinyin}")

        # 查找微信窗口
        all_wins = []

        def callback(hwnd, _):
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if psutil.Process(pid).name().lower() != "weixin.exe":
                    return
                cls = win32gui.GetClassName(hwnd)
                if cls != "Qt51514QWindowIcon":
                    return
                title = win32gui.GetWindowText(hwnd)
                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                visible = win32gui.IsWindowVisible(hwnd)
                iconic = win32gui.IsIconic(hwnd)
                all_wins.append({
                    "hwnd": hwnd, "title": title, "pid": pid,
                    "w": w, "h": h, "visible": visible, "iconic": iconic
                })
            except:
                pass

        win32gui.EnumWindows(callback, None)

        # 过滤正常窗口
        valid = [w for w in all_wins if w["visible"] == 1 and w["iconic"] == 0 and w["w"] >= 400]
        if valid:
            valid.sort(key=lambda x: x["w"] * x["h"], reverse=True)
            hwnd = valid[0]["hwnd"]
        else:
            iconic = [w for w in all_wins if w["iconic"] == 1]
            if iconic:
                hwnd = iconic[0]["hwnd"]
            else:
                log("X 未找到微信窗口")
                return False

        log(f"找到微信窗口: hwnd={hwnd}")

        # 激活窗口
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.8)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(1)

        # 点击搜索区域
        rect = win32gui.GetWindowRect(hwnd)
        cx, cy = rect[0] + 30, rect[1] + 150
        ctypes.windll.user32.SetCursorPos(cx, cy)
        ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
        time.sleep(0.1)
        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
        time.sleep(0.5)

        # Ctrl+F 搜索
        send_keys("^f")
        time.sleep(1.5)

        # 输入拼音
        send_keys("^a")
        time.sleep(0.2)
        send_keys(group_pinyin, with_spaces=True)
        time.sleep(2)

        # 回车
        send_keys("{ENTER}")
        time.sleep(1.5)

        # 粘贴图片 (Ctrl+V)
        send_keys("^v")
        time.sleep(1)

        # 发送
        send_keys("{ENTER}")
        time.sleep(0.5)

        log(f"OK 图片发送成功: {WECHAT_TARGET_GROUP}")
        return True

    except Exception as e:
        log(f"X 发送失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main(test_mode=False):
    """
    主流程 - 使用WPS原生复制为图片功能
    """
    # 测试模式发送到文件传输助手
    if test_mode:
        target_group = "文件传输助手"
        target_pinyin = "wjcszs"
        log("=" * 60)
        log("一店一页表格截图发送自动化 [测试模式]")
        log(f"目标: {target_group} ({target_pinyin})")
        log("=" * 60)
    else:
        target_group = WECHAT_TARGET_GROUP
        target_pinyin = WECHAT_GROUP_PINYIN
        log("=" * 60)
        log("一店一页表格截图发送自动化")
        log(f"目标: {target_group} ({target_pinyin})")
        log("=" * 60)

    # 1. 截图并获取表格数据（使用WPS原生复制为图片）
    log("步骤1: 截图并获取表格数据 (WPS原生)...")
    screenshot_path, table_text, current_md5 = wps_capture()

    if not screenshot_path:
        log(f"X 截图失败")
        return False, "截图失败"

    log(f"OK 截图保存: {screenshot_path}")
    log(f"OK 表格文本长度: {len(table_text) if table_text else 0}字符")

    # 2. 计算MD5（wps_capture已返回）
    log("步骤2: 计算MD5...")
    if not current_md5 and table_text:
        current_md5 = calculate_md5(table_text)
    log(f"当前MD5: {current_md5}")

    # 3. 对比MD5
    if not test_mode:
        last_md5 = load_last_md5()
        log(f"上次MD5: {last_md5}")

        if current_md5 == last_md5 and last_md5:
            log("OK 内容无变化，跳过发送")
            return True, "内容无变化"
        else:
            log("检测到内容变化，继续发送...")
    else:
        log("测试模式：跳过MD5对比")

    # 4. 复制图片到剪贴板
    log("步骤3: 复制图片到剪贴板...")
    if not copy_image_to_clipboard(screenshot_path):
        return False, "复制图片失败"

    # 5. 发送微信
    log(f"步骤4: 发送到微信群 ({target_group})...")
    if send_image_to_wechat(target_pinyin):
        if not test_mode:
            save_md5(current_md5)
        return True, "发送成功"
    else:
        return False, "发送失败"


if __name__ == "__main__":
    test_mode = "--test" in sys.argv or "-t" in sys.argv
    success, msg = main(test_mode=test_mode)
    log(f"执行完成: {'成功' if success else '失败'} - {msg}")
    sys.exit(0 if success else 1)
