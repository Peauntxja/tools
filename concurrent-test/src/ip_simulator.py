"""
IP 模拟工具
支持代理池管理和请求头修改
"""
import random
import asyncio
from typing import List, Optional, Dict
from urllib.parse import urlparse
import aiohttp
from config.settings import settings


class ProxyPool:
    """代理池管理"""
    
    def __init__(self, proxy_list: List[str], rotation_strategy: str = "round_robin"):
        """
        初始化代理池
        
        Args:
            proxy_list: 代理列表
            rotation_strategy: 轮换策略 (round_robin, random)
        """
        self.proxy_list = proxy_list
        self.rotation_strategy = rotation_strategy
        self.current_index = 0
        self.valid_proxies = []
        self.invalid_proxies = []
    
    async def validate_proxy(self, proxy: str) -> bool:
        """
        验证代理是否可用
        
        Args:
            proxy: 代理地址
            
        Returns:
            bool: 代理是否可用
        """
        try:
            parsed = urlparse(proxy)
            test_url = f"{parsed.scheme}://httpbin.org/ip"
            timeout = aiohttp.ClientTimeout(total=5)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(test_url, proxy=proxy) as response:
                    if response.status == 200:
                        return True
        except Exception:
            pass
        return False
    
    async def initialize(self):
        """初始化代理池，验证所有代理"""
        if not self.proxy_list:
            return
        
        tasks = [self.validate_proxy(proxy) for proxy in self.proxy_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for proxy, is_valid in zip(self.proxy_list, results):
            if is_valid is True:
                self.valid_proxies.append(proxy)
            else:
                self.invalid_proxies.append(proxy)
    
    def get_proxy(self) -> Optional[str]:
        """
        获取下一个代理
        
        Returns:
            Optional[str]: 代理地址，如果无可用代理返回 None
        """
        if not self.valid_proxies:
            return None
        
        if self.rotation_strategy == "round_robin":
            proxy = self.valid_proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.valid_proxies)
            return proxy
        elif self.rotation_strategy == "random":
            return random.choice(self.valid_proxies)
        else:
            return self.valid_proxies[0]
    
    def mark_invalid(self, proxy: str):
        """标记代理为无效"""
        if proxy in self.valid_proxies:
            self.valid_proxies.remove(proxy)
            self.invalid_proxies.append(proxy)


class IPSimulator:
    """IP 模拟器"""
    
    def __init__(self):
        self.proxy_pool = None
        if settings.proxy.enable_proxy and settings.proxy.proxy_list:
            self.proxy_pool = ProxyPool(
                settings.proxy.proxy_list,
                settings.proxy.proxy_rotation
            )
    
    async def initialize(self):
        """初始化 IP 模拟器"""
        if self.proxy_pool:
            await self.proxy_pool.initialize()
    
    def get_proxy(self) -> Optional[str]:
        """
        获取代理地址
        
        Returns:
            Optional[str]: 代理地址
        """
        if self.proxy_pool:
            return self.proxy_pool.get_proxy()
        return None
    
    def generate_fake_ip(self) -> str:
        """
        生成随机 IP 地址用于请求头
        
        Returns:
            str: 随机 IP 地址
        """
        return f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
    
    def modify_headers(self, headers: Dict[str, str], fake_ip: Optional[str] = None) -> Dict[str, str]:
        """
        修改请求头以模拟不同 IP
        
        Args:
            headers: 原始请求头
            fake_ip: 伪造的 IP 地址，如果为 None 则自动生成
            
        Returns:
            Dict[str, str]: 修改后的请求头
        """
        if not settings.proxy.enable_header_manipulation:
            return headers
        
        modified_headers = headers.copy()
        if fake_ip is None:
            fake_ip = self.generate_fake_ip()
        
        # 设置常见的 IP 相关请求头
        modified_headers["X-Forwarded-For"] = fake_ip
        modified_headers["X-Real-IP"] = fake_ip
        modified_headers["X-Forwarded"] = fake_ip
        modified_headers["Forwarded-For"] = fake_ip
        modified_headers["Forwarded"] = f"for={fake_ip}"
        
        return modified_headers
    
    def get_request_config(self, use_proxy: bool = True, use_fake_header: bool = True) -> Dict:
        """
        获取请求配置（代理和请求头）
        
        Args:
            use_proxy: 是否使用代理
            use_fake_header: 是否使用伪造请求头
            
        Returns:
            Dict: 包含 proxy 和 headers 的配置字典
        """
        config = {
            "proxy": None,
            "headers": settings.api.headers.copy()
        }
        
        if use_proxy and self.proxy_pool:
            config["proxy"] = self.get_proxy()
        
        if use_fake_header:
            config["headers"] = self.modify_headers(config["headers"])
        
        return config
