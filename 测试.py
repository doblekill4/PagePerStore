from playwright.sync_api import sync_playwright
import time

# ===================== 配置 =====================
WPS_USER_DATA_DIR = "./wps_profile"
WPS_URL = "https://www.kdocs.cn/l/ceIalhfmfGZ6"
SHEET_NAME_MAIN = "服务一店一页"

def run():
    with sync_playwright() as p:
        # 有头模式 + 慢速
        context = p.chromium.launch_persistent_context(
            user_data_dir=WPS_USER_DATA_DIR,
            headless=False,
            slow_mo=500,
            args=["--no-sandbox", "--start-maximized"]
        )

        page = context.new_page()
        print("正在打开金山文档...")
        page.goto(WPS_URL)
        page.wait_for_load_state("networkidle")
        time.sleep(15)  # 给足加载时间

        # ==========================================
        # 【最强方案】不纠结iframe！直接全页面模拟按键
        # ==========================================
        print("✅ 表格已加载，开始定位...")
        time.sleep(2)

        # 直接点击页面中央，确保表格获得焦点
        page.mouse.click(x=500, y=300)
        time.sleep(1)

        # =====================
        # 你要的三键连招！肉眼可见！
        # =====================
        print("⌨️ Ctrl + Home → Ctrl + ↓ → ↓")
        page.keyboard.press("Control+Home")
        time.sleep(1)

        page.keyboard.press("Control+ArrowDown")
        time.sleep(1)

        page.keyboard.press("ArrowDown")
        time.sleep(1)

        print("\n🎉【完成】看屏幕！光标已经停在空行！")

        # 窗口一直开着
        page.wait_for_timeout(9999999)

if __name__ == "__main__":
    run()