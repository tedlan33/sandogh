# -*- coding: utf-8 -*-
"""نسخه بهبودیافته با اضافه شدن end_date و linked_cell و هماهنگی با کد فعلی"""

import sqlite3
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Tuple, Union
from pathlib import Path
import logging
from datetime import datetime
import shutil
import os

from core.config import DatabaseConfig, BACKUP_DIR, LOG_DIR

logger = logging.getLogger(__name__)

class DatabaseManager:
    """کلاس مدیریت پایگاه داده با بهبودهای ساختاری"""
    
    def __init__(self):
        self.db_path = Path(DatabaseConfig.CONFIG["path"])
        self.conn = None
        self._initialize_db()

    def _initialize_db(self):
        """مقداردهی اولیه با مدیریت خطا و اضافه کردن ستون‌های جدید"""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(str(self.db_path))
            self._apply_pragmas()
            self._create_tables()
            self._update_schema()  # به‌روزرسانی ساختار جدول‌ها
            self._insert_default_settings()
            logger.info("پایگاه داده با موفقیت مقداردهی شد")
        except Exception as e:
            logger.critical(f"خطا در مقداردهی اولیه دیتابیس: {str(e)}")
            raise

    def _apply_pragmas(self):
        """تنظیمات بهینه‌سازی SQLite"""
        pragmas = {
            'journal_mode': DatabaseConfig.CONFIG['journal_mode'],
            'foreign_keys': int(DatabaseConfig.CONFIG['foreign_keys']),
            'cache_size': DatabaseConfig.CONFIG['cache_size'],
            'synchronous': DatabaseConfig.CONFIG['synchronous'],
            'temp_store': DatabaseConfig.CONFIG['temp_store'],
            'busy_timeout': DatabaseConfig.CONFIG['timeout'] * 1000
        }
        for name, value in pragmas.items():
            self.conn.execute(f"PRAGMA {name}={value}")

    def _create_tables(self):
        """ایجاد جداول اولیه"""
        with self.transaction() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    membership_code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    family_name TEXT,
                    phone TEXT,
                    account_number TEXT,
                    join_date TEXT NOT NULL,
                    balance REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'فعال'
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    member_id INTEGER,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    type TEXT NOT NULL,
                    description TEXT,
                    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS loans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    member_id INTEGER,
                    amount REAL NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT,
                    installments INTEGER NOT NULL,
                    monthly_payment REAL NOT NULL,
                    status TEXT DEFAULT 'فعال',
                    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    member_id INTEGER,
                    date TEXT NOT NULL,
                    note TEXT NOT NULL,
                    linked_cell TEXT,  -- ستون جدید برای لینک به سلول
                    FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_member_date ON transactions(member_id, date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_loans_member ON loans(member_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_member_date ON notes(member_id, date)")

    def _update_schema(self):
        """به‌روزرسانی ساختار جدول‌ها (اضافه کردن ستون‌های جدید اگر وجود نداشته باشند)"""
        with self.transaction() as cursor:
            # چک کردن جدول loans برای ستون end_date
            cursor.execute("PRAGMA table_info(loans)")
            columns = [col[1] for col in cursor.fetchall()]
            if "end_date" not in columns:
                cursor.execute("ALTER TABLE loans ADD COLUMN end_date TEXT")
                logger.info("ستون end_date به جدول loans اضافه شد")

            # چک کردن جدول notes برای ستون linked_cell
            cursor.execute("PRAGMA table_info(notes)")
            columns = [col[1] for col in cursor.fetchall()]
            if "linked_cell" not in columns:
                cursor.execute("ALTER TABLE notes ADD COLUMN linked_cell TEXT")
                logger.info("ستون linked_cell به جدول notes اضافه شد")

    def _insert_default_settings(self):
        """درج تنظیمات پیش‌فرض"""
        default_settings = [
            ("share_price", "2000000", "قیمت هر سهم به ریال"),
            ("monthly_increase", "0", "افزایش ماهانه سهام"),
            ("loan_factor", "2", "ضریب وام"),
            ("share_price_start_date", "", "تاریخ شروع قیمت سهام"),
            ("fund_balance", "0", "موجودی صندوق"),
            ("backup_enabled", "1", "فعال بودن بکاپ خودکار")
        ]
        with self.transaction() as cursor:
            for key, value, desc in default_settings:
                cursor.execute(
                    "INSERT OR IGNORE INTO settings (key, value, description) VALUES (?, ?, ?)",
                    (key, value, desc)
                )

    @contextmanager
    def transaction(self):
        """مدیریت تراکنش‌ها"""
        cursor = self.conn.cursor()
        try:
            yield cursor
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logger.error(f"ترکنش ناموفق: {str(e)}")
            raise

    def execute_query(self, query: str, params: tuple = (), fetch: bool = False):
        """اجرای کوئری‌ها"""
        with self.transaction() as cursor:
            cursor.execute(query, params)
            if fetch:
                return cursor.fetchall()

    def add_member(self, name: str, membership_number: str, **kwargs):
        """اضافه کردن عضو"""
        try:
            join_date = kwargs.get('join_date', datetime.now().strftime("%Y-%m-%d"))
            with self.transaction() as cursor:
                cursor.execute(
                    """INSERT INTO members 
                    (name, membership_code, phone, account_number, join_date) 
                    VALUES (?, ?, ?, ?, ?)""",
                    (name, membership_number, kwargs.get('phone'), kwargs.get('account_number'), join_date)
                )
            return True
        except sqlite3.IntegrityError as e:
            logger.error(f"عضویت تکراری: {str(e)}")
            return False

    def get_member(self, member_id: int):
        """دریافت اطلاعات عضو"""
        result = self.execute_query(
            "SELECT * FROM members WHERE id=?", 
            (member_id,), 
            fetch=True
        )
        return result[0] if result else None

    def calculate_loan_balance(self, member_id: int):
        """محاسبه مانده وام"""
        result = self.execute_query("""
            SELECT SUM(amount - (amount / installments) * (
                SELECT COUNT(*) FROM transactions t 
                WHERE t.member_id = loans.member_id 
                AND t.type = 'پرداخت' 
                AND t.date >= loans.start_date
            ))
            FROM loans WHERE member_id=? AND status='فعال'
        """, (member_id,), fetch=True)
        return int(result[0][0]) if result and result[0][0] is not None else 0

    def get_member_financial_summary(self, member_id: int) -> Dict[str, float]:
        """خلاصه مالی عضو"""
        with self.transaction() as cursor:
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN type='عضویت' THEN amount ELSE 0 END),
                    SUM(CASE WHEN type='وام' THEN amount ELSE 0 END),
                    SUM(CASE WHEN type='پرداخت' THEN amount ELSE 0 END)
                FROM transactions WHERE member_id=?
            """, (member_id,))
            result = cursor.fetchone()
            return {
                'دارایی': int(result[0] or 0),
                'وام‌ها': int(result[1] or 0),
                'پرداخت‌ها': int(result[2] or 0)
            }

    def get_setting(self, key: str, default: Any = None) -> Any:
        """دریافت تنظیمات"""
        try:
            result = self.execute_query(
                "SELECT value FROM settings WHERE key = ?",
                (key,),
                fetch=True
            )
            return result[0][0] if result else default
        except sqlite3.Error as e:
            logger.error(f"خطا در دریافت تنظیمات {key}: {str(e)}")
            return default

    def set_setting(self, key: str, value: Any, description: str = "") -> None:
        """ذخیره تنظیمات"""
        try:
            self.execute_query(
                "INSERT OR REPLACE INTO settings (key, value, description) VALUES (?, ?, ?)",
                (key, str(value), description)
            )
        except sqlite3.Error as e:
            logger.error(f"خطا در ذخیره تنظیمات {key}: {str(e)}")
            raise

    def backup_db(self, backup_path: str = None) -> str:
        """ایجاد نسخه پشتیبان"""
        try:
            if not os.path.exists(BACKUP_DIR):
                os.makedirs(BACKUP_DIR)
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_backup_path = BACKUP_DIR / f"backup_{timestamp}.db"
            final_path = Path(backup_path) if backup_path else default_backup_path
            
            self.conn.close()
            shutil.copy2(self.db_path, final_path)
            self.conn = sqlite3.connect(str(self.db_path))
            self._apply_pragmas()
            
            max_backups = DatabaseConfig.CONFIG["backup"]["max_files"]
            backups = sorted(BACKUP_DIR.glob("backup_*.db"), key=os.path.getmtime)
            while len(backups) > max_backups:
                os.remove(backups.pop(0))
                
            logger.info(f"نسخه پشتیبان در {final_path} ایجاد شد")
            return str(final_path)
        except Exception as e:
            logger.error(f"خطا در ایجاد نسخه پشتیبان: {str(e)}")
            raise

    def check_db_integrity(self) -> bool:
        """بررسی سلامت پایگاه داده"""
        try:
            with self.transaction() as cursor:
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                is_ok = result[0] == "ok"
            logger.info("بررسی سلامت پایگاه داده: بدون مشکل" if is_ok else f"مشکل: {result[0]}")
            return is_ok
        except sqlite3.Error as e:
            logger.error(f"خطا در بررسی سلامت پایگاه داده: {str(e)}")
            return False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
            logger.debug("اتصال دیتابیس بسته شد")

if __name__ == "__main__":
    with DatabaseManager() as db:
        db.add_member("تست کاربر", "M001", phone="09123456789", account_number="1234567890")
        summary = db.get_member_financial_summary(1)
        print(f"خلاصه مالی: {summary}")
        backup_path = db.backup_db()
        print(f"پشتیبان در: {backup_path}")
        print(f"سلامت دیتابیس: {db.check_db_integrity()}")