import requests
import time
import os
from typing import Optional, Dict, Any
import ssl
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter as RequestsHTTPAdapter


class RetryHTTPAdapter(RequestsHTTPAdapter):
    """支持SSL错误重试的HTTP适配器"""
    def __init__(self, *args, **kwargs):
        self.max_retries = kwargs.pop('max_retries', 5)
        super().__init__(*args, **kwargs)
    
    def init_poolmanager(self, *args, **kwargs):
        kwargs['ssl_context'] = ssl.create_default_context()
        kwargs['ssl_context'].check_hostname = False
        kwargs['ssl_context'].verify_mode = ssl.CERT_NONE
        return super().init_poolmanager(*args, **kwargs)


def download_file_with_retry(
    url: str, 
    file_path: str, 
    max_retries: int = 5, 
    delay_between_downloads: float = 1.0,
    timeout: int = 60,
    filename: Optional[str] = None
) -> Dict[str, Any]:
    """
    带重试机制的文件下载函数
    
    Args:
        url: 下载链接
        file_path: 保存路径
        max_retries: 最大重试次数（默认5次）
        delay_between_downloads: 下载间隔时间（秒）
        timeout: 请求超时时间（秒）
        filename: 文件名（用于日志显示）
    
    Returns:
        dict: 包含成功状态、错误信息等的结果字典
    """
    display_name = filename or os.path.basename(file_path)
    
    # 创建session并配置重试策略
    session = requests.Session()
    
    # 配置重试策略
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    
    # 使用自定义适配器处理SSL错误
    adapter = RetryHTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # 设置请求头
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
    })
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            print(f"正在下载 {display_name} (尝试 {attempt + 1}/{max_retries})")
            
            # 发起请求
            response = session.get(url, stream=True, timeout=timeout)
            response.raise_for_status()
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 下载文件
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            print(f"下载成功: {display_name}")
            
            # 添加延时（最后一次下载后不需要延时）
            if delay_between_downloads > 0 and attempt < max_retries - 1:
                time.sleep(delay_between_downloads)
            
            return {
                'success': True,
                'file_path': file_path,
                'filename': display_name,
                'attempts': attempt + 1
            }
            
        except requests.exceptions.SSLError as e:
            last_error = f"SSL错误: {str(e)}"
            print(f"下载失败 {display_name} (尝试 {attempt + 1}/{max_retries}): {last_error}")
            
        except requests.exceptions.Timeout as e:
            last_error = f"请求超时: {str(e)}"
            print(f"下载失败 {display_name} (尝试 {attempt + 1}/{max_retries}): {last_error}")
            
        except requests.exceptions.ConnectionError as e:
            last_error = f"连接错误: {str(e)}"
            print(f"下载失败 {display_name} (尝试 {attempt + 1}/{max_retries}): {last_error}")
            
        except requests.exceptions.HTTPError as e:
            last_error = f"HTTP错误: {str(e)}"
            print(f"下载失败 {display_name} (尝试 {attempt + 1}/{max_retries}): {last_error}")
            
        except Exception as e:
            last_error = f"未知错误: {str(e)}"
            print(f"下载失败 {display_name} (尝试 {attempt + 1}/{max_retries}): {last_error}")
        
        # 重试前等待
        if attempt < max_retries - 1:
            wait_time = min(2 ** attempt, 10)  # 指数退避，最多等待10秒
            print(f"等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)
    
    # 所有重试都失败了
    print(f"下载最终失败 {display_name}: {last_error}")
    return {
        'success': False,
        'filename': display_name,
        'error': last_error,
        'attempts': max_retries
    }


def batch_download_files(
    file_infos: list,
    max_retries: int = 5,
    delay_between_downloads: float = 0,  # 并行下载不需要间隔
    timeout: int = 60,
    max_workers: int = 5  # 最大并行下载数
) -> Dict[str, Any]:
    """
    批量下载文件（支持并行下载）
    
    Args:
        file_infos: 文件信息列表，每个元素包含 url, file_path, filename
        max_retries: 最大重试次数
        delay_between_downloads: 下载间隔时间（并行下载时忽略此参数）
        timeout: 请求超时时间
        max_workers: 最大并行下载数（默认5个）
    
    Returns:
        dict: 包含成功和失败统计的结果字典
    """
    import concurrent.futures
    
    success_count = 0
    failed_files = []
    successful_files = []
    
    total_files = len(file_infos)
    print(f"开始批量下载，共 {total_files} 个文件，最大并行数: {max_workers}")
    
    # 使用线程池并发下载
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有下载任务
        future_to_file_info = {
            executor.submit(
                download_file_with_retry,
                url=file_info['url'],
                file_path=file_info['file_path'],
                max_retries=max_retries,
                delay_between_downloads=0,  # 并行下载内部不需要延迟
                timeout=timeout,
                filename=file_info.get('filename')
            ): file_info for file_info in file_infos
        }
        
        # 等待所有任务完成
        completed = 0
        for future in concurrent.futures.as_completed(future_to_file_info):
            completed += 1
            result = future.result()
            
            print(f"下载进度: {completed}/{total_files}")
            
            if result['success']:
                success_count += 1
                successful_files.append(result)
            else:
                failed_files.append(result)
    
    print(f"\n批量下载完成: 成功 {success_count} 个，失败 {len(failed_files)} 个")
    
    return {
        'success_count': success_count,
        'failed_count': len(failed_files),
        'total_count': total_files,
        'successful_files': successful_files,
        'failed_files': failed_files
    }


def download_single_file(
    url: str,
    file_path: str,
    max_retries: int = 3,
    timeout: int = 60
) -> Dict[str, Any]:
    """
    单个文件下载函数（简化版本，用于单个视频下载）

    Args:
        url: 下载链接
        file_path: 保存路径
        max_retries: 最大重试次数（默认3次）
        timeout: 请求超时时间（秒）

    Returns:
        dict: 包含成功状态、错误信息等的结果字典
    """
    return download_file_with_retry(
        url=url,
        file_path=file_path,
        max_retries=max_retries,
        delay_between_downloads=0,  # 单个文件下载不需要间隔
        timeout=timeout,
        filename=os.path.basename(file_path)
    ) 