# 邮件通知.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from datetime import datetime
import logging
import traceback

from 本地配置 import 加载配置, 取值

_本地配置 = 加载配置()


class 邮件通知器:
    """邮件通知器（配置来自程序同目录的 config.json，不在源码中保存授权码）"""

    # 邮件配置（来自 config.json 的 邮件 段）
    SMTP_SERVER = 取值(_本地配置, "邮件.SMTP_SERVER", "smtp.qq.com")
    SMTP_PORT = 取值(_本地配置, "邮件.SMTP_PORT", 465)
    SENDER_EMAIL = 取值(_本地配置, "邮件.SENDER_EMAIL", "")
    AUTHORIZATION_CODE = 取值(_本地配置, "邮件.AUTHORIZATION_CODE", "")
    RECIPIENTS = 取值(_本地配置, "邮件.RECIPIENTS", [])

    def __init__(self, logger=None):
        """初始化邮件通知器"""
        self.logger = logger or self._setup_logger()
        self._验证配置()

    # 重新加载配置（首次运行向导写入 config.json 后调用，就地更新类属性）
    @staticmethod
    def 重新加载():
        global _本地配置
        _本地配置 = 加载配置()
        邮件通知器.SMTP_SERVER = 取值(_本地配置, "邮件.SMTP_SERVER", "smtp.qq.com")
        邮件通知器.SMTP_PORT = 取值(_本地配置, "邮件.SMTP_PORT", 465)
        邮件通知器.SENDER_EMAIL = 取值(_本地配置, "邮件.SENDER_EMAIL", "")
        邮件通知器.AUTHORIZATION_CODE = 取值(_本地配置, "邮件.AUTHORIZATION_CODE", "")
        邮件通知器.RECIPIENTS = 取值(_本地配置, "邮件.RECIPIENTS", [])

    def _验证配置(self):
        """验证邮件配置是否正确"""
        if not self.SENDER_EMAIL:
            self.logger.warning("⚠️ 未配置发件邮箱（SENDER_EMAIL），请检查程序同目录的 config.json")
        if not self.AUTHORIZATION_CODE:
            self.logger.warning("⚠️ 未配置邮件授权码（AUTHORIZATION_CODE），请检查程序同目录的 config.json")
        if not self.RECIPIENTS:
            self.logger.warning("⚠️ 未配置收件人（RECIPIENTS），邮件无法发送")

    def _setup_logger(self):
        """设置日志"""
        logger = logging.getLogger('邮件通知')
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        return logger

    def _send_mail(self, subject, content, is_error=False):
        """
        发送邮件
        :param subject: 邮件主题
        :param content: 邮件内容
        :param is_error: 是否为错误通知
        """
        # 验证配置
        if not self.SENDER_EMAIL or not self.AUTHORIZATION_CODE or not self.RECIPIENTS:
            self.logger.error("❌ 邮件配置不完整，请检查程序同目录的 config.json（需含 邮件.SENDER_EMAIL / 邮件.AUTHORIZATION_CODE / 邮件.RECIPIENTS）")
            return False

        try:
            # 创建邮件对象
            msg = MIMEMultipart('alternative')

            # 处理发件人（确保是ASCII字符）
            msg['From'] = self.SENDER_EMAIL

            # 处理收件人
            msg['To'] = ', '.join(self.RECIPIENTS)

            # 处理主题（使用Header处理中文）
            msg['Subject'] = Header(subject, 'utf-8').encode()

            # 添加时间戳
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 构建邮件内容
            if is_error:
                full_content = f"❌ 错误通知\n\n{content}\n\n时间: {timestamp}"
            else:
                full_content = f"✅ 任务通知\n\n{content}\n\n时间: {timestamp}"

            # 添加邮件正文（使用utf-8编码）
            text_part = MIMEText(full_content, 'plain', 'utf-8')
            msg.attach(text_part)

            # 连接SMTP服务器并发送
            self.logger.info(f"正在连接到 {self.SMTP_SERVER}:{self.SMTP_PORT}...")
            with smtplib.SMTP_SSL(self.SMTP_SERVER, self.SMTP_PORT) as server:
                server.login(self.SENDER_EMAIL, self.AUTHORIZATION_CODE)
                server.send_message(msg)

            self.logger.info(f"✅ 邮件发送成功: {subject}")
            return True

        except UnicodeEncodeError as e:
            self.logger.error(f"邮件编码错误: {e}")
            self.logger.error("请检查发件人邮箱和授权码是否包含中文字符")
            return False
        except smtplib.SMTPAuthenticationError as e:
            self.logger.error(f"邮件认证失败: {e}")
            self.logger.error("请检查QQ邮箱和授权码是否正确")
            return False
        except Exception as e:
            self.logger.error(f"邮件发送失败: {e}")
            self.logger.error(traceback.format_exc())
            return False

    def 发送成功通知(self, 任务描述):
        """
        发送成功通知
        :param 任务描述: 任务描述，如"次日订单同步完成"
        """
        subject = f"【订单系统】{任务描述}"
        content = f"""
任务类型: {任务描述}
执行结果: 成功

详细信息:
- 订单已成功导出并同步到WPS表格
- 请登录WPS表格查看最新数据
        """
        return self._send_mail(subject, content, is_error=False)

    def 发送失败通知(self, 错误描述):
        """
        发送失败通知
        :param 错误描述: 错误描述信息
        """
        subject = "【订单系统】任务失败"
        content = f"""
任务执行失败

错误信息: {错误描述}

请检查:
1. 网络连接是否正常
2. 登录状态是否有效
3. WPS表格是否可访问
4. 查看本地日志获取详细信息
        """
        return self._send_mail(subject, content, is_error=True)

    def 发送测试邮件(self):
        """发送测试邮件"""
        subject = "【订单系统】测试邮件"
        content = f"""
这是一封测试邮件

如果您收到此邮件，说明邮件通知功能配置正常。

当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        return self._send_mail(subject, content, is_error=False)



if __name__ == "__main__":
    # 测试代码
    print(配置说明)

    # 取消下面的注释来测试
    # notifier = 邮件通知器()
    # notifier.发送测试邮件()