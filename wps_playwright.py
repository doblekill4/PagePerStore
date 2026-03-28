from playwright.sync_api import sync_playwright
import time
import os
import threading
import win32clipboard
import win32con

# ===================== 配置 =====================
WPS_USER_DATA_DIR = "./wps_profile"
WPS_URL = "https://www.kdocs.cn/l/ceIalhfmfGZ6"
SHEET_NAME_MAIN = "服务一店一页"


# ===================== 剪贴板工具（和你测试.py完全一致） =====================
def set_clipboard(text):
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
    except:
        pass


# ===================== 登录逻辑 =====================
def wps_first_login():
    if os.path.exists(WPS_USER_DATA_DIR):
        print("✅ 已存在登录状态，跳过登录")
        return True

    print("👉 打开浏览器，请扫码登录（登录后无需关闭浏览器）")
    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=WPS_USER_DATA_DIR,
                headless=False
            )
            page = context.new_page()
            page.goto(WPS_URL)
            for i in range(10):
                time.sleep(1)
                print(f"⏳ 登录倒计时：{10 - i} 秒")
            context.close()
        print("✅ 登录完成，继续启动程序")
        return True
    except Exception as e:
        print(f"⚠️ 登录流程异常：{e}")
        return True


# ===================== 核心：完全复用你测试.py的定位+粘贴逻辑 =====================
def wps_append_data(data_list, is_today_order=True):
    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=WPS_USER_DATA_DIR,
                headless=False
            )
            page = context.new_page()

            print("✅ 打开表格...")
            page.goto(WPS_URL)
            time.sleep(10)  # 和你测试.py完全一致的等待时间

            # ==========================================
            # 1. 切换到【服务一店一页】（和你测试.py完全一致）
            # ==========================================
            print("✅ 切换到【服务一店一页】")
            page.get_by_text("服务一店一页").click(timeout=15000)
            time.sleep(3)

            # ==========================================
            # 2. 定位到最后一行空行（和你测试.py完全一致，一个字都不改）
            # ==========================================
            print("✅ 回到表格顶部 A1")
            page.keyboard.press("Control+Home")
            time.sleep(1)

            print("✅ 跳转到数据最后一行")
            page.keyboard.press("Control+ArrowDown")
            time.sleep(1)

            print("✅ 移动到新的空行")
            page.keyboard.press("ArrowDown")
            time.sleep(1)

            # ==========================================
            # 3. 准备真实订单数据并粘贴（只替换这部分，其他和你测试.py完全一致）
            # ==========================================
            print("✅ 准备真实订单数据...")

            # 列顺序（和你测试.py一致，11列）
            cols = [
                '订单序号', '商品名称', '配送方式', '配送或自提时间',
                '收货人姓名', '收货人手机号', '收货地址', '购买人手机号',
                '客户留言', '门店签字', '取货人签字'
            ]

            # 构建TSV文本
            tsv_lines = []
            for row in data_list:
                row_values = [str(row.get(col, "")) for col in cols]
                tsv_lines.append("\t".join(row_values))
            tsv_content = "\n".join(tsv_lines)

            # 复制到剪贴板（和你测试.py完全一致）
            set_clipboard(tsv_content)

            print("✅ 粘贴数据到表格")
            page.keyboard.press("Control+v")
            time.sleep(2)

            # ================================
            # 完成（和你测试.py完全一致）
            # ================================
            print("\n🎉 **粘贴完成！**")
            context.close()
            return True

    except Exception as e:
        print(f"❌ 写入失败：{e}")
        import traceback
        traceback.print_exc()
        return False


# ===================== 启动停止 =====================
def start_wps_keep_alive():
    threading.Thread(target=wps_first_login, daemon=True).start()


def stop_wps_keep_alive():
    pass