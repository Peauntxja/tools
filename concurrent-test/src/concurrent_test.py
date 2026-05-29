"""
并发测试核心模块
使用 asyncio + aiohttp 实现高并发请求测试
"""
import asyncio
import time
from typing import List, Dict, Optional, Any
import aiohttp
from config.settings import settings
from src.ip_simulator import IPSimulator


class RequestResult:
    """请求结果数据类"""
    
    def __init__(self, request_id: int, success: bool, status_code: Optional[int] = None,
                 response_time: float = 0.0, response_body: Optional[str] = None,
                 error_message: Optional[str] = None, headers: Optional[Dict] = None):
        self.request_id = request_id
        self.success = success
        self.status_code = status_code
        self.response_time = response_time
        self.response_body = response_body
        self.error_message = error_message
        self.headers = headers or {}
        self.timestamp = time.time()
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "request_id": self.request_id,
            "success": self.success,
            "status_code": self.status_code,
            "response_time": self.response_time,
            "response_body": self.response_body,
            "error_message": self.error_message,
            "headers": dict(self.headers),
            "timestamp": self.timestamp
        }


class ConcurrentTester:
    """并发测试器"""
    
    def __init__(self, ip_simulator: Optional[IPSimulator] = None):
        """
        初始化并发测试器
        
        Args:
            ip_simulator: IP 模拟器实例
        """
        self.ip_simulator = ip_simulator or IPSimulator()
        self.results: List[RequestResult] = []
    
    async def send_request(
        self,
        session: aiohttp.ClientSession,
        url: str,
        headers: Dict[str, str],
        semaphore: asyncio.Semaphore,
        request_id: int,
        proxy: Optional[str] = None
    ) -> RequestResult:
        """
        发送单个请求
        
        Args:
            session: aiohttp 会话
            url: 请求 URL
            headers: 请求头
            semaphore: 信号量控制并发
            request_id: 请求 ID
            proxy: 代理地址
            
        Returns:
            RequestResult: 请求结果
        """
        async with semaphore:
            start_time = time.time()
            try:
                timeout = aiohttp.ClientTimeout(total=settings.test.timeout)
                async with session.request(
                    method=settings.api.method,
                    url=url,
                    headers=headers,
                    data=settings.api.body,
                    proxy=proxy,
                    timeout=timeout
                ) as response:
                    response_time = time.time() - start_time
                    response_body = await response.text()
                    
                    return RequestResult(
                        request_id=request_id,
                        success=200 <= response.status < 300,
                        status_code=response.status,
                        response_time=response_time,
                        response_body=response_body,
                        headers=dict(response.headers)
                    )
            except asyncio.TimeoutError:
                return RequestResult(
                    request_id=request_id,
                    success=False,
                    response_time=time.time() - start_time,
                    error_message="Request timeout"
                )
            except Exception as e:
                return RequestResult(
                    request_id=request_id,
                    success=False,
                    response_time=time.time() - start_time,
                    error_message=str(e)
                )
    
    async def concurrent_test(
        self,
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        concurrency: Optional[int] = None,
        total_requests: Optional[int] = None,
        use_proxy: bool = False,
        use_fake_header: bool = False
    ) -> Dict[str, Any]:
        """
        执行并发测试
        
        Args:
            url: 接口 URL，如果为 None 则使用配置中的 URL
            headers: 请求头，如果为 None 则使用配置中的请求头
            concurrency: 并发数，如果为 None 则使用配置中的并发数
            total_requests: 总请求数，如果为 None 则使用配置中的总请求数
            use_proxy: 是否使用代理
            use_fake_header: 是否使用伪造请求头
            
        Returns:
            Dict: 包含结果列表和统计信息的字典
        """
        url = url or settings.api.url
        concurrency = concurrency or settings.test.concurrency
        total_requests = total_requests or settings.test.total_requests
        
        # 获取请求配置
        if use_proxy or use_fake_header:
            request_config = self.ip_simulator.get_request_config(use_proxy, use_fake_header)
            headers = headers or request_config["headers"]
            proxy = request_config["proxy"] if use_proxy else None
        else:
            headers = headers or settings.api.headers.copy()
            proxy = None
        
        # 创建信号量控制并发
        semaphore = asyncio.Semaphore(concurrency)
        
        # 创建会话
        connector = aiohttp.TCPConnector(limit=concurrency * 2)
        timeout = aiohttp.ClientTimeout(total=settings.test.timeout)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # 创建所有请求任务
            tasks = [
                self.send_request(session, url, headers, semaphore, i, proxy)
                for i in range(total_requests)
            ]
            
            # 执行所有请求
            self.results = await asyncio.gather(*tasks)
        
        # 计算统计信息
        stats = self._calculate_statistics()
        
        return {
            "results": [r.to_dict() for r in self.results],
            "statistics": stats
        }
    
    def _calculate_statistics(self) -> Dict[str, Any]:
        """
        计算统计信息
        
        Returns:
            Dict: 统计信息
        """
        if not self.results:
            return {}
        
        total = len(self.results)
        successful = sum(1 for r in self.results if r.success)
        failed = total - successful
        
        response_times = [r.response_time for r in self.results if r.success]
        
        stats = {
            "total_requests": total,
            "successful_requests": successful,
            "failed_requests": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0,
        }
        
        if response_times:
            response_times.sort()
            stats["avg_response_time"] = sum(response_times) / len(response_times)
            stats["min_response_time"] = min(response_times)
            stats["max_response_time"] = max(response_times)
            stats["p50_response_time"] = response_times[len(response_times) // 2]
            stats["p95_response_time"] = response_times[int(len(response_times) * 0.95)]
            stats["p99_response_time"] = response_times[int(len(response_times) * 0.99)]
            
            # 计算 QPS（基于总时间和成功请求数）
            total_time = max(r.timestamp for r in self.results) - min(r.timestamp for r in self.results)
            if total_time > 0:
                stats["qps"] = successful / total_time
            else:
                stats["qps"] = 0
        else:
            stats["avg_response_time"] = 0
            stats["min_response_time"] = 0
            stats["max_response_time"] = 0
            stats["p50_response_time"] = 0
            stats["p95_response_time"] = 0
            stats["p99_response_time"] = 0
            stats["qps"] = 0
        
        # 状态码分布
        status_code_dist = {}
        for r in self.results:
            if r.status_code:
                status_code_dist[r.status_code] = status_code_dist.get(r.status_code, 0) + 1
        stats["status_code_distribution"] = status_code_dist
        
        # 错误分布
        error_dist = {}
        for r in self.results:
            if r.error_message:
                error_dist[r.error_message] = error_dist.get(r.error_message, 0) + 1
        stats["error_distribution"] = error_dist
        
        return stats
