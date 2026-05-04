"""
飞宇网吧收银交班管理系统
功能：记录商品初始数量、售出操作、自动计算剩余数量和销售金额、包夜费用计算
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import sys
import ctypes
from datetime import datetime

# Windows DPI 适配，避免界面模糊
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


def _get_app_dir():
    """获取程序所在目录（兼容 PyInstaller --onefile 打包）"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


APP_DIR = _get_app_dir()

# ============ 全局样式常量 ============
FONT_FAMILY = "Microsoft YaHei UI"
BG_MAIN = "#EEF1F5"       # 主背景
BG_CARD = "#FFFFFF"        # 卡片背景
BG_HEADER = "#34495E"      # 深色顶栏
BG_TOTAL = "#2C3E50"       # 总计栏
COLOR_TEXT = "#2D3436"     # 主文字
COLOR_MUTED = "#95A5A6"    # 次要文字
COLOR_SUCCESS = "#00B894"  # 绿色/成功
COLOR_DANGER = "#E17055"   # 红色/警告
COLOR_PRIMARY = "#0984E3"  # 蓝色/主色
COLOR_ACCENT = "#6C5CE7"   # 紫色/强调
COLOR_GOLD = "#FDCB6E"     # 金色

# ============ 商品配置 ============
# 格式：(商品名称, 单价)  名称作为唯一标识
CATEGORIES = {
    "饮料": [("2元", 2), ("3元", 3), ("4元", 4), ("5元", 5), ("6元", 6)],
    "小零食": [("1元", 1), ("2元", 2), ("3元", 3), ("4元", 4), ("5元", 5),
              ("6元", 6), ("7元", 7), ("8元", 8), ("9元", 9), ("10元", 10),
              ("30元", 30), ("50元", 50), ("100元", 100)],
    "香烟": [("17元", 17), ("24元", 24), ("30元", 30), ("60元", 60), ("100元", 100)],
    "自制饮品": [("冰杯", 2), ("咖啡", 5), ("泡茶", 5), ("果汁", 6), ("可乐", 6), ("奶茶", 7)],
}

CATEGORY_COLORS = {
    "饮料": "#0984E3",
    "小零食": "#E17055",
    "香烟": "#6C5CE7",
    "自制饮品": "#00B894",
}

DATA_FILE = "cashier_data.json"

# 分类售出按钮样式映射（由 _configure_styles 填充）
CATEGORY_SELL_STYLES = {}

# ============ 包夜计算器配置 ============
OVERNIGHT_RATES = [
    ("临时卡", 12, 40),
    ("普通会员", 9, 30),
    ("黄金会员", 8.6, 30),
    ("白金会员", 7.7, 30),
    ("钻石会员", 6.8, 30),
    ("金钻会员", 5.9, 30),
]
OVERNIGHT_START = 23
OVERNIGHT_END = 8


def _configure_styles():
    """配置全局 ttk 主题样式"""
    style = ttk.Style()
    style.theme_use("clam")

    # Notebook 标签页样式
    style.configure("TNotebook", background=BG_MAIN, borderwidth=0)
    style.configure("TNotebook.Tab",
                    font=(FONT_FAMILY, 11, "bold"),
                    padding=[18, 8],
                    background="#DFE6E9",
                    foreground=COLOR_TEXT)
    style.map("TNotebook.Tab",
              background=[("selected", BG_CARD)],
              foreground=[("selected", COLOR_PRIMARY)],
              expand=[("selected", [0, 2, 0, 0])])

    # Treeview 样式
    style.configure("Treeview",
                    font=(FONT_FAMILY, 10),
                    rowheight=30,
                    background=BG_CARD,
                    fieldbackground=BG_CARD,
                    foreground=COLOR_TEXT)
    style.configure("Treeview.Heading",
                    font=(FONT_FAMILY, 10, "bold"),
                    background="#DFE6E9",
                    foreground=COLOR_TEXT)
    style.map("Treeview",
              background=[("selected", "#D6EAF8")],
              foreground=[("selected", COLOR_TEXT)])

    # Scrollbar
    style.configure("Vertical.TScrollbar", gripcount=0,
                    background="#DFE6E9", troughcolor=BG_MAIN)

    # ---- 自定义按钮样式（clam 主题下可正确显示前景/背景色）----
    _btn_defs = [
        ("Green.TButton",  COLOR_SUCCESS, "#00A381", (FONT_FAMILY, 10, "bold"), [16, 6]),
        ("Red.TButton",    COLOR_DANGER,  "#D35400", (FONT_FAMILY, 10, "bold"), [16, 6]),
        ("Blue.TButton",   COLOR_PRIMARY, "#0767B2", (FONT_FAMILY, 10, "bold"), [16, 6]),
        ("Gray.TButton",   "#B2BEC3",     "#7F8C8D", (FONT_FAMILY, 9),          [6, 3]),
        ("Orange.TButton", "#F39C12",     "#D68910", (FONT_FAMILY, 9),          [6, 3]),
        ("Gold.TButton",   COLOR_GOLD,    COLOR_GOLD, (FONT_FAMILY, 10, "bold"), [8, 3]),
        ("BlueSm.TButton", COLOR_PRIMARY, "#0767B2", (FONT_FAMILY, 9, "bold"),  [10, 3]),
        ("GreenLg.TButton", COLOR_SUCCESS, "#00A381", (FONT_FAMILY, 11, "bold"), [20, 8]),
    ]
    for sname, bg, abg, font_cfg, pad in _btn_defs:
        style.configure(sname,
                        font=font_cfg, foreground="white", background=bg,
                        borderwidth=1, padding=pad)
        style.map(sname,
                  foreground=[("disabled", "#999999"), ("active", "white")],
                  background=[("disabled", "#CCCCCC"), ("active", abg)])

    # 各商品分类的售出按钮样式
    for cat_name, color in CATEGORY_COLORS.items():
        sn = "Sell_%s.TButton" % id(cat_name)
        CATEGORY_SELL_STYLES[cat_name] = sn
        style.configure(sn,
                        font=(FONT_FAMILY, 10, "bold"), foreground="white",
                        background=color, borderwidth=1, padding=[8, 3])
        style.map(sn,
                  foreground=[("disabled", "#999999"), ("active", "white")],
                  background=[("disabled", "#CCCCCC"), ("active", "#1A1A2E")])


class CashierApp:
    def __init__(self, root):
        self.root = root
        self.root.title("飞宇网吧收银交班管理系统")
        self.root.geometry("1080x1080")
        self.root.minsize(1080, 900)
        self.root.configure(bg=BG_MAIN)

        _configure_styles()

        # 数据：self.data[cat][item_name] = {"initial": 0, "sold": 0, "price": price}
        self.data = {}
        for cat, items in CATEGORIES.items():
            self.data[cat] = {}
            for item_name, price in items:
                self.data[cat][item_name] = {"initial": 0, "sold": 0, "price": price}

        self.sell_log = []
        self.widgets = {}          # key: (cat, item_name)
        self.subtotal_labels = {}
        self.grand_total_var = tk.StringVar(value="0.00")
        self.grand_sold_count_var = tk.StringVar(value="0")
        self.mode = "setup"

        # 交班核算相关变量
        self.settle_reserve_var = tk.StringVar(value="500")
        self.settle_net_income_var = tk.StringVar(value="0")
        self.settle_goods_var = tk.StringVar(value="0.00")
        self.settle_wechat_var = tk.StringVar(value="0")
        self.settle_alipay_var = tk.StringVar(value="0")
        self.settle_actual_cash_var = tk.StringVar(value="0")
        self.settle_other_items = []  # [{"note": str, "amount": float}]
        self.settle_other_note_var = tk.StringVar(value="")
        self.settle_other_amount_var = tk.StringVar(value="")
        self.settle_other_total_var = tk.StringVar(value="0.00")
        self.settle_theory_var = tk.StringVar(value="--")
        self.settle_diff_var = tk.StringVar(value="--")
        self.settle_diff_status_var = tk.StringVar(value="")

        self._build_ui()
        self._load_data()

    # ==================== UI 构建 ====================
    def _build_ui(self):
        # --- 顶部标题栏 ---
        header = tk.Frame(self.root, bg=BG_HEADER, height=52)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(header, text="飞宇网吧收银交班管理系统",
                 font=(FONT_FAMILY, 16, "bold"),
                 fg="white", bg=BG_HEADER).pack(side=tk.LEFT, padx=24, pady=10)

        self.time_label = tk.Label(header, font=(FONT_FAMILY, 11),
                                   fg="#B2BEC3", bg=BG_HEADER)
        self.time_label.pack(side=tk.RIGHT, padx=24)
        self._update_time()

        # --- 操作栏 ---
        ctrl = tk.Frame(self.root, bg=BG_MAIN, pady=8)
        ctrl.pack(fill=tk.X, padx=16)

        self.start_btn = ttk.Button(
            ctrl, text=" 确认初始数量, 开始营业 ",
            style="Green.TButton", cursor="hand2",
            command=self._start_selling)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.reset_btn = ttk.Button(
            ctrl, text=" 重新设置 ",
            style="Red.TButton", cursor="hand2",
            command=self._reset_to_setup, state=tk.DISABLED)
        self.reset_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.export_btn = ttk.Button(
            ctrl, text=" 导出交班报表 ",
            style="Blue.TButton", cursor="hand2",
            command=self._export_report)
        self.export_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.status_var = tk.StringVar(
            value="[ 设置模式 ]  请填写各商品初始数量后点击\"确认初始数量\"")
        self.status_label = tk.Label(ctrl, textvariable=self.status_var,
                                     font=(FONT_FAMILY, 9),
                                     fg=COLOR_DANGER, bg=BG_MAIN)
        self.status_label.pack(side=tk.LEFT, padx=16)

        # --- 总计面板 ---
        total_bar = tk.Frame(self.root, bg=BG_TOTAL, pady=8)
        total_bar.pack(fill=tk.X, padx=16)

        tk.Label(total_bar, text="   总售出 :", font=(FONT_FAMILY, 12),
                 fg="#B2BEC3", bg=BG_TOTAL).pack(side=tk.LEFT)
        tk.Label(total_bar, textvariable=self.grand_sold_count_var,
                 font=(FONT_FAMILY, 16, "bold"),
                 fg=COLOR_GOLD, bg=BG_TOTAL).pack(side=tk.LEFT, padx=(4, 8))
        tk.Label(total_bar, text="件    |    销售总额 :",
                 font=(FONT_FAMILY, 12),
                 fg="#B2BEC3", bg=BG_TOTAL).pack(side=tk.LEFT)
        tk.Label(total_bar, textvariable=self.grand_total_var,
                 font=(FONT_FAMILY, 18, "bold"),
                 fg=COLOR_SUCCESS, bg=BG_TOTAL).pack(side=tk.LEFT, padx=(4, 4))
        tk.Label(total_bar, text="元",
                 font=(FONT_FAMILY, 12),
                 fg="#B2BEC3", bg=BG_TOTAL).pack(side=tk.LEFT)

        # --- Notebook 标签页 ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=(8, 16))

        for cat_name, items in CATEGORIES.items():
            tab = tk.Frame(self.notebook, bg=BG_CARD)
            self.notebook.add(tab, text=f"  {cat_name} ({len(items)}种)  ")
            self._build_category_tab(tab, cat_name, items)

        self._build_log_tab()
        self._build_settlement_tab()
        self._build_overnight_tab()

    # -------------------- 商品分类标签页 --------------------
    def _build_category_tab(self, parent, cat_name, items):
        color = CATEGORY_COLORS.get(cat_name, "#555")

        # 表头
        hdr = tk.Frame(parent, bg="#DFE6E9")
        hdr.pack(fill=tk.X, padx=12, pady=(12, 0))
        col_defs = [("商品名称", 12), ("初始数量", 10), ("售出数量", 10),
                    ("剩余数量", 10), ("销售金额", 13), ("操作", 24)]
        for i, (text, w) in enumerate(col_defs):
            tk.Label(hdr, text=text, font=(FONT_FAMILY, 10, "bold"),
                     width=w, bg="#DFE6E9", fg=COLOR_TEXT,
                     anchor=tk.CENTER).grid(row=0, column=i, padx=1, pady=6)

        # 商品行
        body = tk.Frame(parent, bg=BG_CARD)
        body.pack(fill=tk.BOTH, expand=True, padx=12)

        for idx, (item_name, price) in enumerate(items):
            bg = BG_CARD if idx % 2 == 0 else "#F8F9FA"

            display_text = item_name if item_name.endswith("元") else f"{item_name} {price}元"
            tk.Label(body, text=display_text,
                     font=(FONT_FAMILY, 11, "bold"), width=12,
                     bg=bg, fg=color, anchor=tk.CENTER).grid(
                row=idx, column=0, padx=1, pady=1, sticky="ew")

            init_var = tk.StringVar(value="0")
            init_entry = tk.Entry(body, textvariable=init_var,
                                  font=(FONT_FAMILY, 11), width=7,
                                  justify=tk.CENTER, relief=tk.SOLID, bd=1)
            init_entry.grid(row=idx, column=1, padx=1, pady=1)

            sold_label = tk.Label(body, text="0",
                                  font=(FONT_FAMILY, 11, "bold"), width=10,
                                  bg=bg, fg=COLOR_DANGER, anchor=tk.CENTER)
            sold_label.grid(row=idx, column=2, padx=1, pady=1, sticky="ew")

            remain_label = tk.Label(body, text="0",
                                    font=(FONT_FAMILY, 11), width=10,
                                    bg=bg, fg=COLOR_TEXT, anchor=tk.CENTER)
            remain_label.grid(row=idx, column=3, padx=1, pady=1, sticky="ew")

            amount_label = tk.Label(body, text="0.00",
                                    font=(FONT_FAMILY, 11), width=13,
                                    bg=bg, fg=COLOR_SUCCESS, anchor=tk.CENTER)
            amount_label.grid(row=idx, column=4, padx=1, pady=1, sticky="ew")

            btn_cell = tk.Frame(body, bg=bg)
            btn_cell.grid(row=idx, column=5, padx=1, pady=1)

            sell_style = CATEGORY_SELL_STYLES.get(cat_name, "Green.TButton")
            sell_btn = ttk.Button(
                btn_cell, text="  售出 +1  ",
                style=sell_style, cursor="hand2",
                command=lambda c=cat_name, n=item_name: self._sell_one(c, n))
            sell_btn.pack(side=tk.LEFT, padx=4)

            undo_btn = ttk.Button(
                btn_cell, text=" 撤销 -1 ",
                style="Gray.TButton", cursor="hand2",
                command=lambda c=cat_name, n=item_name: self._undo_one(c, n))
            undo_btn.pack(side=tk.LEFT, padx=2)

            restock_btn = ttk.Button(
                btn_cell, text=" 补货 ",
                style="Orange.TButton", cursor="hand2",
                command=lambda c=cat_name, n=item_name: self._restock(c, n))
            restock_btn.pack(side=tk.LEFT, padx=2)

            sell_btn.config(state=tk.DISABLED)
            undo_btn.config(state=tk.DISABLED)
            restock_btn.config(state=tk.DISABLED)

            self.widgets[(cat_name, item_name)] = {
                "init_var": init_var, "init_entry": init_entry,
                "sold_label": sold_label, "remain_label": remain_label,
                "amount_label": amount_label,
                "sell_btn": sell_btn, "undo_btn": undo_btn,
                "restock_btn": restock_btn,
            }

        # 小计
        sub = tk.Frame(parent, bg="#FFF3E0", pady=8)
        sub.pack(fill=tk.X, padx=12, pady=(6, 12))

        tk.Label(sub, text=f"  {cat_name} 小计 :",
                 font=(FONT_FAMILY, 12, "bold"),
                 bg="#FFF3E0", fg=color).pack(side=tk.LEFT, padx=8)
        sub_count = tk.Label(sub, text="售出 0 件",
                             font=(FONT_FAMILY, 11), bg="#FFF3E0", fg=COLOR_TEXT)
        sub_count.pack(side=tk.LEFT, padx=16)
        sub_amount = tk.Label(sub, text="金额 : 0.00 元",
                              font=(FONT_FAMILY, 12, "bold"),
                              bg="#FFF3E0", fg=COLOR_DANGER)
        sub_amount.pack(side=tk.LEFT, padx=16)
        self.subtotal_labels[cat_name] = {"count": sub_count, "amount": sub_amount}

    # -------------------- 售出记录标签页 --------------------
    def _build_log_tab(self):
        log_tab = tk.Frame(self.notebook, bg=BG_CARD)
        self.notebook.add(log_tab, text="  售出记录  ")

        toolbar = tk.Frame(log_tab, bg=BG_CARD, pady=8)
        toolbar.pack(fill=tk.X, padx=12)
        tk.Label(toolbar, text="所有售出 / 撤销操作按时间顺序记录（最新在最上方）",
                 font=(FONT_FAMILY, 10), fg=COLOR_MUTED,
                 bg=BG_CARD).pack(side=tk.LEFT)
        self.log_count_var = tk.StringVar(value="共 0 条记录")
        tk.Label(toolbar, textvariable=self.log_count_var,
                 font=(FONT_FAMILY, 10, "bold"), fg=COLOR_TEXT,
                 bg=BG_CARD).pack(side=tk.RIGHT)

        tree_frame = tk.Frame(log_tab, bg=BG_CARD)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        columns = ("seq", "time", "action", "category", "item", "price", "running_total")
        self.log_tree = ttk.Treeview(tree_frame, columns=columns,
                                     show="headings", height=20)
        self.log_tree.heading("seq", text="序号")
        self.log_tree.heading("time", text="时间")
        self.log_tree.heading("action", text="操作")
        self.log_tree.heading("category", text="商品类别")
        self.log_tree.heading("item", text="商品名称")
        self.log_tree.heading("price", text="单价(元)")
        self.log_tree.heading("running_total", text="累计销售额(元)")

        self.log_tree.column("seq", width=50, anchor=tk.CENTER)
        self.log_tree.column("time", width=150, anchor=tk.CENTER)
        self.log_tree.column("action", width=60, anchor=tk.CENTER)
        self.log_tree.column("category", width=90, anchor=tk.CENTER)
        self.log_tree.column("item", width=90, anchor=tk.CENTER)
        self.log_tree.column("price", width=80, anchor=tk.CENTER)
        self.log_tree.column("running_total", width=120, anchor=tk.CENTER)

        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                           command=self.log_tree.yview)
        self.log_tree.configure(yscrollcommand=sb.set)
        self.log_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_tree.tag_configure("sell", foreground=COLOR_SUCCESS)
        self.log_tree.tag_configure("undo", foreground=COLOR_DANGER)

    # -------------------- 交班核算标签页 --------------------
    def _build_settlement_tab(self):
        tab = tk.Frame(self.notebook, bg=BG_CARD)
        self.notebook.add(tab, text="  交班核算  ")

        # 标题栏
        title_bar = tk.Frame(tab, bg=BG_HEADER, height=44)
        title_bar.pack(fill=tk.X, padx=12, pady=(12, 0))
        title_bar.pack_propagate(False)
        tk.Label(title_bar, text="交班核算",
                 font=(FONT_FAMILY, 14, "bold"),
                 fg="white", bg=BG_HEADER).pack(side=tk.LEFT, padx=16)

        # 左右布局
        body = tk.Frame(tab, bg=BG_CARD)
        body.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        left = tk.Frame(body, bg=BG_CARD)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        right = tk.Frame(body, bg=BG_CARD)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))

        # ===== 左侧上方: 基础金额 =====
        base_f = tk.LabelFrame(left, text="  基础金额  ",
                                font=(FONT_FAMILY, 11, "bold"),
                                fg=COLOR_PRIMARY, bg=BG_CARD, padx=14, pady=10)
        base_f.pack(fill=tk.X, pady=(0, 8))

        entry_font = (FONT_FAMILY, 12)
        label_font = (FONT_FAMILY, 11)

        fields = [
            ("备用金 :", self.settle_reserve_var),
            ("本班网费收入 :", self.settle_net_income_var),
            ("商品销售金额 :", self.settle_goods_var),
            ("微信收款 :", self.settle_wechat_var),
            ("支付宝收款 :", self.settle_alipay_var),
            ("实际现金总额 :", self.settle_actual_cash_var),
        ]
        for i, (label_text, var) in enumerate(fields):
            tk.Label(base_f, text=label_text, font=label_font,
                     bg=BG_CARD, fg=COLOR_TEXT, anchor="e", width=14).grid(
                row=i, column=0, padx=(0, 8), pady=5, sticky="e")
            e = tk.Entry(base_f, textvariable=var,
                         font=entry_font, width=14,
                         justify=tk.CENTER, relief=tk.SOLID, bd=1)
            e.grid(row=i, column=1, padx=0, pady=5)
            tk.Label(base_f, text="元", font=label_font,
                     bg=BG_CARD, fg=COLOR_MUTED).grid(
                row=i, column=2, padx=(4, 0), pady=5, sticky="w")
            # 商品销售行加"同步"按钮
            if var is self.settle_goods_var:
                self.settle_goods_entry = e
                ttk.Button(base_f, text=" 同步 ",
                          style="BlueSm.TButton", cursor="hand2",
                          command=self._settle_sync_goods).grid(
                    row=i, column=3, padx=(8, 0), pady=5)

        # ===== 左侧下方: 其他收支 =====
        other_f = tk.LabelFrame(left, text="  其他收支  ",
                                 font=(FONT_FAMILY, 11, "bold"),
                                 fg=COLOR_ACCENT, bg=BG_CARD, padx=14, pady=10)
        other_f.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # 输入行
        input_row = tk.Frame(other_f, bg=BG_CARD)
        input_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(input_row, text="备注:", font=(FONT_FAMILY, 10),
                 bg=BG_CARD, fg=COLOR_TEXT).pack(side=tk.LEFT)
        tk.Entry(input_row, textvariable=self.settle_other_note_var,
                 font=(FONT_FAMILY, 10), width=12,
                 relief=tk.SOLID, bd=1).pack(side=tk.LEFT, padx=(4, 8))
        tk.Label(input_row, text="金额:", font=(FONT_FAMILY, 10),
                 bg=BG_CARD, fg=COLOR_TEXT).pack(side=tk.LEFT)
        tk.Entry(input_row, textvariable=self.settle_other_amount_var,
                 font=(FONT_FAMILY, 10), width=8,
                 justify=tk.CENTER, relief=tk.SOLID, bd=1).pack(side=tk.LEFT, padx=(4, 8))
        ttk.Button(input_row, text=" 添加 ",
                  style="Green.TButton", cursor="hand2",
                  command=self._settle_add_other).pack(side=tk.LEFT, padx=4)

        # Treeview 明细列表
        tree_frame = tk.Frame(other_f, bg=BG_CARD)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        columns = ("seq", "note", "amount")
        self.settle_other_tree = ttk.Treeview(tree_frame, columns=columns,
                                               show="headings", height=5)
        self.settle_other_tree.heading("seq", text="序号")
        self.settle_other_tree.heading("note", text="备注")
        self.settle_other_tree.heading("amount", text="金额(元)")
        self.settle_other_tree.column("seq", width=50, anchor=tk.CENTER)
        self.settle_other_tree.column("note", width=180, anchor=tk.CENTER)
        self.settle_other_tree.column("amount", width=100, anchor=tk.CENTER)

        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL,
                           command=self.settle_other_tree.yview)
        self.settle_other_tree.configure(yscrollcommand=sb.set)
        self.settle_other_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.settle_other_tree.tag_configure("income", foreground=COLOR_SUCCESS)
        self.settle_other_tree.tag_configure("expense", foreground=COLOR_DANGER)

        # 底部操作行
        bottom_row = tk.Frame(other_f, bg=BG_CARD)
        bottom_row.pack(fill=tk.X)
        ttk.Button(bottom_row, text=" 删除选中 ",
                  style="Red.TButton", cursor="hand2",
                  command=self._settle_remove_other).pack(side=tk.LEFT, padx=(0, 16))
        tk.Label(bottom_row, text="其他收支合计 :", font=(FONT_FAMILY, 10, "bold"),
                 bg=BG_CARD, fg=COLOR_TEXT).pack(side=tk.LEFT)
        tk.Label(bottom_row, textvariable=self.settle_other_total_var,
                 font=(FONT_FAMILY, 11, "bold"),
                 bg=BG_CARD, fg=COLOR_ACCENT).pack(side=tk.LEFT, padx=(4, 0))
        tk.Label(bottom_row, text="元", font=(FONT_FAMILY, 10),
                 bg=BG_CARD, fg=COLOR_MUTED).pack(side=tk.LEFT, padx=(4, 0))

        # ===== 右侧: 结算结果 =====
        res_f = tk.Frame(right, bg="#F8F9FA", bd=1, relief=tk.SOLID)
        res_f.pack(fill=tk.BOTH, expand=True)

        res_header = tk.Frame(res_f, bg=BG_HEADER, height=40)
        res_header.pack(fill=tk.X)
        res_header.pack_propagate(False)
        tk.Label(res_header, text="  结算结果",
                 font=(FONT_FAMILY, 12, "bold"),
                 fg="white", bg=BG_HEADER).pack(side=tk.LEFT, padx=8)

        res_body = tk.Frame(res_f, bg="#F8F9FA", padx=20, pady=12)
        res_body.pack(fill=tk.BOTH, expand=True)

        # 公式说明
        tk.Label(res_body,
                 text="理论现金 = 备用金 + 网费 + 商品销售 + 其他收支 - 微信 - 支付宝",
                 font=(FONT_FAMILY, 8), bg="#F8F9FA", fg=COLOR_MUTED,
                 wraplength=350, justify=tk.LEFT).pack(anchor="w", pady=(0, 8))

        # 汇总项展示
        self.settle_summary_labels = {}
        summary_items = [
            ("reserve", "备用金", COLOR_TEXT),
            ("net_income", "本班网费收入", COLOR_PRIMARY),
            ("goods", "商品销售金额", COLOR_SUCCESS),
            ("other_total", "其他收支合计", COLOR_ACCENT),
            ("wechat", "微信收款 (扣除)", COLOR_MUTED),
            ("alipay", "支付宝收款 (扣除)", COLOR_MUTED),
        ]
        for key, title, color in summary_items:
            row = tk.Frame(res_body, bg="#F8F9FA")
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=title, font=(FONT_FAMILY, 10),
                     bg="#F8F9FA", fg=COLOR_MUTED, width=18, anchor="w").pack(side=tk.LEFT)
            lbl = tk.Label(row, text="--",
                           font=(FONT_FAMILY, 11, "bold"),
                           bg="#F8F9FA", fg=color)
            lbl.pack(side=tk.LEFT)
            self.settle_summary_labels[key] = lbl

        # 分隔线
        tk.Frame(res_body, height=2, bg="#DFE6E9").pack(fill=tk.X, pady=8)

        # 理论现金
        tk.Label(res_body, text="理论现金",
                 font=(FONT_FAMILY, 11, "bold"),
                 bg="#F8F9FA", fg=COLOR_TEXT).pack(anchor="w", pady=(4, 2))
        tk.Label(res_body, textvariable=self.settle_theory_var,
                 font=(FONT_FAMILY, 16, "bold"),
                 bg="#F8F9FA", fg=COLOR_PRIMARY).pack(anchor="w", pady=(0, 4))

        # 实际现金
        tk.Label(res_body, text="实际现金",
                 font=(FONT_FAMILY, 11, "bold"),
                 bg="#F8F9FA", fg=COLOR_TEXT).pack(anchor="w", pady=(4, 2))
        self.settle_actual_display_label = tk.Label(
            res_body, text="--",
            font=(FONT_FAMILY, 16, "bold"),
            bg="#F8F9FA", fg=COLOR_TEXT)
        self.settle_actual_display_label.pack(anchor="w", pady=(0, 4))

        # 粗分隔线
        tk.Frame(res_body, height=3, bg=BG_HEADER).pack(fill=tk.X, pady=8)

        # 差额
        tk.Label(res_body, text="差 额",
                 font=(FONT_FAMILY, 12, "bold"),
                 bg="#F8F9FA", fg=COLOR_TEXT).pack(anchor="w", pady=(4, 2))
        self.settle_diff_label = tk.Label(
            res_body, textvariable=self.settle_diff_var,
            font=(FONT_FAMILY, 28, "bold"),
            bg="#F8F9FA", fg=COLOR_TEXT)
        self.settle_diff_label.pack(anchor="w", pady=(0, 2))
        self.settle_status_label = tk.Label(
            res_body, textvariable=self.settle_diff_status_var,
            font=(FONT_FAMILY, 12, "bold"),
            bg="#F8F9FA", fg=COLOR_TEXT)
        self.settle_status_label.pack(anchor="w", pady=(0, 8))

        # 计算按钮
        ttk.Button(res_body, text="  计算核算  ",
                  style="GreenLg.TButton", cursor="hand2",
                  command=self._settle_calculate).pack(pady=(8, 0))

    # -------------------- 交班核算业务逻辑 --------------------
    def _settle_sync_goods(self):
        """从当前售出数据同步商品销售金额"""
        ga = 0
        for cat, items in CATEGORIES.items():
            for item_name, price in items:
                ga += self.data[cat][item_name]["sold"] * price
        self.settle_goods_var.set(f"{ga:.2f}")

    def _settle_add_other(self):
        """添加一条其他收支明细"""
        note = self.settle_other_note_var.get().strip()
        amount_str = self.settle_other_amount_var.get().strip()
        if not note:
            messagebox.showerror("输入错误", "备注不能为空！")
            return
        try:
            amount = float(amount_str)
        except (ValueError, TypeError):
            messagebox.showerror("输入错误", f"金额必须是数字！\n当前输入: \"{amount_str}\"")
            return
        self.settle_other_items.append({"note": note, "amount": amount})
        self.settle_other_note_var.set("")
        self.settle_other_amount_var.set("")
        self._settle_refresh_other_list()

    def _settle_remove_other(self):
        """删除选中的其他收支明细"""
        selected = self.settle_other_tree.selection()
        if not selected:
            return
        # 获取选中项的索引（从 values 中的序号减 1）
        indices = []
        for item_id in selected:
            vals = self.settle_other_tree.item(item_id, "values")
            indices.append(int(vals[0]) - 1)
        for idx in sorted(indices, reverse=True):
            if 0 <= idx < len(self.settle_other_items):
                self.settle_other_items.pop(idx)
        self._settle_refresh_other_list()

    def _settle_refresh_other_list(self):
        """刷新其他收支 Treeview 和合计"""
        for item in self.settle_other_tree.get_children():
            self.settle_other_tree.delete(item)
        total = 0.0
        for i, entry in enumerate(self.settle_other_items):
            amount = entry["amount"]
            total += amount
            tag = "income" if amount >= 0 else "expense"
            display_amount = f"+{amount:.2f}" if amount >= 0 else f"{amount:.2f}"
            self.settle_other_tree.insert("", "end", values=(
                i + 1, entry["note"], display_amount
            ), tags=(tag,))
        self.settle_other_total_var.set(f"{total:.2f}")

    def _settle_calculate(self):
        """核心计算：理论现金 vs 实际现金"""
        def _parse(var, name):
            s = var.get().strip()
            try:
                return float(s)
            except (ValueError, TypeError):
                messagebox.showerror("输入错误", f"【{name}】必须是数字！\n当前输入: \"{s}\"")
                return None

        reserve = _parse(self.settle_reserve_var, "备用金")
        if reserve is None:
            return
        net_income = _parse(self.settle_net_income_var, "本班网费收入")
        if net_income is None:
            return
        goods = _parse(self.settle_goods_var, "商品销售金额")
        if goods is None:
            return
        wechat = _parse(self.settle_wechat_var, "微信收款")
        if wechat is None:
            return
        alipay = _parse(self.settle_alipay_var, "支付宝收款")
        if alipay is None:
            return
        actual = _parse(self.settle_actual_cash_var, "实际现金总额")
        if actual is None:
            return

        other_total = sum(item["amount"] for item in self.settle_other_items)

        # 理论现金 = 备用金 + 网费 + 商品销售 + 其他收支 - 微信 - 支付宝
        theory = reserve + net_income + goods + other_total - wechat - alipay
        diff = actual - theory

        # 更新右侧汇总数字
        self.settle_summary_labels["reserve"].config(text=f"{reserve:.2f} 元")
        self.settle_summary_labels["net_income"].config(text=f"{net_income:.2f} 元")
        self.settle_summary_labels["goods"].config(text=f"{goods:.2f} 元")
        other_disp = f"+{other_total:.2f}" if other_total >= 0 else f"{other_total:.2f}"
        self.settle_summary_labels["other_total"].config(text=f"{other_disp} 元")
        self.settle_summary_labels["wechat"].config(text=f"-{wechat:.2f} 元")
        self.settle_summary_labels["alipay"].config(text=f"-{alipay:.2f} 元")

        self.settle_theory_var.set(f"{theory:.2f} 元")
        self.settle_actual_display_label.config(text=f"{actual:.2f} 元")

        # 差额判定
        diff_rounded = round(diff, 2)
        if diff_rounded == 0:
            color = COLOR_SUCCESS
            self.settle_diff_var.set("0.00 元")
            self.settle_diff_status_var.set("账目正确")
        elif diff_rounded > 0:
            color = COLOR_PRIMARY
            self.settle_diff_var.set(f"+{diff_rounded:.2f} 元")
            self.settle_diff_status_var.set(f"多出 {abs(diff_rounded):.2f} 元")
        else:
            color = COLOR_DANGER
            self.settle_diff_var.set(f"{diff_rounded:.2f} 元")
            self.settle_diff_status_var.set(f"少了 {abs(diff_rounded):.2f} 元")

        self.settle_diff_label.config(fg=color)
        self.settle_status_label.config(fg=color)
        self._save_data()

    # -------------------- 包夜计算器标签页 --------------------
    def _build_overnight_tab(self):
        tab = tk.Frame(self.notebook, bg=BG_CARD)
        self.notebook.add(tab, text="  包夜计算器  ")

        # 标题
        title_bar = tk.Frame(tab, bg=BG_HEADER, height=44)
        title_bar.pack(fill=tk.X, padx=12, pady=(12, 0))
        title_bar.pack_propagate(False)
        tk.Label(title_bar, text="包夜费用计算器",
                 font=(FONT_FAMILY, 14, "bold"),
                 fg="white", bg=BG_HEADER).pack(side=tk.LEFT, padx=16)
        self.overnight_sys_time_label = tk.Label(
            title_bar, font=(FONT_FAMILY, 11), fg="#B2BEC3", bg=BG_HEADER)
        self.overnight_sys_time_label.pack(side=tk.RIGHT, padx=16)

        # 左右布局
        body = tk.Frame(tab, bg=BG_CARD)
        body.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        left = tk.Frame(body, bg=BG_CARD)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        right = tk.Frame(body, bg=BG_CARD)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))

        # ===== 左 : 时间设置 =====
        time_f = tk.LabelFrame(left, text="  起算时间  ",
                               font=(FONT_FAMILY, 11, "bold"),
                               fg=COLOR_PRIMARY, bg=BG_CARD, padx=14, pady=10)
        time_f.pack(fill=tk.X, pady=(0, 8))

        r0 = tk.Frame(time_f, bg=BG_CARD)
        r0.pack(fill=tk.X, pady=4)
        tk.Label(r0, text="当前系统时间 :", font=(FONT_FAMILY, 10),
                 bg=BG_CARD, fg=COLOR_MUTED).pack(side=tk.LEFT)
        self.overnight_clock_label = tk.Label(
            r0, text="--:--:--", font=(FONT_FAMILY, 11, "bold"),
            bg=BG_CARD, fg=COLOR_TEXT)
        self.overnight_clock_label.pack(side=tk.LEFT, padx=8)

        r1 = tk.Frame(time_f, bg=BG_CARD)
        r1.pack(fill=tk.X, pady=8)
        tk.Label(r1, text="起算时间 :", font=(FONT_FAMILY, 11, "bold"),
                 bg=BG_CARD, fg=COLOR_TEXT).pack(side=tk.LEFT)

        now = datetime.now()
        self.overnight_hour_var = tk.StringVar(value=str(now.hour))
        self.overnight_minute_var = tk.StringVar(value=str(now.minute))

        spin_font = (FONT_FAMILY, 16, "bold")
        h_spin = tk.Spinbox(r1, from_=0, to=23, width=3,
                            textvariable=self.overnight_hour_var,
                            font=spin_font, justify=tk.CENTER, wrap=True,
                            relief=tk.SOLID, bd=1,
                            command=self._on_overnight_time_changed)
        h_spin.pack(side=tk.LEFT, padx=(10, 0))
        tk.Label(r1, text=" : ", font=spin_font,
                 bg=BG_CARD, fg=COLOR_TEXT).pack(side=tk.LEFT)
        m_spin = tk.Spinbox(r1, from_=0, to=59, width=3,
                            textvariable=self.overnight_minute_var,
                            font=spin_font, justify=tk.CENTER, wrap=True,
                            relief=tk.SOLID, bd=1,
                            command=self._on_overnight_time_changed)
        m_spin.pack(side=tk.LEFT)
        h_spin.bind("<KeyRelease>", lambda e: self._on_overnight_time_changed())
        m_spin.bind("<KeyRelease>", lambda e: self._on_overnight_time_changed())

        ttk.Button(r1, text=" 使用当前时间 ",
                  style="BlueSm.TButton", cursor="hand2",
                  command=self._reset_overnight_to_now).pack(side=tk.LEFT, padx=14)

        r2 = tk.Frame(time_f, bg=BG_CARD)
        r2.pack(fill=tk.X, pady=4)
        tk.Label(r2, text="取整后时间 :", font=(FONT_FAMILY, 10),
                 bg=BG_CARD, fg=COLOR_MUTED).pack(side=tk.LEFT)
        self.overnight_rounded_label = tk.Label(
            r2, text="--:--", font=(FONT_FAMILY, 13, "bold"),
            bg=BG_CARD, fg="#E17055")
        self.overnight_rounded_label.pack(side=tk.LEFT, padx=8)
        tk.Label(r2, text="( 不满30分取整点, 满30分取30 )",
                 font=(FONT_FAMILY, 8), bg=BG_CARD, fg="#B2BEC3").pack(side=tk.LEFT)

        # ===== 左 : 会员类型 =====
        mem_f = tk.LabelFrame(left, text="  会员类型  ",
                              font=(FONT_FAMILY, 11, "bold"),
                              fg=COLOR_ACCENT, bg=BG_CARD, padx=14, pady=10)
        mem_f.pack(fill=tk.X, pady=(0, 8))

        self.overnight_member_var = tk.StringVar(value=OVERNIGHT_RATES[0][0])
        for i, (name, rate, _) in enumerate(OVERNIGHT_RATES):
            tk.Radiobutton(
                mem_f, text=f" {name}  ({rate}元/时)",
                variable=self.overnight_member_var, value=name,
                font=(FONT_FAMILY, 10), bg=BG_CARD,
                activebackground=BG_CARD, cursor="hand2",
                selectcolor=BG_CARD,
                command=self._on_member_type_changed
            ).grid(row=i // 3, column=i % 3, sticky="w", padx=10, pady=4)

        # ===== 左 : 费率参考 =====
        ref_f = tk.LabelFrame(left, text="  费率参考  ",
                              font=(FONT_FAMILY, 10, "bold"),
                              fg=COLOR_MUTED, bg=BG_CARD, padx=10, pady=8)
        ref_f.pack(fill=tk.X)

        for c, h in enumerate(["会员类型", "每小时费率", "包夜费(23-08点)"]):
            tk.Label(ref_f, text=h, font=(FONT_FAMILY, 9, "bold"),
                     bg="#DFE6E9", fg=COLOR_TEXT, width=15,
                     anchor=tk.CENTER).grid(row=0, column=c, padx=1, pady=1)

        self.overnight_rate_row_labels = []
        for i, (name, rate, ofee) in enumerate(OVERNIGHT_RATES):
            bg = BG_CARD if i % 2 == 0 else "#F8F9FA"
            lbls = []
            for c, txt in enumerate([name, f"{rate} 元", f"{ofee} 元"]):
                lbl = tk.Label(ref_f, text=txt, font=(FONT_FAMILY, 9),
                               bg=bg, fg=COLOR_TEXT, width=15, anchor=tk.CENTER)
                lbl.grid(row=i + 1, column=c, padx=1, pady=1)
                lbls.append(lbl)
            self.overnight_rate_row_labels.append(lbls)

        # ===== 右 : 计算结果 =====
        res_f = tk.Frame(right, bg="#F8F9FA", bd=1, relief=tk.SOLID)
        res_f.pack(fill=tk.BOTH, expand=True)

        res_header = tk.Frame(res_f, bg=BG_HEADER, height=40)
        res_header.pack(fill=tk.X)
        res_header.pack_propagate(False)
        tk.Label(res_header, text="  计算结果",
                 font=(FONT_FAMILY, 12, "bold"),
                 fg="white", bg=BG_HEADER).pack(side=tk.LEFT, padx=8)

        res_body = tk.Frame(res_f, bg="#F8F9FA", padx=20, pady=16)
        res_body.pack(fill=tk.BOTH, expand=True)

        def _result_section(parent, title, var_ref, value_color):
            tk.Label(parent, text=title, font=(FONT_FAMILY, 10),
                     bg="#F8F9FA", fg=COLOR_MUTED).pack(anchor="w", pady=(8, 2))
            lbl = tk.Label(parent, textvariable=var_ref,
                           font=(FONT_FAMILY, 13, "bold"),
                           bg="#F8F9FA", fg=value_color)
            lbl.pack(anchor="w", pady=(0, 4))

        self.overnight_detail_var = tk.StringVar(value="--")
        _result_section(res_body, "包夜前时段", self.overnight_detail_var, COLOR_TEXT)

        self.overnight_hourly_cost_var = tk.StringVar(value="--")
        _result_section(res_body, "上机费用", self.overnight_hourly_cost_var, COLOR_PRIMARY)

        self.overnight_fee_display_var = tk.StringVar(value="--")
        _result_section(res_body, "包夜费用", self.overnight_fee_display_var, COLOR_ACCENT)

        tk.Frame(res_body, height=2, bg="#DFE6E9").pack(fill=tk.X, pady=10)

        tk.Label(res_body, text="应收总费用",
                 font=(FONT_FAMILY, 11, "bold"),
                 bg="#F8F9FA", fg=COLOR_TEXT).pack(anchor="w", pady=(4, 2))
        self.overnight_total_var = tk.StringVar(value="--")
        tk.Label(res_body, textvariable=self.overnight_total_var,
                 font=(FONT_FAMILY, 28, "bold"),
                 bg="#F8F9FA", fg=COLOR_DANGER).pack(anchor="w", pady=(0, 12))

        ttk.Button(res_body, text="  重新计算  ",
                  style="GreenLg.TButton", cursor="hand2",
                  command=self._calc_overnight_fee).pack(pady=(8, 0))

        self._highlight_rate_row()
        self._calc_overnight_fee()
        self._update_overnight_time()

    def _update_time(self):
        self.time_label.config(text=datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))
        self.root.after(1000, self._update_time)

    # ==================== 业务逻辑 ====================
    def _start_selling(self):
        for (cat, item_name), w in self.widgets.items():
            val = w["init_var"].get().strip()
            if not val.isdigit():
                price = self.data[cat][item_name]["price"]
                messagebox.showerror("输入错误",
                                     f"【{cat}】{item_name}({price}元) 的初始数量必须是非负整数！\n当前输入: \"{val}\"")
                return
            self.data[cat][item_name]["initial"] = int(val)
            self.data[cat][item_name]["sold"] = 0

        self.mode = "selling"
        for (cat, item_name), w in self.widgets.items():
            w["init_entry"].config(state=tk.DISABLED)
            w["sell_btn"].config(state=tk.NORMAL)
            w["undo_btn"].config(state=tk.NORMAL)
            w["restock_btn"].config(state=tk.NORMAL)

        self.start_btn.config(state=tk.DISABLED)
        self.reset_btn.config(state=tk.NORMAL)
        self.status_var.set("[ 营业中 ]  点击 \"售出 +1\" 记录卖出商品")
        self.status_label.config(fg=COLOR_SUCCESS)
        self._refresh_all()
        self._save_data()
        messagebox.showinfo("提示", "初始数量已确认！\n现在可以点击 \"售出 +1\" 按钮记录卖出商品。")

    def _reset_to_setup(self):
        if not messagebox.askyesno("确认", "重新设置将清除当前所有售出记录，确定吗？"):
            return
        self.mode = "setup"
        for (cat, item_name), w in self.widgets.items():
            w["init_entry"].config(state=tk.NORMAL)
            w["sell_btn"].config(state=tk.DISABLED)
            w["undo_btn"].config(state=tk.DISABLED)
            w["restock_btn"].config(state=tk.DISABLED)
            self.data[cat][item_name]["sold"] = 0
            self.data[cat][item_name]["initial"] = 0
            w["init_var"].set("0")
        self.start_btn.config(state=tk.NORMAL)
        self.reset_btn.config(state=tk.DISABLED)
        self.status_var.set("[ 设置模式 ]  请填写各商品初始数量后点击\"确认初始数量\"")
        self.status_label.config(fg=COLOR_DANGER)
        self.sell_log.clear()
        self._refresh_log_display()
        self._refresh_all()
        self._save_data()

    def _sell_one(self, cat, item_name):
        d = self.data[cat][item_name]
        price = d["price"]
        if d["sold"] >= d["initial"]:
            messagebox.showwarning("库存不足",
                                   f"【{cat}】{item_name}({price}元) 已全部售出（初始{d['initial']}件）！\n"
                                   f"如需补货请点击 \"补货\" 按钮。")
            return
        d["sold"] += 1
        self._add_log_entry(cat, item_name, price, "sell")
        self._refresh_item(cat, item_name)
        self._refresh_subtotal(cat)
        self._refresh_grand_total()
        self._save_data()

        btn = self.widgets[(cat, item_name)]["sell_btn"]
        original_style = CATEGORY_SELL_STYLES.get(cat, "Green.TButton")
        btn.configure(style="Gold.TButton")
        self.root.after(150, lambda: btn.configure(style=original_style))

    def _undo_one(self, cat, item_name):
        d = self.data[cat][item_name]
        if d["sold"] <= 0:
            return
        d["sold"] -= 1
        self._add_log_entry(cat, item_name, d["price"], "undo")
        self._refresh_item(cat, item_name)
        self._refresh_subtotal(cat)
        self._refresh_grand_total()
        self._save_data()

    def _restock(self, cat, item_name):
        """补货：增加商品初始数量"""
        price = self.data[cat][item_name]["price"]
        qty = simpledialog.askinteger(
            "补货", f"【{cat}】{item_name}({price}元) 补货数量：",
            minvalue=1, maxvalue=9999, parent=self.root)
        if qty is None:
            return
        self.data[cat][item_name]["initial"] += qty
        self.widgets[(cat, item_name)]["init_var"].set(
            str(self.data[cat][item_name]["initial"]))
        self._refresh_item(cat, item_name)
        self._refresh_subtotal(cat)
        self._refresh_grand_total()
        self._save_data()

    # ==================== 售出记录日志 ====================
    def _add_log_entry(self, cat, item_name, price, action):
        self.sell_log.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cat": cat, "item": item_name, "price": price, "action": action,
        })
        self._refresh_log_display()

    def _refresh_log_display(self):
        for item in self.log_tree.get_children():
            self.log_tree.delete(item)
        running = 0
        running_list = []
        for entry in self.sell_log:
            running += entry["price"] if entry["action"] == "sell" else -entry["price"]
            running_list.append(running)
        total = len(self.sell_log)
        for i in range(total - 1, -1, -1):
            e = self.sell_log[i]
            self.log_tree.insert("", "end", values=(
                i + 1, e["time"],
                "售出" if e["action"] == "sell" else "撤销",
                e["cat"], e.get("item", ""),
                f"{e['price']} 元", f"{running_list[i]:.2f}",
            ), tags=(e["action"],))
        self.log_count_var.set(f"共 {total} 条记录")

    # ==================== 包夜计算器逻辑 ====================
    def _round_time(self, hour, minute):
        if minute < 30:
            return hour, 0
        return hour, 30

    def _calc_overnight_fee(self):
        member_name = self.overnight_member_var.get()
        hourly_rate = overnight_fee = 0
        for name, rate, fee in OVERNIGHT_RATES:
            if name == member_name:
                hourly_rate, overnight_fee = rate, fee
                break
        try:
            hour = int(self.overnight_hour_var.get())
            minute = int(self.overnight_minute_var.get())
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
        except (ValueError, TypeError):
            self.overnight_detail_var.set("时间输入无效")
            self.overnight_hourly_cost_var.set("--")
            self.overnight_fee_display_var.set("--")
            self.overnight_total_var.set("--")
            self.overnight_rounded_label.config(text="--:--")
            return

        r_hour, r_minute = self._round_time(hour, minute)
        self.overnight_rounded_label.config(text=f"{r_hour:02d}:{r_minute:02d}")

        if r_hour >= OVERNIGHT_START or r_hour < OVERNIGHT_END:
            hourly_cost = 0.0
            self.overnight_detail_var.set("已在包夜时段内 (23:00 ~ 08:00)")
            self.overnight_hourly_cost_var.set("0.00 元  ( 无需加钟 )")
        else:
            diff_minutes = OVERNIGHT_START * 60 - (r_hour * 60 + r_minute)
            hourly_hours = diff_minutes / 60
            hourly_cost = hourly_hours * hourly_rate
            h_str = str(int(hourly_hours)) if hourly_hours == int(hourly_hours) else f"{hourly_hours:.1f}"
            self.overnight_detail_var.set(
                f"{r_hour:02d}:{r_minute:02d}  ->  23:00  =  {h_str} 小时")
            self.overnight_hourly_cost_var.set(
                f"{h_str}  x  {hourly_rate}  =  {hourly_cost:.2f} 元")

        total = hourly_cost + overnight_fee
        # 取整：小数部分超过 0.1 元则进 1 元，否则舍去
        fraction = round(total - int(total), 2)
        if fraction > 0.1:
            total = int(total) + 1
        else:
            total = int(total)
        self.overnight_fee_display_var.set(f"{overnight_fee} 元")
        self.overnight_total_var.set(f"{total} 元")

    def _update_overnight_time(self):
        now = datetime.now()
        self.overnight_sys_time_label.config(text=now.strftime("%Y-%m-%d %H:%M:%S"))
        self.overnight_clock_label.config(text=now.strftime("%H:%M:%S"))
        self.root.after(1000, self._update_overnight_time)

    def _reset_overnight_to_now(self):
        now = datetime.now()
        self.overnight_hour_var.set(str(now.hour))
        self.overnight_minute_var.set(str(now.minute))
        self._calc_overnight_fee()

    def _on_member_type_changed(self):
        self._highlight_rate_row()
        self._calc_overnight_fee()

    def _on_overnight_time_changed(self):
        self._calc_overnight_fee()

    def _highlight_rate_row(self):
        selected = self.overnight_member_var.get()
        for i, (name, _, _) in enumerate(OVERNIGHT_RATES):
            if name == selected:
                bg, fg = "#FFF3E0", COLOR_DANGER
            else:
                bg = BG_CARD if i % 2 == 0 else "#F8F9FA"
                fg = COLOR_TEXT
            for lbl in self.overnight_rate_row_labels[i]:
                lbl.config(bg=bg, fg=fg)

    # ==================== UI 刷新 ====================
    def _refresh_item(self, cat, item_name):
        d = self.data[cat][item_name]
        w = self.widgets[(cat, item_name)]
        sold, initial, price = d["sold"], d["initial"], d["price"]
        remain = initial - sold
        w["sold_label"].config(text=str(sold))
        w["remain_label"].config(text=str(remain))
        w["amount_label"].config(text=f"{sold * price:.2f}")
        w["remain_label"].config(fg=COLOR_DANGER if remain <= 0 and initial > 0 else COLOR_TEXT)

    def _refresh_subtotal(self, cat):
        tc = ta = 0
        for item_name, price in CATEGORIES[cat]:
            d = self.data[cat][item_name]
            tc += d["sold"]
            ta += d["sold"] * price
        self.subtotal_labels[cat]["count"].config(text=f"售出 {tc} 件")
        self.subtotal_labels[cat]["amount"].config(text=f"金额 : {ta:.2f} 元")

    def _refresh_grand_total(self):
        ga = gc = 0
        for cat, items in CATEGORIES.items():
            for item_name, price in items:
                d = self.data[cat][item_name]
                gc += d["sold"]
                ga += d["sold"] * price
        self.grand_total_var.set(f"{ga:.2f}")
        self.grand_sold_count_var.set(str(gc))

    def _refresh_all(self):
        for cat, items in CATEGORIES.items():
            for item_name, price in items:
                self._refresh_item(cat, item_name)
            self._refresh_subtotal(cat)
        self._refresh_grand_total()

    # ==================== 数据持久化 ====================
    def _save_data(self):
        save_obj = {"mode": self.mode, "data": {}, "log": self.sell_log}
        for cat in self.data:
            save_obj["data"][cat] = {}
            for item_name in self.data[cat]:
                save_obj["data"][cat][item_name] = self.data[cat][item_name]
        save_obj["settlement"] = {
            "reserve": self.settle_reserve_var.get(),
            "net_income": self.settle_net_income_var.get(),
            "goods": self.settle_goods_var.get(),
            "wechat": self.settle_wechat_var.get(),
            "alipay": self.settle_alipay_var.get(),
            "actual_cash": self.settle_actual_cash_var.get(),
            "other_items": self.settle_other_items,
        }
        try:
            fp = os.path.join(APP_DIR, DATA_FILE)
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(save_obj, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_data(self):
        try:
            fp = os.path.join(APP_DIR, DATA_FILE)
            if not os.path.exists(fp):
                return
            with open(fp, "r", encoding="utf-8") as f:
                save_obj = json.load(f)

            mode = save_obj.get("mode", "setup")
            saved = save_obj.get("data", {})

            for cat in self.data:
                if cat not in saved:
                    continue
                for item_name in self.data[cat]:
                    if item_name not in saved[cat]:
                        continue
                    self.data[cat][item_name]["initial"] = saved[cat][item_name].get("initial", 0)
                    self.data[cat][item_name]["sold"] = saved[cat][item_name].get("sold", 0)
                    self.widgets[(cat, item_name)]["init_var"].set(
                        str(self.data[cat][item_name]["initial"]))

            if mode == "selling":
                self.mode = "selling"
                for (cat, item_name), w in self.widgets.items():
                    w["init_entry"].config(state=tk.DISABLED)
                    w["sell_btn"].config(state=tk.NORMAL)
                    w["undo_btn"].config(state=tk.NORMAL)
                    w["restock_btn"].config(state=tk.NORMAL)
                self.start_btn.config(state=tk.DISABLED)
                self.reset_btn.config(state=tk.NORMAL)
                self.status_var.set("[ 营业中 ]  点击 \"售出 +1\" 记录卖出商品")
                self.status_label.config(fg=COLOR_SUCCESS)

            self.sell_log = save_obj.get("log", [])
            self._refresh_log_display()
            self._refresh_all()

            # 恢复交班核算数据
            settle = save_obj.get("settlement", {})
            if settle:
                self.settle_reserve_var.set(settle.get("reserve", "500"))
                self.settle_net_income_var.set(settle.get("net_income", "0"))
                self.settle_goods_var.set(settle.get("goods", "0.00"))
                self.settle_wechat_var.set(settle.get("wechat", "0"))
                self.settle_alipay_var.set(settle.get("alipay", "0"))
                self.settle_actual_cash_var.set(settle.get("actual_cash", "0"))
                self.settle_other_items = settle.get("other_items", [])
                self._settle_refresh_other_list()
        except Exception:
            pass

    # ==================== 导出报表 ====================
    def _export_report(self):
        now = datetime.now()
        filename = f"交班报表_{now.strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(APP_DIR, filename)

        lines = [
            "=" * 55,
            "        飞宇网吧收银交班报表",
            "=" * 55,
            f"导出时间: {now.strftime('%Y-%m-%d %H:%M:%S')}", "",
        ]
        grand_count = grand_amount = 0
        for cat, items in CATEGORIES.items():
            lines.append(f"--- {cat} ---")
            lines.append(f"{'商品':>8}  {'单价':>6}  {'初始':>6}  {'售出':>6}  {'剩余':>6}  {'金额':>10}")
            cc = ca = 0
            for item_name, price in items:
                d = self.data[cat][item_name]
                sold, initial = d["sold"], d["initial"]
                remain = initial - sold
                amount = sold * price
                cc += sold
                ca += amount
                if sold > 0 or initial > 0:
                    lines.append(f"{item_name:>8}  {price:>5}元  {initial:>6}  {sold:>6}  {remain:>6}  {amount:>9.2f}元")
            lines.append(f"  小计: 售出 {cc} 件, 金额 {ca:.2f} 元")
            lines.append("")
            grand_count += cc
            grand_amount += ca

        lines.append("=" * 55)
        lines.append(f"  总计: 售出 {grand_count} 件")
        lines.append(f"  销售总额: {grand_amount:.2f} 元")
        lines.append("=" * 55)

        if self.sell_log:
            lines.append("")
            lines.append("--- 售出记录明细（按时间顺序）---")
            lines.append(f"{'序号':>4}  {'时间':<20}  {'操作':<6}  {'类别':<8}  {'商品':<8}  {'单价':>6}")
            for i, e in enumerate(self.sell_log):
                act = "售出" if e["action"] == "sell" else "撤销"
                item = e.get("item", "")
                lines.append(f"{i+1:>4}  {e['time']:<20}  {act:<6}  {e['cat']:<8}  {item:<8}  {e['price']:>5}元")
            lines.append(f"  共 {len(self.sell_log)} 条操作记录")
            lines.append("=" * 55)

        # 交班核算信息
        lines.append("")
        lines.append("--- 交班核算 ---")
        try:
            reserve = float(self.settle_reserve_var.get())
            net_income = float(self.settle_net_income_var.get())
            goods_amount = float(self.settle_goods_var.get())
            wechat = float(self.settle_wechat_var.get())
            alipay = float(self.settle_alipay_var.get())
            actual_cash = float(self.settle_actual_cash_var.get())
            other_total = sum(item["amount"] for item in self.settle_other_items)
            theory = reserve + net_income + goods_amount + other_total - wechat - alipay
            diff = actual_cash - theory

            lines.append(f"  备用金:          {reserve:.2f} 元")
            lines.append(f"  本班网费收入:    {net_income:.2f} 元")
            lines.append(f"  商品销售金额:    {goods_amount:.2f} 元")
            if self.settle_other_items:
                lines.append(f"  其他收支明细:")
                for i, item in enumerate(self.settle_other_items):
                    sign = "+" if item["amount"] >= 0 else ""
                    lines.append(f"    {i+1}. {item['note']}  {sign}{item['amount']:.2f} 元")
            lines.append(f"  其他收支合计:    {other_total:+.2f} 元")
            lines.append(f"  微信收款:        {wechat:.2f} 元")
            lines.append(f"  支付宝收款:      {alipay:.2f} 元")
            lines.append(f"  {'─' * 30}")
            lines.append(f"  理论现金:        {theory:.2f} 元")
            lines.append(f"  实际现金:        {actual_cash:.2f} 元")
            lines.append(f"  差额:            {diff:+.2f} 元")
            if round(diff, 2) == 0:
                lines.append(f"  状态: 账目正确")
            elif diff > 0:
                lines.append(f"  状态: 多出 {abs(diff):.2f} 元")
            else:
                lines.append(f"  状态: 少了 {abs(diff):.2f} 元")
        except (ValueError, TypeError):
            lines.append("  (核算数据未填写完整)")
        lines.append("=" * 55)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            messagebox.showinfo("导出成功", f"交班报表已保存到:\n{filepath}")
        except Exception as e:
            messagebox.showerror("导出失败", f"保存报表时出错:\n{e}")


def main():
    root = tk.Tk()
    CashierApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
