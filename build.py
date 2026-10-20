# [file name]: 强制打包.py
import os  # ✅ 添加这行
import subprocess
import sys


def 强制打包():
    """强制打包，跳过依赖检查"""
    print("=" * 60)
    print("订单导出调度器 - 强制打包")
    print("=" * 60)

    # 清理旧文件
    for 目录 in ['build', 'dist', '__pycache__']:
        if os.path.exists(目录):
            import shutil
            shutil.rmtree(目录, ignore_errors=True)

    # ✅ 先使用 console 模式（显示控制台），调试完成后再改回 windowed
    CONSOLE_MODE = False  # True=显示控制台, False=隐藏控制台

    console_flag = '--console' if CONSOLE_MODE else '--windowed'

    print(f"打包模式: {'显示控制台' if CONSOLE_MODE else '隐藏控制台'}")

    # 构建命令
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name=订单导出调度器',
        '--onefile',
        console_flag,  # ✅ 使用变量控制
        '--clean',
        '--noconfirm',
        '--icon=icon.ico',
        '--runtime-tmpdir=.\\temp',

        # 核心隐藏导入
        '--hidden-import=pandas',
        '--hidden-import=numpy',
        '--hidden-import=openpyxl',
        '--hidden-import=requests',
        '--hidden-import=apscheduler',
        '--hidden-import=apscheduler.schedulers.background',
        '--hidden-import=apscheduler.triggers.cron',
        '--hidden-import=PIL',
        '--hidden-import=PIL.Image',
        '--hidden-import=win32clipboard',
        '--hidden-import=win32gui',
        '--hidden-import=win32con',
        '--hidden-import=tkinter',
        '--hidden-import=tkinter.ttk',
        '--hidden-import=playwright',
        '--hidden-import=playwright.sync_api',
        '--hidden-import=asyncio',

        # 收集 Playwright
        '--collect-all=playwright',

        # 添加所有Python文件
        '--add-data=主程序.py;.',
        '--add-data=认证管理.py;.',
        '--add-data=订单获取.py;.',
        '--add-data=数据处理.py;.',
        '--add-data=导出管理.py;.',
        '--add-data=任务执行器.py;.',
        '--add-data=定时任务.py;.',
        '--add-data=配置.py;.',
        '--add-data=邮件通知.py;.',
        '--add-data=wps_playwright.py;.',
        '--add-data=报告生成.py;.',

        # 添加资源
        '--add-data=icon.ico;.',

        # 入口点
        '定时任务.py'
    ]

    print("开始打包，请等待...")
    print(f"命令: {' '.join(cmd[:10])}...")  # 只打印前几个参数

    try:
        # 运行打包命令
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')

        if result.returncode == 0:
            print("\n" + "=" * 60)
            print("✅ 打包成功！")
            print("=" * 60)

            # 验证结果
            exe_path = os.path.join('dist', '订单导出调度器.exe')
            if os.path.exists(exe_path):
                大小 = os.path.getsize(exe_path) / (1024 * 1024)
                print(f"📦 文件位置: {exe_path}")
                print(f"📦 文件大小: {大小:.2f} MB")

                if CONSOLE_MODE:
                    print("\n⚠️  当前是控制台模式（有黑窗口）")
                    print("   测试没问题后，将 CONSOLE_MODE = False 重新打包即可隐藏控制台")

                # 创建打包说明
                with open('打包完成.txt', 'w', encoding='utf-8') as f:
                    f.write(f"""打包完成！
文件: {exe_path}
大小: {大小:.2f} MB
时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
模式: {'控制台模式（显示黑窗口）' if CONSOLE_MODE else '窗口模式（无控制台）'}

========================================
测试步骤
========================================

1. 双击运行 订单导出调度器.exe
2. 观察控制台输出（如果有黑窗口）
3. 测试所有功能：
   - 导出次日订单
   - 更新今日订单  
   - 邮件通知
   - WPS同步

4. 确认没问题后：
   - 修改 build.py 中的 CONSOLE_MODE = False
   - 重新运行 build.py
   - 即可生成无控制台的正式版本

========================================
""")
                print("📄 打包说明已保存: 打包完成.txt")
            else:
                print("⚠️  警告: 可执行文件未生成")
        else:
            print("\n" + "=" * 60)
            print("❌ 打包失败！")
            print("=" * 60)
            if result.stderr:
                print("\n错误信息:")
                print(result.stderr[:1000])

    except Exception as e:
        print(f"\n❌ 打包异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    强制打包()
    input("\n按回车键退出...")