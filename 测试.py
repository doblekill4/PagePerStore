from playwright.sync_api import sync_playwright
import time
import win32clipboard
import win32con

# 配置
WPS_USER_DATA_DIR = "./wps_profile"
WPS_URL = "https://www.kdocs.cn/l/ceIalhfmfGZ6"


# 剪贴板工具
def set_clipboard(text):
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
    except:
        pass


# ========================
# 最终极简版：只粘贴订单到服务一店一页
# ========================
def test_only_paste():
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=WPS_USER_DATA_DIR,
            headless=False
        )
        page = context.new_page()

        print("✅ 打开表格...")
        page.goto(WPS_URL)
        time.sleep(10)

        # ==========================================
        # 1. 切换到【服务一店一页】
        # ==========================================
        print("✅ 切换到【服务一店一页】")
        page.get_by_text("服务一店一页").click(timeout=15000)
        time.sleep(3)

        # ==========================================
        # 2. 定位到最后一行空行（干净无多余操作）
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
        # 3. 粘贴数据（你旧代码的标准粘贴方式）
        # ==========================================
        test_data = [
            "TEST001", "测试蛋糕", "自提", "2026-03-28",
            "张三", "13800000000", "测试地址", "13800000000",
            "测试备注", "", ""
        ]
        line = "\t".join(str(i) for i in test_data)
        set_clipboard(line)

        print("✅ 粘贴数据到表格")
        page.keyboard.press("Control+v")
        time.sleep(2)

        # ================================
        # 完成
        # ================================
        print("\n🎉 **粘贴完成！**")
        input("\n按回车退出")
        context.close()


if __name__ == "__main__":
    test_only_paste()