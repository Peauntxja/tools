# 上海市人社局社保稽核公告爬虫

## 项目简介

本项目用于爬取上海市人力资源和社会保障局网站的社保稽核（征收）公告数据。

## 功能特性

- 自动爬取列表页所有公告链接
- 解析每条公告的详细信息（公告编号、发布时间、公司名称、投诉人、时间段、缴费基数等）
- 自动过滤最近一年的数据
- 支持导出为CSV和JSON格式
- 包含错误处理和重试机制

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

直接运行主程序：

```bash
python main.py
```

程序会自动：
1. 访问列表页获取所有公告链接
2. 遍历每个链接获取详细信息
3. 过滤最近一年的数据
4. 保存为CSV和JSON文件

## 输出文件

- `announcements_YYYYMMDD_HHMMSS.csv`: CSV格式的数据文件
- `announcements_YYYYMMDD_HHMMSS.json`: JSON格式的数据文件

## 数据字段说明

- `announcement_number`: 公告编号（如：沪社险（2025）稽意173000259号）
- `publish_date`: 发布时间（格式：YYYY-MM-DD）
- `company_name`: 公司名称
- `complaint_person`: 投诉人姓名
- `period`: 社保缴费时间段
- `payment_base`: 缴费基数
- `url`: 公告详情页URL
- `content`: 公告完整内容

## 注意事项

- 请遵守网站的robots.txt和使用条款
- 爬取时已设置合理的请求间隔，避免对服务器造成压力
- 如遇到网络问题，程序会自动重试
