# -*- coding: utf-8 -*-
"""تب اطلاعات اعضا با چیدمان پیشرفته و قابلیت‌های کامل"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QTextEdit, QLabel, QMessageBox, 
    QComboBox, QFrame, QLineEdit, QStyledItemDelegate, 
    QMenu, QDialog, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QFont
from core.database import DatabaseManager
from core.config import AppConfig, BACKUP_DIR
from core.utils import format_persian_number, get_persian_date, calculate_loan_capacity, validate_phone_number
import logging
from datetime import datetime
import os

class PersianNumberDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        value = index.data()
        text = format_persian_number(value)  # مستقیم از utils استفاده می‌کنیم
        try:
            float_value = float(value.replace('٬', '')) if value else 0
            text = "۰" if float_value == 0 else format_persian_number(str(int(float_value) if float_value.is_integer() else float_value))
        except (ValueError, TypeError):
            text = "۰" if not value else str(value)
        option.text = text
        option.displayAlignment = Qt.AlignCenter | Qt.AlignVCenter
        option.font = QFont("B Nazanin", 14, QFont.Bold)
        super().paint(painter, option, index)

class MemberTab(QWidget):
    update_parent_report = pyqtSignal()
    update_parent_all = pyqtSignal()
    table_changed = False

    def __init__(self, member_id, parent=None):
        super().__init__(parent)
        self.member_id = member_id
        self.current_year = get_persian_date().split('/')[0]
        self.edit_mode = False
        self.notes_visible = True
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self.auto_save_check)
        self.auto_save_timer.start(30000)
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # ======= ستون چپ (یادداشت‌ها و وام قابل دریافت) =======
        left_column = QFrame()
        left_column.setFrameShape(QFrame.StyledPanel)
        left_column.setStyleSheet("background: #F5F5F5; border-radius: 8px;")
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(10, 10, 10, 10)

        notes_header = QHBoxLayout()
        self.toggle_notes_btn = QPushButton("📝 مخفی کردن یادداشت‌ها")
        self.toggle_notes_btn.setStyleSheet("""
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
        self.toggle_notes_btn.clicked.connect(self.toggle_notes)
        notes_header.addWidget(self.toggle_notes_btn)

        self.note_search = QLineEdit()
        self.note_search.setPlaceholderText("🔍 جستجو در یادداشت‌ها...")
        self.note_search.setStyleSheet("""
            QLineEdit {
                font-family: 'B Nazanin';
                font-size: 14px;
                padding: 8px;
                border: 1px solid #BDBDBD;
                border-radius: 4px;
            }
        """)
        self.note_search.textChanged.connect(self.filter_notes)
        notes_header.addWidget(self.note_search)

        left_layout.addLayout(notes_header)

        self.notes_table = QTableWidget(0, 3)
        self.notes_table.setHorizontalHeaderLabels(["📅 تاریخ", "📝 یادداشت", "❌ حذف"])
        self.notes_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.notes_table.setColumnWidth(0, 120)
        self.notes_table.setColumnWidth(2, 60)
        self.notes_table.setStyleSheet("""
            QTableWidget {
                font-family: 'B Nazanin';
                font-size: 14px;
                border: none;
                background: white;
                border-radius: 5px;
            }
            QHeaderView::section {
                background-color: #1976D2;
                color: white;
                padding: 5px;
            }
        """)
        self.notes_table.itemClicked.connect(self.show_note_cell_info)
        left_layout.addWidget(self.notes_table)

        # وام قابل دریافت
        loan_capacity_frame = QFrame()
        loan_capacity_frame.setStyleSheet("background: #C8E6C9; border-radius: 4px; padding: 5px;")
        loan_capacity_frame.setMinimumHeight(50)  # تغییر این مقدار برای تنظیم ارتفاع
        loan_capacity_layout = QHBoxLayout(loan_capacity_frame)
        self.loan_capacity_label = QLabel("🏦 وام قابل دریافت: -")
        self.loan_capacity_label.setStyleSheet("""
            QLabel {
                font-family: 'B Nazanin';
                font-size: 16px;
                font-weight: bold;
                color: #0288D1;
            }
        """)
        loan_capacity_layout.addWidget(self.loan_capacity_label)
        left_layout.addWidget(loan_capacity_frame)

        main_layout.addWidget(left_column, 1)

        # ======= ستون راست (اطلاعات اصلی) =======
        right_column = QFrame()
        right_column.setFrameShape(QFrame.StyledPanel)
        right_column.setStyleSheet("background: #FFFFFF; border-radius: 8px;")
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(15, 15, 15, 15)

        # ===== بخش اطلاعات فردی =====
        personal_info_frame = QFrame()
        personal_info_frame.setStyleSheet("background: #E3F2FD; border-radius: 6px; padding: 5px;")
        personal_info_layout = QVBoxLayout(personal_info_frame)

        top_row = QHBoxLayout()
        shares_phone_layout = QVBoxLayout()
        self.shares_label = QLabel("📊 سهام: -")
        self.shares_label.setStyleSheet("""
            QLabel {
                font-family: 'B Nazanin';
                font-size: 18px;
                font-weight: bold;
                color: #1976D2;
            }
        """)
        shares_phone_layout.addWidget(self.shares_label, alignment=Qt.AlignLeft)

        self.phone_label = QLabel("📞 تلفن: -")
        self.phone_label.setStyleSheet("""
            QLabel {
                font-family: 'B Nazanin';
                font-size: 16px;
                color: #388E3C;
                padding-top: 5px;
            }
        """)
        shares_phone_layout.addWidget(self.phone_label, alignment=Qt.AlignLeft)
        top_row.addLayout(shares_phone_layout, 1)

        self.code_label = QLabel("-")
        self.code_label.setStyleSheet("""
            QLabel {
                font-family: 'B Nazanin';
                font-size: 20px;
                font-weight: bold;
                color: #1976D2;
                border: 1px solid #1976D2;
                border-radius: 20px;
                padding: 5px 10px;
                background: #E3F2FD;
            }
        """)
        top_row.addWidget(self.code_label, 1, Qt.AlignCenter)

        name_account_layout = QVBoxLayout()
        self.name_label = QLabel("👤 نام: -")
        self.name_label.setStyleSheet("""
            QLabel {
                font-family: 'B Nazanin';
                font-size: 18px;
                font-weight: bold;
                color: #1976D2;
            }
        """)
        name_account_layout.addWidget(self.name_label, alignment=Qt.AlignRight)

        self.account_label = QLabel("💳 حساب: -")
        self.account_label.setStyleSheet("""
            QLabel {
                font-family: 'B Nazanin';
                font-size: 16px;
                color: #388E3C;
                padding-top: 5px;
            }
        """)
        name_account_layout.addWidget(self.account_label, alignment=Qt.AlignRight)
        top_row.addLayout(name_account_layout, 1)

        personal_info_layout.addLayout(top_row)
        right_layout.addWidget(personal_info_frame)

        # ===== بخش انتخاب سال و دکمه‌ها =====
        year_save_layout = QHBoxLayout()
        year_layout = QHBoxLayout()
        year_layout.addWidget(QLabel("📅 سال:"))
        self.year_combo = QComboBox()
        self.year_combo.addItems([str(year) for year in range(1390, 1501)])
        self.year_combo.setCurrentText(self.current_year)
        self.year_combo.currentTextChanged.connect(self.load_transactions_for_year)
        self.year_combo.setStyleSheet("""
            QComboBox {
                font-family: 'B Nazanin';
                font-size: 14px;
                padding: 5px;
                min-width: 100px;
            }
        """)
        year_layout.addWidget(self.year_combo)
        year_save_layout.addLayout(year_layout)

        year_save_layout.addStretch()

        self.calculator_btn = QPushButton("🖩 ماشین‌حساب")
        self.calculator_btn.setStyleSheet("""
            QPushButton {
                background: #0288D1;
                color: white;
                font-family: 'B Nazanin';
                font-size: 14px;
                padding: 8px;
                border-radius: 4px;
                min-width: 120px;
            }
            QPushButton:hover { background: #0277BD; }
        """)
        self.calculator_btn.clicked.connect(self.open_calculator)
        year_save_layout.addWidget(self.calculator_btn)

        self.save_btn = QPushButton("💾 ذخیره تغییرات")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background: #388E3C;
                color: white;
                font-family: 'B Nazanin';
                font-size: 14px;
                padding: 8px 15px;
                border-radius: 4px;
                min-width: 120px;
            }
            QPushButton:hover { background: #2E7D32; }
        """)
        self.save_btn.clicked.connect(self.save_table_data)
        year_save_layout.addWidget(self.save_btn)

        right_layout.addLayout(year_save_layout)

        # ===== جدول تراکنش‌ها (فقط 12 ماه) =====
        self.transactions_table = QTableWidget(12, 4)
        self.transactions_table.setHorizontalHeaderLabels(["💵 قسط", "🏦 وام", "📊 عضویت", "📅 تاریخ"])
        self.transactions_table.setItemDelegate(PersianNumberDelegate(self))
        self.transactions_table.setEditTriggers(QTableWidget.AnyKeyPressed | QTableWidget.SelectedClicked)
        self.transactions_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.transactions_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.transactions_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.transactions_table.setColumnWidth(3, 150)
        self.transactions_table.verticalHeader().setVisible(False)
        self.transactions_table.cellChanged.connect(self.update_balance)
        self.transactions_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.transactions_table.customContextMenuRequested.connect(self.show_context_menu)
        self.transactions_table.setStyleSheet("""
            QTableWidget {
                font-family: 'B Nazanin';
                font-size: 14px;
                gridline-color: #E0E0E0;
                border: 1px solid #E0E0E0;
                border-radius: 5px;
            }
            QHeaderView::section {
                background-color: #1976D2;
                color: white;
                padding: 5px;
                font-weight: bold;
                border: none;
            }
        """)
        right_layout.addWidget(self.transactions_table, stretch=2)

        # ===== جمع کل (زیر جدول) =====
        total_frame = QFrame()
        total_frame.setStyleSheet("background: #1976D2; border-radius: 4px; padding: 2px;")
        total_frame.setFixedHeight(60)  # ارتفاع 60px
        total_layout = QHBoxLayout(total_frame)

        # مقادیر زیر ستون‌ها
        self.total_installment_label = QLabel("۰")
        self.total_installment_label.setStyleSheet("font-family: 'B Nazanin'; font-size: 16px; font-weight: bold; color: white;")
        total_layout.addWidget(self.total_installment_label, stretch=1)

        self.total_loan_label = QLabel("۰")
        self.total_loan_label.setStyleSheet("font-family: 'B Nazanin'; font-size: 16px; font-weight: bold; color: white;")
        total_layout.addWidget(self.total_loan_label, stretch=1)

        self.total_membership_label = QLabel("۰")
        self.total_membership_label.setStyleSheet("font-family: 'B Nazanin'; font-size: 16px; font-weight: bold; color: white;")
        total_layout.addWidget(self.total_membership_label, stretch=1)

        self.total_title_label = QLabel("جمع کل")
        self.total_title_label.setStyleSheet("font-family: 'B Nazanin'; font-size: 16px; font-weight: bold; color: white;")
        self.total_title_label.setFixedWidth(150)  # هم‌راستا با ستون تاریخ
        total_layout.addWidget(self.total_title_label)

        right_layout.addWidget(total_frame)

        # ===== بخش پایین (مانده و دکمه‌ها) =====
        bottom_frame = QFrame()
        bottom_frame.setStyleSheet("background: #E8F5E9; border-radius: 6px; padding: 10px;")
        bottom_layout = QVBoxLayout(bottom_frame)

        balance_frame = QFrame()
        balance_frame.setStyleSheet("background: #C8E6C9; border-radius: 4px; padding: 5px;")
        balance_layout = QHBoxLayout(balance_frame)
        self.balance_label = QLabel("💰 مانده: -")
        self.balance_label.setStyleSheet("""
            QLabel {
                font-family: 'B Nazanin';
                font-size: 16px;
                font-weight: bold;
                color: #388E3C;
            }
        """)
        balance_layout.addWidget(self.balance_label)
        bottom_layout.addWidget(balance_frame)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.edit_btn = QPushButton("✏️ ویرایش اطلاعات")
        self.edit_btn.setStyleSheet("""
            QPushButton {
                background: #1976D2;
                color: white;
                font-family: 'B Nazanin';
                font-size: 14px;
                padding: 8px;
                border-radius: 4px;
                min-width: 120px;
            }
            QPushButton:hover { background: #1565C0; }
        """)
        self.edit_btn.clicked.connect(self.toggle_edit)
        btn_layout.addWidget(self.edit_btn)

        self.show_balance_btn = QPushButton("📈 نمایش حساب")
        self.show_balance_btn.setStyleSheet("""
            QPushButton {
                background: #0288D1;
                color: white;
                font-family: 'B Nazanin';
                font-size: 14px;
                padding: 8px;
                border-radius: 4px;
                min-width: 120px;
            }
            QPushButton:hover { background: #0277BD; }
        """)
        self.show_balance_btn.clicked.connect(self.show_balance_details)
        btn_layout.addWidget(self.show_balance_btn)

        self.export_btn = QPushButton("📤 خروجی")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background: #1976D2;
                color: white;
                font-family: 'B Nazanin';
                font-size: 14px;
                padding: 8px;
                border-radius: 4px;
                min-width: 120px;
            }
            QPushButton:hover { background: #1565C0; }
        """)
        self.export_btn.clicked.connect(self.export_data)
        btn_layout.addWidget(self.export_btn)

        bottom_layout.addLayout(btn_layout)
        right_layout.addWidget(bottom_frame)

        main_layout.addWidget(right_column, 2)

    def toggle_notes(self):
        self.notes_visible = not self.notes_visible
        for row in range(self.notes_table.rowCount()):
            self.notes_table.setRowHidden(row, not self.notes_visible)
        self.toggle_notes_btn.setText("📝 نمایش یادداشت‌ها" if not self.notes_visible else "📝 مخفی کردن یادداشت‌ها")

    def load_data(self):
        try:
            with DatabaseManager() as db:
                member = db.execute_query(
                    "SELECT name, membership_code, phone, account_number, status FROM members WHERE id=?",
                    (self.member_id,),
                    fetch=True
                )[0]
                membership_amount = float(db.execute_query(
                    "SELECT SUM(amount) FROM transactions WHERE member_id=? AND type='عضویت'",
                    (self.member_id,),
                    fetch=True
                )[0][0] or 0)
                share_price = float(self.parent()._get_current_share_price())
                shares = membership_amount / share_price if share_price > 0 else 0
                shares_text = str(int(shares)) if shares.is_integer() else f"{shares:.2f}"

                self.name_label.setText(f"👤 نام: {member[0]}")
                self.code_label.setText(f"{member[1]}")
                self.shares_label.setText(f"📊 سهام: {format_persian_number(shares_text)} واحد")
                self.phone_label.setText(f"📞 تلفن: {member[2] or '-'}")
                self.account_label.setText(f"💳 حساب: {member[3] or '-'}")

                status_color = "#D32F2F" if member[4] == "غیرفعال" else "#388E3C"
                self.name_label.setStyleSheet(f"font-family: 'B Nazanin'; font-size: 18px; font-weight: bold; color: {status_color};")

                loan_capacity = calculate_loan_capacity(self.member_id)
                self.loan_capacity_label.setText(f"🏦 وام قابل دریافت: {format_persian_number(str(loan_capacity))} تومان")

                saved_year = db.get_setting(f"last_year_member_{self.member_id}", self.current_year)
                self.year_combo.setCurrentText(saved_year)
                self.load_transactions_for_year(saved_year)
                self.load_notes()

            self.table_changed = False
        except Exception as e:
            logging.error(f"خطا در بارگذاری اطلاعات عضو {self.member_id}: {str(e)}")
            QMessageBox.critical(self, "❌ خطا", f"خطا در بارگذاری اطلاعات:\n{str(e)}")

    def load_transactions_for_year(self, year):
        try:
            with DatabaseManager() as db:
                self.transactions_table.blockSignals(True)
                self.transactions_table.clearContents()
                total_membership = total_loan = total_installment = 0.0

                total_loan_all = float(db.execute_query(
                    "SELECT SUM(amount) FROM transactions WHERE member_id=? AND type='وام'",
                    (self.member_id,),
                    fetch=True
                )[0][0] or 0)
                total_installment_all = float(db.execute_query(
                    "SELECT SUM(amount) FROM transactions WHERE member_id=? AND type='پرداخت'",
                    (self.member_id,),
                    fetch=True
                )[0][0] or 0)
                total_membership_all = float(db.execute_query(
                    "SELECT SUM(amount) FROM transactions WHERE member_id=? AND type='عضویت'",
                    (self.member_id,),
                    fetch=True
                )[0][0] or 0)

                for row in range(12):
                    month = f"{year}/{str(row + 1).zfill(2)}"
                    date_item = QTableWidgetItem(month)
                    date_item.setFlags(Qt.ItemIsEnabled)
                    self.transactions_table.setItem(row, 3, date_item)

                    for col, type_ in enumerate(["پرداخت", "وام", "عضویت"]):
                        amount_result = db.execute_query(
                            "SELECT SUM(amount) FROM transactions WHERE member_id=? AND date LIKE ? AND type=?",
                            (self.member_id, f"{month}%", type_),
                            fetch=True
                        )
                        amount = amount_result[0][0] if amount_result and amount_result[0][0] is not None else 0.0
                        item = QTableWidgetItem(str(amount))
                        if col == 1 and amount > 0:
                            item.setForeground(QColor("#D32F2F"))
                        self.transactions_table.setItem(row, col, item)

                        if col == 2:
                            total_membership += amount
                        elif col == 1:
                            total_loan += amount
                        else:
                            total_installment += amount

                self.total_installment_label.setText(format_persian_number(str(total_installment_all)))
                self.total_loan_label.setText(format_persian_number(str(total_loan_all)))
                self.total_membership_label.setText(format_persian_number(str(total_membership_all)))

                balance = total_loan_all - total_installment_all
                self.balance_label.setText(f"💰 مانده: {format_persian_number(str(balance))} تومان")

                if total_loan_all > 0 and total_loan_all == total_installment_all:
                    for row in range(11, -1, -1):
                        installment_item = self.transactions_table.item(row, 0)
                        if installment_item and float(installment_item.text()) > 0:
                            installment_item.setBackground(QColor("#C8E6C9"))
                            break

                self.transactions_table.blockSignals(False)
                self.load_notes()
        except Exception as e:
            logging.error(f"خطا در بارگذاری تراکنش‌های سال {year}: {str(e)}")
            QMessageBox.critical(self, "❌ خطا", f"خطا در بارگذاری تراکنش‌ها:\n{str(e)}")

    def save_table_data(self):
        try:
            year = self.year_combo.currentText()
            with DatabaseManager() as db:
                db.execute_query("DELETE FROM transactions WHERE member_id=? AND date LIKE ?", (self.member_id, f"{year}/%"), fetch=False)
                total_loan = total_installment = total_membership = 0.0
                for row in range(12):
                    month = f"{year}/{str(row + 1).zfill(2)}"
                    for col, type_ in enumerate(["پرداخت", "وام", "عضویت"]):
                        item = self.transactions_table.item(row, col)
                        amount = float(item.text().replace('٬', '')) if item and item.text() else 0.0
                        if amount:
                            db.execute_query(
                                "INSERT INTO transactions (member_id, date, amount, type, description) VALUES (?, ?, ?, ?, 'ثبت از تب عضو')",
                                (self.member_id, f"{month}/01", amount, type_),
                                fetch=False
                            )
                        if col == 1:
                            total_loan += amount
                        elif col == 0:
                            total_installment += amount
                        else:
                            total_membership += amount

                total_loan_all = float(db.execute_query(
                    "SELECT SUM(amount) FROM transactions WHERE member_id=? AND type='وام'",
                    (self.member_id,),
                    fetch=True
                )[0][0] or 0)
                total_installment_all = float(db.execute_query(
                    "SELECT SUM(amount) FROM transactions WHERE member_id=? AND type='پرداخت'",
                    (self.member_id,),
                    fetch=True
                )[0][0] or 0)
                total_membership_all = float(db.execute_query(
                    "SELECT SUM(amount) FROM transactions WHERE member_id=? AND type='عضویت'",
                    (self.member_id,),
                    fetch=True
                )[0][0] or 0)

                balance = total_loan_all - total_installment_all
                db.set_setting(f"balance_{self.member_id}_{year}", str(balance), f"مانده سال {year} برای عضو {self.member_id}")
                db.set_setting(f"last_year_member_{self.member_id}", year, f"آخرین سال انتخاب‌شده برای عضو {self.member_id}")
                backup_path = BACKUP_DIR / f"transactions_{self.member_id}_{year}.bak"
                db.backup_db(str(backup_path))

                self.total_installment_label.setText(format_persian_number(str(total_installment_all)))
                self.total_loan_label.setText(format_persian_number(str(total_loan_all)))
                self.total_membership_label.setText(format_persian_number(str(total_membership_all)))
                self.balance_label.setText(f"💰 مانده: {format_persian_number(str(balance))} تومان")

                self.table_changed = False
                self.update_parent_report.emit()
                self.update_parent_all.emit()
                QMessageBox.information(self, "✅ موفق", "تغییرات با موفقیت ذخیره شد!")
            return True
        except Exception as e:
            logging.error(f"خطا در ذخیره اطلاعات تب عضو {self.member_id}: {str(e)}")
            QMessageBox.critical(self, "❌ خطا", f"خطا در ذخیره اطلاعات:\n{str(e)}")
            return False

    def update_balance(self, row, col):
        if col == 3:
            return
        try:
            self.transactions_table.blockSignals(True)
            item = self.transactions_table.item(row, col)
            if not item:
                return
            value = float(item.text().replace('٬', '')) if item.text() else 0.0
            if value < 0:
                QMessageBox.warning(self, "⚠️ خطا", "مقدار نمی‌تواند منفی باشد!")
                self.load_transactions_for_year(self.year_combo.currentText())
                return
            new_item = QTableWidgetItem(str(value))
            if col == 1:
                new_item.setForeground(QColor("#D32F2F" if value > 0 else "#388E3C"))
            self.transactions_table.setItem(row, col, new_item)

            with DatabaseManager() as db:
                total_loan_all = float(db.execute_query(
                    "SELECT SUM(amount) FROM transactions WHERE member_id=? AND type='وام'",
                    (self.member_id,),
                    fetch=True
                )[0][0] or 0)
                total_installment_all = float(db.execute_query(
                    "SELECT SUM(amount) FROM transactions WHERE member_id=? AND type='پرداخت'",
                    (self.member_id,),
                    fetch=True
                )[0][0] or 0)
                total_membership_all = float(db.execute_query(
                    "SELECT SUM(amount) FROM transactions WHERE member_id=? AND type='عضویت'",
                    (self.member_id,),
                    fetch=True
                )[0][0] or 0)

            self.total_installment_label.setText(format_persian_number(str(total_installment_all)))
            self.total_loan_label.setText(format_persian_number(str(total_loan_all)))
            self.total_membership_label.setText(format_persian_number(str(total_membership_all)))

            balance = total_loan_all - total_installment_all
            self.balance_label.setText(f"💰 مانده: {format_persian_number(str(balance))} تومان")

            if total_loan_all > 0 and total_loan_all == total_installment_all:
                new_item.setBackground(QColor("#C8E6C9"))

            self.table_changed = True
            self.transactions_table.blockSignals(False)
        except Exception as e:
            logging.error(f"خطا در به‌روزرسانی مانده: {str(e)}")
            self.transactions_table.blockSignals(False)

    def toggle_edit(self):
        self.edit_mode = not self.edit_mode
        if self.edit_mode:
            self.edit_btn.setText("💾 ذخیره اطلاعات")
            self.edit_btn.setStyleSheet("""
                QPushButton {
                    background: #388E3C;
                    color: white;
                    font-family: 'B Nazanin';
                    font-size: 14px;
                    padding: 8px;
                    border-radius: 4px;
                    min-width: 120px;
                }
                QPushButton:hover { background: #2E7D32; }
            """)
            self.show_edit_dialog()
        else:
            self.edit_btn.setText("✏️ ویرایش اطلاعات")
            self.edit_btn.setStyleSheet("""
                QPushButton {
                    background: #1976D2;
                    color: white;
                    font-family: 'B Nazanin';
                    font-size: 14px;
                    padding: 8px;
                    border-radius: 4px;
                    min-width: 120px;
                }
                QPushButton:hover { background: #1565C0; }
            """)

    def show_edit_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("✏️ ویرایش اطلاعات")
        layout = QVBoxLayout(dialog)

        phone_input = QLineEdit(self.phone_label.text().replace("📞 تلفن: ", ""))
        account_input = QLineEdit(self.account_label.text().replace("💳 حساب: ", ""))
        for input_field in (phone_input, account_input):
            input_field.setStyleSheet("padding: 8px; border: 1px solid #BDBDBD; border-radius: 4px;")

        layout.addWidget(QLabel("📞 تلفن:"))
        layout.addWidget(phone_input)
        layout.addWidget(QLabel("💳 شماره حساب:"))
        layout.addWidget(account_input)

        save_btn = QPushButton("💾 ذخیره")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #388E3C;
                color: white;
                padding: 8px;
                font-size: 14px;
                border-radius: 4px;
            }
            QPushButton:hover { background: #2E7D32; }
        """)
        save_btn.clicked.connect(lambda: self.save_edit(dialog, phone_input, account_input))
        layout.addWidget(save_btn)

        dialog.exec_()

    def save_edit(self, dialog, phone_input, account_input):
        phone = phone_input.text().strip()
        account = account_input.text().strip()
        if phone and not validate_phone_number(phone):
            QMessageBox.warning(self, "⚠️ خطا", "شماره تلفن نامعتبر است!")
            return
        try:
            with DatabaseManager() as db:
                db.execute_query("UPDATE members SET phone=?, account_number=? WHERE id=?", (phone, account, self.member_id), fetch=False)
                backup_path = BACKUP_DIR / f"member_{self.member_id}_{get_persian_date().replace('/', '_')}.bak"
                db.backup_db(str(backup_path))
            self.phone_label.setText(f"📞 تلفن: {phone or '-'}")
            self.account_label.setText(f"💳 حساب: {account or '-'}")
            dialog.accept()
            QMessageBox.information(self, "✅ موفق", "اطلاعات با موفقیت ذخیره شد!")
            self.toggle_edit()
        except Exception as e:
            logging.error(f"خطا در ذخیره ویرایش عضو {self.member_id}: {str(e)}")
            QMessageBox.critical(self, "❌ خطا", f"خطا در ذخیره:\n{str(e)}")

    def load_notes(self):
        try:
            year = self.year_combo.currentText()
            with DatabaseManager() as db:
                notes = db.execute_query(
                    "SELECT id, note, date, linked_cell FROM notes WHERE member_id=? AND date LIKE ? ORDER BY date DESC",
                    (self.member_id, f"{year}/%"),
                    fetch=True
                )
                self.notes_table.setRowCount(len(notes))
                for row, (note_id, note_text, note_date, linked_cell) in enumerate(notes):
                    self.notes_table.setItem(row, 0, QTableWidgetItem(note_date))
                    note_item = QTableWidgetItem(note_text)
                    note_item.setData(Qt.UserRole, note_id)
                    note_item.setData(Qt.UserRole + 1, linked_cell)
                    self.notes_table.setItem(row, 1, note_item)
                    delete_btn = QPushButton("❌")
                    delete_btn.setStyleSheet("""
                        QPushButton {
                            background: #D32F2F;
                            color: white;
                            padding: 3px;
                            border-radius: 3px;
                            min-width: 25px;
                            max-width: 25px;
                        }
                        QPushButton:hover { background: #B71C1C; }
                    """)
                    delete_btn.clicked.connect(lambda _, nid=note_id: self.delete_note(nid))
                    self.notes_table.setCellWidget(row, 2, delete_btn)
        except Exception as e:
            logging.error(f"خطا در بارگذاری یادداشت‌ها: {str(e)}")
            QMessageBox.critical(self, "❌ خطا", f"خطا در بارگذاری یادداشت‌ها:\n{str(e)}")

    def filter_notes(self):
        search_text = self.note_search.text().lower()
        for row in range(self.notes_table.rowCount()):
            note_text = self.notes_table.item(row, 1).text().lower()
            self.notes_table.setRowHidden(row, search_text not in note_text)

    def show_note_dialog(self):
        row = self.transactions_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "⚠️ خطا", "لطفاً یک ردیف از جدول را انتخاب کنید!")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("📝 یادداشت جدید")
        layout = QVBoxLayout()
        note_edit = QTextEdit()
        note_edit.setPlaceholderText("متن یادداشت خود را وارد کنید...")
        note_edit.setStyleSheet("""
            QTextEdit {
                font-family: 'B Nazanin';
                font-size: 14px;
                padding: 10px;
                border: 1px solid #BDBDBD;
                border-radius: 3px;
                min-height: 150px;
            }
        """)
        btn_save = QPushButton("💾 ذخیره یادداشت")
        btn_save.clicked.connect(lambda: self.save_note(dialog, note_edit.toPlainText(), row))
        btn_save.setStyleSheet("""
            QPushButton {
                background: #388E3C;
                color: white;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover { background: #2E7D32; }
        """)
        layout.addWidget(note_edit)
        layout.addWidget(btn_save)
        dialog.setLayout(layout)
        dialog.exec_()

    def save_note(self, dialog, note_text, row):
        if not note_text.strip():
            QMessageBox.warning(self, "⚠️ خطا", "یادداشت نمی‌تواند خالی باشد!")
            return
        try:
            year = self.year_combo.currentText()
            month = f"{year}/{str(row + 1).zfill(2)}"
            linked_cell = f"ردیف {row + 1} ({self.transactions_table.item(row, 3).text()})"
            with DatabaseManager() as db:
                db.execute_query(
                    "INSERT INTO notes (member_id, date, note, linked_cell) VALUES (?, ?, ?, ?)",
                    (self.member_id, month, note_text.strip(), linked_cell),
                    fetch=False
                )
            QMessageBox.information(self, "✅ موفق", "یادداشت با موفقیت ثبت شد!")
            dialog.accept()
            self.load_notes()
        except Exception as e:
            logging.error(f"خطا در ثبت یادداشت برای عضو {self.member_id}: {str(e)}")
            QMessageBox.critical(self, "❌ خطا", f"خطا در ثبت یادداشت:\n{str(e)}")

    def show_note_cell_info(self, item):
        if item.column() == 1:
            note_id = item.data(Qt.UserRole)
            linked_cell = item.data(Qt.UserRole + 1)
            QMessageBox.information(self, "📝 اطلاعات یادداشت", f"یادداشت مربوط به: {linked_cell}\nمتن: {item.text()}")

    def delete_note(self, note_id):
        reply = QMessageBox.question(
            self, "⚠️ تأیید حذف", "آیا از حذف این یادداشت مطمئن هستید؟",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                with DatabaseManager() as db:
                    db.execute_query("DELETE FROM notes WHERE id=?", (note_id,), fetch=False)
                self.load_notes()
            except Exception as e:
                logging.error(f"خطا در حذف یادداشت {note_id}: {str(e)}")
                QMessageBox.critical(self, "❌ خطا", f"خطا در حذف یادداشت:\n{str(e)}")

    def open_calculator(self):
        try:
            os.startfile("calc.exe")
        except Exception as e:
            logging.error(f"خطا در باز کردن ماشین‌حساب: {str(e)}")
            QMessageBox.critical(self, "❌ خطا", "خطا در باز کردن ماشین‌حساب!")

    def show_balance_details(self):
        QMessageBox.information(self, "📈 نمایش حساب", "این بخش در حال توسعه است!")

    def auto_save_check(self):
        if self.table_changed:
            reply = QMessageBox.question(
                self, "💾 ذخیره خودکار",
                "تغییرات ذخیره نشده‌ای وجود دارد. آیا می‌خواهید آن‌ها را ذخیره کنید؟",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.save_table_data()

    def export_data(self):
        try:
            file_name, _ = QFileDialog.getSaveFileName(
                self, "ذخیره اطلاعات عضو", f"member_{self.member_id}_{get_persian_date().replace('/', '_')}.csv",
                "CSV Files (*.csv)"
            )
            if not file_name:
                return

            import csv
            with open(file_name, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["تاریخ", "عضویت", "وام", "پرداخت"])
                for row in range(12):
                    row_data = [
                        self.transactions_table.item(row, 3).text() if self.transactions_table.item(row, 3) else "",
                        self.transactions_table.item(row, 2).text() if self.transactions_table.item(row, 2) else "0",
                        self.transactions_table.item(row, 1).text() if self.transactions_table.item(row, 1) else "0",
                        self.transactions_table.item(row, 0).text() if self.transactions_table.item(row, 0) else "0"
                    ]
                    writer.writerow(row_data)
                writer.writerow([
                    "جمع کل",
                    self.total_membership_label.text(),
                    self.total_loan_label.text(),
                    self.total_installment_label.text()
                ])
                writer.writerow(["مانده", "", "", self.balance_label.text().replace("💰 مانده: ", "")])

            QMessageBox.information(self, "✅ موفق", "اطلاعات با موفقیت ذخیره شد!")
        except Exception as e:
            logging.error(f"خطا در صدور اطلاعات: {str(e)}")
            QMessageBox.critical(self, "❌ خطا", f"خطا در صدور اطلاعات:\n{str(e)}")

    def show_context_menu(self, pos):
        menu = QMenu(self)
        add_note_action = menu.addAction("📝 افزودن یادداشت")
        repeat_action = menu.addAction("🔄 تکرار در سلول بعد")
        refresh_action = menu.addAction("🔄 بروزرسانی")

        action = menu.exec_(self.transactions_table.mapToGlobal(pos))
        if action == add_note_action:
            self.show_note_dialog()
        elif action == repeat_action:
            self.repeat_cell_value()
        elif action == refresh_action:
            self.load_data()

    def repeat_cell_value(self):
        current_item = self.transactions_table.currentItem()
        if not current_item or self.transactions_table.currentColumn() == 3:
            return
        row = self.transactions_table.currentRow()
        col = self.transactions_table.currentColumn()
        value = current_item.text()
        if row + 1 < 12:
            new_item = QTableWidgetItem(value)
            if col == 1:
                new_item.setForeground(QColor("#D32F2F" if float(value.replace('٬', '')) > 0 else "#388E3C"))
            self.transactions_table.setItem(row + 1, col, new_item)
            self.update_balance(row + 1, col)

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    window = MemberTab(1)
    window.show()
    sys.exit(app.exec_())