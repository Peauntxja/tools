"""
主程序入口
"""
import pandas as pd  # pyright: ignore[reportMissingImports]
import json
from datetime import datetime
from spider import RSJSpider
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def save_to_csv(data, filename='announcements.csv'):
    """
    保存数据到CSV文件
    
    Args:
        data: 数据列表
        filename: 文件名
    """
    if not data:
        logger.warning("没有数据可保存")
        return
    
    df = pd.DataFrame(data)
    
    # 确保列的顺序
    columns_order = [
        'announcement_number',
        'publish_date',
        'company_name',
        'complaint_person',
        'period',
        'payment_base',
        'url',
        'content'
    ]
    
    # 只保留存在的列
    existing_columns = [col for col in columns_order if col in df.columns]
    df = df[existing_columns]
    
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    logger.info(f"数据已保存到 {filename}")


def save_to_json(data, filename='announcements.json'):
    """
    保存数据到JSON文件
    
    Args:
        data: 数据列表
        filename: 文件名
    """
    if not data:
        logger.warning("没有数据可保存")
        return
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"数据已保存到 {filename}")


def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("开始爬取上海市人社局社保稽核公告")
    logger.info("=" * 50)
    
    spider = RSJSpider()
    
    # 爬取所有44页的数据（不过滤年份，获取全部数据）
    data = spider.crawl_all(filter_by_year=False, total_pages=44)
    
    if not data:
        logger.warning("未获取到任何数据")
        return
    
    # 生成带时间戳的文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f'announcements_{timestamp}.csv'
    json_filename = f'announcements_{timestamp}.json'
    
    # 保存数据
    save_to_csv(data, csv_filename)
    save_to_json(data, json_filename)
    
    logger.info("=" * 50)
    logger.info(f"爬取完成！共获取 {len(data)} 条数据")
    logger.info(f"CSV文件: {csv_filename}")
    logger.info(f"JSON文件: {json_filename}")
    logger.info("=" * 50)
    
    # 打印前几条数据预览
    if data:
        logger.info("\n数据预览（前3条）:")
        for i, item in enumerate(data[:3], 1):
            logger.info(f"\n第 {i} 条:")
            logger.info(f"  公告编号: {item.get('announcement_number', 'N/A')}")
            logger.info(f"  发布时间: {item.get('publish_date', 'N/A')}")
            logger.info(f"  公司名称: {item.get('company_name', 'N/A')}")
            logger.info(f"  投诉人: {item.get('complaint_person', 'N/A')}")
            logger.info(f"  时间段: {item.get('period', 'N/A')}")
            logger.info(f"  缴费基数: {item.get('payment_base', 'N/A')}")


if __name__ == '__main__':
    main()
