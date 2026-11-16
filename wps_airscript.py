# -*- coding: utf-8 -*-
"""金山文档在线表格后台写入（AirScript Webhook）。

纯 HTTP 调用，不启动浏览器、不占用窗口焦点、不经过系统剪贴板，
因此在导出期间用户打字、点鼠标、复制粘贴都不会干扰写入结果。

一次性准备（只需在浏览器里做一次，之后永久不再需要浏览器）：
  1. 打开目标在线表格 -> 效率 / 高级开发 -> AirScript 脚本编辑器
  2. 新建「文档共享脚本」，把 wps_airscript_append.js 的内容粘贴进去并保存
  3. 工具栏【脚本令牌(beta)】-> 创建 APIToken（需实名认证，免费，默认 180 天有效）
  4. 脚本侧栏「更多」-> 复制 webhook 链接，形如
     https://www.kdocs.cn/api/v3/ide/file/<file_id>/script/<script_id>/sync_task
  5. 把 webhook / token 填到程序同目录 config.json 的 "WPS" 段（见 config.example.json）

命令行用法（Python 3.10+，需 requests）：
  python wps_airscript.py --check                     # 只检查配置，不联网
  python wps_airscript.py --ping                      # 联网验证令牌/脚本/表名，不写数据
  python wps_airscript.py --from-clipboard --dry-run  # 预览将写入的数据，不写
  python wps_airscript.py --from-clipboard            # 读系统剪贴板 TSV 并追加
  python wps_airscript.py --file data.tsv             # 读 TSV 文件并追加
"""

import argparse
import csv
import io
import json
import os
import sys

import requests

from 本地配置 import 加载配置, 取值, 获取配置文件路径

默认工作表名 = "服务一店一页"
浏览器模式 = ("browser", "playwright", "旧版", "旧浏览器")


def _输出(日志器, 级别, 消息):
    if 日志器 is not None and hasattr(日志器, 级别):
        getattr(日志器, 级别)(消息)
    else:
        print(消息)


def 读配置():
    """从同目录 config.json 读取 WPS 段；环境变量可覆盖 webhook/token。"""
    数据 = 加载配置()
    配置段 = 取值(数据, "WPS", {}) or {}
    if not isinstance(配置段, dict):
        配置段 = {}

    webhook = str(配置段.get("webhook") or os.environ.get("WPS_AIRSCRIPT_WEBHOOK") or "").strip()
    token = str(配置段.get("token") or os.environ.get("WPS_AIRSCRIPT_TOKEN") or "").strip()
    模式 = str(配置段.get("模式") or "airscript").strip().lower()

    try:
        超时 = int(配置段.get("timeout", 60))
    except (TypeError, ValueError):
        超时 = 60

    return {
        "webhook": webhook,
        "token": token,
        "模式": 模式,
        "sheet_name": str(配置段.get("sheet_name") or 默认工作表名).strip(),
        "timeout": max(10, 超时),
        "ping_only": False,
        "dedup": bool(配置段.get("dedup", False)),
        "numeric_columns": 配置段.get("numeric_columns") or [],
        "start_row": 配置段.get("start_row"),
    }


def 配置就绪():
    """是否启用了 AirScript 模式且凭据齐全；False 时调用方应回退到浏览器链路。"""
    配置 = 读配置()
    if 配置["模式"] in 浏览器模式:
        return False
    if not (配置["webhook"] and 配置["token"]):
        return False
    # 防止把 config.example.json 里的占位符当成真配置，误发到无效地址
    if "在此填入" in 配置["webhook"] or "在此填入" in 配置["token"]:
        return False
    if "/api/v3/ide/file/" not in 配置["webhook"] or "/sync_task" not in 配置["webhook"]:
        return False
    return True


def dataframe转行(df):
    """DataFrame -> 二维字符串数组（不经 TSV，字段内换行/制表符不会错列）。"""
    副本 = df.fillna("").astype(str)
    副本 = 副本.replace({"^nan$": "", "^NaN$": ""}, regex=True)
    return 副本.values.tolist()


def tsv转行(tsv文本):
    """按 pandas.to_csv(sep='\\t', quoting=csv.QUOTE_MINIMAL) 的规则解析 TSV。"""
    行列表 = []
    for 行 in csv.reader(io.StringIO(tsv文本), delimiter="\t"):
        if not 行:
            continue
        if any(str(单元).strip() for 单元 in 行):
            行列表.append([str(单元) for 单元 in 行])
    return 行列表


def 读剪贴板文本():
    import win32clipboard
    win32clipboard.OpenClipboard()
    try:
        return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT) or ""
    finally:
        win32clipboard.CloseClipboard()


def _整理行(行列表):
    """补齐列数、统一为字符串，并检查规模。"""
    if not 行列表:
        raise ValueError("没有可写入的数据行")
    if len(行列表) > 2000:
        raise ValueError(f"单次写入 {len(行列表)} 行过多，请分批后再调用")

    列数 = max(len(行) for 行 in 行列表)
    if 列数 == 0:
        raise ValueError("数据没有列")

    整理后 = []
    for 行 in 行列表:
        新行 = ["" if 值 is None else str(值) for 值 in 行]
        新行 += [""] * (列数 - len(新行))
        整理后.append(新行)
    return 整理后, 列数


def _解析返回体(响应):
    try:
        外层 = 响应.json()
    except ValueError:
        raise RuntimeError(f"AirScript 返回的不是 JSON: {响应.text[:300]}")

    if not isinstance(外层, dict):
        raise RuntimeError(f"AirScript 返回结构异常: {str(外层)[:300]}")

    错误信息 = 外层.get("error") or ""
    if 错误信息:
        raise RuntimeError(f"脚本执行报错: {错误信息}")

    状态 = str(外层.get("status") or "").lower()
    if 状态 and 状态 not in ("finished", "finish", "success", "ok"):
        raise RuntimeError(f"脚本未正常结束: status={状态}, error={错误信息}")

    数据 = 外层.get("data") or {}
    结果 = 数据.get("result")
    if isinstance(结果, str):
        try:
            结果 = json.loads(结果)
        except ValueError:
            pass

    日志 = 数据.get("logs") or []
    脚本错误 = [
        条 for 条 in 日志
        if isinstance(条, dict) and str(条.get("level", "")).lower() in ("error", "warn", "warning")
    ]

    return 结果, 日志, 脚本错误


def 追加行(行列表, 配置=None, sheet_name=None, dry_run=False, ping=False, 日志器=None):
    """把二维数组追加到在线表格末尾，返回详细结果 dict（ok / message / result）。"""
    配置 = 配置 or 读配置()
    表名 = sheet_name or 配置["sheet_name"]

    try:
        if ping:
            有效行, 列数 = [], 0
        else:
            有效行, 列数 = _整理行(行列表)
    except ValueError as e:
        return {"ok": False, "message": str(e)}

    if not 配置["webhook"] or not 配置["token"]:
        return {
            "ok": False,
            "message": f"AirScript 未配置完整，请在 {获取配置文件路径()} 的 WPS 段填写 webhook / token",
        }

    选项 = {
        "ping": bool(ping),
        "dedup": bool(配置["dedup"]),
        "numeric_columns": 配置["numeric_columns"],
    }
    if 配置["start_row"]:
        选项["start_row"] = int(配置["start_row"])

    载荷 = {
        "Context": {
            "argv": {
                "sheet_name": 表名,
                "rows": 有效行,
                "options": 选项,
            }
        }
    }

    if dry_run:
        _输出(日志器, "info", f"[dry-run] 目标工作表={表名}，将追加 {len(有效行)} 行 x {列数} 列，未发送")
        for 行 in 有效行[:2]:
            _输出(日志器, "info", f"[dry-run] 预览: {行[:6]}")
        return {"ok": True, "message": "dry-run，未写入", "result": {"written": 0}}

    _输出(日志器, "info", f"开始后台写入 WPS：{表名}，{len(有效行)} 行 x {列数} 列" if not ping else "开始探测 AirScript（不写入）")

    try:
        响应 = requests.post(
            配置["webhook"],
            headers={
                "Content-Type": "application/json",
                "AirScript-Token": 配置["token"],
            },
            json=载荷,
            timeout=配置["timeout"],
        )
    except requests.RequestException as e:
        return {"ok": False, "message": f"AirScript 请求失败: {e}"}

    if 响应.status_code in (401, 403):
        return {"ok": False, "message": f"AirScript 令牌无效或已过期（HTTP {响应.status_code}），请在脚本编辑器重新生成脚本令牌"}
    if 响应.status_code != 200:
        return {"ok": False, "message": f"AirScript HTTP {响应.status_code}: {响应.text[:300]}"}

    try:
        结果, 日志, 脚本错误 = _解析返回体(响应)
    except RuntimeError as e:
        return {"ok": False, "message": str(e)}

    if not isinstance(结果, dict) or 结果.get("ok") is not True:
        详情 = 结果 if isinstance(结果, dict) else str(结果)
        return {"ok": False, "message": f"脚本未确认写入成功: {详情}", "result": 结果, "logs": 日志}

    if 脚本错误:
        _输出(日志器, "warning", f"AirScript 日志中有告警: {脚本错误[:3]}")

    if not ping:
        实际写入 = 结果.get("written")
        if 实际写入 is not None and int(实际写入) != len(有效行) and not 结果.get("duplicated"):
            return {
                "ok": False,
                "message": f"写入行数不一致：预期 {len(有效行)}，实际 {实际写入}",
                "result": 结果,
            }

    消息 = (
        f"AirScript 连通正常，工作表={表名}，当前最后一行={结果.get('last_row')}"
        if ping else
        f"后台写入完成：{结果.get('start_row')} 行起，共 {结果.get('written')} 行"
        + ("（重复数据已跳过）" if 结果.get("duplicated") else "")
    )
    _输出(日志器, "info", 消息)
    return {"ok": True, "message": 消息, "result": 结果, "logs": 日志}


def wps_append_data(data_list=None, is_today_order=True, df=None, tsv_text=None, 日志器=None):
    """兼容 wps_playwright.wps_append_data 的入口，返回 bool。

    优先使用直接传入的 df / tsv_text（不碰系统剪贴板）；
    都没传时才从剪贴板读取，方便与旧的调用方式平滑替换。
    """
    try:
        if df is not None:
            行列表 = dataframe转行(df)
        elif tsv_text is not None:
            行列表 = tsv转行(tsv_text)
        elif data_list is not None:
            if hasattr(data_list, "values"):
                行列表 = dataframe转行(data_list)
            elif isinstance(data_list, str):
                行列表 = tsv转行(data_list)
            else:
                行列表 = [list(行) for 行 in data_list]
        else:
            行列表 = tsv转行(读剪贴板文本())

        结果 = 追加行(行列表, 日志器=日志器)
        if not 结果["ok"]:
            _输出(日志器, "error", 结果["message"])
        return 结果["ok"]
    except Exception as e:
        _输出(日志器, "error", f"AirScript 后台写入异常: {e}")
        return False


def _命令行():
    解析器 = argparse.ArgumentParser(description="金山文档在线表格后台追加数据（无需浏览器）")
    解析器.add_argument("--check", action="store_true", help="只检查配置是否就绪，不联网")
    解析器.add_argument("--ping", action="store_true", help="联网验证令牌/脚本/表名，不写入任何数据")
    解析器.add_argument("--dry-run", action="store_true", help="只预览将写入的数据，不发送")
    解析器.add_argument("--from-clipboard", action="store_true", help="从系统剪贴板读取 TSV")
    解析器.add_argument("--file", help="从 TSV 文件读取")
    解析器.add_argument("--tsv", help="直接传入 TSV 文本")
    解析器.add_argument("--sheet", help="覆盖目标工作表名")
    参数 = 解析器.parse_args()

    配置 = 读配置()

    if 参数.check:
        print(f"配置文件: {获取配置文件路径()}")
        print(f"模式: {配置['模式']}")
        print(f"webhook: {'已配置' if 配置['webhook'] else '未配置'}")
        print(f"token: {'已配置' if 配置['token'] else '未配置'}")
        print(f"工作表名: {配置['sheet_name']}")
        print(f"配置就绪: {配置就绪()}")
        return 0 if 配置就绪() else 2

    if 参数.ping:
        结果 = 追加行([], 配置=配置, sheet_name=参数.sheet, ping=True)
        print(结果["message"])
        return 0 if 结果["ok"] else 1

    if 参数.tsv:
        文本 = 参数.tsv
    elif 参数.file:
        with open(参数.file, "r", encoding="utf-8-sig") as f:
            文本 = f.read()
    elif 参数.from_clipboard:
        文本 = 读剪贴板文本()
    else:
        解析器.error("请指定数据来源：--from-clipboard / --file / --tsv，或使用 --check / --ping")
        return 2

    行列表 = tsv转行(文本)
    结果 = 追加行(行列表, 配置=配置, sheet_name=参数.sheet, dry_run=参数.dry_run)
    print(结果["message"])
    return 0 if 结果["ok"] else 1


if __name__ == "__main__":
    sys.exit(_命令行())
