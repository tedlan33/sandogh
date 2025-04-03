# -*- coding: utf-8 -*-
"""
ماژول توابع کمکی برای مدیریت عمومی برنامه
نسخه بهبودیافته با هماهنگی کامل با main_window.py و member_tab.py
"""

import os
import shutil
import re
from datetime import datetime
from typing import Union, Optional, Tuple
import logging
from jdatetime import datetime as jdatetime
from core.config import AppConfig, BACKUP_DIR
from core.database import DatabaseManager

logger = logging.getLogger(__name__)

def unformat_persian_number(text: str) -> str:
    """حذف فرمت‌های فارسی از اعداد"""
    persian_digits = str.maketrans("۰۱۲۳۴۵۶۷۸۹-", "0123456789-")
    return text.translate(persian_digits).replace(',', '').replace('٬', '')

def format_persian_number(
    number: Union[int, float, str], 
    decimal_places: int = 0,
    with_currency: bool = False, 
    currency_symbol: str = AppConfig.CURRENCY["symbol"]
) -> str:
    """قالب‌بندی اعداد به صورت فارسی"""
    try:
        # تبدیل ورودی به عدد
        if isinstance(number, str):
            if not number.strip():  # اگه خالی باشه
                return "۰"
            number = float(unformat_persian_number(number))
        else:
            number = float(number) if number is not None else 0

        # اگر عدد صفر باشه
        if number == 0:
            formatted = "۰"
        else:
            # فقط اعداد صحیح رو نشون می‌دیم چون پروژه‌ات اعشار نمی‌خواد
            formatted = "{:,}".format(int(number)).replace(',', '٬')
            persian_digits = str.maketrans("0123456789-", "۰۱۲۳۴۵۶۷۸۹-")
            formatted = formatted.translate(persian_digits)

        # اضافه کردن واحد پول اگه لازم باشه
        if with_currency:
            formatted = (
                f"{formatted} {currency_symbol}" 
                if AppConfig.CURRENCY["symbol_position"] == "after" 
                else f"{currency_symbol} {formatted}"
            )
        return formatted
    except (ValueError, TypeError) as e:
        logger.error(f"خطا در قالب‌بندی عدد {number}: {str(e)}", exc_info=True)
        return "۰"

def validate_phone_number(phone: str) -> bool:
    """اعتبارسنجی شماره تلفن ایرانی"""
    phone = unformat_persian_number(phone).strip()
    return re.match(r"^(\+98|0)?9\d{9}$", phone) is not None

def calculate_loan_capacity(member_id: int) -> int:
    """محاسبه وام قابل دریافت (هماهنگ با main_window.py)"""
    try:
        with DatabaseManager() as db:
            shares, total_invested = calculate_member_shares(member_id)
            share_price = int(float(db.get_setting("share_price", "2000000")))
            loan_factor = int(float(db.get_setting("loan_factor", "2")))
            max_loan = shares * share_price * loan_factor
            
            active_loans = int(db.execute_query(
                "SELECT COALESCE(SUM(amount), 0) FROM loans WHERE member_id=? AND status='فعال'",
                (member_id,), fetch=True
            )[0][0])
            
            return max(0, max_loan - active_loans)
    except Exception as e:
        logger.error(f"خطا در محاسبه وام قابل دریافت برای عضو {member_id}: {str(e)}")
        return 0

def calculate_member_shares(member_id: int) -> Tuple[int, int]:
    """محاسبه تعداد سهام و ارزش آن"""
    try:
        with DatabaseManager() as db:
            share_price = int(float(db.get_setting("share_price", "2000000")))
            if share_price <= 0:
                return (0, 0)
                
            investments = db.execute_query(
                "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE member_id=? AND type='عضویت'",
                (member_id,), fetch=True
            )[0][0]
            investments = int(float(investments))
            
            shares = investments // share_price
            return (shares, investments)
    except Exception as e:
        logger.error(f"خطا در محاسبه سهام عضو {member_id}: {str(e)}")
        return (0, 0)

def get_persian_date(date_obj: Optional[Union[datetime, str]] = None, format_str: Optional[str] = None) -> str:
    """دریافت تاریخ شمسی"""
    format_str = format_str or AppConfig.DATE_FORMATS["short"]
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.strptime(date_obj, "%Y/%m/%d")
        except ValueError:
            logger.error(f"فرمت تاریخ نامعتبر: {date_obj}")
            return date_obj
    date_obj = date_obj or datetime.now()
    try:
        return jdatetime.fromgregorian(datetime=date_obj).strftime(format_str)
    except Exception as e:
        logger.error(f"خطا در تبدیل تاریخ: {str(e)}")
        return "تاریخ نامعتبر"

def create_backup(
    source_path: str, 
    backup_dir: Optional[str] = None,
    timestamp_format: str = "%Y%m%d_%H%M%S"
) -> str:
    """ایجاد پشتیبان"""
    backup_dir = backup_dir or str(BACKUP_DIR)
    
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"فایل منبع یافت نشد: {source_path}")
    
    os.makedirs(backup_dir, exist_ok=True)
    
    filename = os.path.basename(source_path)
    name, ext = os.path.splitext(filename)
    timestamp = datetime.now().strftime(timestamp_format)
    backup_filename = f"{name}_{timestamp}{ext}"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    try:
        if os.path.isdir(source_path):
            shutil.copytree(source_path, backup_path)
        else:
            shutil.copy2(source_path, backup_path)
        logger.info(f"پشتیبان با موفقیت ایجاد شد: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"خطا در ایجاد پشتیبان از {source_path}: {str(e)}")
        raise OSError(f"خطا در ایجاد پشتیبان: {str(e)}") from e

def generate_membership_code(last_code: Optional[str] = None) -> str:
    """تولید کد عضویت"""
    try:
        with DatabaseManager() as db:
            if last_code is None:
                result = db.execute_query(
                    "SELECT membership_code FROM members ORDER BY id DESC LIMIT 1",
                    fetch=True
                )
                last_code = result[0][0] if result else "M000"
            
            prefix = "M"
            number = int(unformat_persian_number(last_code[1:])) + 1 if last_code else 1
            return f"{prefix}{str(number).zfill(3)}"
    except Exception as e:
        logger.error(f"خطا در تولید کد عضویت: {str(e)}")
        return "M001"

def calculate_profit(amount: float, months: int) -> int:
    """محاسبه سود وام (فعلاً 0 چون کد فعلی سودی نداره)"""
    try:
        return 0  # هماهنگ با کد فعلی که سود حساب نمی‌کنه
    except Exception as e:
        logger.error(f"خطا در محاسبه سود: {str(e)}")
        return 0

if __name__ == "__main__":
    print(format_persian_number("1234567", with_currency=True))  # ۱٬۲۳۴٬۵۶۷ تومان
    print(format_persian_number("0"))  # ۰
    print(format_persian_number("1000000"))  # ۱٬۰۰۰٬۰۰۰
    print(unformat_persian_number("۱٬۲۳۴٬۵۶۷"))  # 1234567
    print(get_persian_date("2025/04/02"))  # ۱۴۰۴/۰۱/۱۳ (تقریبی)
    print(validate_phone_number("09123456789"))  # True
    print(generate_membership_code("M005"))  # M006
    print(calculate_profit(10000000, 12))  # 0