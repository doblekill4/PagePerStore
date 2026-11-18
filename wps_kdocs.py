# -*- coding: utf-8 -*-
"""金山文档在线表格后台写入（kdocs-cli）。

链路：拉取订单 → 读尾部窗口 → 本地按 B~N 差集清洗 → 一次写增量 → 回读校验。
不启动浏览器、不占窗口焦点、不经过系统剪贴板；写入前完成去重，避免云端异步
去重脚本带来的 8~16 秒延迟和重复写入。

写入值的类型保护：所有值统一加单引号前缀（'值），强制按文本写入，避免手机号丢
前导零、长订单号变科学计数法、日期被转成序列号。空值写空字符串、不加前缀。
实测该写法不改变单元格 numFormat，也不会把单元格变成公式。

依赖：本机安装 kdocs-cli 并完成一次 `kdocs-cli auth login`（凭据存系统密钥链）。
配置：程序同目录 config.json 的 "WPS_KDOCS" 段，见 config.example.json。

命令行：
  python wps_kdocs.py --check                      # 检查 CLI/登录/表格连通（只读）
  python wps_kdocs.py --dry-run --tsv "..."        # 预览清洗后的增量，不写入
  python wps_kdocs.py --file data.tsv             # 从 TSV 文件写入增量
"""

import argparse
import csv
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

from 本地配置 import 加载配置, 取值, 获取配置文件路径

数据列数 = 14          # A~N；DataFrame 实际 13 列（A~M），N 列恒为空
判重列 = range(1, 14)  # B~N，与云端「删除一店一页完全相同的行」规则一致
日期列 = 3             # D 列（配送或自提日期）
单批操作数 = 800       # 单次 update-range-data 的操作条数上限

_文件ID缓存 = ""
# Windows 下调用 kdocs-cli（控制台程序）时隐藏窗口，避免定时任务 / GUI 运行时闪黑框；
# 非 Windows 平台该常量不存在，退化为 0 不影响行为。
_无窗口标志 = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _输出(日志器, 级别, 消息):
    if 日志器 is not None and hasattr(日志器, 级别):
        getattr(日志器, 级别)(消息)
    else:
        print(消息)


def _环境():
    env = os.environ.copy()
    # 用户已完成登录持久化：密钥链为准，屏蔽可能残留的旧环境变量
    env.pop("KINGSOFT_DOCS_TOKEN", None)
    return env


def 读配置():
    数据 = 加载配置()
    段 = 取值(数据, "WPS_KDOCS", {}) or {}
    if not isinstance(段, dict):
        段 = {}

    def 取(键, 默认=None):
        环境变量 = os.environ.get("WPS_KDOCS_" + 键.upper())
        return 环境变量 if 环境变量 else 段.get(键, 默认)

    try:
        尾部行数 = int(取("tail_rows", 200))
    except (TypeError, ValueError):
        尾部行数 = 200
    try:
        超时 = int(取("timeout", 90))
    except (TypeError, ValueError):
        超时 = 90
    try:
        工作表ID = int(取("sheet_id", 4))
    except (TypeError, ValueError):
        工作表ID = 4

    return {
        "启用": str(取("enabled", True)).strip().lower() not in ("false", "0", "no", "off", ""),
        "cli_path": str(取("cli_path", "") or ""),
        "file_id": str(取("file_id", "") or "").strip(),
        # 默认目标表格链接：旧 config.json 没有 WPS_KDOCS 段时也能直接启用；
        # 换表格时在 config.json 覆盖即可
        "link_id": str(取("link_id", "ceIalhfmfGZ6") or "").strip(),
        "sheet_id": 工作表ID,
        "sheet_name": str(取("sheet_name", "服务一店一页") or "服务一店一页"),
        "tail_rows": max(50, 尾部行数),
        "timeout": max(20, 超时),
    }


def _cli路径(配置):
    候选 = 配置["cli_path"]
    if 候选 and os.path.exists(候选):
        return 候选
    找到 = shutil.which("kdocs-cli")
    if 找到:
        return 找到
    本地 = os.path.join(os.environ.get("LOCALAPPDATA", ""), "kdocs-cli", "kdocs-cli.exe")
    return 本地 if os.path.exists(本地) else ""


def _cli(配置, 服务, 动作, 参数=None):
    路径 = _cli路径(配置)
    if not 路径:
        return {"code": -1, "message": "找不到 kdocs-cli，请先安装并运行 kdocs-cli auth login"}

    命令 = [路径, 服务, 动作]
    临时文件 = None
    if 参数 is not None:
        临时文件 = os.path.join(tempfile.gettempdir(), f"_wpsk_{os.getpid()}_{time.time_ns()}.json")
        with open(临时文件, "w", encoding="utf-8") as f:
            json.dump(参数, f, ensure_ascii=False)
        命令.append("@" + 临时文件)
    命令 += ["--output", "json"]

    try:
        结果 = subprocess.run(
            命令, capture_output=True, text=True, encoding="utf-8",
            env=_环境(), timeout=配置["timeout"], creationflags=_无窗口标志,
        )
    except subprocess.TimeoutExpired:
        return {"code": -1, "message": f"kdocs-cli 调用超时（{服务}.{动作}）"}
    except OSError as e:
        return {"code": -1, "message": f"kdocs-cli 调用失败: {e}"}
    finally:
        if 临时文件 and os.path.exists(临时文件):
            try:
                os.remove(临时文件)
            except OSError:
                pass

    if 结果.returncode != 0:
        return {"code": -1, "message": (结果.stderr or 结果.stdout or "").strip()[:300]}
    try:
        响应 = json.loads(结果.stdout)
    except ValueError:
        return {"code": -1, "message": f"kdocs-cli 返回非 JSON: {(结果.stdout or '')[:200]}"}
    if str(响应.get("code")) == "400006":
        try:
            from kdocs_auth import 重置有效期
            重置有效期(f"{服务}.{动作} 返回 400006")
        except Exception:
            pass
    return 响应


def _取数据(响应):
    data = 响应.get("data") or {}
    if not isinstance(data, dict):
        return {}
    return data.get("detail") if isinstance(data.get("detail"), dict) else data


def _取单元格(响应):
    数据 = _取数据(响应)
    return 数据.get("rangeData") or []


def 文件ID(配置):
    """优先用配置里的 file_id，否则由分享链接解析（进程内缓存）。"""
    global _文件ID缓存
    if 配置["file_id"]:
        return 配置["file_id"]
    if _文件ID缓存:
        return _文件ID缓存
    if not 配置["link_id"]:
        return ""
    响应 = _cli(配置, "drive", "get-share-info", {"link_id": 配置["link_id"]})
    if 响应.get("code") != 0:
        return ""
    _文件ID缓存 = str(_取数据(响应).get("file_id") or "")
    return _文件ID缓存


def 配置就绪():
    配置 = 读配置()
    return bool(配置["启用"] and _cli路径(配置) and (配置["file_id"] or 配置["link_id"]))


def dataframe转行(df):
    副本 = df.fillna("").astype(str)
    副本 = 副本.replace({"^nan$": "", "^NaN$": ""}, regex=True)
    return 副本.values.tolist()


def tsv转行(文本):
    行列表 = []
    for 行 in csv.reader(io.StringIO(文本), delimiter="\t"):
        if 行 and any(str(单元).strip() for 单元 in 行):
            行列表.append([str(单元) for 单元 in 行])
    return 行列表


def _补齐(行):
    新行 = ["" if 值 is None else str(值) for 值 in 行][:数据列数]
    新行 += [""] * (数据列数 - len(新行))
    return 新行


def _键(行):
    return "\u0001".join(行[c] for c in 判重列)


def 找最后订单行(行字典):
    """以 B 列（商品名称）非空判定有效订单行。

    手工删除订单时可能只清掉部分单元格，残留 L 列门店手机号等辅助值；
    若把这类空洞行当成数据行，写入位置会跳到空洞下方，中间留下空行。
    """
    有数据的行 = [r for r, 单元 in 行字典.items() if str(单元.get(1) or "").strip()]
    if not 有数据的行:
        raise RuntimeError("尾部窗口内没有有效订单行（B列均为空），无法定位最后一行")
    return max(有数据的行)


def 读尾部(配置, 文件标识):
    """读尾部窗口，返回 (行字典, 真实最后数据行, 工作表已用末行)。"""
    响应 = _cli(配置, "sheet", "get-sheets-info", {"file_id": 文件标识})
    if 响应.get("code") != 0:
        raise RuntimeError(f"获取工作表信息失败: {响应.get('message')}")
    工作表列表 = _取数据(响应).get("sheetsInfo") or []
    目标 = next((s for s in 工作表列表 if s.get("sheetId") == 配置["sheet_id"]), None)
    if not 目标:
        raise RuntimeError(f"找不到 sheetId={配置['sheet_id']} 的工作表")
    已用末行 = int(目标.get("rowTo") or 0)
    起始 = max(0, 已用末行 - 配置["tail_rows"] + 1)

    响应 = _cli(配置, "sheet", "get-range-data", {
        "file_id": 文件标识, "sheetId": 配置["sheet_id"],
        "range": {"rowFrom": 起始, "rowTo": 已用末行, "colFrom": 0, "colTo": 数据列数 - 1},
    })
    if 响应.get("code") != 0:
        raise RuntimeError(f"读取尾部数据失败: {响应.get('message')}")

    行字典 = {}
    for 单元 in _取单元格(响应):
        if not isinstance(单元, dict):
            continue
        r = 单元.get("rowFrom")
        if r is None:
            continue
        行字典.setdefault(r, {})[单元.get("colFrom", 0)] = str(单元.get("cellText") or "")

    真实最后行 = 找最后订单行(行字典)
    return 行字典, 真实最后行, 已用末行


def 清洗增量(新行列表, 行字典, 真实最后行):
    """按目标日期筛出表格内候选行，按 B~N 全字段做差集。"""
    补齐后 = [_补齐(行) for 行 in 新行列表]
    if not 补齐后:
        return []

    目标日期 = {行[日期列][:10] for 行 in 补齐后 if 行[日期列][:10]}
    已有键 = set()
    for r, 单元 in 行字典.items():
        if r > 真实最后行:
            continue
        日期 = 单元.get(日期列, "")[:10]
        if 目标日期 and 日期 not in 目标日期:
            continue
        已有键.add(_键([单元.get(c, "") for c in range(数据列数)]))

    增量 = []
    for 行 in 补齐后:
        键 = _键(行)
        if 键 in 已有键:
            continue
        已有键.add(键)   # 同时去掉本次批次内的重复
        增量.append(行)
    return 增量


def 检查目标区域(配置, 文件标识, 起始行, 行数):
    """写入前确认目标区域没有已有订单，防止定位偏差覆盖真实数据。"""
    响应 = _cli(配置, "sheet", "get-range-data", {
        "file_id": 文件标识, "sheetId": 配置["sheet_id"],
        "range": {"rowFrom": 起始行, "rowTo": 起始行 + 行数 - 1,
                  "colFrom": 0, "colTo": 数据列数 - 1},
    })
    if 响应.get("code") != 0:
        return False, f"目标区域检查失败: {响应.get('message')}"
    行字典 = {}
    for 单元 in _取单元格(响应):
        if isinstance(单元, dict) and 单元.get("rowFrom") is not None:
            行字典.setdefault(单元["rowFrom"], {})[单元.get("colFrom", 0)] = str(单元.get("cellText") or "")
    for r in range(起始行, 起始行 + 行数):
        if str(行字典.get(r, {}).get(1) or "").strip():
            return False, f"第 {r} 行已有订单数据（B列非空），为防止覆盖已中止写入"
    return True, ""


def 写入增量(配置, 文件标识, 增量, 起始行):
    操作 = []
    for i, 行 in enumerate(增量):
        for c, 值 in enumerate(行[:数据列数]):
            文本 = "" if 值 is None else str(值)
            公式 = ("'" + 文本) if 文本 else ""
            操作.append({
                "opType": "formula",
                "rowFrom": 起始行 + i, "rowTo": 起始行 + i,
                "colFrom": c, "colTo": c,
                "formula": 公式,
            })

    for 批起始 in range(0, len(操作), 单批操作数):
        响应 = _cli(配置, "sheet", "update-range-data", {
            "file_id": 文件标识, "sheetId": 配置["sheet_id"],
            "rangeData": 操作[批起始:批起始 + 单批操作数],
        })
        if 响应.get("code") != 0:
            return False, f"写入失败（第 {批起始 // 单批操作数 + 1} 批）: {响应.get('message')}"
    return True, ""


def 回读校验(配置, 文件标识, 增量, 起始行):
    响应 = _cli(配置, "sheet", "get-range-data", {
        "file_id": 文件标识, "sheetId": 配置["sheet_id"],
        "range": {"rowFrom": 起始行, "rowTo": 起始行 + len(增量) - 1,
                  "colFrom": 0, "colTo": 数据列数 - 1},
    })
    if 响应.get("code") != 0:
        return False, f"回读失败: {响应.get('message')}"
    行字典 = {}
    for 单元 in _取单元格(响应):
        if isinstance(单元, dict) and 单元.get("rowFrom") is not None:
            行字典.setdefault(单元["rowFrom"], {})[单元.get("colFrom", 0)] = str(单元.get("cellText") or "")

    for i, 期望 in enumerate(增量):
        实际 = 行字典.get(起始行 + i, {})
        for c in range(数据列数):
            if 实际.get(c, "") != 期望[c]:
                return False, (f"第 {起始行 + i} 行第 {c + 1} 列不一致: "
                               f"期望 {期望[c][:20]!r}，实际 {实际.get(c, '')[:20]!r}")
    return True, ""


def 追加订单(df=None, tsv_text=None, data_list=None, dry_run=False, 日志器=None, 是否手动=False):
    """后台写入主入口，返回详细结果 dict。

    是否手动=True（UI 按钮触发）：token 失效时直接拉起 CLI 登录页，不发邮件；
    默认 False（定时自动）：token 失效只发邮件，不弹浏览器。
    """
    配置 = 读配置()
    try:
        from kdocs_auth import 检查并告警
        可用, 说明 = 检查并告警(日志器=日志器, 发邮件=not 是否手动, 失败时登录=是否手动)
        if not 可用:
            return {"ok": False, "message": 说明}
        _输出(日志器, "info", f"登录有效期检查：{说明}")
    except Exception as e:
        _输出(日志器, "warning", f"登录有效期检查未完成: {e}")
    try:
        文件标识 = 文件ID(配置)
        if not 文件标识:
            return {"ok": False, "message": f"未配置 file_id / link_id，请检查 {获取配置文件路径()} 的 WPS_KDOCS 段"}

        if df is not None:
            新行列表 = dataframe转行(df)
        elif tsv_text is not None:
            新行列表 = tsv转行(tsv_text)
        elif data_list is not None:
            if hasattr(data_list, "values"):
                新行列表 = dataframe转行(data_list)
            elif isinstance(data_list, str):
                新行列表 = tsv转行(data_list)
            else:
                新行列表 = [list(行) for 行 in data_list]
        else:
            return {"ok": False, "message": "未提供数据：请传 df / tsv_text / data_list 之一"}

        行字典, 真实最后行, 已用末行 = 读尾部(配置, 文件标识)
        增量 = 清洗增量(新行列表, 行字典, 真实最后行)
        起始行 = 真实最后行 + 1
        _输出(日志器, "info",
              f"后台同步：尾部窗口 {配置['tail_rows']} 行，真实最后数据行 {真实最后行}"
              f"（已用末行 {已用末行}），原始 {len(新行列表)} 行 → 增量 {len(增量)} 行")

        if not 增量:
            return {"ok": True, "message": "无新增订单，未执行写入", "written": 0,
                    "start_row": 起始行, "existing": len(新行列表)}

        if dry_run:
            _输出(日志器, "info", f"[dry-run] 将写入 {起始行} 行起的 {len(增量)} 行，未发送")
            return {"ok": True, "message": f"dry-run：增量 {len(增量)} 行，未写入",
                    "written": 0, "start_row": 起始行, "preview": 增量[:2]}

        检查通过, 错误 = 检查目标区域(配置, 文件标识, 起始行, len(增量))
        if not 检查通过:
            return {"ok": False, "message": 错误, "start_row": 起始行}

        成功, 错误 = 写入增量(配置, 文件标识, 增量, 起始行)
        if not 成功:
            return {"ok": False, "message": 错误, "start_row": 起始行}

        校验通过, 错误 = 回读校验(配置, 文件标识, 增量, 起始行)
        if not 校验通过:
            return {"ok": False, "message": f"写入后校验未通过: {错误}", "start_row": 起始行}

        消息 = f"后台写入完成：第 {起始行} 行起共 {len(增量)} 行，已回读校验"
        _输出(日志器, "info", 消息)
        return {"ok": True, "message": 消息, "written": len(增量), "start_row": 起始行}
    except Exception as e:
        return {"ok": False, "message": f"kdocs-cli 后台写入异常: {e}"}


def wps_append_data(data_list=None, is_today_order=True, df=None, tsv_text=None, 日志器=None, 是否手动=False):
    """兼容旧调用形态的入口（历史名沿用自已移除的 wps_playwright），返回 bool。

    失败原因保留在 module 级 `最后失败原因`，供 UI 状态栏读取（返回值仍是 bool，
    不破坏兼容契约）。
    """
    global 最后失败原因
    最后失败原因 = ""
    结果 = 追加订单(df=df, tsv_text=tsv_text, data_list=data_list,
                   日志器=日志器, 是否手动=是否手动)
    if not 结果["ok"]:
        最后失败原因 = str(结果.get("message") or "未知原因")
        _输出(日志器, "error", 最后失败原因)
    return 结果["ok"]


最后失败原因 = ""


def _命令行():
    解析器 = argparse.ArgumentParser(description="金山文档在线表格后台增量写入（kdocs-cli，无需浏览器）")
    解析器.add_argument("--check", action="store_true", help="检查 CLI/登录/表格连通（只读）")
    解析器.add_argument("--dry-run", action="store_true", help="只预览清洗结果，不写入")
    解析器.add_argument("--file", help="从 TSV 文件读取")
    解析器.add_argument("--tsv", help="直接传入 TSV 文本")
    参数 = 解析器.parse_args()

    配置 = 读配置()
    if 参数.check:
        print(f"配置文件: {获取配置文件路径()}")
        print(f"CLI: {_cli路径(配置) or '未找到'}")
        print(f"启用: {配置['启用']}, 工作表: {配置['sheet_name']}(ID={配置['sheet_id']}), 尾部窗口: {配置['tail_rows']}")
        print(f"配置就绪: {配置就绪()}")
        if not 配置就绪():
            return 2
        try:
            from kdocs_auth import 检查并告警
            _可用, _说明 = 检查并告警(发邮件=False)
            print(f"登录有效期: {_说明}")
        except Exception as e:
            print(f"登录有效期检查失败: {e}")
        响应 = _cli(配置, "drive", "search-files", {"keyword": "test", "page_size": 1})
        print(f"登录验证: {'通过' if 响应.get('code') == 0 else 响应.get('message')}")
        标识 = 文件ID(配置)
        print(f"file_id: {标识 or '解析失败'}")
        if 标识:
            行字典, 真实最后行, 已用末行 = 读尾部(配置, 标识)
            print(f"尾部读取: {len(行字典)} 行有单元格，真实最后数据行 {真实最后行}，已用末行 {已用末行}")
        return 0

    if 参数.tsv:
        文本 = 参数.tsv
    elif 参数.file:
        with open(参数.file, "r", encoding="utf-8-sig") as f:
            文本 = f.read()
    else:
        解析器.error("请指定 --file / --tsv，或使用 --check")
        return 2

    结果 = 追加订单(tsv_text=文本, dry_run=参数.dry_run)
    print(结果["message"])
    if 参数.dry_run and 结果.get("preview"):
        for 行 in 结果["preview"]:
            print(f"  预览: {行[:6]}")
    return 0 if 结果["ok"] else 1


if __name__ == "__main__":
    sys.exit(_命令行())
