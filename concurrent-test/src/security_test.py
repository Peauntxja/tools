"""
安全性测试模块
包括 IP 限制测试、Token 验证测试、并发安全测试
"""
import asyncio
from typing import List, Dict, Any, Optional
from src.concurrent_test import ConcurrentTester, RequestResult
from src.ip_simulator import IPSimulator
from src.advanced_security_test import AdvancedSecurityTester
from config.settings import settings


class SecurityTester:
    """安全性测试器"""
    
    def __init__(self, concurrent_tester: Optional[ConcurrentTester] = None,
                 ip_simulator: Optional[IPSimulator] = None):
        """
        初始化安全性测试器
        
        Args:
            concurrent_tester: 并发测试器实例
            ip_simulator: IP 模拟器实例
        """
        self.concurrent_tester = concurrent_tester or ConcurrentTester()
        self.ip_simulator = ip_simulator or IPSimulator()
        self.advanced_tester = AdvancedSecurityTester(self.concurrent_tester)
        self.results: Dict[str, Any] = {}
    
    async def initialize(self):
        """初始化安全性测试器"""
        await self.ip_simulator.initialize()
    
    async def ip_restriction_test(
        self,
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        IP 限制测试
        
        Args:
            url: 接口 URL
            headers: 请求头
            
        Returns:
            Dict: IP 限制测试结果
        """
        url = url or settings.api.url
        headers = headers or settings.api.headers.copy()
        
        test_results = {}
        
        # 1. 基准测试：使用真实 IP
        print("执行基准测试（真实 IP）...")
        baseline_result = await self.concurrent_tester.concurrent_test(
            url=url,
            headers=headers,
            concurrency=5,
            total_requests=10,
            use_proxy=False,
            use_fake_header=False
        )
        test_results["baseline"] = baseline_result
        
        # 2. 使用代理池测试
        if settings.proxy.enable_proxy and self.ip_simulator.proxy_pool:
            print("执行代理池测试...")
            proxy_result = await self.concurrent_tester.concurrent_test(
                url=url,
                headers=headers,
                concurrency=5,
                total_requests=10,
                use_proxy=True,
                use_fake_header=False
            )
            test_results["proxy"] = proxy_result
        else:
            test_results["proxy"] = {"note": "Proxy not enabled or no proxy available"}
        
        # 3. 使用请求头修改测试
        if settings.proxy.enable_header_manipulation:
            print("执行请求头修改测试...")
            header_result = await self.concurrent_tester.concurrent_test(
                url=url,
                headers=headers,
                concurrency=5,
                total_requests=10,
                use_proxy=False,
                use_fake_header=True
            )
            test_results["header_manipulation"] = header_result
        else:
            test_results["header_manipulation"] = {"note": "Header manipulation not enabled"}
        
        # 分析 IP 限制
        analysis = self._analyze_ip_restriction(test_results)
        
        return {
            "test_results": test_results,
            "analysis": analysis
        }
    
    def _analyze_ip_restriction(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析 IP 限制情况
        
        Args:
            test_results: 测试结果
            
        Returns:
            Dict: IP 限制分析结果
        """
        analysis = {
            "ip_restriction_detected": False,
            "restriction_type": None,
            "details": {}
        }
        
        baseline_stats = test_results.get("baseline", {}).get("statistics", {})
        baseline_status_codes = baseline_stats.get("status_code_distribution", {})
        
        # 检查基准测试中的限制状态码
        restricted_codes = {403, 429, 401}
        baseline_restricted = any(code in restricted_codes for code in baseline_status_codes.keys())
        
        if baseline_restricted:
            analysis["ip_restriction_detected"] = True
            analysis["restriction_type"] = "baseline_ip_restricted"
            analysis["details"]["baseline"] = "Baseline IP is already restricted"
            return analysis
        
        # 比较代理测试结果
        if "proxy" in test_results and "statistics" in test_results["proxy"]:
            proxy_stats = test_results["proxy"]["statistics"]
            proxy_status_codes = proxy_stats.get("status_code_distribution", {})
            proxy_restricted = any(code in restricted_codes for code in proxy_status_codes.keys())
            
            if proxy_restricted:
                analysis["ip_restriction_detected"] = True
                analysis["restriction_type"] = "proxy_ip_restricted"
                analysis["details"]["proxy"] = {
                    "restricted_status_codes": [code for code in proxy_status_codes.keys() if code in restricted_codes],
                    "success_rate": proxy_stats.get("success_rate", 0)
                }
        
        # 比较请求头修改测试结果
        if "header_manipulation" in test_results and "statistics" in test_results["header_manipulation"]:
            header_stats = test_results["header_manipulation"]["statistics"]
            header_status_codes = header_stats.get("status_code_distribution", {})
            header_restricted = any(code in restricted_codes for code in header_status_codes.keys())
            
            if header_restricted:
                analysis["ip_restriction_detected"] = True
                if analysis["restriction_type"] is None:
                    analysis["restriction_type"] = "header_manipulation_restricted"
                analysis["details"]["header_manipulation"] = {
                    "restricted_status_codes": [code for code in header_status_codes.keys() if code in restricted_codes],
                    "success_rate": header_stats.get("success_rate", 0)
                }
        
        if not analysis["ip_restriction_detected"]:
            analysis["details"]["conclusion"] = "No IP restriction detected in tests"
        
        return analysis
    
    async def token_validation_test(
        self,
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Token 验证测试
        
        Args:
            url: 接口 URL
            headers: 请求头
            
        Returns:
            Dict: Token 验证测试结果
        """
        url = url or settings.api.url
        base_headers = headers or settings.api.headers.copy()
        
        test_results = {}
        
        # 1. 有效 token 测试（基准）
        print("测试有效 token...")
        valid_result = await self.concurrent_tester.concurrent_test(
            url=url,
            headers=base_headers,
            concurrency=1,
            total_requests=5,
            use_proxy=False,
            use_fake_header=False
        )
        test_results["valid_token"] = valid_result
        
        # 2. 无效 token 测试
        print("测试无效 token...")
        invalid_headers = base_headers.copy()
        invalid_headers["token"] = "invalid_token_12345"
        invalid_result = await self.concurrent_tester.concurrent_test(
            url=url,
            headers=invalid_headers,
            concurrency=1,
            total_requests=5,
            use_proxy=False,
            use_fake_header=False
        )
        test_results["invalid_token"] = invalid_result
        
        # 3. 空 token 测试
        print("测试空 token...")
        empty_headers = base_headers.copy()
        empty_headers["token"] = ""
        empty_result = await self.concurrent_tester.concurrent_test(
            url=url,
            headers=empty_headers,
            concurrency=1,
            total_requests=5,
            use_proxy=False,
            use_fake_header=False
        )
        test_results["empty_token"] = empty_result
        
        # 4. 缺少 token 测试
        print("测试缺少 token...")
        no_token_headers = base_headers.copy()
        if "token" in no_token_headers:
            del no_token_headers["token"]
        no_token_result = await self.concurrent_tester.concurrent_test(
            url=url,
            headers=no_token_headers,
            concurrency=1,
            total_requests=5,
            use_proxy=False,
            use_fake_header=False
        )
        test_results["no_token"] = no_token_result
        
        # 5. 格式错误的 token 测试
        print("测试格式错误的 token...")
        malformed_headers = base_headers.copy()
        malformed_headers["token"] = "not_a_valid_token_format!!!"
        malformed_result = await self.concurrent_tester.concurrent_test(
            url=url,
            headers=malformed_headers,
            concurrency=1,
            total_requests=5,
            use_proxy=False,
            use_fake_header=False
        )
        test_results["malformed_token"] = malformed_result
        
        # 分析 token 验证
        analysis = self._analyze_token_validation(test_results)
        
        return {
            "test_results": test_results,
            "analysis": analysis
        }
    
    def _analyze_token_validation(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析 Token 验证情况
        
        Args:
            test_results: 测试结果
            
        Returns:
            Dict: Token 验证分析结果
        """
        analysis = {
            "token_validation_working": False,
            "validation_strength": "unknown",
            "details": {}
        }
        
        # 检查有效 token 是否成功
        valid_stats = test_results.get("valid_token", {}).get("statistics", {})
        valid_success_rate = valid_stats.get("success_rate", 0)
        
        if valid_success_rate > 80:
            analysis["token_validation_working"] = True
        
        # 检查无效 token 是否被拒绝
        invalid_stats = test_results.get("invalid_token", {}).get("statistics", {})
        invalid_status_codes = invalid_stats.get("status_code_distribution", {})
        invalid_rejected = any(code in {401, 403} for code in invalid_status_codes.keys())
        
        empty_stats = test_results.get("empty_token", {}).get("statistics", {})
        empty_status_codes = empty_stats.get("status_code_distribution", {})
        empty_rejected = any(code in {401, 403} for code in empty_status_codes.keys())
        
        no_token_stats = test_results.get("no_token", {}).get("statistics", {})
        no_token_status_codes = no_token_stats.get("status_code_distribution", {})
        no_token_rejected = any(code in {401, 403} for code in no_token_status_codes.keys())
        
        malformed_stats = test_results.get("malformed_token", {}).get("statistics", {})
        malformed_status_codes = malformed_stats.get("status_code_distribution", {})
        malformed_rejected = any(code in {401, 403} for code in malformed_status_codes.keys())
        
        rejection_count = sum([
            invalid_rejected,
            empty_rejected,
            no_token_rejected,
            malformed_rejected
        ])
        
        if rejection_count == 4:
            analysis["validation_strength"] = "strong"
        elif rejection_count >= 2:
            analysis["validation_strength"] = "moderate"
        else:
            analysis["validation_strength"] = "weak"
        
        analysis["details"] = {
            "valid_token_success_rate": valid_success_rate,
            "invalid_token_rejected": invalid_rejected,
            "empty_token_rejected": empty_rejected,
            "no_token_rejected": no_token_rejected,
            "malformed_token_rejected": malformed_rejected,
            "total_rejection_cases": rejection_count
        }
        
        return analysis
    
    async def concurrent_security_test(
        self,
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        concurrency: Optional[int] = None,
        total_requests: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        并发安全测试（检测高并发下的数据一致性和竞态条件）
        
        Args:
            url: 接口 URL
            headers: 请求头
            concurrency: 并发数
            total_requests: 总请求数
            
        Returns:
            Dict: 并发安全测试结果
        """
        url = url or settings.api.url
        headers = headers or settings.api.headers.copy()
        concurrency = concurrency or settings.test.concurrency
        total_requests = total_requests or settings.test.total_requests
        
        print(f"执行并发安全测试（并发数: {concurrency}, 总请求数: {total_requests}）...")
        
        # 执行高并发测试
        result = await self.concurrent_tester.concurrent_test(
            url=url,
            headers=headers,
            concurrency=concurrency,
            total_requests=total_requests,
            use_proxy=False,
            use_fake_header=False
        )
        
        # 分析并发安全性
        analysis = self._analyze_concurrent_security(result)
        
        return {
            "test_results": result,
            "analysis": analysis
        }
    
    def _analyze_concurrent_security(self, test_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析并发安全性
        
        Args:
            test_result: 测试结果
            
        Returns:
            Dict: 并发安全分析结果
        """
        analysis = {
            "concurrent_safety": "unknown",
            "data_consistency": "unknown",
            "details": {}
        }
        
        stats = test_result.get("statistics", {})
        results = test_result.get("results", [])
        
        # 检查响应一致性
        response_bodies = [r.get("response_body") for r in results if r.get("success") and r.get("response_body")]
        
        if response_bodies:
            unique_responses = len(set(response_bodies))
            total_responses = len(response_bodies)
            consistency_rate = (total_responses - unique_responses + 1) / total_responses * 100 if total_responses > 0 else 0
            
            if consistency_rate >= 95:
                analysis["data_consistency"] = "high"
            elif consistency_rate >= 80:
                analysis["data_consistency"] = "moderate"
            else:
                analysis["data_consistency"] = "low"
            
            analysis["details"]["response_consistency_rate"] = consistency_rate
            analysis["details"]["unique_responses"] = unique_responses
            analysis["details"]["total_responses"] = total_responses
        
        # 检查错误率
        success_rate = stats.get("success_rate", 0)
        if success_rate >= 95:
            analysis["concurrent_safety"] = "high"
        elif success_rate >= 80:
            analysis["concurrent_safety"] = "moderate"
        else:
            analysis["concurrent_safety"] = "low"
        
        analysis["details"]["success_rate"] = success_rate
        analysis["details"]["error_distribution"] = stats.get("error_distribution", {})
        
        # 检查响应时间稳定性
        if "p95_response_time" in stats and "p50_response_time" in stats:
            time_variance = stats["p95_response_time"] - stats["p50_response_time"]
            analysis["details"]["response_time_variance"] = time_variance
        
        return analysis
    
    async def advanced_security_test(
        self,
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        执行所有高级安全性测试
        
        Args:
            url: 接口 URL
            headers: 请求头
            
        Returns:
            Dict: 高级安全性测试结果
        """
        url = url or settings.api.url
        headers = headers or settings.api.headers.copy()
        
        advanced_results = {}
        
        # 1. 协议与链路安全测试
        print("执行协议与链路安全测试...")
        protocol_result = await self.advanced_tester.protocol_security_test(url, headers)
        advanced_results["protocol_security"] = protocol_result
        
        # 2. 缓存控制测试
        print("执行缓存控制测试...")
        cache_result = await self.advanced_tester.cache_control_test(url, headers)
        advanced_results["cache_control"] = cache_result
        
        # 3. CORS 与 Referrer 测试
        print("执行 CORS 与 Referrer 测试...")
        cors_result = await self.advanced_tester.cors_and_referrer_test(url, headers)
        advanced_results["cors_and_referrer"] = cors_result
        
        # 4. 模糊测试
        print("执行模糊测试...")
        fuzzing_result = await self.advanced_tester.fuzzing_test(url, headers)
        advanced_results["fuzzing"] = fuzzing_result
        
        # 5. 生命周期测试
        print("执行生命周期测试...")
        lifecycle_result = await self.advanced_tester.lifecycle_test(url, headers)
        advanced_results["lifecycle"] = lifecycle_result
        
        return advanced_results