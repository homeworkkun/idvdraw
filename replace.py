import os
import json
import requests
from urllib.parse import urlparse
import hashlib
import traceback
import mimetypes
import re

def get_file_hash(url):
    """根据URL生成文件名哈希值"""
    return hashlib.md5(url.encode()).hexdigest()

def get_extension_from_url(url):
    """从URL获取文件扩展名"""
    parsed_url = urlparse(url)
    filename = os.path.basename(parsed_url.path)
    
    if '.' in filename:
        return os.path.splitext(filename)[1]
    return ''

def get_extension_from_content_type(content_type):
    """根据Content-Type获取文件扩展名"""
    if not content_type:
        return ''
    
    # 常见的Content-Type到扩展名映射
    type_map = {
        'image/png': '.png',
        'image/jpeg': '.jpg',
        'image/jpg': '.jpg',
        'image/gif': '.gif',
        'image/webp': '.webp',
        'application/json': '.json',
        'text/html': '.html',
        'text/css': '.css',
        'application/javascript': '.js',
        'text/plain': '.txt',
        'application/pdf': '.pdf',
        'application/zip': '.zip',
        'application/x-zip-compressed': '.zip',
        'audio/mpeg': '.mp3',
        'video/mp4': '.mp4',
        'font/woff': '.woff',
        'font/woff2': '.woff2',
        'application/octet-stream': '.bin'
    }
    
    content_type = content_type.lower().split(';')[0].strip()
    return type_map.get(content_type, '')

def download_resource(url, resource_folder):
    """下载资源并返回本地路径"""
    if not url or not isinstance(url, str) or not url.startswith(('http://', 'https://')):
        return url
    
    # 创建文件夹
    try:
        os.makedirs(resource_folder, exist_ok=True)
    except Exception as e:
        print(f"创建目录失败 {resource_folder}: {str(e)}")
        return url
    
    # 根据URL生成唯一文件名
    url_hash = get_file_hash(url)
    
    # 确定文件扩展名
    extension = get_extension_from_url(url)
    
    # 如果URL中没有扩展名，尝试从Content-Type获取
    if not extension:
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            content_type = response.headers.get('content-type', '')
            extension = get_extension_from_content_type(content_type)
        except:
            pass
    
    # 如果仍然没有扩展名，使用默认扩展名
    if not extension:
        extension = '.dat'  # 默认二进制文件扩展名
    
    # 确保扩展名以点开头
    if extension and not extension.startswith('.'):
        extension = '.' + extension
    
    # 生成最终文件名
    filename = f"{url_hash}{extension}"
    file_path = os.path.join(resource_folder, filename)
    
    # 如果文件已存在，跳过下载
    if os.path.exists(file_path):
        print(f"  文件已存在，跳过下载: {filename}")
        return f"/resource/{filename}"
    
    # 下载文件
    try:
        print(f"  开始下载: {url[:80]}{'...' if len(url) > 80 else ''}")
        response = requests.get(url, timeout=60)  # 增加超时时间
        response.raise_for_status()
        
        with open(file_path, 'wb') as f:
            f.write(response.content)
        print(f"  下载成功: {filename} ({len(response.content)} bytes)")
        return f"/resource/{filename}"
    except Exception as e:
        print(f"  下载失败 {url}: {str(e)}")
        return url

def process_string_value(value, resource_folder):
    """处理字符串值，如果是HTTPS链接则下载并替换"""
    if isinstance(value, str) and value.startswith('https://'):
        # 更宽松的检查，处理任何https链接
        # 可以添加一些过滤条件，比如排除特定域名
        print(f"  发现HTTPS链接: {value[:80]}{'...' if len(value) > 80 else ''}")
        return download_resource(value, resource_folder)
    return value

def process_json_data(data, resource_folder, path=""):
    """递归处理JSON数据中的所有HTTPS链接"""
    try:
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                if isinstance(value, str):
                    data[key] = process_string_value(value, resource_folder)
                elif isinstance(value, dict):
                    process_json_data(value, resource_folder, current_path)
                elif isinstance(value, list):
                    process_list_data(value, resource_folder, current_path)
                elif isinstance(value, (int, float, bool)) and not isinstance(value, str):
                    # 跳过非字符串类型
                    pass
                    
        elif isinstance(data, list):
            process_list_data(data, resource_folder, path)
            
    except Exception as e:
        print(f"处理JSON数据时出错 (路径: {path}): {str(e)}")
        # 不中断处理过程
    
    return data

def process_list_data(data_list, resource_folder, path=""):
    """处理列表数据"""
    try:
        for i, item in enumerate(data_list):
            current_path = f"{path}[{i}]"
            
            if isinstance(item, str):
                data_list[i] = process_string_value(item, resource_folder)
            elif isinstance(item, dict):
                process_json_data(item, resource_folder, current_path)
            elif isinstance(item, list):
                process_list_data(item, resource_folder, current_path)
            elif isinstance(item, (int, float, bool)) and not isinstance(item, str):
                # 跳过非字符串类型
                pass
    except Exception as e:
        print(f"处理列表数据时出错 (路径: {path}): {str(e)}")

def process_json_file(file_path, resource_folder):
    """处理单个JSON文件"""
    try:
        print(f"\n开始处理JSON文件: {file_path}")
        
        # 读取JSON文件
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # 解析JSON
        data = json.loads(original_content)
        
        # 处理数据中的HTTPS链接
        processed_data = process_json_data(data, resource_folder, "")
        
        # 生成处理后的内容
        new_content = json.dumps(processed_data, ensure_ascii=False, indent=2)
        
        # 只有当内容发生变化时才写入文件
        if original_content != new_content:
            # 写回原文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✓ 更新JSON文件: {file_path}")
            return True
        else:
            print(f"- JSON文件无变化: {file_path}")
            return True
            
    except json.JSONDecodeError as e:
        print(f"✗ JSON解析错误 {file_path}: {str(e)}")
        # 如果不是有效的JSON文件，可能是其他文本文件，稍后处理
        return "not_json"
    except PermissionError as e:
        print(f"✗ 权限错误 {file_path}: {str(e)}")
        return False
    except Exception as e:
        print(f"✗ 处理JSON文件失败 {file_path}: {str(e)}")
        traceback.print_exc()
        return False

def find_all_files(root_dir, exclude_dirs=None):
    """递归查找所有文件"""
    if exclude_dirs is None:
        exclude_dirs = ['resource', '__pycache__', '.git', '.vscode', 'node_modules']
    
    all_files = []
    for root, dirs, files in os.walk(root_dir):
        # 排除指定目录
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            file_path = os.path.join(root, file)
            all_files.append(file_path)
    return all_files

def process_text_file(file_path, resource_folder):
    """处理文本文件中的HTTPS链接"""
    try:
        # 检查文件大小，避免处理过大的文件
        file_size = os.path.getsize(file_path)
        if file_size > 50 * 1024 * 1024:  # 50MB
            print(f"  跳过大文件: {file_path} ({file_size} bytes)")
            return True
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        original_content = content
        
        # 查找所有HTTPS链接
        https_pattern = r'https://[^\s"\'<>\)\}\]]+'
        matches = re.findall(https_pattern, content)
        
        # 去重并按长度排序（优先处理长链接）
        unique_matches = list(set(matches))
        unique_matches.sort(key=len, reverse=True)
        
        replacement_count = 0
        for match in unique_matches:
            # 过滤掉明显不是资源链接的内容
            if any(skip_word in match.lower() for skip_word in 
                   ['javascript:', 'mailto:', 'data:', 'about:']):
                continue
                
            print(f"  在文本中发现链接: {match[:60]}{'...' if len(match) > 60 else ''}")
            local_path = download_resource(match, resource_folder)
            
            if local_path != match:  # 如果确实发生了替换
                content = content.replace(match, local_path)
                replacement_count += 1
        
        # 只有当内容发生变化时才写入文件
        if original_content != content and replacement_count > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ 更新文本文件: {file_path} (替换了 {replacement_count} 个链接)")
            return True
        else:
            print(f"- 文本文件无变化: {file_path}")
            return True
            
    except UnicodeDecodeError:
        print(f"  跳过二进制文件: {file_path}")
        return True
    except Exception as e:
        print(f"✗ 处理文本文件失败 {file_path}: {str(e)}")
        return False

def should_process_as_text(file_path):
    """判断文件是否应该作为文本文件处理"""
    # 已知的文本文件扩展名
    text_extensions = {
        '.json', '.txt', '.md', '.html', '.htm', '.css', '.js', '.jsx', '.ts', '.tsx',
        '.xml', '.yaml', '.yml', '.ini', '.conf', '.config', '.log', '.csv', '.sql',
        '.php', '.py', '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.rb', '.go',
        '.sh', '.bat', '.cmd', '.ps1', '.vue', '.scss', '.sass', '.less'
    }
    
    # 检查扩展名
    _, ext = os.path.splitext(file_path.lower())
    if ext in text_extensions:
        return True
    
    # 检查文件名
    filename = os.path.basename(file_path).lower()
    if filename in ['readme', 'license', 'changelog', 'package', 'composer']:
        return True
    
    return False

def main():
    # 设置目录路径
    current_dir = os.getcwd()
    resource_folder = os.path.join(current_dir, 'resource')
    
    print(f"当前工作目录: {current_dir}")
    print(f"资源保存目录: {resource_folder}")
    
    # 查找所有文件
    all_files = find_all_files(current_dir)
    
    if not all_files:
        print("未找到任何文件")
        return
    
    print(f"总共找到 {len(all_files)} 个文件")
    
    # 分类处理文件
    json_files = []
    text_files = []
    other_files = []
    
    for file_path in all_files:
        if file_path.endswith('.json'):
            json_files.append(file_path)
        elif should_process_as_text(file_path):
            text_files.append(file_path)
        else:
            other_files.append(file_path)
    
    print(f"JSON文件: {len(json_files)} 个")
    print(f"文本文件: {len(text_files)} 个")
    print(f"其他文件: {len(other_files)} 个")
    
    # 统计信息
    total_processed = 0
    success_count = 0
    failed_files = []
    
    # 处理JSON文件
    if json_files:
        print(f"\n{'='*50}")
        print(f"开始处理 {len(json_files)} 个JSON文件")
        print(f"{'='*50}")
        
        for i, json_file in enumerate(json_files, 1):
            print(f"\n[{i}/{len(json_files)}] 正在处理: {json_file}")
            result = process_json_file(json_file, resource_folder)
            if result == True:
                success_count += 1
                total_processed += 1
            elif result == "not_json":
                # 如果不是有效的JSON，当作普通文本文件处理
                if process_text_file(json_file, resource_folder):
                    success_count += 1
                    total_processed += 1
                else:
                    failed_files.append(json_file)
            else:
                failed_files.append(json_file)
    
    # 处理文本文件
    if text_files:
        print(f"\n{'='*50}")
        print(f"开始处理 {len(text_files)} 个文本文件")
        print(f"{'='*50}")
        
        for i, text_file in enumerate(text_files, 1):
            print(f"\n[{i}/{len(text_files)}] 正在处理: {text_file}")
            if process_text_file(text_file, resource_folder):
                success_count += 1
                total_processed += 1
            else:
                failed_files.append(text_file)
    
    # 其他文件通常不需要处理内容，除非有特殊需求
    
    print(f"\n{'='*60}")
    print(f"处理完成统计:")
    print(f"总共处理: {total_processed} 个文件")
    print(f"成功处理: {success_count} 个文件")
    print(f"失败处理: {len(failed_files)} 个文件")
    
    if failed_files:
        print(f"\n失败的文件列表 (前20个):")
        for file in failed_files[:20]:
            print(f"  - {file}")
        if len(failed_files) > 20:
            print(f"  ... 还有 {len(failed_files) - 20} 个文件")

if __name__ == "__main__":
    main()
