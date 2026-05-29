"""
幂等性测试模块
验证接口在多次相同请求下的响应一致性
"""
import asyncio
from typing import List, Dict, Any, Optional
from src.concurrent_test import ConcurrentTester, RequestResult
from config.settings import settings


class IdempotencyTester:
    """幂等性测试器"""
    
    def __init__(self, concurrent_tester: Optional[ConcurrentTester] = None):
        """
        初始化幂等性测试器
        
        Args:
            concurrent_tester: 并发测试器实例
        """
        self.concurrent_tester = concurrent_tester or ConcurrentTester()
        self.results: List[RequestResult] = []
    
    async def idempotency_test(
        self,
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        test_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        执行幂等性测试
        
        Args:
            url: 接口 URL
            headers: 请求头
            test_count: 测试请求次数
            
        Returns:
            Dict: 包含测试结果和分析的字典
        """
        url = url or settings.api.url
        headers = headers or settings.api.headers.copy()
        test_count = test_count or settings.test.idempotency_test_count
        
        # 使用并发测试器发送多次相同请求
        # 设置并发数为1，确保请求按顺序发送（避免并发影响）
        result = await self.concurrent_tester.concurrent_test(
            url=url,
            headers=headers,
            concurrency=1,
            total_requests=test_count,
            use_proxy=False,
            use_fake_header=False
        )
        
        # 从字典重建 RequestResult，排除 timestamp（它会在 __init__ 中自动生成）
        self.results = []
        for r in result["results"]:
            r_copy = r.copy()
            r_copy.pop("timestamp", None)  # 移除 timestamp，让 __init__ 生成新的
            self.results.append(RequestResult(**r_copy))
        
        # 分析幂等性
        analysis = self._analyze_idempotency()
        
        return {
            "results": [r.to_dict() for r in self.results],
            "analysis": analysis
        }
    
    def _analyze_idempotency(self) -> Dict[str, Any]:
        """
        分析幂等性
        
        Returns:
            Dict: 幂等性分析结果
        """
        if not self.results:
            return {"is_idempotent": False, "reason": "No results"}
        
        # 检查所有请求是否成功
        all_success = all(r.success for r in self.results)
        if not all_success:
            failed_count = sum(1 for r in self.results if not r.success)
            return {
                "is_idempotent": False,
                "reason": f"{failed_count} requests failed",
                "failed_requests": failed_count
            }
        
        # 检查状态码一致性
        status_codes = [r.status_code for r in self.results]
        unique_status_codes = set(status_codes)
        if len(unique_status_codes) > 1:
            return {
                "is_idempotent": False,
                "reason": "Status codes are inconsistent",
                "status_codes": list(unique_status_codes),
                "status_code_distribution": {code: status_codes.count(code) for code in unique_status_codes}
            }
        
        # 检查响应体一致性
        response_bodies = [r.response_body for r in self.results if r.response_body]
        if not response_bodies:
            return {
                "is_idempotent": False,
                "reason": "No response bodies"
            }
        
        # 比较所有响应体是否完全相同
        first_body = response_bodies[0]
        all_same = all(body == first_body for body in response_bodies)
        
        if all_same:
            # 响应体完全一致
            response_times = [r.response_time for r in self.results]
            avg_time = sum(response_times) / len(response_times)
            variance = sum((t - avg_time) ** 2 for t in response_times) / len(response_times)
            
            return {
                "is_idempotent": True,
                "reason": "All responses are identical",
                "response_consistency": 100.0,
                "avg_response_time": avg_time,
                "response_time_variance": variance,
                "response_time_std": variance ** 0.5
            }
        else:
            # 响应体不一致，计算相似度
            unique_bodies = set(response_bodies)
            consistency = (len(response_bodies) - len(unique_bodies) + 1) / len(response_bodies) * 100
            
            # 检查是否只是时间戳等动态字段不同
            # 简单检查：如果响应体长度差异很小，可能是动态字段
            body_lengths = [len(body) for body in response_bodies]
            length_variance = sum((l - sum(body_lengths) / len(body_lengths)) ** 2 for l in body_lengths) / len(body_lengths)
            length_std = length_variance ** 0.5
            avg_length = sum(body_lengths) / len(body_lengths)
            
            # 如果长度标准差小于平均长度的5%，认为可能是动态字段差异
            is_likely_dynamic_field = length_std < avg_length * 0.05 if avg_length > 0 else False
            
            return {
                "is_idempotent": False if consistency < 100 else True,
                "reason": "Response bodies are not identical" if not is_likely_dynamic_field else "Response bodies differ slightly (possibly due to dynamic fields)",
                "response_consistency": consistency,
                "unique_responses": len(unique_bodies),
                "total_responses": len(response_bodies),
                "is_likely_dynamic_field": is_likely_dynamic_field,
                "response_body_length_stats": {
                    "avg": avg_length,
                    "min": min(body_lengths),
                    "max": max(body_lengths),
                    "std": length_std
                }
            }
    
    async def concurrent_idempotency_test(
        self,
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        test_count: Optional[int] = None,
        concurrency: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        并发幂等性测试（同时发送多个相同请求，测试并发下的幂等性）
        
        Args:
            url: 接口 URL
            headers: 请求头
            test_count: 测试请求次数
            concurrency: 并发数
            
        Returns:
            Dict: 包含测试结果和分析的字典
        """
        url = url or settings.api.url
        headers = headers or settings.api.headers.copy()
        test_count = test_count or settings.test.idempotency_test_count
        concurrency = concurrency or min(settings.test.concurrency, test_count)
        
        # 使用并发测试器同时发送多个相同请求
        result = await self.concurrent_tester.concurrent_test(
            url=url,
            headers=headers,
            concurrency=concurrency,
            total_requests=test_count,
            use_proxy=False,
            use_fake_header=False
        )
        
        # 从字典重建 RequestResult，排除 timestamp（它会在 __init__ 中自动生成）
        self.results = []
        for r in result["results"]:
            r_copy = r.copy()
            r_copy.pop("timestamp", None)  # 移除 timestamp，让 __init__ 生成新的
            self.results.append(RequestResult(**r_copy))
        
        # 分析幂等性
        analysis = self._analyze_idempotency()
        
        return {
            "results": [r.to_dict() for r in self.results],
            "analysis": analysis,
            "concurrency": concurrency
        }
