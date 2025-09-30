#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易历史记录系统
记录、存储和分析交易历史数据
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import sqlite3
import threading

class TradeRecord:
    """交易记录类"""
    
    def __init__(self, trade_id: str, symbol: str, side: str, quantity: float, 
                 price: float, timestamp: datetime, account: str, 
                 funding_rate: float = 0.0, pnl: float = 0.0):
        self.trade_id = trade_id
        self.symbol = symbol
        self.side = side  # BUY/SELL
        self.quantity = quantity
        self.price = price
        self.timestamp = timestamp
        self.account = account
        self.funding_rate = funding_rate
        self.pnl = pnl
        self.notional_value = quantity * price
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'trade_id': self.trade_id,
            'symbol': self.symbol,
            'side': self.side,
            'quantity': self.quantity,
            'price': self.price,
            'timestamp': self.timestamp.isoformat(),
            'account': self.account,
            'funding_rate': self.funding_rate,
            'pnl': self.pnl,
            'notional_value': self.notional_value
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TradeRecord':
        """从字典创建交易记录"""
        return cls(
            trade_id=data['trade_id'],
            symbol=data['symbol'],
            side=data['side'],
            quantity=data['quantity'],
            price=data['price'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            account=data['account'],
            funding_rate=data.get('funding_rate', 0.0),
            pnl=data.get('pnl', 0.0)
        )

class TradeHistoryManager:
    """交易历史管理器"""
    
    def __init__(self, db_path: str = "trade_history.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.init_database()
    
    def init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建交易记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
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
                )
            ''')
            
            # 创建交易对统计表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pair_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    date TEXT,
                    total_trades INTEGER,
                    total_volume REAL,
                    total_pnl REAL,
                    avg_funding_rate REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, date)
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_account ON trades(account)')
            
            conn.commit()
    
    def add_trade(self, trade: TradeRecord) -> bool:
        """添加交易记录"""
        try:
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO trades 
                        (trade_id, symbol, side, quantity, price, timestamp, 
                         account, funding_rate, pnl, notional_value)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        trade.trade_id, trade.symbol, trade.side, trade.quantity,
                        trade.price, trade.timestamp.isoformat(), trade.account,
                        trade.funding_rate, trade.pnl, trade.notional_value
                    ))
                    
                    conn.commit()
                    return True
        except Exception as e:
            print(f"添加交易记录失败: {e}")
            return False
    
    def get_trades(self, symbol: str = None, account: str = None, 
                   start_date: datetime = None, end_date: datetime = None,
                   limit: int = 100) -> List[TradeRecord]:
        """获取交易记录"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM trades WHERE 1=1"
                params = []
                
                if symbol:
                    query += " AND symbol = ?"
                    params.append(symbol)
                
                if account:
                    query += " AND account = ?"
                    params.append(account)
                
                if start_date:
                    query += " AND timestamp >= ?"
                    params.append(start_date.isoformat())
                
                if end_date:
                    query += " AND timestamp <= ?"
                    params.append(end_date.isoformat())
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                trades = []
                for row in rows:
                    trade = TradeRecord(
                        trade_id=row[1],
                        symbol=row[2],
                        side=row[3],
                        quantity=row[4],
                        price=row[5],
                        timestamp=datetime.fromisoformat(row[6]),
                        account=row[7],
                        funding_rate=row[8],
                        pnl=row[9]
                    )
                    trades.append(trade)
                
                return trades
        except Exception as e:
            print(f"获取交易记录失败: {e}")
            return []
    
    def get_daily_stats(self, date: datetime = None) -> Dict:
        """获取每日统计"""
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime('%Y-%m-%d')
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(notional_value) as total_volume,
                        SUM(pnl) as total_pnl,
                        AVG(funding_rate) as avg_funding_rate,
                        COUNT(DISTINCT symbol) as symbols_traded,
                        COUNT(DISTINCT account) as accounts_used
                    FROM trades 
                    WHERE DATE(timestamp) = ?
                ''', (date_str,))
                
                row = cursor.fetchone()
                
                return {
                    'date': date_str,
                    'total_trades': row[0] or 0,
                    'total_volume': row[1] or 0.0,
                    'total_pnl': row[2] or 0.0,
                    'avg_funding_rate': row[3] or 0.0,
                    'symbols_traded': row[4] or 0,
                    'accounts_used': row[5] or 0
                }
        except Exception as e:
            print(f"获取每日统计失败: {e}")
            return {}
    
    def get_symbol_stats(self, symbol: str, days: int = 30) -> Dict:
        """获取交易对统计"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(notional_value) as total_volume,
                        SUM(pnl) as total_pnl,
                        AVG(funding_rate) as avg_funding_rate,
                        MIN(price) as min_price,
                        MAX(price) as max_price,
                        AVG(price) as avg_price
                    FROM trades 
                    WHERE symbol = ? AND timestamp >= ? AND timestamp <= ?
                ''', (symbol, start_date.isoformat(), end_date.isoformat()))
                
                row = cursor.fetchone()
                
                return {
                    'symbol': symbol,
                    'period_days': days,
                    'total_trades': row[0] or 0,
                    'total_volume': row[1] or 0.0,
                    'total_pnl': row[2] or 0.0,
                    'avg_funding_rate': row[3] or 0.0,
                    'min_price': row[4] or 0.0,
                    'max_price': row[5] or 0.0,
                    'avg_price': row[6] or 0.0
                }
        except Exception as e:
            print(f"获取交易对统计失败: {e}")
            return {}
    
    def get_account_performance(self, account: str, days: int = 30) -> Dict:
        """获取账户表现"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN side = 'BUY' THEN notional_value ELSE 0 END) as buy_volume,
                        SUM(CASE WHEN side = 'SELL' THEN notional_value ELSE 0 END) as sell_volume,
                        SUM(pnl) as total_pnl,
                        AVG(pnl) as avg_pnl_per_trade,
                        COUNT(CASE WHEN pnl > 0 THEN 1 END) as profitable_trades,
                        COUNT(CASE WHEN pnl < 0 THEN 1 END) as losing_trades
                    FROM trades 
                    WHERE account = ? AND timestamp >= ? AND timestamp <= ?
                ''', (account, start_date.isoformat(), end_date.isoformat()))
                
                row = cursor.fetchone()
                
                total_trades = row[0] or 0
                profitable_trades = row[5] or 0
                losing_trades = row[6] or 0
                
                win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
                
                return {
                    'account': account,
                    'period_days': days,
                    'total_trades': total_trades,
                    'buy_volume': row[1] or 0.0,
                    'sell_volume': row[2] or 0.0,
                    'total_pnl': row[3] or 0.0,
                    'avg_pnl_per_trade': row[4] or 0.0,
                    'profitable_trades': profitable_trades,
                    'losing_trades': losing_trades,
                    'win_rate': win_rate
                }
        except Exception as e:
            print(f"获取账户表现失败: {e}")
            return {}
    
    def export_to_csv(self, filename: str, symbol: str = None, 
                      start_date: datetime = None, end_date: datetime = None):
        """导出交易记录到CSV"""
        try:
            import csv
            
            trades = self.get_trades(symbol=symbol, start_date=start_date, 
                                   end_date=end_date, limit=10000)
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['trade_id', 'symbol', 'side', 'quantity', 'price', 
                             'timestamp', 'account', 'funding_rate', 'pnl', 'notional_value']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for trade in trades:
                    writer.writerow(trade.to_dict())
            
            print(f"交易记录已导出到: {filename}")
            return True
        except Exception as e:
            print(f"导出CSV失败: {e}")
            return False
    
    def cleanup_old_records(self, days: int = 90):
        """清理旧记录"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with self.lock:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        DELETE FROM trades 
                        WHERE timestamp < ?
                    ''', (cutoff_date.isoformat(),))
                    
                    deleted_count = cursor.rowcount
                    conn.commit()
                    
                    print(f"已清理 {deleted_count} 条旧交易记录")
                    return deleted_count
        except Exception as e:
            print(f"清理旧记录失败: {e}")
            return 0

# 全局交易历史管理器实例
trade_history_manager = TradeHistoryManager()
