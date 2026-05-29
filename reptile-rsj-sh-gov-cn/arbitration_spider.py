"""
仲裁公告爬虫模块
"""
import requests  # pyright: ignore[reportMissingModuleSource]
from requests.adapters import HTTPAdapter  # pyright: ignore[reportMissingModuleSource]
from urllib3.util.retry import Retry  # pyright: ignore[reportMissingImports]
import time
from parser import ListPageParser, DetailPageParser
from utils import is_within_year, extract_date_from_url
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ArbitrationListPageParser:
    """仲裁公告列表页解析器"""
    
    def __init__(self, html_content, base_url):
        """
        初始化列表页解析器
        
        Args:
            html_content: HTML内容
            base_url: 基础URL
        """
        from bs4 import BeautifulSoup
        import re
        from urllib.parse import urljoin
        from utils import clean_text
        
        self.soup = BeautifulSoup(html_content, 'lxml')
        self.base_url = base_url
        self.re = re
        self.urljoin = urljoin
        self.clean_text = clean_text
    
    def extract_total_pages(self):
        """
        提取总页数
        
        Returns:
            int: 总页数，如果无法提取则返回1
        """
        # 查找分页信息
        page_links = self.soup.find_all('a', href=self.re.compile(r'index.*\.html'))
        
        max_page = 1
        for link in page_links:
            href = link.get('href', '')
            page_match = self.re.search(r'[_\?](\d+)', href)
            if page_match:
                page_num = int(page_match.group(1))
                max_page = max(max_page, page_num)
        
        # 尝试从文本中提取总页数
        text_content = self.soup.get_text()
        page_patterns = [
            r'共\s*(\d+)\s*页',
            r'/\s*共\s*(\d+)\s*页',
            r'总页数[：:]\s*(\d+)',
            r'共\s*(\d+)\s*条'
        ]
        
        for pattern in page_patterns:
            match = self.re.search(pattern, text_content)
            if match:
                total_pages = int(match.group(1))
                max_page = max(max_page, total_pages)
                break
        
        return max_page
    
    def extract_announcement_links(self):
        """
        提取所有公告链接
        
        Returns:
            list: 包含(链接URL, 公告编号, 发布时间)的字典列表
        """
        links = []
        
        # 查找所有包含公告链接的元素
        list_items = self.soup.find_all('li')
        
        for item in list_items:
            link_tag = item.find('a')
            if link_tag and link_tag.get('href'):
                href = link_tag.get('href')
                # 跳过非详情页链接和分页链接
                if 'index.html' in href or not href.startswith('/'):
                    continue
                    
                full_url = self.urljoin(self.base_url, href)
                
                # 提取公告编号和发布时间
                text = self.clean_text(item.get_text())
                
                # 提取公告编号，格式如：沪劳人仲(2025)办字第1646号
                number_match = self.re.search(r'沪劳人仲[（(]\d{4}[）)][办]字第\d+号', text)
                if number_match:
                    announcement_number = number_match.group(0)
                else:
                    # 尝试其他格式
                    number_match2 = self.re.search(r'沪劳人仲.*?\d+号', text)
                    if number_match2:
                        announcement_number = number_match2.group(0)
                    else:
                        announcement_number = ''
                
                # 提取发布时间，格式如：2025-12-05
                date_match = self.re.search(r'(\d{4}-\d{2}-\d{2})', text)
                publish_date = date_match.group(1) if date_match else ''
                
                links.append({
                    'url': full_url,
                    'announcement_number': announcement_number,
                    'publish_date': publish_date
                })
        
        return links


class ArbitrationDetailPageParser:
    """仲裁公告详情页解析器"""
    
    def __init__(self, html_content):
        """
        初始化详情页解析器
        
        Args:
            html_content: HTML内容
        """
        from bs4 import BeautifulSoup
        import re
        from utils import clean_text
        
        self.soup = BeautifulSoup(html_content, 'lxml')
        self.re = re
        self.clean_text = clean_text
    
    def extract_announcement_info(self):
        """
        提取公告详细信息
        
        Returns:
            dict: 包含公告信息的字典
        """
        info = {}
        text_content = self.soup.get_text()
        
        # 提取公告编号，格式如：沪劳人仲(2025)办字第1646号
        number_match = self.re.search(r'沪劳人仲[（(]\d{4}[）)][办]字第\d+号', text_content)
        if number_match:
            info['announcement_number'] = number_match.group(0)
        else:
            # 尝试其他格式
            number_match2 = self.re.search(r'沪劳人仲.*?\d+号', text_content)
            if number_match2:
                info['announcement_number'] = number_match2.group(0)
            else:
                info['announcement_number'] = ''
        
        # 提取发布时间
        date_match = self.re.search(r'发布时间[：:]\s*(\d{4}-\d{2}-\d{2})', text_content)
        if date_match:
            info['publish_date'] = date_match.group(1)
        else:
            date_match2 = self.re.search(r'(\d{4}-\d{2}-\d{2})', text_content)
            if date_match2:
                info['publish_date'] = date_match2.group(1)
            else:
                info['publish_date'] = ''
        
        # 提取公司名称（被申请人）
        company_patterns = [
            r'([^：\n]*有限公司)[：:]',
            r'([^：\n]*股份[^：\n]*)[：:]',
            r'([^：\n]*企业[^：\n]*)[：:]',
            r'([^：\n]*公司)[：:]'
        ]
        
        company_name = ''
        for pattern in company_patterns:
            match = self.re.search(pattern, text_content)
            if match:
                potential_name = self.clean_text(match.group(1))
                if any(keyword in potential_name for keyword in ['公司', '企业', '股份', '有限']):
                    company_name = potential_name
                    break
        
        info['company_name'] = company_name
        
        # 提取申请人信息
        applicant_match = self.re.search(r'受理\s*([^与]+)\s*与', text_content)
        if applicant_match:
            info['applicant'] = self.clean_text(applicant_match.group(1))
        else:
            # 尝试其他格式
            applicant_match2 = self.re.search(r'申请人[：:]\s*([^\n]+)', text_content)
            if applicant_match2:
                info['applicant'] = self.clean_text(applicant_match2.group(1))
            else:
                info['applicant'] = ''
        
        # 提取案号
        case_number_match = self.re.search(r'案号[：:]\s*([^）\n]+)', text_content)
        if case_number_match:
            info['case_number'] = self.clean_text(case_number_match.group(1))
        else:
            info['case_number'] = ''
        
        # 提取裁决内容（包含金额信息）
        # 查找"裁决内容如下"之后的内容
        content_match = self.re.search(r'裁决内容[如下：:](.*?)(?:如不服|特此公告)', text_content, self.re.DOTALL)
        if content_match:
            info['ruling_content'] = self.clean_text(content_match.group(1))
        else:
            info['ruling_content'] = ''
        
        # 提取金额信息
        amount_patterns = [
            r'人民币\s*(\d+(?:\.\d+)?)\s*元',
            r'(\d+(?:\.\d+)?)\s*元',
            r'合计人民币\s*(\d+(?:\.\d+)?)\s*元'
        ]
        
        amounts = []
        for pattern in amount_patterns:
            matches = self.re.findall(pattern, text_content)
            amounts.extend(matches)
        
        info['amounts'] = ', '.join(amounts) if amounts else ''
        
        # 提取完整文本内容
        content_div = self.soup.find('div', class_=self.re.compile('content|main|detail|article'))
        if not content_div:
            content_div = self.soup.find('div', id=self.re.compile('content|main|detail|article'))
        if not content_div:
            content_div = self.soup.find('div', {'class': lambda x: x and ('content' in x.lower() or 'main' in x.lower())})
        
        if content_div:
            info['content'] = self.clean_text(content_div.get_text())
        else:
            body = self.soup.find('body')
            if body:
                info['content'] = self.clean_text(body.get_text())
            else:
                info['content'] = self.clean_text(text_content)
        
        return info


class ArbitrationSpider:
    """仲裁公告爬虫"""
    
    def __init__(self):
        """初始化爬虫"""
        self.session = self._create_session()
        self.base_url = 'https://rsj.sh.gov.cn'
        self.list_url = 'https://rsj.sh.gov.cn/tzcgg_17342/index.html'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    def _create_session(self):
        """创建带重试机制的session"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def fetch_page(self, url, max_retries=3):
        """
        获取网页内容
        
        Args:
            url: 目标URL
            max_retries: 最大重试次数
        
        Returns:
            str: HTML内容，失败返回None
        """
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                response.encoding = 'utf-8'
                return response.text
            except requests.exceptions.RequestException as e:
                logger.warning(f"获取页面失败 (尝试 {attempt + 1}/{max_retries}): {url}, 错误: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    logger.error(f"获取页面最终失败: {url}")
                    return None
    
    def get_list_page_url(self, page_num=1):
        """
        获取指定页码的列表页URL
        
        Args:
            page_num: 页码，从1开始
        
        Returns:
            str: 列表页URL
        """
        if page_num == 1:
            return self.list_url
        else:
            base_path = self.list_url.replace('index.html', '')
            return f"{base_path}index_{page_num}.html"
    
    def crawl_list_page(self, page_num=1):
        """
        爬取指定页码的列表页
        
        Args:
            page_num: 页码，从1开始
        
        Returns:
            tuple: (公告链接列表, 总页数)
        """
        page_url = self.get_list_page_url(page_num)
        logger.info(f"开始爬取列表页 (第{page_num}页): {page_url}")
        html_content = self.fetch_page(page_url)
        
        if not html_content:
            logger.error(f"列表页获取失败: {page_url}")
            return [], 1
        
        parser = ArbitrationListPageParser(html_content, self.base_url)
        links = parser.extract_announcement_links()
        
        total_pages = 1
        if page_num == 1:
            total_pages = parser.extract_total_pages()
            logger.info(f"检测到总页数: {total_pages}")
        
        logger.info(f"从第{page_num}页提取到 {len(links)} 条公告链接")
        return links, total_pages
    
    def crawl_all_pages(self, total_pages=None):
        """
        爬取所有页面的公告链接
        
        Args:
            total_pages: 总页数，如果为None则自动检测
        
        Returns:
            list: 所有公告链接列表
        """
        all_links = []
        
        # 先爬取第一页，获取总页数
        links, detected_pages = self.crawl_list_page(1)
        all_links.extend(links)
        
        if total_pages is None:
            total_pages = detected_pages
        
        logger.info(f"开始爬取所有 {total_pages} 页数据")
        
        # 从第2页开始爬取
        for page_num in range(2, total_pages + 1):
            links, _ = self.crawl_list_page(page_num)
            all_links.extend(links)
            time.sleep(0.5)
        
        logger.info(f"从所有页面共提取到 {len(all_links)} 条公告链接")
        return all_links
    
    def crawl_detail_page(self, url):
        """
        爬取详情页
        
        Args:
            url: 详情页URL
        
        Returns:
            dict: 公告信息字典，失败返回None
        """
        html_content = self.fetch_page(url)
        
        if not html_content:
            return None
        
        parser = ArbitrationDetailPageParser(html_content)
        info = parser.extract_announcement_info()
        info['url'] = url
        
        return info
    
    def crawl_all(self, total_pages=None):
        """
        爬取所有数据
        
        Args:
            total_pages: 总页数，如果为None则自动检测
        
        Returns:
            list: 所有公告信息列表
        """
        all_data = []
        
        # 获取所有页面的链接
        links = self.crawl_all_pages(total_pages)
        
        if not links:
            logger.warning("未获取到任何公告链接")
            return all_data
        
        # 去重
        seen_urls = set()
        unique_links = []
        for link_info in links:
            url = link_info['url']
            if url not in seen_urls:
                seen_urls.add(url)
                unique_links.append(link_info)
        
        logger.info(f"去重后共有 {len(unique_links)} 条唯一链接")
        
        # 遍历每个链接，爬取详情
        total = len(unique_links)
        for idx, link_info in enumerate(unique_links, 1):
            url = link_info['url']
            
            logger.info(f"正在爬取详情页 ({idx}/{total}): {url}")
            
            detail_info = self.crawl_detail_page(url)
            
            if detail_info:
                # 合并列表页和详情页的信息
                detail_info['announcement_number'] = link_info.get('announcement_number', detail_info.get('announcement_number', ''))
                if not detail_info.get('publish_date'):
                    detail_info['publish_date'] = link_info.get('publish_date', '')
                all_data.append(detail_info)
                logger.info(f"成功获取公告: {detail_info.get('announcement_number', '未知编号')}")
            else:
                logger.warning(f"获取详情页失败: {url}")
            
            time.sleep(1)
        
        logger.info(f"爬取完成，共获取 {len(all_data)} 条数据")
        return all_data
