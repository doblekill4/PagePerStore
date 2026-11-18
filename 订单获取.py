# 订单获取.py - 适配新平台API + 剪贴板数据处理
import time
from datetime import datetime, timedelta
from 配置 import 配置
import json
import os


class OrderFetcher:
    def __init__(self, session, base_url, headers, auth_manager, logger=None):
        """初始化订单获取模块"""
        self.session = session
        self.base_url = base_url
        self.headers = headers
        self.auth_manager = auth_manager
        # 最近一次 _fetch_orders 是否通信成功（含成功返回 0 条）；
        # 用于区分「正常无订单」与「通信失败」，避免无单被误报为错误
        self.最后查询通信正常 = True

        if logger:
            self.logger = logger
        else:
            self.setup_logging()

    def setup_logging(self):
        """设置日志记录（统一到 日志管理：同目录、按天分文件、保留近 N 天）"""
        from 日志管理 import 获取日志器
        self.logger = 获取日志器("订单获取")

    def 日期转时间戳(self, 日期字符串):
        """将日期字符串转换为时间戳（毫秒）"""
        try:
            dt = datetime.strptime(日期字符串, '%Y-%m-%d')
            # 转换为时间戳（毫秒）
            时间戳 = int(dt.timestamp() * 1000)
            return 时间戳
        except Exception as e:
            self.logger.error(f"日期转换失败: {日期字符串}, 错误: {e}")
            return None

    def 获取时间戳范围(self, 日期字符串):
        """获取日期的时间戳范围（从00:00到23:59:59.999）"""
        try:
            dt = datetime.strptime(日期字符串, '%Y-%m-%d')
            # 开始时间：当天00:00
            start_dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            # 结束时间：当天23:59:59.999
            end_dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)

            start_ts = int(start_dt.timestamp() * 1000)
            end_ts = int(end_dt.timestamp() * 1000)

            return start_ts, end_ts
        except Exception as e:
            self.logger.error(f"获取时间戳范围失败: {日期字符串}, 错误: {e}")
            return None, None

    # ✅ 拉取全量订单，无额外筛选，仅做支付时间匹配（微信月度导出用，复刻 2.5 逻辑）
    def get_orders_by_pay_time_range(self, start_pay_date, end_pay_date, status_list=None, page_size=1000):
        if not self.auth_manager.ensure_valid_token():
            self.logger.error("token无效")
            return []

        # ✅ 拉取所有有效订单状态，无过滤
        if status_list is None:
            status_list = [10, 20, 50, 80, 90]

        start_ts = self.日期转时间戳(start_pay_date)
        end_ts = self.日期转时间戳(end_pay_date) + 86400 * 1000 - 1

        self.logger.info(f"✅ 接口查询创建时间: {start_pay_date} ~ {end_pay_date}")
        self.logger.info(f"✅ 拉取订单状态: {status_list}")
        self.logger.info(f"✅ pageSize设置为{page_size}，单页拉取全量订单，无分页漏单")

        all_orders = []
        for status in status_list:
            url = f"{self.base_url}{配置.ORDER_API}"
            data = {
                "pageIndex": 1,
                "pageSize": page_size,
                "shopId": 配置.门店ID,
                "status": status,
                "startTime": start_ts,
                "endTime": end_ts,
                "startAndEnd": [start_ts, end_ts]
            }
            orders = self._fetch_orders(url, data, 3, f"状态{status}")
            if orders:
                all_orders.extend(orders)
                self.logger.info(f"✅ 状态{status}拉取到 {len(orders)} 条订单")

        # ✅ 仅做支付时间范围匹配，无其他任何筛选
        filtered = []
        for o in all_orders:
            pay_time_str = o.get("payTime", "")
            if not pay_time_str:
                pay_time_str = o.get("createTime", "")
            try:
                if " " in pay_time_str:
                    pay_time = datetime.strptime(pay_time_str, "%Y-%m-%d %H:%M:%S")
                else:
                    pay_time = datetime.strptime(pay_time_str, "%Y-%m-%d")
                pay_date = pay_time.strftime("%Y-%m-%d")
                if start_pay_date <= pay_date <= end_pay_date:
                    filtered.append(o)
            except Exception as e:
                self.logger.warning(f"⚠️ 订单{o.get('orderNo')}时间格式异常，跳过: {e}")
                continue

        for o in filtered:
            o["order_type"] = "自提" if o.get("bookPickupDate") else "配送"

        self.logger.info(f"✅ 接口拉取总订单：{len(all_orders)} 条")
        self.logger.info(f"✅ 最终符合支付时间订单：{len(filtered)} 条")
        return filtered

    def get_delivery_orders(self, status=None, delivery_date=None, page_size=100, max_retries=2):
        """获取配送订单数据，支持多个状态 - 适配新平台API"""
        self.最后查询通信正常 = True
        if not self.auth_manager.ensure_valid_token():
            self.logger.error("无法获取有效的token，无法继续获取订单")
            self.最后查询通信正常 = False
            return None

        # 支持状态列表
        if status is None:
            status_list = [20, 50]  # 默认获取待发货和待收货
        elif isinstance(status, int):
            status_list = [status]
        else:
            status_list = status

        # 如果没有指定配送日期，默认使用明天（实际使用）
        if not delivery_date:
            delivery_date = self.auth_manager.get_tomorrow_date()

        self.logger.info(f"\n正在获取配送订单数据...")
        self.logger.info(f"状态: {status_list} (待发货+待收货)")
        self.logger.info(f"配送日期: {delivery_date}")

        # 获取时间戳范围
        start_ts, end_ts = self.获取时间戳范围(delivery_date)
        if not start_ts or not end_ts:
            self.logger.error("日期转换失败，无法获取订单")
            self.最后查询通信正常 = False
            return None

        # 获取所有状态的订单；只要有一个状态通信成功（哪怕 0 条）就算链路正常
        all_orders = []
        任一通信成功 = False
        for status_value in status_list:
            order_url = f"{self.base_url}{配置.ORDER_API}"

            # 构造请求参数 - 配送订单（新平台格式）
            order_data = {
                "pageIndex": 1,
                "pageSize": page_size,
                "shopId": 配置.门店ID,  # 注意：新平台是shopId，不是shopIds
                "status": status_value,
                "pickupTime": None,
                "deliveryTime": [start_ts, end_ts],
                "startCustomDeliveryDate": start_ts,
                "endCustomDeliveryDate": end_ts
            }

            orders = self._fetch_orders(order_url, order_data, max_retries, f"配送-状态{status_value}")
            if orders is not None:
                任一通信成功 = True
                if orders:
                    all_orders.extend(orders)
        self.最后查询通信正常 = 任一通信成功

        # Debug: dump delivery raw orders
        try:
            dbg_path = os.path.join(os.getcwd(), 'orders_delivery_raw_debug.json')
            with open(dbg_path, 'w', encoding='utf-8') as f:
                json.dump(all_orders, f, ensure_ascii=False, indent=2)
            self.logger.info(f"已将配送订单原始数据写入调试文件: {dbg_path}")
        except Exception as e:
            self.logger.warning(f"写入配送订单调试文件失败: {e}")

        # 为配送订单添加配送时间信息和订单类型标记
        for order in all_orders:
            # 从订单数据中提取配送时间
            delivery_time = order.get('customDeliveryTime')
            if delivery_time:
                # 格式化配送时间
                order['delivery_or_pickup_time'] = self._format_delivery_time(delivery_time)
            else:
                order['delivery_or_pickup_time'] = '未知时间'

            # 确保订单类型标记正确
            order['order_type'] = '配送'

        self.logger.info(f"总共获取到 {len(all_orders)} 条配送订单")
        return all_orders

    def get_pickup_orders(self, status=None, pickup_date=None, page_size=100, max_retries=2):
        """获取自提订单数据，支持自动重试 - 适配新平台API"""
        self.最后查询通信正常 = True
        if not self.auth_manager.ensure_valid_token():
            self.logger.error("无法获取有效的token，无法继续获取订单")
            self.最后查询通信正常 = False
            return None

        # 支持状态列表
        if status is None:
            status_list = [20, 50]  # 同时查询待发货和待收货
        elif isinstance(status, int):
            status_list = [status]
        else:
            status_list = status

        # 如果没有指定自提日期，默认使用明天（实际使用）
        if not pickup_date:
            pickup_date = self.auth_manager.get_tomorrow_date()

        self.logger.info(f"\n正在获取自提订单数据...")
        self.logger.info(f"状态: {status_list} (待发货+待收货)")
        self.logger.info(f"自提日期: {pickup_date}")

        # 获取时间戳范围
        start_ts, end_ts = self.获取时间戳范围(pickup_date)
        if not start_ts or not end_ts:
            self.logger.error("日期转换失败，无法获取订单")
            self.最后查询通信正常 = False
            return None

        # 获取所有状态的订单；只要有一个状态通信成功（哪怕 0 条）就算链路正常
        all_orders = []
        任一通信成功 = False
        for status_value in status_list:
            order_url = f"{self.base_url}{配置.ORDER_API}"

            # 构造请求参数 - 自提订单（新平台格式）
            order_data = {
                "pageIndex": 1,
                "pageSize": page_size,
                "shopId": 配置.门店ID,
                "status": status_value,
                "pickupTime": [start_ts, end_ts],
                "startBookPickupTime": start_ts,
                "endBookPickupTime": end_ts,
                "deliveryTime": None
            }

            orders = self._fetch_orders(order_url, order_data, max_retries, f"自提-状态{status_value}")
            if orders is not None:
                任一通信成功 = True
                if orders:
                    all_orders.extend(orders)
        self.最后查询通信正常 = 任一通信成功

        # Debug: dump pickup raw orders
        try:
            dbg_path = os.path.join(os.getcwd(), 'orders_pickup_raw_debug.json')
            with open(dbg_path, 'w', encoding='utf-8') as f:
                json.dump(all_orders, f, ensure_ascii=False, indent=2)
            self.logger.info(f"已将自提订单原始数据写入调试文件: {dbg_path}")
        except Exception as e:
            self.logger.warning(f"写入自提订单调试文件失败: {e}")

        # 为自提订单添加自提时间信息和订单类型标记
        for order in all_orders:
            # 从订单数据中提取自提时间
            pickup_time = order.get('bookPickupTime')
            if pickup_time:
                # 格式化自提时间
                order['delivery_or_pickup_time'] = self._format_pickup_time(pickup_time)
            else:
                # 如果没有自提时间，检查是否有其他时间字段
                delivery_time = order.get('customDeliveryTime')
                if delivery_time:
                    order['delivery_or_pickup_time'] = self._format_delivery_time(delivery_time)
                else:
                    order['delivery_or_pickup_time'] = '未知时间'

            # 确保订单类型标记正确
            order['order_type'] = '自提'

        self.logger.info(f"总共获取到 {len(all_orders)} 条自提订单")
        return all_orders

    def _format_delivery_time(self, delivery_time_value):
        """格式化配送时间 - 适配新平台"""
        try:
            # 新平台可能使用时间戳或字符串
            if isinstance(delivery_time_value, (int, float)):
                # 如果是时间戳，转换为时间格式
                dt = datetime.fromtimestamp(delivery_time_value / 1000)
                return dt.strftime("%H:%M")
            elif isinstance(delivery_time_value, str):
                # 如果是字符串，尝试解析
                if '-' in delivery_time_value:
                    return delivery_time_value  # 可能是 "HH:MM-HH:MM" 格式
                elif ':' in delivery_time_value:
                    return delivery_time_value  # 可能是 "HH:MM" 格式
                else:
                    # 尝试转换为数字
                    try:
                        timestamp = int(delivery_time_value)
                        dt = datetime.fromtimestamp(timestamp / 1000)
                        return dt.strftime("%H:%M")
                    except:
                        return str(delivery_time_value)
            else:
                return str(delivery_time_value)
        except Exception as e:
            self.logger.warning(f"格式化配送时间失败: {delivery_time_value}, 错误: {e}")
            return str(delivery_time_value)

    def _format_pickup_time(self, pickup_time_value):
        """格式化自提时间 - 适配新平台"""
        try:
            # 处理方式同配送时间
            return self._format_delivery_time(pickup_time_value)
        except Exception as e:
            self.logger.warning(f"格式化自提时间失败: {pickup_time_value}, 错误: {e}")
            return str(pickup_time_value)

    def _fetch_orders(self, order_url, order_data, max_retries, order_type):
        """通用的订单获取方法 - 适配新平台"""
        for attempt in range(max_retries):
            try:
                self.logger.info(f"尝试获取{order_type}订单 (第{attempt + 1}次)...")

                response = self.session.post(
                    order_url,
                    json=order_data,
                    headers=self.headers,
                    timeout=15
                )

                self.logger.info(f"{order_type}订单查询状态码: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()

                    # 新平台可能使用code或success字段
                    success = result.get('success', False) or result.get('code', 0) == 200

                    if success:
                        if 'data' in result:
                            data = result['data']
                            if isinstance(data, dict) and 'list' in data:
                                orders = data['list']
                                total_orders = data.get('total', len(orders))
                                self.logger.info(f"成功获取{order_type}订单数据！")
                                self.logger.info(f"找到 {len(orders)} 条{order_type}订单 (总共 {total_orders} 条)")
                                self.最后查询通信正常 = True
                                return orders
                            elif isinstance(data, list):
                                # data直接是列表的情况
                                orders = data
                                self.logger.info(f"成功获取{order_type}订单数据！")
                                self.logger.info(f"找到 {len(orders)} 条{order_type}订单")
                                self.最后查询通信正常 = True
                                return orders
                            else:
                                self.logger.warning(f"data字段格式异常: {type(data)}")
                                self.logger.debug(f"data内容: {data}")
                        else:
                            self.logger.warning(f"响应中没有data字段")
                            self.logger.debug(f"响应: {result}")
                    else:
                        error_msg = result.get('message') or result.get('msg') or '未知错误'
                        self.logger.warning(f"获取{order_type}订单数据失败: {error_msg}")

                        # 如果是认证错误，尝试重新登录
                        if "token" in error_msg.lower() or "认证" in error_msg or "登录" in error_msg or "forbidden" in error_msg.lower():
                            self.logger.info("检测到认证错误，尝试重新登录...")
                            if self.auth_manager.login(self.auth_manager.username, self.auth_manager.password):
                                continue
                elif response.status_code == 401 or response.status_code == 403:
                    self.logger.warning("访问被拒绝，尝试重新登录...")
                    if self.auth_manager.login(self.auth_manager.username, self.auth_manager.password):
                        continue
                else:
                    self.logger.error(f"获取{order_type}订单数据失败，状态码: {response.status_code}")
                    self.logger.debug(f"响应内容: {response.text[:200]}")

                # 如果不是最后一次尝试，等待一会儿再重试
                if attempt < max_retries - 1:
                    time.sleep(2)

            except Exception as e:
                self.logger.error(f"获取{order_type}订单数据异常: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)

        self.logger.error(f"经过{max_retries}次尝试后，仍然无法获取{order_type}订单数据")
        self.最后查询通信正常 = False
        return None

# 使用示例
if __name__ == "__main__":

    pass