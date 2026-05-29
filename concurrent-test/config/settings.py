"""
配置管理模块
支持接口配置、测试参数、代理配置等
"""
from typing import Dict, List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class APIConfig(BaseSettings):
    """API 接口配置"""
    url: str = Field(
        default="http://202.100.246.215:9084/hn-api/user/getUserInfoByToken",
        description="接口 URL"
    )
    method: str = Field(default="GET", description="请求方法")
    headers: Dict[str, str] = Field(
        default_factory=lambda: {
            "accept": "*/*",
            "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "token": "0912801a50cf47e3a248d0238f383a67935405"
        },
        description="请求头"
    )
    body: Optional[str] = Field(default=None, description="请求体")


class TestConfig(BaseSettings):
    """测试参数配置"""
    concurrency: int = Field(default=10, description="并发数", ge=1, le=1000)
    total_requests: int = Field(default=100, description="总请求数", ge=1)
    timeout: int = Field(default=30, description="请求超时时间（秒）", ge=1)
    idempotency_test_count: int = Field(default=20, description="幂等性测试请求次数", ge=2)


class ProxyConfig(BaseSettings):
    """代理配置"""
    proxy_list: List[str] = Field(
        default_factory=list,
        description="代理列表，格式: http://ip:port 或 https://ip:port"
    )
    proxy_rotation: str = Field(
        default="round_robin",
        description="代理轮换策略: round_robin, random"
    )
    enable_proxy: bool = Field(default=False, description="是否启用代理")
    enable_header_manipulation: bool = Field(
        default=True,
        description="是否启用请求头修改（X-Forwarded-For等）"
    )


class ReportConfig(BaseSettings):
    """报告配置"""
    output_dir: str = Field(default="reports", description="报告输出目录")
    output_format: List[str] = Field(
        default_factory=lambda: ["html", "json", "markdown"],
        description="输出格式: html, json, markdown"
    )
    include_charts: bool = Field(default=True, description="是否包含图表")


class Settings(BaseSettings):
    """总配置"""
    api: APIConfig = Field(default_factory=APIConfig)
    test: TestConfig = Field(default_factory=TestConfig)
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    report: ReportConfig = Field(default_factory=ReportConfig)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"


# 全局配置实例
settings = Settings()
