# -*- coding: utf-8 -*-
"""
فایل اصلی اجرای برنامه مدیریت صندوق قرض‌الحسنه
نسخه بهبودیافته با سازگاری کامل و مدیریت بهتر خطاها
"""

import sys
import os
import logging
import traceback
from datetime import datetime
from pathlib import Path


from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QTimer

from ui.main_window import MainWindow
from core.database import DatabaseManager
from core.config import (
    AppConfig,
    LOG_DIR,
    ICON_DIR,
    BASE_DIR,
    DatabaseConfig,
    BACKUP_DIR
)

def setup_logging() -> logging.Logger:
    """تنظیم سیستم لاگ‌گیری"""
    try:
        LOG_DIR.mkdir(exist_ok=True, parents=True)
        log_file = LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        logger = logging.getLogger(__name__)
        logger.info("سیستم لاگ‌گیری با موفقیت راه‌اندازی شد")
        return logger
    except Exception as e:
        print(f"خطا در راه‌اندازی سیستم لاگ‌گیری: {str(e)}")
        raise

def check_system_requirements(logger: logging.Logger) -> bool:
    """بررسی نیازمندی‌های سیستم"""
    try:
        required_files = [
            ICON_DIR / "app_icon.png",
            BASE_DIR / "ui" / "main_window.py",
            BASE_DIR / "core" / "database.py",
            BASE_DIR / "core" / "config.py",
            BASE_DIR / "core" / "utils.py"
        ]
        for file in required_files:
            if not file.exists():
                logger.error(f"فایل ضروری یافت نشد: {file}")
                QMessageBox.critical(
                    None,
                    "خطای سیستمی",
                    f"فایل ضروری یافت نشد:\n{file}"
                )
                return False
        
        db_path = Path(DatabaseConfig.CONFIG["path"])
        if db_path.exists() and not os.access(db_path, os.R_OK | os.W_OK):
            logger.error(f"عدم دسترسی به فایل دیتابیس: {db_path}")
            QMessageBox.critical(
                None,
                "خطای دسترسی",
                f"عدم دسترسی به فایل دیتابیس:\n{db_path}"
            )
            return False
        
        logger.info("تمام نیازمندی‌های سیستم با موفقیت بررسی شد")
        return True
    except Exception as e:
        logger.error(f"خطا در بررسی نیازمندی‌ها: {str(e)}")
        QMessageBox.critical(
            None,
            "خطای بررسی سیستم",
            f"خطا در بررسی نیازمندی‌ها:\n{str(e)}"
        )
        return False

def handle_uncaught_exceptions(exc_type, exc_value, exc_traceback):
    """مدیریت خطاهای پیش‌بینی‌نشده"""
    logger = logging.getLogger(__name__)
    logger.critical(
        "خطای پیش‌بینی‌نشده رخ داد:",
        exc_info=(exc_type, exc_value, exc_traceback)
    )
    error_msg = f"""
    خطای بحرانی:
    نوع: {exc_type.__name__}
    پیام: {str(exc_value)}
    جزئیات: {''.join(traceback.format_tb(exc_traceback))}
    """
    QMessageBox.critical(None, "خطای سیستمی", error_msg)
    
    try:
        with DatabaseManager() as db:
            backup_path = BACKUP_DIR / f"emergency_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            db.backup_db(str(backup_path))
            logger.info(f"بکاپ اضطراری ایجاد شد: {backup_path}")
    except Exception as e:
        logger.error(f"خطا در ایجاد بکاپ اضطراری: {str(e)}")
    
    sys.exit(1)

def setup_application() -> QApplication:
    """تنظیم اولیه برنامه PyQt5"""
    app = QApplication(sys.argv)
    app.setApplicationName(AppConfig.APP_NAME)
    app.setApplicationVersion(AppConfig.APP_VERSION)
    app.setOrganizationName(AppConfig.ORGANIZATION)
    
    icon_path = ICON_DIR / "app_icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    else:
        logging.getLogger(__name__).warning(f"آیکون برنامه یافت نشد: {icon_path}")
    
    return app

def main():
    """نقطه ورود اصلی برنامه"""
    logger = setup_logging()
    sys.excepthook = handle_uncaught_exceptions
    app = setup_application()  # اصلاح شده
    
    try:
        logger.info(f"شروع برنامه {AppConfig.APP_NAME} نسخه {AppConfig.APP_VERSION}")
        
        if not check_system_requirements(logger):
            logger.error("نیازمندی‌های سیستم برآورده نشد، خروج از برنامه")
            sys.exit(1)
        
        logger.info("بررسی سلامت دیتابیس...")
        with DatabaseManager() as db:
            if not db.check_db_integrity():
                logger.warning("دیتابیس سالم نیست، تلاش برای مقداردهی اولیه...")
                db.init_db()
                if not db.check_db_integrity():
                    logger.error("دیتابیس همچنان مشکل دارد، خروج از برنامه")
                    QMessageBox.critical(None, "خطای دیتابیس", "دیتابیس قابل تعمیر نیست!")
                    sys.exit(1)
            else:
                logger.info("دیتابیس سالم است")
        
        logger.info("ایجاد رابط کاربری اصلی...")
        window = MainWindow()
        logger.info("نمایش پنجره اصلی...")
        window.show()
        
        if not window.isVisible():
            logger.error("پنجره اصلی نمایش داده نشد!")
            raise Exception("خطا در نمایش رابط کاربری")
        
        if AppConfig.SYSTEM.get("auto_backup", False):
            interval = AppConfig.SYSTEM.get("backup_interval", 24) * 3600 * 1000
            def auto_backup():
                with DatabaseManager() as db:
                    backup_path = BACKUP_DIR / f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                    db.backup_db(str(backup_path))
                    logger.info(f"بکاپ خودکار ایجاد شد: {backup_path}")
            
            timer = QTimer()
            timer.timeout.connect(auto_backup)
            timer.start(interval)
            logger.info(f"بکاپ خودکار هر {interval // 3600000} ساعت تنظیم شد")
        
        logger.info("برنامه با موفقیت راه‌اندازی شد")
        sys.exit(app.exec_())
    
    except Exception as e:
        logger.error(f"خطای اصلی در راه‌اندازی: {str(e)}", exc_info=True)
        QMessageBox.critical(
            None,
            "خطای راه‌اندازی",
            f"برنامه نمی‌تواند اجرا شود:\n{str(e)}"
        )
        sys.exit(1)

if __name__ == "__main__":
    main()