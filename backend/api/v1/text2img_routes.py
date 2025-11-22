# -*- coding: utf-8 -*-
"""
即梦文生图API路由
"""

import os
import json
import requests
import asyncio
from datetime import datetime
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import uuid
from backend.models.models import JimengText2ImgTask
import subprocess
import platform
import threading
from urllib.parse import urlparse

# 创建蓝图
jimeng_text2img_bp = Blueprint('jimeng_text2img', __name__, url_prefix='/api/jimeng/text2img')

@jimeng_text2img_bp.route('/tasks', methods=['GET'])
def get_text2img_tasks():
    """获取文生图任务列表"""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 1000))
        status = request.args.get('status', None)
        
        print("获取文生图任务列表，页码: {}, 每页数量: {}, 状态: {}".format(page, page_size, status))
        
        # 构建查询 - 过滤掉空任务
        query = JimengText2ImgTask.select()
        if status is not None:
            query = query.where(JimengText2ImgTask.status == status)
        
        # 分页
        total = query.count()
        tasks = query.order_by(JimengText2ImgTask.create_at.desc()).paginate(page, page_size)
        
        data = []
        for task in tasks:
            images = task.get_images()  # 获取所有图片路径
            videos = []
            try:
                videos = task.get_videos()
            except Exception:
                videos = []
            data.append({
                'id': task.id,
                'prompt': task.prompt,
                'status': task.status,
                'status_text': task.get_status_text(),
                'account_id': task.account_id,
                'images': images,  # 图片路径列表
                'image_count': len(images),  # 图片数量
                'videos': videos,
                'video_count': len(videos),
                'failure_reason': task.failure_reason,  # 失败原因类型
                'error_message': task.error_message,  # 详细错误信息
                'create_at': task.create_at.strftime('%Y-%m-%d %H:%M:%S'),
                'update_at': task.update_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        print("成功获取任务列表，总数: {}, 当前页任务数: {}".format(total, len(data)))
        return jsonify({
            'success': True,
            'data': data,
            'pagination': {
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            }
        })
        
    except Exception as e:
        print("获取任务列表失败: {}".format(str(e)))
        return jsonify({
            'success': False,
            'message': '获取任务列表失败: {}'.format(str(e))
        }), 500

@jimeng_text2img_bp.route('/tasks', methods=['POST'])
def create_text2img_task():
    """创建文生图任务 - 支持 JSON 与 multipart/form-data"""
    try:
        data = request.get_json(silent=True) or {}
        prompt = data.get('prompt') or request.form.get('prompt')
        print("创建新的文生图任务: {}".format((prompt or '')[:50]))
        
        # 验证必要字段
        if not prompt:
            return jsonify({
                'success': False,
                'message': '缺少必要字段: prompt'
            }), 400
        
        # 设置固定参数
        model = "jimeng-v1"  # 固定模型
        aspect_ratio = "1:1"  # 固定比例
        quality = "1K"  # 固定质量
        
        # 创建任务（不包含图片路径，这些在任务完成后才填入）
        task = JimengText2ImgTask.create(
            prompt=prompt,
            model=model,
            ratio=aspect_ratio,  # 字段名映射
            quality=quality,  # 使用固定的质量参数
            account_id=data.get('account_id') or request.form.get('account_id'),
            status=0,  # 默认状态：0-排队中
            # 图片路径字段保持为空，由任务处理器填入
            image1=None,
            image2=None,
            image3=None,
            image4=None
        )
        
        # 如果上传了图片，保存到临时目录（带task_id前缀）供执行阶段读取
        try:
            files = request.files.getlist('images') if 'images' in request.files else []
            print(f"接收到上传文件数量: {len(files)}")
            if files:
                tmp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tmp')
                print(f"临时目录路径: {tmp_dir}")
                os.makedirs(tmp_dir, exist_ok=True)
                saved = 0
                for f in files:
                    print(f"处理文件对象: {f}")
                    if f and f.filename:
                        filename = secure_filename(f.filename)
                        print(f"原始文件名: {f.filename}, 安全文件名: {filename}")
                        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
                        unique_name = f"text2img_{task.id}_{uuid.uuid4().hex}.{ext}"
                        path = os.path.join(tmp_dir, unique_name)
                        print(f"保存文件: {filename} -> {path}")
                        try:
                            f.save(path)
                            saved += 1
                            print(f"文件保存成功: {path}")
                            # 验证文件是否真的保存成功
                            if os.path.exists(path):
                                file_size = os.path.getsize(path)
                                print(f"文件大小: {file_size} 字节")
                            else:
                                print(f"警告: 文件似乎没有保存成功: {path}")
                        except Exception as se:
                            print(f"保存上传图片失败: {se}")
                    else:
                        print("文件对象为空或没有文件名")
                if saved:
                    print(f"文生图任务{task.id}已保存输入图片 {saved} 张")
                else:
                    print(f"文生图任务{task.id}没有成功保存任何图片")
            else:
                print("没有接收到上传的文件")
        except Exception as e:
            print(f"处理上传图片异常（忽略继续）: {e}")
        
        print("任务创建成功，任务ID: {}".format(task.id))
        return jsonify({
            'success': True,
            'data': {
                'id': task.id,
                'status': task.status,
                'status_text': task.get_status_text(),
                'create_at': task.create_at.strftime('%Y-%m-%d %H:%M:%S')
            },
            'message': '任务创建成功'
        })
        
    except Exception as e:
        print("创建任务失败: {}".format(str(e)))
        return jsonify({
            'success': False,
            'message': '创建任务失败: {}'.format(str(e))
        }), 500

@jimeng_text2img_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_text2img_task(task_id):
    """删除文生图任务"""
    try:
        task = JimengText2ImgTask.get(JimengText2ImgTask.id == task_id)
        task_prompt = task.prompt[:50] + '...' if len(task.prompt) > 50 else task.prompt

        # 删除关联的图片文件
        deleted_files_count = 0
        try:
            images = task.get_images()
            for image_path in images:
                if image_path and os.path.exists(image_path):
                    os.remove(image_path)
                    deleted_files_count += 1
                    print(f"删除图片文件: {image_path}")
        except Exception as file_error:
            print(f"删除图片文件时出错（但任务仍会被删除）: {str(file_error)}")

        # 删除任务记录
        task.delete_instance()

        print("删除任务成功: {}, 删除图片文件: {}个".format(task_prompt, deleted_files_count))
        return jsonify({
            'success': True,
            'message': f'已删除任务，同时清理了 {deleted_files_count} 个图片文件',
            'data': {
                'deleted_files_count': deleted_files_count
            }
        })

    except JimengText2ImgTask.DoesNotExist:
        print("删除失败：任务不存在，ID: {}".format(task_id))
        return jsonify({
            'success': False,
            'message': '任务不存在'
        }), 404
    except Exception as e:
        print("删除任务失败: {}".format(str(e)))
        return jsonify({
            'success': False,
            'message': '删除任务失败: {}'.format(str(e))
        }), 500

@jimeng_text2img_bp.route('/tasks/<int:task_id>/retry', methods=['POST'])
def retry_text2img_task(task_id):
    """重试文生图任务"""
    try:
        task = JimengText2ImgTask.get_by_id(task_id)
        task.status = 0  # 重置为排队状态
        task.save()
        
        print("重试文生图任务: {}".format(task_id))
        return jsonify({
            'success': True,
            'message': '任务已重新加入队列'
        })
        
    except JimengText2ImgTask.DoesNotExist:
        return jsonify({
            'success': False,
            'message': '任务不存在'
        }), 404
    except Exception as e:
        print("重试任务失败: {}".format(str(e)))
        return jsonify({
            'success': False,
            'message': '重试任务失败: {}'.format(str(e))
        }), 500

@jimeng_text2img_bp.route('/tasks/batch-retry', methods=['POST'])
def batch_retry_text2img_tasks():
    """批量重试失败的文生图任务"""
    try:
        data = request.get_json()
        task_ids = data.get('task_ids', [])
        
        if task_ids:
            # 如果提供了特定的任务ID列表，只重试这些任务
            retry_count = JimengText2ImgTask.update(status=0).where(
                JimengText2ImgTask.id.in_(task_ids),
                JimengText2ImgTask.status == 3  # 只重试失败的任务
            ).execute()
        else:
            # 如果没有提供任务ID，重试所有失败的任务
            retry_count = JimengText2ImgTask.update(status=0).where(
                JimengText2ImgTask.status == 3  # 只重试失败的任务
            ).execute()
        
        print(f"批量重试文生图任务: {retry_count}个")
        return jsonify({
            'success': True,
            'message': f'已重新加入队列 {retry_count} 个任务',
            'data': {
                'retry_count': retry_count
            }
        })
        
    except Exception as e:
        print(f"批量重试文生图任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'批量重试失败: {str(e)}'
        }), 500

@jimeng_text2img_bp.route('/stats', methods=['GET'])
def get_text2img_stats():
    """获取文生图任务统计信息"""
    try:
        # 统计时过滤掉空任务
        base_query = JimengText2ImgTask.select()
        total_tasks = base_query.count()
        queued_tasks = base_query.where(JimengText2ImgTask.status == 0).count()  # 排队中
        processing_tasks = base_query.where(JimengText2ImgTask.status == 1).count()  # 生成中
        completed_tasks = base_query.where(JimengText2ImgTask.status == 2).count()  # 已完成
        failed_tasks = base_query.where(JimengText2ImgTask.status == 3).count()  # 失败
        
        print("获取任务统计 - 总数:{}, 排队:{}, 处理中:{}, 已完成:{}, 失败:{}".format(
            total_tasks, queued_tasks, processing_tasks, completed_tasks, failed_tasks))
        
        return jsonify({
            'success': True,
            'data': {
                'total': total_tasks,
                'queued': queued_tasks,
                'processing': processing_tasks,
                'completed': completed_tasks,
                'failed': failed_tasks
            },
            'message': '统计信息获取成功'
        })
        
    except Exception as e:
        print("获取统计信息失败: {}".format(str(e)))
        return jsonify({
            'success': False,
            'message': '获取统计信息失败: {}'.format(str(e))
        }), 500

@jimeng_text2img_bp.route('/tasks/batch-delete', methods=['POST'])
def batch_delete_text2img_tasks():
    """批量删除文生图任务"""
    try:
        data = request.get_json()
        task_ids = data.get('task_ids', [])

        if not task_ids:
            return jsonify({
                'success': False,
                'message': '未提供任务ID'
            }), 400

        # 先查询要删除的任务，获取图片路径
        tasks_to_delete = JimengText2ImgTask.select().where(
            JimengText2ImgTask.id.in_(task_ids)
        )

        deleted_files_count = 0
        error_count = 0

        # 删除关联的图片文件
        for task in tasks_to_delete:
            try:
                images = task.get_images()
                for image_path in images:
                    if image_path and os.path.exists(image_path):
                        os.remove(image_path)
                        deleted_files_count += 1
                        print(f"删除图片文件: {image_path}")
            except Exception as file_error:
                print(f"删除任务 {task.id} 的图片文件时出错: {str(file_error)}")
                error_count += 1

        # 删除任务记录
        deleted_count = JimengText2ImgTask.delete().where(JimengText2ImgTask.id.in_(task_ids)).execute()

        print(f"批量删除文生图任务: {deleted_count}个，删除图片文件: {deleted_files_count}个，错误: {error_count}个")
        return jsonify({
            'success': True,
            'message': f'成功删除 {deleted_count} 个任务，同时清理了 {deleted_files_count} 个图片文件',
            'data': {
                'deleted_tasks': deleted_count,
                'deleted_files_count': deleted_files_count,
                'error_count': error_count
            }
        })

    except Exception as e:
        print(f"批量删除文生图任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'批量删除失败: {str(e)}'
        }), 500

@jimeng_text2img_bp.route('/tasks/batch-download', methods=['POST'])
def batch_download_images():
    """批量下载任务图片"""
    try:
        data = request.get_json()
        task_ids = data.get('task_ids', [])
        
        if not task_ids:
            return jsonify({
                'success': False,
                'message': '请提供要下载的任务ID列表'
            }), 400
        
        # 获取任务信息
        tasks = list(JimengText2ImgTask.select().where(
            JimengText2ImgTask.id.in_(task_ids),
            JimengText2ImgTask.status == 2  # 只下载已完成的任务
        ))
        
        if not tasks:
            return jsonify({
                'success': False,
                'message': '没有找到可下载的已完成任务'
            }), 400
        
        # 收集所有图片URL
        all_images = []
        for task in tasks:
            images = task.get_images()
            for i, img_url in enumerate(images):
                if img_url:
                    all_images.append({
                        'task_id': task.id,
                        'image_index': i + 1,
                        'url': img_url,
                        'filename': f'task_{task.id}_image_{i + 1}.jpg'
                    })
        
        if not all_images:
            return jsonify({
                'success': False,
                'message': '选中的任务没有图片可下载'
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
                            set selectedFolder to choose folder with prompt "选择图片下载文件夹" default location (path to downloads folder)
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
                            $folderBrowser.Description = "选择图片下载文件夹"
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
                            '--title=选择图片下载文件夹'
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
                
                print(f"开始下载 {len(all_images)} 张图片到: {download_dir}")
                
                # 创建以当前时间命名的子文件夹
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                batch_folder = os.path.join(download_dir, f"jimeng_images_{timestamp}")
                os.makedirs(batch_folder, exist_ok=True)
                
                # 准备下载信息
                file_infos = []
                for img_info in all_images:
                    file_infos.append({
                        'url': img_info['url'],
                        'file_path': os.path.join(batch_folder, img_info['filename']),
                        'filename': img_info['filename']
                    })
                
                # 使用带重试机制的批量下载（支持并行）
                from utils.download_util import batch_download_files
                download_result = batch_download_files(
                    file_infos=file_infos,
                    max_retries=5,
                    timeout=30,
                    max_workers=5  # 并行下载数
                )
                
                success_count = download_result['success_count']
                error_count = download_result['failed_count']
                
                print(f"批量下载完成: 成功 {success_count} 张，失败 {error_count} 张")
                print(f"文件保存位置: {batch_folder}")
                
            except Exception as e:
                print(f"批量下载过程出错: {str(e)}")
        
        # 在后台线程中执行下载
        download_thread = threading.Thread(target=download_in_background)
        download_thread.daemon = True
        download_thread.start()
        
        return jsonify({
            'success': True,
            'message': f'开始下载 {len(all_images)} 张图片，请选择下载文件夹',
            'data': {
                'total_images': len(all_images),
                'tasks_count': len(tasks)
            }
        })
        
    except Exception as e:
        print(f"批量下载失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'批量下载失败: {str(e)}'
        }), 500

@jimeng_text2img_bp.route('/tasks/delete-before-today', methods=['DELETE'])
def delete_tasks_before_today():
    """删除今日前的所有文生图任务"""
    try:
        from datetime import datetime, timedelta
        import pytz

        # 获取今日开始时间（凌晨0点）
        beijing_tz = pytz.timezone('Asia/Shanghai')
        today_start = datetime.now(beijing_tz).replace(hour=0, minute=0, second=0, microsecond=0)

        # 查询今日前的任务
        before_today_tasks = JimengText2ImgTask.select().where(
            JimengText2ImgTask.create_at < today_start
        )

        count = before_today_tasks.count()

        if count == 0:
            return jsonify({
                'success': True,
                'message': '没有今日前的任务需要删除',
                'data': {'deleted_count': 0, 'deleted_files_count': 0}
            })

        # 删除关联的图片文件
        deleted_files_count = 0
        for task in before_today_tasks:
            try:
                images = task.get_images()
                for image_path in images:
                    if image_path and os.path.exists(image_path):
                        os.remove(image_path)
                        deleted_files_count += 1
                        print(f"删除图片文件: {image_path}")
            except Exception as file_error:
                print(f"删除任务 {task.id} 的图片文件时出错: {str(file_error)}")

        # 删除任务
        deleted_count = JimengText2ImgTask.delete().where(
            JimengText2ImgTask.create_at < today_start
        ).execute()

        print(f"删除了 {deleted_count} 个今日前的文生图任务，删除图片文件: {deleted_files_count}个")

        return jsonify({
            'success': True,
            'message': f'成功删除 {deleted_count} 个今日前的任务，同时清理了 {deleted_files_count} 个图片文件',
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

@jimeng_text2img_bp.route('/cleanup-orphaned-images', methods=['DELETE'])
def cleanup_orphaned_text2img_images():
    """清理孤立的文生图图片文件（没有关联任务的图片）"""
    try:
        # 获取项目中所有存储的图片路径
        all_tasks = JimengText2ImgTask.select()
        used_image_paths = set()

        for task in all_tasks:
            images = task.get_images()
            used_image_paths.update(images)

        # 获取项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        # 检查上传目录 (文生图通常不需要上传目录，但可能有一些临时文件)
        tmp_dir = os.path.join(project_root, 'tmp')
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

        print(f"清理文生图孤立图片完成: 删除 {deleted_files_count} 个文件，失败 {error_count} 个")

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