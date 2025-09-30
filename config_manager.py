#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理增强系统
提供配置验证、备份恢复、导入导出等功能
"""

import json
import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any
import threading
from pathlib import Path

class ConfigValidator:
    """配置验证器"""
    
    @staticmethod
    def validate_account_config(config: Dict) -> List[str]:
        """验证账户配置"""
        errors = []
        
        if not config.get("name"):
            errors.append("账户名称不能为空")
        
        api_key = config.get("api_key", "")
        if not api_key:
            errors.append("API密钥不能为空")
        elif len(api_key) < 10:
            errors.append("API密钥长度不足")
        
        api_secret = config.get("api_secret", "")
        if not api_secret:
            errors.append("API Secret不能为空")
        elif len(api_secret) < 10:
            errors.append("API Secret长度不足")
        
        return errors
    
    @staticmethod
    def validate_trading_config(config: Dict) -> List[str]:
        """验证交易配置"""
        errors = []
        
        # 验证交易对
        symbol = config.get("symbol", "")
        valid_symbols = ["ETHUSDT", "BTCUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
        if symbol not in valid_symbols:
            errors.append(f"交易对必须是以下之一: {', '.join(valid_symbols)}")
        
        # 验证USDT金额
        try:
            usdt_amount = float(config.get("usdt_amount", 0))
            if usdt_amount <= 0:
                errors.append("USDT金额必须大于0")
            elif usdt_amount < 5:
                errors.append("USDT金额不能小于5（交易所最小限制）")
            elif usdt_amount > 10000:
                errors.append("USDT金额不建议超过10000（风险控制）")
        except (ValueError, TypeError):
            errors.append("USDT金额必须是有效数字")
        
        # 验证杠杆倍数
        try:
            leverage = int(config.get("leverage", 0))
            if leverage <= 0:
                errors.append("杠杆倍数必须大于0")
            elif leverage > 125:
                errors.append("杠杆倍数不能超过125")
        except (ValueError, TypeError):
            errors.append("杠杆倍数必须是有效整数")
        
        # 验证持仓时间
        try:
            wait_seconds = int(config.get("wait_seconds", 0))
            if wait_seconds < 30:
                errors.append("持仓时间不能少于30秒")
            elif wait_seconds > 3600:
                errors.append("持仓时间不建议超过3600秒（1小时）")
        except (ValueError, TypeError):
            errors.append("持仓时间必须是有效整数")
        
        # 验证最大交易次数
        try:
            max_trades = int(config.get("max_trades", 0))
            if max_trades <= 0:
                errors.append("最大交易次数必须大于0")
            elif max_trades > 1000:
                errors.append("最大交易次数不建议超过1000")
        except (ValueError, TypeError):
            errors.append("最大交易次数必须是有效整数")
        
        return errors

class ConfigManager:
    """增强的配置管理器"""
    
    def __init__(self, config_file: str = "config.json", backup_dir: str = "config_backups"):
        self.config_file = config_file
        self.backup_dir = backup_dir
        self.lock = threading.Lock()
        
        # 创建备份目录
        Path(self.backup_dir).mkdir(exist_ok=True)
        
        # 配置模板
        self.default_config = {
            "account1": {
                "name": "账户1",
                "api_key": "",
                "api_secret": ""
            },
            "account2": {
                "name": "账户2", 
                "api_key": "",
                "api_secret": ""
            },
            "trading": {
                "symbol": "ETHUSDT",
                "leverage": 20,
                "usdt_amount": 300,
                "wait_seconds": 60,
                "max_trades": 10,
                "order_type": "MARKET",
                "position_side": "BOTH"
            },
            "risk": {
                "max_position_size": 1000.0,
                "max_drawdown_percent": 10.0,
                "stop_loss_percent": 5.0,
                "take_profit_percent": 10.0,
                "max_daily_loss": 500.0
            },
            "ui": {
                "theme": "superhero",
                "window_size": "1700x1000",
                "auto_save": True,
                "show_notifications": True
            },
            "logging": {
                "level": "INFO",
                "max_file_size": 10485760,  # 10MB
                "backup_count": 5,
                "console_output": True
            }
        }
    
    def load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with self.lock:
                if os.path.exists(self.config_file):
                    with open(self.config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    
                    # 合并默认配置（确保所有字段都存在）
                    merged_config = self._merge_config(self.default_config, config)
                    
                    # 如果配置有更新，保存回文件
                    if merged_config != config:
                        self.save_config(merged_config)
                    
                    return merged_config
                else:
                    # 创建默认配置文件
                    self.save_config(self.default_config)
                    return self.default_config.copy()
        
        except Exception as e:
            print(f"加载配置失败: {e}")
            return self.default_config.copy()
    
    def save_config(self, config: Dict) -> bool:
        """保存配置文件"""
        try:
            with self.lock:
                # 验证配置
                errors = self.validate_config(config)
                if errors:
                    print(f"配置验证失败: {'; '.join(errors)}")
                    return False
                
                # 备份当前配置
                if os.path.exists(self.config_file):
                    self.create_backup()
                
                # 保存新配置
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                
                print("✅ 配置保存成功")
                return True
        
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    def validate_config(self, config: Dict) -> List[str]:
        """验证完整配置"""
        all_errors = []
        
        # 验证账户配置
        for account_key in ["account1", "account2"]:
            if account_key in config:
                account_errors = ConfigValidator.validate_account_config(config[account_key])
                if account_errors:
                    all_errors.extend([f"{account_key}: {error}" for error in account_errors])
        
        # 验证交易配置
        if "trading" in config:
            trading_errors = ConfigValidator.validate_trading_config(config["trading"])
            if trading_errors:
                all_errors.extend([f"交易配置: {error}" for error in trading_errors])
        
        return all_errors
    
    def create_backup(self, custom_name: str = None) -> str:
        """创建配置备份"""
        try:
            if not os.path.exists(self.config_file):
                return ""
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if custom_name:
                backup_name = f"config_backup_{custom_name}_{timestamp}.json"
            else:
                backup_name = f"config_backup_{timestamp}.json"
            
            backup_path = os.path.join(self.backup_dir, backup_name)
            shutil.copy2(self.config_file, backup_path)
            
            print(f"✅ 配置备份已创建: {backup_path}")
            
            # 清理旧备份（保留最近10个）
            self._cleanup_old_backups()
            
            return backup_path
        
        except Exception as e:
            print(f"创建备份失败: {e}")
            return ""
    
    def restore_backup(self, backup_file: str) -> bool:
        """恢复配置备份"""
        try:
            backup_path = os.path.join(self.backup_dir, backup_file)
            if not os.path.exists(backup_path):
                print(f"备份文件不存在: {backup_path}")
                return False
            
            # 验证备份文件
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_config = json.load(f)
            
            errors = self.validate_config(backup_config)
            if errors:
                print(f"备份文件验证失败: {'; '.join(errors)}")
                return False
            
            # 备份当前配置
            self.create_backup("before_restore")
            
            # 恢复配置
            shutil.copy2(backup_path, self.config_file)
            print(f"✅ 配置已从备份恢复: {backup_file}")
            return True
        
        except Exception as e:
            print(f"恢复备份失败: {e}")
            return False
    
    def list_backups(self) -> List[Dict]:
        """列出所有备份文件"""
        try:
            backups = []
            for file in os.listdir(self.backup_dir):
                if file.startswith("config_backup_") and file.endswith(".json"):
                    file_path = os.path.join(self.backup_dir, file)
                    stat = os.stat(file_path)
                    
                    backups.append({
                        "filename": file,
                        "size": stat.st_size,
                        "created": datetime.fromtimestamp(stat.st_ctime),
                        "modified": datetime.fromtimestamp(stat.st_mtime)
                    })
            
            # 按创建时间排序
            backups.sort(key=lambda x: x["created"], reverse=True)
            return backups
        
        except Exception as e:
            print(f"列出备份失败: {e}")
            return []
    
    def export_config(self, export_path: str, include_sensitive: bool = False) -> bool:
        """导出配置到指定路径"""
        try:
            config = self.load_config()
            
            if not include_sensitive:
                # 移除敏感信息
                export_config = self._remove_sensitive_data(config)
            else:
                export_config = config
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_config, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 配置已导出到: {export_path}")
            return True
        
        except Exception as e:
            print(f"导出配置失败: {e}")
            return False
    
    def import_config(self, import_path: str, merge: bool = True) -> bool:
        """从指定路径导入配置"""
        try:
            if not os.path.exists(import_path):
                print(f"导入文件不存在: {import_path}")
                return False
            
            with open(import_path, 'r', encoding='utf-8') as f:
                import_config = json.load(f)
            
            if merge:
                # 合并配置
                current_config = self.load_config()
                merged_config = self._merge_config(current_config, import_config)
            else:
                # 完全替换
                merged_config = self._merge_config(self.default_config, import_config)
            
            # 验证配置
            errors = self.validate_config(merged_config)
            if errors:
                print(f"导入配置验证失败: {'; '.join(errors)}")
                return False
            
            # 保存配置
            return self.save_config(merged_config)
        
        except Exception as e:
            print(f"导入配置失败: {e}")
            return False
    
    def reset_to_default(self) -> bool:
        """重置为默认配置"""
        try:
            # 备份当前配置
            self.create_backup("before_reset")
            
            # 重置为默认
            return self.save_config(self.default_config.copy())
        
        except Exception as e:
            print(f"重置配置失败: {e}")
            return False
    
    def get_config_summary(self) -> Dict:
        """获取配置摘要"""
        try:
            config = self.load_config()
            
            return {
                "accounts_configured": sum(1 for key in ["account1", "account2"] 
                                         if config.get(key, {}).get("api_key")),
                "trading_symbol": config.get("trading", {}).get("symbol", "未设置"),
                "leverage": config.get("trading", {}).get("leverage", 0),
                "usdt_amount": config.get("trading", {}).get("usdt_amount", 0),
                "max_trades": config.get("trading", {}).get("max_trades", 0),
                "theme": config.get("ui", {}).get("theme", "默认"),
                "backup_count": len(self.list_backups()),
                "config_file_size": os.path.getsize(self.config_file) if os.path.exists(self.config_file) else 0,
                "last_modified": datetime.fromtimestamp(os.path.getmtime(self.config_file)).isoformat() 
                                if os.path.exists(self.config_file) else None
            }
        
        except Exception as e:
            print(f"获取配置摘要失败: {e}")
            return {}
    
    def _merge_config(self, base: Dict, update: Dict) -> Dict:
        """递归合并配置"""
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _remove_sensitive_data(self, config: Dict) -> Dict:
        """移除敏感数据"""
        safe_config = config.copy()
        
        # 移除API密钥和Secret
        for account_key in ["account1", "account2"]:
            if account_key in safe_config:
                if "api_key" in safe_config[account_key]:
                    safe_config[account_key]["api_key"] = "***已隐藏***"
                if "api_secret" in safe_config[account_key]:
                    safe_config[account_key]["api_secret"] = "***已隐藏***"
        
        return safe_config
    
    def _cleanup_old_backups(self, keep_count: int = 10):
        """清理旧备份文件"""
        try:
            backups = self.list_backups()
            if len(backups) > keep_count:
                # 删除多余的备份
                for backup in backups[keep_count:]:
                    backup_path = os.path.join(self.backup_dir, backup["filename"])
                    os.remove(backup_path)
                    print(f"🗑️ 已删除旧备份: {backup['filename']}")
        
        except Exception as e:
            print(f"清理备份失败: {e}")

# 全局配置管理器实例
config_manager = ConfigManager()
