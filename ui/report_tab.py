# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, QLabel, QPushButton, QDialog, QLineEdit, QHeaderView, QMessageBox, QFrame
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from core.database import DatabaseManager
from core.utils import format_persian_number, get_persian_date
import logging

class FundBalanceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("💰 موجودی صندوق")
        self.setMinimumWidth(400)
        self.setStyleSheet("background: #F5F5F5; border-radius: 8px;")
        self.parent = parent
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        self.table = QTreeWidget()
        self.table.setHeaderLabels(["🏦 نام بانک", "💵 مبلغ"])
        self.table.header().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("""
            QTreeWidget {
                font-family: 'B Nazanin';
                font-size: 14px;
                border: 1px solid #E0E0E0;
            }
            QHeaderView::section {
                background-color: #1976D2;
                color: white;
                padding: 5px;
            }
        """)
        layout.addWidget(self.table)

        self._load_existing_data()

        btn_layout = QHBoxLayout()
        add_row_btn = QPushButton("➕ افزودن ردیف")
        add_row_btn.setStyleSheet("""
            QPushButton {
                background: #388E3C;
                color: white;
                font-family: 'B Nazanin';
                font-size: 14px;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover { background: #2E7D32; }
        """)
        add_row_btn.clicked.connect(self.add_row)

        delete_row_btn = QPushButton("🗑️ حذف ردیف")
        delete_row_btn.setStyleSheet("""
            QPushButton {
                background: #D32F2F;
                color: white;
                font-family: 'B Nazanin';
                font-size: 14px;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover { background: #C62828; }
        """)
        delete_row_btn.clicked.connect(self.delete_row)

        save_btn = QPushButton("💾 ذخیره")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #1976D2;
                color: white;
                font-family: 'B Nazanin';
                font-size: 14px;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover { background: #1565C0; }
        """)
        save_btn.clicked.connect(self.save_balance)

        btn_layout.addWidget(add_row_btn)
        btn_layout.addWidget(delete_row_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _load_existing_data(self):
        try:
            with DatabaseManager() as db:
                balances = db.execute_query("SELECT bank_name, amount FROM fund_balances", fetch=True)
                self.table.clear()
                for bank, amount in balances:
                    item = QTreeWidgetItem(self.table)
                    item.setText(0, bank)
                    item.setText(1, format_persian_number(str(amount)))  # عدد اعشاری هم نگه می‌داره
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
        except Exception as e:
            logging.error(f"خطا در بارگذاری موجودی‌های صندوق: {str(e)}")

    def add_row(self):
        item = QTreeWidgetItem(self.table)
        item.setText(0, "")
        item.setText(1, "0")
        item.setFlags(item.flags() | Qt.ItemIsEditable)

    def delete_row(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "⚠️ خطا", "لطفاً یک ردیف را انتخاب کنید!")
            return
        for item in selected_items:
            self.table.takeTopLevelItem(self.table.indexOfTopLevelItem(item))

    def save_balance(self):
        total = 0
        balances = []
        for i in range(self.table.topLevelItemCount()):
            item = self.table.topLevelItem(i)
            bank = item.text(0).strip()
            amount_text = item.text(1).strip().replace('٬', '')
            if not bank or not amount_text:
                QMessageBox.warning(self, "⚠️ خطا", "نام بانک و مبلغ نمی‌توانند خالی باشند!")
                return
            try:
                amount = float(amount_text)
                total += amount
                balances.append((bank, amount))
            except ValueError:
                QMessageBox.warning(self, "⚠️ خطا", "مبلغ باید عدد باشد!")
                return
        try:
            with DatabaseManager() as db:
                db.execute_query("DROP TABLE IF EXISTS fund_balances")
                db.execute_query("""
                    CREATE TABLE IF NOT EXISTS fund_balances (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        bank_name TEXT NOT NULL,
                        amount REAL NOT NULL
                    )
                """)
                for bank, amount in balances:
                    db.execute_query("INSERT INTO fund_balances (bank_name, amount) VALUES (?, ?)", (bank, amount))
                db.set_setting("fund_balance", str(total), "موجودی صندوق")
            QMessageBox.information(self, "✅ موفق", f"موجودی صندوق: {format_persian_number(str(total))} تومان")
            self.parent.load_data()
            self.accept()
        except Exception as e:
            logging.error(f"خطا در ذخیره موجودی صندوق: {str(e)}")
            QMessageBox.critical(self, "❌ خطا", f"خطا در ذخیره:\n{str(e)}")

class ReportTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        self.members_table = QTreeWidget()
        self.members_table.setHeaderLabels([
            "🔢 شماره", "👤 نام عضو", "📌 کد عضویت", "🏦 دارایی", "⚠️ مانده", "💵 اقساط"
        ])
        self.members_table.setStyleSheet("""
            QTreeWidget {
                font-family: 'B Nazanin';
                font-size: 14px;
                alternate-background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
            }
            QTreeWidget::item {
                padding: 10px;
                height: 40px;
                border-bottom: 1px solid #EEEEEE;
            }
            QHeaderView::section {
                background-color: #1976D2;
                color: white;
                padding: 5px;
            }
        """)
        self.members_table.setColumnWidth(0, 80)
        self.members_table.setColumnWidth(1, 200)
        self.members_table.setColumnWidth(3, 150)
        self.members_table.setColumnWidth(4, 150)
        self.members_table.setColumnWidth(5, 150)
        self.members_table.itemDoubleClicked.connect(self._on_member_double_clicked)  # اتصال دابل‌کلیک
        layout.addWidget(self.members_table)

        summary_frame = QFrame()
        summary_frame.setStyleSheet("background: #E8F5E9; border-radius: 6px; padding: 10px;")
        summary_layout = QVBoxLayout(summary_frame)

        row1_frame = QFrame()
        row1_frame.setStyleSheet("border: 1px solid #388E3C; border-radius: 4px; padding: 5px;")
        row1_layout = QHBoxLayout(row1_frame)
        self.total_assets_label = QLabel("📊 کل موجودی اعضا: -")
        self.total_loans_label = QLabel("🏦 کل وام پرداختی: -")
        self.total_installments_label = QLabel("💵 اقساط پرداخت‌شده: -")
        for label in (self.total_assets_label, self.total_loans_label, self.total_installments_label):
            label.setStyleSheet("font-family: 'B Nazanin'; font-size: 16px; font-weight: bold; color: #388E3C;")
            row1_layout.addWidget(label)
        summary_layout.addWidget(row1_frame)

        row2_frame = QFrame()
        row2_frame.setStyleSheet("border: 1px solid #388E3C; border-radius: 4px; padding: 5px;")
        row2_layout = QHBoxLayout(row2_frame)
        self.total_debt_label = QLabel("⚠️ مانده قابل پرداخت: -")
        self.balance_diff_label = QLabel("🔄 اختلاف حساب: -")
        self.fund_balance_label = QLabel("💰 موجودی صندوق: -")
        for label in (self.total_debt_label, self.balance_diff_label, self.fund_balance_label):
            label.setStyleSheet("font-family: 'B Nazanin'; font-size: 16px; font-weight: bold; color: #388E3C;")
            row2_layout.addWidget(label)
        summary_layout.addWidget(row2_frame)

        buttons_layout = QHBoxLayout()
        fund_btn = QPushButton("💰 موجودی صندوق")
        fund_btn.setStyleSheet("""
            QPushButton {
                background: #0288D1;
                color: white;
                font-family: 'B Nazanin';
                font-size: 14px;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover { background: #0277BD; }
        """)
        fund_btn.clicked.connect(self.show_fund_balance)
        refresh_btn = QPushButton("🔄 بروزرسانی")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #607D8B;
                color: white;
                font-family: 'B Nazanin';
                font-size: 14px;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover { background: #455A64; }
        """)
        refresh_btn.clicked.connect(self.load_data)
        buttons_layout.addStretch()
        buttons_layout.addWidget(fund_btn)
        buttons_layout.addWidget(refresh_btn)
        summary_layout.addLayout(buttons_layout)

        layout.addWidget(summary_frame)

    def load_data(self):
        try:
            with DatabaseManager() as db:
                members = db.execute_query("SELECT id, name, membership_code FROM members", fetch=True)
                self.members_table.clear()
                total_assets = total_loans = total_installments = 0

                for idx, (member_id, name, code) in enumerate(members, 1):
                    assets = float(db.execute_query(
                        "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE member_id=? AND type='عضویت'",
                        (member_id,), fetch=True)[0][0])
                    loans = float(db.execute_query(
                        "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE member_id=? AND type='وام'",
                        (member_id,), fetch=True)[0][0])
                    installments = float(db.execute_query(
                        "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE member_id=? AND type='پرداخت'",
                        (member_id,), fetch=True)[0][0])
                    debt = max(0, loans - installments)

                    item = QTreeWidgetItem(self.members_table)
                    item.setText(0, str(idx))
                    item.setText(1, name)
                    item.setText(2, code)
                    item.setText(3, format_persian_number(str(assets)))
                    item.setText(4, format_persian_number(str(debt)))
                    item.setText(5, format_persian_number(str(installments)))
                    item.setData(0, Qt.UserRole, member_id)  # ذخیره member_id برای دابل‌کلیک

                    total_assets += assets
                    total_loans += loans
                    total_installments += installments

                total_debt = total_loans - total_installments
                fund_balance = float(db.get_setting("fund_balance", "0"))
                balance_diff = total_debt - total_assets - fund_balance  # اصلاح منطق

                self.total_assets_label.setText(f"📊 کل موجودی اعضا: {format_persian_number(str(total_assets))} تومان")
                self.total_loans_label.setText(f"🏦 کل وام پرداختی: {format_persian_number(str(total_loans))} تومان")
                self.total_installments_label.setText(f"💵 اقساط پرداخت‌شده: {format_persian_number(str(total_installments))} تومان")
                self.total_debt_label.setText(f"⚠️ مانده قابل پرداخت: {format_persian_number(str(total_debt))} تومان")
                self.balance_diff_label.setText(f"🔄 اختلاف حساب: {format_persian_number(str(balance_diff))} تومان")
                self.fund_balance_label.setText(f"💰 موجودی صندوق: {format_persian_number(str(fund_balance))} تومان")

                if hasattr(self.parent, 'update_all'):
                    self.parent.update_all.emit()
        except Exception as e:
            logging.error(f"خطا در بارگذاری گزارشات: {str(e)}")
            QMessageBox.critical(self, "❌ خطا", f"خطا در بارگذاری گزارشات:\n{str(e)}")

    def _on_member_double_clicked(self, item, column):
        member_id = item.data(0, Qt.UserRole)
        if member_id and hasattr(self.parent, 'open_member_tab'):
            self.parent.open_member_tab(member_id)

    def show_fund_balance(self):
        dialog = FundBalanceDialog(self)
        dialog.exec_()