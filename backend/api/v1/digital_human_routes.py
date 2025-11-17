"""
即梦数字人任务管理API
"""

import os
import tempfile
import uuid
import platform
import subprocess
import threading
from datetime import datetime, date
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from backend.models.models import JimengDigitalHumanTask, JimengAccount

# 创建蓝图
jimeng_digital_human_bp = Blueprint('jimeng_digital_human', __name__, url_prefix='/api/jimeng/digital-human')

@jimeng_digital_human_bp.route('/tasks', methods=['GET'])
def get_tasks():
    """获取数字人任务列表"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 1000))
        status_filter = request.args.get('status', 'all')
        
        # 构建查询
        query = JimengDigitalHumanTask.select()
        
        if status_filter != 'all':
            try:
                status_value = int(status_filter)
                query = query.where(JimengDigitalHumanTask.status == status_value)
            except ValueError:
                pass
        
        # 获取总数
        total = query.count()
        
        # 分页查询
        tasks = (query.order_by(JimengDigitalHumanTask.create_at.desc())
                .paginate(page, per_page))
        
        # 转换为字典列表
        task_list = []
        for task in tasks:
            # 获取账号信息
            account_info = None
            if task.account_id:
                try:
                    account = JimengAccount.get_by_id(task.account_id)
                    account_info = account.account
                except:
                    account_info = f"账号ID:{task.account_id}"
            
            task_dict = {
                'id': task.id,
                'image_path': task.image_path,
                'audio_path': task.audio_path,
                'action_description': task.action_description,  # 动作描述
                'status': task.status,
                'account_id': task.account_id,
                'account_info': account_info,
                'create_at': task.create_at.isoformat() if task.create_at else None,
                'start_time': task.start_time.isoformat() if task.start_time else None,
                'video_url': task.video_url,
                'failure_reason': task.failure_reason,  # 失败原因类型
                'error_message': task.error_message,  # 详细错误信息
            }
            task_list.append(task_dict)
        
        return jsonify({
            'success': True,
            'data': {
                'tasks': task_list,
                'total': total,
                'page': page,
                'per_page': per_page
            }
        })
        
    except Exception as e:
        print(f"获取数字人任务列表失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取任务列表失败: {str(e)}'
        }), 500

@jimeng_digital_human_bp.route('/tasks', methods=['POST'])
def create_task():
    """创建数字人任务"""
    try:
        # 检查文件上传
        if 'image' not in request.files or 'audio' not in request.files:
            return jsonify({
                'success': False,
                'message': '请同时上传图片和音频文件'
            }), 400
        
        image_file = request.files['image']
        audio_file = request.files['audio']
        
        if image_file.filename == '' or audio_file.filename == '':
            return jsonify({
                'success': False,
                'message': '请选择有效的图片和音频文件'
            }), 400
        
        # 创建tmp目录（在后端根目录下）
        import os
        from pathlib import Path
        
        # 获取后端根目录
        backend_root = Path(__file__).parent.parent.parent  # 从api/v1/ 向上两级到backend/
        tmp_dir = backend_root / 'tmp'
        tmp_dir.mkdir(exist_ok=True)
        
        # 生成唯一文件名
        image_ext = os.path.splitext(image_file.filename)[1]
        audio_ext = os.path.splitext(audio_file.filename)[1]
        
        unique_id = str(uuid.uuid4())
        image_filename = f"{unique_id}_image{image_ext}"
        audio_filename = f"{unique_id}_audio{audio_ext}"
        
        # 保存文件到tmp目录
        image_path = tmp_dir / image_filename
        audio_path = tmp_dir / audio_filename
        
        image_file.save(str(image_path))
        audio_file.save(str(audio_path))
        
        print(f"保存图片文件: {image_path}")
        print(f"保存音频文件: {audio_path}")
        
        # 获取动作描述（可选）
        action_description = request.form.get('action_description', '').strip()

        # 创建任务记录
        task = JimengDigitalHumanTask.create(
            image_path=str(image_path),
            audio_path=str(audio_path),
            action_description=action_description if action_description else None,
            status=0,  # 排队中
            create_at=datetime.now()
        )

          
        return jsonify({
            'success': True,
            'message': '数字人任务创建成功',
            'data': {
                'task_id': task.id
            }
        })
        
    except Exception as e:
        print(f"创建数字人任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'创建任务失败: {str(e)}'
        }), 500

@jimeng_digital_human_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除数字人任务"""
    try:
        task = JimengDigitalHumanTask.get_by_id(task_id)

        # 删除任务相关的文件副本（保存在tmp目录中的副本，不影响用户原始文件）
        deleted_files_count = 0
        try:
            if task.image_path and os.path.exists(task.image_path):
                # 确认删除的是tmp目录中的副本文件
                if 'tmp' in task.image_path:
                    os.remove(task.image_path)
                    deleted_files_count += 1
                    print(f"删除图片副本文件: {task.image_path}")
                else:
                    print(f"警告：检测到非tmp目录文件，为保护用户原始数据跳过删除: {task.image_path}")
            if task.audio_path and os.path.exists(task.audio_path):
                # 确认删除的是tmp目录中的副本文件
                if 'tmp' in task.audio_path:
                    os.remove(task.audio_path)
                    deleted_files_count += 1
                    print(f"删除音频副本文件: {task.audio_path}")
                else:
                    print(f"警告：检测到非tmp目录文件，为保护用户原始数据跳过删除: {task.audio_path}")
        except Exception as e:
            print(f"删除文件失败: {str(e)}")

        # 删除任务记录
        task.delete_instance()

        print(f"删除数字人任务: {task_id}，清理副本文件: {deleted_files_count}个")
        return jsonify({
            'success': True,
            'message': f'任务删除成功，同时清理了 {deleted_files_count} 个临时副本文件（不影响您的原始文件）',
            'data': {
                'deleted_files_count': deleted_files_count
            }
        })

    except JimengDigitalHumanTask.DoesNotExist:
        return jsonify({
            'success': False,
            'message': '任务不存在'
        }), 404
    except Exception as e:
        print(f"删除数字人任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'删除任务失败: {str(e)}'
        }), 500

@jimeng_digital_human_bp.route('/tasks/<int:task_id>/retry', methods=['POST'])
def retry_task(task_id):
    """重试数字人任务"""
    try:
        task = JimengDigitalHumanTask.get_by_id(task_id)
        
        # 重置任务状态
        task.status = 0  # 排队中
        task.account_id = None
        task.start_time = None
        task.video_url = None
        task.save()
        
        return jsonify({
            'success': True,
            'message': '任务已重新排队'
        })
        
    except JimengDigitalHumanTask.DoesNotExist:
        return jsonify({
            'success': False,
            'message': '任务不存在'
        }), 404
    except Exception as e:
        print(f"重试数字人任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'重试任务失败: {str(e)}'
        }), 500

@jimeng_digital_human_bp.route('/tasks/batch-retry', methods=['POST'])
def batch_retry_tasks():
    """批量重试失败任务"""
    try:
        data = request.get_json()
        task_ids = data.get('task_ids', [])
        
        if not task_ids:
            # 重试所有失败的任务
            failed_tasks = JimengDigitalHumanTask.select().where(JimengDigitalHumanTask.status == 3)
        else:
            # 重试指定的任务
            failed_tasks = JimengDigitalHumanTask.select().where(JimengDigitalHumanTask.id.in_(task_ids))
        
        retry_count = 0
        for task in failed_tasks:
            task.status = 0  # 排队中
            task.account_id = None
            task.start_time = None
            task.video_url = None
            task.save()
            retry_count += 1
        
        return jsonify({
            'success': True,
            'message': f'已重试 {retry_count} 个任务'
        })
        
    except Exception as e:
        print(f"批量重试数字人任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'批量重试失败: {str(e)}'
        }), 500

@jimeng_digital_human_bp.route('/tasks/batch-delete', methods=['POST'])
def batch_delete_tasks():
    """批量删除任务"""
    try:
        data = request.get_json()
        task_ids = data.get('task_ids', [])

        if not task_ids:
            return jsonify({
                'success': False,
                'message': '请选择要删除的任务'
            }), 400

        # 获取要删除的任务
        tasks = JimengDigitalHumanTask.select().where(JimengDigitalHumanTask.id.in_(task_ids))

        delete_count = 0
        deleted_files_count = 0
        error_count = 0

        for task in tasks:
            # 删除任务相关的文件副本（保存在tmp目录中的副本，不影响用户原始文件）
            try:
                if task.image_path and os.path.exists(task.image_path):
                    # 确认删除的是tmp目录中的副本文件
                    if 'tmp' in task.image_path:
                        os.remove(task.image_path)
                        deleted_files_count += 1
                        print(f"删除图片副本文件: {task.image_path}")
                    else:
                        print(f"警告：检测到非tmp目录文件，为保护用户原始数据跳过删除: {task.image_path}")
                if task.audio_path and os.path.exists(task.audio_path):
                    # 确认删除的是tmp目录中的副本文件
                    if 'tmp' in task.audio_path:
                        os.remove(task.audio_path)
                        deleted_files_count += 1
                        print(f"删除音频副本文件: {task.audio_path}")
                    else:
                        print(f"警告：检测到非tmp目录文件，为保护用户原始数据跳过删除: {task.audio_path}")
            except Exception as e:
                print(f"删除任务 {task.id} 的副本文件时出错: {str(e)}")
                error_count += 1

            # 删除任务记录
            task.delete_instance()
            delete_count += 1

        print(f"批量删除数字人任务: {delete_count}个，清理副本文件: {deleted_files_count}个，错误: {error_count}个")
        return jsonify({
            'success': True,
            'message': f'成功删除 {delete_count} 个任务，同时清理了 {deleted_files_count} 个临时副本文件（不影响您的原始文件）',
            'data': {
                'deleted_tasks': delete_count,
                'deleted_files_count': deleted_files_count,
                'error_count': error_count
            }
        })

    except Exception as e:
        print(f"批量删除数字人任务失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'批量删除失败: {str(e)}'
        }), 500

@jimeng_digital_human_bp.route('/tasks/batch-download', methods=['POST'])
def batch_download_videos():
    """批量下载数字人视频"""
    try:
        data = request.get_json()
        task_ids = data.get('task_ids', [])
        
        if not task_ids:
            return jsonify({
                'success': False,
                'message': '请选择要下载的任务'
            }), 400
        
        print(f"数字人批量下载任务，任务ID: {task_ids}")
        
        def select_folder_and_download():
            try:
                # 调用原生文件夹选择对话框
                folder_path = None
                system = platform.system()
                
                if system == "Darwin":  # macOS
                    result = subprocess.run([
                        'osascript', '-e',
                        'tell application "Finder" to set folder_path to (choose folder with prompt "选择视频保存文件夹") as string',
                        '-e',
                        'return POSIX path of folder_path'
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0 and result.stdout.strip():
                        folder_path = result.stdout.strip()
                        
                elif system == "Windows":  # Windows
                    print("正在调用Windows文件选择器...")
                    ps_script = """
                    try {
                        Add-Type -AssemblyName System.Windows.Forms
                        $folderBrowser = New-Object System.Windows.Forms.FolderBrowserDialog
                        $folderBrowser.Description = "选择视频保存文件夹"
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
                        folder_path = result.stdout.strip()
                        print(f"用户选择了文件夹: {folder_path}")
                    elif result.returncode == 1:
                        print("用户取消了文件夹选择")
                        return
                        
                elif system == "Linux":  # Linux
                    result = subprocess.run([
                        'zenity', '--file-selection', '--directory',
                        '--title=选择视频保存文件夹'
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0 and result.stdout.strip():
                        folder_path = result.stdout.strip()
                
                if not folder_path:
                    print("用户取消了文件夹选择")
                    return
                
                print(f"选择的保存文件夹: {folder_path}")
                
                if not os.path.exists(folder_path):
                    print(f"文件夹不存在: {folder_path}")
                    return
                
                # 获取要下载的任务
                tasks = JimengDigitalHumanTask.select().where(
                    JimengDigitalHumanTask.id.in_(task_ids),
                    JimengDigitalHumanTask.status == 2,  # 已完成
                    JimengDigitalHumanTask.video_url.is_null(False)  # 有视频URL
                )
                
                # 准备下载信息
                file_infos = []
                for task in tasks:
                    if task.video_url:
                        filename = f"digital_human_task_{task.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                        file_infos.append({
                            'url': task.video_url,
                            'file_path': os.path.join(folder_path, filename),
                            'filename': filename
                        })
                
                if not file_infos:
                    print("没有可下载的视频")
                    return
                
                # 使用带重试机制的批量下载（支持并行）
                from utils.download_util import batch_download_files
                download_result = batch_download_files(
                    file_infos=file_infos,
                    max_retries=5,
                    timeout=60,
                    max_workers=5  # 并行下载数
                )
                
                download_count = download_result['success_count']
                
                print(f"批量下载完成，成功下载 {download_count} 个视频")
                
            except Exception as e:
                print(f"批量下载处理失败: {str(e)}")
        
        # 在后台线程中执行文件选择和下载
        thread = threading.Thread(target=select_folder_and_download)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': '开始选择保存文件夹并下载，请在弹出的对话框中选择保存位置'
        })
        
    except Exception as e:
        print(f"批量下载数字人视频失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'批量下载失败: {str(e)}'
        }), 500

@jimeng_digital_human_bp.route('/tasks/delete-before-today', methods=['DELETE'])
def delete_tasks_before_today():
    """删除今日前的所有数字人任务"""
    try:
        from datetime import datetime, timedelta
        import pytz

        # 获取今日开始时间（凌晨0点）
        beijing_tz = pytz.timezone('Asia/Shanghai')
        today_start = datetime.now(beijing_tz).replace(hour=0, minute=0, second=0, microsecond=0)

        # 查询今日前的任务
        before_today_tasks = JimengDigitalHumanTask.select().where(
            JimengDigitalHumanTask.create_at < today_start
        )

        count = before_today_tasks.count()

        if count == 0:
            return jsonify({
                'success': True,
                'message': '没有今日前的任务需要删除',
                'data': {'deleted_count': 0, 'deleted_files_count': 0}
            })

        # 删除关联的文件
        deleted_files_count = 0
        for task in before_today_tasks:
            try:
                if task.image_path and os.path.exists(task.image_path):
                    os.remove(task.image_path)
                    deleted_files_count += 1
                    print(f"删除图片文件: {task.image_path}")
                if task.audio_path and os.path.exists(task.audio_path):
                    os.remove(task.audio_path)
                    deleted_files_count += 1
                    print(f"删除音频文件: {task.audio_path}")
            except Exception as file_error:
                print(f"删除任务 {task.id} 的文件时出错: {str(file_error)}")

        # 删除任务
        deleted_count = JimengDigitalHumanTask.delete().where(
            JimengDigitalHumanTask.create_at < today_start
        ).execute()

        print(f"删除了 {deleted_count} 个今日前的数字人任务，删除文件: {deleted_files_count}个")

        return jsonify({
            'success': True,
            'message': f'成功删除 {deleted_count} 个今日前的任务，同时清理了 {deleted_files_count} 个文件',
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

@jimeng_digital_human_bp.route('/tasks/batch-create-from-table', methods=['POST'])
def batch_create_tasks_from_table():
    """从表格批量创建数字人任务"""
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
                if 'audio_path' not in task_data or not task_data['audio_path']:
                    failed_tasks.append(f"第 {i+1} 行: 缺少音频路径")
                    continue

                image_path = task_data['image_path'].strip()
                audio_path = task_data['audio_path'].strip()

                # 验证文件路径是否存在（如果是本地文件路径）
                is_url = image_path.startswith(('http://', 'https://')) or audio_path.startswith(('http://', 'https://'))
                
                if not is_url:
                    # 如果不是URL，则检查本地文件是否存在
                    if not os.path.exists(image_path):
                        failed_tasks.append(f"第 {i+1} 行: 图片文件不存在 - {image_path}")
                        continue
                    if not os.path.exists(audio_path):
                        failed_tasks.append(f"第 {i+1} 行: 音频文件不存在 - {audio_path}")
                        continue

                # 获取动作描述（可选）
                action_description = task_data.get('action_description', '').strip() if task_data.get('action_description') else None

                # 创建任务
                task = JimengDigitalHumanTask.create(
                    image_path=image_path,
                    audio_path=audio_path,
                    action_description=action_description if action_description else None,
                    status=0,  # 排队中
                    create_at=datetime.now()
                )
                created_tasks.append(task.id)
                print(f"从表格创建数字人任务: {task.id}, 图片: {image_path}, 音频: {audio_path}")

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


@jimeng_digital_human_bp.route('/tasks/single-download', methods=['POST'])
def single_download_video():
    """单个下载数字人视频"""
    try:
        data = request.get_json()
        video_url = data.get('video_url')
        filename = data.get('filename', f"digital_human_{uuid.uuid4()}.mp4")

        if not video_url:
            return jsonify({'success': False, 'message': '缺少 video_url 参数'}), 400

        def select_folder_and_download_single():
            try:
                folder_path = None
                system = platform.system()
                
                if system == "Windows":
                    ps_script = """
                    Add-Type -AssemblyName System.Windows.Forms
                    $folderBrowser = New-Object System.Windows.Forms.FolderBrowserDialog
                    $folderBrowser.Description = "选择视频保存文件夹"
                    $result = $folderBrowser.ShowDialog()
                    if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
                        return $folderBrowser.SelectedPath
                    }
                    return ''
                    """
                    result = subprocess.run(['powershell', '-Command', ps_script], capture_output=True, text=True, timeout=60)
                    if result.returncode == 0 and result.stdout.strip():
                        folder_path = result.stdout.strip()
                
                if not folder_path:
                    print("用户取消了文件夹选择")
                    return

                file_path = os.path.join(folder_path, filename)
                
                from utils.download_util import download_single_file
                download_single_file(video_url, file_path)
                print(f"视频下载成功: {file_path}")

            except Exception as e:
                print(f"单个视频下载处理失败: {str(e)}")

        thread = threading.Thread(target=select_folder_and_download_single)
        thread.daemon = True
        thread.start()

        return jsonify({'success': True, 'message': '开始选择保存文件夹并下载'})

    except Exception as e:
        print(f"单个下载数字人视频失败: {str(e)}")
        return jsonify({'success': False, 'message': f'单个下载失败: {str(e)}'}), 500

@jimeng_digital_human_bp.route('/stats', methods=['GET'])
def get_stats():
    """获取数字人任务统计"""
    try:
        today = date.today()
        
        # 获取统计数据
        total = JimengDigitalHumanTask.select().count()
        today_count = JimengDigitalHumanTask.select().where(
            JimengDigitalHumanTask.create_at >= today
        ).count()
        in_progress = JimengDigitalHumanTask.select().where(JimengDigitalHumanTask.status == 1).count()
        completed = JimengDigitalHumanTask.select().where(JimengDigitalHumanTask.status == 2).count()
        failed = JimengDigitalHumanTask.select().where(JimengDigitalHumanTask.status == 3).count()
        
        return jsonify({
            'success': True,
            'data': {
                'total': total,
                'today': today_count,
                'in_progress': in_progress,
                'completed': completed,
                'failed': failed
            }
        })
        
    except Exception as e:
        print(f"获取数字人任务统计失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'获取统计失败: {str(e)}'
        }), 500

@jimeng_digital_human_bp.route('/cleanup-orphaned-files', methods=['DELETE'])
def cleanup_orphaned_digital_human_files():
    """清理孤立的数字人文件（没有关联任务的图片和音频）"""
    try:
        # 获取项目中所有存储的文件路径
        all_tasks = JimengDigitalHumanTask.select()
        used_file_paths = set()

        for task in all_tasks:
            if task.image_path:
                used_file_paths.add(task.image_path)
            if task.audio_path:
                used_file_paths.add(task.audio_path)

        # 获取项目根目录
        from pathlib import Path
        backend_root = Path(__file__).parent.parent.parent
        tmp_dir = backend_root / 'tmp'

        deleted_files_count = 0
        error_count = 0

        # 检查tmp目录
        if tmp_dir.exists():
            for filename in os.listdir(str(tmp_dir)):
                file_path = tmp_dir / filename
                if file_path.is_file():
                    # 检查文件是否为图片或音频文件
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.mp3', '.wav', '.m4a', '.aac', '.ogg')):
                        # 检查文件是否被任何任务使用
                        if str(file_path) not in used_file_paths:
                            try:
                                os.remove(str(file_path))
                                deleted_files_count += 1
                                print(f"删除孤立文件: {file_path}")
                            except Exception as e:
                                error_count += 1
                                print(f"删除孤立文件失败: {file_path}, 错误: {str(e)}")

        print(f"清理数字人孤立文件完成: 删除 {deleted_files_count} 个文件，失败 {error_count} 个")

        return jsonify({
            'success': True,
            'message': f'清理完成，删除了 {deleted_files_count} 个孤立文件',
            'data': {
                'deleted_count': deleted_files_count,
                'error_count': error_count,
                'total_used_files': len(used_file_paths)
            }
        })

    except Exception as e:
        print(f"清理孤立文件失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'清理孤立文件失败: {str(e)}'
        }), 500
