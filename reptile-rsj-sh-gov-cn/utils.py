"""
工具函数模块
"""
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
import re


def is_within_year(date_str):
    """
    判断日期是否在最近一年内
    
    Args:
        date_str: 日期字符串，格式如 '2025-12-03'
    
    Returns:
        bool: 如果在最近一年内返回True，否则返回False
    """
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        one_year_ago = datetime.now() - timedelta(days=365)
        return date_obj >= one_year_ago
    except ValueError:
        return False


def build_full_url(base_url, relative_url):
    """
    构建完整URL
    
    Args:
        base_url: 基础URL
        relative_url: 相对URL
    
    Returns:
        str: 完整URL
    """
    return urljoin(base_url, relative_url)


def extract_date_from_url(url):
    """
    从URL中提取日期
    
    Args:
        url: URL字符串，格式如 'https://rsj.sh.gov.cn/tsbjhzsgg_17345/20251203/t0035_1437227.html'
    
    Returns:
        str: 日期字符串，格式如 '2025-12-03'，如果提取失败返回None
    """
    match = re.search(r'/(\d{8})/', url)
    if match:
        date_str = match.group(1)
        try:
            date_obj = datetime.strptime(date_str, '%Y%m%d')
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            return None
    return None


def clean_text(text):
    """
    清理文本，去除多余空白字符
    
    Args:
        text: 原始文本
    
    Returns:
        str: 清理后的文本
    """
    if not text:
        return ''
    return ' '.join(text.split())
