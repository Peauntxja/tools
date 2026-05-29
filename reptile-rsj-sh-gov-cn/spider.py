"""
爬虫核心模块
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


class RSJSpider:
    """上海市人社局社保稽核公告爬虫"""
    
    def __init__(self):
        """初始化爬虫"""
        self.session = self._create_session()
        self.base_url = 'https://rsj.sh.gov.cn'
        self.list_url = 'https://rsj.sh.gov.cn/tsbjhzsgg_17345/index.html'
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
                    time.sleep(2 ** attempt)  # 指数退避
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
            # 尝试不同的分页URL格式
            # 格式1: index_2.html, index_3.html
            # 格式2: index.html?page=2
            # 格式3: index_1.html (第2页)
            base_path = self.list_url.replace('index.html', '')
            return f"{base_path}index_{page_num}.html"
    
    def crawl_list_page(self, page_num=1):
        """
        爬取指定页码的列表页，获取所有公告链接
        
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
        
        parser = ListPageParser(html_content, self.base_url)
        links = parser.extract_announcement_links()
        
        # 如果是第一页，尝试获取总页数
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
        
        # 使用用户提供的总页数或检测到的总页数
        if total_pages is None:
            total_pages = detected_pages
        
        logger.info(f"开始爬取所有 {total_pages} 页数据")
        
        # 从第2页开始爬取
        for page_num in range(2, total_pages + 1):
            links, _ = self.crawl_list_page(page_num)
            all_links.extend(links)
            # 避免请求过快
            time.sleep(0.5)
        
        logger.info(f"从所有页面共提取到 {len(all_links)} 条公告链接")
        return all_links
    
    def crawl_detail_page(self, url):
        """
        爬取详情页，获取公告详细信息
        
        Args:
            url: 详情页URL
        
        Returns:
            dict: 公告信息字典，失败返回None
        """
        html_content = self.fetch_page(url)
        
        if not html_content:
            return None
        
        parser = DetailPageParser(html_content)
        info = parser.extract_announcement_info()
        info['url'] = url
        
        return info
    
    def crawl_all(self, filter_by_year=True, total_pages=None):
        """
        爬取所有数据
        
        Args:
            filter_by_year: 是否只爬取最近一年的数据
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
        
        # 去重：根据URL去重
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
            publish_date = link_info.get('publish_date', '')
            
            # 如果设置了年份过滤，检查日期
            if filter_by_year:
                if publish_date:
                    if not is_within_year(publish_date):
                        logger.info(f"跳过非最近一年的公告: {url} ({publish_date})")
                        continue
                else:
                    # 如果列表页没有日期，尝试从URL提取
                    url_date = extract_date_from_url(url)
                    if url_date and not is_within_year(url_date):
                        logger.info(f"跳过非最近一年的公告: {url} ({url_date})")
                        continue
            
            logger.info(f"正在爬取详情页 ({idx}/{total}): {url}")
            
            detail_info = self.crawl_detail_page(url)
            
            if detail_info:
                # 合并列表页和详情页的信息
                detail_info['announcement_number'] = link_info.get('announcement_number', detail_info.get('announcement_number', ''))
                if not detail_info.get('publish_date'):
                    detail_info['publish_date'] = publish_date
                all_data.append(detail_info)
                logger.info(f"成功获取公告: {detail_info.get('announcement_number', '未知编号')}")
            else:
                logger.warning(f"获取详情页失败: {url}")
            
            # 避免请求过快
            time.sleep(1)
        
        logger.info(f"爬取完成，共获取 {len(all_data)} 条数据")
        return all_data
