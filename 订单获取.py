# 订单获取.py - 适配新平台API + 剪贴板数据处理
import time
import logging
import pyperclip
from datetime import datetime, timedelta
from 配置 import 配置
import pandas as pd
from io import StringIO
import csv
import io
import json
import os


class OrderFetcher:
    def __init__(self, session, base_url, headers, auth_manager, logger=None):
        """初始化订单获取模块"""
        self.session = session
        self.base_url = base_url
        self.headers = headers
        self.auth_manager = auth_manager

        if logger:
            self.logger = logger
        else:
            self.setup_logging()

    def setup_logging(self):
        """设置日志记录"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("order_fetcher.log", encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

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

    def get_delivery_orders(self, status=None, delivery_date=None, page_size=100, max_retries=2):
        """获取配送订单数据，支持多个状态 - 适配新平台API"""
        if not self.auth_manager.ensure_valid_token():
            self.logger.error("无法获取有效的token，无法继续获取订单")
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
            return None

        # 获取所有状态的订单
        all_orders = []
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
            if orders:
                all_orders.extend(orders)

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
        if not self.auth_manager.ensure_valid_token():
            self.logger.error("无法获取有效的token，无法继续获取订单")
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
            return None

        # 获取所有状态的订单
        all_orders = []
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
            if orders:
                all_orders.extend(orders)

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
                                return orders
                            elif isinstance(data, list):
                                # data直接是列表的情况
                                orders = data
                                self.logger.info(f"成功获取{order_type}订单数据！")
                                self.logger.info(f"找到 {len(orders)} 条{order_type}订单")
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
        return None

    def get_all_orders(self, delivery_date=None, pickup_date=None, status=None):
        """获取所有订单（配送+自提）- 适配新平台"""
        # 如果没有指定日期，默认使用明天（次日）
        if not delivery_date:
            delivery_date = self.auth_manager.get_tomorrow_date()
        if not pickup_date:
            pickup_date = self.auth_manager.get_tomorrow_date()

        self.logger.info(f"获取有效订单数据 - 配送日期: {delivery_date}, 自提日期: {pickup_date}")

        # 配送订单使用待发货状态
        delivery_orders = self.get_delivery_orders(status=20, delivery_date=delivery_date)

        # 自提订单使用待发货和待收货状态
        pickup_orders = self.get_pickup_orders(status=[20, 50], pickup_date=pickup_date)

        all_orders = []
        if delivery_orders:
            for order in delivery_orders:
                order['order_type'] = '配送'
            all_orders.extend(delivery_orders)

        if pickup_orders:
            for order in pickup_orders:
                order['order_type'] = '自提'
            all_orders.extend(pickup_orders)

        # 过滤掉取消状态的订单（额外保护）
        valid_orders = [order for order in all_orders if order.get('status') not in [90]]

        if len(valid_orders) < len(all_orders):
            self.logger.warning(f"过滤掉 {len(all_orders) - len(valid_orders)} 条取消状态订单")

        # Debug: dump raw fetched orders to a file for inspection
        try:
            debug_path = os.path.join(os.getcwd(), 'orders_raw_debug.json')
            # Write the original all_orders (not filtered) so we can inspect API response
            with open(debug_path, 'w', encoding='utf-8') as f:
                json.dump(all_orders, f, ensure_ascii=False, indent=2)
            self.logger.info(f"已将原始订单数据写入调试文件: {debug_path}")
        except Exception as e:
            self.logger.warning(f"写入原始订单调试文件失败: {e}")

        return valid_orders

    def check_different_dates(self):
        """检查不同日期的订单数据"""
        # 获取今天和明天的日期字符串
        today_str = self.auth_manager.get_today_date()
        tomorrow_str = self.auth_manager.get_tomorrow_date()

        # 计算昨天的日期
        today_dt = datetime.strptime(today_str, '%Y-%m-%d')
        yesterday_dt = today_dt - timedelta(days=1)
        yesterday_str = yesterday_dt.strftime('%Y-%m-%d')

        dates_to_check = [
            today_str,  # 今天
            tomorrow_str,  # 明天
            yesterday_str  # 昨天
        ]

        print(f"\n{'=' * 60}")
        print("开始多日期检查任务")
        print(f"{'=' * 60}")

        all_results = []

        for check_date in dates_to_check:
            print(f"\n检查日期: {check_date}")

            # 检查配送订单
            print(f"\n1. 检查配送订单:")
            delivery_results = self._check_orders_with_filters(check_date, "delivery")
            all_results.extend(delivery_results)

            # 检查自提订单
            print(f"\n2. 检查自提订单:")
            pickup_results = self._check_orders_with_filters(check_date, "pickup")
            all_results.extend(pickup_results)

        return all_results

    def _check_orders_with_filters(self, check_date, order_type):
        """检查特定类型订单的不同筛选条件"""
        results = []

        # 获取时间戳范围
        start_ts, end_ts = self.获取时间戳范围(check_date)
        if not start_ts or not end_ts:
            print(f"  日期转换失败: {check_date}")
            return results

        # 定义不同的状态筛选条件
        status_filters = [
            {"name": "待发货", "status": 20},
            {"name": "待收货", "status": 50},
            {"name": "取消订单", "status": 90},
            {"name": "全部状态", "status": None}
        ]

        for filter_info in status_filters:
            status_name = f"{order_type}-{filter_info['name']}"
            status_value = filter_info["status"]

            print(f"  正在检查 [{status_name}]...")

            # 构造请求参数
            order_data = {
                "pageIndex": 1,
                "pageSize": 10,  # 只获取前10条用于检查
                "shopId": 配置.门店ID,
            }

            # 根据订单类型添加时间参数
            if order_type == "delivery":
                order_data.update({
                    "pickupTime": None,
                    "deliveryTime": [start_ts, end_ts],
                    "startCustomDeliveryDate": start_ts,
                    "endCustomDeliveryDate": end_ts
                })
            else:  # pickup
                order_data.update({
                    "pickupTime": [start_ts, end_ts],
                    "startBookPickupTime": start_ts,
                    "endBookPickupTime": end_ts,
                    "deliveryTime": None
                })

            # 添加状态筛选（如果不是全部状态）
            if status_value is not None:
                order_data["status"] = status_value

            try:
                response = self.session.post(
                    f"{self.base_url}{配置.ORDER_API}",
                    json=order_data,
                    headers=self.headers,
                    timeout=10
                )

                if response.status_code == 200:
                    result = response.json()
                    success = result.get('success', False) or result.get('code', 0) == 200

                    if success and 'data' in result:
                        data = result['data']
                        orders = data.get('list', [])
                        total_orders = data.get('total', 0)

                        result_info = {
                            "order_type": order_type,
                            "status_name": status_name,
                            "status_value": status_value,
                            "total_orders": total_orders,
                            "sample_orders": orders[:3] if orders else [],
                            "success": True
                        }
                        results.append(result_info)

                        print(f"    ✓ 找到 {total_orders} 条订单")

                        # 显示样本订单信息
                        if orders:
                            for i, order in enumerate(orders[:2], 1):
                                receiver = order.get('receiverName', '未知')
                                items_count = len(order.get('orderItemList', []))
                                amount = order.get('paymentAmount', 0)
                                print(f"      样本{i}: {receiver} - {items_count}件商品 - ¥{amount}")
                    else:
                        error_msg = result.get('message') or result.get('msg') or '未知错误'
                        print(f"    ✗ 查询失败: {error_msg}")
                        results.append({
                            "order_type": order_type,
                            "status_name": status_name,
                            "status_value": status_value,
                            "error": error_msg,
                            "success": False
                        })
                else:
                    print(f"    ✗ 请求失败，状态码: {response.status_code}")
                    results.append({
                        "order_type": order_type,
                        "status_name": status_name,
                        "status_value": status_value,
                        "error": f"HTTP {response.status_code}",
                        "success": False
                    })

            except Exception as e:
                print(f"    ✗ 查询异常: {e}")
                results.append({
                    "order_type": order_type,
                    "status_name": status_name,
                    "status_value": status_value,
                    "error": str(e),
                    "success": False
                })

            # 稍微延迟一下，避免请求过于频繁
            time.sleep(1)

        return results

    def process_orders_to_clipboard(self, orders, required_fields=None):
        """
        处理订单数据，按要求字段整理并写入剪贴板
        在J列填写"烘焙"，L列填写"13552025004"
        """
        if not orders:
            self.logger.warning("没有订单数据可处理")
            return False

        # 默认需要的字段（可根据实际需求调整）
        if required_fields is None:
            required_fields = [
                'orderNo', 'receiverName', 'receiverPhone', 'receiverAddress',
                'paymentAmount', 'order_type', 'delivery_or_pickup_time',
                'createTime', 'status'
            ]

        # 使用 DataProcessor 的逻辑来生成最终导出 DataFrame，保持与主程序一致
        try:
            from 数据处理 import DataProcessor

            dp = DataProcessor(self.logger)
            processed_data = dp.process_orders_for_export(orders)
            df = dp.create_dataframe(processed_data)

            # 导出为 TSV 文本，保留引号以包裹包含换行的字段
            output = io.StringIO()
            df.to_csv(output, index=False, sep='\t', header=False, quoting=csv.QUOTE_MINIMAL)
            tsv_text = output.getvalue()

            # 使用 win32clipboard 写入（优先），回退到 pyperclip
            try:
                import win32clipboard
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(tsv_text, win32clipboard.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
            except Exception:
                pyperclip.copy(tsv_text)

            self.logger.info(f"成功处理 {len(orders)} 条订单数据并写入剪贴板 (使用 DataProcessor 生成)")
            return True

        except Exception as e:
            self.logger.error(f"处理订单数据并写入剪贴板失败: {e}")
            return False

    def get_orders_and_copy_to_clipboard(self, delivery_date=None, pickup_date=None, status=None):
        """
        获取所有订单并直接复制到剪贴板（完整流程）
        """
        # 获取所有订单
        all_orders = self.get_all_orders(delivery_date, pickup_date, status)

        if not all_orders:
            self.logger.error("未获取到任何订单数据")
            return False

        # 处理并复制到剪贴板
        return self.process_orders_to_clipboard(all_orders)


# 使用示例
if __name__ == "__main__":

    pass