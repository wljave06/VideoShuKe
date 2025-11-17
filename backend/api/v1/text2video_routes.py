# -*- coding: utf-8 -*-
"""
即梦文生视频API路由
"""

import os
import json
import requests
import asyncio
from datetime import datetime
from flask import Blueprint, request, jsonify
from backend.models.models import JimengText2VideoTask
import subprocess
import platform
import threading
from urllib.parse import urlparse

# 创建蓝图
jimeng_text2video_bp = Blueprint('jimeng_text2video', __name__, url_prefix='/api/jimeng/text2video')

@jimeng_text2video_bp.route('/tasks', methods=['GET'])
def get_text2video_tasks():
    """获取文生视频任务列表"""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 1000))
        status = request.args.get('status', None)
        
        print("获取文生视频任务列表，页码: {}, 每页数量: {}, 状态: {}".format(page, page_size, status))
        
        # 构建查询
        query = JimengText2VideoTask.select()
        if status is not None:
            query = query.where(JimengText2VideoTask.status == status)
        
        # 分页
        total = query.count()
        tasks = query.order_by(JimengText2VideoTask.create_at.desc()).paginate(page, page_size)
        
        data = []
        for task in tasks:
            data.append({
                'id': task.id,
                'prompt': task.prompt,
                'model': task.model,
                'second': task.second,
                'resolution': task.resolution,  # 分辨率字段
                'ratio': task.ratio,  # 视频比例
                'status': task.status,
                'status_text': task.get_status_text(),
                'account_id': task.account_id,
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
        print(f"获取文生视频任务列表失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@jimeng_text2video_bp.route('/tasks', methods=['POST'])
def create_text2video_task():
    """创建文生视频任务"""
    try:
        data = request.get_json()
        
        # 单个任务创建
        if 'prompt' in data and 'model' in data:
            task = JimengText2VideoTask.create(
                prompt=data['prompt'],
                model=data.get('model', 'Video 3.0'),
                second=data.get('second', 5),
                resolution=data.get('resolution', '720p'),  # 分辨率参数
                ratio=data.get('ratio', '1:1'),  # 视频比例参数
                status=0
            )
            
            print(f"创建文生视频任务: {task.id}")
            return jsonify({'success': True, 'data': {'task_id': task.id}})
        
        # 批量任务创建
        elif 'tasks' in data:
            tasks = data['tasks']
            created_tasks = []
            
            for task_data in tasks:
                task = JimengText2VideoTask.create(
                    prompt=task_data.get('prompt', ''),
                    model=task_data.get('model', 'Video 3.0'),
                    second=task_data.get('second', 5),
                    resolution=task_data.get('resolution', '720p'),  # 分辨率参数
                    ratio=task_data.get('ratio', '1:1'),  # 视频比例参数
                    status=0
                )
                created_tasks.append(task.id)
            
            print(f"批量创建文生视频任务: {len(created_tasks)}个")
            return jsonify({'success': True, 'data': {'task_ids': created_tasks}})
        
        else:
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400
            
    except Exception as e:
        print(f"创建文生视频任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@jimeng_text2video_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_text2video_task(task_id):
    """删除文生视频任务"""
    try:
        task = JimengText2VideoTask.get_by_id(task_id)
        task.delete_instance()
        
        print(f"删除文生视频任务: {task_id}")
        return jsonify({'success': True, 'message': '任务删除成功'})
        
    except JimengText2VideoTask.DoesNotExist:
        return jsonify({'success': False, 'message': '任务不存在'}), 404
    except Exception as e:
        print(f"删除文生视频任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@jimeng_text2video_bp.route('/tasks/<int:task_id>/retry', methods=['POST'])
def retry_text2video_task(task_id):
    """重试文生视频任务"""
    try:
        task = JimengText2VideoTask.get_by_id(task_id)
        task.update_status(0)  # 重置为排队状态
        
        print(f"重试文生视频任务: {task_id}")
        return jsonify({'success': True, 'message': '任务已重新加入队列'})
        
    except JimengText2VideoTask.DoesNotExist:
        return jsonify({'success': False, 'message': '任务不存在'}), 404
    except Exception as e:
        print(f"重试文生视频任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@jimeng_text2video_bp.route('/tasks/batch-retry', methods=['POST'])
def batch_retry_text2video_tasks():
    """批量重试失败的文生视频任务"""
    try:
        data = request.get_json()
        task_ids = data.get('task_ids', [])
        
        if task_ids:
            # 如果提供了特定的任务ID列表，只重试这些任务
            tasks = JimengText2VideoTask.select().where(
                JimengText2VideoTask.id.in_(task_ids),
                JimengText2VideoTask.status == 3  # 只重试失败的任务
            )
            retry_count = 0
            for task in tasks:
                task.update_status(0)  # 重置为排队状态
                retry_count += 1
        else:
            # 如果没有提供任务ID，重试所有失败的任务
            tasks = JimengText2VideoTask.select().where(
                JimengText2VideoTask.status == 3  # 只重试失败的任务
            )
            retry_count = 0
            for task in tasks:
                task.update_status(0)  # 重置为排队状态
                retry_count += 1
        
        print(f"批量重试文生视频任务: {retry_count}个")
        return jsonify({
            'success': True,
            'message': f'已重新加入队列 {retry_count} 个任务',
            'data': {
                'retry_count': retry_count
            }
        })
        
    except Exception as e:
        print(f"批量重试文生视频任务失败: {str(e)}")
        return jsonify({'success': False, 'message': f'批量重试失败: {str(e)}'}), 500

@jimeng_text2video_bp.route('/tasks/batch-delete', methods=['POST'])
def batch_delete_text2video_tasks():
    """批量删除文生视频任务"""
    try:
        data = request.get_json()
        task_ids = data.get('task_ids', [])
        
        if not task_ids:
            return jsonify({'success': False, 'message': '未提供任务ID'}), 400
        
        # 删除任务
        deleted_count = JimengText2VideoTask.delete().where(JimengText2VideoTask.id.in_(task_ids)).execute()
        
        print(f"批量删除文生视频任务: {deleted_count}个")
        return jsonify({'success': True, 'message': f'成功删除 {deleted_count} 个任务'})
        
    except Exception as e:
        print(f"批量删除文生视频任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@jimeng_text2video_bp.route('/tasks/batch-add', methods=['POST'])
def batch_add_tasks():
    """批量添加文生视频任务"""
    try:
        data = request.get_json()
        
        # 检查是否包含提示词列表
        if 'prompts' not in data:
            return jsonify({
                'success': False,
                'message': '缺少提示词列表'
            }), 400

        prompts = data['prompts']
        model = data.get('model', 'Video 3.0')
        second = data.get('second', 5)
        resolution = data.get('resolution', '720p')  # 分辨率参数
        ratio = data.get('ratio', '1:1')  # 视频比例参数

        created_tasks = []
        failed_tasks = []
        
        for i, prompt in enumerate(prompts):
            try:
                task = JimengText2VideoTask.create(
                    prompt=prompt,
                    model=model,
                    second=second,
                    resolution=resolution,  # 添加分辨率参数
                    ratio=ratio,  # 添加比例参数
                    status=0
                )
                created_tasks.append(task.id)
                print(f"创建文生视频任务: {task.id}, 提示词: {prompt}")
                
            except Exception as e:
                failed_tasks.append(f"提示词 {i+1}: {str(e)}")
                print(f"处理提示词 {prompt} 失败: {str(e)}")

        # 构建响应消息
        message_parts = []
        if created_tasks:
            message_parts.append(f"成功创建 {len(created_tasks)} 个任务")
        if failed_tasks:
            message_parts.append(f"失败 {len(failed_tasks)} 个")

        return jsonify({
            'success': True,
            'message': ', '.join(message_parts) if message_parts else '没有创建任何任务',
            'data': {
                'created_count': len(created_tasks),
                'failed_count': len(failed_tasks),
                'created_task_ids': created_tasks,
                'failed_tasks': failed_tasks
            }
        })

    except Exception as e:
        print(f"批量添加任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@jimeng_text2video_bp.route('/tasks/batch-download', methods=['POST'])
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
        tasks = list(JimengText2VideoTask.select().where(
            JimengText2VideoTask.id.in_(task_ids),
            JimengText2VideoTask.status == 2  # 只下载已完成的任务
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

@jimeng_text2video_bp.route('/stats', methods=['GET'])
def get_text2video_stats():
    """获取文生视频统计信息"""
    try:
        # 统计时过滤掉空任务
        base_query = JimengText2VideoTask.select()
        total_tasks = base_query.count()
        pending_tasks = base_query.where(JimengText2VideoTask.status == 0).count()
        processing_tasks = base_query.where(JimengText2VideoTask.status == 1).count()
        completed_tasks = base_query.where(JimengText2VideoTask.status == 2).count()
        failed_tasks = base_query.where(JimengText2VideoTask.status == 3).count()
        
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
        print(f"获取文生视频统计失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500 

@jimeng_text2video_bp.route('/tasks/delete-before-today', methods=['DELETE'])
def delete_tasks_before_today():
    """删除今日前的所有文生视频任务"""
    try:
        from datetime import datetime, timedelta
        import pytz
        
        # 获取今日开始时间（凌晨0点）
        beijing_tz = pytz.timezone('Asia/Shanghai')
        today_start = datetime.now(beijing_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 查询今日前的任务
        before_today_tasks = JimengText2VideoTask.select().where(
            JimengText2VideoTask.create_at < today_start
        )
        
        count = before_today_tasks.count()

        if count == 0:
            return jsonify({
                'success': True,
                'message': '没有今日前的任务需要删除',
                'data': {'deleted_count': 0}
            })

        # 删除任务
        deleted_count = JimengText2VideoTask.delete().where(
            JimengText2VideoTask.create_at < today_start
        ).execute()

        print(f"删除了 {deleted_count} 个今日前的文生视频任务")

        return jsonify({
            'success': True,
            'message': f'成功删除 {deleted_count} 个今日前的任务',
            'data': {'deleted_count': deleted_count}
        })

    except Exception as e:
        print(f"删除今日前任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'删除今日前任务失败: {str(e)}'
        }), 500 

@jimeng_text2video_bp.route('/tasks/batch-create-from-table', methods=['POST'])
def batch_create_tasks_from_table():
    """从表格批量创建文生视频任务"""
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
                if 'prompt' not in task_data or not task_data['prompt']:
                    failed_tasks.append(f"第 {i+1} 行: 缺少提示词")
                    continue

                prompt = task_data['prompt'].strip()
                model = task_data.get('model', 'Video 3.0')
                second = int(task_data.get('second', 5))
                resolution = task_data.get('resolution', '720p')  # 默认分辨率为720p
                ratio = task_data.get('ratio', '1:1')  # 视频比例

                # 创建任务
                task = JimengText2VideoTask.create(
                    prompt=prompt,
                    model=model,
                    second=second,
                    resolution=resolution,  # 添加分辨率参数
                    ratio=ratio,  # 添加比例参数
                    status=0
                )
                created_tasks.append(task.id)
                print(f"从表格创建文生视频任务: {task.id}, 提示词: {prompt}, 模型: {model}, 时长: {second}s, 分辨率: {resolution}, 比例: {ratio}")

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