"""
页面解析器模块
"""
from bs4 import BeautifulSoup  # pyright: ignore[reportMissingModuleSource]
from urllib.parse import urljoin
import re
from utils import clean_text, extract_date_from_url


class ListPageParser:
    """列表页解析器"""
    
    def __init__(self, html_content, base_url):
        """
        初始化列表页解析器
        
        Args:
            html_content: HTML内容
            base_url: 基础URL
        """
        self.soup = BeautifulSoup(html_content, 'lxml')
        self.base_url = base_url
    
    def extract_total_pages(self):
        """
        提取总页数
        
        Returns:
            int: 总页数，如果无法提取则返回1
        """
        # 查找分页信息，可能的形式：
        # 1. 分页链接中的数字
        # 2. "共XX页" 或 "第X页/共XX页"
        page_links = self.soup.find_all('a', href=re.compile(r'index.*\.html'))
        
        max_page = 1
        for link in page_links:
            href = link.get('href', '')
            # 尝试从URL中提取页码，如 index_2.html 或 index.html?page=2
            page_match = re.search(r'[_\?](\d+)', href)
            if page_match:
                page_num = int(page_match.group(1))
                max_page = max(max_page, page_num)
        
        # 尝试从文本中提取总页数
        text_content = self.soup.get_text()
        # 匹配 "共XX页" 或 "第X页/共XX页" 或 "共 44 页"
        page_patterns = [
            r'共\s*(\d+)\s*页',
            r'/\s*共\s*(\d+)\s*页',
            r'总页数[：:]\s*(\d+)',
            r'共\s*(\d+)\s*条'
        ]
        
        for pattern in page_patterns:
            match = re.search(pattern, text_content)
            if match:
                total_pages = int(match.group(1))
                max_page = max(max_page, total_pages)
                break
        
        return max_page
    
    def extract_announcement_links(self):
        """
        提取所有公告链接
        
        Returns:
            list: 包含(链接URL, 公告编号, 发布时间)的元组列表
        """
        links = []
        
        # 查找所有包含公告链接的元素
        # 根据网页结构，公告链接通常在li标签或a标签中
        list_items = self.soup.find_all('li')
        
        for item in list_items:
            link_tag = item.find('a')
            if link_tag and link_tag.get('href'):
                href = link_tag.get('href')
                # 跳过非详情页链接和分页链接
                if 'index.html' in href or not href.startswith('/'):
                    continue
                    
                full_url = urljoin(self.base_url, href)
                
                # 提取公告编号和发布时间
                text = clean_text(item.get_text())
                
                # 提取公告编号，格式如：沪社险（2025）稽通103000168号
                number_match = re.search(r'沪社险[（(]\d{4}[）)][\u4e00-\u9fa5]+\d+号', text)
                if number_match:
                    announcement_number = number_match.group(0)
                else:
                    announcement_number = ''
                
                # 提取发布时间，格式如：2025-12-03
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)
                publish_date = date_match.group(1) if date_match else ''
                
                links.append({
                    'url': full_url,
                    'announcement_number': announcement_number,
                    'publish_date': publish_date
                })
        
        return links


class DetailPageParser:
    """详情页解析器"""
    
    def __init__(self, html_content):
        """
        初始化详情页解析器
        
        Args:
            html_content: HTML内容
        """
        self.soup = BeautifulSoup(html_content, 'lxml')
    
    def extract_announcement_info(self):
        """
        提取公告详细信息
        
        Returns:
            dict: 包含公告信息的字典
        """
        info = {}
        text_content = self.soup.get_text()
        
        # 提取公告编号，格式如：沪社险（2025）稽意173000259号
        number_match = re.search(r'沪社险[（(]\d{4}[）)][\u4e00-\u9fa5]+\d+号', text_content)
        if number_match:
            info['announcement_number'] = number_match.group(0)
        else:
            info['announcement_number'] = ''
        
        # 提取发布时间，格式如：发布时间：2025-12-03
        date_match = re.search(r'发布时间[：:]\s*(\d{4}-\d{2}-\d{2})', text_content)
        if date_match:
            info['publish_date'] = date_match.group(1)
        else:
            # 备用方法：查找日期格式
            date_match2 = re.search(r'(\d{4}-\d{2}-\d{2})', text_content)
            if date_match2:
                info['publish_date'] = date_match2.group(1)
            else:
                info['publish_date'] = ''
        
        # 提取公司名称，格式如：上海南库新能源技术有限公司：
        # 查找包含"有限公司"或"股份"等关键词，且后面跟"："的文本
        company_patterns = [
            r'([^：\n]*有限公司)[：:]',
            r'([^：\n]*股份[^：\n]*)[：:]',
            r'([^：\n]*企业[^：\n]*)[：:]',
            r'([^：\n]*公司)[：:]'
        ]
        
        company_name = ''
        for pattern in company_patterns:
            match = re.search(pattern, text_content)
            if match:
                potential_name = clean_text(match.group(1))
                # 确保是公司名称（包含公司相关关键词）
                if any(keyword in potential_name for keyword in ['公司', '企业', '股份', '有限']):
                    company_name = potential_name
                    break
        
        info['company_name'] = company_name
        
        # 提取投诉人信息，格式如：对王昶久投诉你单位
        # 匹配"对XXX投诉"的模式
        complaint_match = re.search(r'对([^投诉\n]+)投诉', text_content)
        if complaint_match:
            complaint_text = clean_text(complaint_match.group(1))
            # 提取人名（去除可能的空格和标点）
            complaint_person = complaint_text.strip('，。、')
            info['complaint_person'] = complaint_person
        else:
            # 备用方法：查找"XXX投诉"格式
            complaint_match2 = re.search(r'([^投诉\n]+)投诉', text_content)
            if complaint_match2:
                complaint_text = clean_text(complaint_match2.group(1))
                # 提取最后一个词作为人名
                words = complaint_text.split()
                if words:
                    info['complaint_person'] = words[-1].strip('，。、')
                else:
                    info['complaint_person'] = ''
            else:
                info['complaint_person'] = ''
        
        # 提取时间段信息，格式如：2022年7月至2023年1月 或 2022-07至2023-01
        period_patterns = [
            r'(\d{4}年\d{1,2}月至\d{4}年\d{1,2}月)',
            r'(\d{4}-\d{2}月至\d{4}-\d{2}月)',
            r'(\d{4}年\d{1,2}月[至到]\d{4}年\d{1,2}月)',
            r'(\d{4}-\d{2}[月至到]\d{4}-\d{2})'
        ]
        
        period = ''
        for pattern in period_patterns:
            match = re.search(pattern, text_content)
            if match:
                period = match.group(1)
                break
        
        info['period'] = period
        
        # 提取缴费基数，格式如：缴费基数为12259.8元
        base_patterns = [
            r'缴费基数[为是]\s*(\d+(?:\.\d+)?)',
            r'缴费基数[：:]\s*(\d+(?:\.\d+)?)',
            r'基数[为是]\s*(\d+(?:\.\d+)?)'
        ]
        
        payment_base = ''
        for pattern in base_patterns:
            match = re.search(pattern, text_content)
            if match:
                payment_base = match.group(1)
                break
        
        info['payment_base'] = payment_base
        
        # 提取完整文本内容
        # 尝试找到主要内容区域
        content_div = self.soup.find('div', class_=re.compile('content|main|detail|article'))
        if not content_div:
            content_div = self.soup.find('div', id=re.compile('content|main|detail|article'))
        if not content_div:
            # 查找包含公告内容的div
            content_div = self.soup.find('div', {'class': lambda x: x and ('content' in x.lower() or 'main' in x.lower())})
        
        if content_div:
            info['content'] = clean_text(content_div.get_text())
        else:
            # 如果找不到特定区域，提取body的主要内容
            body = self.soup.find('body')
            if body:
                info['content'] = clean_text(body.get_text())
            else:
                info['content'] = clean_text(text_content)
        
        return info
