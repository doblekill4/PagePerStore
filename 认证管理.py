# 认证管理.py - 更新为新平台API
import logging
import json
from datetime import datetime
from 配置 import 配置


class AuthManager:
    def __init__(self, session, base_url, headers, logger=None):
        """初始化认证管理模块"""
        self.session = session
        self.base_url = base_url
        self.headers = headers
        self.token = None
        self.refresh_token = None
        self.username = None
        self.password = None

        if logger:
            self.logger = logger
        else:
            self.setup_logging()

    def setup_logging(self):
        """设置日志记录"""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # 清除现有的处理器
        if self.logger.handlers:
            self.logger.handlers.clear()

        # 创建格式化器
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # 创建控制台处理器（始终存在）
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def login(self, username, password):
        """登录系统并获取token - 适配新平台API"""
        self.username = username
        self.password = password

        self.logger.info("正在登录新平台系统...")

        # 新平台的登录端点
        login_url = f"{self.base_url}{配置.LOGIN_API}"
        login_data = {
            'userName': username,
            'password': password
        }

        try:
            response = self.session.post(
                login_url,
                json=login_data,
                headers=self.headers,
                timeout=10
            )

            self.logger.info(f"登录状态码: {response.status_code}")

            if response.status_code == 200:
                try:
                    result = response.json()
                    self.logger.debug(f"登录响应: {json.dumps(result, ensure_ascii=False)[:200]}...")

                    # 检查登录是否成功 - 新平台可能使用code字段
                    if result.get('code') == 200 or result.get('success') or 'data' in result:
                        # 登录成功，尝试从响应中提取token
                        self.extract_tokens_from_response(result)

                        self.logger.info("登录成功！")

                        # 显示用户信息（如果有）
                        if 'data' in result and result['data']:
                            data = result['data']
                            if isinstance(data, dict):
                                for key in ['name', 'userName', 'realName']:
                                    if key in data:
                                        self.logger.info(f"用户: {data[key]}")
                                        break

                        # 验证token有效性
                        return self.verify_token_with_order_request()
                    else:
                        error_msg = result.get('msg') or result.get('message') or '未知错误'
                        self.logger.error(f"登录失败: {error_msg}")
                        return False

                except json.JSONDecodeError as e:
                    self.logger.error(f"JSON解析错误: {e}")
                    self.logger.debug(f"响应文本: {response.text[:500]}")
                    return False
            else:
                self.logger.error(f"登录失败，状态码: {response.status_code}")
                self.logger.debug(f"响应文本: {response.text[:500]}")
                return False

        except Exception as e:
            self.logger.error(f"登录请求异常: {e}")
            return False

    def extract_tokens_from_response(self, login_result):
        """尝试从登录响应中提取token - 适配新平台"""
        try:
            # 新平台的token可能在data中
            data = login_result.get('data', {})

            # 尝试多种可能的token字段
            token_fields = ['token', 'accessToken', 'access_token']
            refresh_token_fields = ['refreshToken', 'refresh_token']

            # 查找token
            for field in token_fields:
                if field in data:
                    self.token = data[field]
                    self.headers['token'] = self.token
                    self.logger.info(f"从登录响应中提取到token")
                    break
                elif field in login_result:
                    self.token = login_result[field]
                    self.headers['token'] = self.token
                    self.logger.info(f"从响应中提取到token")
                    break

            # 查找refresh token
            for field in refresh_token_fields:
                if field in data:
                    self.refresh_token = data[field]
                    self.headers['refreshtoken'] = self.refresh_token
                    self.logger.info(f"从登录响应中提取到refresh token")
                    break
                elif field in login_result:
                    self.refresh_token = login_result[field]
                    self.headers['refreshtoken'] = self.refresh_token
                    self.logger.info(f"从响应中提取到refresh token")
                    break

        except Exception as e:
            self.logger.warning(f"从响应提取token失败: {e}")

    def verify_token_with_order_request(self):
        """通过尝试获取订单来验证token有效性 - 适配新平台"""
        self.logger.info("通过订单请求验证token有效性...")

        # 获取当前日期的时间戳
        today_str = self.get_today_date()
        today_timestamp = 配置.日期转时间戳(today_str)

        if not today_timestamp:
            self.logger.warning("无法转换日期时间戳，跳过token验证")
            return True  # 暂时返回True

        # 尝试获取少量订单数据来验证token - 使用新平台参数格式
        test_order_data = {
            "pageIndex": 1,
            "pageSize": 1,  # 只请求1条记录来测试
            "shopId": 配置.门店ID,  # 注意：新平台是shopId，不是shopIds
            "status": 20,  # 待发货状态
            "startCustomDeliveryDate": today_timestamp,  # 使用时间戳
            "endCustomDeliveryDate": today_timestamp,  # 使用时间戳
            "deliveryTime": [today_timestamp, today_timestamp],  # 新平台参数
            "pickupTime": None  # 新平台参数
        }

        try:
            order_url = f"{self.base_url}{配置.ORDER_API}"

            response = self.session.post(
                order_url,
                json=test_order_data,
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 200 or result.get('success'):
                    self.logger.info("Token验证成功（通过订单API）")
                    return True
                else:
                    error_msg = result.get('msg') or result.get('message') or '未知错误'
                    self.logger.warning(f"Token验证失败: {error_msg}")
                    return False
            elif response.status_code == 401 or response.status_code == 403:
                self.logger.warning("Token验证失败：认证错误")
                return False
            else:
                self.logger.warning(f"Token验证请求失败，状态码: {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"Token验证异常: {e}")
            return True  # 发生异常时，假设token有效

    def check_token_valid(self):
        """检查token是否有效 - 简化版本"""
        # 直接检查是否有token，不进行API调用验证
        if self.token:
            self.logger.info("Token存在，假设有效")
            return True
        return False

    def ensure_valid_token(self):
        """确保有有效的token，必要时重新登录"""
        if not self.check_token_valid():
            self.logger.info("Token无效，尝试重新登录...")
            if self.username and self.password:
                return self.login(self.username, self.password)
            else:
                self.logger.error("无法重新登录：缺少用户名或密码")
                return False
        return True

    def get_today_date(self):
        """获取今天的日期"""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d')

    def get_tomorrow_date(self):
        """获取明天的日期"""
        from datetime import datetime, timedelta
        return (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')