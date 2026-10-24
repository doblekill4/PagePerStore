# 配置向导.py - 首次运行配置向导
#
# 场景：新环境（换电脑 / 首次拿到 exe）运行时，若程序同目录没有 config.json
#      或配置不完整，则弹出本向导让用户填写必要信息，并自动生成 config.json。
#
# 注意：向导只负责收集与写文件，源码中不保存任何明文凭据。
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox

from 本地配置 import 加载配置, 取值, 获取配置文件路径, 获取程序目录

平台必填项 = ["平台.用户名", "平台.密码", "平台.门店ID"]
邮件选填项 = ["邮件.SENDER_EMAIL", "邮件.AUTHORIZATION_CODE", "邮件.RECIPIENTS"]

默认BASE_URL = "https://wxapp.trtjkmall.com"


def 检查缺失项():
    """返回缺失的必填配置项（平台账号相关），邮件配置缺失只做提醒不算致命"""
    配置 = 加载配置()
    缺失 = []
    for 项 in 平台必填项:
        值 = 取值(配置, 项)
        if 值 is None or 值 == '':
            缺失.append(项)
    return 缺失


def 生成配置文件(数据, 路径=None):
    """把收集到的信息写成 config.json，返回写入路径；失败返回 None"""
    路径 = 路径 or 获取配置文件路径()
    try:
        os.makedirs(os.path.dirname(os.path.abspath(路径)), exist_ok=True)
        with open(路径, 'w', encoding='utf-8') as f:
            json.dump(数据, f, ensure_ascii=False, indent=2)
        return 路径
    except Exception as e:
        try:
            messagebox.showerror("配置文件写入失败",
                                 f"无法写入配置文件：\n{路径}\n\n原因：{e}\n\n"
                                 f"请把该文件放到有写入权限的目录（例如 exe 同目录）后重试。")
        except Exception:
            print(f"配置文件写入失败: {e}")
        return None


def 重载配置模块():
    """配置写入后，让已导入的模块重新读取配置"""
    try:
        import 配置 as 配置模块
        配置模块.配置.重新加载()
    except Exception as e:
        print(f"重载配置模块失败: {e}")
    try:
        import 邮件通知 as 邮件模块
        邮件模块.邮件通知器.重新加载()
    except Exception as e:
        print(f"重载邮件模块失败: {e}")


def _拆分收件人(文本):
    收件人 = []
    for 部分 in str(文本 or '').replace('，', ',').replace('；', ',').replace(';', ',').split(','):
        部分 = 部分.strip()
        if 部分:
            收件人.append(部分)
    return 收件人


def 收集必要信息(缺失项=None):
    """弹出配置向导；用户确认返回配置 dict，取消返回 None"""
    已有 = 加载配置()

    根 = tk.Tk()
    根.withdraw()

    结果 = {'数据': None}
    对话框 = tk.Toplevel(根)
    对话框.title("首次运行配置向导")
    对话框.resizable(False, False)
    对话框.transient(根)

    框架 = ttk.Frame(对话框, padding=16)
    框架.grid(row=0, column=0, sticky='nsew')

    说明 = ("未找到完整的配置文件（config.json）。\n"
            "请填写以下信息，程序将自动在程序目录生成 config.json。\n"
            "带 * 的为必填项；邮件配置留空则不发送通知。")
    ttk.Label(框架, text=说明, justify='left').grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 10))

    字段 = [
        ('平台账号 *', '平台.用户名', False),
        ('平台密码 *', '平台.密码', True),
        ('门店ID *', '平台.门店ID', False),
        ('发件邮箱', '邮件.SENDER_EMAIL', False),
        ('邮箱授权码', '邮件.AUTHORIZATION_CODE', True),
        ('收件邮箱(多个用逗号分隔)', '邮件.RECIPIENTS', False),
        ('日志目录(留空则用程序目录/日志)', '路径.日志目录', False),
    ]

    变量 = {}
    行号 = 1
    for 标签, 键, 隐藏 in 字段:
        ttk.Label(框架, text=标签).grid(row=行号, column=0, sticky='w', pady=3)
        当前值 = 取值(已有, 键, '')
        if isinstance(当前值, list):
            当前值 = ','.join(当前值)
        变量[键] = tk.StringVar(value=当前值 or '')
        入口 = ttk.Entry(框架, textvariable=变量[键], width=42, show='*' if 隐藏 else '')
        入口.grid(row=行号, column=1, sticky='w', pady=3, padx=(8, 0))
        行号 += 1

    ttk.Label(框架, text="提示：QQ邮箱需在设置中开启 SMTP 服务，使用「授权码」而非登录密码。",
              foreground="#666666").grid(row=行号, column=0, columnspan=2, sticky='w', pady=(8, 0))
    行号 += 1

    def 保存并关闭():
        用户名 = 变量['平台.用户名'].get().strip()
        密码 = 变量['平台.密码'].get()
        门店ID = 变量['平台.门店ID'].get().strip()

        错误 = []
        if not 用户名:
            错误.append("平台账号")
        if not 密码:
            错误.append("平台密码")
        if not 门店ID:
            错误.append("门店ID")

        发件邮箱 = 变量['邮件.SENDER_EMAIL'].get().strip()
        if 发件邮箱 and '@' not in 发件邮箱:
            错误.append("发件邮箱格式不正确")

        收件人 = _拆分收件人(变量['邮件.RECIPIENTS'].get())
        for 一个 in 收件人:
            if '@' not in 一个:
                错误.append(f"收件邮箱格式不正确：{一个}")

        if 错误:
            messagebox.showwarning("信息不完整", "请补全/修正以下内容：\n- " + "\n- ".join(错误))
            return

        数据 = {
            "平台": {
                "用户名": 用户名,
                "密码": 密码,
                "门店ID": 门店ID,
                "BASE_URL": 取值(已有, "平台.BASE_URL", 默认BASE_URL) or 默认BASE_URL,
            },
            "邮件": {
                "SMTP_SERVER": 取值(已有, "邮件.SMTP_SERVER", "smtp.qq.com") or "smtp.qq.com",
                "SMTP_PORT": 取值(已有, "邮件.SMTP_PORT", 465) or 465,
                "SENDER_EMAIL": 发件邮箱,
                "AUTHORIZATION_CODE": 变量['邮件.AUTHORIZATION_CODE'].get().strip(),
                "RECIPIENTS": 收件人,
            },
            "路径": {
                "日志目录": 变量['路径.日志目录'].get().strip()
            },
        }
        结果['数据'] = 数据
        对话框.destroy()

    def 取消关闭():
        结果['数据'] = None
        对话框.destroy()

    按钮区 = ttk.Frame(框架)
    按钮区.grid(row=行号, column=0, columnspan=2, sticky='e', pady=(14, 0))
    ttk.Button(按钮区, text="取消", command=取消关闭).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(按钮区, text="保存并启动", command=保存并关闭).grid(row=0, column=1)

    对话框.protocol("WM_DELETE_WINDOW", 取消关闭)
    对话框.update_idletasks()
    宽度 = 对话框.winfo_reqwidth()
    高度 = 对话框.winfo_reqheight()
    对话框.geometry(f"{宽度}x{高度}")
    对话框.focus_force()

    根.wait_window(对话框)
    try:
        根.destroy()
    except Exception:
        pass
    return 结果['数据']


def 确保配置已完整():
    """确保配置完整：缺失时弹向导并生成 config.json。True 表示配置已就绪"""
    缺失 = 检查缺失项()
    if not 缺失:
        return True

    print(f"[配置] 检测到配置缺失（{', '.join(缺失)}），启动配置向导...")
    数据 = 收集必要信息(缺失)
    if 数据 is None:
        try:
            messagebox.showwarning(
                "缺少必要配置",
                "未完成配置，程序无法继续。\n\n"
                f"你可以把 config.json 放在程序目录"
                f"（{获取程序目录()}）后重新运行。")
        except Exception:
            pass
        return False

    路径 = 生成配置文件(数据)
    if not 路径:
        return False

    print(f"[配置] 已生成配置文件: {路径}")
    重载配置模块()
    return True
