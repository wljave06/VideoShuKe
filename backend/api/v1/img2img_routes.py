# -*- coding: utf-8 -*-
"""
即梦图生图API路由
"""

import os
import json
import requests
import asyncio
import pandas as pd
from datetime import datetime
from flask import Blueprint, request, jsonify
from backend.models.models import JimengImg2ImgTask
import subprocess
import platform
import threading
from urllib.parse import urlparse
from werkzeug.utils import secure_filename
import uuid

# 创建蓝图
jimeng_img2img_bp = Blueprint('jimeng_img2img', __name__, url_prefix='/api/jimeng/img2img')

def allowed_file(filename):
    """检查文件类型是否允许"""
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@jimeng_img2img_bp.route('/tasks', methods=['GET'])
def get_img2img_tasks():
    """获取图生图任务列表"""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 1000))
        status = request.args.get('status', None)
        
        print("获取图生图任务列表，页码: {}, 每页数量: {}, 状态: {}".format(page, page_size, status))
        
        # 构建查询 - 过滤掉空任务
        query = JimengImg2ImgTask.select()
        if status is not None:
            query = query.where(JimengImg2ImgTask.status == status)
        
        # 分页
        total = query.count()
        tasks = query.order_by(JimengImg2ImgTask.create_at.desc()).paginate(page, page_size)
        
        data = []
        for task in tasks:
            input_images = task.get_input_images()
            output_images = task.get_images()
            
            data.append({
                'id': task.id,
                'prompt': task.prompt,
                'model': task.model,
                'ratio': task.ratio,
                'status': task.status,
                'status_text': task.get_status_text(),
                'account_id': task.account_id,
                'input_images': input_images,
                'output_images': output_images,
                'task_id': task.task_id,
                'retry_count': task.retry_count,
                'max_retry': task.max_retry,
                'failure_reason': task.failure_reason,
                'error_message': task.error_message,
                'create_at': task.create_at.strftime('%Y-%m-%d %H:%M:%S'),
                'update_at': task.update_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return jsonify({
            'success': True,
            'data': {
                'tasks': data,
                'total': total,
                'page': page,
                'page_size': page_size
            }
        })
        
    except Exception as e:
        print("获取任务列表失败: {}".format(str(e)))
        return jsonify({
            'success': False,
            'message': '获取任务列表失败: {}'.format(str(e))
        }), 500

@jimeng_img2img_bp.route('/stats', methods=['GET'])
def get_img2img_stats():
    """获取图生图任务统计"""
    try:
        # 统计各状态的任务数量
        total = JimengImg2ImgTask.select().count()
        queued = JimengImg2ImgTask.select().where(JimengImg2ImgTask.status == 0).count()
        processing = JimengImg2ImgTask.select().where(JimengImg2ImgTask.status == 1).count()
        completed = JimengImg2ImgTask.select().where(JimengImg2ImgTask.status == 2).count()
        failed = JimengImg2ImgTask.select().where(JimengImg2ImgTask.status == 3).count()
        
        return jsonify({
            'success': True,
            'data': {
                'total': total,
                'queued': queued,
                'processing': processing,
                'completed': completed,
                'failed': failed
            }
        })
        
    except Exception as e:
        print("获取统计信息失败: {}".format(str(e)))
        return jsonify({
            'success': False,
            'message': '获取统计信息失败: {}'.format(str(e))
        }), 500

@jimeng_img2img_bp.route('/tasks', methods=['POST'])
def create_img2img_task():
    """创建图生图任务"""
    try:
        # 检查是否有文件上传
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
        
        # 检查文件格式
        for file in files:
            if file.filename != '' and not allowed_file(file.filename):
                return jsonify({
                    'success': False,
                    'message': '不支持的图片格式，请上传PNG、JPG、JPEG、GIF、BMP或WebP格式的图片'
                }), 400
        
        # 获取表单数据
        prompt = request.form.get('prompt', '').strip()
        model = request.form.get('model', 'Nano Banana')
        aspect_ratio = request.form.get('aspect_ratio')
        # 如果用户没有选择比例或传递空字符串，则设置为None
        if not aspect_ratio or aspect_ratio.strip() == '':
            aspect_ratio = None
        # 获取质量参数，如果未提供则使用默认值
        quality = request.form.get('quality', '1K')
        # 获取重复次数参数，默认为1
        repeat_count = int(request.form.get('repeat_count', 1))
        # 确保重复次数在1-50范围内
        repeat_count = max(1, min(50, repeat_count))
        
        # 验证图片数量
        valid_files = [f for f in files if f.filename != '']
        if model == 'Nano Banana':
            if len(valid_files) > 3:
                return jsonify({
                    'success': False,
                    'message': f'{model}模型最多支持3张图片'
                }), 400
        elif model == 'Image 4.0':
            if len(valid_files) > 6:
                return jsonify({
                    'success': False,
                    'message': f'{model}模型最多支持6张图片'
                }), 400
        else:
            if len(valid_files) > 1:
                return jsonify({
                    'success': False,
                    'message': f'{model}模型只支持1张图片'
                }), 400
        
        if not prompt:
            return jsonify({
                'success': False,
                'message': '请输入提示词'
            }), 400
        
        # 保存上传的图片
        saved_images = []
        tmp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tmp')
        os.makedirs(tmp_dir, exist_ok=True)
        
        for file in files:
            if file.filename != '':
                filename = secure_filename(file.filename)
                file_ext = filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
                file_path = os.path.join(tmp_dir, unique_filename)
                file.save(file_path)
                saved_images.append(file_path)
        
        # 根据repeat_count创建多个任务
        created_task_ids = []
        for i in range(repeat_count):
            task = JimengImg2ImgTask.create(
                prompt=prompt,
                model=model,
                ratio=aspect_ratio,
                quality=quality,  # 添加质量参数
                status=0,  # 默认状态：0-排队中
                # 输出图片路径字段保持为空，由任务处理器填入
                image1=None,
                image2=None,
                image3=None,
                image4=None
            )
            
            # 设置输入图片
            task.set_input_images(saved_images)
            created_task_ids.append(task.id)
            print("图生图任务创建成功，任务ID: {}".format(task.id))
        
        return jsonify({
            'success': True,
            'data': {
                'ids': created_task_ids,
                'count': len(created_task_ids),
                'status_text': '排队中' if created_task_ids else '无任务创建',
                'create_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'message': f'成功创建 {len(created_task_ids)} 个任务'
        })
        
    except Exception as e:
        print("创建任务失败: {}".format(str(e)))
        return jsonify({
            'success': False,
            'message': '创建任务失败: {}'.format(str(e))
        }), 500

@jimeng_img2img_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_img2img_task(task_id):
    """删除图生图任务"""
    try:
        task = JimengImg2ImgTask.get_by_id(task_id)

        deleted_input_count = 0
        deleted_output_count = 0

        # 删除输入图片文件
        input_images = task.get_input_images()
        for image_path in input_images:
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                    deleted_input_count += 1
                    print(f"删除输入图片文件: {image_path}")
                except Exception as e:
                    print(f"删除输入图片文件失败: {image_path}, 错误: {e}")

        # 删除任务记录
        task.delete_instance()

        print(f"删除图生图任务: {task_id}，删除输入图片: {deleted_input_count}个")

        return jsonify({
            'success': True,
            'message': f'任务删除成功，同时清理了 {deleted_input_count} 个输入图片文件',
            'data': {
                'deleted_input_count': deleted_input_count,
                'total_deleted_files': deleted_input_count
            }
        })

    except JimengImg2ImgTask.DoesNotExist:
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

@jimeng_img2img_bp.route('/tasks/<int:task_id>/retry', methods=['POST'])
def retry_img2img_task(task_id):
    """重试图生图任务"""
    try:
        task = JimengImg2ImgTask.get_by_id(task_id)
        
        if task.can_retry():
            task.retry_task()
            return jsonify({
                'success': True,
                'message': '任务已重新排队'
            })
        else:
            return jsonify({
                'success': False,
                'message': '任务不能重试'
            }), 400
            
    except JimengImg2ImgTask.DoesNotExist:
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

@jimeng_img2img_bp.route('/tasks/batch-delete', methods=['POST'])
def batch_delete_img2img_tasks():
    """批量删除图生图任务"""
    try:
        data = request.get_json()
        task_ids = data.get('task_ids', [])

        if not task_ids:
            return jsonify({
                'success': False,
                'message': '请选择要删除的任务'
            }), 400

        # 先查询要删除的任务，获取图片路径
        tasks_to_delete = JimengImg2ImgTask.select().where(
            JimengImg2ImgTask.id.in_(task_ids)
        )

        deleted_count = 0
        deleted_input_count = 0
        deleted_output_count = 0
        error_count = 0

        # 删除关联的图片文件
        for task in tasks_to_delete:
            try:
                # 删除输入图片文件
                input_images = task.get_input_images()
                for image_path in input_images:
                    if image_path and os.path.exists(image_path):
                        try:
                            os.remove(image_path)
                            deleted_input_count += 1
                            print(f"删除输入图片文件: {image_path}")
                        except Exception as e:
                            print(f"删除输入图片文件失败: {image_path}, 错误: {e}")

                # 删除输出图片文件
                output_images = task.get_images()
                for image_path in output_images:
                    if image_path and os.path.exists(image_path):
                        try:
                            os.remove(image_path)
                            deleted_output_count += 1
                            print(f"删除输出图片文件: {image_path}")
                        except Exception as e:
                            print(f"删除输出图片文件失败: {image_path}, 错误: {e}")

            except Exception as file_error:
                print(f"删除任务 {task.id} 的图片文件时出错: {str(file_error)}")
                error_count += 1

        # 删除任务记录
        deleted_count = JimengImg2ImgTask.delete().where(JimengImg2ImgTask.id.in_(task_ids)).execute()

        total_deleted_files = deleted_input_count + deleted_output_count
        print(f"批量删除图生图任务: {deleted_count}个，删除输入图片: {deleted_input_count}个，删除输出图片: {deleted_output_count}个，错误: {error_count}个")

        return jsonify({
            'success': True,
            'message': f'成功删除 {deleted_count} 个任务，同时清理了 {total_deleted_files} 个图片文件',
            'data': {
                'deleted_tasks': deleted_count,
                'deleted_input_count': deleted_input_count,
                'deleted_output_count': deleted_output_count,
                'total_deleted_files': total_deleted_files,
                'error_count': error_count
            }
        })

    except Exception as e:
        print("批量删除任务失败: {}".format(str(e)))
        return jsonify({
            'success': False,
            'message': '批量删除任务失败: {}'.format(str(e))
        }), 500

@jimeng_img2img_bp.route('/tasks/batch-download', methods=['POST'])
def batch_download_img2img_tasks():
    """批量下载图生图任务的生成图片"""
    try:
        data = request.get_json()
        task_ids = data.get('task_ids', [])
        
        if not task_ids:
            return jsonify({
                'success': False,
                'message': '请选择要下载的任务'
            }), 400
        
        def select_folder_and_download():
            try:
                # 调用原生文件夹选择对话框
                folder_path = None
                system = platform.system()
                
                if system == "Darwin":  # macOS
                    result = subprocess.run([
                        'osascript', '-e',
                        'tell application "Finder" to set folder_path to (choose folder with prompt "选择图片保存文件夹") as string',
                        '-e',
                        'return POSIX path of folder_path'
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0 and result.stdout.strip():
                        folder_path = result.stdout.strip()
                        
                elif system == "Windows":  # Windows
                    print("正在调用Windows文件夹选择器...")
                    ps_script = """
                    try {
                        [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms") | Out-Null
                        $folderBrowser = New-Object System.Windows.Forms.FolderBrowserDialog
                        $folderBrowser.Description = "选择图片保存文件夹"
                        $folderBrowser.RootFolder = "MyComputer"
                        $folderBrowser.ShowNewFolderButton = $true
                        $result = $folderBrowser.ShowDialog()
                        if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
                            [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
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
                    
                    try:
                        # 使用系统默认编码
                        result = subprocess.run([
                            'powershell', '-ExecutionPolicy', 'Bypass', '-Command', ps_script
                        ], capture_output=True, timeout=60)
                        
                        # 尝试处理输出
                        stdout_decoded = result.stdout
                        if result.stdout:
                            try:
                                stdout_decoded = result.stdout.decode('utf-8')
                            except UnicodeDecodeError:
                                try:
                                    stdout_decoded = result.stdout.decode('gbk')  # Windows中文系统常用编码
                                except UnicodeDecodeError:
                                    stdout_decoded = result.stdout.decode('utf-8', errors='ignore')  # 忽略错误字符
                        
                        stderr_decoded = result.stderr
                        if result.stderr:
                            try:
                                stderr_decoded = result.stderr.decode('utf-8')
                            except UnicodeDecodeError:
                                try:
                                    stderr_decoded = result.stderr.decode('gbk')
                                except UnicodeDecodeError:
                                    stderr_decoded = result.stderr.decode('utf-8', errors='ignore')
                        
                        print(f"PowerShell返回码: {result.returncode}")
                        print(f"PowerShell输出: {stdout_decoded}")
                        print(f"PowerShell错误: {stderr_decoded}")
                        
                        if result.returncode == 0 and stdout_decoded and stdout_decoded.strip() and stdout_decoded.strip() != "CANCELLED":
                            folder_path = stdout_decoded.strip()
                            print(f"用户选择了文件夹: {folder_path}")
                        elif result.returncode == 1:
                            print("用户取消了文件夹选择")
                            return
                    except Exception as e:
                        print(f"执行PowerShell命令时出错: {e}")
                        return
                        
                elif system == "Linux":  # Linux
                    result = subprocess.run([
                        'zenity', '--file-selection', '--directory',
                        '--title=选择图片保存文件夹'
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0 and result.stdout.strip():
                        folder_path = result.stdout.strip()
                
                if not folder_path:
                    print("用户取消了文件夹选择或获取路径失败")
                    return
                
                print(f"选择的保存文件夹: {folder_path}")
                
                if not os.path.exists(folder_path):
                    print(f"文件夹不存在: {folder_path}")
                    return
                
                # 获取要下载的任务
                tasks = JimengImg2ImgTask.select().where(
                    JimengImg2ImgTask.id.in_(task_ids),
                    JimengImg2ImgTask.status == 2  # 已完成
                )
                
                if not tasks:
                    print("没有找到符合条件的已完成任务")
                    return
                
                # 准备下载信息
                file_infos = []
                for task in tasks:
                    images = task.get_images()
                    for i, image_path in enumerate(images):
                        if image_path and image_path.strip():
                            # 获取文件扩展名
                            if image_path.lower().endswith('.png'):
                                ext = 'png'
                            elif image_path.lower().endswith('.jpg') or image_path.lower().endswith('.jpeg'):
                                ext = 'jpg'
                            elif image_path.lower().endswith('.gif'):
                                ext = 'gif'
                            elif image_path.lower().endswith('.bmp'):
                                ext = 'bmp'
                            elif image_path.lower().endswith('.webp'):
                                ext = 'webp'
                            else:
                                ext = 'png'  # 默认为png
                            
                            # 构建图像URL
                            if image_path.startswith('http://') or image_path.startswith('https://'):
                                image_url = image_path
                            else:
                                # 如果是本地文件路径，构建服务器URL
                                image_url = f"http://localhost:8888/static/images/{os.path.basename(image_path)}"
                            
                            filename = f"img2img_task_{task.id}_{i+1}.{ext}"
                            file_infos.append({
                                'url': image_url,
                                'filename': filename,
                                'task_id': task.id
                            })
                
                if not file_infos:
                    print("没有找到可下载的图片")
                    return
                
                # 创建批量下载文件夹
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                batch_folder = os.path.join(folder_path, f"jimeng_img2img_{timestamp}")
                
                # 确保路径编码正确
                try:
                    batch_folder = batch_folder.encode('utf-8').decode('utf-8')
                except UnicodeError:
                    batch_folder = batch_folder.encode('gbk').decode('gbk')
                
                os.makedirs(batch_folder, exist_ok=True)
                
                # 使用并行下载文件
                from utils.download_util import batch_download_files
                
                # 为每个file_info添加file_path
                for file_info in file_infos:
                    file_info['file_path'] = os.path.join(batch_folder, file_info['filename'])
                
                # 使用并行批量下载
                download_result = batch_download_files(
                    file_infos=file_infos,
                    max_retries=5,
                    timeout=30,
                    max_workers=5  # 并行下载数
                )
                
                success_count = download_result['success_count']
                print(f"批量下载完成，成功下载 {success_count} 个文件到: {batch_folder}")
                
                print(f"批量下载完成，成功下载 {success_count} 个文件到: {batch_folder}")
                
            except Exception as e:
                print(f"批量下载过程中出错: {e}")
                import traceback
                traceback.print_exc()
        
        # 在后台线程中执行下载
        thread = threading.Thread(target=select_folder_and_download)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': '正在选择下载文件夹，请稍候...'
        })
        
    except Exception as e:
        print("批量下载失败: {}".format(str(e)))
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': '批量下载失败: {}'.format(str(e))
        }), 500


@jimeng_img2img_bp.route('/tasks/batch-retry', methods=['POST'])
def batch_retry_img2img_tasks():
    """批量重试图生图失败任务"""
    try:
        data = request.get_json()
        task_ids = data.get('task_ids', []) if data else []
        
        success_count = 0
        
        if task_ids:
            # 如果提供了任务ID列表，只重试这些任务
            for task_id in task_ids:
                try:
                    task = JimengImg2ImgTask.get_by_id(task_id)
                    if task.status == 3:  # 只重试失败的任务
                        # 重置任务状态为排队中
                        task.status = 0
                        task.error_message = None
                        task.update_at = datetime.now()
                        task.save()
                        success_count += 1
                except JimengImg2ImgTask.DoesNotExist:
                    # 任务不存在，跳过
                    continue
        else:
            # 如果没有提供任务ID列表，重试所有失败的任务
            failed_tasks = JimengImg2ImgTask.select().where(JimengImg2ImgTask.status == 3)
            for task in failed_tasks:
                task.status = 0  # 重置为排队中
                task.error_message = None
                task.update_at = datetime.now()
                task.save()
                success_count += 1
        
        return jsonify({
            'success': True,
            'data': {
                'retry_count': success_count
            },
            'message': f'成功重试 {success_count} 个任务'
        })
        
    except Exception as e:
        print("批量重试失败: {}".format(str(e)))
        return jsonify({
            'success': False,
            'message': '批量重试失败: {}'.format(str(e))
        }), 500

@jimeng_img2img_bp.route('/tasks/import-folder', methods=['POST'])
def import_folder_img2img_tasks():
    """从文件夹导入图片创建图生图任务"""
    try:
        # 获取请求数据
        data = request.get_json()
        model = data.get('model', 'Nano Banana')  # 默认为Nano Banana
        quality = data.get('quality', '1K')  # 默认质量为1K
        aspect_ratio = data.get('aspect_ratio', '1:1')  # 默认比例为1:1
        use_prompt = data.get('usePrompt', False)  # 是否使用提示词
        prompt = data.get('prompt', '')  # 提示词内容

        print(f"导入文件夹图生图任务，模型: {model}, 质量: {quality}, 比例: {aspect_ratio}, 使用提示词: {use_prompt}, 提示词: {prompt}")

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
                        # 根据use_prompt参数决定是否使用提示词
                        task_prompt = prompt if use_prompt else ''

                        # 复制图片到后端tmp目录
                        tmp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tmp')
                        os.makedirs(tmp_dir, exist_ok=True)

                        # 生成唯一的文件名
                        filename = os.path.basename(image_path)
                        file_ext = os.path.splitext(filename)[1].lower()
                        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
                        dest_path = os.path.join(tmp_dir, unique_filename)

                        # 复制文件
                        import shutil
                        shutil.copy2(image_path, dest_path)
                        print(f"复制图片到后端: {image_path} -> {dest_path}")

                        # 创建图生图任务
                        task = JimengImg2ImgTask.create(
                            prompt=task_prompt,  # 根据use_prompt参数决定提示词
                            model=model,  # 使用传入的模型参数
                            ratio=aspect_ratio if model != 'Nano Banana' else None,  # Nano Banana不设置比例
                            quality=quality,  # 使用传入的质量参数
                            status=0,  # 默认状态：0-排队中
                            # 输出图片字段保持为空
                            image1=None,
                            image2=None,
                            image3=None,
                            image4=None
                        )

                        # 设置输入图片（使用复制后的路径）
                        task.set_input_images([dest_path])
                        created_count += 1
                    except Exception as e:
                        print(f"创建任务失败 {image_path}: {str(e)}")

                print(f"成功创建 {created_count} 个图生图任务，模型: {model}, 质量: {quality}, 比例: {aspect_ratio}, 提示词: {task_prompt}")

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

@jimeng_img2img_bp.route('/cleanup-orphaned-images', methods=['DELETE'])
def cleanup_orphaned_img2img_images():
    """清理孤立的图生图图片文件（没有关联任务的图片）"""
    try:
        # 获取项目中所有存储的图片路径
        all_tasks = JimengImg2ImgTask.select()
        used_image_paths = set()

        # 收集输入图片路径
        for task in all_tasks:
            input_images = task.get_input_images()
            used_image_paths.update(input_images)

        # 收集输出图片路径
        for task in all_tasks:
            output_images = task.get_images()
            used_image_paths.update(output_images)

        # 获取项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        # 检查上传目录
        tmp_dir = os.path.join(project_root, 'tmp')
        deleted_files_count = 0
        error_count = 0

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

        print(f"清理图生图孤立图片完成: 删除 {deleted_files_count} 个文件，失败 {error_count} 个")

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

@jimeng_img2img_bp.route('/tasks/delete-before-today', methods=['DELETE'])
def delete_img2img_tasks_before_today():
    """删除今日前的所有图生图任务"""
    try:
        from datetime import datetime, timedelta
        import pytz

        # 获取今日开始时间（凌晨0点）
        beijing_tz = pytz.timezone('Asia/Shanghai')
        today_start = datetime.now(beijing_tz).replace(hour=0, minute=0, second=0, microsecond=0)

        # 查询今日前的任务
        before_today_tasks = JimengImg2ImgTask.select().where(
            JimengImg2ImgTask.create_at < today_start
        )

        count = before_today_tasks.count()

        if count == 0:
            return jsonify({
                'success': True,
                'message': '没有今日前的任务需要删除',
                'data': {'deleted_count': 0, 'deleted_files_count': 0}
            })

        # 删除关联的图片文件
        deleted_input_count = 0
        deleted_output_count = 0

        for task in before_today_tasks:
            try:
                # 删除输入图片文件
                input_images = task.get_input_images()
                for image_path in input_images:
                    if image_path and os.path.exists(image_path):
                        os.remove(image_path)
                        deleted_input_count += 1
                        print(f"删除输入图片: {image_path}")

                # 删除输出图片文件
                output_images = task.get_images()
                for image_path in output_images:
                    if image_path and os.path.exists(image_path):
                        os.remove(image_path)
                        deleted_output_count += 1
                        print(f"删除输出图片: {image_path}")

            except Exception as file_error:
                print(f"删除任务 {task.id} 的图片文件时出错: {str(file_error)}")

        # 删除任务
        deleted_count = JimengImg2ImgTask.delete().where(
            JimengImg2ImgTask.create_at < today_start
        ).execute()

        total_deleted_files = deleted_input_count + deleted_output_count
        print(f"删除了 {deleted_count} 个今日前的图生图任务，删除输入图片: {deleted_input_count}个，删除输出图片: {deleted_output_count}个")

        return jsonify({
            'success': True,
            'message': f'成功删除 {deleted_count} 个今日前的任务，同时清理了 {total_deleted_files} 个图片文件',
            'data': {
                'deleted_count': deleted_count,
                'deleted_input_count': deleted_input_count,
                'deleted_output_count': deleted_output_count,
                'deleted_files_count': total_deleted_files
            }
        })

    except Exception as e:
        print(f"删除今日前任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'删除今日前任务失败: {str(e)}'
        }), 500