"""
主程序入口
提供命令行接口整合所有测试模块
"""
import asyncio
import argparse
import sys
from typing import Optional
from datetime import datetime
from src.concurrent_test import ConcurrentTester
from src.idempotency_test import IdempotencyTester
from src.security_test import SecurityTester
from src.ip_simulator import IPSimulator
from src.result_analyzer import ResultAnalyzer
from src.report_generator import ReportGenerator
from config.settings import settings


class APITestRunner:
    """API 测试运行器"""
    
    def __init__(self):
        """初始化测试运行器"""
        self.ip_simulator = IPSimulator()
        self.concurrent_tester = ConcurrentTester(self.ip_simulator)
        self.idempotency_tester = IdempotencyTester(self.concurrent_tester)
        self.security_tester = SecurityTester(self.concurrent_tester, self.ip_simulator)
        self.result_analyzer = ResultAnalyzer()
        self.report_generator = ReportGenerator()
    
    async def initialize(self):
        """初始化所有组件"""
        print("初始化测试环境...")
        await self.ip_simulator.initialize()
        await self.security_tester.initialize()
        print("初始化完成！\n")
    
    async def run_concurrent_test(self) -> dict:
        """运行并发测试"""
        print("=" * 60)
        print("开始并发测试")
        print("=" * 60)
        print(f"接口 URL: {settings.api.url}")
        print(f"并发数: {settings.test.concurrency}")
        print(f"总请求数: {settings.test.total_requests}")
        print()
        
        result = await self.concurrent_tester.concurrent_test()
        
        print(f"测试完成！")
        print(f"成功率: {result['statistics']['success_rate']:.2f}%")
        print(f"QPS: {result['statistics'].get('qps', 0):.2f}")
        print(f"平均响应时间: {result['statistics'].get('avg_response_time', 0):.3f}s")
        print()
        
        return result
    
    async def run_idempotency_test(self) -> dict:
        """运行幂等性测试"""
        print("=" * 60)
        print("开始幂等性测试")
        print("=" * 60)
        print(f"接口 URL: {settings.api.url}")
        print(f"测试次数: {settings.test.idempotency_test_count}")
        print()
        
        result = await self.idempotency_tester.idempotency_test()
        
        print(f"测试完成！")
        print(f"是否幂等: {'是' if result['analysis']['is_idempotent'] else '否'}")
        print(f"响应一致性: {result['analysis'].get('response_consistency', 0):.2f}%")
        print(f"原因: {result['analysis']['reason']}")
        print()
        
        return result
    
    async def run_security_test(self) -> dict:
        """运行安全性测试"""
        print("=" * 60)
        print("开始安全性测试")
        print("=" * 60)
        print()
        
        security_results = {}
        
        # IP 限制测试
        print("执行 IP 限制测试...")
        ip_result = await self.security_tester.ip_restriction_test()
        security_results["ip_restriction"] = ip_result
        print(f"IP 限制检测: {'是' if ip_result['analysis']['ip_restriction_detected'] else '否'}")
        print()
        
        # Token 验证测试
        print("执行 Token 验证测试...")
        token_result = await self.security_tester.token_validation_test()
        security_results["token_validation"] = token_result
        print(f"Token 验证强度: {token_result['analysis']['validation_strength']}")
        print()
        
        # 并发安全测试
        print("执行并发安全测试...")
        concurrent_security_result = await self.security_tester.concurrent_security_test()
        security_results["concurrent_security"] = concurrent_security_result
        print(f"并发安全性: {concurrent_security_result['analysis']['concurrent_safety']}")
        print(f"数据一致性: {concurrent_security_result['analysis']['data_consistency']}")
        print()
        
        # 高级安全测试
        print("执行高级安全测试...")
        advanced_security_result = await self.security_tester.advanced_security_test()
        security_results["advanced_security"] = advanced_security_result
        print("高级安全测试完成！")
        print()
        
        return security_results
    
    async def run_all_tests(self) -> dict:
        """运行所有测试"""
        print("=" * 60)
        print("开始执行完整测试套件")
        print("=" * 60)
        print()
        
        results = {}
        
        # 并发测试
        results["concurrent"] = await self.run_concurrent_test()
        
        # 幂等性测试
        results["idempotency"] = await self.run_idempotency_test()
        
        # 安全性测试
        results["security"] = await self.run_security_test()
        
        return results
    
    def generate_report(self, results: dict):
        """生成测试报告"""
        print("=" * 60)
        print("生成测试报告")
        print("=" * 60)
        print()
        
        # 分析结果
        concurrent_analysis = None
        idempotency_analysis = None
        security_analysis = None
        
        if "concurrent" in results:
            concurrent_analysis = self.result_analyzer.analyze_concurrent_test(results["concurrent"])
        
        if "idempotency" in results:
            idempotency_analysis = self.result_analyzer.analyze_idempotency_test(results["idempotency"])
        
        if "security" in results:
            security_analysis = self.result_analyzer.analyze_security_test(results["security"])
        
        # 生成综合报告
        summary_report = self.result_analyzer.generate_summary_report(
            concurrent_result=results.get("concurrent"),
            idempotency_result=results.get("idempotency"),
            security_result=results.get("security")
        )
        
        # 添加详细分析
        summary_report["concurrent_test"] = concurrent_analysis
        summary_report["idempotency_test"] = idempotency_analysis
        summary_report["security_test"] = security_analysis
        
        # 生成报告文件
        generated_files = self.report_generator.generate_reports(
            summary_report,
            api_url=settings.api.url
        )
        
        print("报告生成完成！")
        for format_type, filepath in generated_files.items():
            print(f"  {format_type.upper()} 报告: {filepath}")
        print()
        
        return summary_report


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="API 并发安全测试框架")
    parser.add_argument(
        "--test-type",
        choices=["concurrent", "idempotency", "security", "advanced-security", "all"],
        default="all",
        help="选择测试类型 (默认: all)"
    )
    parser.add_argument(
        "--url",
        type=str,
        help="接口 URL（覆盖配置文件）"
    )
    parser.add_argument(
        "--token",
        type=str,
        help="Token（覆盖配置文件）"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        help="并发数（覆盖配置文件）"
    )
    parser.add_argument(
        "--total-requests",
        type=int,
        help="总请求数（覆盖配置文件）"
    )
    
    args = parser.parse_args()
    
    # 创建测试运行器
    runner = APITestRunner()
    
    # 初始化
    await runner.initialize()
    
    # 应用命令行参数覆盖配置
    if args.url:
        settings.api.url = args.url
    if args.token:
        settings.api.headers["token"] = args.token
    if args.concurrency:
        settings.test.concurrency = args.concurrency
    if args.total_requests:
        settings.test.total_requests = args.total_requests
    
    # 执行测试
    results = {}
    
    try:
        if args.test_type == "concurrent" or args.test_type == "all":
            results["concurrent"] = await runner.run_concurrent_test()
        
        if args.test_type == "idempotency" or args.test_type == "all":
            results["idempotency"] = await runner.run_idempotency_test()
        
        if args.test_type == "security" or args.test_type == "all":
            results["security"] = await runner.run_security_test()
        
        if args.test_type == "advanced-security":
            # 仅运行高级安全测试
            print("=" * 60)
            print("开始执行高级安全测试")
            print("=" * 60)
            print()
            advanced_result = await runner.security_tester.advanced_security_test()
            results["advanced_security"] = advanced_result
            # 生成报告
            summary_report = {
                "test_timestamp": datetime.now().isoformat(),
                "summary": {
                    "tests_performed": ["advanced_security_test"],
                    "overall_status": "completed"
                },
                "advanced_security_test": advanced_result
            }
            generated_files = runner.report_generator.generate_reports(
                summary_report,
                api_url=settings.api.url
            )
            print("\n报告生成完成！")
            for format_type, filepath in generated_files.items():
                print(f"  {format_type.upper()} 报告: {filepath}")
            print()
            # 提前返回，避免重复生成报告
            return
        
        # 生成报告
        if results:
            runner.generate_report(results)
        
        print("=" * 60)
        print("所有测试完成！")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
