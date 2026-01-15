"""
业务服务模块
提供各种业务服务的统一接口
"""
from business_services.menu_handler import MenuHandler
from business_services.essay_service import EssayService
from business_services.accounting_service import AccountingService
from business_services.employee_service import EmployeeService
from business_services.tarot_service import TarotService

__all__ = [
    "MenuHandler",
    "EssayService",
    "AccountingService",
    "EmployeeService",
    "TarotService",
]

