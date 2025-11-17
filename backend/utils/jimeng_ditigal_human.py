"""
即梦平台自动化模块 - 数字人生成
based on BaseTaskExecutor refactoring version
"""

import asyncio
import time
from typing import Optional, List, Dict, Any
from backend.utils.base_task_executor import BaseTaskExecutor, TaskResult, ErrorCode, TaskLogger

class JimengDigitalHumanExecutor(BaseTaskExecutor):
    """即梦数字人生成执行器"""
    
    def __init__(self, headless: bool = False):
        super().__init__(headless)
        self.task_id = None
        self.video_url = None
        self.generation_completed = False
    
    async def handle_cookies(self, cookies: str):
        """处理cookies字符串格式"""
        try:
            # 将cookies字符串转换为字典列表格式
            cookie_pairs = cookies.split('; ')
            cookie_list = []
            for pair in cookie_pairs:
                if '=' in pair:
                    name, value = pair.split('=', 1)
                    cookie_list.append({
                        'name': name.strip(),
                        'value': value.strip(),
                        'domain': '.capcut.com',
                        'path': '/'
                    })
            
            await self.context.add_cookies(cookie_list)
            self.logger.info("即梦平台cookies设置成功")
            
        except Exception as e:
            self.logger.error("设置即梦平台cookies时出错", error=str(e))
            
    async def perform_login(self, username: str, password: str) -> TaskResult:
        """执行登录流程"""
        try:
            self.logger.info("开始登录即梦平台", username=username)
            
            await self.page.goto('https://dreamina.capcut.com/en-us', timeout=60000)
            await asyncio.sleep(2)
            
            # 点击语言切换按钮
            self.logger.info("点击语言切换按钮")
            await self.page.click('button.dreamina-header-secondary-button')
            await asyncio.sleep(1)
            
            # 点击切换为英文
            self.logger.info("切换为英文")
            await self.page.click('div.language-item:has-text("English")')
            await asyncio.sleep(2)
            
            # 检查并关闭可能出现的弹窗
            try:
                self.logger.info("检查是否有弹窗需要关闭")
                close_button = await self.page.query_selector('img.close-icon')
                if close_button:
                    self.logger.info("关闭弹窗")
                    await close_button.click()
                    await asyncio.sleep(1)
            except Exception as e:
                self.logger.debug("没有发现需要关闭的弹窗", error=str(e))
            
            # 点击登录按钮
            self.logger.info("点击登录按钮")
            await self.page.click('#loginButton')
            await asyncio.sleep(2)
            
            # 等待登录页面加载
            await self.page.wait_for_selector('.lv-checkbox-mask', timeout=60000)
            await asyncio.sleep(2)
            
            # 勾选同意条款复选框
            self.logger.info("勾选同意条款")
            await self.page.click('.lv-checkbox-mask')
            await asyncio.sleep(2)
            
            # 点击登录按钮
            await self.page.click('div[class^="login-button-"]:has-text("Sign in")')
            await asyncio.sleep(2)
            
            # 点击使用邮箱登录
            self.logger.info("选择邮箱登录方式")
            await self.page.click('span.lv_new_third_part_sign_in_expand-label:has-text("Continue with Email")')
            await asyncio.sleep(2)
            
            # 输入账号密码
            self.logger.info("输入账号密码")
            await self.page.fill('input[placeholder="Enter email"]', username)
            await asyncio.sleep(2)
            await self.page.fill('input[type="password"]', password)
            await asyncio.sleep(2)
            
            # 点击登录
            self.logger.info("点击登录按钮")
            await self.page.click('.lv_new_sign_in_panel_wide-sign-in-button')
            await asyncio.sleep(2)
            
            # 等待登录完成
            self.logger.info("等待登录完成")
            # 实现等待登录完成，如果10秒后还是没反应就刷新下界面，依旧最多等待30秒
            login_complete = False
            start_wait_time = time.time()
            
            # 检查登录是否完成，最多等待30秒
            while not login_complete and (time.time() - start_wait_time) < 30:
                try:
                    # 使用较短的超时时间来检测页面加载
                    await self.page.wait_for_load_state('networkidle', timeout=10000)
                    
                    # 检查URL是否已经跳转为主页面，表示登录完成
                    current_url = self.page.url
                    if "dreamina.capcut.com" in current_url and "login" not in current_url:
                        self.logger.info("检测到登录成功，已跳转到主页面")
                        login_complete = True
                        break
                    else:
                        # 如果尚未跳转，等待一段时间后继续检查
                        await asyncio.sleep(2)
                except:
                    self.logger.info("等待登录超时，刷新页面")
                    await self.page.reload()
                    await asyncio.sleep(2)
                    
                    # 检查URL是否已经跳转为主页面，表示登录完成
                    current_url = self.page.url
                    if "dreamina.capcut.com" in current_url and "login" not in current_url:
                        self.logger.info("检测到登录成功，已跳转到主页面")
                        login_complete = True
                        break
            
            # 检查是否有确认按钮，如果有则点击
            self.logger.info("检查是否需要确认")
            try:
                confirm_button = await self.page.query_selector('button:has-text("Confirm")')
                if confirm_button:
                    self.logger.info("检测到确认按钮，点击确认")
                    await confirm_button.click()
                    await asyncio.sleep(2)
            except Exception as e:
                self.logger.debug("没有确认按钮，跳过", error=str(e))
            
            return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="登录成功")
            
        except Exception as e:
            self.logger.error("登录失败", error=str(e))
            return TaskResult(
                code=ErrorCode.WEB_INTERACTION_FAILED.value,
                data=None,
                message="登录失败",
                error_details={"error": str(e)}
            )
    
    async def validate_login_success(self) -> TaskResult:
        """验证登录是否成功"""
        try:
            # 增加等待时间，让页面有足够时间完成跳转
            await asyncio.sleep(2)
            current_url = self.page.url
            if "dreamina.capcut.com" in current_url and "login" not in current_url:
                self.logger.info("登录验证成功")
                return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="登录验证成功")
            else:
                self.logger.error("登录验证失败", current_url=current_url)
                return TaskResult(
                    code=ErrorCode.WEB_INTERACTION_FAILED.value,
                    data=None,
                    message="登录验证失败，页面跳转异常"
                )
        except Exception as e:
            self.logger.error("登录验证异常", error=str(e))
            return TaskResult(
                code=ErrorCode.WEB_INTERACTION_FAILED.value,
                data=None,
                message="登录验证异常",
                error_details={"error": str(e)}
            )


    async def check_login_status(self) -> TaskResult:
        """检查登录状态，如果有登录按钮说明cookies过期"""
        try:
            self.logger.info("检查登录状态")
            
            # 跳转到主页面
            await self.page.goto('https://dreamina.capcut.com/ai-tool/home/en-us', timeout=60000)
            await asyncio.sleep(3)
            self.logger.info("等待3秒后刷新页面")
            await self.page.reload(timeout=60000)
            await self.page.wait_for_load_state('networkidle', timeout=60000)
            await asyncio.sleep(3)
            
            # 检查是否存在登录按钮
            login_button = await self.page.query_selector('div[class*="login-button"]:has-text("Sign in")')
            if login_button:
                self.logger.warning("检测到登录按钮，cookies已过期")
                return TaskResult(
                    code=600,
                    data=None,
                    message="cookies已过期，需要重新登录",
                    cookies=""
                )
            
            self.logger.info("登录状态正常")
            return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="登录状态正常")
            
        except Exception as e:
            self.logger.error("检查登录状态时出错", error=str(e))
            return TaskResult(
                code=ErrorCode.WEB_INTERACTION_FAILED.value,
                data=None,
                message="检查登录状态失败",
                error_details={"error": str(e)}
            )


    async def navigate_to_digital_human_page(self) -> TaskResult:
        """跳转到数字人生成页面"""
        try:
            self.logger.info("正在跳转到数字人生成页面")
            await self.page.goto('https://dreamina.capcut.com/ai-tool/generate')
            await self.page.wait_for_load_state('networkidle', timeout=60000)
            await asyncio.sleep(2)
            
            # 检测并处理弹窗 - 检测可能存在的多种弹窗类型，不区分先后顺序
            self.logger.info("页面已跳转，检测是否有弹窗")
            
            # 检测第二种弹窗 - 问卷调查弹窗
            survey_popup_selector = 'div.lv-modal-content'
            
            # 检测第一种弹窗 - 应用下载弹窗
            popup_selector = 'div.app-download-container-rH5mzB'
            
            # 检查并处理第二种弹窗
            survey_popup_element = await self.page.query_selector(survey_popup_selector)
            if survey_popup_element:
                try:
                    # 查找关闭按钮，根据提供的HTML结构，关闭按钮在 'div.close-btn-JxU6Mw' 中
                    survey_close_button = await self.page.query_selector('div.close-btn-JxU6Mw')
                    if survey_close_button:
                        await survey_close_button.click()
                        self.logger.info("已点击第二种弹窗关闭按钮")
                        await asyncio.sleep(2)
                    else:
                        # 检查是否有"Continue to Dreamina"按钮，可以选择一个选项然后继续
                        continue_button = await self.page.query_selector('button.submit-NVxHv4')
                        if continue_button:
                            # 点击第一个选项"Art professional"
                            first_option = await self.page.query_selector('div.question-option-D0gxAX')
                            if first_option:
                                await first_option.click()
                                await asyncio.sleep(1)
                                # 再次点击继续按钮
                                await continue_button.click()
                                self.logger.info("已通过选择选项并点击继续按钮关闭第二种弹窗")
                                await asyncio.sleep(2)
                except Exception as e:
                    # 静默处理异常，不输出警告
                    pass
            
            # 检查并处理第一种弹窗
            popup_element = await self.page.query_selector(popup_selector)
            if popup_element:
                try:
                    # 尝试点击关闭按钮（X按钮）
                    close_button = await self.page.query_selector('div.close-button-tXOdin')
                    if close_button:
                        await close_button.click()
                        self.logger.info("已点击第一种弹窗关闭按钮")
                        await asyncio.sleep(2)
                    else:
                        # 如果没有关闭按钮，点击Copy link按钮
                        copy_link_button = await self.page.query_selector('button.lv-btn.lv-btn-primary.lv-btn-size-default.lv-btn-shape-square.app-download-button-gIF_OD')
                        if copy_link_button:
                            await copy_link_button.click()
                            self.logger.info("已点击Copy link按钮")
                            await asyncio.sleep(2)
                except Exception as e:
                    # 静默处理异常，不输出警告
                    pass
            
            self.logger.info("弹窗检测和处理完成，继续执行")
            
            # 检查是否存在标签页模式的AI Avatar按钮
            self.logger.info("检查页面模式")
            try:
                # 先尝试查找标签页模式的AI Avatar按钮
                ai_avatar_tab = await self.page.query_selector('button[class*="tab-"]:has-text("AI Avatar")')
                if ai_avatar_tab:
                    self.logger.info("发现标签页模式，点击AI Avatar标签")
                    await ai_avatar_tab.click()
                    await asyncio.sleep(2)
                else:
                    # 如果没有标签页模式，使用下拉框模式
                    self.logger.info("使用下拉框模式，点击类型选择下拉框")
                    await self.page.click('div.lv-select[role="combobox"]')
                    await asyncio.sleep(1)
                    
                    # 选择AI Avatar选项
                    self.logger.info("选择AI Avatar选项")
                    await self.page.click('span[class^="select-option-label-content"]:has-text("AI Avatar")')
                    await asyncio.sleep(2)
            except Exception as e:
                self.logger.error("选择AI Avatar失败", error=str(e))
                return TaskResult(
                    code=ErrorCode.WEB_INTERACTION_FAILED.value,
                    data=None,
                    message=f"选择AI Avatar失败: {str(e)}",
                    error_details={"error": str(e)}
                )
            
            self.logger.info("已跳转到数字人生成页面并选择AI Avatar")
            return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="页面跳转成功")
        except Exception as e:
            self.logger.error("页面跳转失败", error=str(e))
            return TaskResult(
                code=ErrorCode.WEB_INTERACTION_FAILED.value,
                data=None,
                message="页面跳转失败",
                error_details={"error": str(e)}
            )
    
    async def upload_avatar_image(self, image_path: str) -> TaskResult:
        """上传头像图片"""
        try:
            self.logger.info("上传头像图片", image_path=image_path)
            
            # 检查文件是否存在
            import os
            if not os.path.exists(image_path):
                self.logger.error("图片文件不存在", image_path=image_path)
                return TaskResult(
                    code=ErrorCode.WEB_INTERACTION_FAILED.value,
                    data=None,
                    message=f"图片文件不存在: {image_path}"
                )
            
            avatar_upload = await self.page.query_selector('div[class^="reference-upload-"]:has-text("Avatar") input[type="file"]')
            if not avatar_upload:
                self.logger.error("未找到头像上传控件")
                return TaskResult(
                    code=ErrorCode.WEB_INTERACTION_FAILED.value,
                    data=None,
                    message="未找到头像上传控件"
                )
            
            await avatar_upload.set_input_files(image_path)
            await asyncio.sleep(2)
            self.logger.info("头像图片上传成功")
            return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="头像图片上传成功")
        except Exception as e:
            self.logger.error("头像图片上传失败", error=str(e))
            return TaskResult(
                code=ErrorCode.WEB_INTERACTION_FAILED.value,
                data=None,
                message="头像图片上传失败",
                error_details={"error": str(e)}
            )
    
    async def upload_speech_audio(self, audio_path: str) -> TaskResult:
        """上传语音文件"""
        try:
            self.logger.info("上传语音文件", audio_path=audio_path)

            # 检查文件是否存在
            import os
            if not os.path.exists(audio_path):
                self.logger.error("音频文件不存在", audio_path=audio_path)
                return TaskResult(
                    code=ErrorCode.WEB_INTERACTION_FAILED.value,
                    data=None,
                    message=f"音频文件不存在: {audio_path}"
                )

            speech_upload = await self.page.query_selector('div[class^="reference-upload-"]:has-text("Speech") input[type="file"]')
            if not speech_upload:
                self.logger.error("未找到语音上传控件")
                return TaskResult(
                    code=ErrorCode.WEB_INTERACTION_FAILED.value,
                    data=None,
                    message="未找到语音上传控件"
                )

            await speech_upload.set_input_files(audio_path)
            await asyncio.sleep(2)
            self.logger.info("语音文件上传成功")
            return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="语音文件上传成功")
        except Exception as e:
            self.logger.error("语音文件上传失败", error=str(e))
            return TaskResult(
                code=ErrorCode.WEB_INTERACTION_FAILED.value,
                data=None,
                message="语音文件上传失败",
                error_details={"error": str(e)}
            )

    async def input_action_description(self, action_description: str) -> TaskResult:
        """输入动作描述（可选）"""
        try:
            if not action_description or not action_description.strip():
                self.logger.info("动作描述为空，跳过输入")
                return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="跳过动作描述输入")

            self.logger.info("输入动作描述", action_description=action_description[:100] + "..." if len(action_description) > 100 else action_description)

            # 查找ProseMirror富文本编辑器并尝试输入
            try:
                prose_mirrors = await self.page.query_selector_all('.ProseMirror')

                for editor in prose_mirrors:
                    try:
                        is_visible = await editor.is_visible()
                        if not is_visible:
                            continue

                        # 使用fill方法输入动作描述
                        await editor.click()  # 先点击聚焦
                        await asyncio.sleep(0.5)
                        await editor.fill("")  # 清空
                        await editor.fill(action_description.strip())
                        await asyncio.sleep(2)

                        # 验证输入是否成功
                        current_text = await editor.inner_text()
                        if action_description.strip() in current_text:
                            self.logger.info("成功输入动作描述")
                            return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="动作描述输入成功")

                    except Exception as e:
                        continue

                # 如果所有编辑器都无法输入
                self.logger.warning("未能成功输入动作描述，但继续执行任务")
                return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="动作描述输入失败但继续执行")

            except Exception as e:
                self.logger.warning("未能成功输入动作描述，但继续执行任务", error=str(e))
                return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="动作描述输入失败但继续执行")

        except Exception as e:
            self.logger.warning("输入动作描述时发生异常，但继续执行任务", error=str(e))
            # 动作描述是可选的，即使失败也不应该阻止任务执行
            return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="动作描述输入异常但继续执行")
    

    
    async def setup_response_listener(self):
        """设置响应监听器"""
        async def handle_response(response):
            if "aigc_draft/generate" in response.url:
                try:
                    data = await response.json()
                    self.logger.info("监测到生成请求响应")
                    if data.get("ret") == "0" and "data" in data and "aigc_data" in data["data"]:
                        self.task_id = data["data"]["aigc_data"]["task"]["task_id"]
                        self.logger.info("获取到任务ID", task_id=self.task_id)
                except:
                    pass
            
            if "/v1/get_asset_list" in response.url and self.task_id:
                try:
                    data = await response.json()
                    if "data" in data and "asset_list" in data["data"]:
                        asset_list = data["data"]["asset_list"]
                        for asset in asset_list:
                            if "id" in asset and asset.get("id") == self.task_id:
                                if "video" in asset and asset["video"].get("finish_time", 0) != 0:
                                    try:
                                        self.video_url = asset["video"]["item_list"][0]["video"]["transcoded_video"]["origin"]["video_url"]
                                        self.logger.info("数字人视频生成完成", video_url=self.video_url)
                                        self.generation_completed = True
                                    except (KeyError, IndexError):
                                        self.logger.warning("数字人视频已完成但无法获取URL")
                                        self.generation_completed = True  # 标记为完成，即使没有URL
                                else:
                                    self.logger.debug("数字人视频生成尚未完成，继续等待")
                except:
                    pass
        
        # 注册响应监听器
        self.page.on("response", handle_response)
    
    async def start_generation(self) -> TaskResult:
        """点击生成按钮开始生成"""
        try:
            self.logger.info("等待生成按钮可用并点击")
            
            # 等待生成按钮变为可用状态（不带有 lv-btn-disabled 类）
            try:
                # 使用更精确的选择器，避免多个元素的问题
                await self.page.wait_for_selector('button.lv-btn.lv-btn-primary.submit-button-_3B9GU.submit-button-FEaBl7:not(.lv-btn-disabled)', timeout=30000)
            except Exception as wait_error:
                self.logger.warning(f"等待生成按钮超时，尝试直接查找可用按钮: {str(wait_error)}")
            
            # 多次尝试获取并点击生成按钮
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    # 先尝试使用最精确的选择器找到特定的生成按钮
                    button = await self.page.query_selector('button.lv-btn.lv-btn-primary.submit-button-_3B9GU.submit-button-FEaBl7:not(.lv-btn-disabled)')
                    
                    # 如果没找到，尝试更通用的选择器
                    if not button:
                        # 获取所有可能的提交按钮，但使用更具体的选择器来减少匹配元素数量
                        buttons = await self.page.query_selector_all('button.lv-btn.lv-btn-primary[class*="submit-button-"]:not(.lv-btn-disabled)')
                        if buttons:
                            button = buttons[0]  # 使用第一个可用的按钮
                        else:
                            # 再次检查是否有不带禁用类的按钮
                            all_buttons = await self.page.query_selector_all('button[class*="submit-button-"]')
                            for btn in all_buttons:
                                btn_class = await btn.get_attribute('class')
                                if 'lv-btn-disabled' not in btn_class:
                                    button = btn
                                    break
                    
                    if button:
                        # 获取按钮的关键类名，用于日志输出
                        button_classes = await button.get_attribute('class')
                        # 提取关键标识类名用于日志
                        submit_classes = [cls for cls in button_classes.split() if 'submit-button' in cls or 'lv-btn-primary' in cls or 'lv-btn-disabled' not in cls and 'lv-btn' in cls]
                        log_class = ' '.join(submit_classes[:3])  # 只显示前几个关键类名
                        
                        self.logger.info(f"找到生成按钮: {log_class}")
                        
                        # 使用JavaScript强制点击生成按钮
                        self.logger.info("使用JavaScript强制点击生成按钮")
                        clicked = await self.page.evaluate('''
                            (btn) => {
                                if (btn) {
                                    btn.click();
                                    return true;
                                }
                                return false;
                            }
                        ''', button)
                        
                        if clicked:
                            self.logger.info("已点击生成按钮，开始生成数字人视频")
                            await asyncio.sleep(2)
                            return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="开始生成")
                        else:
                            self.logger.warning(f"第{attempt + 1}次尝试点击生成按钮失败，重试...")
                            await asyncio.sleep(1)
                            continue
                    else:
                        self.logger.warning(f"第{attempt + 1}次尝试未找到可用的生成按钮，重试...")
                        await asyncio.sleep(2)
                        
                except Exception as click_error:
                    self.logger.warning(f"第{attempt + 1}次尝试点击生成按钮时出错: {str(click_error)}")
                    await asyncio.sleep(1)
            
            self.logger.error("多次尝试后仍无法点击生成按钮")
            return TaskResult(
                code=ErrorCode.WEB_INTERACTION_FAILED.value,
                data=None,
                message="多次尝试后仍无法点击生成按钮",
                error_details={"error": "无法点击生成按钮"}
            )
            
        except Exception as e:
            self.logger.error("点击生成按钮失败", error=str(e))
            return TaskResult(
                code=ErrorCode.WEB_INTERACTION_FAILED.value,
                data=None,
                message="点击生成按钮失败",
                error_details={"error": str(e)}
            )
    
    async def wait_for_generation_complete(self, max_wait_time: int = 3600) -> TaskResult:
        """等待生成完成"""
        try:
            # 等待获取到任务ID
            self.logger.info("等待获取任务ID")
            wait_task_id_time = 120
            task_id_start_time = time.time()
            
            while not self.task_id and time.time() - task_id_start_time < wait_task_id_time:
                elapsed = time.time() - task_id_start_time
                self.logger.debug(f"等待任务ID中，已等待 {elapsed:.1f} 秒")
                await asyncio.sleep(1)
            
            if not self.task_id:
                self.logger.error("未能获取到任务ID，生成可能失败")
                return TaskResult(
                    code=ErrorCode.TASK_ID_NOT_OBTAINED.value,
                    data=None,
                    message="任务ID等待超时"
                )
                
            # 等待数字人视频生成完成
            self.logger.info("已获取任务ID，等待数字人视频生成完成", task_id=self.task_id)
            start_time = time.time()
            
            while not self.generation_completed and time.time() - start_time < max_wait_time:
                elapsed = time.time() - start_time
                self.logger.debug(f"等待数字人视频生成中，已等待 {elapsed:.1f} 秒")
                await self.page.reload()
                self.logger.debug("刷新页面，检查数字人视频生成状态")
                await asyncio.sleep(5)
            
            if self.generation_completed and self.video_url:
                self.logger.info("数字人视频生成成功", total_time=f"{time.time() - start_time:.1f}秒", video_url=self.video_url)
                return TaskResult(
                    code=ErrorCode.SUCCESS.value,
                    data=self.video_url,
                    message="数字人视频生成成功"
                )
            elif self.generation_completed and not self.video_url:
                self.logger.error("任务已完成但未获取到数字人视频URL", task_id=self.task_id, wait_time=f"{time.time() - start_time:.1f}秒")
                return TaskResult(
                    code=ErrorCode.GENERATION_FAILED.value,
                    data=None,
                    message="当前任务生成失败，请手动生成"
                )
            else:
                self.logger.warning("等待超时，任务未完成", wait_time=f"{time.time() - start_time:.1f}秒", task_id=self.task_id)
                return TaskResult(
                    code=ErrorCode.GENERATION_FAILED.value,
                    data=None,
                    message="当前任务生成失败，请手动生成"
                )
                
        except Exception as e:
            self.logger.error("等待生成完成时出错", error=str(e))
            return TaskResult(
                code=ErrorCode.OTHER_ERROR.value,
                data=None,
                message="等待生成完成时出错",
                error_details={"error": str(e)}
            )
    
    async def execute(self, **kwargs) -> TaskResult:
        """执行数字人生成任务"""
        start_time = time.time()

        # 提取参数
        image_path = kwargs.get('image_path')
        audio_path = kwargs.get('audio_path')
        action_description = kwargs.get('action_description', '')
        username = kwargs.get('username')
        password = kwargs.get('password')
        cookies = kwargs.get('cookies')

        self.logger.info("开始执行数字人生成任务",
                        image_path=image_path, audio_path=audio_path,
                        has_action_description=bool(action_description))
        
        # 参数验证
        if not image_path:
            self.logger.error("图片路径参数为空")
            return TaskResult(
                code=ErrorCode.WEB_INTERACTION_FAILED.value,
                data=None,
                message="图片路径参数为空",
                execution_time=time.time() - start_time
            )
        
        if not audio_path:
            self.logger.error("音频路径参数为空")
            return TaskResult(
                code=ErrorCode.WEB_INTERACTION_FAILED.value,
                data=None,
                message="音频路径参数为空",
                execution_time=time.time() - start_time
            )
        
        try:
            # 初始化浏览器
            init_result = await self.init_browser(cookies)
            if init_result.code != ErrorCode.SUCCESS.value:
                return init_result

            if cookies:
                await self.handle_cookies(cookies)
                # 检查登录状态
                login_status_result = await self.check_login_status()
            
            # 如果没有cookies或cookies检查失败，需要登录
            if not cookies or login_status_result.code == 600:
                login_result = await self.perform_login(username, password)
                if login_result.code != ErrorCode.SUCCESS.value:
                    return login_result
                
                validate_result = await self.validate_login_success()
                if validate_result.code != ErrorCode.SUCCESS.value:
                    return validate_result
            else:
                # 如果有cookies，直接设置
                await self.handle_cookies(cookies)
            
            # 跳转到数字人生成页面
            nav_result = await self.navigate_to_digital_human_page()
            if nav_result.code != ErrorCode.SUCCESS.value:
                return nav_result
            
            # 设置响应监听器
            await self.setup_response_listener()
            
            # 上传头像图片
            avatar_result = await self.upload_avatar_image(image_path)
            if avatar_result.code != ErrorCode.SUCCESS.value:
                return avatar_result
            
            # 上传语音文件
            speech_result = await self.upload_speech_audio(audio_path)
            if speech_result.code != ErrorCode.SUCCESS.value:
                return speech_result

            # 输入动作描述（可选）
            action_result = await self.input_action_description(action_description)
            # 动作描述输入失败不会阻止任务继续执行

            # 开始生成
            gen_result = await self.start_generation()
            if gen_result.code != ErrorCode.SUCCESS.value:
                return gen_result
            
            # 等待生成完成
            complete_result = await self.wait_for_generation_complete()
            
            # 获取最新的cookies
            final_cookies = await self.get_cookies()
            complete_result.cookies = final_cookies
            complete_result.execution_time = time.time() - start_time
            
            return complete_result
            
        except asyncio.TimeoutError as e:
            self.logger.error("Playwright等待超时", error=str(e))
            return TaskResult(
                code=ErrorCode.WEB_INTERACTION_FAILED.value,
                data=None,
                message=f"Playwright等待超时: {str(e)}",
                execution_time=time.time() - start_time
            )
        except Exception as e:
            error_msg = str(e)
            self.logger.error("生成数字人视频时出错", error=error_msg)
            
            # 根据错误信息判断错误类型
            if "selector" in error_msg.lower() or "element" in error_msg.lower() or "not found" in error_msg.lower():
                error_code = ErrorCode.WEB_INTERACTION_FAILED.value
            elif "timeout" in error_msg.lower():
                error_code = ErrorCode.WEB_INTERACTION_FAILED.value
            else:
                error_code = ErrorCode.OTHER_ERROR.value
                
            return TaskResult(
                code=error_code,
                data=None,
                message=f"生成数字人视频时出错: {error_msg}",
                execution_time=time.time() - start_time,
                error_details={"error": error_msg}
            )
        
        finally:
            await self.close_browser()

    async def run(self, **kwargs) -> TaskResult:
        """运行任务的入口方法"""
        return await self.execute(**kwargs)

# 兼容性函数，保持向后兼容
async def digital_human(image_path, audio_path, username=None, password=None, headless=False, cookies=None):
    """
    兼容性函数，用于保持向后兼容
    """
    executor = JimengDigitalHumanExecutor(headless=headless)
    result = await executor.run(
        image_path=image_path,
        audio_path=audio_path,
        username=username,
        password=password,
        cookies=cookies
    )
    
    # 转换为旧格式的返回值
    return {
        "code": result.code,
        "data": result.data,
        "message": result.message
    }

# 使用示例
if __name__ == "__main__":
    async def test():
        username = "test@example.com"
        password = "password123"
        image_path = "/path/to/avatar.jpg"
        audio_path = "/path/to/speech.mp3"
        
        executor = JimengDigitalHumanExecutor(headless=False)
        result = await executor.run(
            image_path=image_path,
            audio_path=audio_path,
            username=username,
            password=password
        )
        
        if result.code == 200:
            print(f"生成成功，数字人视频链接: {result.data}")
        else:
            print(f"生成失败: {result.message}")
    
    # 运行测试
    asyncio.run(test())
