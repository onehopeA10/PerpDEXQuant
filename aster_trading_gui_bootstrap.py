#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 忽略 libpng 警告
import warnings
import os
import sys
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*iCCP.*")

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledText
from ttkbootstrap.toast import ToastNotification
import tkinter as tk
from tkinter import messagebox
import threading
import time
import json
import os
from datetime import datetime
import queue

# 导入原有的交易逻辑
from aster_trading import AsterDexAPI

# 导入新增的模块
from log_manager import log_manager
from trade_history import trade_history_manager, TradeRecord
from risk_manager import risk_manager

class BootstrapTradingGUI:
    def set_window_icon(self):
        """设置窗口图标 - 支持多种格式和打包后运行"""
        import sys
        import platform

        # 获取正确的路径（支持打包后的exe）
        if getattr(sys, 'frozen', False):
            # 如果是打包后的exe
            application_path = sys._MEIPASS
        else:
            # 如果是普通Python运行
            application_path = os.path.dirname(os.path.abspath(__file__))

        # Windows系统优先使用ICO格式
        if platform.system() == 'Windows':
            # 优先级顺序：faviconV2.ico > icon.ico
            icon_files = [
                os.path.join(application_path, "faviconV2.ico"),
                os.path.join(application_path, "icon.ico"),
                "faviconV2.ico",
                "icon.ico"
            ]
        else:
            # 其他系统使用PNG格式
            icon_files = [
                os.path.join(application_path, "faviconV2.png"),
                "faviconV2.png",
                os.path.join(application_path, "faviconV2.ico"),
                "faviconV2.ico"
            ]

        icon_set = False
        for icon_file in icon_files:
            if os.path.exists(icon_file):
                try:
                    if icon_file.endswith('.ico'):
                        # Windows平台使用ico文件
                        self.root.iconbitmap(default=icon_file)
                        # 设置任务栏图标（Windows特有）
                        self.root.wm_iconbitmap(icon_file)
                        print(f"✅ 已设置图标: {icon_file}")
                        icon_set = True
                        break
                    elif icon_file.endswith('.png'):
                        # 使用PNG作为备选
                        photo = tk.PhotoImage(file=icon_file)
                        self.root.iconphoto(True, photo)
                        print(f"✅ 已设置图标: {icon_file}")
                        icon_set = True
                        break
                except Exception as e:
                    print(f"⚠️ 设置图标失败 {icon_file}: {e}")
                    continue

        if not icon_set:
            print("❌ 未找到图标文件，使用默认图标")

    def __init__(self):
        # 创建主窗口，使用darkly主题（深色主题）
        self.root = ttk.Window(
            title="onehopeA9的对冲工具",
            themename="superhero",  # 可选: darkly, cyborg, vapor, solar, superhero
            size=(1700, 1000),
            resizable=(True, True)
        )

        # 设置窗口图标 - 优先使用ICO格式
        self.set_window_icon()

        # 设置窗口最小尺寸
        self.root.minsize(1600, 900)

        # 窗口居中
        self.center_window()

        # 配置文件路径
        self.config_file = "config.json"
        self.config = self.load_config()

        # 交易控制变量
        self.trading_active = False
        self.trading_thread = None
        self.update_thread = None

        # 账户API实例
        self.account1_api = None
        self.account2_api = None

        # 日志队列
        self.log_queue = queue.Queue()

        # 当前页面
        self.current_page = "dashboard"

        # Toast通知
        self.toast = ToastNotification(
            title="系统通知",
            message="",
            duration=3000,
            bootstyle="success"
        )

        # 交易统计
        self.stats = {
            "trade_count": 0,
            "total_volume_usdt": 0,
            "position_open_time": None,
            "actual_hold_time": 0,
            "current_funding_rate": 0,
            "current_price": 0,
            "symbol": self.config.get("trading", {}).get("symbol", "ETHUSDT"),
            "leverage": self.config.get("trading", {}).get("leverage", 100),
            "wait_seconds": self.config.get("trading", {}).get("wait_seconds", 300),
            "initial_total_balance": 0,
            "last_trade_time": None
        }

        # 账户状态
        self.account_status = {
            "账户1": {
                "position_side": "NONE",
                "quantity": 0,
                "entry_price": 0,
                "unrealized_pnl": 0,
                "margin": 0,
                "liquidation_price": 0,
                "current_balance": 0,
                "initial_balance": 0,
                "last_update": "-"
            },
            "账户2": {
                "position_side": "NONE",
                "quantity": 0,
                "entry_price": 0,
                "unrealized_pnl": 0,
                "margin": 0,
                "liquidation_price": 0,
                "current_balance": 0,
                "initial_balance": 0,
                "last_update": "-"
            }
        }

        # 创建UI
        self.create_ui()

        # 启动更新循环
        self.update_display()

        # 窗口关闭处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def center_window(self):
        """让窗口在屏幕上居中"""
        self.root.update_idletasks()

        # 获取屏幕宽度和高度
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # 获取窗口宽度和高度
        window_width = 1700
        window_height = 1000

        # 计算居中位置
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2 - 30  # 稍微偏上一点

        # 设置窗口位置
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def create_ui(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=BOTH, expand=YES)

        # 创建顶部工具栏
        self.create_toolbar(main_frame)

        # 创建笔记本（选项卡）控件
        self.notebook = ttk.Notebook(main_frame, bootstyle="dark")
        self.notebook.pack(fill=BOTH, expand=YES, padx=5, pady=5)

        # 创建仪表板页面
        self.dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.dashboard_frame, text="📊 交易仪表板")
        self.create_dashboard()

        # 创建配置页面
        self.config_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.config_frame, text="⚙️ 系统配置")
        self.create_config_page()

        # 创建日志页面
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text="📝 交易日志")
        self.create_log_page()

    def create_toolbar(self, parent):
        """创建工具栏"""
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=X, padx=5, pady=5)

        # 左侧标题
        title_frame = ttk.Frame(toolbar)
        title_frame.pack(side=LEFT)

        title_label = ttk.Label(
            title_frame,
            text="🚀 onehopeA9的对冲工具",
            font=("Microsoft YaHei UI", 16, "bold")
        )
        title_label.pack(side=LEFT, padx=10)

        # 创建可点击的Twitter链接
        subtitle_label = ttk.Label(
            title_frame,
            text="免费开源,关注支持❤️Twitter: @onehopeA9",
            font=("Microsoft YaHei UI", 11, "bold"),
            bootstyle="warning",  # 使用warning黄色更显眼
            cursor="hand2"  # 鼠标变成手型
        )
        subtitle_label.pack(side=LEFT, padx=(20, 0))

        # 添加点击事件打开Twitter
        import webbrowser
        subtitle_label.bind("<Button-1>", lambda e: webbrowser.open("https://x.com/onehopeA9"))

        # 鼠标悬停效果
        def on_enter(e):
            subtitle_label.configure(bootstyle="info", font=("Microsoft YaHei UI", 11, "bold underline"))

        def on_leave(e):
            subtitle_label.configure(bootstyle="warning", font=("Microsoft YaHei UI", 11, "bold"))

        subtitle_label.bind("<Enter>", on_enter)
        subtitle_label.bind("<Leave>", on_leave)

        # 右侧控制按钮
        control_frame = ttk.Frame(toolbar)
        control_frame.pack(side=RIGHT)

        self.start_btn = ttk.Button(
            control_frame,
            text="▶ 启动交易",
            command=self.start_trading,
            bootstyle="success-outline",
            width=12
        )
        self.start_btn.pack(side=LEFT, padx=5)

        self.stop_btn = ttk.Button(
            control_frame,
            text="⏹ 停止交易",
            command=self.stop_trading,
            bootstyle="danger-outline",
            width=12,
            state=DISABLED
        )
        self.stop_btn.pack(side=LEFT, padx=5)

    def create_dashboard(self):
        """创建仪表板"""
        # 创建外层容器用于居中
        outer_container = ttk.Frame(self.dashboard_frame)
        outer_container.pack(fill=BOTH, expand=YES)

        # 创建内容容器，限制最大宽度
        main_container = ttk.Frame(outer_container)
        main_container.place(relx=0.5, rely=0.5, anchor="center", width=1600, height=900)

        # 统计卡片区域
        stats_container = ttk.Frame(main_container)
        stats_container.pack(fill=X, padx=10, pady=(5, 10))

        # 创建统计卡片
        self.create_stat_cards(stats_container)

        # 创建两列布局
        columns_frame = ttk.Frame(main_container)
        columns_frame.pack(fill=BOTH, expand=YES, padx=10, pady=5)

        # 左列 - 市场信息
        left_col = ttk.Frame(columns_frame)
        left_col.pack(side=LEFT, fill=BOTH, expand=YES, padx=(0, 5))

        # 市场信息卡片
        market_card = ttk.LabelFrame(
            left_col,
            text="📈 市场信息",
            bootstyle="primary",
            padding=15
        )
        market_card.pack(fill=BOTH, expand=YES)

        self.create_market_info(market_card)

        # 右列 - 账户状态
        right_col = ttk.Frame(columns_frame)
        right_col.pack(side=RIGHT, fill=BOTH, expand=YES, padx=(5, 0))

        # 账户状态卡片
        account_card = ttk.LabelFrame(
            right_col,
            text="💼 账户状态",
            bootstyle="info",
            padding=15
        )
        account_card.pack(fill=BOTH, expand=YES)

        self.create_account_table(account_card)

        # 实时日志区域
        log_card = ttk.LabelFrame(
            main_container,
            text="📊 实时交易动态",
            bootstyle="secondary",
            padding=10
        )
        log_card.pack(fill=BOTH, expand=YES, padx=10, pady=(5, 10))

        self.dashboard_log = ScrolledText(
            log_card,
            height=8,
            wrap=tk.WORD,
            autohide=True
        )
        self.dashboard_log.pack(fill=BOTH, expand=YES)

    def create_stat_cards(self, parent):
        """创建统计卡片"""
        self.stat_meters = {}

        # 第一行统计
        row1 = ttk.Frame(parent)
        row1.pack(fill=X, pady=(0, 10))

        # 当前价格表
        price_frame = ttk.Frame(row1)
        price_frame.pack(side=LEFT, fill=BOTH, expand=YES, padx=5)

        price_meter = ttk.Meter(
            price_frame,
            metersize=160,
            padding=15,
            amountused=0,
            metertype="semi",
            subtext="当前价格 USDT",
            subtextstyle="secondary",
            bootstyle="primary",
            textright="",
            stripethickness=10
        )
        price_meter.pack()
        self.stat_meters["price"] = price_meter

        # 总盈亏表
        pnl_frame = ttk.Frame(row1)
        pnl_frame.pack(side=LEFT, fill=BOTH, expand=YES, padx=5)

        pnl_meter = ttk.Meter(
            pnl_frame,
            metersize=160,
            padding=15,
            amountused=0,
            metertype="semi",
            subtext="总盈亏 USDT",
            subtextstyle="secondary",
            bootstyle="success",
            textright="",
            stripethickness=10
        )
        pnl_meter.pack()
        self.stat_meters["pnl"] = pnl_meter

        # 交易次数表
        trades_frame = ttk.Frame(row1)
        trades_frame.pack(side=LEFT, fill=BOTH, expand=YES, padx=5)

        trades_meter = ttk.Meter(
            trades_frame,
            metersize=160,
            padding=15,
            amountused=0,
            metertype="semi",
            subtext="交易次数",
            subtextstyle="secondary",
            bootstyle="warning",
            textright="/100",
            stripethickness=10
        )
        trades_meter.pack()
        self.stat_meters["trades"] = trades_meter

        # 持仓时间表
        time_frame = ttk.Frame(row1)
        time_frame.pack(side=LEFT, fill=BOTH, expand=YES, padx=5)

        time_meter = ttk.Meter(
            time_frame,
            metersize=160,
            padding=15,
            amountused=0,
            metertype="semi",
            subtext="持仓时间(秒)",
            subtextstyle="secondary",
            bootstyle="info",
            textright="/30",
            stripethickness=10
        )
        time_meter.pack()
        self.stat_meters["time"] = time_meter

    def create_market_info(self, parent):
        """创建市场信息面板"""
        self.market_labels = {}

        info_items = [
            ("交易对", "ETHUSDT"),
            ("当前杠杆", "20x"),
            ("资金费率", "0.0000%"),
            ("总交易量", "0.00 USDT"),
            ("账户1余额", "0.00 USDT"),
            ("账户2余额", "0.00 USDT"),
            ("初始总资产", "0.00 USDT"),
            ("上次交易", "-"),
            ("当前时间", "-")
        ]

        for i, (label, value) in enumerate(info_items):
            row_frame = ttk.Frame(parent)
            row_frame.pack(fill=X, pady=3)

            label_widget = ttk.Label(
                row_frame,
                text=label,
                font=("Microsoft YaHei UI", 10),
                width=15,
                anchor=W
            )
            label_widget.pack(side=LEFT)

            # 根据不同类型使用不同样式
            style = "primary" if "余额" in label or "资产" in label else "secondary"

            value_widget = ttk.Label(
                row_frame,
                text=value,
                font=("Microsoft YaHei UI", 10, "bold"),
                bootstyle=style
            )
            value_widget.pack(side=RIGHT)

            self.market_labels[label] = value_widget

    def create_account_table(self, parent):
        """创建账户状态表格"""
        # 创建Treeview
        columns = ('账号', '方向', '数量', '开仓价', '盈亏', '保证金', '清算价')

        self.account_tree = ttk.Treeview(
            parent,
            columns=columns,
            show='headings',
            height=8,
            bootstyle="primary"
        )

        # 设置列
        column_widths = [80, 60, 100, 100, 100, 100, 100]
        for col, width in zip(columns, column_widths):
            self.account_tree.heading(col, text=col)
            self.account_tree.column(col, width=width, anchor=CENTER)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(
            parent,
            orient=VERTICAL,
            command=self.account_tree.yview,
            bootstyle="primary-round"
        )

        self.account_tree.configure(yscrollcommand=scrollbar.set)

        self.account_tree.pack(side=LEFT, fill=BOTH, expand=YES)
        scrollbar.pack(side=RIGHT, fill=Y)

        # 初始化数据
        self.account_tree.insert('', 'end', iid='账户1',
                                values=('账户1', '-', '0.000', '0.00', '0.00', '0.00', '0.00'))
        self.account_tree.insert('', 'end', iid='账户2',
                                values=('账户2', '-', '0.000', '0.00', '0.00', '0.00', '0.00'))

        # 设置标签样式
        self.account_tree.tag_configure('long', foreground='#00ff00')
        self.account_tree.tag_configure('short', foreground='#ff0000')

    def create_config_page(self):
        """创建配置页面"""
        # 创建滚动框架
        canvas = ttk.Canvas(self.config_frame)
        scrollbar = ttk.Scrollbar(self.config_frame, orient="vertical", command=canvas.yview)
        config_container = ttk.Frame(canvas)

        config_container.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        # 在canvas中创建窗口，并居中
        canvas.create_window((850, 0), window=config_container, anchor="n")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 账户1配置
        account1_frame = ttk.LabelFrame(
            config_container,
            text="👤 账户1 API配置",
            padding=20,
            bootstyle="primary"
        )
        account1_frame.pack(fill=X, padx=50, pady=15)

        self.account1_entries = {}
        self.create_account_inputs(account1_frame, "account1", self.account1_entries)

        # 账户2配置
        account2_frame = ttk.LabelFrame(
            config_container,
            text="👥 账户2 API配置",
            padding=20,
            bootstyle="info"
        )
        account2_frame.pack(fill=X, padx=50, pady=15)

        self.account2_entries = {}
        self.create_account_inputs(account2_frame, "account2", self.account2_entries)

        # 交易参数配置
        trading_frame = ttk.LabelFrame(
            config_container,
            text="📊 交易参数配置",
            padding=20,
            bootstyle="success"
        )
        trading_frame.pack(fill=X, padx=50, pady=15)

        self.trading_entries = {}
        self.create_trading_inputs(trading_frame)

        # 按钮组
        button_frame = ttk.Frame(config_container)
        button_frame.pack(pady=25)

        save_btn = ttk.Button(
            button_frame,
            text="💾 保存配置",
            command=self.save_config,
            bootstyle="success",
            width=20
        )
        save_btn.pack(side=LEFT, padx=5)

        reset_btn = ttk.Button(
            button_frame,
            text="🔄 重置配置",
            command=self.reset_config,
            bootstyle="warning",
            width=20
        )
        reset_btn.pack(side=LEFT, padx=5)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_account_inputs(self, parent, account_key, entries_dict):
        """创建账户配置输入框"""
        # 账户名称
        name_frame = ttk.Frame(parent)
        name_frame.pack(fill=X, pady=5)

        ttk.Label(name_frame, text="账户名称:", width=15).pack(side=LEFT)
        name_entry = ttk.Entry(name_frame, bootstyle="primary")
        name_entry.pack(side=LEFT, fill=X, expand=YES, padx=(10, 0))
        name_entry.insert(0, self.config.get(account_key, {}).get("name", ""))
        entries_dict["name"] = name_entry

        # API Key
        key_frame = ttk.Frame(parent)
        key_frame.pack(fill=X, pady=5)

        ttk.Label(key_frame, text="API密钥:", width=15).pack(side=LEFT)
        key_entry = ttk.Entry(key_frame, bootstyle="primary")
        key_entry.pack(side=LEFT, fill=X, expand=YES, padx=(10, 0))
        key_entry.insert(0, self.config.get(account_key, {}).get("api_key", ""))
        entries_dict["api_key"] = key_entry

        # API Secret
        secret_frame = ttk.Frame(parent)
        secret_frame.pack(fill=X, pady=5)

        ttk.Label(secret_frame, text="API Secret:", width=15).pack(side=LEFT)
        secret_entry = ttk.Entry(secret_frame, show="*", bootstyle="primary")
        secret_entry.pack(side=LEFT, fill=X, expand=YES, padx=(10, 0))
        secret_entry.insert(0, self.config.get(account_key, {}).get("api_secret", ""))
        entries_dict["api_secret"] = secret_entry

    def create_trading_inputs(self, parent):
        """创建交易参数输入框"""
        config_items = [
            ("交易对", "symbol", self.config.get("trading", {}).get("symbol", "ETHUSDT")),
            ("USDT金额", "usdt_amount", str(self.config.get("trading", {}).get("usdt_amount", 300))),
            ("杠杆倍数", "leverage", str(self.config.get("trading", {}).get("leverage", 100))),
            ("持仓时间(秒)", "wait_seconds", str(self.config.get("trading", {}).get("wait_seconds", 300))),
            ("最大交易次数", "max_trades", str(self.config.get("trading", {}).get("max_trades", 10)))
        ]

        for label, key, default in config_items:
            frame = ttk.Frame(parent)
            frame.pack(fill=X, pady=5)

            ttk.Label(frame, text=f"{label}:", width=15).pack(side=LEFT)

            if key == "symbol":
                # 使用下拉框选择交易对
                entry = ttk.Combobox(
                    frame,
                    values=["ETHUSDT", "BTCUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"],
                    bootstyle="success"
                )
            else:
                entry = ttk.Entry(frame, bootstyle="success")

            entry.pack(side=LEFT, fill=X, expand=YES, padx=(10, 0))
            entry.set(default) if isinstance(entry, ttk.Combobox) else entry.insert(0, default)
            self.trading_entries[key] = entry

    def create_log_page(self):
        """创建日志页面"""
        log_container = ttk.Frame(self.log_frame)
        log_container.pack(fill=BOTH, expand=YES, padx=10, pady=10)

        # 控制栏
        control_bar = ttk.Frame(log_container)
        control_bar.pack(fill=X, pady=(0, 10))

        ttk.Label(control_bar, text="📝 系统日志", font=("Microsoft YaHei UI", 12, "bold")).pack(side=LEFT)

        clear_btn = ttk.Button(
            control_bar,
            text="清空日志",
            command=self.clear_log,
            bootstyle="secondary-outline"
        )
        clear_btn.pack(side=RIGHT, padx=5)

        export_btn = ttk.Button(
            control_bar,
            text="导出日志",
            command=self.export_log,
            bootstyle="primary-outline"
        )
        export_btn.pack(side=RIGHT)

        # 日志文本区域
        self.log_text = ScrolledText(
            log_container,
            wrap=tk.WORD,
            height=25,
            autohide=True,
            bootstyle="dark"
        )
        self.log_text.pack(fill=BOTH, expand=YES)

    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.log(f"❌ 加载配置失败: {e}")

        # 返回默认配置
        return {
            "account1": {"name": "账户1", "api_key": "", "api_secret": ""},
            "account2": {"name": "账户2", "api_key": "", "api_secret": ""},
            "trading": {
                "symbol": "ETHUSDT",
                "leverage": 20,  # 与实际配置文件保持一致
                "usdt_amount": 300,
                "wait_seconds": 60,  # 与实际配置文件保持一致
                "max_trades": 10,  # 与实际配置文件保持一致
                "order_type": "MARKET",
                "position_side": "BOTH"
            }
        }

    def save_config(self):
        """保存配置"""
        try:
            # 更新账户配置
            for i, entries in enumerate([self.account1_entries, self.account2_entries], 1):
                account_key = f"account{i}"
                self.config[account_key]["name"] = entries["name"].get()
                self.config[account_key]["api_key"] = entries["api_key"].get()
                self.config[account_key]["api_secret"] = entries["api_secret"].get()

            # 更新交易配置
            self.config["trading"]["symbol"] = self.trading_entries["symbol"].get()
            self.config["trading"]["usdt_amount"] = float(self.trading_entries["usdt_amount"].get())
            self.config["trading"]["leverage"] = int(self.trading_entries["leverage"].get())
            self.config["trading"]["wait_seconds"] = int(self.trading_entries["wait_seconds"].get())
            self.config["trading"]["max_trades"] = int(self.trading_entries["max_trades"].get())

            # 保存到文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)

            # 立即更新内存中的统计数据
            self.stats.update({
                "symbol": self.config["trading"]["symbol"],
                "leverage": self.config["trading"]["leverage"],
                "wait_seconds": self.config["trading"]["wait_seconds"]
            })

            self.log("✅ 配置已保存并生效")
            self.show_toast("配置保存成功，新参数已生效", "success")
        except Exception as e:
            self.log(f"❌ 保存配置失败: {e}")
            self.show_toast(f"保存失败: {e}", "danger")

    def reset_config(self):
        """重置配置"""
        result = messagebox.askyesno("确认", "确定要重置所有配置吗？")
        if result:
            # 重置为默认值
            for entry in self.account1_entries.values():
                entry.delete(0, tk.END)
            for entry in self.account2_entries.values():
                entry.delete(0, tk.END)

            # 设置默认交易参数
            self.trading_entries["symbol"].set("ETHUSDT")
            self.trading_entries["usdt_amount"].delete(0, tk.END)
            self.trading_entries["usdt_amount"].insert(0, "300")
            self.trading_entries["leverage"].delete(0, tk.END)
            self.trading_entries["leverage"].insert(0, "100")
            self.trading_entries["wait_seconds"].delete(0, tk.END)
            self.trading_entries["wait_seconds"].insert(0, "300")
            self.trading_entries["max_trades"].delete(0, tk.END)
            self.trading_entries["max_trades"].insert(0, "10")

            self.show_toast("配置已重置", "warning")

    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        self.dashboard_log.delete(1.0, tk.END)
        self.show_toast("日志已清空", "info")

    def export_log(self):
        """导出日志"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trading_log_{timestamp}.txt"

            with open(filename, 'w', encoding='utf-8') as f:
                content = self.log_text.get(1.0, tk.END)
                f.write(content)

            self.show_toast(f"日志已导出到 {filename}", "success")
        except Exception as e:
            self.show_toast(f"导出失败: {e}", "danger")

    def show_toast(self, message, style="info"):
        """显示Toast通知"""
        toast = ToastNotification(
            title="系统通知",
            message=message,
            duration=3000,
            bootstyle=style
        )
        toast.show_toast()

    def log(self, message):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        self.log_queue.put(log_message)

    def update_display(self):
        """更新显示"""
        # 处理日志队列
        try:
            while not self.log_queue.empty():
                message = self.log_queue.get_nowait()
                # 写入主日志
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.see(tk.END)
                # 写入仪表板日志
                self.dashboard_log.insert(tk.END, message + "\n")
                self.dashboard_log.see(tk.END)
        except:
            pass

        # 更新统计表盘
        if hasattr(self, 'stat_meters'):
            # 更新价格
            price = self.stats.get('current_price', 0)
            if price > 0:
                # 价格范围 3000-5000
                price_percent = min((price - 3000) / 2000 * 100, 100) if price > 3000 else 0
                self.stat_meters["price"].configure(amountused=price_percent)
                self.stat_meters["price"].configure(amountused=price_percent,
                                                   amounttotal=100,
                                                   subtext=f"当前价格 {price:.2f} USDT")

            # 更新盈亏（包括未实现盈亏）
            realized_pnl = sum(
                self.account_status[acc].get("current_balance", 0) -
                self.account_status[acc].get("initial_balance", 0)
                for acc in ["账户1", "账户2"]
                if self.account_status[acc].get("initial_balance", 0) > 0
            )

            unrealized_pnl = sum(
                self.account_status[acc].get("unrealized_pnl", 0)
                for acc in ["账户1", "账户2"]
            )

            total_pnl = realized_pnl + unrealized_pnl
            pnl_percent = min(abs(total_pnl) / 100 * 100, 100) if total_pnl != 0 else 0
            pnl_style = "success" if total_pnl >= 0 else "danger"
            self.stat_meters["pnl"].configure(amountused=pnl_percent,
                                             bootstyle=pnl_style,
                                             subtext=f"总盈亏 {total_pnl:.2f} USDT")

            # 更新交易次数
            trades = self.stats.get("trade_count", 0)
            max_trades = self.config.get("trading", {}).get("max_trades", 100)
            trades_percent = min(trades / max_trades * 100, 100)
            self.stat_meters["trades"].configure(amountused=trades_percent,
                                                textright=f"/{max_trades}",
                                                subtext=f"已完成 {trades} 次交易")

            # 更新持仓时间
            if self.stats.get("position_open_time"):
                actual_hold_time = int(time.time() - self.stats["position_open_time"])
                wait_seconds = self.stats.get('wait_seconds', 30)
                time_percent = min(actual_hold_time / wait_seconds * 100, 100)
                self.stat_meters["time"].configure(amountused=time_percent,
                                                  textright=f"/{wait_seconds}s",
                                                  subtext=f"已持仓 {actual_hold_time} 秒")
            else:
                self.stat_meters["time"].configure(amountused=0,
                                                  subtext="未持仓")

        # 更新市场信息
        if hasattr(self, 'market_labels'):
            self.market_labels["交易对"].config(text=self.stats.get("symbol", "ETHUSDT"))
            self.market_labels["当前杠杆"].config(text=f"{self.stats.get('leverage', 100)}x")
            self.market_labels["资金费率"].config(text=f"{self.stats.get('current_funding_rate', 0) * 100:.4f}%")
            self.market_labels["总交易量"].config(text=f"{self.stats.get('total_volume_usdt', 0):.2f} USDT")

            # 更新账户余额（增加精度）
            for acc in ["账户1", "账户2"]:
                balance = self.account_status[acc].get("current_balance", 0)
                if balance > 0:
                    self.market_labels[f"{acc}余额"].config(text=f"{balance:.6f} USDT")
                else:
                    self.market_labels[f"{acc}余额"].config(text="获取中...")

            # 更新时间
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.market_labels["当前时间"].config(text=current_time)

            # 上次交易时间
            last_trade = self.stats.get("last_trade_time", "-")
            self.market_labels["上次交易"].config(text=last_trade if last_trade else "-")

            # 初始总资产（增加精度和判断）
            initial_total = sum(
                self.account_status[acc].get("initial_balance", 0)
                for acc in ["账户1", "账户2"]
            )
            if initial_total > 0:
                self.market_labels["初始总资产"].config(text=f"{initial_total:.6f} USDT")
            else:
                self.market_labels["初始总资产"].config(text="未记录")

        # 定时调用
        self.root.after(1000, self.update_display)

    def update_account_status(self, account_name, status):
        """更新账户状态"""
        if account_name in self.account_status:
            self.account_status[account_name].update(status)

            # 更新表格
            position_side = status.get("position_side", "NONE")

            # 设置方向显示
            if position_side == "LONG":
                side_text = "多"
                tag = "long"
            elif position_side == "SHORT":
                side_text = "空"
                tag = "short"
            else:
                side_text = "-"
                tag = None

            values = (
                account_name,
                side_text,
                f"{abs(status.get('quantity', 0)):.3f}",
                f"{status.get('entry_price', 0):.2f}",
                f"{status.get('unrealized_pnl', 0):.2f}",
                f"{status.get('margin', 0):.2f}",
                f"{status.get('liquidation_price', 0):.2f}"
            )

            self.account_tree.item(account_name, values=values)
            if tag:
                self.account_tree.item(account_name, tags=(tag,))

    def start_trading(self):
        """启动交易"""
        if self.trading_active:
            return

        # 强制重新加载配置文件，确保使用最新参数
        print("🔄 重新加载配置文件...")
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            print(f"✅ 配置已更新: {self.config['trading']}")
        except Exception as e:
            self.log(f"❌ 加载配置失败: {e}")
            return

        # 检查API配置
        if not self.config.get("account1", {}).get("api_key"):
            self.show_toast("请先配置账户1的API密钥", "warning")
            self.notebook.select(1)  # 切换到配置页面
            return
        if not self.config.get("account2", {}).get("api_key"):
            self.show_toast("请先配置账户2的API密钥", "warning")
            self.notebook.select(1)  # 切换到配置页面
            return

        self.trading_active = True
        self.start_btn.configure(state=DISABLED)
        self.stop_btn.configure(state=NORMAL)

        self.log("🚀 正在启动交易系统...")
        self.log(f"📊 交易参数: 杠杆{self.config['trading']['leverage']}x, 金额{self.config['trading']['usdt_amount']}USDT, 持仓{self.config['trading']['wait_seconds']}秒")
        self.show_toast("交易系统启动中...", "info")

        # 初始化API
        try:
            self.account1_api = AsterDexAPI(
                self.config["account1"]["api_key"],
                self.config["account1"]["api_secret"]
            )
            self.account2_api = AsterDexAPI(
                self.config["account2"]["api_key"],
                self.config["account2"]["api_secret"]
            )

            # 立即获取并记录初始余额
            self.log("📊 获取账户初始余额...")
            balance1 = self.account1_api.get_account_balance()
            balance2 = self.account2_api.get_account_balance()

            # 记录初始余额
            self.account_status["账户1"]["initial_balance"] = balance1
            self.account_status["账户1"]["current_balance"] = balance1
            self.account_status["账户2"]["initial_balance"] = balance2
            self.account_status["账户2"]["current_balance"] = balance2

            self.log(f"✅ 账户1初始余额: {balance1:.6f} USDT")
            self.log(f"✅ 账户2初始余额: {balance2:.6f} USDT")
            self.log(f"✅ 初始总资产: {balance1 + balance2:.6f} USDT")

            # 更新交易参数（使用最新配置）
            self.stats.update({
                "symbol": self.config["trading"]["symbol"],
                "leverage": self.config["trading"]["leverage"],
                "wait_seconds": self.config["trading"]["wait_seconds"]
            })

            self.log("✅ API初始化成功")
            self.show_toast("交易系统已启动", "success")
        except Exception as e:
            self.log(f"❌ API初始化失败: {e}")
            self.show_toast(f"启动失败: {e}", "danger")
            self.stop_trading()
            return

        # 启动交易线程
        self.trading_thread = threading.Thread(target=self.trading_loop, daemon=True)
        self.trading_thread.start()

        # 启动状态更新线程
        self.update_thread = threading.Thread(target=self.update_status_loop, daemon=True)
        self.update_thread.start()

    def stop_trading(self):
        """停止交易"""
        if not self.trading_active:
            return

        self.trading_active = False
        self.start_btn.configure(state=NORMAL)
        self.stop_btn.configure(state=DISABLED)

        self.log("⏹ 正在停止交易系统...")
        self.show_toast("正在停止交易...", "warning")

        # 清理持仓
        if self.account1_api and self.account2_api:
            self.cleanup_positions()

        self.show_toast("交易系统已停止", "info")

    def cleanup_positions(self):
        """清理所有持仓"""
        symbol = self.config["trading"]["symbol"]

        try:
            for i, api in enumerate([self.account1_api, self.account2_api], 1):
                positions = api.get_position_info(symbol)
                if positions and isinstance(positions, list) and len(positions) > 0:
                    pos_amt = float(positions[0].get("positionAmt", 0))
                    if pos_amt != 0:
                        side = "SELL" if pos_amt > 0 else "BUY"
                        result = api.place_order(
                            symbol=symbol,
                            side=side,
                            order_type="MARKET",
                            quantity=abs(pos_amt),
                            position_side="BOTH"
                        )
                        if result:
                            self.log(f"✅ 账户{i}已平仓")

            self.log("✅ 所有持仓已清理")
        except Exception as e:
            self.log(f"❌ 清理持仓失败: {e}")

    def trading_loop(self):
        """交易主循环"""
        # 使用start_trading时加载的配置
        symbol = self.config.get("trading", {}).get("symbol", "ETHUSDT")
        leverage = self.config.get("trading", {}).get("leverage", 100)
        usdt_amount = self.config.get("trading", {}).get("usdt_amount", 300)
        wait_seconds = self.config.get("trading", {}).get("wait_seconds", 300)
        max_trades = self.config.get("trading", {}).get("max_trades", 10)

        self.log(f"📊 使用配置: {symbol} {leverage}x {usdt_amount}USDT {wait_seconds}秒")

        # 设置杠杆
        try:
            self.account1_api.set_leverage(symbol, leverage)
            self.account2_api.set_leverage(symbol, leverage)
            self.log(f"✅ 已设置杠杆为 {leverage}x")
        except Exception as e:
            self.log(f"❌ 设置杠杆失败: {e}")

        while self.trading_active and self.stats["trade_count"] < max_trades:
            try:
                self.log(f"🔄 开始第{self.stats['trade_count']+1}轮检查...")

                # 获取当前价格和资金费率
                self.log(f"📊 获取当前价格...")
                current_price = self.account1_api.get_current_price(symbol)
                self.log(f"📊 当前价格: {current_price:.2f} USDT")

                self.log(f"📊 获取资金费率...")
                funding_rate = self.account1_api.get_funding_rate(symbol)
                self.log(f"📊 资金费率: {funding_rate*100:.6f}%")

                # 检查价格是否有效，避免除零错误
                if current_price <= 0:
                    self.log(f"⚠️ 无法获取有效价格，跳过本轮")
                    time.sleep(5)
                    continue

                self.stats["current_price"] = current_price
                self.stats["current_funding_rate"] = funding_rate

                # 检查两个账户是否都有持仓（避免单边持仓）
                self.log(f"🔍 检查持仓状态...")
                positions1 = self.account1_api.get_position_info(symbol)
                positions2 = self.account2_api.get_position_info(symbol)
                self.log(f"🔍 持仓检查完成")

                has_position1 = False
                has_position2 = False
                pos_amt1 = 0
                pos_amt2 = 0

                if positions1 and isinstance(positions1, list) and len(positions1) > 0:
                    pos_amt1 = float(positions1[0].get("positionAmt", 0))
                    has_position1 = (pos_amt1 != 0)

                if positions2 and isinstance(positions2, list) and len(positions2) > 0:
                    pos_amt2 = float(positions2[0].get("positionAmt", 0))
                    has_position2 = (pos_amt2 != 0)

                # 如果只有一边有持仓，先平掉（异常情况处理）
                if has_position1 != has_position2:
                    self.log(f"⚠️ 检测到单边持仓，正在修复...")
                    if has_position1:
                        side = "SELL" if pos_amt1 > 0 else "BUY"
                        self.account1_api.place_order(symbol, side, "MARKET", abs(pos_amt1), "BOTH")
                        self.log(f"✅ 账户1单边持仓已平仓")
                    if has_position2:
                        side = "SELL" if pos_amt2 > 0 else "BUY"
                        self.account2_api.place_order(symbol, side, "MARKET", abs(pos_amt2), "BOTH")
                        self.log(f"✅ 账户2单边持仓已平仓")
                    time.sleep(2)
                    continue

                # 现在两边要么都有持仓，要么都没有
                has_position = has_position1 and has_position2

                if not has_position:
                    # 再次确认没有持仓（避免累积）
                    if pos_amt1 != 0 or pos_amt2 != 0:
                        self.log(f"⚠️ 检测到残留持仓，跳过本轮")
                        time.sleep(5)
                        continue

                    # 计算交易数量
                    quantity = self.account1_api.calculate_quantity_from_usdt(
                        symbol, usdt_amount, leverage
                    )

                    # 检查名义价值
                    notional_value = quantity * current_price
                    if notional_value < 5:
                        self.log(f"⚠️ 名义价值 {notional_value:.2f} USDT 小于最小值 5 USDT，跳过开仓")
                        time.sleep(5)
                        continue

                    # 根据资金费率决定开仓方向
                    if funding_rate > 0:
                        self.log(f"📊 资金费率: {funding_rate*100:.4f}% (正值)")
                        self.log(f"[账户1] 做空 {quantity:.3f} {symbol} @ {current_price:.2f}")
                        result1 = self.account1_api.place_order(
                            symbol=symbol,
                            side="SELL",
                            order_type="MARKET",
                            quantity=quantity,
                            position_side="BOTH"
                        )

                        self.log(f"[账户2] 做多 {quantity:.3f} {symbol} @ {current_price:.2f}")
                        result2 = self.account2_api.place_order(
                            symbol=symbol,
                            side="BUY",
                            order_type="MARKET",
                            quantity=quantity,
                            position_side="BOTH"
                        )

                        if result1 and result2:
                            self.stats["trade_count"] += 1
                            self.stats["total_volume_usdt"] += quantity * current_price * 2
                            self.stats["position_open_time"] = time.time()
                            self.stats["last_trade_time"] = datetime.now().strftime("%H:%M:%S")

                            # 立即更新持仓状态（资金费率>0时，账户1做空，账户2做多）
                            self.account_status["账户1"]["quantity"] = quantity
                            self.account_status["账户1"]["position_side"] = "SHORT"
                            self.account_status["账户1"]["entry_price"] = current_price
                            self.account_status["账户2"]["quantity"] = quantity
                            self.account_status["账户2"]["position_side"] = "LONG"
                            self.account_status["账户2"]["entry_price"] = current_price

                            self.log("✅ 对冲交易成功建立")
                            self.show_toast(f"第{self.stats['trade_count']}次交易成功", "success")
                    else:
                        self.log(f"📊 资金费率: {funding_rate*100:.4f}% (负值)")
                        self.log(f"[账户1] 做多 {quantity:.3f} {symbol} @ {current_price:.2f}")
                        result1 = self.account1_api.place_order(
                            symbol=symbol,
                            side="BUY",
                            order_type="MARKET",
                            quantity=quantity,
                            position_side="BOTH"
                        )

                        self.log(f"[账户2] 做空 {quantity:.3f} {symbol} @ {current_price:.2f}")
                        result2 = self.account2_api.place_order(
                            symbol=symbol,
                            side="SELL",
                            order_type="MARKET",
                            quantity=quantity,
                            position_side="BOTH"
                        )

                        if result1 and result2:
                            self.stats["trade_count"] += 1
                            self.stats["total_volume_usdt"] += quantity * current_price * 2
                            self.stats["position_open_time"] = time.time()
                            self.stats["last_trade_time"] = datetime.now().strftime("%H:%M:%S")

                            # 立即更新持仓状态（资金费率<0时，账户1做多，账户2做空）
                            self.account_status["账户1"]["quantity"] = quantity
                            self.account_status["账户1"]["position_side"] = "LONG"
                            self.account_status["账户1"]["entry_price"] = current_price
                            self.account_status["账户2"]["quantity"] = quantity
                            self.account_status["账户2"]["position_side"] = "SHORT"
                            self.account_status["账户2"]["entry_price"] = current_price

                            self.log("✅ 对冲交易成功建立")
                            self.show_toast(f"第{self.stats['trade_count']}次交易成功", "success")
                else:
                    # 检查是否需要平仓
                    if self.stats.get("position_open_time"):
                        hold_time = int(time.time() - self.stats["position_open_time"])
                        if hold_time >= wait_seconds:
                            self.log(f"⏱ 持仓时间已达到 {hold_time} 秒，开始平仓")

                            # 使用各自的实际持仓量平仓，避免累积错误
                            if pos_amt1 != 0 and pos_amt2 != 0:
                                # 账户1平仓
                                side1 = "SELL" if pos_amt1 > 0 else "BUY"
                                self.log(f"[账户1] 平仓 {abs(pos_amt1):.3f} {symbol}")
                                result1 = self.account1_api.place_order(
                                    symbol=symbol,
                                    side=side1,
                                    order_type="MARKET",
                                    quantity=abs(pos_amt1),
                                    position_side="BOTH"
                                )

                                # 账户2平仓
                                side2 = "SELL" if pos_amt2 > 0 else "BUY"
                                self.log(f"[账户2] 平仓 {abs(pos_amt2):.3f} {symbol}")
                                result2 = self.account2_api.place_order(
                                    symbol=symbol,
                                    side=side2,
                                    order_type="MARKET",
                                    quantity=abs(pos_amt2),
                                    position_side="BOTH"
                                )

                                if result1 and result2:
                                    self.log("✅ 平仓成功")
                                    self.stats["position_open_time"] = None

                                    # 立即清空持仓状态
                                    for acc in ["账户1", "账户2"]:
                                        self.account_status[acc]["quantity"] = 0
                                        self.account_status[acc]["position_side"] = "NONE"
                                        self.account_status[acc]["entry_price"] = 0
                                        self.account_status[acc]["unrealized_pnl"] = 0

                                    # 等待一下确保平仓完成
                                    time.sleep(2)
                                else:
                                    self.log(f"⚠️ 平仓可能未完全成功，将重试")
                            else:
                                self.log(f"⚠️ 持仓数据异常，跳过平仓")

                time.sleep(1)

            except Exception as e:
                self.log(f"❌ 交易循环错误: {e}")
                import traceback
                self.log(f"❌ 错误详情: {traceback.format_exc()}")
                time.sleep(5)

        if self.stats["trade_count"] >= max_trades:
            self.log(f"📊 已达到最大交易次数 {max_trades}")
            self.show_toast(f"已完成{max_trades}次交易", "info")
            self.stop_trading()

    def update_status_loop(self):
        """状态更新循环"""
        symbol = self.config["trading"]["symbol"]
        last_balance_update = 0  # 上次余额更新时间
        balance_update_interval = 5  # 余额更新间隔（秒）

        while self.trading_active:
            try:
                current_time = time.time()

                for i, api in enumerate([self.account1_api, self.account2_api], 1):
                    account_name = f"账户{i}"

                    # 余额更新（每5秒一次）
                    balance = self.account_status[account_name].get("current_balance", 0)
                    if current_time - last_balance_update >= balance_update_interval:
                        new_balance = api.get_account_balance()
                        if new_balance > 0:
                            balance = new_balance
                        elif balance == 0:
                            # 如果缓存也是0，尝试多获取一次
                            time.sleep(0.5)
                            new_balance = api.get_account_balance()
                            if new_balance > 0:
                                balance = new_balance

                    # 持仓信息（每秒更新）
                    positions = api.get_position_info(symbol)

                    status = {
                        "current_balance": balance,
                        "last_update": datetime.now().strftime("%H:%M:%S")
                    }

                    if positions and isinstance(positions, list) and len(positions) > 0:
                        pos = positions[0]
                        pos_amt = float(pos.get("positionAmt", 0))

                        status.update({
                            "position_side": "LONG" if pos_amt > 0 else "SHORT" if pos_amt < 0 else "NONE",
                            "quantity": abs(pos_amt),
                            "entry_price": float(pos.get("entryPrice", 0)),
                            "unrealized_pnl": float(pos.get("unRealizedProfit", 0)),
                            "margin": api.calculate_margin(pos) if pos_amt != 0 else 0,
                            "liquidation_price": float(pos.get("liquidationPrice", 0))
                        })
                    else:
                        status.update({
                            "position_side": "NONE",
                            "quantity": 0,
                            "entry_price": 0,
                            "unrealized_pnl": 0,
                            "margin": 0,
                            "liquidation_price": 0
                        })

                    # 不再在这里更新initial_balance，已在start_trading时设置

                    self.update_account_status(account_name, status)

                # 更新余额更新时间
                if current_time - last_balance_update >= balance_update_interval:
                    last_balance_update = current_time

                time.sleep(1)

            except Exception as e:
                pass

    def on_closing(self):
        """窗口关闭处理"""
        if self.trading_active:
            result = messagebox.askyesno("确认", "交易正在进行中，是否停止交易并退出？")
            if result:
                self.stop_trading()
                time.sleep(2)
                self.root.destroy()
        else:
            self.root.destroy()

    def run(self):
        """运行GUI"""
        self.root.mainloop()

def main():
    try:
        app = BootstrapTradingGUI()
        app.run()
    except Exception as e:
        print(f"程序启动失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
