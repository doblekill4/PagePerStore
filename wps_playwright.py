# wps_playwright.py - 最终修复版（无头模式+登录目录+粘贴正常+保留截图）
from playwright.sync_api import sync_playwright
import time
import os
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox

# ===================== 配置 =====================
程序目录 = os.path.dirname(os.path.abspath(sys.argv[0] if getattr(sys, 'frozen', False) else __file__))
WPS_USER_DATA_DIR = os.path.join(程序目录, "wps_profile")
WPS_URL = "https://www.kdocs.cn/l/ceIalhfmfGZ6"
TARGET_SHEET_NAME = "服务一店一页"
HEADLESS_MODE = True
DEBUG_MODE = False

print(f"程序目录: {程序目录}")
print(f"用户数据目录: {WPS_USER_DATA_DIR}")


def 检查登录状态():
    """检查是否有有效的登录状态"""
    if not os.path.exists(WPS_USER_DATA_DIR):
        print("用户目录不存在")
        return False

    关键文件 = [
        os.path.join(WPS_USER_DATA_DIR, "Cookies"),
        os.path.join(WPS_USER_DATA_DIR, "Local State"),
    ]

    for 文件 in 关键文件:
        if os.path.exists(文件) and os.path.getsize(文件) > 0:
            print(f"找到有效登录文件: {文件}")
            return True

    print("未检测到有效登录状态")
    return False


def 弹窗提示登录():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    result = messagebox.askyesno("首次使用需要登录", "检测到未登录金山文档\n\n点击【是】打开浏览器手动登录")
    root.destroy()
    return result


def 弹窗等待登录确认():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    messagebox.showinfo("请完成登录", "登录完成后，关闭浏览器，然后点击【确定】")
    root.destroy()


def 手动登录引导():
    print("首次登录引导...")
    if not 弹窗提示登录():
        return False

    os.makedirs(WPS_USER_DATA_DIR, exist_ok=True)

    browser_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    browser_path = None
    for path in browser_paths:
        if os.path.exists(path):
            browser_path = path
            break

    if not browser_path:
        弹窗提示登录失败("未找到浏览器")
        return False

    cmd = [browser_path, f"--user-data-dir={WPS_USER_DATA_DIR}", "--new-window", WPS_URL]
    subprocess.Popen(cmd)
    弹窗等待登录确认()
    return 检查登录状态()


def wps_append_data(data_list=None, is_today_order=True):
    """从剪贴板读取数据并粘贴（使用 JS API）"""
    try:
        import win32clipboard
        import datetime

        print(f"[{datetime.datetime.now()}] ========== wps_append_data 被调用 ==========")

        # 检查登录状态
        if not 检查登录状态():
            if not 手动登录引导():
                return False

        # 读取系统剪贴板
        win32clipboard.OpenClipboard()
        tsv_data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()

        if not tsv_data:
            print("❌ 剪贴板无数据")
            return False

        lines = [line for line in tsv_data.split('\n') if line.strip()]
        print(f"准备粘贴 {len(lines)} 行数据")

        # ✅ 恢复原来的浏览器查找逻辑，并添加你的 Chrome 路径
        browser_path = None

        # 1. 优先查找 Chrome（包括你提供的路径）
        chrome_paths = [
            r"C:\Users\swear\AppData\Local\Google\Chrome\Application\chrome.exe",  # 你的路径放最前面
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Users\Administrator\AppData\Local\Google\Chrome\Application\chrome.exe",
            r"C:\Users\Administrator\Desktop\Google Chrome.lnk",
            r"C:\Users\Administrator\AppData\Roaming\Microsoft\Internet Explorer\Quick Launch\Google Chrome.lnk",
            r"C:\Users\Administrator\AppData\Roaming\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\Google Chrome.lnk",
        ]

        for path in chrome_paths:
            if os.path.exists(path):
                browser_path = path
                print(f"✅ 找到 Chrome: {browser_path}")
                break

        # 2. 如果没找到 Chrome，尝试 Edge
        if not browser_path:
            edge_paths = [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                r"C:\Users\Administrator\Desktop\Microsoft Edge.lnk",
                r"C:\Users\Administrator\AppData\Roaming\Microsoft\Internet Explorer\Quick Launch\Microsoft Edge.lnk",
                r"C:\Users\Administrator\AppData\Roaming\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\Microsoft Edge.lnk",
            ]
            for path in edge_paths:
                if os.path.exists(path):
                    browser_path = path
                    print(f"✅ 找到 Edge: {browser_path}")
                    break

        # 3. 如果还没找到，尝试 360 浏览器
        if not browser_path:
            q360_paths = [
                r"C:\Users\Administrator\AppData\Roaming\360se6\Application\360se.exe",
                r"C:\Program Files (x86)\360\360se\Application\360se.exe",
                r"C:\Users\Administrator\Desktop\360安全浏览器.lnk",
                r"C:\Users\Administrator\AppData\Roaming\Microsoft\Internet Explorer\Quick Launch\360安全浏览器.lnk",
            ]
            for path in q360_paths:
                if os.path.exists(path):
                    browser_path = path
                    print(f"✅ 找到 360浏览器: {browser_path}")
                    break

        # 4. 搜索快捷方式
        if not browser_path:
            try:
                import glob
                search_paths = [
                    r"C:\Users\*\Desktop\*.lnk",
                    r"C:\Users\*\AppData\Roaming\Microsoft\Internet Explorer\Quick Launch\*.lnk",
                    r"C:\Users\*\AppData\Roaming\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\*.lnk",
                ]
                for pattern in search_paths:
                    matches = glob.glob(pattern)
                    for match in matches:
                        lnk_name = os.path.basename(match).lower()
                        if 'chrome' in lnk_name or 'edge' in lnk_name or '360' in lnk_name:
                            browser_path = match
                            print(f"✅ 搜索找到浏览器快捷方式: {browser_path}")
                            break
                    if browser_path:
                        break
            except Exception as e:
                print(f"搜索快捷方式时出错: {e}")

        # 5. 解析快捷方式真实路径
        if browser_path and browser_path.endswith('.lnk'):
            try:
                import win32com.client
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortcut(browser_path)
                browser_path = shortcut.TargetPath
                print(f"解析快捷方式真实路径: {browser_path}")
            except Exception as e:
                print(f"解析快捷方式失败: {e}")

        # 6. 最后都没找到，报错
        if not browser_path:
            print("❌ 未找到任何浏览器 (Chrome/Edge/360)")
            print("请确保已安装 Chrome 或 Edge 浏览器")
            return False

        print(f"使用浏览器: {browser_path}")

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=WPS_USER_DATA_DIR,
                headless=HEADLESS_MODE,
                executable_path=browser_path,
                viewport={'width': 1920, 'height': 1080},
                permissions=['clipboard-read', 'clipboard-write'],
                # 添加参数避免崩溃
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                ]
            )

            page = context.new_page()

            print("打开表格...")
            page.goto(WPS_URL)

            # 等待页面完全加载
            print("等待页面加载...")
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            # 切换工作表
            print(f"切换到工作表: {TARGET_SHEET_NAME}")
            try:
                page.get_by_text(TARGET_SHEET_NAME).first.click(timeout=10000)
                print(f"✅ 切换到工作表: {TARGET_SHEET_NAME}")
                time.sleep(2)
            except:
                for i in range(3):
                    page.keyboard.press("Control+PageDown")
                    time.sleep(0.5)
                print("✅ 使用键盘切换工作表")

            # 定位到最后一行
            print("定位到最后一行...")
            page.mouse.click(500, 300)
            page.keyboard.press("Control+Home")
            time.sleep(1)
            page.keyboard.press("Control+ArrowDown")
            time.sleep(1)
            page.keyboard.press("ArrowDown")
            time.sleep(1)
            print("✅ 定位完成")

            # 使用 JS API 设置和粘贴
            escaped_data = tsv_data.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')

            js_set_clipboard = f"""
            (async function() {{
                try {{
                    const text = `{escaped_data}`;
                    await navigator.clipboard.writeText(text);
                    return 'clipboard_set: ' + text.length + ' chars';
                }} catch(e) {{
                    return 'error: ' + e.message;
                }}
            }})();
            """
            set_result = page.evaluate(js_set_clipboard)
            print(f"设置剪贴板: {set_result}")

            # ✅ 带防抖的粘贴
            js_paste = """
            (async function() {
                if (window._wps_pasting) return 'already_pasting';
                window._wps_pasting = true;

                try {
                    const text = await navigator.clipboard.readText();
                    if (!text) {
                        window._wps_pasting = false;
                        return 'empty_clipboard';
                    }

                    const activeElement = document.activeElement;
                    if (!activeElement) {
                        window._wps_pasting = false;
                        return 'no_active_element';
                    }

                    activeElement.focus();

                    const pasteEvent = new ClipboardEvent('paste', {
                        bubbles: true,
                        cancelable: true,
                        clipboardData: new DataTransfer()
                    });
                    pasteEvent.clipboardData.setData('text/plain', text);
                    activeElement.dispatchEvent(pasteEvent);

                    setTimeout(() => {
                        window._wps_pasting = false;
                    }, 500);

                    return 'success: ' + text.length + ' chars';
                } catch(e) {
                    window._wps_pasting = false;
                    return 'error: ' + e.message;
                }
            })();
            """
            result = page.evaluate(js_paste)
            print(f"粘贴结果: {result}")

            time.sleep(2)
            # page.keyboard.press("Enter")  # 确保这行被注释

            context.close()

            print(f"[{datetime.datetime.now()}] ========== wps_append_data 执行完成 ==========")
            return True

    except Exception as e:
        print(f"❌ 粘贴失败：{e}")
        import traceback
        traceback.print_exc()
        return False

def start_wps_keep_alive():
    if 检查登录状态():
        print("✅ WPS登录状态已存在")
    else:
        print("⚠️ WPS未登录")


def stop_wps_keep_alive():
    pass


__all__ = ['wps_append_data', 'start_wps_keep_alive', 'stop_wps_keep_alive']