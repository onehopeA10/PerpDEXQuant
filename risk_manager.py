#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风险管理系统
提供止损止盈、风险评估和资金管理功能
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import threading

class RiskLevel(Enum):
    """风险等级枚举"""
    LOW = "低风险"
    MEDIUM = "中等风险"
    HIGH = "高风险"
    CRITICAL = "极高风险"

@dataclass
class RiskMetrics:
    """风险指标"""
    max_drawdown: float = 0.0  # 最大回撤
    current_drawdown: float = 0.0  # 当前回撤
    win_rate: float = 0.0  # 胜率
    profit_factor: float = 0.0  # 盈利因子
    sharpe_ratio: float = 0.0  # 夏普比率
    var_95: float = 0.0  # 95% VaR
    risk_level: RiskLevel = RiskLevel.LOW

@dataclass
class PositionRisk:
    """持仓风险"""
    symbol: str
    account: str
    position_size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    liquidation_price: float
    margin_ratio: float
    risk_score: float

class RiskManager:
    """风险管理器"""
    
    def __init__(self, config_file: str = "risk_config.json"):
        self.config_file = config_file
        self.config = self.load_config()
        self.position_history = []
        self.pnl_history = []
        self.lock = threading.Lock()
        
        # 风险监控状态
        self.monitoring = False
        self.alerts = []
        self.last_check_time = datetime.now()
    
    def load_config(self) -> Dict:
        """加载风险配置"""
        default_config = {
            "max_position_size": 1000.0,  # 最大持仓金额
            "max_drawdown_percent": 10.0,  # 最大回撤百分比
            "stop_loss_percent": 5.0,  # 止损百分比
            "take_profit_percent": 10.0,  # 止盈百分比
            "max_daily_loss": 500.0,  # 每日最大亏损
            "max_leverage": 100,  # 最大杠杆
            "min_margin_ratio": 0.1,  # 最小保证金比例
            "risk_free_rate": 0.03,  # 无风险利率
            "var_confidence": 0.95,  # VaR置信度
            "alert_thresholds": {
                "drawdown": 5.0,
                "margin_ratio": 0.15,
                "daily_loss": 300.0
            }
        }
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并默认配置
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
        except FileNotFoundError:
            self.save_config(default_config)
            return default_config
        except Exception as e:
            print(f"加载风险配置失败: {e}")
            return default_config
    
    def save_config(self, config: Dict = None):
        """保存风险配置"""
        if config is None:
            config = self.config
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存风险配置失败: {e}")
    
    def calculate_position_size(self, account_balance: float, risk_percent: float, 
                              entry_price: float, stop_loss_price: float) -> float:
        """
        计算合适的持仓大小
        
        Args:
            account_balance: 账户余额
            risk_percent: 风险百分比 (0-100)
            entry_price: 入场价格
            stop_loss_price: 止损价格
            
        Returns:
            建议的持仓大小
        """
        try:
            # 计算每单位风险
            price_risk = abs(entry_price - stop_loss_price) / entry_price
            
            # 计算风险金额
            risk_amount = account_balance * (risk_percent / 100)
            
            # 计算持仓大小
            position_size = risk_amount / price_risk
            
            # 限制最大持仓
            max_position = min(
                self.config["max_position_size"],
                account_balance * 0.8  # 不超过账户余额的80%
            )
            
            return min(position_size, max_position)
        
        except Exception as e:
            print(f"计算持仓大小失败: {e}")
            return 0.0
    
    def check_stop_loss(self, entry_price: float, current_price: float, 
                       position_side: str) -> bool:
        """
        检查是否触发止损
        
        Args:
            entry_price: 入场价格
            current_price: 当前价格
            position_side: 持仓方向 (LONG/SHORT)
            
        Returns:
            是否应该止损
        """
        stop_loss_percent = self.config["stop_loss_percent"] / 100
        
        if position_side == "LONG":
            # 多头止损：当前价格低于入场价格一定百分比
            stop_price = entry_price * (1 - stop_loss_percent)
            return current_price <= stop_price
        elif position_side == "SHORT":
            # 空头止损：当前价格高于入场价格一定百分比
            stop_price = entry_price * (1 + stop_loss_percent)
            return current_price >= stop_price
        
        return False
    
    def check_take_profit(self, entry_price: float, current_price: float, 
                         position_side: str) -> bool:
        """
        检查是否触发止盈
        
        Args:
            entry_price: 入场价格
            current_price: 当前价格
            position_side: 持仓方向 (LONG/SHORT)
            
        Returns:
            是否应该止盈
        """
        take_profit_percent = self.config["take_profit_percent"] / 100
        
        if position_side == "LONG":
            # 多头止盈：当前价格高于入场价格一定百分比
            profit_price = entry_price * (1 + take_profit_percent)
            return current_price >= profit_price
        elif position_side == "SHORT":
            # 空头止盈：当前价格低于入场价格一定百分比
            profit_price = entry_price * (1 - take_profit_percent)
            return current_price <= profit_price
        
        return False
    
    def evaluate_position_risk(self, position: Dict) -> PositionRisk:
        """评估单个持仓的风险"""
        try:
            symbol = position.get("symbol", "")
            account = position.get("account", "")
            position_size = abs(float(position.get("positionAmt", 0)))
            entry_price = float(position.get("entryPrice", 0))
            current_price = float(position.get("markPrice", entry_price))
            unrealized_pnl = float(position.get("unRealizedProfit", 0))
            liquidation_price = float(position.get("liquidationPrice", 0))
            
            # 计算保证金比例
            notional_value = position_size * current_price
            margin = float(position.get("isolatedMargin", notional_value / 10))
            margin_ratio = margin / notional_value if notional_value > 0 else 0
            
            # 计算风险评分 (0-100)
            risk_score = 0
            
            # 价格风险 (30%)
            if entry_price > 0:
                price_change = abs(current_price - entry_price) / entry_price
                risk_score += min(price_change * 100, 30)
            
            # 保证金风险 (40%)
            if margin_ratio < self.config["min_margin_ratio"]:
                risk_score += 40
            elif margin_ratio < self.config["min_margin_ratio"] * 2:
                risk_score += 20
            
            # 清算风险 (30%)
            if liquidation_price > 0:
                distance_to_liquidation = abs(current_price - liquidation_price) / current_price
                if distance_to_liquidation < 0.05:  # 5%以内
                    risk_score += 30
                elif distance_to_liquidation < 0.1:  # 10%以内
                    risk_score += 15
            
            return PositionRisk(
                symbol=symbol,
                account=account,
                position_size=position_size,
                entry_price=entry_price,
                current_price=current_price,
                unrealized_pnl=unrealized_pnl,
                liquidation_price=liquidation_price,
                margin_ratio=margin_ratio,
                risk_score=min(risk_score, 100)
            )
        
        except Exception as e:
            print(f"评估持仓风险失败: {e}")
            return PositionRisk("", "", 0, 0, 0, 0, 0, 0, 100)
    
    def calculate_portfolio_risk(self, positions: List[Dict], 
                               account_balances: Dict) -> RiskMetrics:
        """计算投资组合风险指标"""
        try:
            # 计算总资产和当前权益
            total_balance = sum(account_balances.values())
            total_unrealized_pnl = sum(
                float(pos.get("unRealizedProfit", 0)) for pos in positions
            )
            current_equity = total_balance + total_unrealized_pnl
            
            # 更新PnL历史
            with self.lock:
                self.pnl_history.append({
                    'timestamp': datetime.now(),
                    'equity': current_equity,
                    'pnl': total_unrealized_pnl
                })
                
                # 只保留最近30天的数据
                cutoff_time = datetime.now() - timedelta(days=30)
                self.pnl_history = [
                    record for record in self.pnl_history 
                    if record['timestamp'] > cutoff_time
                ]
            
            # 计算最大回撤
            max_equity = max([record['equity'] for record in self.pnl_history], default=current_equity)
            max_drawdown = (max_equity - current_equity) / max_equity * 100 if max_equity > 0 else 0
            current_drawdown = max_drawdown
            
            # 计算胜率（需要交易历史）
            win_rate = self.calculate_win_rate()
            
            # 计算盈利因子
            profit_factor = self.calculate_profit_factor()
            
            # 计算夏普比率
            sharpe_ratio = self.calculate_sharpe_ratio()
            
            # 计算VaR
            var_95 = self.calculate_var()
            
            # 确定风险等级
            risk_level = self.determine_risk_level(max_drawdown, current_drawdown)
            
            return RiskMetrics(
                max_drawdown=max_drawdown,
                current_drawdown=current_drawdown,
                win_rate=win_rate,
                profit_factor=profit_factor,
                sharpe_ratio=sharpe_ratio,
                var_95=var_95,
                risk_level=risk_level
            )
        
        except Exception as e:
            print(f"计算投资组合风险失败: {e}")
            return RiskMetrics()
    
    def calculate_win_rate(self) -> float:
        """计算胜率"""
        try:
            # 这里需要从交易历史中获取数据
            # 暂时返回模拟数据，实际应该从 trade_history_manager 获取
            return 65.0
        except Exception as e:
            print(f"计算胜率失败: {e}")
            return 0.0
    
    def calculate_profit_factor(self) -> float:
        """计算盈利因子"""
        try:
            if len(self.pnl_history) < 2:
                return 1.0
            
            profits = []
            losses = []
            
            for i in range(1, len(self.pnl_history)):
                pnl_change = self.pnl_history[i]['pnl'] - self.pnl_history[i-1]['pnl']
                if pnl_change > 0:
                    profits.append(pnl_change)
                elif pnl_change < 0:
                    losses.append(abs(pnl_change))
            
            total_profit = sum(profits)
            total_loss = sum(losses)
            
            return total_profit / total_loss if total_loss > 0 else float('inf')
        
        except:
            return 1.0
    
    def calculate_sharpe_ratio(self) -> float:
        """计算夏普比率"""
        try:
            if len(self.pnl_history) < 2:
                return 0.0
            
            returns = []
            for i in range(1, len(self.pnl_history)):
                prev_equity = self.pnl_history[i-1]['equity']
                curr_equity = self.pnl_history[i]['equity']
                if prev_equity > 0:
                    returns.append((curr_equity - prev_equity) / prev_equity)
            
            if not returns:
                return 0.0
            
            avg_return = sum(returns) / len(returns)
            risk_free_rate = self.config["risk_free_rate"] / 365  # 日化
            
            excess_returns = [r - risk_free_rate for r in returns]
            avg_excess_return = sum(excess_returns) / len(excess_returns)
            
            # 计算标准差
            variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
            std_dev = variance ** 0.5
            
            return avg_excess_return / std_dev if std_dev > 0 else 0.0
        
        except:
            return 0.0
    
    def calculate_var(self, confidence: float = None) -> float:
        """计算风险价值 (VaR)"""
        try:
            if confidence is None:
                confidence = self.config["var_confidence"]
            
            if len(self.pnl_history) < 10:
                return 0.0
            
            returns = []
            for i in range(1, len(self.pnl_history)):
                prev_equity = self.pnl_history[i-1]['equity']
                curr_equity = self.pnl_history[i]['equity']
                if prev_equity > 0:
                    returns.append((curr_equity - prev_equity) / prev_equity)
            
            if not returns:
                return 0.0
            
            # 排序并找到对应百分位数
            returns.sort()
            index = int((1 - confidence) * len(returns))
            var = abs(returns[index]) if index < len(returns) else 0
            
            # 转换为金额
            current_equity = self.pnl_history[-1]['equity']
            return var * current_equity
        
        except:
            return 0.0
    
    def determine_risk_level(self, max_drawdown: float, current_drawdown: float) -> RiskLevel:
        """确定风险等级"""
        if max_drawdown > 15 or current_drawdown > 10:
            return RiskLevel.CRITICAL
        elif max_drawdown > 10 or current_drawdown > 7:
            return RiskLevel.HIGH
        elif max_drawdown > 5 or current_drawdown > 3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def check_daily_loss_limit(self, current_pnl: float) -> bool:
        """检查是否超过每日亏损限制"""
        max_daily_loss = self.config["max_daily_loss"]
        return current_pnl < -max_daily_loss
    
    def generate_risk_alert(self, alert_type: str, message: str, severity: str = "WARNING"):
        """生成风险警报"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'type': alert_type,
            'message': message,
            'severity': severity
        }
        
        with self.lock:
            self.alerts.append(alert)
            # 只保留最近100条警报
            if len(self.alerts) > 100:
                self.alerts = self.alerts[-100:]
        
        print(f"🚨 风险警报 [{severity}]: {message}")
    
    def get_risk_summary(self) -> Dict:
        """获取风险摘要"""
        return {
            'config': self.config,
            'alerts_count': len(self.alerts),
            'recent_alerts': self.alerts[-5:] if self.alerts else [],
            'monitoring_status': self.monitoring,
            'last_check': self.last_check_time.isoformat()
        }

# 全局风险管理器实例
risk_manager = RiskManager()
