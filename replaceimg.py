import os
import json
import requests
from urllib.parse import urlparse
import traceback

def download_image(url, folder_path):
    """下载图片并返回本地路径"""
    if not url or not isinstance(url, str) or not url.startswith(('http://', 'https://')):
        return url
    
    # 创建文件夹
    try:
        os.makedirs(folder_path, exist_ok=True)
    except Exception as e:
        print(f"创建目录失败 {folder_path}: {str(e)}")
        return url
    
    # 获取文件名
    try:
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        
        # 处理特殊字符
        filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        
        # 如果URL没有明确的文件扩展名，则尝试从Content-Type获取
        if not os.path.splitext(filename)[1]:
            try:
                response = requests.head(url, timeout=10)
                content_type = response.headers.get('content-type', '').lower()
                if 'png' in content_type:
                    filename += '.png'
                elif 'jpeg' in content_type or 'jpg' in content_type:
                    filename += '.jpg'
                elif 'gif' in content_type:
                    filename += '.gif'
                elif 'webp' in content_type:
                    filename += '.webp'
            except:
                # 默认使用.png扩展名
                filename += '.png'
        
        file_path = os.path.join(folder_path, filename)
        
        # 如果文件已存在，跳过下载
        if os.path.exists(file_path):
            print(f"  文件已存在，跳过下载: {filename}")
            return f"./img/{filename}"
        
        # 下载文件
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        with open(file_path, 'wb') as f:
            f.write(response.content)
        print(f"  下载成功: {filename}")
        return f"./img/{filename}"
    except Exception as e:
        print(f"  下载失败 {url}: {str(e)}")
        return url

def process_json_data(data, img_folder, file_path=""):
    """处理JSON数据中的所有图片链接"""
    try:
        if isinstance(data, dict):
            # 处理常见的图片字段
            image_fields = ['image', 'essenceImage', 'img']
            for field in image_fields:
                if field in data and data[field]:
                    if isinstance(data[field], str) and data[field].startswith(('http://', 'https://')):
                        print(f"  处理字段 {field}")
                        local_path = download_image(data[field], img_folder)
                        data[field] = local_path
            
            # 处理特殊结构
            # 处理fragmentsInfo
            if 'fragmentsInfo' in data and isinstance(data['fragmentsInfo'], dict):
                if 'img' in data['fragmentsInfo'] and isinstance(data['fragmentsInfo']['img'], str):
                    if data['fragmentsInfo']['img'].startswith(('http://', 'https://')):
                        print(f"  处理 fragmentsInfo.img")
                        local_path = download_image(data['fragmentsInfo']['img'], img_folder)
                        data['fragmentsInfo']['img'] = local_path
            
            # 处理items
            if 'items' in data and isinstance(data['items'], dict):
                for rarity_key, rarity_items in data['items'].items():
                    if isinstance(rarity_items, list):
                        for i, item in enumerate(rarity_items):
                            if isinstance(item, dict) and 'img' in item and isinstance(item['img'], str):
                                if item['img'].startswith(('http://', 'https://')):
                                    print(f"  处理 items[{rarity_key}][{i}].img")
                                    local_path = download_image(item['img'], img_folder)
                                    item['img'] = local_path
            
            # 处理award
            if 'award' in data and isinstance(data['award'], dict):
                for award_key, award_value in data['award'].items():
                    if isinstance(award_value, list):
                        for i, val in enumerate(award_value):
                            if isinstance(val, str) and val.startswith(('http://', 'https://')):
                                if any(ext in val.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                                    print(f"  处理 award[{award_key}][{i}]")
                                    local_path = download_image(val, img_folder)
                                    award_value[i] = local_path
            
            # 通用处理所有字段
            for key, value in data.items():
                if isinstance(value, str) and value.startswith(('http://', 'https://')):
                    if any(ext in value.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                        print(f"  处理字段 {key}")
                        local_path = download_image(value, img_folder)
                        data[key] = local_path
                elif isinstance(value, dict):
                    process_json_data(value, img_folder, f"{file_path}.{key}")
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, str) and item.startswith(('http://', 'https://')):
                            if any(ext in item.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                                print(f"  处理数组 {key}[{i}]")
                                local_path = download_image(item, img_folder)
                                value[i] = local_path
                        elif isinstance(item, dict):
                            process_json_data(item, img_folder, f"{file_path}.{key}[{i}]")
                        elif isinstance(item, list):
                            for j, sub_item in enumerate(item):
                                if isinstance(sub_item, str) and sub_item.startswith(('http://', 'https://')):
                                    if any(ext in sub_item.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                                        print(f"  处理数组 {key}[{i}][{j}]")
                                        local_path = download_image(sub_item, img_folder)
                                        item[j] = local_path
                                        
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, str) and item.startswith(('http://', 'https://')):
                    if any(ext in item.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                        print(f"  处理数组 [{i}]")
                        local_path = download_image(item, img_folder)
                        data[i] = local_path
                elif isinstance(item, dict):
                    process_json_data(item, img_folder, f"{file_path}[{i}]")
                elif isinstance(item, list):
                    for j, sub_item in enumerate(item):
                        if isinstance(sub_item, str) and sub_item.startswith(('http://', 'https://')):
                            if any(ext in sub_item.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                                print(f"  处理数组 [{i}][{j}]")
                                local_path = download_image(sub_item, img_folder)
                                item[j] = local_path
    except Exception as e:
        print(f"处理JSON数据时出错: {str(e)}")
        traceback.print_exc()
    
    return data

def process_json_file(file_path, img_folder):
    """处理单个JSON文件"""
    try:
        print(f"\n开始处理文件: {file_path}")
        
        # 读取JSON文件
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 处理数据中的图片链接
        processed_data = process_json_data(data, img_folder, file_path)
        
        # 写回原文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 成功处理文件: {file_path}")
        return True
        
    except json.JSONDecodeError as e:
        print(f"✗ JSON解析错误 {file_path}: {str(e)}")
        return False
    except PermissionError as e:
        print(f"✗ 权限错误 {file_path}: {str(e)}")
        return False
    except Exception as e:
        print(f"✗ 处理文件失败 {file_path}: {str(e)}")
        traceback.print_exc()
        return False

def find_all_json_files(root_dir):
    """递归查找所有JSON文件"""
    json_files = []
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.json'):
                json_files.append(os.path.join(root, file))
    return json_files

def main():
    # 设置目录路径
    current_dir = os.getcwd()
    img_folder = os.path.join(current_dir, 'img')
    
    print(f"当前工作目录: {current_dir}")
    print(f"图片保存目录: {img_folder}")
    
    # 查找所有JSON文件（包括子目录）
    json_files = find_all_json_files(current_dir)
    
    if not json_files:
        print("未找到任何JSON文件")
        return
    
    print(f"总共找到 {len(json_files)} 个JSON文件")
    
    # 处理每个JSON文件
    success_count = 0
    failed_files = []
    
    for i, json_file in enumerate(json_files, 1):
        print(f"\n[{i}/{len(json_files)}] 正在处理: {json_file}")
        if process_json_file(json_file, img_folder):
            success_count += 1
        else:
            failed_files.append(json_file)
    
    print(f"\n" + "="*50)
    print(f"处理完成统计:")
    print(f"成功处理: {success_count}/{len(json_files)} 个文件")
    print(f"失败处理: {len(failed_files)}/{len(json_files)} 个文件")
    
    if failed_files:
        print(f"\n失败的文件列表:")
        for file in failed_files:
            print(f"  - {file}")

if __name__ == "__main__":
    main()
