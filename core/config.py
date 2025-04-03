# -*- coding: utf-8 -*-
"""
فایل تنظیمات اصلی برنامه مدیریت صندوق قرض‌الحسنه
نسخه بهبودیافته با تغییرات ضروری
"""

from pathlib import Path
import os
import logging
import json
from typing import Dict, Any, Optional

# مسیرهای اصلی
BASE_DIR = Path(__file__).parent.parent.resolve()
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
BACKUP_DIR = BASE_DIR / "backups"
ICON_DIR = BASE_DIR / "icons"
TEMP_DIR = BASE_DIR / "temp"
REPORTS_DIR = BASE_DIR / "reports"
TEMPLATES_DIR = BASE_DIR / "templates"

# مسیر دیتابیس
DB_PATH = DATA_DIR / "finance_v2.db"

# ایجاد پوشه‌های ضروری
REQUIRED_DIRS = [
    DATA_DIR, LOG_DIR, BACKUP_DIR, 
    ICON_DIR, TEMP_DIR, REPORTS_DIR,
    TEMPLATES_DIR
]

for directory in REQUIRED_DIRS:
    try:
        directory.mkdir(exist_ok=True, parents=True)
    except Exception as e:
        print(f"خطا در ایجاد پوشه {directory}: {str(e)}")

# تنظیمات لاگ‌گیری
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "app_config.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AppConfig:
    """تنظیمات اصلی برنامه"""
    APP_NAME: str = "سامانه مدیریت صندوق قرض‌الحسنه"
    APP_VERSION: str = "2.1.0"
    ORGANIZATION: str = "شرکت نمونه"
    SUPPORT_EMAIL: str = "support@example.com"
    DEFAULT_THEME: str = "light"
    
    # تنظیمات مالی
    FINANCIAL: Dict[str, Any] = {
        "share_price": 2000000,  # هماهنگ با کد قبلی
        "loan_settings": {
            "min_share_for_loan": 10,
            "loan_to_value_ratio": 2,  # هماهنگ با "loan_factor" پیش‌فرض
            "max_loan_term": 36,       # حداکثر مدت وام (ماه)
            "profit_rate": 0.0         # بدون سود (طبق کد فعلی)
        }
    }
    
    UI_THEMES: Dict[str, Dict[str, Any]] = {
        "light": {
            "primary_color": "#1976D2",
            "secondary_color": "#FF9800",
            "background": "#F5F5F5",
            "text_color": "#212121",
            "font_family": "B Nazanin",
            "font_size": 12,
            "window_size": (1400, 900)  # هماهنگ با main_window
        },
        "dark": {
            "primary_color": "#2196F3",
            "secondary_color": "#FFC107",
            "background": "#424242",
            "text_color": "#FFFFFF",
            "font_family": "B Nazanin",
            "font_size": 12,
            "window_size": (1400, 900)
        }
    }
    
    CURRENCY: Dict[str, Any] = {
        "symbol": "تومان",
        "thousand_separator": "٬",
        "decimal_places": 0,  # بدون اعشار
        "symbol_position": "after"
    }
    
    DATE_FORMATS: Dict[str, str] = {
        "short": "%Y/%m/%d",
        "medium": "%Y/%m/%d %H:%M",
        "long": "%A %d %B %Y",
        "database": "%Y-%m-%d %H:%M:%S"
    }
    
    SYSTEM: Dict[str, Any] = {
        "auto_backup": True,
        "backup_interval": 24,
        "max_log_files": 7,
        "max_backups": 30,
        "auto_update_check": True
    }

class DatabaseConfig:
    """تنظیمات پایگاه داده"""
    CONFIG: Dict[str, Any] = {
        "path": str(DB_PATH),
        "timeout": 30,
        "journal_mode": "WAL",
        "foreign_keys": True,
        "cache_size": -2000,
        "synchronous": 1,
        "temp_store": 2,
        "backup": {
            "enabled": True,
            "max_files": 30,
            "compress": False
        }
    }

class SecurityConfig:
    """تنظیمات امنیتی"""
    PASSWORD_POLICY: Dict[str, Any] = {
        "min_length": 8,
        "require_upper": True,
        "require_lower": True,
        "require_digit": True,
        "require_special": True,
        "max_attempts": 5
    }

def load_custom_config(config_file: Optional[Path] = None) -> Dict[str, Any]:
    """بارگذاری تنظیمات سفارشی از فایل JSON"""
    if config_file is None:
        config_file = BASE_DIR / "config.json"
    
    if not config_file.exists():
        logger.info(f"فایل تنظیمات سفارشی در {config_file} یافت نشد.")
        return {}
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"خطا در بارگذاری فایل تنظیمات: {str(e)}")
        return {}

def apply_custom_config(config: Dict[str, Any]) -> None:
    """اعمال تنظیمات سفارشی"""
    if not config:
        return
    
    config_mapping = {
        "app": AppConfig,
        "database": DatabaseConfig,
        "security": SecurityConfig
    }
    
    for section, values in config.items():
        if section.lower() in config_mapping:
            target_class = config_mapping[section.lower()]
            for key, value in values.items():
                if hasattr(target_class, key.upper()):
                    setattr(target_class, key.upper(), value)
                elif hasattr(target_class, key):
                    setattr(target_class, key, value)

# اعمال تنظیمات سفارشی
apply_custom_config(load_custom_config())

__all__ = [
    'AppConfig', 'DatabaseConfig', 'SecurityConfig',
    'DB_PATH', 'BACKUP_DIR', 'LOG_DIR', 'BASE_DIR',
    'load_custom_config', 'apply_custom_config'
]