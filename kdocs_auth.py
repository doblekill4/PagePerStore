# -*- coding: utf-8 -*-
"""kdocs-cli Token 登录与有效期管理。

背景（调研结论 2026-11-16）：
- kdocs-cli 的 token 存在 Windows 系统密钥链，跨会话持久化；但 CLI 没有 refresh
  子命令，也没有查询有效期的命令。
- WPS SkillHub 的 code→token 交换接口在登录成功时返回 expires_in（秒）。本地
  get-token.sh 把它换算成小时打印；用户记忆中的「8760 小时」= 31536000 秒 = 1 年，
  是服务端下发的 expires_in，不是 CLI 写死的常量，且本地 get-token.ps1/js 只提取
  该字段、不保存、不展示。
- SkillHub 流程只看到 code → token/expires_in，没有 refresh_token，因此**无法静默
  刷新**，到期只能重新登录（浏览器）。setup.sh 里名为 refresh_token_via_login 的
  函数实际是「重新跑 get-token.sh 登录」，不是 OAuth refresh。

本模块用途：
- 登录()：浏览器登录换取 token + expires_in，同步写入 kdocs-cli 密钥链，并把精确
  到期时间记录到本地**非敏感**元数据文件（不含 token）。
- 检查并告警()：运行时检查认证状态；失效或剩余不足 7 天时发邮件报警，每天最多一次。

用法：
  python kdocs_auth.py --login    # 重新登录并记录有效期（替换 kdocs-cli auth login）
  python kdocs_auth.py --check    # 查看认证状态 / 剩余有效期 / 是否触发告警
"""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid
import webbrowser
from datetime import datetime
from pathlib import Path

交换地址 = "https://api.wps.cn/office/v5/ai/skill_hub/wps_auth/exchange"
回调模板 = "https://api.wps.cn/office/v5/ai/skill_hub/users/callback?code={code}"
登录模板 = "https://account.wps.cn/login?cb={cb}"
元数据路径 = Path(os.environ.get("LOCALAPPDATA") or str(Path.home())) / "PagePerStore" / "kdocs_token_meta.json"
告警提前秒 = 7 * 24 * 3600
# Windows 下调用 kdocs-cli（控制台程序）时隐藏窗口，避免闪黑框；非 Windows 退化为 0。
_无窗口标志 = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _输出(日志器, 级别, 消息):
    if 日志器 is not None and hasattr(日志器, 级别):
        getattr(日志器, 级别)(消息)
    else:
        print(消息)


def cli路径():
    找到 = shutil.which("kdocs-cli")
    if 找到:
        return 找到
    本地 = Path(os.environ.get("LOCALAPPDATA", "")) / "kdocs-cli" / "kdocs-cli.exe"
    return str(本地) if 本地.exists() else ""


def _读元数据():
    try:
        with open(元数据路径, "r", encoding="utf-8") as f:
            数据 = json.load(f)
        return 数据 if isinstance(数据, dict) else {}
    except (OSError, ValueError):
        return {}


def _写元数据(数据):
    元数据路径.parent.mkdir(parents=True, exist_ok=True)
    临时 = 元数据路径.with_suffix(".tmp")
    with open(临时, "w", encoding="utf-8") as f:
        json.dump(数据, f, ensure_ascii=False, indent=2)
    os.replace(临时, 元数据路径)


def 记录有效期(expires_in):
    """在拿到新 token 后调用，记录精确到期时间（不保存 token 本身）。"""
    try:
        秒 = int(expires_in)
    except (TypeError, ValueError):
        秒 = 0
    if 秒 <= 0:
        秒 = 31536000  # 服务端异常返回时按 1 年兜底，并在元数据中标记 source
    现在 = time.time()
    数据 = _读元数据()
    数据.update({
        "issued_at": 现在,
        "expires_in": 秒,
        "expires_at": 现在 + 秒,
        "issued_date": datetime.fromtimestamp(现在).strftime("%Y-%m-%d %H:%M:%S"),
        "source": "server" if 秒 > 0 and expires_in else "fallback_1year",
    })
    数据.pop("last_warn_date", None)
    数据.pop("invalidated_at", None)
    数据.pop("invalid_reason", None)
    _写元数据(数据)
    return 数据


def 重置有效期(原因="登录失效"):
    """确认需要重登时立即作废旧计数，避免继续用过期时间戳误判。

    保留 invalidated_at / invalid_reason 供排查；issued_at / expires_at /
    expires_in 全部清掉，剩余有效期秒() 随即返回 None，直到下次 --login 重新记录。
    """
    数据 = _读元数据()
    for 键 in ("issued_at", "expires_at", "expires_in", "issued_date", "last_warn_date", "source"):
        数据.pop(键, None)
    数据["invalidated_at"] = time.time()
    数据["invalid_reason"] = str(原因)[:300]
    _写元数据(数据)
    return 数据


def 剩余有效期秒():
    """返回剩余秒数；未记录有效期时返回 None。"""
    数据 = _读元数据()
    到期 = 数据.get("expires_at")
    if not isinstance(到期, (int, float)):
        return None
    return 到期 - time.time()


def 认证状态():
    """调用 kdocs-cli auth status，返回 (是否认证, 原始输出)。

    与 wps_kdocs._环境() 保持一致：屏蔽残留的 KINGSOFT_DOCS_TOKEN 环境变量，
    只认系统密钥链。否则 env token 会让 status 误报已登录，但业务写入（已 pop
    掉 env token）实际会 400006，导致判断与写入不一致。
    """
    路径 = cli路径()
    if not 路径:
        return False, "找不到 kdocs-cli"
    环境 = os.environ.copy()
    环境.pop("KINGSOFT_DOCS_TOKEN", None)
    try:
        结果 = subprocess.run(
            [路径, "auth", "status"], capture_output=True, text=True,
            encoding="utf-8", timeout=30, env=环境, creationflags=_无窗口标志,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"auth status 调用失败: {e}"
    文本 = (结果.stdout or "").strip()
    if 结果.returncode != 0:
        return False, (结果.stderr or 文本 or "auth status 失败")[:300]
    try:
        数据 = json.loads(文本)
        return bool(数据.get("authenticated")), 文本
    except ValueError:
        return False, f"auth status 返回非 JSON: {文本[:200]}"


def _写入密钥链(token):
    路径 = cli路径()
    if not 路径 or not token:
        return False
    try:
        结果 = subprocess.run(
            [路径, "auth", "set-token", "-"], input=token,
            capture_output=True, text=True, encoding="utf-8", timeout=30,
            creationflags=_无窗口标志,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return 结果.returncode == 0


def _交换(code, timeout=10):
    请求 = urllib.request.Request(
        交换地址,
        data=json.dumps({"code": code}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(请求, timeout=timeout) as 响应:
        return json.loads(响应.read().decode("utf-8"))


def 登录(等待秒=300, 日志器=None):
    """浏览器登录，token 写入 CLI 密钥链并记录有效期。返回 (成功, 说明)。"""
    if not cli路径():
        return False, "找不到 kdocs-cli，请先安装"
    code = str(uuid.uuid4())
    回调 = 回调模板.format(code=code)
    登录链接 = 登录模板.format(cb=urllib.parse.quote(回调, safe=""))
    _输出(日志器, "info", "请在浏览器完成 WPS 登录（若未自动打开请手动复制下面的链接）：")
    _输出(日志器, "info", 登录链接)
    try:
        webbrowser.open(登录链接)
    except Exception:
        pass

    开始 = time.time()
    while time.time() - 开始 < 等待秒:
        try:
            响应 = _交换(code)
        except Exception:
            响应 = {}
        返回码 = str(响应.get("code", ""))
        数据 = 响应.get("data") if isinstance(响应.get("data"), dict) else 响应
        token = 数据.get("token") or 响应.get("token")
        if 返回码 == "200" and token:
            if not _写入密钥链(token):
                return False, "已拿到 token，但写入 kdocs-cli 密钥链失败"
            expires_in = 数据.get("expires_in", 响应.get("expires_in", 0))
            元数据 = 记录有效期(expires_in)
            小时 = round(元数据["expires_in"] / 3600, 1)
            return True, f"登录成功，token 已写入密钥链；服务端有效期 {元数据['expires_in']} 秒（约 {小时} 小时）"
        if 返回码 == "403":
            return False, "企业账号被拒绝，请使用个人 WPS 账号"
        if 返回码 == "409":
            return False, "登录已取消"
        time.sleep(1)
    return False, f"等待登录超时（{等待秒} 秒）"


def _发邮件(标题, 正文, 日志器=None):
    try:
        from 邮件通知 import 邮件通知器
        通知器 = 邮件通知器(logger=日志器)
        return 通知器._send_mail(标题, 正文, is_error=True)
    except Exception as e:
        _输出(日志器, "error", f"发送告警邮件失败: {e}")
        return False


def _拉起登录并复查(日志器, 原因):
    """手动触发时使用：拉起浏览器登录，成功后复查密钥链，不自动重试写入以外的事。"""
    _输出(日志器, "info", f"检测到{原因}，正在拉起 kdocs-cli 登录页，请在浏览器完成登录…")
    成功, 说明 = 登录(日志器=日志器)
    if not 成功:
        return False, f"自动拉起登录失败：{说明}"
    已认证, 状态文本 = 认证状态()
    if not 已认证:
        return False, f"登录流程已结束，但 CLI 认证状态仍为失效：{状态文本[:200]}"
    return True, f"已自动重新登录并写入密钥链：{说明}"


def 检查并告警(日志器=None, 发邮件=True, 失败时登录=False):
    """运行时检查。返回 (认证是否可用, 说明)。

    失效/临期时默认发邮件、不自动登录（定时无人值守场景）。
    手动触发时传 发邮件=False, 失败时登录=True，直接拉起浏览器登录。
    """
    已认证, 状态文本 = 认证状态()
    if not 已认证:
        重置有效期("auth status 失效：" + 状态文本[:200])
        正文 = (f"kdocs-cli 登录态失效，后台写入将无法进行。\n\n"
                f"auth status 返回：{状态文本}\n\n"
                f"旧的有效期计数已立即作废。处理方式：运行 python kdocs_auth.py --login "
                f"重新登录（浏览器），脚本会同步写入密钥链并记录新的有效期。")
        _输出(日志器, "error", "kdocs-cli 登录态失效，需要重新登录；旧有效期计数已重置")
        if 发邮件:
            _发邮件("【PagePerStore】kdocs-cli 登录失效，请重新登录", 正文, 日志器)
        if 失败时登录:
            return _拉起登录并复查(日志器, "登录态失效")
        return False, "kdocs-cli 登录态失效，需要重新登录；旧有效期计数已重置"

    剩余 = 剩余有效期秒()
    if 剩余 is None:
        return True, "认证有效；未记录有效期，请用 python kdocs_auth.py --login 登录一次以启用到期预警"

    天 = 剩余 / 86400
    if 天 < 0:
        重置有效期("按记录已过期")
        正文 = ("kdocs-cli token 按记录已过期，请立即重新登录："
                "python kdocs_auth.py --login。旧的有效期计数已作废。")
        _输出(日志器, "error", "kdocs-cli token 已过期；旧有效期计数已重置")
        if 发邮件:
            _发邮件("【PagePerStore】kdocs-cli token 已过期，请重新登录", 正文, 日志器)
        if 失败时登录:
            return _拉起登录并复查(日志器, "token 已过期")
        return False, "kdocs-cli token 已过期，需要重新登录；旧有效期计数已重置"

    if 剩余 < 告警提前秒:
        元数据 = _读元数据()
        今天 = datetime.now().strftime("%Y-%m-%d")
        if 元数据.get("last_warn_date") != 今天:
            元数据["last_warn_date"] = 今天
            _写元数据(元数据)
            _输出(日志器, "warning",
                  f"kdocs-cli token 仅剩 {天:.1f} 天，请运行 python kdocs_auth.py --login 重新登录"
                  f"（临期只记日志、不发邮件）")
        return True, f"认证有效，但 token 仅剩 {天:.1f} 天，已触发到期预警（仅日志）"

    return True, f"认证有效，token 剩余 {天:.0f} 天"


def _命令行():
    参数 = sys.argv[1:]
    if "--login" in 参数:
        成功, 说明 = 登录()
        print(说明)
        return 0 if 成功 else 1
    if "--reset" in 参数:
        数据 = 重置有效期("手动重置")
        print(f"有效期计数已重置：{数据['invalidated_at']}（{数据['invalid_reason']}）")
        return 0
    if "--check" in 参数:
        已认证, 状态文本 = 认证状态()
        print(f"认证状态: {'有效' if 已认证 else '失效'}")
        print(f"CLI 返回: {状态文本}")
        元数据 = _读元数据()
        if 元数据.get("invalidated_at"):
            print(f"旧计数已作废: {datetime.fromtimestamp(元数据['invalidated_at']).strftime('%Y-%m-%d %H:%M:%S')}"
                  f"（{元数据.get('invalid_reason', '')}）")
        剩余 = 剩余有效期秒()
        if 剩余 is None:
            print("有效期: 未记录（运行 python kdocs_auth.py --login 记录）")
        else:
            print(f"有效期: 剩余 {剩余 / 86400:.1f} 天")
        可用, 说明 = 检查并告警(发邮件="--no-mail" not in 参数)
        print(f"告警检查: {说明}")
        return 0 if 可用 else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(_命令行())
