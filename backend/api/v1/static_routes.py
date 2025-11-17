# -*- coding: utf-8 -*-
"""
静态文件服务路由
"""
import os
import requests
from flask import Blueprint, send_file, request, redirect, Response
from urllib.parse import unquote
import re

# 创建蓝图
static_bp = Blueprint('static', __name__)

@static_bp.route('/static/first-last-frame-images/<path:filename>')
def serve_first_last_frame_image(filename):
    """
    提供首尾帧图片文件服务
    """
    try:
        # 解码URL
        filename = unquote(filename)

        # 获取项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        # 首先尝试在tmp/first_last_frame_upload目录中查找
        tmp_first_last_path = os.path.join(project_root, 'tmp', 'first_last_frame_upload', filename)
        if os.path.exists(tmp_first_last_path) and os.path.isfile(tmp_first_last_path):
            print(f"找到首尾帧图片文件: {tmp_first_last_path}")
            return send_file(tmp_first_last_path)

        # 尝试在tmp目录中查找
        tmp_path = os.path.join(project_root, 'tmp', filename)
        if os.path.exists(tmp_path) and os.path.isfile(tmp_path):
            print(f"找到首尾帧图片文件: {tmp_path}")
            return send_file(tmp_path)

        # 尝试在static/first-last-frame-images目录中查找
        static_first_last_path = os.path.join(project_root, 'static', 'first-last-frame-images', filename)
        if os.path.exists(static_first_last_path) and os.path.isfile(static_first_last_path):
            print(f"找到静态首尾帧图片文件: {static_first_last_path}")
            return send_file(static_first_last_path)

        # 如果都没找到，返回404
        print(f"首尾帧图片未找到: {filename}")
        return {'success': False, 'message': 'Image not found'}, 404

    except Exception as e:
        print(f"Serve first last frame image error: {str(e)}")
        return {'success': False, 'message': 'Server error'}, 500

@static_bp.route('/static/images/<path:filename>')
def serve_image(filename):
    """
    提供图片文件服务，支持本地文件和远程URL
    """
    try:
        # 解码URL
        filename = unquote(filename)
        
        # 检查是否为完整URL格式（包含http://或https://）
        if filename.startswith(('http://', 'https://')):
            # 如果是远程URL，直接重定向
            return redirect(filename)
        
        # 特殊处理：如果路径中包含盘符（如 C:/...），提取文件名
        if re.match(r'^[A-Za-z]:[/\\]', filename):
            # 这是一个Windows绝对路径，提取文件名
            actual_filename = os.path.basename(filename)
        else:
            # 从URL中提取实际的文件名，移除查询参数等
            # 例如 a8976b5e59e845f282b68f2da44e8d69~tplv-wopfjsm1ax-aigc_resize:0:0.jpeg?lk3s=43402efa&x-expires=1761264000&x-signature=I7Nn9sS1wwpJ4RmtHs%2B318decYQ%3D&format=.jpeg
            # 提取 a8976b5e59e845f282b68f2da44e8d69~tplv-wopfjsm1ax-aigc_resize:0:0.jpeg
            actual_filename = filename.split('?')[0]
        
        # 获取项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # 检查文件名是否包含路径遍历
        if '..' in actual_filename or actual_filename.startswith('/'):
            return {'success': False, 'message': 'Invalid file path'}, 400
        
        # 首先尝试在tmp目录中查找原文件名
        tmp_images_path = os.path.join(project_root, 'tmp', actual_filename)
        if os.path.exists(tmp_images_path) and os.path.isfile(tmp_images_path):
            print(f"找到图片文件: {tmp_images_path}")
            return send_file(tmp_images_path)
        
        # 如果没找到，尝试从文件名中提取可能的UUID部分
        # 即梦平台生成的图片URL通常以UUID开头
        # 例如 a8976b5e59e845f282b68f2da44e8d69~tplv-wopfjsm1ax-aigc_resize:0:0.jpeg
        # 其中的 a8976b5e59e845f282b68f2da44e8d69 是主要文件名
        uuid_part_match = re.match(r'^([a-fA-F0-9]{32})', actual_filename)
        if uuid_part_match:
            uuid_part = uuid_part_match.group(1)
            
            # 尝试在tmp目录中查找UUID部分的文件
            for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                tmp_path = os.path.join(project_root, 'tmp', uuid_part + ext)
                if os.path.exists(tmp_path) and os.path.isfile(tmp_path):
                    print(f"找到图片文件 (UUID匹配): {tmp_path}")
                    return send_file(tmp_path)
            
            # 再次查找不带扩展名的文件
            tmp_path = os.path.join(project_root, 'tmp', uuid_part)
            if os.path.exists(tmp_path) and os.path.isfile(tmp_path):
                print(f"找到图片文件 (UUID无扩展名): {tmp_path}")
                return send_file(tmp_path)
        
        # 尝试在tmp目录中的所有文件中查找包含主文件名的文件
        try:
            tmp_dir = os.path.join(project_root, 'tmp')
            if os.path.exists(tmp_dir):
                for file in os.listdir(tmp_dir):
                    file_path = os.path.join(tmp_dir, file)
                    if os.path.isfile(file_path):
                        # 检查文件名是否包含UUID部分
                        if uuid_part_match and uuid_part_match.group(1) in file:
                            print(f"找到匹配的图片文件 (通过UUID匹配): {file_path}")
                            return send_file(file_path)
                        # 或者检查是否包含原始文件名中的主要部分
                        elif actual_filename.split('~')[0] in file or actual_filename.split('.')[0] in file:
                            print(f"找到匹配的图片文件 (通过主文件名匹配): {file_path}")
                            return send_file(file_path)
        except Exception as e:
            print(f"扫描tmp目录时出错: {str(e)}")
        
        # 如果在tmp目录中没找到，尝试在static/images目录中查找
        static_images_path = os.path.join(project_root, 'static', 'images', actual_filename)
        if os.path.exists(static_images_path) and os.path.isfile(static_images_path):
            print(f"找到静态图片文件: {static_images_path}")
            return send_file(static_images_path)
        
        # 如果本地文件都没找到，尝试将文件名作为URL访问（可能是即梦平台返回的完整URL）
        full_url = actual_filename
        if actual_filename.startswith('http'):
            try:
                # 发起请求获取图片内容
                response = requests.get(full_url, stream=True, timeout=30)
                if response.status_code == 200:
                    # 返回远程图片内容
                    return Response(
                        response.iter_content(chunk_size=1024),
                        mimetype=response.headers.get('content-type', 'image/jpeg'),
                        headers={
                            'Content-Disposition': f'inline; filename="{actual_filename.split("/")[-1]}"',
                            'Cache-Control': 'max-age=3600'
                        }
                    )
            except Exception as e:
                print(f"获取远程图片失败: {str(e)}")
        
        # 如果都没找到，返回404
        print(f"Image not found: {filename}, actual: {actual_filename}, uuid_part: {uuid_part_match.group(1) if uuid_part_match else 'N/A'}")
        return {'success': False, 'message': 'Image not found'}, 404
        
    except Exception as e:
        print(f"Serve image error: {str(e)}")
        return {'success': False, 'message': 'Server error'}, 500