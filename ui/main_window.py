# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
    QTreeWidgetItem, QPushButton, QLineEdit, QLabel, QMessageBox, QHeaderView,
    QTabBar, QDialog, QComboBox, QDateEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QDate
from PyQt5.QtGui import QFont, QColor
from core.database import DatabaseManager
from core.config import AppConfig
from core.utils import format_persian_number, get_persian_date
from ui.member_tab import MemberTab
from ui.report_tab import ReportTab
from ui.dialogs import SharePriceDialog, AddMemberDialog
import logging
from datetime import datetime
import sys

class MainWindow(QMainWindow):
    update_report = pyqtSignal()
    update_all = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{AppConfig.APP_NAME} 🏛️ - نسخه {AppConfig.APP_VERSION}")
        self.setGeometry(100, 100, 1400, 900)
        self.member_tabs = {}
        self.is_refreshing = False
        self._setup_ui()
        self.update_report.connect(self.reports_tab.load_data)
        self.update_all.connect(self._refresh_all)
        self._initial_load()

    def _get_styles(self):
        return {
            "main_window": """
                QMainWindow {
                    background-color: #F5F5F5;
                    font-family: 'B Nazanin';
                }
                QTabBar::tab {
                    background: #E0E0E0;
                    border: 1px solid #BDBDBD;
                    padding: 6px 12px;
                    margin-right: 2px;
                    border-top-left-radius: 5px;
                    border-top-right-radius: 5px;
                    font-family: 'B Nazanin';
                    font-size: 14px;
                }
                QTabBar::tab:selected {
                    background: #FFFFFF;
                    border-bottom: 3px solid #1976D2;
                    font-weight: bold;
                }
            """,
            "button_primary": """
                QPushButton {
                    background-color: #1976D2;
                    color: white;
                    border: none;
                    padding: 8px 12px;
                    border-radius: 4px;
                    font-family: 'B Nazanin';
                    font-size: 14px;
                    min-width: 100px;
                }
                QPushButton:hover {
                    background-color: #1565C0;
                }
            """,
            "button_secondary": """
                QPushButton {
                    background-color: #607D8B;
                    color: white;
                    border: none;
                    padding: 8px 12px;
                    border-radius: 4px;
                    font-family: 'B Nazanin';
                    font-size: 14px;
                    min-width: 100px;
                }
                QPushButton:hover {
                    background-color: #455A64;
                }
            """,
            "edit_button": """
                QPushButton {
                    background-color: #0288D1;
                    color: white;
                    border: none;
                    padding: 3px;
                    border-radius: 3px;
                    font-family: 'B Nazanin';
                    font-size: 12px;
                    min-width: 25px;
                    max-width: 25px;
                }
                QPushButton:hover {
                    background-color: #0277BD;
                }
            """,
            "tree_view": """
                QTreeWidget {
                    font-family: 'B Nazanin';
                    font-size: 14px;
                    alternate-background-color: #FAFAFA;
                    border: 1px solid #E0E0E0;
                }
                QTreeWidget::item {
                    padding: 5px;
                    border-bottom: 1px solid #EEEEEE;
                }
                QTreeWidget::item:selected {
                    background: #E3F2FD;
                    color: #000000;
                }
                QHeaderView::section {
                    background-color: #1976D2;
                    color: white;
                    padding: 5px;
                    border: none;
                    font-weight: bold;
                    font-family: 'B Nazanin';
                }
            """,
            "line_edit": """
                QLineEdit {
                    font-family: 'B Nazanin';
                    font-size: 14px;
                    padding: 8px;
                    border: 1px solid #BDBDBD;
                    border-radius: 4px;
                    min-width: 200px;
                }
                QLineEdit:focus {
                    border: 1px solid #1976D2;
                }
            """
        }

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.setStyleSheet(self._get_styles()["main_window"])
        self._setup_main_tabs()
        main_layout.addWidget(self.tabs)

    def _setup_main_tabs(self):
        self.members_tab = self._create_members_tab()
        self.tabs.addTab(self.members_tab, "📋 مدیریت اعضا")
        self.transactions_tab = self._create_transactions_tab()
        self.tabs.addTab(self.transactions_tab, "💸 تراکنش‌ها")
        self.loans_tab = self._create_loans_tab()
        self.tabs.addTab(self.loans_tab, "🏦 مدیریت وام‌ها")
        self.reports_tab = ReportTab(self)
        self.tabs.addTab(self.reports_tab, "📊 گزارش کلی")

    def _create_members_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        toolbar = QHBoxLayout()
        self.btn_new_member = QPushButton("➕ عضو جدید")
        self.btn_new_member.setStyleSheet(self._get_styles()["button_primary"])
        self.btn_new_member.clicked.connect(self._add_new_member)
        self.btn_formula = QPushButton("📈 فرمول")
        self.btn_formula.setStyleSheet(self._get_styles()["button_secondary"])
        self.btn_formula.clicked.connect(self._show_share_price_dialog)
        self.share_price_label = QLabel("💰 قیمت سهام: -")
        self.share_price_label.setStyleSheet("font-family: 'B Nazanin'; font-size: 14px; color: #333;")
        self.btn_refresh = QPushButton("🔄 بروزرسانی")
        self.btn_refresh.setStyleSheet(self._get_styles()["button_secondary"])
        self.btn_refresh.clicked.connect(self._refresh_all)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 جستجوی عضو (نام، کد، تلفن)...")
        self.search_box.setStyleSheet(self._get_styles()["line_edit"])
        self.search_box.textChanged.connect(self._search_members)
        self.search_box.returnPressed.connect(self._open_member_by_search)
        toolbar.addWidget(self.btn_new_member)
        toolbar.addWidget(self.btn_formula)
        toolbar.addWidget(self.share_price_label)
        toolbar.addWidget(self.btn_refresh)
        toolbar.addStretch()
        toolbar.addWidget(self.search_box)
        layout.addLayout(toolbar)
        
        self.members_table = QTreeWidget()
        self.members_table.setHeaderLabels([
            "🔢 شماره", "👤 نام و نام خانوادگی", "📌 کد عضویت", "📱 تلفن", 
            "🏦 شماره حساب", "📅 تاریخ عضویت", "⚡ وضعیت", "📈 تعداد سهام", "✏️"
        ])
        self.members_table.setStyleSheet(self._get_styles()["tree_view"])
        self.members_table.setColumnWidth(0, 80)
        self.members_table.setColumnWidth(1, 250)
        self.members_table.setColumnWidth(2, 120)
        self.members_table.setColumnWidth(8, 40)
        self.members_table.itemDoubleClicked.connect(self._on_member_double_clicked)
        layout.addWidget(self.members_table)
        
        return tab

    def _create_transactions_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        filter_layout = QHBoxLayout()
        self.trans_filter_type = QComboBox()
        self.trans_filter_type.addItems(["📜 همه تراکنش‌ها", "💵 عضویت", "💸 پرداخت", "🏦 وام"])
        self.trans_filter_type.setStyleSheet("font-family: 'B Nazanin'; font-size: 14px; padding: 5px;")
        
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setStyleSheet("font-family: 'B Nazanin'; font-size: 14px; padding: 5px;")
        self.start_date.setDisplayFormat("yyyy/MM/dd")
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setStyleSheet("font-family: 'B Nazanin'; font-size: 14px; padding: 5px;")
        self.end_date.setDisplayFormat("yyyy/MM/dd")
        self.end_date.setDate(QDate.currentDate())

        refresh_btn = QPushButton("🔄 بروزرسانی")
        refresh_btn.setStyleSheet(self._get_styles()["button_secondary"])
        refresh_btn.clicked.connect(self._load_transactions)
        filter_layout.addWidget(QLabel("📋 نوع تراکنش:"))
        filter_layout.addWidget(self.trans_filter_type)
        filter_layout.addWidget(QLabel("📅 از تاریخ:"))
        filter_layout.addWidget(self.start_date)
        filter_layout.addWidget(QLabel("📅 تا تاریخ:"))
        filter_layout.addWidget(self.end_date)
        filter_layout.addWidget(refresh_btn)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        self.transactions_table = QTreeWidget()
        self.transactions_table.setHeaderLabels([
            "🔢 شماره", "📅 تاریخ", "👤 عضو", "💰 مبلغ", "📋 نوع", "📝 توضیحات"
        ])
        self.transactions_table.setStyleSheet(self._get_styles()["tree_view"])
        self.transactions_table.setColumnWidth(0, 80)
        self.transactions_table.setColumnWidth(1, 120)
        self.transactions_table.setColumnWidth(2, 200)
        layout.addWidget(self.transactions_table)
        
        return tab

    def _create_loans_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        filter_layout = QHBoxLayout()
        self.loan_filter_status = QComboBox()
        self.loan_filter_status.addItems(["🏦 همه وام‌ها", "✅ وام‌های فعال", "✔️ وام‌های تسویه‌شده"])
        self.loan_filter_status.setStyleSheet("font-family: 'B Nazanin'; font-size: 14px; padding: 5px;")
        self.loan_start_date = QDateEdit()
        self.loan_start_date.setCalendarPopup(True)
        self.loan_start_date.setStyleSheet("font-family: 'B Nazanin'; font-size: 14px; padding: 5px;")
        self.loan_start_date.setDisplayFormat("yyyy/MM/dd")
        self.loan_end_date = QDateEdit()
        self.loan_end_date.setCalendarPopup(True)
        self.loan_end_date.setStyleSheet("font-family: 'B Nazanin'; font-size: 14px; padding: 5px;")
        self.loan_end_date.setDisplayFormat("yyyy/MM/dd")
        self.loan_end_date.setDate(QDate.currentDate())
        refresh_btn = QPushButton("🔄 بروزرسانی")
        refresh_btn.setStyleSheet(self._get_styles()["button_secondary"])
        refresh_btn.clicked.connect(self._load_loans)
        filter_layout.addWidget(QLabel("🏦 وضعیت وام:"))
        filter_layout.addWidget(self.loan_filter_status)
        filter_layout.addWidget(QLabel("📅 از تاریخ:"))
        filter_layout.addWidget(self.loan_start_date)
        filter_layout.addWidget(QLabel("📅 تا تاریخ:"))
        filter_layout.addWidget(self.loan_end_date)
        filter_layout.addWidget(refresh_btn)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        self.loans_table = QTreeWidget()
        self.loans_table.setHeaderLabels([
            "🔢 شماره", "👤 عضو", "💰 مبلغ", "📅 تاریخ اعطا", "📅 تاریخ تسویه",
            "📋 تعداد اقساط", "💵 قسط ماهانه", "⚡ وضعیت"
        ])
        self.loans_table.setStyleSheet(self._get_styles()["tree_view"])
        self.loans_table.setColumnWidth(0, 80)
        self.loans_table.setColumnWidth(1, 200)
        self.loans_table.setColumnWidth(3, 120)
        self.loans_table.setColumnWidth(4, 120)
        layout.addWidget(self.loans_table)
        
        return tab

    def _load_members(self):
        try:
            self.members_table.clear()
            query = "SELECT id, name, membership_code, phone, account_number, join_date, status FROM members ORDER BY join_date DESC"
            with DatabaseManager() as db:
                members = db.execute_query(query, fetch=True)
                for idx, member in enumerate(members, 1):
                    item = QTreeWidgetItem(self.members_table)
                    shares = self._calculate_shares(member[0])
                    item.setText(0, str(idx))
                    item.setText(1, member[1])
                    item.setText(2, member[2])
                    item.setText(3, member[3] or "-")
                    item.setText(4, member[4] or "-")
                    item.setText(5, get_persian_date(member[5]))
                    item.setText(6, member[6])
                    item.setText(7, format_persian_number(str(shares)))
                    if member[6] == "غیرفعال":
                        item.setForeground(6, QColor("#D32F2F"))
                    else:
                        item.setForeground(6, QColor("#388E3C"))
                    item.setData(0, Qt.UserRole, member[0])

                    edit_btn = QPushButton("✏️")
                    edit_btn.setStyleSheet(self._get_styles()["edit_button"])
                    edit_btn.clicked.connect(lambda _, mid=member[0]: self._edit_member(mid))
                    self.members_table.setItemWidget(item, 8, edit_btn)
        except Exception as e:
            logging.error(f"خطا در بارگذاری اعضا: {str(e)}")
            QMessageBox.critical(self, "❌ خطا", "خطا در بارگذاری لیست اعضا")

    def _load_transactions(self):
        try:
            self.transactions_table.clear()
            with DatabaseManager() as db:
                start_date = self.start_date.date().toString("yyyy/MM/dd")
                end_date = self.end_date.date().toString("yyyy/MM/dd")
                filter_type = self.trans_filter_type.currentText().split()[1] if self.trans_filter_type.currentIndex() > 0 else None
                query = """
                    SELECT t.id, t.date, m.name, t.amount, t.type, t.description 
                    FROM transactions t JOIN members m ON t.member_id = m.id
                    WHERE t.date BETWEEN ? AND ?
                """
                params = [start_date, end_date]
                if filter_type:
                    query += " AND t.type = ?"
                    params.append(filter_type)
                query += " ORDER BY t.id DESC"
                transactions = db.execute_query(query, params, fetch=True)
                for idx, trans in enumerate(transactions, 1):
                    item = QTreeWidgetItem(self.transactions_table)
                    amount = float(trans[3]) if trans[3] else 0
                    item.setText(0, str(idx))
                    item.setText(1, get_persian_date(trans[1]))
                    item.setText(2, trans[2])
                    item.setText(3, format_persian_number(str(amount)))
                    item.setText(4, trans[4])
                    item.setText(5, trans[5] if trans[5] else "-")
                    if trans[4] == "عضویت":
                        item.setForeground(3, QColor("#388E3C"))
                    elif trans[4] == "پرداخت":
                        item.setForeground(3, QColor("#1976D2"))
                    elif trans[4] == "وام":
                        item.setForeground(3, QColor("#D32F2F"))
        except Exception as e:
            logging.error(f"خطا در بارگذاری تراکنش‌ها: {str(e)}")
            QMessageBox.critical(self, "❌ خطا", f"خطا در بارگذاری تراکنش‌ها:\n{str(e)}")

    def _load_loans(self):
        try:
            self.loans_table.clear()
            with DatabaseManager() as db:
                start_date = self.loan_start_date.date().toString("yyyy/MM/dd")
                end_date = self.loan_end_date.date().toString("yyyy/MM/dd")
                filter_status = self.loan_filter_status.currentText().split()[1] if self.loan_filter_status.currentIndex() > 0 else None
                query = """
                    SELECT l.id, m.name, l.amount, l.start_date, l.end_date,
                    l.installments, l.monthly_payment, l.status 
                    FROM loans l JOIN members m ON l.member_id = m.id
                    WHERE l.start_date BETWEEN ? AND ?
                """
                params = [start_date, end_date]
                if filter_status:
                    query += " AND l.status = ?"
                    params.append(filter_status)
                query += " ORDER BY l.id DESC"
                loans = db.execute_query(query, params, fetch=True)
                for idx, loan in enumerate(loans, 1):
                    item = QTreeWidgetItem(self.loans_table)
                    amount = float(loan[2]) if loan[2] else 0
                    monthly_payment = float(loan[6]) if loan[6] else 0
                    item.setText(0, str(idx))
                    item.setText(1, loan[1])
                    item.setText(2, format_persian_number(str(amount)))
                    item.setText(3, get_persian_date(loan[3]))
                    item.setText(4, get_persian_date(loan[4]) if loan[4] else "-")
                    item.setText(5, str(loan[5]))
                    item.setText(6, format_persian_number(str(monthly_payment)))
                    item.setText(7, loan[7])
                    if loan[7] == "فعال":
                        item.setForeground(7, QColor("#1976D2"))
                    else:
                        item.setForeground(7, QColor("#388E3C"))
        except Exception as e:
            logging.error(f"خطا در بارگذاری وام‌ها: {str(e)}")
            QMessageBox.critical(self, "❌ خطا", f"خطا در بارگذاری وام‌ها:\n{str(e)}")

    def _edit_member(self, member_id):
        from PyQt5.QtWidgets import QFormLayout
        dialog = QDialog(self)
        dialog.setWindowTitle("✏️ ویرایش اطلاعات عضو")
        layout = QFormLayout(dialog)

        with DatabaseManager() as db:
            member = db.execute_query(
                "SELECT name, phone, account_number FROM members WHERE id=?",
                (member_id,), fetch=True
            )[0]
        
        name_input = QLineEdit(member[0])
        phone_input = QLineEdit(member[1] or "")
        account_input = QLineEdit(member[2] or "")
        for input_field in (name_input, phone_input, account_input):
            input_field.setStyleSheet(self._get_styles()["line_edit"])

        layout.addRow("👤 نام:", name_input)
        layout.addRow("📱 تلفن:", phone_input)
        layout.addRow("🏦 شماره حساب:", account_input)

        save_btn = QPushButton("💾 ذخیره")
        save_btn.setStyleSheet(self._get_styles()["button_primary"])
        save_btn.clicked.connect(lambda: self._save_member_edit(dialog, member_id, name_input, phone_input, account_input))
        layout.addWidget(save_btn)

        dialog.exec_()

    def _save_member_edit(self, dialog, member_id, name_input, phone_input, account_input):
        name = name_input.text().strip()
        phone = phone_input.text().strip()
        account = account_input.text().strip()
        if not name:
            QMessageBox.warning(self, "⚠️ خطا", "نام نمی‌تواند خالی باشد!")
            return
        try:
            with DatabaseManager() as db:
                db.execute_query(
                    "UPDATE members SET name=?, phone=?, account_number=? WHERE id=?",
                    (name, phone, account, member_id), fetch=False
                )
            self._refresh_all()
            dialog.accept()
            QMessageBox.information(self, "✅ موفق", "اطلاعات با موفقیت ویرایش شد!")
        except Exception as e:
            logging.error(f"خطا در ویرایش عضو {member_id}: {str(e)}")
            QMessageBox.critical(self, "❌ خطا", f"خطا در ذخیره:\n{str(e)}")

    def _calculate_shares(self, member_id):
        try:
            with DatabaseManager() as db:
                investments = db.execute_query(
                    "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE member_id=? AND type='عضویت'",
                    (member_id,), fetch=True
                )[0][0] or 0
                share_price = self._get_current_share_price()
                return investments / share_price if share_price > 0 else 0
        except Exception as e:
            logging.error(f"خطا در محاسبه سهام: {str(e)}")
            return 0

    def _calculate_loan_capacity(self, member_id):
        try:
            with DatabaseManager() as db:
                shares = self._calculate_shares(member_id)
                share_price = self._get_current_share_price()
                loan_factor = float(db.get_setting("loan_factor", "2"))
                return int(shares * loan_factor * share_price)
        except Exception as e:
            logging.error(f"خطا در محاسبه ظرفیت وام: {str(e)}")
            return 0

    def _get_current_share_price(self):
        try:
            with DatabaseManager() as db:
                base_price = float(db.get_setting("share_price", "2000000"))
                monthly_increase = float(db.get_setting("monthly_increase", "0"))
                start_date_str = db.get_setting("share_price_start_date", None)
                if not start_date_str:
                    return int(base_price)
                start_date = datetime.strptime(start_date_str, "%Y/%m/%d")
                now = datetime.now()
                months_passed = (now.year - start_date.year) * 12 + (now.month - start_date.month)
                current_price = base_price + (monthly_increase * months_passed)
                return int(max(current_price, base_price))
        except Exception as e:
            logging.error(f"خطا در محاسبه قیمت فعلی سهام: {str(e)}")
            return int(float(db.get_setting("share_price", "2000000")))

    def _on_member_double_clicked(self, item):
        member_id = item.data(0, Qt.UserRole)
        self.open_member_tab(member_id)

    def _open_member_by_search(self):
        search_text = self.search_box.text().strip()
        if not search_text:
            return
        try:
            with DatabaseManager() as db:
                member = db.execute_query(
                    "SELECT id FROM members WHERE membership_code=? OR name=?",
                    (search_text, search_text), fetch=True
                )
                if member:
                    self.open_member_tab(member[0][0])
                    self.search_box.clear()
                else:
                    QMessageBox.warning(self, "⚠️ خطا", "عضو با این کد یا نام یافت نشد!")
        except Exception as e:
            logging.error(f"خطا در جستجوی عضو: {str(e)}")
            QMessageBox.critical(self, "❌ خطا", "خطا در جستجوی عضو")

    def open_member_tab(self, member_id):
        if member_id in self.member_tabs:
            self.tabs.setCurrentWidget(self.member_tabs[member_id])
            return
        tab = MemberTab(member_id, self)
        tab.update_parent_report.connect(self.reports_tab.load_data)
        tab.update_parent_all.connect(self._refresh_all)
        with DatabaseManager() as db:
            member_name = db.execute_query(
                "SELECT name FROM members WHERE id=?",
                (member_id,), fetch=True
            )[0][0]
        tab_index = self.tabs.addTab(tab, f"👤 عضو: {member_name}")
        self.tabs.setCurrentIndex(tab_index)
        self.member_tabs[member_id] = tab

    def _add_new_member(self):
        dialog = AddMemberDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.update_all.emit()

    def _show_share_price_dialog(self):
        dialog = SharePriceDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.update_all.emit()

    def _search_members(self):
        search_text = self.search_box.text().strip()
        if not search_text:
            self._load_members()
            return
        query = """
            SELECT id, name, membership_code, phone, account_number, join_date, status 
            FROM members 
            WHERE (name LIKE ? OR membership_code LIKE ? OR phone LIKE ?)
            ORDER BY join_date DESC
        """
        params = (f"%{search_text}%", f"%{search_text}%", f"%{search_text}%")
        try:
            self.members_table.clear()
            with DatabaseManager() as db:
                members = db.execute_query(query, params, fetch=True)
                for idx, member in enumerate(members, 1):
                    item = QTreeWidgetItem(self.members_table)
                    shares = self._calculate_shares(member[0])
                    item.setText(0, str(idx))
                    item.setText(1, member[1])
                    item.setText(2, member[2])
                    item.setText(3, member[3] or "-")
                    item.setText(4, member[4] or "-")
                    item.setText(5, get_persian_date(member[5]))
                    item.setText(6, member[6])
                    item.setText(7, format_persian_number(str(shares)))
                    if member[6] == "غیرفعال":
                        item.setForeground(6, QColor("#D32F2F"))
                    else:
                        item.setForeground(6, QColor("#388E3C"))
                    item.setData(0, Qt.UserRole, member[0])

                    edit_btn = QPushButton("✏️")
                    edit_btn.setStyleSheet(self._get_styles()["edit_button"])
                    edit_btn.clicked.connect(lambda _, mid=member[0]: self._edit_member(mid))
                    self.members_table.setItemWidget(item, 8, edit_btn)
        except Exception as e:
            logging.error(f"خطا در جستجوی اعضا: {str(e)}")
            QMessageBox.critical(self, "❌ خطا", "خطا در انجام جستجو")

    def _initial_load(self):
        self._load_members()
        self._load_transactions()
        self._load_loans()
        self.reports_tab.load_data()
        try:
            current_price = self._get_current_share_price()
            self.share_price_label.setText(f"💰 قیمت سهام: {format_persian_number(str(current_price))} تومان")
        except Exception as e:
            logging.error(f"خطا در به‌روزرسانی قیمت سهام: {str(e)}")
            self.share_price_label.setText("💰 قیمت سهام: نامشخص")

    def _refresh_all(self):
        if self.is_refreshing:
            return
        self.is_refreshing = True
        try:
            self._load_members()
            self._load_transactions()
            self._load_loans()
            self.reports_tab.load_data()
            current_price = self._get_current_share_price()
            self.share_price_label.setText(f"💰 قیمت سهام: {format_persian_number(str(current_price))} تومان")
        except Exception as e:
            logging.error(f"خطا در به‌روزرسانی کامل: {str(e)}")
        finally:
            self.is_refreshing = False

    def close_tab(self, index):
        if index < 4:
            return
        widget = self.tabs.widget(index)
        if hasattr(widget, 'table_changed') and widget.table_changed:
            reply = QMessageBox.question(
                self, "⚠️ تغییرات ذخیره نشده",
                "تغییرات ذخیره نشده‌ای وجود دارد. آیا مایل به بستن هستید؟",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        for member_id, tab in list(self.member_tabs.items()):
            if tab == widget:
                del self.member_tabs[member_id]
                break
        self.tabs.removeTab(index)

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, "❌ خروج از برنامه",
            "آیا از خروج از برنامه اطمینان دارید؟",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    font = QFont("B Nazanin", 12)
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())