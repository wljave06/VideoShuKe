# -*- coding: utf-8 -*-
"""
即梦首尾帧图生视频API路由
"""

import os
import json
import requests
import asyncio
import pandas as pd
from datetime import datetime
from flask import Blueprint, request, jsonify
from backend.models.models import JimengFirstLastFrameImg2VideoTask
import subprocess
import platform
import threading
from urllib.parse import urlparse

def clean_image_path(image_path):
    """清理和标准化图片路径"""
    if not image_path:
        return ''

    # 去除首尾空白字符
    cleaned_path = str(image_path).strip()

    # 去除首尾的引号（单引号或双引号）
    if (cleaned_path.startswith('"') and cleaned_path.endswith('"')) or \
       (cleaned_path.startswith("'") and cleaned_path.endswith("'")):
        cleaned_path = cleaned_path[1:-1]
        cleaned_path = cleaned_path.strip()

    # 处理Unicode引号
    if (cleaned_path.startswith('"') and cleaned_path.endswith('"')) or \
       (cleaned_path.startswith('"') and cleaned_path.endswith('"')):
        cleaned_path = cleaned_path[1:-1]
        cleaned_path = cleaned_path.strip()

    # 替换正斜杠为反斜杠（在Windows上）
    if platform.system() == "Windows":
        cleaned_path = cleaned_path.replace('/', '\\')

    # 处理转义的反斜杠
    cleaned_path = cleaned_path.replace('\\\\', '\\')

    return cleaned_path

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
            os.path.join(project_root, 'tmp', 'first_last_frame_upload'),
            os.path.join(project_root, 'tmp', 'batch_upload'),
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
jimeng_first_last_frame_img2video_bp = Blueprint('jimeng_first_last_frame_img2video', __name__, url_prefix='/api/jimeng/first-last-frame-img2video')

@jimeng_first_last_frame_img2video_bp.route('/tasks', methods=['GET'])
def get_first_last_frame_img2video_tasks():
    """获取首尾帧图生视频任务列表"""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 1000))
        status = request.args.get('status', None)

        print("获取首尾帧图生视频任务列表，页码: {}, 每页数量: {}, 状态: {}".format(page, page_size, status))

        # 构建查询
        query = JimengFirstLastFrameImg2VideoTask.select()
        if status is not None:
            query = query.where(JimengFirstLastFrameImg2VideoTask.status == status)

        # 分页
        total = query.count()
        tasks = query.order_by(JimengFirstLastFrameImg2VideoTask.create_at.desc()).paginate(page, page_size)

        data = []
        for task in tasks:
            data.append({
                'id': task.id,
                'prompt': task.prompt,
                'model': task.model,
                'second': task.second,
                'resolution': task.resolution,
                'status': task.status,
                'status_text': task.get_status_text(),
                'account_id': task.account_id,
                'first_frame_image_path': task.first_frame_image_path,
                'last_frame_image_path': task.last_frame_image_path,
                'video_url': task.video_url,
                'failure_reason': task.failure_reason,
                'error_message': task.error_message,
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
        print(f"获取首尾帧图生视频任务列表失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@jimeng_first_last_frame_img2video_bp.route('/tasks', methods=['POST'])
def create_first_last_frame_img2video_task():
    """创建首尾帧图生视频任务"""
    try:
        # 检查是否有图片文件
        if 'first_image' not in request.files or 'last_image' not in request.files:
            return jsonify({
                'success': False,
                'message': '请上传首帧和尾帧图片'
            }), 400

        first_image = request.files['first_image']
        last_image = request.files['last_image']

        if first_image.filename == '' or last_image.filename == '':
            return jsonify({
                'success': False,
                'message': '请上传首帧和尾帧图片'
            }), 400

        # 获取配置参数
        model = request.form.get('model', 'Video 3.0')
        second = int(request.form.get('second', 5))
        resolution = request.form.get('resolution', '1080p')
        prompt = request.form.get('prompt', '')

        # 支持的图片格式
        ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

        def allowed_file(filename):
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

        if not allowed_file(first_image.filename) or not allowed_file(last_image.filename):
            return jsonify({
                'success': False,
                'message': '不支持的文件格式，请上传图片文件'
            }), 400

        # 创建临时目录保存上传的图片
        import uuid
        from werkzeug.utils import secure_filename

        tmp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tmp', 'first_last_frame_upload')
        os.makedirs(tmp_dir, exist_ok=True)

        # 保存首帧图片
        first_filename = secure_filename(first_image.filename)
        first_file_ext = first_filename.rsplit('.', 1)[1].lower()
        first_unique_filename = f"{uuid.uuid4().hex}_first.{first_file_ext}"
        first_file_path = os.path.join(tmp_dir, first_unique_filename)
        first_image.save(first_file_path)

        # 保存尾帧图片
        last_filename = secure_filename(last_image.filename)
        last_file_ext = last_filename.rsplit('.', 1)[1].lower()
        last_unique_filename = f"{uuid.uuid4().hex}_last.{last_file_ext}"
        last_file_path = os.path.join(tmp_dir, last_unique_filename)
        last_image.save(last_file_path)

        # 创建任务
        task = JimengFirstLastFrameImg2VideoTask.create(
            prompt=prompt,
            model=model,
            second=second,
            resolution=resolution,
            first_frame_image_path=first_file_path,
            last_frame_image_path=last_file_path,
            status=0
        )

        print(f"创建首尾帧图生视频任务: {task.id}, 首帧: {first_filename}, 尾帧: {last_filename}")

        return jsonify({
            'success': True,
            'message': '任务创建成功',
            'data': {'task_id': task.id}
        })

    except Exception as e:
        print(f"创建首尾帧图生视频任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@jimeng_first_last_frame_img2video_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_first_last_frame_img2video_task(task_id):
    """删除首尾帧图生视频任务"""
    try:
        task = JimengFirstLastFrameImg2VideoTask.get_by_id(task_id)

        # 安全删除关联的图片文件（只删除缓存目录中的文件）
        deleted_files_count = 0
        try:
            # 删除首帧图片
            if safe_remove_image_file(task.first_frame_image_path):
                deleted_files_count += 1

            # 删除尾帧图片
            if safe_remove_image_file(task.last_frame_image_path):
                deleted_files_count += 1

        except Exception as file_error:
            print(f"删除图片文件时出错（但任务仍会被删除）: {str(file_error)}")

        # 删除任务记录
        task.delete_instance()

        print(f"删除首尾帧图生视频任务: {task_id}，清理了 {deleted_files_count} 个缓存文件")
        return jsonify({
            'success': True,
            'message': f'任务删除成功，清理了 {deleted_files_count} 个缓存文件'
        })

    except JimengFirstLastFrameImg2VideoTask.DoesNotExist:
        return jsonify({'success': False, 'message': '任务不存在'}), 404
    except Exception as e:
        print(f"删除首尾帧图生视频任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@jimeng_first_last_frame_img2video_bp.route('/tasks/<int:task_id>/retry', methods=['POST'])
def retry_first_last_frame_img2video_task(task_id):
    """重试首尾帧图生视频任务"""
    try:
        task = JimengFirstLastFrameImg2VideoTask.get_by_id(task_id)
        task.update_status(0)  # 重置为排队状态

        print(f"重试首尾帧图生视频任务: {task_id}")
        return jsonify({'success': True, 'message': '任务已重新加入队列'})

    except JimengFirstLastFrameImg2VideoTask.DoesNotExist:
        return jsonify({'success': False, 'message': '任务不存在'}), 404
    except Exception as e:
        print(f"重试首尾帧图生视频任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@jimeng_first_last_frame_img2video_bp.route('/tasks/batch-retry', methods=['POST'])
def batch_retry_first_last_frame_img2video_tasks():
    """批量重试失败的首尾帧图生视频任务"""
    try:
        data = request.get_json()
        task_ids = data.get('task_ids', [])

        if task_ids:
            # 如果提供了特定的任务ID列表，只重试这些任务
            tasks = JimengFirstLastFrameImg2VideoTask.select().where(
                JimengFirstLastFrameImg2VideoTask.id.in_(task_ids),
                JimengFirstLastFrameImg2VideoTask.status == 3  # 只重试失败的任务
            )
            retry_count = 0
            for task in tasks:
                task.update_status(0)  # 重置为排队状态
                retry_count += 1
        else:
            # 如果没有提供任务ID，重试所有失败的任务
            tasks = JimengFirstLastFrameImg2VideoTask.select().where(
                JimengFirstLastFrameImg2VideoTask.status == 3  # 只重试失败的任务
            )
            retry_count = 0
            for task in tasks:
                task.update_status(0)  # 重置为排队状态
                retry_count += 1

        print(f"批量重试首尾帧图生视频任务: {retry_count}个")
        return jsonify({
            'success': True,
            'message': f'已重新加入队列 {retry_count} 个任务',
            'data': {
                'retry_count': retry_count
            }
        })

    except Exception as e:
        print(f"批量重试首尾帧图生视频任务失败: {str(e)}")
        return jsonify({'success': False, 'message': f'批量重试失败: {str(e)}'}), 500

@jimeng_first_last_frame_img2video_bp.route('/tasks/batch-delete', methods=['POST'])
def batch_delete_first_last_frame_img2video_tasks():
    """批量删除首尾帧图生视频任务"""
    try:
        data = request.get_json()
        task_ids = data.get('task_ids', [])

        if not task_ids:
            return jsonify({'success': False, 'message': '未提供任务ID'}), 400

        # 先查询要删除的任务，获取图片路径
        tasks_to_delete = JimengFirstLastFrameImg2VideoTask.select().where(
            JimengFirstLastFrameImg2VideoTask.id.in_(task_ids)
        )

        deleted_count = 0
        deleted_files_count = 0

        # 安全删除关联的图片文件（只删除缓存目录中的文件）
        for task in tasks_to_delete:
            try:
                # 删除首帧图片
                if safe_remove_image_file(task.first_frame_image_path):
                    deleted_files_count += 1

                # 删除尾帧图片
                if safe_remove_image_file(task.last_frame_image_path):
                    deleted_files_count += 1

            except Exception as file_error:
                print(f"删除任务 {task.id} 的图片文件时出错: {str(file_error)}")

        # 删除任务记录
        deleted_count = JimengFirstLastFrameImg2VideoTask.delete().where(JimengFirstLastFrameImg2VideoTask.id.in_(task_ids)).execute()

        print(f"批量删除首尾帧图生视频任务: {deleted_count}个，清理缓存文件: {deleted_files_count}个")
        return jsonify({
            'success': True,
            'message': f'成功删除 {deleted_count} 个任务，同时清理了 {deleted_files_count} 个缓存文件'
        })

    except Exception as e:
        print(f"批量删除首尾帧图生视频任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@jimeng_first_last_frame_img2video_bp.route('/tasks/single-download', methods=['POST'])
def download_single_first_last_frame_video():
    """单个首尾帧视频下载"""
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
                    print(f"单个首尾帧视频下载完成: {file_path}")
                else:
                    print(f"单个首尾帧视频下载失败: {download_result.get('error', '未知错误')}")

            except Exception as e:
                print(f"单个首尾帧视频下载过程出错: {str(e)}")

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
        print(f"单个首尾帧视频下载失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'单个首尾帧视频下载失败: {str(e)}'
        }), 500

@jimeng_first_last_frame_img2video_bp.route('/tasks/batch-download', methods=['POST'])
def batch_download_first_last_frame_videos():
    """批量下载首尾帧任务视频"""
    try:
        data = request.get_json()
        task_ids = data.get('task_ids', [])

        if not task_ids:
            return jsonify({
                'success': False,
                'message': '请提供要下载的任务ID列表'
            }), 400

        # 获取任务信息
        tasks = list(JimengFirstLastFrameImg2VideoTask.select().where(
            JimengFirstLastFrameImg2VideoTask.id.in_(task_ids),
            JimengFirstLastFrameImg2VideoTask.status == 2  # 只下载已完成的任务
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
                    'filename': f'task_{task.id}_first_last_frame_video.mp4'
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

                        if result.returncode == 0 and result.stdout.strip():
                            download_dir = result.stdout.strip()
                            print(f"用户选择了文件夹: {download_dir}")
                    except Exception as e:
                        print(f"macOS文件选择器失败: {str(e)}")

                elif system == "Windows":  # Windows
                    try:
                        print("正在调用Windows文件选择器...")
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

                        if result.returncode == 0 and result.stdout.strip() and result.stdout.strip() != "CANCELLED":
                            download_dir = result.stdout.strip()
                            print(f"用户选择了文件夹: {download_dir}")
                    except Exception as e:
                        print(f"Windows文件选择器失败: {str(e)}")

                else:  # Linux
                    try:
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
                batch_folder = os.path.join(download_dir, f"jimeng_first_last_frame_videos_{timestamp}")
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

@jimeng_first_last_frame_img2video_bp.route('/stats', methods=['GET'])
def get_first_last_frame_img2video_stats():
    """获取首尾帧图生视频统计信息"""
    try:
        base_query = JimengFirstLastFrameImg2VideoTask.select()
        total_tasks = base_query.count()
        pending_tasks = base_query.where(JimengFirstLastFrameImg2VideoTask.status == 0).count()
        processing_tasks = base_query.where(JimengFirstLastFrameImg2VideoTask.status == 1).count()
        completed_tasks = base_query.where(JimengFirstLastFrameImg2VideoTask.status == 2).count()
        failed_tasks = base_query.where(JimengFirstLastFrameImg2VideoTask.status == 3).count()

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
        print(f"获取首尾帧图生视频统计失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@jimeng_first_last_frame_img2video_bp.route('/tasks/delete-before-today', methods=['DELETE'])
def delete_first_last_frame_tasks_before_today():
    """删除今日前的所有首尾帧图生视频任务"""
    try:
        from datetime import datetime, timedelta
        import pytz

        # 获取今日开始时间（凌晨0点）
        beijing_tz = pytz.timezone('Asia/Shanghai')
        today_start = datetime.now(beijing_tz).replace(hour=0, minute=0, second=0, microsecond=0)

        # 查询今日前的任务
        before_today_tasks = JimengFirstLastFrameImg2VideoTask.select().where(
            JimengFirstLastFrameImg2VideoTask.create_at < today_start
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
                # 删除首帧图片
                if safe_remove_image_file(task.first_frame_image_path):
                    deleted_files_count += 1

                # 删除尾帧图片
                if safe_remove_image_file(task.last_frame_image_path):
                    deleted_files_count += 1

            except Exception as file_error:
                print(f"删除任务 {task.id} 的图片文件时出错: {str(file_error)}")

        # 删除任务
        deleted_count = JimengFirstLastFrameImg2VideoTask.delete().where(
            JimengFirstLastFrameImg2VideoTask.create_at < today_start
        ).execute()

        print(f"删除了 {deleted_count} 个今日前的首尾帧图生视频任务，清理缓存文件: {deleted_files_count}个")

        return jsonify({
            'success': True,
            'message': f'成功删除 {deleted_count} 个今日前的任务，同时清理了 {deleted_files_count} 个缓存文件',
            'data': {'deleted_count': deleted_count, 'deleted_files_count': deleted_files_count}
        })

    except Exception as e:
        print(f"删除今日前任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'删除今日前任务失败: {str(e)}'
        }), 500

@jimeng_first_last_frame_img2video_bp.route('/cleanup-orphaned-images', methods=['DELETE'])
def cleanup_orphaned_images():
    """清理孤立的首尾帧图片文件（没有关联任务的图片）"""
    try:
        # 获取项目中所有存储的图片路径
        all_tasks = JimengFirstLastFrameImg2VideoTask.select()
        used_image_paths = set()

        for task in all_tasks:
            if task.first_frame_image_path:
                used_image_paths.add(task.first_frame_image_path)
            if task.last_frame_image_path:
                used_image_paths.add(task.last_frame_image_path)

        # 获取项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        # 检查缓存目录
        cache_directories = [
            os.path.join(project_root, 'tmp', 'first_last_frame_upload'),
            os.path.join(project_root, 'tmp', 'batch_upload'),
        ]

        deleted_files_count = 0
        error_count = 0
        skipped_files_count = 0

        for cache_dir in cache_directories:
            if os.path.exists(cache_dir):
                for filename in os.listdir(cache_dir):
                    file_path = os.path.join(cache_dir, filename)
                    if os.path.isfile(file_path):
                        # 检查文件是否被任何任务使用
                        if file_path not in used_image_paths:
                            try:
                                os.remove(file_path)
                                deleted_files_count += 1
                                print(f"删除孤立缓存图片文件: {file_path}")
                            except Exception as e:
                                error_count += 1
                                print(f"删除孤立缓存图片文件失败: {file_path}, 错误: {str(e)}")
                        else:
                            skipped_files_count += 1

        print(f"清理孤立缓存图片完成: 删除 {deleted_files_count} 个文件，失败 {error_count} 个，跳过 {skipped_files_count} 个使用中的文件")

        return jsonify({
            'success': True,
            'message': f'清理完成，删除了 {deleted_files_count} 个孤立缓存图片文件',
            'data': {
                'deleted_count': deleted_files_count,
                'error_count': error_count,
                'skipped_count': skipped_files_count,
                'total_used_files': len(used_image_paths)
            }
        })

    except Exception as e:
        print(f"清理孤立图片失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'清理孤立图片失败: {str(e)}'
        }), 500

@jimeng_first_last_frame_img2video_bp.route('/get-local-file', methods=['POST'])
def get_local_file():
    """获取本地文件的base64编码，用于前端预览"""
    try:
        data = request.get_json()
        if not data or 'path' not in data:
            return jsonify({
                'success': False,
                'message': '请提供文件路径'
            }), 400

        file_path = data['path']
        if not file_path:
            return jsonify({
                'success': False,
                'message': '文件路径不能为空'
            }), 400

        # 清理文件路径
        file_path = clean_image_path(file_path)

        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            return jsonify({
                'success': False,
                'message': f'文件不存在: {file_path}'
            }), 404

        # 检查是否为图片文件
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({
                'success': False,
                'message': '不支持的文件格式'
            }), 400

        # 读取文件并转换为base64
        try:
            import base64
            with open(file_path, 'rb') as f:
                file_data = f.read()
                base64_data = base64.b64encode(file_data).decode('utf-8')

                # 根据文件类型设置MIME类型
                mime_type = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.bmp': 'image/bmp',
                    '.webp': 'image/webp'
                }.get(file_ext, 'image/jpeg')

                # 构建data URL
                data_url = f"data:{mime_type};base64,{base64_data}"

                print(f"成功读取本地文件: {file_path} ({len(file_data)} bytes)")

                return jsonify({
                    'success': True,
                    'data': data_url,
                    'message': '文件读取成功'
                })

        except Exception as e:
            print(f"读取文件失败: {file_path}, 错误: {str(e)}")
            return jsonify({
                'success': False,
                'message': '读取文件失败'
            }), 500

    except Exception as e:
        print(f"获取本地文件API失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': '服务器内部错误'
        }), 500

@jimeng_first_last_frame_img2video_bp.route('/tasks/batch-create-from-table', methods=['POST'])
def batch_create_first_last_frame_tasks_from_table():
    """从表格批量创建首尾帧图生视频任务"""
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
                if 'first_image_path' not in task_data or not task_data['first_image_path']:
                    failed_tasks.append(f"第 {i+1} 行: 缺少首帧图片路径")
                    continue

                if 'last_image_path' not in task_data or not task_data['last_image_path']:
                    failed_tasks.append(f"第 {i+1} 行: 缺少尾帧图片路径")
                    continue

                # 清理图片路径
                original_first_path = task_data['first_image_path']
                original_last_path = task_data['last_image_path']
                first_image_path = clean_image_path(task_data['first_image_path'])
                last_image_path = clean_image_path(task_data['last_image_path'])

                # 调试日志
                print(f"第 {i+1} 行路径处理:")
                print(f"  原始首帧路径: {original_first_path}")
                print(f"  清理后首帧路径: {first_image_path}")
                print(f"  原始尾帧路径: {original_last_path}")
                print(f"  清理后尾帧路径: {last_image_path}")
                print(f"  首帧文件存在: {os.path.exists(first_image_path)}")
                print(f"  尾帧文件存在: {os.path.exists(last_image_path)}")

                prompt = task_data.get('prompt', '').strip()
                model = task_data.get('model', 'Video 3.0')
                second = int(task_data.get('second', 5))
                resolution = task_data.get('resolution', '1080p')

                # 验证图片路径是否存在
                if not os.path.exists(first_image_path):
                    failed_tasks.append(f"第 {i+1} 行: 首帧图片文件不存在 - {first_image_path}")
                    continue

                if not os.path.exists(last_image_path):
                    failed_tasks.append(f"第 {i+1} 行: 尾帧图片文件不存在 - {last_image_path}")
                    continue

                # 创建任务
                task = JimengFirstLastFrameImg2VideoTask.create(
                    prompt=prompt,
                    model=model,
                    second=second,
                    resolution=resolution,
                    first_frame_image_path=first_image_path,
                    last_frame_image_path=last_image_path,
                    status=0
                )
                created_tasks.append(task.id)
                print(f"从表格创建首尾帧图生视频任务: {task.id}, 首帧: {first_image_path}, 尾帧: {last_image_path}, 提示词: {prompt}, 模型: {model}, 时长: {second}s")

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
        print(f"表格批量创建首尾帧任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'表格批量创建任务失败: {str(e)}'
        }), 500
