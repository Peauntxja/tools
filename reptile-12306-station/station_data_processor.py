#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
火车站数据处理脚本
从12306官网获取火车站数据并整理
"""

try:
    import requests
except ImportError:
    print("错误: 需要安装 requests 库")
    print("请运行: pip install requests")
    sys.exit(1)

import re
import json
import csv
import sys
from typing import List, Dict, Optional


def fetch_station_data(url: str) -> str:
    """
    从指定URL获取火车站数据
    
    Args:
        url: 数据源URL
        
    Returns:
        获取到的JavaScript文件内容
        
    Raises:
        requests.RequestException: 网络请求失败时抛出
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        response.encoding = 'utf-8'
        return response.text
    except requests.RequestException as e:
        print(f"获取数据失败: {e}", file=sys.stderr)
        raise


def parse_station_data(js_content: str) -> List[Dict[str, str]]:
    """
    解析JavaScript文件中的火车站数据
    
    Args:
        js_content: JavaScript文件内容
        
    Returns:
        解析后的火车站数据列表，每个元素包含站点的详细信息
    """
    # 使用正则表达式提取 station_names 变量的值
    pattern = r"var\s+station_names\s*=\s*['\"](.*?)['\"]"
    match = re.search(pattern, js_content, re.DOTALL)
    
    if not match:
        raise ValueError("无法找到 station_names 变量")
    
    station_string = match.group(1)
    
    # 按 @ 分割各个站点
    stations = []
    station_parts = station_string.split('@')
    
    for part in station_parts:
        if not part.strip():
            continue
            
        # 按 | 分割字段
        fields = part.split('|')
        
        # 根据观察到的数据格式，字段顺序为：
        # 代码、中文名、拼音码、拼音、简拼、序号、区号、城市、其他字段...
        if len(fields) >= 8:
            station = {
                'code': fields[0].strip(),
                'name': fields[1].strip(),
                'pinyin_code': fields[2].strip(),
                'pinyin': fields[3].strip(),
                'short_pinyin': fields[4].strip(),
                'index': fields[5].strip(),
                'area_code': fields[6].strip(),
                'city': fields[7].strip(),
            }
            # 如果有额外字段，也保存
            if len(fields) > 8:
                station['extra'] = '|'.join(fields[8:])
            
            stations.append(station)
    
    return stations


def save_to_json(stations: List[Dict[str, str]], filename: str = 'stations.json'):
    """
    将数据保存为JSON格式
    
    Args:
        stations: 火车站数据列表
        filename: 输出文件名
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(stations, f, ensure_ascii=False, indent=2)
    print(f"数据已保存到 {filename}，共 {len(stations)} 条记录")


def save_to_csv(stations: List[Dict[str, str]], filename: str = 'stations.csv'):
    """
    将数据保存为CSV格式
    
    Args:
        stations: 火车站数据列表
        filename: 输出文件名
    """
    if not stations:
        print("没有数据可保存", file=sys.stderr)
        return
    
    fieldnames = ['code', 'name', 'pinyin_code', 'pinyin', 'short_pinyin', 
                  'index', 'area_code', 'city']
    
    # 检查是否有extra字段
    if 'extra' in stations[0]:
        fieldnames.append('extra')
    
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(stations)
    
    print(f"数据已保存到 {filename}，共 {len(stations)} 条记录")


def main():
    """主函数"""
    url = "https://www.12306.cn/index/script/core/common/station_name_new_v10092.js"
    
    print("正在获取火车站数据...")
    try:
        js_content = fetch_station_data(url)
        print("数据获取成功")
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    
    print("正在解析数据...")
    try:
        stations = parse_station_data(js_content)
        print(f"解析完成，共找到 {len(stations)} 个火车站")
    except Exception as e:
        print(f"解析错误: {e}", file=sys.stderr)
        sys.exit(1)
    
    # 保存为JSON和CSV格式
    print("\n正在保存数据...")
    save_to_json(stations, 'stations.json')
    save_to_csv(stations, 'stations.csv')
    
    # 显示前5条数据作为示例
    print("\n前5条数据示例:")
    for i, station in enumerate(stations[:5], 1):
        print(f"{i}. {station['name']} ({station['code']}) - {station['city']}")
    
    print("\n处理完成！")


if __name__ == '__main__':
    main()
