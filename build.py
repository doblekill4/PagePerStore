# [file name]: 强制打包.py
import os
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

    # 构建命令
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name=订单导出调度器',
        '--onefile',
        '--windowed',
        '--clean',
        '--noconfirm',
        '--icon=icon.ico',

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
        '--hidden-import=PIL.ImageGrab',
        '--hidden-import=psutil',
        '--hidden-import=pyautogui',
        '--hidden-import=pydirectinput',
        '--hidden-import=cv2',
        '--hidden-import=win32com',
        '--hidden-import=pythoncom',
        '--hidden-import=win32clipboard',
        '--hidden-import=win32gui',
        '--hidden-import=win32con',
        '--hidden-import=tkinter',
        '--hidden-import=tkinter.ttk',

        # 添加所有Python文件
        '--add-data=主程序.py;.',
        '--add-data=认证管理.py;.',
        '--add-data=订单获取.py;.',
        '--add-data=数据处理.py;.',
        '--add-data=报告生成.py;.',
        '--add-data=导出管理.py;.',
        '--add-data=任务执行器.py;.',
        '--add-data=定时任务.py;.',
        '--add-data=配置.py;.',
        '--add-data=通用工具.py;.',
        '--add-data=日期工具.py;.',
        '--add-data=锁定管理.py;.',
        '--add-data=顺丰.py;.',
        '--add-data=月度微信订单筛选.py;.',

        # 添加资源
        '--add-data=图片备份;图片备份',
        '--add-data=icon.ico;.',

        # 入口点
        '定时任务.py'
    ]

    print("开始打包，请等待...")
    print(f"命令长度: {len(cmd)} 个参数")

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

                # 创建快捷打包说明
                with open('打包完成.txt', 'w', encoding='utf-8') as f:
                    f.write(f"""打包完成！
文件: {exe_path}
大小: {大小:.2f} MB
时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

测试步骤:
1. 双击运行 {exe_path}
2. 检查图标是否显示
3. 测试导出次日订单功能
4. 检查日志目录: D:\\一店一页\\
""")
                print("📄 打包说明已保存: 打包完成.txt")
            else:
                print("⚠️  警告: 可执行文件未生成")

            # 显示部分输出
            if result.stdout:
                lines = result.stdout.split('\n')
                print("\n打包输出 (最后10行):")
                for line in lines[-10:]:
                    if line.strip():
                        print(f"  {line}")
        else:
            print("\n" + "=" * 60)
            print("❌ 打包失败！")
            print("=" * 60)
            print(f"错误代码: {result.returncode}")

            if result.stderr:
                print("\n错误信息:")
                print(result.stderr[:500])  # 只显示前500字符

            # 尝试简化命令重新打包
            print("\n尝试简化打包...")
            简化打包()

    except Exception as e:
        print(f"\n❌ 打包异常: {e}")
        import traceback
        traceback.print_exc()


def 简化打包():
    """简化版打包命令"""
    print("\n" + "=" * 60)
    print("尝试简化打包...")
    print("=" * 60)

    # 最简命令
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name=订单导出调度器',
        '--onefile',
        '--windowed',
        '--clean',
        '--icon=icon.ico',
        '定时任务.py'
    ]

    print(f"简化命令: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, check=True)

        exe_path = os.path.join('dist', '订单导出调度器.exe')
        if os.path.exists(exe_path):
            大小 = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"\n✅ 简化打包成功！")
            print(f"文件: {exe_path}")
            print(f"大小: {大小:.2f} MB")
            print("\n⚠️  注意: 简化打包可能缺少某些资源文件")
            print("如果运行有问题，请使用完整打包命令:")
            print(
                'PyInstaller --onefile --windowed --icon=icon.ico --add-data="*.py;." --add-data="图片备份;图片备份" 定时任务.py')
        else:
            print("❌ 简化打包失败，文件未生成")

    except subprocess.CalledProcessError as e:
        print(f"❌ 简化打包失败: {e}")


if __name__ == '__main__':
    强制打包()
    input("\n按回车键退出...")