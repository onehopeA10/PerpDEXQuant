#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的日志管理系统
提供更好的日志格式化、文件管理和搜索功能
"""

import logging
import os
import time
from datetime import datetime
from typing import Optional, List
import threading
import queue

class EnhancedLogManager:
    """增强的日志管理器"""
    
    def __init__(self, log_dir: str = "logs", max_file_size: int = 10*1024*1024):
        """
        初始化日志管理器
        
        Args:
            log_dir: 日志文件目录
            max_file_size: 单个日志文件最大大小（字节）
        """
        self.log_dir = log_dir
        self.max_file_size = max_file_size
        self.log_queue = queue.Queue()
        self.callbacks = []
        
        # 创建日志目录
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 设置日志格式
        self.formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 创建文件处理器
        self.setup_file_handler()
        
        # 启动日志处理线程
        self.log_thread = threading.Thread(target=self._process_logs, daemon=True)
        self.log_thread.start()
    
    def setup_file_handler(self):
        """设置文件处理器"""
        log_filename = os.path.join(
            self.log_dir, 
            f"trading_{datetime.now().strftime('%Y%m%d')}.log"
        )
        
        # 创建文件处理器
        self.file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        self.file_handler.setFormatter(self.formatter)
        
        # 配置根日志器
        self.logger = logging.getLogger('trading')
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(self.file_handler)
    
    def add_callback(self, callback):
        """添加日志回调函数"""
        self.callbacks.append(callback)
    
    def log(self, level: str, message: str, category: str = "GENERAL"):
        """
        记录日志
        
        Args:
            level: 日志级别 (INFO, WARNING, ERROR, DEBUG)
            message: 日志消息
            category: 日志分类
        """
        timestamp = datetime.now()
        formatted_message = f"[{category}] {message}"
        
        # 添加到队列
        self.log_queue.put({
            'timestamp': timestamp,
            'level': level,
            'message': formatted_message,
            'category': category
        })
    
    def info(self, message: str, category: str = "INFO"):
        """记录信息日志"""
        self.log("INFO", message, category)
    
    def warning(self, message: str, category: str = "WARNING"):
        """记录警告日志"""
        self.log("WARNING", message, category)
    
    def error(self, message: str, category: str = "ERROR"):
        """记录错误日志"""
        self.log("ERROR", message, category)
    
    def debug(self, message: str, category: str = "DEBUG"):
        """记录调试日志"""
        self.log("DEBUG", message, category)
    
    def _process_logs(self):
        """处理日志队列"""
        while True:
            try:
                if not self.log_queue.empty():
                    log_entry = self.log_queue.get()
                    
                    # 写入文件
                    level = log_entry['level']
                    message = log_entry['message']
                    
                    if level == "INFO":
                        self.logger.info(message)
                    elif level == "WARNING":
                        self.logger.warning(message)
                    elif level == "ERROR":
                        self.logger.error(message)
                    elif level == "DEBUG":
                        self.logger.debug(message)
                    
                    # 调用回调函数
                    for callback in self.callbacks:
                        try:
                            callback(log_entry)
                        except Exception as e:
                            print(f"日志回调错误: {e}")
                    
                    # 检查文件大小
                    self._check_file_rotation()
                
                time.sleep(0.1)
            except Exception as e:
                print(f"日志处理错误: {e}")
                time.sleep(1)
    
    def _check_file_rotation(self):
        """检查是否需要轮转日志文件"""
        try:
            current_file = self.file_handler.baseFilename
            if os.path.exists(current_file):
                file_size = os.path.getsize(current_file)
                if file_size > self.max_file_size:
                    self._rotate_log_file()
        except Exception as e:
            print(f"检查日志文件大小错误: {e}")
    
    def _rotate_log_file(self):
        """轮转日志文件"""
        try:
            # 关闭当前文件处理器
            self.logger.removeHandler(self.file_handler)
            self.file_handler.close()
            
            # 重命名当前文件
            current_file = self.file_handler.baseFilename
            timestamp = datetime.now().strftime('%H%M%S')
            new_name = current_file.replace('.log', f'_{timestamp}.log')
            os.rename(current_file, new_name)
            
            # 创建新的文件处理器
            self.setup_file_handler()
            
        except Exception as e:
            print(f"轮转日志文件错误: {e}")
    
    def search_logs(self, keyword: str, days: int = 7) -> List[str]:
        """
        搜索日志
        
        Args:
            keyword: 搜索关键词
            days: 搜索最近几天的日志
            
        Returns:
            匹配的日志行列表
        """
        results = []
        try:
            # 获取日志文件列表
            log_files = []
            for i in range(days):
                date = datetime.now() - timedelta(days=i)
                filename = f"trading_{date.strftime('%Y%m%d')}.log"
                filepath = os.path.join(self.log_dir, filename)
                if os.path.exists(filepath):
                    log_files.append(filepath)
            
            # 搜索关键词
            for filepath in log_files:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        if keyword.lower() in line.lower():
                            results.append(f"{os.path.basename(filepath)}:{line_num}: {line.strip()}")
        
        except Exception as e:
            print(f"搜索日志错误: {e}")
        
        return results
    
    def get_log_stats(self) -> dict:
        """获取日志统计信息"""
        stats = {
            'total_files': 0,
            'total_size': 0,
            'today_lines': 0,
            'error_count': 0,
            'warning_count': 0
        }
        
        try:
            # 统计日志文件
            for filename in os.listdir(self.log_dir):
                if filename.endswith('.log'):
                    filepath = os.path.join(self.log_dir, filename)
                    stats['total_files'] += 1
                    stats['total_size'] += os.path.getsize(filepath)
                    
                    # 统计今天的日志
                    today = datetime.now().strftime('%Y%m%d')
                    if today in filename:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            for line in f:
                                stats['today_lines'] += 1
                                if 'ERROR' in line:
                                    stats['error_count'] += 1
                                elif 'WARNING' in line:
                                    stats['warning_count'] += 1
        
        except Exception as e:
            print(f"获取日志统计错误: {e}")
        
        return stats
    
    def export_logs(self, start_date: str, end_date: str, output_file: str):
        """
        导出指定日期范围的日志
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            output_file: 输出文件路径
        """
        try:
            from datetime import datetime, timedelta
            
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            
            with open(output_file, 'w', encoding='utf-8') as out_f:
                current = start
                while current <= end:
                    filename = f"trading_{current.strftime('%Y%m%d')}.log"
                    filepath = os.path.join(self.log_dir, filename)
                    
                    if os.path.exists(filepath):
                        out_f.write(f"\n=== {filename} ===\n")
                        with open(filepath, 'r', encoding='utf-8') as in_f:
                            out_f.write(in_f.read())
                    
                    current += timedelta(days=1)
            
            print(f"日志已导出到: {output_file}")
            
        except Exception as e:
            print(f"导出日志错误: {e}")

# 全局日志管理器实例
log_manager = EnhancedLogManager()
