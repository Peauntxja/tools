# 使用指南

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置接口信息

编辑 `config/settings.py` 或使用环境变量配置接口 URL 和 token。

默认配置已包含示例接口：
- URL: `http://202.100.246.215:9084/hn-api/user/getUserInfoByToken`
- Token: `0912801a50cf47e3a248d0238f383a67935405`

### 3. 运行测试

#### 运行所有测试
```bash
python main.py
```

#### 运行特定测试
```bash
# 仅并发测试
python main.py --test-type concurrent

# 仅幂等性测试
python main.py --test-type idempotency

# 仅安全性测试
python main.py --test-type security
```

#### 使用命令行参数覆盖配置
```bash
# 指定接口 URL
python main.py --url "http://example.com/api"

# 指定 token
python main.py --token "your_token_here"

# 指定并发数和总请求数
python main.py --concurrency 20 --total-requests 200
```

## 测试类型说明

### 1. 并发测试
- 测试接口在高并发场景下的性能表现
- 统计 QPS、响应时间、成功率等指标
- 分析响应时间分布（P50、P95、P99）

### 2. 幂等性测试
- 发送多次相同请求，验证响应一致性
- 检测接口是否具备幂等性
- 分析响应时间方差和响应体一致性

### 3. 安全性测试
包含三个子测试：

#### IP 限制测试
- 使用真实 IP 进行基准测试
- 使用代理池模拟不同 IP
- 修改请求头（X-Forwarded-For 等）模拟不同 IP
- 检测是否触发 IP 限制（403/429 状态码）

#### Token 验证测试
- 测试有效 token
- 测试无效 token
- 测试空 token
- 测试缺少 token
- 测试格式错误的 token
- 评估 token 验证强度

#### 并发安全测试
- 高并发下测试数据一致性
- 检测是否存在竞态条件
- 评估并发安全性

### 4. 高级安全性测试

#### 协议与链路安全测试
- **HTTPS 支持测试**：检查接口是否支持 HTTPS，评估传输加密
- **重放攻击测试**：验证接口是否有防重放机制（nonce/timestamp 校验）

#### 缓存控制测试
- 检查响应头中的 `Cache-Control`、`Pragma`、`Expires` 等缓存控制指令
- 评估敏感信息是否会被浏览器或代理缓存
- 建议设置 `no-store, no-cache, must-revalidate`

#### CORS 与 Referrer 策略测试
- **CORS 测试**：检查 `Access-Control-Allow-Origin` 是否使用通配符，评估 CSRF 风险
- **Referrer 测试**：验证不同域名的 Referrer 是否被正确拒绝

#### 健壮性与模糊测试
- **超长 Token 测试**：发送 10KB 的 Token，检查是否被正确处理
- **特殊字符测试**：测试 SQL 注入字符、XSS 脚本、Unicode 等特殊输入
- **异常数据测试**：测试空 Token、null 值、格式错误的数据处理

#### 生命周期与状态同步测试
- **Token 失效测试**：模拟多端登录场景，检查旧 Token 是否失效
- **状态同步测试**：验证用户状态变化是否能实时反映到接口响应

## 配置代理池

如果需要测试 IP 限制功能，可以在 `config/settings.py` 中配置代理池：

```python
proxy: ProxyConfig = Field(default_factory=lambda: ProxyConfig(
    proxy_list=[
        "http://proxy1.example.com:8080",
        "http://proxy2.example.com:8080",
    ],
    enable_proxy=True,
    enable_header_manipulation=True
))
```

## 查看测试报告

测试完成后，报告会保存在 `reports/` 目录下：
- HTML 报告：可视化测试结果，包含图表和详细分析
- JSON 报告：原始测试数据，便于程序化处理

## 环境变量配置

支持通过环境变量覆盖配置（使用双下划线分隔嵌套配置）：

```bash
export API__URL="http://example.com/api"
export API__HEADERS__TOKEN="your_token"
export TEST__CONCURRENCY=20
export TEST__TOTAL_REQUESTS=200
```

## 注意事项

1. **并发测试**：请根据目标服务器的承载能力合理设置并发数，避免对服务器造成过大压力
2. **代理配置**：如果使用代理池，确保代理服务器可用且稳定
3. **Token 安全**：不要在代码仓库中提交包含真实 token 的配置文件
4. **测试环境**：建议在测试环境进行测试，避免影响生产环境
