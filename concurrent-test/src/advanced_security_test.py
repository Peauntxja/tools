"""
高级安全性测试模块
包括协议安全、缓存控制、CORS、模糊测试、生命周期测试
"""
import asyncio
import time
import json
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import aiohttp
from src.concurrent_test import ConcurrentTester, RequestResult
from config.settings import settings


class AdvancedSecurityTester:
    """高级安全性测试器"""
    
    def __init__(self, concurrent_tester: Optional[ConcurrentTester] = None):
        """
        初始化高级安全性测试器
        
        Args:
            concurrent_tester: 并发测试器实例
        """
        self.concurrent_tester = concurrent_tester or ConcurrentTester()
    
    async def protocol_security_test(
        self,
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        协议与链路安全测试
        1. HTTPS 支持测试
        2. 重放攻击测试
        
        Args:
            url: 接口 URL
            headers: 请求头
            
        Returns:
            Dict: 协议安全测试结果
        """
        url = url or settings.api.url
        headers = headers or settings.api.headers.copy()
        
        test_results = {}
        
        # 1. HTTPS 支持测试
        print("测试 HTTPS 支持...")
        parsed_url = urlparse(url)
        is_http = parsed_url.scheme == "http"
        
        https_url = None
        if is_http:
            https_url = url.replace("http://", "https://", 1)
        
        https_supported = False
        https_error = None
        
        if https_url:
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(https_url, headers=headers) as response:
                        if response.status < 500:  # 不是服务器错误，说明 HTTPS 可能支持
                            https_supported = True
            except aiohttp.ClientConnectorError as e:
                https_error = f"HTTPS connection failed: {str(e)}"
            except asyncio.TimeoutError:
                https_error = "HTTPS connection timeout"
            except Exception as e:
                https_error = f"HTTPS test error: {str(e)}"
        
        test_results["https_support"] = {
            "current_protocol": parsed_url.scheme,
            "is_http": is_http,
            "https_supported": https_supported,
            "https_error": https_error,
            "recommendation": "使用 HTTPS 以保护传输中的数据" if is_http else "已使用 HTTPS"
        }
        
        # 2. 重放攻击测试
        print("测试重放攻击防护...")
        replay_test_results = await self._replay_attack_test(url, headers)
        test_results["replay_attack"] = replay_test_results
        
        # 分析结果
        analysis = self._analyze_protocol_security(test_results)
        
        return {
            "test_results": test_results,
            "analysis": analysis
        }
    
    async def _replay_attack_test(
        self,
        url: str,
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        重放攻击测试
        
        Args:
            url: 接口 URL
            headers: 请求头
            
        Returns:
            Dict: 重放攻击测试结果
        """
        # 记录一次成功的请求
        print("  记录原始请求...")
        original_result = await self.concurrent_tester.concurrent_test(
            url=url,
            headers=headers,
            concurrency=1,
            total_requests=1,
            use_proxy=False,
            use_fake_header=False
        )
        
        if not original_result["results"] or not original_result["results"][0].get("success"):
            return {
                "original_request_success": False,
                "replay_test_performed": False,
                "note": "原始请求失败，无法进行重放测试"
            }
        
        original_response = original_result["results"][0]
        original_status = original_response.get("status_code")
        original_body = original_response.get("response_body")
        
        # 等待一段时间后重放（模拟攻击者在稍后时间重放请求）
        print("  等待 5 秒后重放请求...")
        await asyncio.sleep(5)
        
        # 重放相同的请求
        print("  重放原始请求...")
        replay_result = await self.concurrent_tester.concurrent_test(
            url=url,
            headers=headers,
            concurrency=1,
            total_requests=1,
            use_proxy=False,
            use_fake_header=False
        )
        
        replay_response = replay_result["results"][0] if replay_result["results"] else None
        replay_success = replay_response and replay_response.get("success")
        replay_status = replay_response.get("status_code") if replay_response else None
        
        # 检查是否被拒绝（理想情况下应该被拒绝或返回不同的结果）
        is_rejected = False
        if replay_status and replay_status in [401, 403, 429]:
            is_rejected = True
        
        # 检查响应是否相同（如果相同，说明没有防重放机制）
        response_identical = False
        if replay_response:
            replay_body = replay_response.get("response_body")
            if original_body and replay_body and original_body == replay_body:
                response_identical = True
        
        return {
            "original_request_success": True,
            "original_status_code": original_status,
            "replay_success": replay_success,
            "replay_status_code": replay_status,
            "is_rejected": is_rejected,
            "response_identical": response_identical,
            "has_replay_protection": is_rejected or not response_identical,
            "recommendation": "建议实现 nonce 或 timestamp 校验机制" if not is_rejected and response_identical else "重放攻击防护正常"
        }
    
    def _analyze_protocol_security(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """分析协议安全测试结果"""
        analysis = {
            "protocol_security_score": 0,
            "issues": [],
            "recommendations": []
        }
        
        # HTTPS 支持分析
        https_info = test_results.get("https_support", {})
        if https_info.get("is_http"):
            analysis["issues"].append("使用 HTTP 协议，数据传输未加密")
            analysis["recommendations"].append("强制使用 HTTPS 协议")
        else:
            analysis["protocol_security_score"] += 50
        
        # 重放攻击防护分析
        replay_info = test_results.get("replay_attack", {})
        if replay_info.get("has_replay_protection"):
            analysis["protocol_security_score"] += 50
        else:
            analysis["issues"].append("未检测到重放攻击防护机制")
            analysis["recommendations"].append("实现 nonce 或 timestamp 校验机制")
        
        return analysis
    
    async def cache_control_test(
        self,
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        缓存控制测试
        检查响应头中的缓存控制指令
        
        Args:
            url: 接口 URL
            headers: 请求头
            
        Returns:
            Dict: 缓存控制测试结果
        """
        url = url or settings.api.url
        headers = headers or settings.api.headers.copy()
        
        print("测试缓存控制策略...")
        
        # 发送请求并检查响应头
        result = await self.concurrent_tester.concurrent_test(
            url=url,
            headers=headers,
            concurrency=1,
            total_requests=1,
            use_proxy=False,
            use_fake_header=False
        )
        
        if not result["results"]:
            return {
                "error": "无法获取响应"
            }
        
        response = result["results"][0]
        response_headers = response.get("headers", {})
        
        # 检查缓存控制相关的响应头
        cache_control = response_headers.get("Cache-Control", "").lower()
        pragma = response_headers.get("Pragma", "").lower()
        expires = response_headers.get("Expires")
        etag = response_headers.get("ETag")
        last_modified = response_headers.get("Last-Modified")
        
        # 检查是否包含禁止缓存的指令
        has_no_store = "no-store" in cache_control
        has_no_cache = "no-cache" in cache_control
        has_must_revalidate = "must-revalidate" in cache_control
        has_pragma_no_cache = "no-cache" in pragma
        
        # 评估缓存控制强度
        cache_control_score = 0
        if has_no_store:
            cache_control_score += 40
        if has_no_cache:
            cache_control_score += 30
        if has_must_revalidate:
            cache_control_score += 20
        if has_pragma_no_cache:
            cache_control_score += 10
        
        is_safe = cache_control_score >= 70  # 至少需要 no-store 和 no-cache
        
        analysis = {
            "cache_control_header": cache_control or "未设置",
            "pragma_header": pragma or "未设置",
            "expires_header": expires or "未设置",
            "has_no_store": has_no_store,
            "has_no_cache": has_no_cache,
            "has_must_revalidate": has_must_revalidate,
            "has_pragma_no_cache": has_pragma_no_cache,
            "cache_control_score": cache_control_score,
            "is_safe": is_safe,
            "recommendations": []
        }
        
        if not is_safe:
            analysis["recommendations"].append(
                "敏感用户信息接口应设置 Cache-Control: no-store, no-cache, must-revalidate"
            )
            analysis["recommendations"].append(
                "建议设置 Pragma: no-cache 以兼容旧版浏览器"
            )
        
        return {
            "response_headers": dict(response_headers),
            "analysis": analysis
        }
    
    async def cors_and_referrer_test(
        self,
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        CORS 与 Referrer 策略测试
        
        Args:
            url: 接口 URL
            headers: 请求头
            
        Returns:
            Dict: CORS 和 Referrer 测试结果
        """
        url = url or settings.api.url
        base_headers = headers or settings.api.headers.copy()
        
        test_results = {}
        
        # 1. CORS 测试
        print("测试 CORS 策略...")
        cors_test_results = await self._cors_test(url, base_headers)
        test_results["cors"] = cors_test_results
        
        # 2. Referrer 测试
        print("测试 Referrer 策略...")
        referrer_test_results = await self._referrer_test(url, base_headers)
        test_results["referrer"] = referrer_test_results
        
        # 分析结果
        analysis = self._analyze_cors_and_referrer(test_results)
        
        return {
            "test_results": test_results,
            "analysis": analysis
        }
    
    async def _cors_test(
        self,
        url: str,
        base_headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """CORS 测试"""
        # 测试不同的 Origin
        test_origins = [
            "http://localhost:12315",  # 原始 referrer
            "http://evil.com",  # 恶意域名
            "https://example.com",  # 其他域名
            None  # 无 Origin
        ]
        
        cors_results = {}
        
        for origin in test_origins:
            headers = base_headers.copy()
            if origin:
                headers["Origin"] = origin
            
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers=headers) as response:
                        cors_header = response.headers.get("Access-Control-Allow-Origin", "")
                        cors_credentials = response.headers.get("Access-Control-Allow-Credentials", "")
                        cors_methods = response.headers.get("Access-Control-Allow-Methods", "")
                        
                        cors_results[origin or "no_origin"] = {
                            "status_code": response.status,
                            "access_control_allow_origin": cors_header,
                            "access_control_allow_credentials": cors_credentials,
                            "access_control_allow_methods": cors_methods,
                            "is_wildcard": cors_header == "*",
                            "is_allowed": cors_header == "*" or cors_header == origin
                        }
            except Exception as e:
                cors_results[origin or "no_origin"] = {
                    "error": str(e)
                }
        
        return cors_results
    
    async def _referrer_test(
        self,
        url: str,
        base_headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Referrer 测试"""
        # 测试不同的 Referer
        test_referrers = [
            "http://localhost:12315/",  # 原始 referrer
            "http://evil.com/",  # 恶意域名
            "https://example.com/",  # 其他域名
            None  # 无 Referer
        ]
        
        referrer_results = {}
        
        for referrer in test_referrers:
            headers = base_headers.copy()
            if referrer:
                headers["Referer"] = referrer
            
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers=headers) as response:
                        response_text = await response.text()
                        referrer_results[referrer or "no_referrer"] = {
                            "status_code": response.status,
                            "success": 200 <= response.status < 300,
                            "response_size": len(response_text)
                        }
            except Exception as e:
                referrer_results[referrer or "no_referrer"] = {
                    "error": str(e)
                }
        
        return referrer_results
    
    def _analyze_cors_and_referrer(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """分析 CORS 和 Referrer 测试结果"""
        analysis = {
            "cors_security_score": 0,
            "referrer_security_score": 0,
            "issues": [],
            "recommendations": []
        }
        
        # CORS 分析
        cors_results = test_results.get("cors", {})
        wildcard_found = False
        for origin, result in cors_results.items():
            if result.get("is_wildcard"):
                wildcard_found = True
                break
        
        if wildcard_found:
            analysis["issues"].append("CORS 策略使用通配符 *，存在 CSRF 风险")
            analysis["recommendations"].append("CORS 应精确匹配允许的域名，避免使用 *")
        else:
            analysis["cors_security_score"] = 50
        
        # Referrer 分析
        referrer_results = test_results.get("referrer", {})
        evil_allowed = False
        for referrer, result in referrer_results.items():
            if "evil.com" in referrer and result.get("success"):
                evil_allowed = True
                break
        
        if evil_allowed:
            analysis["issues"].append("恶意域名的 Referrer 可以成功访问接口")
            analysis["recommendations"].append("应验证 Referrer，拒绝非法域名的请求")
        else:
            analysis["referrer_security_score"] = 50
        
        return analysis
    
    async def fuzzing_test(
        self,
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        健壮性与模糊测试
        
        Args:
            url: 接口 URL
            headers: 请求头
            
        Returns:
            Dict: 模糊测试结果
        """
        url = url or settings.api.url
        base_headers = headers or settings.api.headers.copy()
        
        test_results = {}
        
        # 1. 超长 Token 测试
        print("测试超长 Token...")
        long_token_result = await self._test_long_token(url, base_headers)
        test_results["long_token"] = long_token_result
        
        # 2. 特殊字符测试
        print("测试特殊字符...")
        special_chars_result = await self._test_special_chars(url, base_headers)
        test_results["special_chars"] = special_chars_result
        
        # 3. 异常数据测试
        print("测试异常数据...")
        malformed_result = await self._test_malformed_data(url, base_headers)
        test_results["malformed_data"] = malformed_result
        
        # 分析结果
        analysis = self._analyze_fuzzing(test_results)
        
        return {
            "test_results": test_results,
            "analysis": analysis
        }
    
    async def _test_long_token(
        self,
        url: str,
        base_headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """测试超长 Token"""
        # 生成 10KB 的 Token
        long_token = "A" * (10 * 1024)
        headers = base_headers.copy()
        headers["token"] = long_token
        
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    return {
                        "status_code": response.status,
                        "is_rejected": response.status in [400, 413, 414],
                        "response_size": len(await response.text()),
                        "handled_properly": response.status in [400, 401, 403, 413, 414]
                    }
        except Exception as e:
            return {
                "error": str(e),
                "handled_properly": False
            }
    
    async def _test_special_chars(
        self,
        url: str,
        base_headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """测试特殊字符"""
        test_cases = [
            ("sql_injection", "' OR 1=1 --"),
            ("xss_script", "<script>alert('xss')</script>"),
            ("null_bytes", "\x00\x00"),
            ("unicode", "测试中文和特殊字符!@#$%^&*()"),
            ("json_injection", '{"malicious": "data"}'),
        ]
        
        results = {}
        
        for name, special_value in test_cases:
            headers = base_headers.copy()
            headers["token"] = special_value
            
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers=headers) as response:
                        results[name] = {
                            "status_code": response.status,
                            "is_rejected": response.status in [400, 401, 403],
                            "handled_properly": response.status in [400, 401, 403, 422]
                        }
            except Exception as e:
                results[name] = {
                    "error": str(e),
                    "handled_properly": False
                }
        
        return results
    
    async def _test_malformed_data(
        self,
        url: str,
        base_headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """测试异常数据"""
        test_cases = [
            ("empty_token", ""),
            ("null_token", None),
            ("numeric_token", "123456"),
            ("very_short_token", "ab"),
        ]
        
        results = {}
        
        for name, token_value in test_cases:
            headers = base_headers.copy()
            if token_value is None:
                if "token" in headers:
                    del headers["token"]
            else:
                headers["token"] = token_value
            
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers=headers) as response:
                        text = await response.text()
                        try:
                            # 尝试解析 JSON，检查格式是否正确
                            json_data = json.loads(text)
                            is_valid_json = True
                        except:
                            is_valid_json = False
                        
                        results[name] = {
                            "status_code": response.status,
                            "is_valid_json": is_valid_json,
                            "response_size": len(text),
                            "handled_properly": response.status in [400, 401, 403, 422] or is_valid_json
                        }
            except Exception as e:
                results[name] = {
                    "error": str(e),
                    "handled_properly": False
                }
        
        return results
    
    def _analyze_fuzzing(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """分析模糊测试结果"""
        analysis = {
            "robustness_score": 0,
            "issues": [],
            "recommendations": []
        }
        
        total_tests = 0
        passed_tests = 0
        
        # 分析超长 Token
        long_token = test_results.get("long_token", {})
        if long_token.get("handled_properly"):
            passed_tests += 1
        else:
            analysis["issues"].append("超长 Token 未正确处理")
            analysis["recommendations"].append("应限制 Token 长度，返回 413 或 400 错误")
        total_tests += 1
        
        # 分析特殊字符
        special_chars = test_results.get("special_chars", {})
        for name, result in special_chars.items():
            total_tests += 1
            if result.get("handled_properly"):
                passed_tests += 1
            else:
                analysis["issues"].append(f"特殊字符测试 {name} 未正确处理")
        if len(special_chars) > 0:
            analysis["recommendations"].append("应过滤和验证输入，防止注入攻击")
        
        # 分析异常数据
        malformed_data = test_results.get("malformed_data", {})
        for name, result in malformed_data.items():
            total_tests += 1
            if result.get("handled_properly"):
                passed_tests += 1
            else:
                analysis["issues"].append(f"异常数据测试 {name} 未正确处理")
        
        if total_tests > 0:
            analysis["robustness_score"] = (passed_tests / total_tests) * 100
        
        return analysis
    
    async def lifecycle_test(
        self,
        url: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        生命周期与状态同步测试
        
        Args:
            url: 接口 URL
            headers: 请求头
            
        Returns:
            Dict: 生命周期测试结果
        """
        url = url or settings.api.url
        headers = headers or settings.api.headers.copy()
        
        test_results = {}
        
        # 1. Token 失效测试（模拟多端登录）
        print("测试 Token 失效机制...")
        token_invalidation_result = await self._test_token_invalidation(url, headers)
        test_results["token_invalidation"] = token_invalidation_result
        
        # 2. 状态同步测试（模拟用户被禁用）
        print("测试状态同步...")
        state_sync_result = await self._test_state_sync(url, headers)
        test_results["state_sync"] = state_sync_result
        
        # 分析结果
        analysis = self._analyze_lifecycle(test_results)
        
        return {
            "test_results": test_results,
            "analysis": analysis
        }
    
    async def _test_token_invalidation(
        self,
        url: str,
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """测试 Token 失效机制"""
        # 连续多次使用相同 Token 请求，模拟多端登录场景
        # 理想情况下，如果在新设备登录，旧 Token 应该失效
        
        results = []
        for i in range(5):
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers=headers) as response:
                        results.append({
                            "request_number": i + 1,
                            "status_code": response.status,
                            "success": 200 <= response.status < 300,
                            "timestamp": time.time()
                        })
                await asyncio.sleep(1)  # 间隔 1 秒
            except Exception as e:
                results.append({
                    "request_number": i + 1,
                    "error": str(e),
                    "success": False
                })
        
        # 检查是否有 Token 失效的情况
        token_invalidated = any(r.get("status_code") in [401, 403] for r in results)
        all_success = all(r.get("success", False) for r in results)
        
        return {
            "results": results,
            "token_invalidated": token_invalidated,
            "all_requests_success": all_success,
            "has_invalidation_mechanism": token_invalidated,
            "recommendation": "建议实现多端登录检测，新设备登录时使旧 Token 失效" if not token_invalidated else "Token 失效机制正常"
        }
    
    async def _test_state_sync(
        self,
        url: str,
        headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """测试状态同步（模拟用户被禁用）"""
        # 连续请求，检查是否能快速感知状态变化
        # 由于我们无法真正禁用用户，这里主要测试接口的响应一致性
        
        results = []
        for i in range(3):
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url, headers=headers) as response:
                        text = await response.text()
                        results.append({
                            "request_number": i + 1,
                            "status_code": response.status,
                            "response_size": len(text),
                            "timestamp": time.time()
                        })
                await asyncio.sleep(0.5)  # 间隔 0.5 秒
            except Exception as e:
                results.append({
                    "request_number": i + 1,
                    "error": str(e)
                })
        
        # 检查响应一致性
        status_codes = [r.get("status_code") for r in results if r.get("status_code")]
        status_consistent = len(set(status_codes)) == 1 if status_codes else False
        
        return {
            "results": results,
            "status_consistent": status_consistent,
            "recommendation": "建议实现实时状态同步，用户被禁用时立即拒绝请求"
        }
    
    def _analyze_lifecycle(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """分析生命周期测试结果"""
        analysis = {
            "lifecycle_score": 0,
            "issues": [],
            "recommendations": []
        }
        
        # Token 失效分析
        token_invalidation = test_results.get("token_invalidation", {})
        if token_invalidation.get("has_invalidation_mechanism"):
            analysis["lifecycle_score"] += 50
        else:
            analysis["issues"].append("未检测到 Token 失效机制")
            analysis["recommendations"].append("实现多端登录检测和 Token 失效机制")
        
        # 状态同步分析
        state_sync = test_results.get("state_sync", {})
        if state_sync.get("status_consistent"):
            analysis["lifecycle_score"] += 50
        else:
            analysis["issues"].append("状态同步可能存在问题")
            analysis["recommendations"].append("确保用户状态变化能实时反映到接口响应中")
        
        return analysis
