# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox, QMessageBox
from PyQt5.QtCore import Qt
from core.database import DatabaseManager
from core.utils import get_persian_date, unformat_persian_number
from datetime import datetime
import logging

class AddMemberDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("➕ افزودن عضو جدید")
        self.setMinimumWidth(400)
        self.member_id = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("👤 نام و نام خانوادگی")
        self.name_input.setStyleSheet("font-family: 'B Nazanin'; font-size: 14px; padding: 8px; border: 1px solid #BDBDBD; border-radius: 4px;")
        layout.addWidget(QLabel("👤 نام و نام خانوادگی:"))
        layout.addWidget(self.name_input)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("📌 کد عضویت (اختیاری)")
        self.code_input.setStyleSheet("font-family: 'B Nazanin'; font-size: 14px; padding: 8px; border: 1px solid #BDBDBD; border-radius: 4px;")
        layout.addWidget(QLabel("📌 کد عضویت:"))
        layout.addWidget(self.code_input)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("📱 شماره تلفن")
        self.phone_input.setStyleSheet("font-family: 'B Nazanin'; font-size: 14px; padding: 8px; border: 1px solid #BDBDBD; border-radius: 4px;")
        layout.addWidget(QLabel("📱 شماره تلفن:"))
        layout.addWidget(self.phone_input)

        self.account_input = QLineEdit()
        self.account_input.setPlaceholderText("🏦 شماره حساب")
        self.account_input.setStyleSheet("font-family: 'B Nazanin'; font-size: 14px; padding: 8px; border: 1px solid #BDBDBD; border-radius: 4px;")
        layout.addWidget(QLabel("🏦 شماره حساب:"))
        layout.addWidget(self.account_input)

        self.join_date_input = QLineEdit()
        self.join_date_input.setPlaceholderText("📅 تاریخ عضویت (YYYY/MM/DD) یا خالی برای امروز")
        self.join_date_input.setStyleSheet("font-family: 'B Nazanin'; font-size: 14px; padding: 8px; border: 1px solid #BDBDBD; border-radius: 4px;")
        layout.addWidget(QLabel("📅 تاریخ عضویت:"))
        layout.addWidget(self.join_date_input)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["✅ فعال", "❌ غیرفعال"])
        self.status_combo.setStyleSheet("font-family: 'B Nazanin'; font-size: 14px; padding: 5px;")
        layout.addWidget(QLabel("⚡ وضعیت:"))
        layout.addWidget(self.status_combo)

        buttons_layout = QHBoxLayout()
        save_btn = QPushButton("💾 ذخیره")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #1976D2; color: white; font-family: 'B Nazanin';
                padding: 8px; border-radius: 4px; font-size: 14px;
            }
            QPushButton:hover { background: #1565C0; }
        """)
        save_btn.clicked.connect(self._save_member)
        cancel_btn = QPushButton("❌ لغو")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #D32F2F; color: white; font-family: 'B Nazanin';
                padding: 8px; border-radius: 4px; font-size: 14px;
            }
            QPushButton:hover { background: #C62828; }
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addStretch()
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)

    def _save_member(self):
        name = self.name_input.text().strip()
        code = self.code_input.text().strip() or None
        phone = self.phone_input.text().strip()
        account = self.account_input.text().strip()
        join_date = self.join_date_input.text().strip() or datetime.now().strftime("%Y/%m/%d")
        status = self.status_combo.currentText().replace("✅ ", "").replace("❌ ", "")

        if not name:
            QMessageBox.warning(self, "⚠️ خطا", "لطفاً نام و نام خانوادگی را وارد کنید.")
            return
        try:
            datetime.strptime(join_date, "%Y/%m/%d")
        except ValueError:
            QMessageBox.warning(self, "⚠️ خطا", "فرمت تاریخ عضویت باید YYYY/MM/DD باشد!")
            return

        try:
            with DatabaseManager() as db:
                if code:
                    existing = db.execute_query(
                        "SELECT id FROM members WHERE membership_code=?",
                        (code,), fetch=True
                    )
                    if existing:
                        QMessageBox.warning(self, "⚠️ خطا", "این کد عضویت قبلاً ثبت شده است.")
                        return
                else:
                    code = self._generate_unique_code(db)

                self.member_id = db.execute_query(
                    "INSERT INTO members (membership_code, name, phone, account_number, join_date, balance, status) "
                    "VALUES (?, ?, ?, ?, ?, 0, ?) RETURNING id",
                    (code, name, phone, account, join_date, status),
                    fetch=True
                )[0][0]

            QMessageBox.information(self, "✅ موفق", f"عضو جدید با کد {code} ثبت شد.")
            self.accept()
        except Exception as e:
            logging.error(f"خطا در ثبت عضو جدید: {str(e)}")
            QMessageBox.critical(self, "❌ خطا", f"خطا در ثبت عضو:\n{str(e)}")

    def _generate_unique_code(self, db):
        while True:
            code = f"M{datetime.now().strftime('%Y%m%d')}{len(db.execute_query('SELECT id FROM members', fetch=True)) + 1:03d}"
            if not db.execute_query("SELECT id FROM members WHERE membership_code=?", (code,), fetch=True):
                return code

class SharePriceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📈 تنظیم قیمت سهام")
        self.setMinimumWidth(400)
        self.setStyleSheet("background: #F5F5F5;")  # بهبود ظاهری
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("💰 قیمت پایه سهام (تومان)")
        self.price_input.setStyleSheet("font-family: 'B Nazanin'; font-size: 14px; padding: 8px; border: 1px solid #BDBDBD; border-radius: 4px;")
        layout.addWidget(QLabel("💰 قیمت پایه سهام:"))
        layout.addWidget(self.price_input)

        self.increase_input = QLineEdit()
        self.increase_input.setPlaceholderText("📈 افزایش ماهانه (تومان)")
        self.increase_input.setStyleSheet("font-family: 'B Nazanin'; font-size: 14px; padding: 8px; border: 1px solid #BDBDBD; border-radius: 4px;")
        layout.addWidget(QLabel("📈 افزایش ماهانه:"))
        layout.addWidget(self.increase_input)

        self.loan_factor_input = QLineEdit()
        self.loan_factor_input.setPlaceholderText("🔢 ضریب وام (مثال: 1.5 یا 2)")
        self.loan_factor_input.setStyleSheet("font-family: 'B Nazanin'; font-size: 14px; padding: 8px; border: 1px solid #BDBDBD; border-radius: 4px;")
        layout.addWidget(QLabel("🔢 ضریب وام:"))
        layout.addWidget(self.loan_factor_input)

        self.date_input = QLineEdit()
        self.date_input.setPlaceholderText("📅 تاریخ شروع (YYYY/MM/DD)")
        self.date_input.setStyleSheet("font-family: 'B Nazanin'; font-size: 14px; padding: 8px; border: 1px solid #BDBDBD; border-radius: 4px;")
        layout.addWidget(QLabel("📅 تاریخ شروع:"))
        layout.addWidget(self.date_input)

        buttons_layout = QHBoxLayout()
        save_btn = QPushButton("💾 ذخیره")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #1976D2; color: white; font-family: 'B Nazanin';
                padding: 8px; border-radius: 4px; font-size: 14px;
            }
            QPushButton:hover { background: #1565C0; }
        """)
        save_btn.clicked.connect(self._save_settings)
        cancel_btn = QPushButton("❌ لغو")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #D32F2F; color: white; font-family: 'B Nazanin';
                padding: 8px; border-radius: 4px; font-size: 14px;
            }
            QPushButton:hover { background: #C62828; }
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addStretch()
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)

        self._load_current_settings()

    def _load_current_settings(self):
        try:
            with DatabaseManager() as db:
                self.price_input.setText(db.get_setting("share_price", "2000000"))
                self.increase_input.setText(db.get_setting("monthly_increase", "0"))
                self.loan_factor_input.setText(db.get_setting("loan_factor", "2"))
                self.date_input.setText(db.get_setting("share_price_start_date", ""))
        except Exception as e:
            logging.error(f"خطا در بارگذاری تنظیمات سهام: {str(e)}")

    def _save_settings(self):
        price = self.price_input.text().strip()
        increase = self.increase_input.text().strip()
        loan_factor = self.loan_factor_input.text().strip()
        start_date = self.date_input.text().strip()

        try:
            price = float(unformat_persian_number(price or "2000000"))
            if price <= 0:
                raise ValueError("قیمت سهام باید مثبت باشد.")
            increase = float(unformat_persian_number(increase or "0"))
            if increase < 0:
                raise ValueError("افزایش ماهانه نمی‌تواند منفی باشد.")
            loan_factor = float(unformat_persian_number(loan_factor or "2"))  # اعشاری قبول می‌کنه
            if loan_factor <= 0:
                raise ValueError("ضریب وام باید مثبت باشد.")
            if start_date:
                datetime.strptime(start_date, "%Y/%m/%d")
            else:
                start_date = datetime.now().strftime("%Y/%m/%d")
        except ValueError as e:
            QMessageBox.warning(self, "⚠️ خطا", f"ورودی نامعتبر: {str(e)}")
            return

        try:
            with DatabaseManager() as db:
                db.set_setting("share_price", str(price), "قیمت پایه سهام")
                db.set_setting("monthly_increase", str(increase), "افزایش ماهانه سهام")
                db.set_setting("loan_factor", str(loan_factor), "ضریب وام")  # به صورت رشته ذخیره می‌شه
                db.set_setting("share_price_start_date", start_date, "تاریخ شروع قیمت سهام")
            QMessageBox.information(self, "✅ موفق", "تنظیمات قیمت سهام ذخیره شد.")
            self.accept()
        except Exception as e:
            logging.error(f"خطا در ذخیره تنظیمات سهام: {str(e)}")
            QMessageBox.critical(self, "❌ خطا", f"خطا در ذخیره تنظیمات:\n{str(e)}")