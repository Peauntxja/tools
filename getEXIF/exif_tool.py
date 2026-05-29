#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EXIF 信息读取和修改工具
支持读取、显示和修改图片的 EXIF 元数据
支持 JPEG, TIFF 和 PNG 格式
"""

import os
import sys
import json
import shutil
import argparse
from datetime import datetime
from PIL import Image, ExifTags
import piexif


def read_exif(image_path):
    """
    读取图片的 EXIF 信息
    
    Args:
        image_path (str): 图片文件路径
        
    Returns:
        dict: EXIF 数据字典，格式为 {'format': 'jpeg'|'png', 'data': {...}, 'metadata': {...}}
             如果读取失败返回 None
    """
    try:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"文件不存在: {image_path}")
        
        # 检查文件格式
        valid_extensions = ('.jpg', '.jpeg', '.tiff', '.tif', '.png')
        if not image_path.lower().endswith(valid_extensions):
            raise ValueError(f"不支持的文件格式: {image_path}")
        
        # 打开图片
        image = Image.open(image_path)
        image_format = image.format.lower() if image.format else ''
        
        result = {
            'format': 'png' if image_path.lower().endswith('.png') else 'jpeg',
            'data': {},
            'metadata': {}
        }
        
        # PNG 格式处理
        if image_path.lower().endswith('.png'):
            # 使用 Pillow 的 getexif() 方法读取 EXIF（PNG 3.0+ 支持）
            exif = image.getexif()
            if exif:
                exif_dict = {}
                for tag_id, value in exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                    exif_dict[tag_id] = {
                        'name': tag_name,
                        'value': value
                    }
                result['data'] = exif_dict
            
            # 读取 PNG 文本块元数据
            png_metadata = {}
            if hasattr(image, 'text') and image.text:
                png_metadata = dict(image.text)
            result['metadata'] = png_metadata
            
            # 如果没有 EXIF 和文本块，返回 None
            if not result['data'] and not result['metadata']:
                return None
        
        # JPEG/TIFF 格式处理
        else:
            if 'exif' in image.info:
                exif_dict = piexif.load(image.info['exif'])
                result['data'] = exif_dict
            else:
                return None
        
        return result
    
    except Exception as e:
        print(f"读取 EXIF 信息时出错: {e}", file=sys.stderr)
        return None


def format_exif_value(value):
    """
    格式化 EXIF 值以便显示
    
    Args:
        value: EXIF 原始值
        
    Returns:
        str: 格式化后的字符串
    """
    if isinstance(value, bytes):
        try:
            return value.decode('utf-8').rstrip('\x00')
        except:
            return value.hex()
    elif isinstance(value, tuple):
        return ', '.join(str(v) for v in value)
    else:
        return str(value)


def print_exif(exif_data, output_format='text'):
    """
    格式化输出 EXIF 信息
    
    Args:
        exif_data (dict): EXIF 数据字典（统一格式）
        output_format (str): 输出格式 ('text' 或 'json')
    """
    if exif_data is None:
        print("该图片没有 EXIF 信息")
        return
    
    # 兼容旧格式（直接是 piexif 字典）
    if 'format' not in exif_data:
        # 旧格式：直接是 piexif 字典
        if output_format == 'json':
            json_data = {}
            for ifd_name in exif_data:
                if ifd_name == 'thumbnail':
                    continue
                json_data[ifd_name] = {}
                for tag in exif_data[ifd_name]:
                    tag_name = piexif.TAGS[ifd_name][tag]['name']
                    value = exif_data[ifd_name][tag]
                    json_data[ifd_name][tag_name] = format_exif_value(value)
            print(json.dumps(json_data, indent=2, ensure_ascii=False))
        else:
            print("\n=== EXIF 信息 ===")
            for ifd_name in exif_data:
                if ifd_name == 'thumbnail':
                    continue
                print(f"\n[{ifd_name}]")
                for tag in exif_data[ifd_name]:
                    tag_name = piexif.TAGS[ifd_name][tag]['name']
                    value = exif_data[ifd_name][tag]
                    formatted_value = format_exif_value(value)
                    print(f"  {tag_name}: {formatted_value}")
            print("=" * 50)
        return
    
    # 新格式：统一格式
    image_format = exif_data.get('format', 'jpeg')
    exif_dict = exif_data.get('data', {})
    metadata = exif_data.get('metadata', {})
    
    if output_format == 'json':
        json_data = {}
        
        # EXIF 数据
        if image_format == 'png' and exif_dict:
            json_data['EXIF'] = {}
            for tag_id, tag_info in exif_dict.items():
                tag_name = tag_info.get('name', tag_id)
                value = tag_info.get('value', '')
                json_data['EXIF'][tag_name] = format_exif_value(value)
        elif image_format == 'jpeg' and exif_dict:
            for ifd_name in exif_dict:
                if ifd_name == 'thumbnail':
                    continue
                json_data[ifd_name] = {}
                for tag in exif_dict[ifd_name]:
                    tag_name = piexif.TAGS[ifd_name][tag]['name']
                    value = exif_dict[ifd_name][tag]
                    json_data[ifd_name][tag_name] = format_exif_value(value)
        
        # PNG 文本块元数据
        if metadata:
            json_data['PNG_Metadata'] = metadata
        
        print(json.dumps(json_data, indent=2, ensure_ascii=False))
    else:
        # 文本格式输出
        print("\n=== EXIF 信息 ===")
        
        # EXIF 数据
        if image_format == 'png' and exif_dict:
            print("\n[EXIF]")
            for tag_id, tag_info in exif_dict.items():
                tag_name = tag_info.get('name', tag_id)
                value = tag_info.get('value', '')
                formatted_value = format_exif_value(value)
                print(f"  {tag_name}: {formatted_value}")
        elif image_format == 'jpeg' and exif_dict:
            for ifd_name in exif_dict:
                if ifd_name == 'thumbnail':
                    continue
                print(f"\n[{ifd_name}]")
                for tag in exif_dict[ifd_name]:
                    tag_name = piexif.TAGS[ifd_name][tag]['name']
                    value = exif_dict[ifd_name][tag]
                    formatted_value = format_exif_value(value)
                    print(f"  {tag_name}: {formatted_value}")
        
        # PNG 文本块元数据
        if metadata:
            print("\n[PNG 文本块元数据]")
            for key, value in metadata.items():
                print(f"  {key}: {value}")
        
        print("=" * 50)


def backup_image(image_path):
    """
    备份原图
    
    Args:
        image_path (str): 图片文件路径
        
    Returns:
        str: 备份文件路径，如果备份失败返回 None
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(image_path)[0]
        extension = os.path.splitext(image_path)[1]
        backup_path = f"{base_name}_backup_{timestamp}{extension}"
        shutil.copy2(image_path, backup_path)
        return backup_path
    except Exception as e:
        print(f"备份文件时出错: {e}", file=sys.stderr)
        return None


def modify_exif(image_path, modifications, create_backup=True):
    """
    修改图片的 EXIF 信息
    
    Args:
        image_path (str): 图片文件路径
        modifications (dict): 修改字典，格式为 {ifd: {tag_name: value}}
        create_backup (bool): 是否创建备份
        
    Returns:
        bool: 修改是否成功
    """
    try:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"文件不存在: {image_path}")
        
        is_png = image_path.lower().endswith('.png')
        
        # 创建备份
        if create_backup:
            backup_path = backup_image(image_path)
            if backup_path:
                print(f"已创建备份: {backup_path}")
            else:
                response = input("备份失败，是否继续？(y/n): ")
                if response.lower() != 'y':
                    return False
        
        # 打开图片
        image = Image.open(image_path)
        
        # PNG 格式处理
        if is_png:
            # 获取现有 EXIF
            exif = image.getexif()
            
            # 应用修改
            for ifd_name, tags in modifications.items():
                for tag_name, value in tags.items():
                    # 查找标签 ID（通过标签名称）
                    tag_id = None
                    for tag, tag_info in ExifTags.TAGS.items():
                        if isinstance(tag_info, str) and tag_info == tag_name:
                            tag_id = tag
                            break
                    
                    if tag_id is None:
                        print(f"警告: 未找到标签 '{tag_name}'，PNG 格式可能不支持此标签", file=sys.stderr)
                        continue
                    
                    # 设置 EXIF 值
                    exif[tag_id] = value
            
            # 保存 PNG（Pillow 会自动处理 EXIF）
            # 注意：PNG 3.0+ 才支持 EXIF，如果图片不支持，EXIF 可能不会被保存
            exif_bytes = exif.tobytes() if exif else None
            if exif_bytes:
                image.save(image_path, format='PNG', exif=exif_bytes)
            else:
                image.save(image_path, format='PNG')
            print(f"已成功修改 {image_path} 的 EXIF 信息")
            print("注意: PNG 格式的 EXIF 支持取决于 PNG 版本（需要 PNG 3.0+）", file=sys.stderr)
            return True
        
        # JPEG/TIFF 格式处理
        else:
            exif_dict = {}
            if 'exif' in image.info:
                exif_dict = piexif.load(image.info['exif'])
            else:
                # 如果没有 EXIF，创建新的
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
            
            # 应用修改
            for ifd_name, tags in modifications.items():
                if ifd_name not in exif_dict:
                    exif_dict[ifd_name] = {}
                
                for tag_name, value in tags.items():
                    # 查找标签 ID
                    tag_id = None
                    for tag, tag_info in piexif.TAGS[ifd_name].items():
                        if tag_info['name'] == tag_name:
                            tag_id = tag
                            break
                    
                    if tag_id is None:
                        print(f"警告: 未找到标签 '{tag_name}' 在 {ifd_name} 中", file=sys.stderr)
                        continue
                    
                    # 转换值为字节（如果需要）
                    if isinstance(value, str):
                        value = value.encode('utf-8')
                    
                    exif_dict[ifd_name][tag_id] = value
            
            # 保存修改后的图片
            exif_bytes = piexif.dump(exif_dict)
            image.save(image_path, exif=exif_bytes)
            print(f"已成功修改 {image_path} 的 EXIF 信息")
            return True
    
    except Exception as e:
        print(f"修改 EXIF 信息时出错: {e}", file=sys.stderr)
        return False


def process_batch(directory, operation='read', modifications=None, output_format='text'):
    """
    批量处理目录中的图片
    
    Args:
        directory (str): 目录路径
        operation (str): 操作类型 ('read' 或 'modify')
        modifications (dict): 修改字典（仅用于 modify 操作）
        output_format (str): 输出格式
    """
    valid_extensions = ('.jpg', '.jpeg', '.tiff', '.tif', '.png')
    image_files = [
        f for f in os.listdir(directory)
        if f.lower().endswith(valid_extensions)
    ]
    
    if not image_files:
        print(f"在 {directory} 中未找到支持的图片文件")
        return
    
    print(f"找到 {len(image_files)} 个图片文件\n")
    
    for filename in image_files:
        filepath = os.path.join(directory, filename)
        print(f"\n处理文件: {filename}")
        print("-" * 50)
        
        if operation == 'read':
            exif_data = read_exif(filepath)
            print_exif(exif_data, output_format)
        elif operation == 'modify' and modifications:
            modify_exif(filepath, modifications)


def main():
    """主函数，处理命令行参数"""
    parser = argparse.ArgumentParser(
        description='EXIF 信息读取和修改工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 读取 EXIF 信息
  python exif_tool.py --read image.jpg
  
  # 读取 EXIF 信息（JSON 格式）
  python exif_tool.py --read image.jpg --output json
  
  # 修改拍摄日期
  python exif_tool.py --modify image.jpg --field DateTimeOriginal --value "2025:01:01 12:00:00"
  
  # 批量读取目录中的图片
  python exif_tool.py --batch ./images
  
  # 批量修改目录中的图片
  python exif_tool.py --batch ./images --modify --field DateTimeOriginal --value "2025:01:01 12:00:00"
        """
    )
    
    parser.add_argument('--read', type=str, help='读取指定图片的 EXIF 信息')
    parser.add_argument('--modify', type=str, help='修改指定图片的 EXIF 信息')
    parser.add_argument('--batch', type=str, help='批量处理指定目录中的图片')
    parser.add_argument('--field', type=str, help='要修改的 EXIF 字段名（如 DateTimeOriginal）')
    parser.add_argument('--value', type=str, help='字段的新值')
    parser.add_argument('--ifd', type=str, default='Exif', 
                       help='EXIF IFD 类型 (0th, Exif, GPS, 1st)，默认为 Exif')
    parser.add_argument('--output', type=str, choices=['text', 'json'], default='text',
                       help='输出格式 (text 或 json)，默认为 text')
    parser.add_argument('--no-backup', action='store_true',
                       help='修改时不创建备份')
    
    args = parser.parse_args()
    
    # 读取操作
    if args.read:
        exif_data = read_exif(args.read)
        print_exif(exif_data, args.output)
    
    # 修改操作
    elif args.modify:
        if not args.field or not args.value:
            print("错误: 修改操作需要指定 --field 和 --value 参数", file=sys.stderr)
            sys.exit(1)
        
        modifications = {
            args.ifd: {
                args.field: args.value
            }
        }
        modify_exif(args.modify, modifications, create_backup=not args.no_backup)
    
    # 批量处理
    elif args.batch:
        if args.modify or (args.field and args.value):
            # 批量修改
            modifications = {
                args.ifd: {
                    args.field: args.value
                }
            } if args.field and args.value else None
            process_batch(args.batch, operation='modify', modifications=modifications, output_format=args.output)
        else:
            # 批量读取
            process_batch(args.batch, operation='read', output_format=args.output)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

