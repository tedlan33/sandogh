"""پکیج هسته برنامه شامل دیتابیس، تنظیمات و توابع کمکی"""

from .database import DatabaseManager
from .config import AppConfig, BACKUP_DIR  # DB_PATH حذف شده اگه استفاده نمی‌شه
from .utils import (
    format_persian_number,
    validate_phone_number,
    calculate_loan_capacity,
    get_persian_date,
    generate_membership_code,  # اضافه شده
    calculate_profit          # اضافه شده
)

__all__ = [
    'DatabaseManager',
    'AppConfig', 'BACKUP_DIR',  # DB_PATH حذف شده
    'format_persian_number', 'validate_phone_number',
    'calculate_loan_capacity', 'get_persian_date',
    'generate_membership_code', 'calculate_profit'  # اضافه شده
]