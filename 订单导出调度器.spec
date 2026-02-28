# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['定时任务.py'],
    pathex=[],
    binaries=[],
    datas=[('主程序.py', '.'), ('认证管理.py', '.'), ('订单获取.py', '.'), ('数据处理.py', '.'), ('报告生成.py', '.'), ('导出管理.py', '.'), ('任务执行器.py', '.'), ('定时任务.py', '.'), ('配置.py', '.'), ('通用工具.py', '.'), ('日期工具.py', '.'), ('锁定管理.py', '.'), ('顺丰.py', '.'), ('月度微信订单筛选.py', '.'), ('图片备份', '图片备份'), ('icon.ico', '.')],
    hiddenimports=['pandas', 'numpy', 'openpyxl', 'requests', 'apscheduler', 'apscheduler.schedulers.background', 'apscheduler.triggers.cron', 'PIL', 'PIL.Image', 'PIL.ImageGrab', 'psutil', 'pyautogui', 'pydirectinput', 'cv2', 'win32com', 'pythoncom', 'win32clipboard', 'win32gui', 'win32con', 'tkinter', 'tkinter.ttk'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='订单导出调度器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
