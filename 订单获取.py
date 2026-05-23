import time
import logging
from datetime import datetime, timedelta
from 配置 import 配置

class OrderFetcher:
    def __init__(self, session, base_url, headers, auth_manager, logger=None):
        self.session = session
        self.base_url = base_url
        self.headers = headers
        self.auth_manager = auth_manager
        if logger:
            self.logger = logger
        else:
            self.setup_logging()

    def setup_logging(self):
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
        dt = datetime.strptime(日期字符串, '%Y-%m-%d')
        return int(dt.timestamp() * 1000)

    # ✅ 拉取全量订单，无额外筛选，仅做支付时间匹配
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

    def _fetch_orders(self, order_url, order_data, max_retries, order_type):
        for attempt in range(max_retries):
            try:
                resp = self.session.post(order_url, json=order_data, headers=self.headers, timeout=20)
                if resp.status_code == 200:
                    res = resp.json()
                    if res.get("success") or res.get("code") == 200:
                        data = res.get("data", {})
                        return data.get("list", []) if isinstance(data, dict) else data
                self.logger.warning(f"⚠️ {order_type}请求失败，状态码{resp.status_code}，重试{attempt+1}/{max_retries}")
                time.sleep(2)
            except Exception as e:
                self.logger.error(f"❌ {order_type}请求异常: {e}，重试{attempt+1}/{max_retries}")
                time.sleep(2)
        self.logger.error(f"❌ {order_type}请求最终失败")
        return []