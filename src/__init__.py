"""
自动询价系统 - 核心模块
"""
__version__ = "0.1.0"

from .scraper import WebScraper
from .manufacturer import ManufacturerInquiry
from .history import HistoryMatcher
from .aggregator import PriceAggregator
from .scheduler import InquiryScheduler

__all__ = [
    "WebScraper",
    "ManufacturerInquiry", 
    "HistoryMatcher",
    "PriceAggregator",
    "InquiryScheduler",
]
