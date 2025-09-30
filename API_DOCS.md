# AsterDex 对冲工具 API 文档

## 概述

本文档详细介绍了 AsterDex 对冲工具的各个模块和 API 接口，帮助开发者理解和扩展系统功能。

## 模块架构

```
asterdex-auto-tool/
├── aster_trading.py          # 核心交易API
├── aster_trading_gui_bootstrap.py  # 主GUI界面
├── log_manager.py            # 日志管理系统
├── trade_history.py          # 交易历史记录
├── risk_manager.py           # 风险管理系统
├── config_manager.py         # 配置管理系统
└── config.json              # 配置文件
```

## 核心模块 API

### 1. AsterDexAPI (aster_trading.py)

#### 类说明
```python
class AsterDexAPI:
    """AsterDex 交易所 API 封装类"""
    
    def __init__(self, api_key: str, api_secret: str):
        """初始化 API 客户端"""
```

#### 主要方法

##### 账户相关
```python
def get_account_balance(self) -> float:
    """获取账户余额"""
    
def get_position_info(self, symbol: str) -> List[Dict]:
    """获取持仓信息"""
    
def set_leverage(self, symbol: str, leverage: int) -> bool:
    """设置杠杆倍数"""
```

##### 交易相关
```python
def place_order(self, symbol: str, side: str, order_type: str, 
                quantity: float, position_side: str = "BOTH") -> Dict:
    """下单交易"""
    
def get_current_price(self, symbol: str) -> float:
    """获取当前价格"""
    
def get_funding_rate(self, symbol: str) -> float:
    """获取资金费率"""
```

##### 工具方法
```python
def calculate_quantity_from_usdt(self, symbol: str, usdt_amount: float, 
                                leverage: int) -> float:
    """根据USDT金额计算交易数量"""
    
def calculate_margin(self, position: Dict) -> float:
    """计算保证金"""
```

### 2. EnhancedLogManager (log_manager.py)

#### 类说明
```python
class EnhancedLogManager:
    """增强的日志管理器"""
    
    def __init__(self, log_dir: str = "logs", max_file_size: int = 10*1024*1024):
        """初始化日志管理器"""
```

#### 主要方法

##### 日志记录
```python
def log(self, level: str, message: str, category: str = "GENERAL"):
    """记录日志"""
    
def info(self, message: str, category: str = "INFO"):
    """记录信息日志"""
    
def warning(self, message: str, category: str = "WARNING"):
    """记录警告日志"""
    
def error(self, message: str, category: str = "ERROR"):
    """记录错误日志"""
```

##### 日志管理
```python
def search_logs(self, keyword: str, days: int = 7) -> List[str]:
    """搜索日志"""
    
def get_log_stats(self) -> dict:
    """获取日志统计信息"""
    
def export_logs(self, start_date: str, end_date: str, output_file: str):
    """导出日志"""
```

### 3. TradeHistoryManager (trade_history.py)

#### 类说明
```python
class TradeRecord:
    """交易记录类"""
    
class TradeHistoryManager:
    """交易历史管理器"""
    
    def __init__(self, db_path: str = "trade_history.db"):
        """初始化交易历史管理器"""
```

#### 主要方法

##### 记录管理
```python
def add_trade(self, trade: TradeRecord) -> bool:
    """添加交易记录"""
    
def get_trades(self, symbol: str = None, account: str = None, 
               start_date: datetime = None, end_date: datetime = None,
               limit: int = 100) -> List[TradeRecord]:
    """获取交易记录"""
```

##### 统计分析
```python
def get_daily_stats(self, date: datetime = None) -> Dict:
    """获取每日统计"""
    
def get_symbol_stats(self, symbol: str, days: int = 30) -> Dict:
    """获取交易对统计"""
    
def get_account_performance(self, account: str, days: int = 30) -> Dict:
    """获取账户表现"""
```

##### 数据导出
```python
def export_to_csv(self, filename: str, symbol: str = None, 
                  start_date: datetime = None, end_date: datetime = None):
    """导出交易记录到CSV"""
```

### 4. RiskManager (risk_manager.py)

#### 类说明
```python
class RiskLevel(Enum):
    """风险等级枚举"""
    LOW = "低风险"
    MEDIUM = "中等风险"
    HIGH = "高风险"
    CRITICAL = "极高风险"

class RiskManager:
    """风险管理器"""
    
    def __init__(self, config_file: str = "risk_config.json"):
        """初始化风险管理器"""
```

#### 主要方法

##### 风险计算
```python
def calculate_position_size(self, account_balance: float, risk_percent: float, 
                          entry_price: float, stop_loss_price: float) -> float:
    """计算合适的持仓大小"""
    
def check_stop_loss(self, entry_price: float, current_price: float, 
                   position_side: str) -> bool:
    """检查是否触发止损"""
    
def check_take_profit(self, entry_price: float, current_price: float, 
                     position_side: str) -> bool:
    """检查是否触发止盈"""
```

##### 风险评估
```python
def evaluate_position_risk(self, position: Dict) -> PositionRisk:
    """评估单个持仓的风险"""
    
def calculate_portfolio_risk(self, positions: List[Dict], 
                           account_balances: Dict) -> RiskMetrics:
    """计算投资组合风险指标"""
```

##### 风险监控
```python
def generate_risk_alert(self, alert_type: str, message: str, severity: str = "WARNING"):
    """生成风险警报"""
    
def get_risk_summary(self) -> Dict:
    """获取风险摘要"""
```

### 5. ConfigManager (config_manager.py)

#### 类说明
```python
class ConfigValidator:
    """配置验证器"""
    
class ConfigManager:
    """增强的配置管理器"""
    
    def __init__(self, config_file: str = "config.json", backup_dir: str = "config_backups"):
        """初始化配置管理器"""
```

#### 主要方法

##### 配置操作
```python
def load_config(self) -> Dict:
    """加载配置文件"""
    
def save_config(self, config: Dict) -> bool:
    """保存配置文件"""
    
def validate_config(self, config: Dict) -> List[str]:
    """验证完整配置"""
```

##### 备份管理
```python
def create_backup(self, custom_name: str = None) -> str:
    """创建配置备份"""
    
def restore_backup(self, backup_file: str) -> bool:
    """恢复配置备份"""
    
def list_backups(self) -> List[Dict]:
    """列出所有备份文件"""
```

##### 导入导出
```python
def export_config(self, export_path: str, include_sensitive: bool = False) -> bool:
    """导出配置到指定路径"""
    
def import_config(self, import_path: str, merge: bool = True) -> bool:
    """从指定路径导入配置"""
```

## 配置文件格式

### config.json
```json
{
  "account1": {
    "name": "账户1",
    "api_key": "your_api_key_here",
    "api_secret": "your_api_secret_here"
  },
  "account2": {
    "name": "账户2",
    "api_key": "your_api_key_here",
    "api_secret": "your_api_secret_here"
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
    "auto_save": true,
    "show_notifications": true
  },
  "logging": {
    "level": "INFO",
    "max_file_size": 10485760,
    "backup_count": 5,
    "console_output": true
  }
}
```

### risk_config.json
```json
{
  "max_position_size": 1000.0,
  "max_drawdown_percent": 10.0,
  "stop_loss_percent": 5.0,
  "take_profit_percent": 10.0,
  "max_daily_loss": 500.0,
  "max_leverage": 100,
  "min_margin_ratio": 0.1,
  "risk_free_rate": 0.03,
  "var_confidence": 0.95,
  "alert_thresholds": {
    "drawdown": 5.0,
    "margin_ratio": 0.15,
    "daily_loss": 300.0
  }
}
```

## 数据库结构

### 交易历史数据库 (trade_history.db)

#### trades 表
```sql
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id TEXT UNIQUE,
    symbol TEXT,
    side TEXT,
    quantity REAL,
    price REAL,
    timestamp TEXT,
    account TEXT,
    funding_rate REAL,
    pnl REAL,
    notional_value REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

#### pair_stats 表
```sql
CREATE TABLE pair_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
    date TEXT,
    total_trades INTEGER,
    total_volume REAL,
    total_pnl REAL,
    avg_funding_rate REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date)
);
```

## 事件和回调

### 日志回调
```python
# 添加日志回调函数
def log_callback(log_entry):
    print(f"[{log_entry['level']}] {log_entry['message']}")

log_manager.add_callback(log_callback)
```

### 风险警报回调
```python
# 风险警报处理
def handle_risk_alert(alert):
    if alert['severity'] == 'CRITICAL':
        # 执行紧急停止交易
        stop_trading()
```

## 错误处理

### 常见错误类型
- `APIError`: API调用失败
- `ConfigError`: 配置文件错误
- `ValidationError`: 数据验证失败
- `DatabaseError`: 数据库操作失败

### 错误处理示例
```python
try:
    api = AsterDexAPI(api_key, api_secret)
    balance = api.get_account_balance()
except APIError as e:
    log_manager.error(f"API调用失败: {e}")
except Exception as e:
    log_manager.error(f"未知错误: {e}")
```

## 扩展开发

### 添加新的交易策略
1. 继承 `AsterDexAPI` 类
2. 实现自定义交易逻辑
3. 集成到主GUI界面

### 添加新的风险指标
1. 扩展 `RiskMetrics` 数据类
2. 在 `RiskManager` 中添加计算方法
3. 更新UI显示

### 添加新的数据导出格式
1. 在 `TradeHistoryManager` 中添加导出方法
2. 支持新的文件格式（如Excel、PDF等）

## 性能优化建议

1. **数据库优化**
   - 定期清理旧数据
   - 添加适当的索引
   - 使用连接池

2. **内存管理**
   - 限制日志队列大小
   - 定期清理缓存数据
   - 使用生成器处理大数据集

3. **网络优化**
   - 实现请求重试机制
   - 使用连接复用
   - 添加请求限流

## 安全考虑

1. **API密钥保护**
   - 加密存储敏感信息
   - 使用环境变量
   - 定期轮换密钥

2. **数据验证**
   - 严格验证输入参数
   - 防止SQL注入
   - 限制文件访问权限

3. **日志安全**
   - 避免记录敏感信息
   - 设置日志文件权限
   - 定期清理日志文件

## 版本兼容性

- Python 3.7+
- SQLite 3.0+
- tkinter (通常随Python安装)
- ttkbootstrap 1.10+

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request
5. 等待代码审查

## 许可证

本项目采用 MIT 许可证，详见 LICENSE 文件。
