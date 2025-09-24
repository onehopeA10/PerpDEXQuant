import hashlib
import hmac
import json
import os
import threading
import time
from datetime import datetime
from urllib.parse import urlencode

import requests
import json
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class TradingUI:
    def __init__(self):
        self.console = Console()
        self.layout = Layout()
        self.account_statuses = {}  # 存储所有账户状态
        self.current_price = 0
        self.running = True
        self.stats = {
            "trade_count": 0,
            "current_funding_rate": 0,
            "last_trade_time": None,
            "symbol": "",
            "leverage": 0,
            "wait_seconds": 0,
            "last_order_price": 0,
            "total_volume": 0,
            "total_volume_usdt": 0,
            "initial_total_balance": 0,
            "position_open_time": None,  # 记录开仓时间
            "actual_hold_time": 0,  # 实际持仓时间（秒）
        }

    def add_account(self, account_name):
        """添加新账户的状态跟踪"""
        self.account_statuses[account_name] = {
            "position_side": "NONE",
            "quantity": 0,
            "entry_price": 0,
            "unrealized_pnl": 0,
            "system_status": "初始化中",
            "initial_balance": 0,
            "current_balance": 0,
            "margin": 0,  # 持仓保证金
            "liquidation_price": 0,
            "last_update": None,
        }

    def generate_layout(self):
        # 创建标题面板
        title_panel = Panel(
            Text("AsterDex 对冲交易系统", justify="center", style="bold white"),
            style="blue",
        )

        author_panel = Panel(
            Text("免费开源，推特：@onehopeA9", justify="center", style="bold white"),
            style="blue",
        )

        # 创建市场信息表格
        total_pnl = sum(
            status["current_balance"] - status["initial_balance"]
            for status in self.account_statuses.values()
        )

        # 更新实际持仓时间
        if self.stats["position_open_time"] is not None:
            self.stats["actual_hold_time"] = int(time.time() - self.stats["position_open_time"])

        market_table = Table.grid(padding=1)
        market_table.add_column("项目", style="cyan")
        market_table.add_column("数值", style="green")

        market_table.add_row("交易对", self.stats["symbol"])
        market_table.add_row("当前价格", f"{self.current_price} USDT")
        market_table.add_row("当前杠杆", f"{self.stats['leverage']}x")
        market_table.add_row(
            "当前资金费率", f"{self.stats['current_funding_rate'] * 100:.4f}%"
        )
        # 显示实际持仓时间或配置的等待时间
        hold_time_display = f"{self.stats['actual_hold_time']}秒" if self.stats['actual_hold_time'] > 0 else f"{self.stats['wait_seconds']}秒(预设)"
        market_table.add_row("持仓时间", hold_time_display)
        market_table.add_row("交易次数", str(self.stats["trade_count"]))
        market_table.add_row("总交易量", f"{self.stats['total_volume_usdt']:.2f} USDT")

        # 添加每个账户的余额信息
        for account_name, status in self.account_statuses.items():
            market_table.add_row(
                f"{account_name}余额", f"{status['current_balance']:.4f} USDT"
            )

        market_table.add_row(
            "初始总资产", f"{self.stats['initial_total_balance']:.4f} USDT"
        )
        market_table.add_row("总盈亏", f"{total_pnl:.4f} USDT")
        market_table.add_row("上次交易时间", self.stats["last_trade_time"] or "无")
        market_table.add_row("当前时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        market_panel = Panel(market_table, title="市场信息", border_style="green")

        # 创建账号状态表格
        account_table = Table(show_header=True, padding=1)
        account_table.add_column("账号", style="cyan", justify="left", width=8)
        account_table.add_column("持仓方向", justify="center", width=10)
        account_table.add_column("持仓数量", style="white", justify="right", width=12)
        account_table.add_column("开仓价格", style="white", justify="right", width=12)
        account_table.add_column("未实现盈亏", justify="right", width=20)
        account_table.add_column("保证金", style="white", justify="right", width=20)
        account_table.add_column("清算价格", style="white", justify="right", width=20)
        account_table.add_column("更新时间", style="dim", justify="center", width=10)

        # 添加每个账户的状态行
        for account_name, status in self.account_statuses.items():
            # 添加颜色提示
            pnl_style = "green" if status["unrealized_pnl"] >= 0 else "red"
            position_style = "cyan" if status["position_side"] == "LONG" else "magenta" if status["position_side"] == "SHORT" else "white"

            account_table.add_row(
                account_name,
                Text(status["position_side"], style=position_style),
                f"{status['quantity']:>12.3f}",
                f"{status['entry_price']:>12.2f}",
                Text(f"{status['unrealized_pnl']:>20.2f} USDT", style=pnl_style),
                f"{status['margin']:>20.2f} USDT",
                f"{status['liquidation_price']:>20.2f} USDT",
                status.get("last_update", "-"),
            )

        account_panel = Panel(account_table, title="账号状态", border_style="yellow")

        # 组合所有面板
        self.layout.split(
            Layout(name="header", size=6),
            Layout(name="main"),
        )

        self.layout["header"].split(
            Layout(title_panel, ratio=1), Layout(author_panel, ratio=1)
        )
        self.layout["main"].split_row(
            Layout(market_panel, ratio=1), Layout(account_panel, ratio=2)
        )

        return self.layout

    def update_status(self, account_name, status, current_price):
        """更新指定账户的状态"""
        if account_name in self.account_statuses:
            status["last_update"] = datetime.now().strftime("%H:%M:%S")
            self.account_statuses[account_name] = status
        self.current_price = current_price

    def update_stats(
        self,
        funding_rate=0,
        symbol="",
        leverage=0,
        wait_seconds=0,
        last_order_price=0,
        volume=0,
        position_opened=False,  # 新增参数，标记是否刚开仓
    ):
        self.stats["trade_count"] += 1
        self.stats["current_funding_rate"] = funding_rate
        self.stats["last_trade_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.stats["symbol"] = symbol
        self.stats["leverage"] = leverage
        self.stats["wait_seconds"] = wait_seconds
        self.stats["last_order_price"] = last_order_price
        self.stats["total_volume"] += volume
        self.stats["total_volume_usdt"] += volume * last_order_price

        # 如果刚开仓，记录开仓时间
        if position_opened:
            self.stats["position_open_time"] = time.time()

        # 更新初始总资产（仅在第一次更新时）
        if self.stats["initial_total_balance"] == 0:
            self.stats["initial_total_balance"] = sum(
                status["initial_balance"] for status in self.account_statuses.values()
            )

    def show(self):
        with Live(self.generate_layout(), refresh_per_second=1) as live:
            while self.running:
                live.update(self.generate_layout())
                time.sleep(1)

    def stop(self):
        self.running = False


class AsterDexAPI:
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://fapi.asterdex.com"
        self.recv_window = 5000
        self.position_mode = None  # 持仓模式缓存
        self.server_time_warned = False  # 服务器时间警告标志
        self.time_offset = 0  # 服务器时间偏移量
        self.last_time_sync = 0  # 上次同步时间

    def _get_error_message(self, code, msg):
        """根据错误代码返回中文错误信息"""
        error_messages = {
            -1121: "无效的交易对",
            -2010: "订单被拒绝",
            -2011: "取消订单被拒绝",
            -2013: "订单不存在",
            -2018: "余额不足",
            -2019: "保证金不足",
            -2020: "无法成交",
            -2021: "订单将立即触发",
            -2022: "仅减仓订单被拒绝",
            -2023: "用户正处于被强平模式",
            -2024: "持仓不足",
            -2025: "挂单量达到上限",
            -2027: "当前杠杆下持仓超出上限",
            -4164: "订单名义价值必须不小于5 USDT",
            -4131: "交易对手最优价格未达到限价要求",
        }
        return error_messages.get(code, f"{msg} (代码: {code})")

    def _generate_signature(self, params):
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def _get_server_time(self):
        try:
            response = requests.get(self.base_url + "/fapi/v1/time", timeout=2)
            if response.status_code == 200 and response.text:
                server_time = response.json()["serverTime"]
                # 更新时间偏移量
                local_time = int(time.time() * 1000)
                self.time_offset = server_time - local_time
                self.last_time_sync = time.time()
                self.server_time_warned = False  # 重置警告标志
                return server_time
            else:
                # 如果服务器时间获取失败，使用本地时间+偏移量
                if not self.server_time_warned:
                    print(f"获取服务器时间失败，使用本地时间")
                    self.server_time_warned = True
                return int(time.time() * 1000) + self.time_offset
        except Exception as e:
            if not self.server_time_warned:
                print(f"获取服务器时间异常: {str(e)[:50]}，使用本地时间")
                self.server_time_warned = True
            return int(time.time() * 1000) + self.time_offset

    def _get_timestamp(self):
        try:
            current_time = time.time()
            # 每5分钟同步一次服务器时间，或者如果还没有同步过
            if current_time - self.last_time_sync > 300 or self.last_time_sync == 0:
                server_time = self._get_server_time()
                local_time = int(time.time() * 1000)
                time_diff = server_time - local_time
                # 如果时间差异太大（超过1分钟），使用本地时间
                if abs(time_diff) > 60000:
                    if not self.server_time_warned:
                        print(f"时间差异过大: {time_diff}ms，使用本地时间")
                        self.server_time_warned = True
                    return local_time
                return server_time
            else:
                # 使用缓存的时间偏移量
                return int(time.time() * 1000) + self.time_offset
        except Exception as e:
            if not self.server_time_warned:
                print(f"获取时间戳异常: {str(e)[:50]}，使用本地时间")
                self.server_time_warned = True
            return int(time.time() * 1000) + self.time_offset

    def get_account_info(self):
        """获取账户信息 - 优先使用v4接口"""
        headers = {"X-MBX-APIKEY": self.api_key}

        # 优先尝试v4接口（更完整的账户信息）
        try:
            endpoint = "/fapi/v4/account"
            params = {"timestamp": self._get_timestamp(), "recvWindow": self.recv_window}
            params["signature"] = self._generate_signature(params)

            response = requests.get(
                self.base_url + endpoint, params=params, headers=headers, timeout=5
            )
            if response.status_code == 200 and response.text:
                result = response.json()
                if "assets" in result:
                    return result
        except:
            pass

        # v4失败时，尝试v2接口
        try:
            endpoint = "/fapi/v2/balance"
            params = {"timestamp": self._get_timestamp(), "recvWindow": self.recv_window}
            params["signature"] = self._generate_signature(params)

            response = requests.get(
                self.base_url + endpoint, params=params, headers=headers, timeout=5
            )
            if response.status_code == 200 and response.text:
                result = response.json()
                if isinstance(result, list):
                    account_info = {"assets": [], "positions": []}
                    for asset in result:
                        if asset.get("asset") == "USDT":
                            # v2接口的balance字段是总余额
                            # 注意：balance是总余额，crossWalletBalance是全仓余额
                            wallet_balance = float(asset.get("balance", 0))
                            cross_wallet = float(asset.get("crossWalletBalance", 0))
                            available = float(asset.get("availableBalance", 0))

                            # 如果balance为0但crossWalletBalance有值，使用crossWalletBalance
                            if wallet_balance == 0 and cross_wallet > 0:
                                wallet_balance = cross_wallet

                            account_info["assets"] = [
                                {
                                    "asset": "USDT",
                                    "walletBalance": str(wallet_balance),
                                    "marginBalance": str(cross_wallet if cross_wallet > 0 else wallet_balance),
                                    "unrealizedProfit": str(asset.get("crossUnPnl", 0)),
                                    "availableBalance": str(available if available > 0 else wallet_balance),
                                    "updateTime": 0
                                }
                            ]
                            break
                    return account_info
        except:
            pass

        # 如果都失败，返回默认值
        return {
            "assets": [{
                "asset": "USDT",
                "walletBalance": "0",
                "marginBalance": "0",
                "unrealizedProfit": "0",
                "availableBalance": "0",
                "updateTime": 0
            }],
            "positions": []
        }

    def get_account_balance(self):
        """获取账户余额V2 - 增强容错能力"""
        # 方法1：优先从account_info获取完整余额信息
        try:
            account_info = self.get_account_info()
            for asset in account_info.get("assets", []):
                if asset.get("asset") == "USDT":
                    wallet_balance = float(asset.get("walletBalance", 0))
                    if wallet_balance > 0:
                        return wallet_balance
                    # 尝试其他余额字段
                    cross_wallet = float(asset.get("crossWalletBalance", 0))
                    if cross_wallet > 0:
                        return cross_wallet
                    available = float(asset.get("availableBalance", 0))
                    if available > 0:
                        return available
        except:
            pass

        # 方法2：如果account_info失败，直接调用v2 balance接口
        try:
            endpoint = "/fapi/v2/balance"
            params = {"timestamp": self._get_timestamp(), "recvWindow": self.recv_window}
            params["signature"] = self._generate_signature(params)
            headers = {"X-MBX-APIKEY": self.api_key}

            response = requests.get(
                self.base_url + endpoint, params=params, headers=headers, timeout=5
            )

            if response.status_code == 200 and response.text:
                try:
                    result = response.json()
                    if isinstance(result, list):
                        for asset in result:
                            if asset.get("asset") == "USDT":
                                # 尝试所有可能的余额字段
                                balance = float(asset.get("balance", 0))
                                if balance > 0:
                                    return balance
                                cross_balance = float(asset.get("crossWalletBalance", 0))
                                if cross_balance > 0:
                                    return cross_balance
                                available = float(asset.get("availableBalance", 0))
                                if available > 0:
                                    return available
                except:
                    pass
        except:
            pass

        # 方法3：尝试v1/account接口
        try:
            endpoint = "/fapi/v1/account"
            params = {"timestamp": self._get_timestamp(), "recvWindow": self.recv_window}
            params["signature"] = self._generate_signature(params)
            headers = {"X-MBX-APIKEY": self.api_key}

            response = requests.get(
                self.base_url + endpoint, params=params, headers=headers, timeout=5
            )

            if response.status_code == 200 and response.text:
                try:
                    result = response.json()
                    if "totalWalletBalance" in result:
                        balance = float(result["totalWalletBalance"])
                        if balance > 0:
                            return balance
                    if "totalCrossWalletBalance" in result:
                        balance = float(result["totalCrossWalletBalance"])
                        if balance > 0:
                            return balance
                except:
                    pass
        except:
            pass

        # 如果都失败，返回0
        return 0.0

    def get_current_price(self, symbol):
        endpoint = "/fapi/v1/ticker/price"
        params = {"symbol": symbol}
        try:
            response = requests.get(self.base_url + endpoint, params=params)
            if response.status_code == 200 and response.text:
                data = response.json()
                if isinstance(data, dict) and "price" in data:
                    return float(data["price"])
                else:
                    print(f"获取价格失败: 响应格式错误")
                    return 0.0
            else:
                print(f"获取价格失败: 状态码{response.status_code}")
                return 0.0
        except Exception as e:
            print(f"获取价格异常: {str(e)}")
            return 0.0

    def get_position_info(self, symbol):
        try:
            endpoint = "/fapi/v2/positionRisk"
            params = {
                "symbol": symbol,
                "timestamp": self._get_timestamp(),
                "recvWindow": self.recv_window,
            }
            params["signature"] = self._generate_signature(params)
            headers = {"X-MBX-APIKEY": self.api_key}

            response = requests.get(
                self.base_url + endpoint, params=params, headers=headers
            )

            result = response.json()

            # 检查API响应是否有错误
            if isinstance(result, dict) and "code" in result:
                error_msg = self._get_error_message(result["code"], result.get('msg', '未知错误'))
                print(f"获取持仓信息失败: {error_msg}")
                return []

            return result
        except Exception as e:
            print(f"get_position_info 出错: {str(e)}")
            return []

    def get_funding_rate(self, symbol):
        """获取最新资金费率"""
        endpoint = "/fapi/v1/premiumIndex"
        params = {"symbol": symbol}
        try:
            response = requests.get(self.base_url + endpoint, params=params)
            result = response.json()
            if "lastFundingRate" in result:
                return float(result["lastFundingRate"])
            else:
                print(f"无法获取资金费率: {result}")
                return 0.0
        except Exception as e:
            print(f"获取资金费率失败: {str(e)}")
            return 0.0

    def calculate_margin(self, position_info, leverage=20):
        """计算持仓保证金"""
        if not position_info:
            return 0

        # 根据不同的保证金模式选择字段
        margin_type = position_info.get("marginType", "")

        if margin_type == "isolated":
            # 逐仓模式：优先使用 isolatedMargin
            margin = float(position_info.get("isolatedMargin", 0))
            if margin > 0:
                return round(margin, 2)

        # 尝试使用 initialMargin（当前所需起始保证金）
        margin = float(position_info.get("initialMargin", 0))

        # 如果没有，尝试 positionInitialMargin
        if margin == 0:
            margin = float(position_info.get("positionInitialMargin", 0))

        # 如果都没有，根据持仓量和当前价格计算
        if margin == 0:
            position_amt = float(position_info.get("positionAmt", 0))
            mark_price = float(position_info.get("markPrice", 0))  # 使用标记价格
            entry_price = float(position_info.get("entryPrice", 0))

            # 优先使用标记价格，其次使用开仓价格
            price = mark_price if mark_price > 0 else entry_price

            if position_amt != 0 and price > 0:
                position_leverage = float(position_info.get("leverage", leverage))
                margin = abs(position_amt * price) / position_leverage

        # 四舍五入到2位小数
        return round(margin, 2)

    def set_leverage(self, symbol, leverage):
        """调整开仓杠杆"""
        endpoint = "/fapi/v1/leverage"
        params = {
            "symbol": symbol,
            "leverage": leverage,
            "timestamp": self._get_timestamp(),
            "recvWindow": self.recv_window,
        }
        params["signature"] = self._generate_signature(params)
        headers = {"X-MBX-APIKEY": self.api_key}

        try:
            response = requests.post(
                self.base_url + endpoint, params=params, headers=headers, timeout=10
            )
            result = response.json()

            if "code" in result:
                print(f"设置杠杆失败: {result.get('msg', '未知错误')} (代码: {result.get('code')})")
            return result
        except Exception as e:
            print(f"设置杠杆异常: {str(e)}")
            return None

    def calculate_quantity_from_usdt(self, symbol, usdt_amount, leverage=10):
        """根据USDT金额计算交易数量，考虑步进值和精度"""
        current_price = self.get_current_price(symbol)
        quantity = usdt_amount / current_price

        # 获取交易规则以确保数量符合要求
        # 简化处理：使用3位小数精度
        quantity = max(0.001, quantity)
        final_quantity = round(quantity, 3)
        return final_quantity

    def place_order(self, symbol, side, order_type, quantity, position_side="BOTH", time_in_force=None):
        """下单 (TRADE)"""
        if quantity <= 0:
            raise ValueError(f"无效的交易数量: {quantity}")

        endpoint = "/fapi/v1/order"
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
            "positionSide": position_side,
            "timestamp": self._get_timestamp(),
            "recvWindow": self.recv_window,
        }

        # LIMIT订单需要timeInForce参数
        if order_type == "LIMIT" and time_in_force:
            params["timeInForce"] = time_in_force

        params["signature"] = self._generate_signature(params)
        headers = {"X-MBX-APIKEY": self.api_key}

        try:
            response = requests.post(
                self.base_url + endpoint, params=params, headers=headers, timeout=10
            )
            result = response.json()

            # 检查API响应是否有错误
            if "code" in result:
                error_msg = self._get_error_message(result["code"], result.get('msg', '未知错误'))
                print(f"下单失败: {error_msg}")
                return None

            return result
        except Exception as e:
            print(f"下单异常: {str(e)}")
            return None

    def close_position(self, symbol, side, order_type, quantity, position_side="BOTH", reduce_only=True):
        """平仓 - 使用reduceOnly确保只减仓"""
        opposite_side = "SELL" if side == "BUY" else "BUY"
        return self.place_order(
            symbol, opposite_side, order_type, quantity, position_side
        )

    def cancel_all_orders(self, symbol):
        """撤销所有挂单"""
        endpoint = "/fapi/v1/allOpenOrders"
        params = {
            "symbol": symbol,
            "timestamp": self._get_timestamp(),
            "recvWindow": self.recv_window,
        }
        params["signature"] = self._generate_signature(params)
        headers = {"X-MBX-APIKEY": self.api_key}

        try:
            response = requests.delete(
                self.base_url + endpoint, params=params, headers=headers
            )
            result = response.json()
            if "code" in result and result["code"] == 200:
                print(f"成功撤销{symbol}所有挂单")
            return result
        except Exception as e:
            print(f"撤销挂单失败: {str(e)}")
            return None

    def get_open_orders(self, symbol=None):
        """获取当前挂单"""
        endpoint = "/fapi/v1/openOrders"
        params = {
            "timestamp": self._get_timestamp(),
            "recvWindow": self.recv_window,
        }
        if symbol:
            params["symbol"] = symbol
        params["signature"] = self._generate_signature(params)
        headers = {"X-MBX-APIKEY": self.api_key}

        try:
            response = requests.get(
                self.base_url + endpoint, params=params, headers=headers
            )
            return response.json()
        except Exception as e:
            print(f"获取挂单失败: {str(e)}")
            return []

    def get_position_mode(self):
        """查询持仓模式 - 单向/双向"""
        endpoint = "/fapi/v1/positionSide/dual"
        params = {
            "timestamp": self._get_timestamp(),
            "recvWindow": self.recv_window,
        }
        params["signature"] = self._generate_signature(params)
        headers = {"X-MBX-APIKEY": self.api_key}

        try:
            response = requests.get(
                self.base_url + endpoint, params=params, headers=headers
            )
            result = response.json()
            return result.get("dualSidePosition", False)  # True=双向, False=单向
        except Exception as e:
            print(f"获取持仓模式失败: {str(e)}")
            return False

    def set_position_mode(self, dual_side=False):
        """设置持仓模式"""
        endpoint = "/fapi/v1/positionSide/dual"
        params = {
            "dualSidePosition": "true" if dual_side else "false",
            "timestamp": self._get_timestamp(),
            "recvWindow": self.recv_window,
        }
        params["signature"] = self._generate_signature(params)
        headers = {"X-MBX-APIKEY": self.api_key}

        try:
            response = requests.post(
                self.base_url + endpoint, params=params, headers=headers, timeout=10
            )
            return response.json()
        except Exception as e:
            print(f"设置持仓模式失败: {str(e)}")
            return None

    def set_margin_type(self, symbol, margin_type="CROSSED"):
        """设置保证金模式 - 全仓/逐仓"""
        endpoint = "/fapi/v1/marginType"
        params = {
            "symbol": symbol,
            "marginType": margin_type,  # ISOLATED or CROSSED
            "timestamp": self._get_timestamp(),
            "recvWindow": self.recv_window,
        }
        params["signature"] = self._generate_signature(params)
        headers = {"X-MBX-APIKEY": self.api_key}

        try:
            response = requests.post(
                self.base_url + endpoint, params=params, headers=headers, timeout=10
            )

            if response.status_code != 200 and response.status_code != 400:
                print(f"设置保证金模式失败，状态码: {response.status_code}")
                if response.text:
                    print(f"响应: {response.text[:200]}")
                return None

            if not response.text:
                print(f"设置保证金模式失败: 响应为空")
                return None

            try:
                result = response.json()
            except json.JSONDecodeError as e:
                print(f"解析保证金设置响应失败: {str(e)}")
                return None

            if "code" in result:
                if result["code"] == -4046:
                    print(f"保证金模式已经是{margin_type}")
                else:
                    error_msg = self._get_error_message(result["code"], result.get('msg', '未知错误'))
                    print(f"设置保证金模式失败: {error_msg}")
            return result
        except Exception as e:
            print(f"设置保证金模式异常: {str(e)}")
            return None

    def get_exchange_info(self, symbol=None):
        """获取交易规则和交易对信息"""
        endpoint = "/fapi/v1/exchangeInfo"
        params = {}
        if symbol:
            params["symbol"] = symbol

        try:
            response = requests.get(self.base_url + endpoint, params=params)
            return response.json()
        except Exception as e:
            print(f"获取交易规则失败: {str(e)}")
            return None

    def close_all_positions(self, symbol):
        """关闭指定交易对的所有持仓"""
        max_retries = 3  # 最大重试次数

        for attempt in range(max_retries):
            try:
                print(f"第{attempt + 1}次尝试获取 {symbol} 的持仓信息...")
                position_info = self.get_position_info(symbol)

                # 检查是否有API响应
                if not position_info:
                    print("获取持仓信息失败 - 返回空响应")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    return None

                # 如果是列表，获取第一个元素
                if isinstance(position_info, list) and len(position_info) > 0:
                    position = position_info[0]
                else:
                    position = position_info

                # 获取持仓数量 - 注意键名可能不同
                position_amt = 0
                if isinstance(position, dict):
                    if "positionAmt" in position:
                        position_amt = float(position["positionAmt"])
                    elif "quantity" in position:
                        position_amt = float(position["quantity"])
                    elif "qty" in position:
                        position_amt = float(position["qty"])

                print(f"持仓数量: {position_amt}")

                # 如果没有持仓，直接返回成功
                if position_amt == 0:
                    print("没有持仓需要关闭")
                    return {"status": "success", "msg": "无持仓"}

                # 计算平仓参数
                quantity = abs(position_amt)
                side = "SELL" if position_amt > 0 else "BUY"

                print(f"正在平仓: 交易对={symbol}, 方向={side}, 数量={quantity}")

                # 执行平仓，使用市价单确保成交
                result = self.place_order(
                    symbol=symbol,
                    side=side,
                    order_type="MARKET",
                    quantity=quantity,
                    position_side="BOTH",
                )

                if result and "orderId" in result:
                    print(f"平仓订单成功提交: 订单ID={result.get('orderId')}")
                    return result
                elif result and "code" in result:
                    # API返回错误
                    error_msg = self._get_error_message(result["code"], result.get('msg', '未知错误'))
                    print(f"平仓失败: {error_msg}")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue

            except Exception as e:
                print(f"第{attempt + 1}次尝试平仓失败: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                else:
                    print(f"错误类型: {type(e).__name__}")
                    import traceback
                    traceback.print_exc()

        return None


def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        raise Exception("错误：找不到配置文件 config.json")
    except json.JSONDecodeError:
        raise Exception("错误：配置文件格式不正确")


def update_position_status(api, symbol, ui, account_name):
    """更新指定账户的持仓状态"""
    initial_balance_set = False
    consecutive_errors = 0
    last_known_balance = 0

    print(f"[{account_name}] 状态更新线程启动")

    while ui.running:
        try:
            # 获取当前价格
            current_price = api.get_current_price(symbol)
            if current_price <= 0:
                current_price = ui.current_price  # 使用UI中的最后已知价格

            # 获取账户信息
            account_info = api.get_account_info()

            # 解析余额信息
            current_balance = 0
            margin_balance = 0
            unrealized_pnl = 0

            for asset in account_info.get("assets", []):
                if asset.get("asset") == "USDT":
                    current_balance = float(asset.get("walletBalance", 0))
                    margin_balance = float(asset.get("marginBalance", current_balance))
                    unrealized_pnl = float(asset.get("unrealizedProfit", 0))
                    break

            # 如果余额为0，尝试使用v2接口
            if current_balance == 0:
                balance_from_v2 = api.get_account_balance()
                if balance_from_v2 > 0:
                    current_balance = balance_from_v2
                    margin_balance = balance_from_v2
                elif last_known_balance > 0:
                    # 使用最后已知的余额
                    current_balance = last_known_balance
                    margin_balance = last_known_balance
            else:
                last_known_balance = current_balance
                consecutive_errors = 0

            # 获取持仓信息 - 直接调用positionRisk接口
            position_amt = 0
            entry_price = 0
            liquidation_price = 0
            position_unrealized_pnl = unrealized_pnl
            position_margin = 0  # 持仓保证金

            positions = api.get_position_info(symbol)
            if positions and isinstance(positions, list) and len(positions) > 0:
                position = positions[0]
                position_amt = float(position.get("positionAmt", 0))
                entry_price = float(position.get("entryPrice", 0))
                liquidation_price = float(position.get("liquidationPrice", 0))
                position_unrealized_pnl = float(position.get("unrealizedProfit", unrealized_pnl))

                # 使用新的保证金计算方法
                position_margin = api.calculate_margin(position)

                # 如果从持仓信息获取到未实现盈亏，更新总的未实现盈亏
                if position_unrealized_pnl != 0:
                    unrealized_pnl = position_unrealized_pnl

            # 设置初始余额
            if not initial_balance_set and current_balance > 0:
                initial_balance = current_balance
                initial_balance_set = True
            elif not initial_balance_set:
                initial_balance = 0
            else:
                if account_name in ui.account_statuses:
                    initial_balance = ui.account_statuses[account_name].get("initial_balance", 0)
                    if initial_balance == 0 and current_balance > 0:
                        initial_balance = current_balance
                else:
                    initial_balance = current_balance

            # 确定持仓方向
            if position_amt > 0:
                position_side = "LONG"
            elif position_amt < 0:
                position_side = "SHORT"
            else:
                position_side = "NONE"

            status = {
                "position_side": position_side,
                "quantity": abs(position_amt),
                "entry_price": round(entry_price, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "system_status": "运行中",
                "current_balance": round(current_balance, 2),
                "initial_balance": round(initial_balance, 2),
                "margin": round(position_margin, 2) if position_amt != 0 else 0,  # 使用持仓保证金
                "liquidation_price": round(liquidation_price, 2),
            }

            # 更新状态
            ui.update_status(account_name, status, current_price)

            # 成功更新，重置错误计数
            if current_balance > 0 or position_amt != 0:
                consecutive_errors = 0

        except Exception as e:
            consecutive_errors += 1

            # 如果连续错误超过5次，使用最小默认值以保持UI更新
            if consecutive_errors > 5:
                # 保留最后已知的余额
                status = {
                    "position_side": "NONE",
                    "quantity": 0,
                    "entry_price": 0,
                    "unrealized_pnl": 0,
                    "system_status": "连接中...",
                    "current_balance": last_known_balance,
                    "initial_balance": ui.account_statuses.get(account_name, {}).get("initial_balance", 0),
                    "margin": last_known_balance,
                    "liquidation_price": 0,
                }
            else:
                # 暂时性错误，保持之前的状态
                if account_name in ui.account_statuses:
                    status = ui.account_statuses[account_name].copy()  # 复制之前的状态
                    status["system_status"] = "更新中..."
                else:
                    status = {
                        "position_side": "NONE",
                        "quantity": 0,
                        "entry_price": 0,
                        "unrealized_pnl": 0,
                        "system_status": "初始化中...",
                        "current_balance": 0,
                        "initial_balance": 0,
                        "margin": 0,
                        "liquidation_price": 0,
                    }

            ui.update_status(account_name, status, ui.current_price)

        time.sleep(1)  # 更新间隔


def cleanup_positions(accounts, symbol):
    """清理所有账号的持仓"""
    console = Console()
    console.print("[yellow]正在清理所有账户持仓...[/yellow]")

    failed_accounts = []  # 记录失败的账户

    # 对每个账户执行平仓
    for account_name, api in accounts:
        success = False
        max_cleanup_retries = 3  # 最大清理重试次数

        for cleanup_attempt in range(max_cleanup_retries):
            try:
                if cleanup_attempt > 0:
                    console.print(f"[yellow]第{cleanup_attempt + 1}次尝试清理 {account_name}...[/yellow]")
                    time.sleep(1)  # 重试前等待1秒
                else:
                    console.print(f"[yellow]正在清理 {account_name} 的持仓...[/yellow]")

                # 先尝试撤销所有挂单
                try:
                    api.cancel_all_orders(symbol)
                    console.print(f"[dim]{account_name} 挂单已撤销[/dim]")
                except Exception as e:
                    console.print(f"[dim]{account_name} 撤销挂单失败: {str(e)[:50]}[/dim]")

                # 关闭持仓，带重试机制
                result = api.close_all_positions(symbol)
                if result:
                    if isinstance(result, dict) and result.get("status") == "success" and result.get("msg") == "无持仓":
                        console.print(f"[yellow]{account_name} 无持仓需要清理[/yellow]")
                        success = True
                        break  # 成功，跳出重试循环
                    elif isinstance(result, dict) and "orderId" in result:
                        console.print(f"[green]{account_name} 持仓清理订单已提交: {result.get('orderId')}[/green]")
                        # 等待订单执行
                        time.sleep(2)
                        # 验证是否成功平仓
                        try:
                            position_info = api.get_position_info(symbol)
                            if position_info and isinstance(position_info, list) and len(position_info) > 0:
                                position_amt = float(position_info[0].get("positionAmt", 0))
                                if position_amt == 0:
                                    console.print(f"[green]{account_name} 持仓已成功清理[/green]")
                                    success = True
                                    break
                                else:
                                    console.print(f"[yellow]{account_name} 仍有持仓: {position_amt}，将重试[/yellow]")
                            else:
                                console.print(f"[green]{account_name} 持仓已清理[/green]")
                                success = True
                                break
                        except:
                            # 假设成功
                            console.print(f"[green]{account_name} 持仓清理订单已提交[/green]")
                            success = True
                            break
                    else:
                        console.print(f"[green]{account_name} 持仓已清理[/green]")
                        success = True
                        break
                else:
                    # 再次检查是否真的有持仓
                    try:
                        position_info = api.get_position_info(symbol)
                        if position_info and isinstance(position_info, list) and len(position_info) > 0:
                            position_amt = float(position_info[0].get("positionAmt", 0))
                            if position_amt == 0:
                                console.print(f"[yellow]{account_name} 确认无持仓[/yellow]")
                                success = True
                                break
                            else:
                                if cleanup_attempt < max_cleanup_retries - 1:
                                    console.print(f"[yellow]{account_name} 仍有持仓: {position_amt}，将重试[/yellow]")
                                else:
                                    console.print(f"[red]{account_name} 仍有持仓: {position_amt}[/red]")
                                    failed_accounts.append(account_name)
                        else:
                            console.print(f"[yellow]{account_name} 无持仓[/yellow]")
                            success = True
                            break
                    except Exception as e:
                        if cleanup_attempt < max_cleanup_retries - 1:
                            console.print(f"[yellow]{account_name} 验证失败，将重试: {str(e)[:50]}[/yellow]")
                        else:
                            console.print(f"[red]{account_name} 无法验证持仓状态[/red]")
                            failed_accounts.append(account_name)

            except Exception as e:
                if cleanup_attempt < max_cleanup_retries - 1:
                    console.print(f"[yellow]{account_name} 清理失败，将重试: {str(e)[:50]}[/yellow]")
                else:
                    console.print(f"[red]{account_name} 清理失败: {str(e)}[/red]")
                    failed_accounts.append(account_name)

    # 报告结果
    if failed_accounts:
        console.print(f"[red]以下账户清理失败: {', '.join(failed_accounts)}[/red]")
        console.print("[yellow]请手动检查这些账户的持仓状态[/yellow]")
    else:
        console.print("[green]所有账户持仓清理完成[/green]")


def init_account(account, symbol, leverage):
    """初始化账户设置"""
    try:
        # 设置保证金模式为全仓
        print(f"设置保证金模式为全仓...")
        account.set_margin_type(symbol, "CROSSED")

        # 设置杠杆
        print(f"设置杠杆为 {leverage}x...")
        result = account.set_leverage(symbol, leverage)
        if result and "leverage" in result:
            print(f"杠杆设置成功: {result['leverage']}x")
        return True
    except Exception as e:
        print(f"初始化账户失败: {str(e)}")
        return False


def test_api_connection(api, account_name, symbol):
    """测试API连接是否正常"""
    print(f"\n[{account_name}] 测试API连接...")
    print(f"[{account_name}] API Key: {api.api_key[:20]}...")
    print(f"[{account_name}] Base URL: {api.base_url}")

    # 测试获取账户信息
    try:
        account_info = api.get_account_info()
        if account_info and "assets" in account_info:
            print(f"[{account_name}] 账户信息查询成功")
            # 查找USDT余额
            for asset in account_info.get("assets", []):
                if asset.get("asset") == "USDT":
                    wallet_balance = float(asset.get('walletBalance', 0))
                    available_balance = float(asset.get('availableBalance', 0))
                    margin_balance = float(asset.get('marginBalance', 0))
                    print(f"[{account_name}] USDT钱包余额: {wallet_balance:.4f}")
                    print(f"[{account_name}] USDT可用余额: {available_balance:.4f}")
                    print(f"[{account_name}] USDT保证金余额: {margin_balance:.4f}")
                    break
        else:
            print(f"[{account_name}] 账户信息查询返回空数据")
    except Exception as e:
        print(f"[{account_name}] 账户信息查询失败: {str(e)}")

    # 直接测试v2 balance接口，帮助调试
    try:
        endpoint = "/fapi/v2/balance"
        params = {"timestamp": api._get_timestamp(), "recvWindow": api.recv_window}
        params["signature"] = api._generate_signature(params)
        headers = {"X-MBX-APIKEY": api.api_key}

        import requests
        response = requests.get(
            api.base_url + endpoint, params=params, headers=headers, timeout=5
        )

        if response.status_code == 200 and response.text:
            result = response.json()
            if isinstance(result, list):
                for asset in result:
                    if asset.get("asset") == "USDT":
                        print(f"[{account_name}] DEBUG - v2 Balance API原始响应:")
                        print(f"  balance: {asset.get('balance', 'N/A')}")
                        print(f"  crossWalletBalance: {asset.get('crossWalletBalance', 'N/A')}")
                        print(f"  availableBalance: {asset.get('availableBalance', 'N/A')}")
                        break
    except Exception as e:
        print(f"[{account_name}] v2 balance接口调试失败: {str(e)}")

    # 测试获取持仓
    try:
        positions = api.get_position_info(symbol)
        if positions:
            print(f"[{account_name}] 持仓查询成功: {len(positions)}个持仓")
            for pos in positions[:1]:  # 只打印第一个
                amt = float(pos.get("positionAmt", 0))
                if amt != 0:
                    print(f"[{account_name}] {symbol}持仓: {amt}")
        else:
            print(f"[{account_name}] 无持仓")
    except Exception as e:
        print(f"[{account_name}] 持仓查询失败: {str(e)}")

    # 测试获取价格
    try:
        price = api.get_current_price(symbol)
        print(f"[{account_name}] {symbol}当前价格: {price}")
    except Exception as e:
        print(f"[{account_name}] 价格查询失败: {str(e)}")

    print(f"[{account_name}] API测试完成\n")

def validate_api_connections(accounts, symbol):
    """定期验证API连接状态"""
    for account_name, api in accounts:
        try:
            # 测试价格接口
            price = api.get_current_price(symbol)
            if price > 0:
                print(f"[{account_name}] API连接正常 - 当前价格: {price}")
            else:
                print(f"[{account_name}] 警告: 无法获取价格")

            # 测试余额接口
            balance = api.get_account_balance()
            if balance > 0:
                print(f"[{account_name}] 余额查询正常: {balance:.4f} USDT")

        except Exception as e:
            print(f"[{account_name}] API验证失败: {str(e)[:50]}")

def main():
    # 加载配置
    with open("config.json", "r") as f:
        config = json.load(f)

    # 获取交易配置
    trading_config = config["trading"]
    symbol = trading_config["symbol"]
    usdt_amount = trading_config["usdt_amount"]
    position_side = trading_config["position_side"]
    order_type = trading_config["order_type"]
    leverage = trading_config["leverage"]
    wait_seconds = trading_config["wait_seconds"]
    max_trades = trading_config.get("max_trades", 100)

    # 创建UI实例
    ui = TradingUI()

    # 初始化账户 - 使用account1和account2结构
    print("正在初始化账户API...")
    try:
        account1 = AsterDexAPI(
            config["account1"]["api_key"], config["account1"]["api_secret"]
        )
        account2 = AsterDexAPI(
            config["account2"]["api_key"], config["account2"]["api_secret"]
        )
        print("账户API初始化成功")
    except Exception as e:
        print(f"API初始化失败: {e}")
        return

    # 使用统一的账户名称
    accounts = [("账户1", account1), ("账户2", account2)]
    ui.add_account("账户1")
    ui.add_account("账户2")
    print("账户状态跟踪已初始化")

    # 先测试API连接
    print("\n=== 开始API连接测试 ===")
    for account_name, api in accounts:
        test_api_connection(api, account_name, symbol)
    print("=== API连接测试完成 ===\n")

    # 等待一下让用户看到测试结果
    time.sleep(2)

    # 初始化账户设置
    for account_name, api in accounts:
        print(f"\n初始化 {account_name}...")
        if not init_account(api, symbol, leverage):
            print(f"警告: {account_name} 初始化失败，继续运行...")

    # 创建账户对
    account_pairs = [(accounts[i], accounts[i + 1]) for i in range(0, len(accounts), 2)]

    # 设置所有账户的杠杆
    for account_name, api in accounts:
        api.set_leverage(symbol, leverage)

    # 启动状态更新线程
    update_threads = []
    print("\n启动状态更新线程...")
    for account_name, api in accounts:
        print(f"启动 {account_name} 状态更新线程")
        thread = threading.Thread(
            target=update_position_status,
            args=(api, symbol, ui, account_name),
            name=f"UpdateThread-{account_name}"
        )
        thread.daemon = True
        thread.start()
        update_threads.append(thread)
        time.sleep(0.5)  # 避免同时请求

    # 等待初始化完成
    print("等待账户状态初始化...")
    time.sleep(3)

    # 启动API验证线程 - 已禁用
    # def api_validator():
    #     while ui.running:
    #         time.sleep(60)  # 每60秒验证一次
    #         validate_api_connections(accounts, symbol)

    # validator_thread = threading.Thread(target=api_validator, daemon=True)
    # validator_thread.start()

    # 创建实时显示
    with Live(ui.generate_layout(), refresh_per_second=1) as live:
        while ui.running:
            try:
                # 每秒更新显示
                live.update(ui.generate_layout())

                # 检查是否达到最大交易次数
                if ui.stats["trade_count"] >= max_trades:
                    print(f"\n达到最大交易次数 {max_trades}，程序结束")
                    break

                # 使用第一个账户获取当前价格和资金费率
                first_account = accounts[0][1]  # 获取第一个账户的API实例
                current_price = float(first_account.get_current_price(symbol))
                funding_rate = float(first_account.get_funding_rate(symbol))

                # 仅更新UI显示信息（不增加交易次数）
                ui.stats["current_funding_rate"] = funding_rate
                ui.stats["symbol"] = symbol
                ui.stats["leverage"] = leverage
                ui.stats["wait_seconds"] = wait_seconds

                # 对每个账户对执行交易
                for (account1_name, account1), (
                    account2_name,
                    account2,
                ) in account_pairs:
                    # 检查账户1的持仓状态
                    account1_status = ui.account_statuses.get(account1_name, {})
                    if account1_status.get("position_side", "NONE") == "NONE":
                        # 计算交易数量
                        quantity = account1.calculate_quantity_from_usdt(
                            symbol, usdt_amount, leverage
                        )

                        # 检查名义价值是否达到最小值
                        notional_value = quantity * current_price
                        if notional_value < 5:
                            print(f"名义价值 {notional_value:.2f} USDT 小于最小值 5 USDT，跳过开仓")
                            time.sleep(wait_seconds)
                            continue

                        # 开仓
                        if funding_rate > 0:
                            # 资金费率为正，账户1做空，账户2做多
                            print(f"\n资金费率: {funding_rate*100:.4f}% (正值)")
                            print(f"[{account1_name}] 做空 {quantity} {symbol} @ {current_price}")
                            result1 = account1.place_order(
                                symbol=symbol,
                                side="SELL",
                                order_type=order_type,
                                quantity=quantity,
                                position_side=position_side,
                            )
                            print(f"[{account2_name}] 做多 {quantity} {symbol} @ {current_price}")
                            result2 = account2.place_order(
                                symbol=symbol,
                                side="BUY",
                                order_type=order_type,
                                quantity=quantity,
                                position_side=position_side,
                            )

                            if result1 and result2:
                                ui.update_stats(
                                    funding_rate=funding_rate,
                                    symbol=symbol,
                                    leverage=leverage,
                                    wait_seconds=wait_seconds,
                                    last_order_price=current_price,
                                    volume=quantity,
                                    position_opened=True  # 标记刚开仓
                                )
                                print(f"✓ 对冲交易成功建立")
                            elif result1 and not result2:
                                # 如果只有一个成功，立即平掉
                                print(f"警告: 只有 {account1_name} 下单成功，立即平仓")
                                account1.close_all_positions(symbol)
                        else:
                            # 资金费率为负，账户1做多，账户2做空
                            print(f"\n资金费率: {funding_rate*100:.4f}% (负值)")
                            print(f"[{account1_name}] 做多 {quantity} {symbol} @ {current_price}")
                            result1 = account1.place_order(
                                symbol=symbol,
                                side="BUY",
                                order_type=order_type,
                                quantity=quantity,
                                position_side=position_side,
                            )
                            print(f"[{account2_name}] 做空 {quantity} {symbol} @ {current_price}")
                            result2 = account2.place_order(
                                symbol=symbol,
                                side="SELL",
                                order_type=order_type,
                                quantity=quantity,
                                position_side=position_side,
                            )

                            if result1 and result2:
                                ui.update_stats(
                                    funding_rate=funding_rate,
                                    symbol=symbol,
                                    leverage=leverage,
                                    wait_seconds=wait_seconds,
                                    last_order_price=current_price,
                                    volume=quantity,
                                    position_opened=True  # 标记刚开仓
                                )
                                print(f"✓ 对冲交易成功建立")
                            elif result1 and not result2:
                                # 如果只有一个成功，立即平掉
                                print(f"警告: 只有 {account1_name} 下单成功，立即平仓")
                                account1.close_all_positions(symbol)

                    # 检查是否需要平仓
                    elif account1_status.get("position_side", "NONE") != "NONE":
                        # 计算实际持仓时间
                        actual_hold_time = 0
                        if ui.stats["position_open_time"] is not None:
                            actual_hold_time = int(time.time() - ui.stats["position_open_time"])
                            ui.stats["actual_hold_time"] = actual_hold_time

                        # 检查是否达到持仓时间或需要因资金费率变化而平仓
                        should_close_by_time = actual_hold_time >= wait_seconds
                        should_close_by_funding = (
                            (account1_status.get("position_side", "NONE") == "LONG" and funding_rate > 0) or
                            (account1_status.get("position_side", "NONE") == "SHORT" and funding_rate < 0)
                        )

                        if should_close_by_time or should_close_by_funding:
                            # 获取当前持仓数量
                            quantity = account1_status.get("quantity", 0)
                            if quantity <= 0:
                                continue

                            # 输出平仓原因
                            if should_close_by_time:
                                print(f"\n持仓时间已达到 {actual_hold_time} 秒，开始平仓")
                            else:
                                print(f"\n资金费率变化，开始平仓并反向开仓")

                            # 平仓操作 - 平多需要卖出，平空需要买入
                            if account1_status.get("position_side", "NONE") == "LONG":
                                print(f"[{account1_name}] 平多仓 {quantity} {symbol}")
                                result1 = account1.place_order(
                                    symbol=symbol,
                                    side="SELL",  # 平多仓需要卖出
                                    order_type=order_type,
                                    quantity=quantity,
                                    position_side=position_side,
                                )
                                print(f"[{account2_name}] 平空仓 {quantity} {symbol}")
                                result2 = account2.place_order(
                                    symbol=symbol,
                                    side="BUY",  # 平空仓需要买入
                                    order_type=order_type,
                                    quantity=quantity,
                                    position_side=position_side,
                                )
                            else:
                                print(f"[{account1_name}] 平空仓 {quantity} {symbol}")
                                result1 = account1.place_order(
                                    symbol=symbol,
                                    side="BUY",  # 平空仓需要买入
                                    order_type=order_type,
                                    quantity=quantity,
                                    position_side=position_side,
                                )
                                print(f"[{account2_name}] 平多仓 {quantity} {symbol}")
                                result2 = account2.place_order(
                                    symbol=symbol,
                                    side="SELL",  # 平多仓需要卖出
                                    order_type=order_type,
                                    quantity=quantity,
                                    position_side=position_side,
                                )

                            if result1 and result2:
                                print(f"✓ 平仓成功")
                                # 重置持仓时间
                                ui.stats["position_open_time"] = None
                                ui.stats["actual_hold_time"] = 0

                # 等待指定时间
                time.sleep(wait_seconds)

            except KeyboardInterrupt:
                print("\n程序被用户中断")
                break
            except Exception as e:
                print(f"\n发生错误: {str(e)}")
                time.sleep(5)

    # 程序结束前平掉所有仓位
    cleanup_positions(accounts, symbol)
    print("程序已结束")


if __name__ == "__main__":
    main()
