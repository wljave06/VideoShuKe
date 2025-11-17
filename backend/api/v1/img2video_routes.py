# -*- coding: utf-8 -*-
"""
即梦图生视频API路由
"""

import os
import json
import requests
import asyncio
import pandas as pd
from datetime import datetime
from flask import Blueprint, request, jsonify
from backend.models.models import JimengImg2VideoTask
import subprocess
import platform
import threading
from urllib.parse import urlparse

def is_cache_directory_file(file_path):
    """判断文件是否在缓存目录中，只有缓存目录的文件才会被删除"""
    if not file_path:
        return False

    try:
        # 标准化路径
        file_path = os.path.abspath(file_path)

        # 获取项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        # 定义缓存目录列表
        cache_directories = [
            os.path.join(project_root, 'tmp', 'batch_upload'),
            os.path.join(project_root, 'tmp', 'first_last_frame_upload'),
        ]

        # 检查文件是否在任何缓存目录中
        for cache_dir in cache_directories:
            cache_dir = os.path.abspath(cache_dir)
            if file_path.startswith(cache_dir):
                print(f"文件 {file_path} 在缓存目录 {cache_dir} 中，允许删除")
                return True

        print(f"文件 {file_path} 不在缓存目录中，保护原始文件不被删除")
        return False

    except Exception as e:
        print(f"判断文件路径时出错: {str(e)}")
        # 出错时默认保护文件，不删除
        return False

def safe_remove_image_file(image_path):
    """安全删除图片文件，只删除缓存目录中的文件"""
    if not image_path or not os.path.exists(image_path):
        return False

    try:
        if is_cache_directory_file(image_path):
            os.remove(image_path)
            print(f"已删除缓存图片文件: {image_path}")
            return True
        else:
            print(f"跳过删除原始图片文件: {image_path}")
            return False
    except Exception as e:
        print(f"删除图片文件失败: {image_path}, 错误: {str(e)}")
        return False

# 创建蓝图
jimeng_img2video_bp = Blueprint('jimeng_img2video', __name__, url_prefix='/api/jimeng/img2video')

@jimeng_img2video_bp.route('/tasks', methods=['GET'])
def get_img2video_tasks():
    """获取图生视频任务列表"""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 1000))
        status = request.args.get('status', None)
        
        print("获取图生视频任务列表，页码: {}, 每页数量: {}, 状态: {}".format(page, page_size, status))
        
        # 构建查询 - 过滤掉空任务
        query = JimengImg2VideoTask.select()
        if status is not None:
            query = query.where(JimengImg2VideoTask.status == status)
        
        # 分页
        total = query.count()
        tasks = query.order_by(JimengImg2VideoTask.create_at.desc()).paginate(page, page_size)
        
        data = []
        for task in tasks:
            data.append({
                'id': task.id,
                'prompt': task.prompt,
                'model': task.model,
                'second': task.second,
                'resolution': task.resolution,  # 新增分辨率字段
                'status': task.status,
                'status_text': task.get_status_text(),
                'account_id': task.account_id,
                'image_path': task.image_path,
                'video_url': task.video_url,
                'failure_reason': task.failure_reason,  # 失败原因类型
                'error_message': task.error_message,  # 详细错误信息
                'create_at': task.create_at.strftime('%Y-%m-%d %H:%M:%S') if task.create_at else None,
                'update_at': task.update_at.strftime('%Y-%m-%d %H:%M:%S') if task.update_at else None
            })
        
        return jsonify({
            'success': True,
            'data': data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total,
                'pages': (total + page_size - 1) // page_size
            }
        })
        
    except Exception as e:
        print(f"获取图生视频任务列表失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@jimeng_img2video_bp.route('/tasks', methods=['POST'])
def create_img2video_task():
    """创建图生视频任务"""
    try:
        data = request.get_json()
        
        # 单个任务创建
        if 'prompt' in data and 'image_path' in data:
            task = JimengImg2VideoTask.create(
                prompt=data['prompt'],
                model=data.get('model', 'Video 3.0'),
                second=data.get('second', 5),
                resolution=data.get('resolution', '1080p'),  # 添加分辨率参数
                image_path=data['image_path'],
                status=0
            )
            
            print(f"创建图生视频任务: {task.id}")
            return jsonify({'success': True, 'data': {'task_id': task.id}})
        
        # 批量任务创建
        elif 'tasks' in data:
            tasks = data['tasks']
            created_tasks = []
            
            for task_data in tasks:
                task = JimengImg2VideoTask.create(
                    prompt=task_data.get('prompt', ''),
                    model=task_data.get('model', 'Video 3.0'),
                    second=task_data.get('second', 5),
                    resolution=task_data.get('resolution', '1080p'),  # 添加分辨率参数
                    image_path=task_data['image_path'],
                    status=0
                )
                created_tasks.append(task.id)
            
            print(f"批量创建图生视频任务: {len(created_tasks)}个")
            return jsonify({'success': True, 'data': {'task_ids': created_tasks}})
        
        else:
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400
            
    except Exception as e:
        print(f"创建图生视频任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@jimeng_img2video_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_img2video_task(task_id):
    """删除图生视频任务"""
    try:
        task = JimengImg2VideoTask.get_by_id(task_id)

        # 安全删除关联的图片文件（只删除缓存目录中的文件）
        deleted_files_count = 0
        try:
            if safe_remove_image_file(task.image_path):
                deleted_files_count += 1
        except Exception as file_error:
            print(f"删除图片文件时出错（但任务仍会被删除）: {str(file_error)}")

        # 删除任务记录
        task.delete_instance()

        print(f"删除图生视频任务: {task_id}，清理了 {deleted_files_count} 个缓存文件")
        return jsonify({
            'success': True,
            'message': f'任务删除成功，清理了 {deleted_files_count} 个缓存文件',
            'data': {
                'deleted_files_count': deleted_files_count
            }
        })

    except JimengImg2VideoTask.DoesNotExist:
        return jsonify({'success': False, 'message': '任务不存在'}), 404
    except Exception as e:
        print(f"删除图生视频任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@jimeng_img2video_bp.route('/tasks/<int:task_id>/retry', methods=['POST'])
def retry_img2video_task(task_id):
    """重试图生视频任务"""
    try:
        task = JimengImg2VideoTask.get_by_id(task_id)
        task.update_status(0)  # 重置为排队状态
        
        print(f"重试图生视频任务: {task_id}")
        return jsonify({'success': True, 'message': '任务已重新加入队列'})
        
    except JimengImg2VideoTask.DoesNotExist:
        return jsonify({'success': False, 'message': '任务不存在'}), 404
    except Exception as e:
        print(f"重试图生视频任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@jimeng_img2video_bp.route('/tasks/batch-retry', methods=['POST'])
def batch_retry_img2video_tasks():
    """批量重试失败的图生视频任务"""
    try:
        data = request.get_json()
        task_ids = data.get('task_ids', [])
        
        if task_ids:
            # 如果提供了特定的任务ID列表，只重试这些任务
            tasks = JimengImg2VideoTask.select().where(
                JimengImg2VideoTask.id.in_(task_ids),
                JimengImg2VideoTask.status == 3  # 只重试失败的任务
            )
            retry_count = 0
            for task in tasks:
                task.update_status(0)  # 重置为排队状态
                retry_count += 1
        else:
            # 如果没有提供任务ID，重试所有失败的任务
            tasks = JimengImg2VideoTask.select().where(
                JimengImg2VideoTask.status == 3  # 只重试失败的任务
            )
            retry_count = 0
            for task in tasks:
                task.update_status(0)  # 重置为排队状态
                retry_count += 1
        
        print(f"批量重试图生视频任务: {retry_count}个")
        return jsonify({
            'success': True,
            'message': f'已重新加入队列 {retry_count} 个任务',
            'data': {
                'retry_count': retry_count
            }
        })
        
    except Exception as e:
        print(f"批量重试图生视频任务失败: {str(e)}")
        return jsonify({'success': False, 'message': f'批量重试失败: {str(e)}'}), 500

@jimeng_img2video_bp.route('/tasks/batch-delete', methods=['POST'])
def batch_delete_img2video_tasks():
    """批量删除图生视频任务"""
    try:
        data = request.get_json()
        task_ids = data.get('task_ids', [])

        if not task_ids:
            return jsonify({'success': False, 'message': '未提供任务ID'}), 400

        # 先查询要删除的任务，获取图片路径
        tasks_to_delete = JimengImg2VideoTask.select().where(
            JimengImg2VideoTask.id.in_(task_ids)
        )

        deleted_count = 0
        deleted_files_count = 0

        # 安全删除关联的图片文件（只删除缓存目录中的文件）
        for task in tasks_to_delete:
            try:
                if safe_remove_image_file(task.image_path):
                    deleted_files_count += 1
            except Exception as file_error:
                print(f"删除任务 {task.id} 的图片文件时出错: {str(file_error)}")

        # 删除任务记录
        deleted_count = JimengImg2VideoTask.delete().where(JimengImg2VideoTask.id.in_(task_ids)).execute()

        print(f"批量删除图生视频任务: {deleted_count}个，清理缓存文件: {deleted_files_count}个")
        return jsonify({
            'success': True,
            'message': f'成功删除 {deleted_count} 个任务，同时清理了 {deleted_files_count} 个缓存文件',
            'data': {
                'deleted_tasks': deleted_count,
                'deleted_files_count': deleted_files_count,
                'error_count': 0
            }
        })

    except Exception as e:
        print(f"批量删除图生视频任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@jimeng_img2video_bp.route('/tasks/import-folder', methods=['POST'])
def import_folder_tasks():
    """从文件夹导入图片任务"""
    try:
        # 获取请求数据
        data = request.get_json()
        model = data.get('model', 'Video 3.0')  # 默认为Video 3.0
        second = data.get('second', 5)  # 默认为5秒
        resolution = data.get('resolution', '1080p')  # 默认分辨率为1080p
        use_prompt = data.get('usePrompt', False)  # 是否使用提示词
        prompt = data.get('prompt', '')  # 提示词内容
        
        print(f"导入文件夹任务，模型: {model}, 时长: {second}秒, 使用提示词: {use_prompt}, 提示词: {prompt}")
        
        def select_folder_and_import():
            try:
                # 调用原生文件夹选择对话框
                folder_path = None
                system = platform.system()
                
                if system == "Darwin":  # macOS
                    result = subprocess.run([
                        'osascript', '-e',
                        'tell application "Finder" to set folder_path to (choose folder with prompt "选择包含图片的文件夹") as string',
                        '-e',
                        'return POSIX path of folder_path'
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0 and result.stdout.strip():
                        folder_path = result.stdout.strip()
                        
                elif system == "Windows":  # Windows
                    result = subprocess.run([
                        'powershell', '-Command',
                        'Add-Type -AssemblyName System.Windows.Forms; $folder = New-Object System.Windows.Forms.FolderBrowserDialog; $folder.Description = "选择包含图片的文件夹"; $folder.ShowNewFolderButton = $true; if ($folder.ShowDialog() -eq "OK") { $folder.SelectedPath } else { "" }'
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0 and result.stdout.strip():
                        folder_path = result.stdout.strip()
                        
                elif system == "Linux":  # Linux
                    result = subprocess.run([
                        'zenity', '--file-selection', '--directory',
                        '--title=选择包含图片的文件夹'
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0 and result.stdout.strip():
                        folder_path = result.stdout.strip()
                
                if not folder_path:
                    print("用户取消了文件夹选择")
                    return
                
                print(f"选择的文件夹: {folder_path}")
                
                # 扫描文件夹中的图片文件
                image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
                image_files = []
                
                for filename in os.listdir(folder_path):
                    file_ext = os.path.splitext(filename)[1].lower()
                    if file_ext in image_extensions:
                        image_files.append(os.path.join(folder_path, filename))
                
                print(f"找到 {len(image_files)} 张图片")
                
                # 创建任务
                created_count = 0
                for image_path in image_files:
                    try:
                        # 根据usePrompt参数决定是否使用提示词
                        task_prompt = prompt if use_prompt else ''
                        
                        task = JimengImg2VideoTask.create(
                            prompt=task_prompt,  # 根据usePrompt参数决定提示词
                            model=model,  # 使用传入的模型参数
                            second=second,  # 使用传入的时长参数
                            resolution=resolution,  # 使用传入的分辨率参数
                            image_path=image_path,
                            status=0
                        )
                        created_count += 1
                    except Exception as e:
                        print(f"创建任务失败 {image_path}: {str(e)}")
                
                print(f"成功创建 {created_count} 个图生视频任务，模型: {model}, 时长: {second}秒, 提示词: {task_prompt}")
                
            except Exception as e:
                print(f"文件夹导入失败: {str(e)}")
        
        # 在后台线程中执行文件夹选择和导入
        import_thread = threading.Thread(target=select_folder_and_import)
        import_thread.daemon = True
        import_thread.start()
        
        return jsonify({'success': True, 'message': '正在打开文件夹选择对话框，请选择包含图片的文件夹'})
        
    except Exception as e:
        print(f"导入文件夹失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@jimeng_img2video_bp.route('/tasks/batch-add', methods=['POST'])
def batch_add_tasks():
    """批量添加图生视频任务"""
    try:
        # 检查是否有图片文件
        if 'images' not in request.files:
            return jsonify({
                'success': False,
                'message': '请选择要上传的图片'
            }), 400

        files = request.files.getlist('images')
        if not files or all(file.filename == '' for file in files):
            return jsonify({
                'success': False,
                'message': '请选择要上传的图片'
            }), 400

        # 获取配置参数
        model = request.form.get('model', 'Video 3.0')
        second = int(request.form.get('second', 5))

        # 支持的图片格式
        ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
        
        def allowed_file(filename):
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

        # 创建临时目录保存上传的图片
        import uuid
        from werkzeug.utils import secure_filename
        
        tmp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tmp', 'batch_upload')
        os.makedirs(tmp_dir, exist_ok=True)

        created_tasks = []
        failed_files = []

        for i, file in enumerate(files):
            try:
                if file.filename == '':
                    continue

                if not allowed_file(file.filename):
                    failed_files.append(f"{file.filename}: 不支持的文件格式")
                    continue

                # 保存上传的图片
                filename = secure_filename(file.filename)
                file_ext = filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
                file_path = os.path.join(tmp_dir, unique_filename)
                file.save(file_path)

                # 获取对应的提示词
                prompt = request.form.get(f'prompts[{i}]', '')

                # 获取分辨率参数，默认为1080p
                resolution = request.form.get('resolution', '1080p')
                
                # 创建任务
                task = JimengImg2VideoTask.create(
                    prompt=prompt,
                    model=model,
                    second=second,
                    resolution=resolution,  # 添加分辨率参数
                    image_path=file_path,
                    status=0
                )
                created_tasks.append(task.id)
                print(f"创建图生视频任务: {task.id}, 图片: {filename}, 提示词: {prompt}")

            except Exception as e:
                failed_files.append(f"{file.filename}: {str(e)}")
                print(f"处理文件 {file.filename} 失败: {str(e)}")

        # 构建响应消息
        message_parts = []
        if created_tasks:
            message_parts.append(f"成功创建 {len(created_tasks)} 个任务")
        if failed_files:
            message_parts.append(f"失败 {len(failed_files)} 个文件")

        return jsonify({
            'success': True,
            'message': ', '.join(message_parts) if message_parts else '没有创建任何任务',
            'data': {
                'created_count': len(created_tasks),
                'failed_count': len(failed_files),
                'created_task_ids': created_tasks,
                'failed_files': failed_files
            }
        })

    except Exception as e:
        print(f"批量添加任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@jimeng_img2video_bp.route('/tasks/single-download', methods=['POST'])
def download_single_video():
    """单个视频下载"""
    try:
        data = request.get_json()
        video_url = data.get('video_url')
        filename = data.get('filename', 'video.mp4')

        if not video_url:
            return jsonify({
                'success': False,
                'message': '请提供视频URL'
            }), 400

        # 在后台线程中选择文件夹并下载
        def download_single_in_background():
            try:
                # 使用系统原生对话框选择文件夹
                download_dir = None
                system = platform.system()

                if system == "Darwin":  # macOS
                    try:
                        print("正在调用macOS文件选择器...")
                        applescript = '''
                        tell application "Finder"
                            activate
                            set selectedFolder to choose folder with prompt "选择视频保存位置" default location (path to downloads folder)
                            return POSIX path of selectedFolder
                        end tell
                        '''
                        result = subprocess.run([
                            'osascript', '-e', applescript
                        ], capture_output=True, text=True, timeout=60)

                        if result.returncode == 0 and result.stdout.strip():
                            download_dir = result.stdout.strip()
                            print(f"用户选择了文件夹: {download_dir}")
                        elif result.returncode == 1:
                            print("用户取消了文件夹选择")
                            return
                        else:
                            print(f"文件选择器异常退出，返回码: {result.returncode}")
                    except subprocess.TimeoutExpired:
                        print("文件选择器超时，用户可能没有响应")
                        return
                    except Exception as e:
                        print(f"macOS文件选择器失败: {str(e)}")

                elif system == "Windows":  # Windows
                    try:
                        print("正在调用Windows文件选择器...")
                        ps_script = """
                        try {
                            Add-Type -AssemblyName System.Windows.Forms
                            $folderBrowser = New-Object System.Windows.Forms.FolderBrowserDialog
                            $folderBrowser.Description = "选择视频保存位置"
                            $folderBrowser.SelectedPath = [Environment]::GetFolderPath("MyDocuments")
                            $folderBrowser.ShowNewFolderButton = $true
                            $result = $folderBrowser.ShowDialog()
                            if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
                                Write-Output $folderBrowser.SelectedPath
                                exit 0
                            } else {
                                Write-Output "CANCELLED"
                                exit 1
                            }
                        } catch {
                            Write-Error $_.Exception.Message
                            exit 2
                        }
                        """
                        result = subprocess.run([
                            'powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script
                        ], capture_output=True, text=True, timeout=60, encoding='utf-8')

                        if result.returncode == 0 and result.stdout.strip() and result.stdout.strip() != "CANCELLED":
                            download_dir = result.stdout.strip()
                            print(f"用户选择了文件夹: {download_dir}")
                        elif result.returncode == 1:
                            print("用户取消了文件夹选择")
                            return
                        else:
                            print(f"PowerShell执行失败，返回码: {result.returncode}")
                    except subprocess.TimeoutExpired:
                        print("Windows文件选择器超时，用户可能没有响应")
                        return
                    except Exception as e:
                        print(f"Windows文件选择器失败: {str(e)}")

                else:  # Linux
                    try:
                        result = subprocess.run([
                            'zenity', '--file-selection', '--directory',
                            '--title=选择视频保存位置'
                        ], capture_output=True, text=True, timeout=30)

                        if result.returncode == 0:
                            download_dir = result.stdout.strip()
                    except Exception as e:
                        print(f"Linux文件选择器失败: {str(e)}")

                # 如果原生对话框失败，使用默认下载目录
                if not download_dir:
                    download_dir = os.path.expanduser("~/Downloads")
                    print(f"文件选择器失败，使用默认下载目录: {download_dir}")

                # 确保目录存在
                if not os.path.exists(download_dir):
                    os.makedirs(download_dir, exist_ok=True)

                print(f"开始下载视频到: {download_dir}")

                # 准备下载信息
                file_path = os.path.join(download_dir, filename)

                # 使用下载工具下载视频
                from utils.download_util import download_single_file
                download_result = download_single_file(
                    url=video_url,
                    file_path=file_path,
                    max_retries=3,
                    timeout=60
                )

                if download_result['success']:
                    print(f"单个视频下载完成: {file_path}")
                else:
                    print(f"单个视频下载失败: {download_result.get('error', '未知错误')}")

            except Exception as e:
                print(f"单个视频下载过程出错: {str(e)}")

        # 在后台线程中执行下载
        download_thread = threading.Thread(target=download_single_in_background)
        download_thread.daemon = True
        download_thread.start()

        return jsonify({
            'success': True,
            'message': '开始下载视频，请选择下载文件夹',
            'data': {
                'filename': filename
            }
        })

    except Exception as e:
        print(f"单个视频下载失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'单个视频下载失败: {str(e)}'
        }), 500

@jimeng_img2video_bp.route('/tasks/batch-download', methods=['POST'])
def batch_download_videos():
    """批量下载任务视频"""
    try:
        data = request.get_json()
        task_ids = data.get('task_ids', [])
        
        if not task_ids:
            return jsonify({
                'success': False,
                'message': '请提供要下载的任务ID列表'
            }), 400
        
        # 获取任务信息
        tasks = list(JimengImg2VideoTask.select().where(
            JimengImg2VideoTask.id.in_(task_ids),
            JimengImg2VideoTask.status == 2  # 只下载已完成的任务
        ))
        
        if not tasks:
            return jsonify({
                'success': False,
                'message': '没有找到可下载的已完成任务'
            }), 400
        
        # 收集所有视频URL
        all_videos = []
        for task in tasks:
            if task.video_url:
                all_videos.append({
                    'task_id': task.id,
                    'url': task.video_url,
                    'filename': f'task_{task.id}_video.mp4'
                })
        
        if not all_videos:
            return jsonify({
                'success': False,
                'message': '选中的任务没有视频可下载'
            }), 400
        
        # 在后台线程中选择文件夹并下载
        def download_in_background():
            try:
                # 使用系统原生对话框选择文件夹
                download_dir = None
                system = platform.system()
                
                if system == "Darwin":  # macOS
                    try:
                        print("正在调用macOS文件选择器...")
                        # 使用osascript调用macOS原生文件选择器
                        applescript = '''
                        tell application "Finder"
                            activate
                            set selectedFolder to choose folder with prompt "选择视频下载文件夹" default location (path to downloads folder)
                            return POSIX path of selectedFolder
                        end tell
                        '''
                        result = subprocess.run([
                            'osascript', '-e', applescript
                        ], capture_output=True, text=True, timeout=60)
                        
                        print(f"文件选择器返回码: {result.returncode}")
                        print(f"文件选择器输出: {result.stdout}")
                        print(f"文件选择器错误: {result.stderr}")
                        
                        if result.returncode == 0 and result.stdout.strip():
                            download_dir = result.stdout.strip()
                            print(f"用户选择了文件夹: {download_dir}")
                        elif result.returncode == 1:
                            print("用户取消了文件夹选择")
                            return
                        else:
                            print(f"文件选择器异常退出，返回码: {result.returncode}")
                    except subprocess.TimeoutExpired:
                        print("文件选择器超时，用户可能没有响应")
                        return
                    except Exception as e:
                        print(f"macOS文件选择器失败: {str(e)}")
                        
                elif system == "Windows":  # Windows
                    try:
                        print("正在调用Windows文件选择器...")
                        # 使用PowerShell调用Windows文件选择器，添加更详细的错误处理
                        ps_script = """
                        try {
                            Add-Type -AssemblyName System.Windows.Forms
                            $folderBrowser = New-Object System.Windows.Forms.FolderBrowserDialog
                            $folderBrowser.Description = "选择视频下载文件夹"
                            $folderBrowser.SelectedPath = [Environment]::GetFolderPath("MyDocuments")
                            $folderBrowser.ShowNewFolderButton = $true
                            $result = $folderBrowser.ShowDialog()
                            if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
                                Write-Output $folderBrowser.SelectedPath
                                exit 0
                            } else {
                                Write-Output "CANCELLED"
                                exit 1
                            }
                        } catch {
                            Write-Error $_.Exception.Message
                            exit 2
                        }
                        """
                        result = subprocess.run([
                            'powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script
                        ], capture_output=True, text=True, timeout=60, encoding='utf-8')
                        
                        print(f"PowerShell返回码: {result.returncode}")
                        print(f"PowerShell输出: {result.stdout}")
                        print(f"PowerShell错误: {result.stderr}")
                        
                        if result.returncode == 0 and result.stdout.strip() and result.stdout.strip() != "CANCELLED":
                            download_dir = result.stdout.strip()
                            print(f"用户选择了文件夹: {download_dir}")
                        elif result.returncode == 1:
                            print("用户取消了文件夹选择")
                            return
                        else:
                            print(f"PowerShell执行失败，返回码: {result.returncode}")
                    except subprocess.TimeoutExpired:
                        print("Windows文件选择器超时，用户可能没有响应")
                        return
                    except Exception as e:
                        print(f"Windows文件选择器失败: {str(e)}")
                        
                else:  # Linux
                    try:
                        # 尝试使用zenity
                        result = subprocess.run([
                            'zenity', '--file-selection', '--directory', 
                            '--title=选择视频下载文件夹'
                        ], capture_output=True, text=True, timeout=30)
                        
                        if result.returncode == 0:
                            download_dir = result.stdout.strip()
                    except Exception as e:
                        print(f"Linux文件选择器失败: {str(e)}")
                
                # 如果原生对话框失败，使用默认下载目录
                if not download_dir:
                    download_dir = os.path.expanduser("~/Downloads")
                    print(f"文件选择器失败，使用默认下载目录: {download_dir}")
                
                # 确保目录存在
                if not os.path.exists(download_dir):
                    os.makedirs(download_dir, exist_ok=True)
                
                print(f"开始下载 {len(all_videos)} 个视频到: {download_dir}")
                
                # 创建以当前时间命名的子文件夹
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                batch_folder = os.path.join(download_dir, f"jimeng_videos_{timestamp}")
                os.makedirs(batch_folder, exist_ok=True)
                
                # 准备下载信息
                file_infos = []
                for video_info in all_videos:
                    file_infos.append({
                        'url': video_info['url'],
                        'file_path': os.path.join(batch_folder, video_info['filename']),
                        'filename': video_info['filename']
                    })
                
                # 使用带重试机制的批量下载（支持并行）
                from utils.download_util import batch_download_files
                download_result = batch_download_files(
                    file_infos=file_infos,
                    max_retries=5,
                    timeout=60,
                    max_workers=5  # 并行下载数
                )
                
                success_count = download_result['success_count']
                error_count = download_result['failed_count']
                
                print(f"批量下载完成: 成功 {success_count} 个，失败 {error_count} 个")
                print(f"文件保存位置: {batch_folder}")
                
            except Exception as e:
                print(f"批量下载过程出错: {str(e)}")
        
        # 在后台线程中执行下载
        download_thread = threading.Thread(target=download_in_background)
        download_thread.daemon = True
        download_thread.start()
        
        return jsonify({
            'success': True,
            'message': f'开始下载 {len(all_videos)} 个视频，请选择下载文件夹',
            'data': {
                'total_videos': len(all_videos),
                'tasks_count': len(tasks)
            }
        })
        
    except Exception as e:
        print(f"批量下载失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'批量下载失败: {str(e)}'
        }), 500

@jimeng_img2video_bp.route('/stats', methods=['GET'])
def get_img2video_stats():
    """获取图生视频统计信息"""
    try:
        # 统计时过滤掉空任务
        base_query = JimengImg2VideoTask.select()
        total_tasks = base_query.count()
        pending_tasks = base_query.where(JimengImg2VideoTask.status == 0).count()
        processing_tasks = base_query.where(JimengImg2VideoTask.status == 1).count()
        completed_tasks = base_query.where(JimengImg2VideoTask.status == 2).count()
        failed_tasks = base_query.where(JimengImg2VideoTask.status == 3).count()
        
        return jsonify({
            'success': True,
            'data': {
                'total_tasks': total_tasks,
                'pending_tasks': pending_tasks,
                'processing_tasks': processing_tasks,
                'completed_tasks': completed_tasks,
                'failed_tasks': failed_tasks
            }
        })
        
    except Exception as e:
        print(f"获取图生视频统计失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500 

@jimeng_img2video_bp.route('/tasks/delete-before-today', methods=['DELETE'])
def delete_tasks_before_today():
    """删除今日前的所有图生视频任务"""
    try:
        from datetime import datetime, timedelta
        import pytz

        # 获取今日开始时间（凌晨0点）
        beijing_tz = pytz.timezone('Asia/Shanghai')
        today_start = datetime.now(beijing_tz).replace(hour=0, minute=0, second=0, microsecond=0)

        # 查询今日前的任务
        before_today_tasks = JimengImg2VideoTask.select().where(
            JimengImg2VideoTask.create_at < today_start
        )

        count = before_today_tasks.count()

        if count == 0:
            return jsonify({
                'success': True,
                'message': '没有今日前的任务需要删除',
                'data': {'deleted_count': 0, 'deleted_files_count': 0}
            })

        # 安全删除关联的图片文件（只删除缓存目录中的文件）
        deleted_files_count = 0
        for task in before_today_tasks:
            try:
                if safe_remove_image_file(task.image_path):
                    deleted_files_count += 1
            except Exception as file_error:
                print(f"删除任务 {task.id} 的图片文件时出错: {str(file_error)}")

        # 删除任务记录
        deleted_count = JimengImg2VideoTask.delete().where(
            JimengImg2VideoTask.create_at < today_start
        ).execute()

        print(f"删除了 {deleted_count} 个今日前的图生视频任务，清理缓存文件: {deleted_files_count}个")

        return jsonify({
            'success': True,
            'message': f'成功删除 {deleted_count} 个今日前的任务，同时清理了 {deleted_files_count} 个缓存文件',
            'data': {
                'deleted_count': deleted_count,
                'deleted_files_count': deleted_files_count
            }
        })

    except Exception as e:
        print(f"删除今日前任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'删除今日前任务失败: {str(e)}'
        }), 500 

@jimeng_img2video_bp.route('/tasks/batch-create-from-table', methods=['POST'])
def batch_create_tasks_from_table():
    """从表格批量创建图生视频任务"""
    try:
        data = request.get_json()
        if not data or 'tasks' not in data:
            return jsonify({
                'success': False,
                'message': '请提供任务数据'
            }), 400

        tasks_data = data['tasks']
        if not tasks_data or not isinstance(tasks_data, list):
            return jsonify({
                'success': False,
                'message': '任务数据格式错误'
            }), 400

        created_tasks = []
        failed_tasks = []

        for i, task_data in enumerate(tasks_data):
            try:
                # 验证必需字段
                if 'image_path' not in task_data or not task_data['image_path']:
                    failed_tasks.append(f"第 {i+1} 行: 缺少图片路径")
                    continue

                image_path = task_data['image_path'].strip()
                prompt = task_data.get('prompt', '').strip()
                model = task_data.get('model', 'Video 3.0')
                second = int(task_data.get('second', 5))
                resolution = task_data.get('resolution', '1080p')  # 默认分辨率为1080p

                # 验证图片路径是否存在
                if not os.path.exists(image_path):
                    failed_tasks.append(f"第 {i+1} 行: 图片文件不存在 - {image_path}")
                    continue

                # 创建任务
                task = JimengImg2VideoTask.create(
                    prompt=prompt,
                    model=model,
                    second=second,
                    resolution=resolution,  # 添加分辨率参数
                    image_path=image_path,
                    status=0
                )
                created_tasks.append(task.id)
                print(f"从表格创建图生视频任务: {task.id}, 图片: {image_path}, 提示词: {prompt}, 模型: {model}, 时长: {second}s")

            except Exception as e:
                failed_tasks.append(f"第 {i+1} 行: {str(e)}")
                print(f"处理第 {i+1} 行任务失败: {str(e)}")

        # 返回结果
        result_message = f"成功创建 {len(created_tasks)} 个任务"
        if failed_tasks:
            result_message += f"，{len(failed_tasks)} 个任务创建失败"

        return jsonify({
            'success': True,
            'message': result_message,
            'data': {
                'created_count': len(created_tasks),
                'failed_count': len(failed_tasks),
                'created_task_ids': created_tasks,
                'failed_tasks': failed_tasks
            }
        })

    except Exception as e:
        print(f"表格批量创建任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'表格批量创建任务失败: {str(e)}'
        }), 500

@jimeng_img2video_bp.route('/cleanup-orphaned-images', methods=['DELETE'])
def cleanup_orphaned_img2video_images():
    """清理孤立的图生视频图片文件（没有关联任务的图片）"""
    try:
        # 获取项目中所有存储的图片路径
        all_tasks = JimengImg2VideoTask.select()
        used_image_paths = set()

        for task in all_tasks:
            if task.image_path:
                used_image_paths.add(task.image_path)

        # 获取项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        # 检查上传目录
        tmp_dir = os.path.join(project_root, 'tmp')
        batch_upload_dir = os.path.join(tmp_dir, 'batch_upload')
        deleted_files_count = 0
        error_count = 0

        # 检查tmp目录
        if os.path.exists(tmp_dir):
            for filename in os.listdir(tmp_dir):
                file_path = os.path.join(tmp_dir, filename)
                if os.path.isfile(file_path):
                    # 检查文件是否为图片文件
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                        # 检查文件是否被任何任务使用
                        if file_path not in used_image_paths:
                            try:
                                os.remove(file_path)
                                deleted_files_count += 1
                                print(f"删除孤立图片文件: {file_path}")
                            except Exception as e:
                                error_count += 1
                                print(f"删除孤立图片文件失败: {file_path}, 错误: {str(e)}")

        # 检查batch_upload目录
        if os.path.exists(batch_upload_dir):
            for filename in os.listdir(batch_upload_dir):
                file_path = os.path.join(batch_upload_dir, filename)
                if os.path.isfile(file_path):
                    # 检查文件是否为图片文件
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
                        # 检查文件是否被任何任务使用
                        if file_path not in used_image_paths:
                            try:
                                os.remove(file_path)
                                deleted_files_count += 1
                                print(f"删除孤立图片文件: {file_path}")
                            except Exception as e:
                                error_count += 1
                                print(f"删除孤立图片文件失败: {file_path}, 错误: {str(e)}")

        print(f"清理图生视频孤立图片完成: 删除 {deleted_files_count} 个文件，失败 {error_count} 个")

        return jsonify({
            'success': True,
            'message': f'清理完成，删除了 {deleted_files_count} 个孤立图片文件',
            'data': {
                'deleted_count': deleted_files_count,
                'error_count': error_count,
                'total_used_files': len(used_image_paths)
            }
        })

    except Exception as e:
        print(f"清理孤立图片失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'清理孤立图片失败: {str(e)}'
        }), 500 