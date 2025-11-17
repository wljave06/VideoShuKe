"""
即梦平台自动化模块 - 文本生成图片
based on BaseTaskExecutor refactoring version
"""

import asyncio
import time
import json
from typing import Optional, List, Dict, Any
from backend.utils.base_task_executor import BaseTaskExecutor, TaskResult, ErrorCode, TaskLogger
from html.parser import HTMLParser

class JimengText2ImageExecutor(BaseTaskExecutor):
    """即梦文本生成图片执行器"""
    
    def __init__(self, headless: bool = False):
        super().__init__(headless)
        self.task_id = None
        self.image_urls = []
        self.generation_completed = False
        self.current_tool_type = None  # 记录当前选择的工具类型
        self.generation_started = False
        self.generation_started_at = None
        self.generation_started_perf = None
        # 生成开始时的容器图片快照，用于区分历史图片与本次新生成
        self.pre_gen_image_urls = []
        self.last_generate_request_url = None
        self.last_generate_request_method = None
        self.last_generate_request_payload_preview = None
        self.last_generate_response_status = None
        self.last_generate_response_preview = None
        self.did_soft_refresh = False
        self.send_via_enter = False
        self.pre_perf_names = set()
    
    async def handle_cookies(self, cookies: str):
        """处理cookies字符串格式"""
        try:
            # 将cookies字符串转换为字典列表格式
            cookie_pairs = cookies.split('; ')
            cookie_list = []
            for pair in cookie_pairs:
                if '=' in pair:
                    name, value = pair.split('=', 1)
                    base = {
                        'name': name.strip(),
                        'value': value.strip(),
                        'path': '/'
                    }
                    cookie_list.append({**base, 'domain': '.capcut.com'})
                    cookie_list.append({**base, 'domain': '.dreamina.capcut.com'})
            
            await self.context.add_cookies(cookie_list)
            self.logger.info("即梦平台cookies设置成功", count=len(cookie_list))
            
        except Exception as e:
            self.logger.error("设置即梦平台cookies时出错", error=str(e))
    
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
            # 实现等待登录完成，如果10秒后还是没反应就刷新下界面，依旧最多等待60秒
            login_complete = False
            start_wait_time = time.time()
            
            # 检查登录是否完成，最多等待60秒
            while not login_complete and (time.time() - start_wait_time) < 60:
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
    
    async def navigate_to_generation_page(self) -> TaskResult:
        """跳转到AI工具生成页面"""
        try:
            self.logger.info("正在跳转到AI工具生成页面")
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
                        copy_link_button = await self.page.query_selector('button.lv-btn.lv-btn-primary.lv-btn-size-default.lv-btn-shape-square.app-download-button-gIF_ODD')
                        if copy_link_button:
                            await copy_link_button.click()
                            self.logger.info("已点击Copy link按钮")
                            await asyncio.sleep(2)
                except Exception as e:
                    # 静默处理异常，不输出警告
                    pass
            
            self.logger.info("弹窗检测和处理完成，继续执行")
            
            # 强制选择 AI Agent 模式
            self.logger.info("选择 AI Agent 模式")
            self.current_tool_type = "AI Agent"
            try:
                # 检查是否存在新的tabs节点
                tabs_selector = 'div.tabs-dTWN8k'
                tabs_element = await self.page.query_selector(tabs_selector)
                
                if tabs_element:
                    self.logger.info("发现新的tabs界面，点击 AI Agent")
                    await self.page.click('button.tab-YSwCEn:has-text("AI Agent")')
                    self.logger.info("已选择AI Agent")
                    await asyncio.sleep(2)
                else:
                    self.logger.info("未发现新tabs界面，使用下拉框方式选择 AI Agent")
                    # 点击类型选择下拉框
                    await self.page.click('div.lv-select[role="combobox"][class*="type-select-"]')
                    await asyncio.sleep(1)
                    
                    await self.page.click('span[class*="select-option-label-content"]:has-text("AI Agent")')
                    self.logger.info("已选择AI Agent")
                    await asyncio.sleep(2)
                
            except Exception as e:
                self.logger.warning("选择 AI Agent 时出错，尝试备用方法", error=str(e))
                # 备用方法：直接尝试传统下拉框方式
                try:
                    await self.page.click('div.lv-select[role="combobox"][class*="type-select-"]')
                    await asyncio.sleep(1)
                    await self.page.click('span[class*="select-option-label-content"]:has-text("AI Agent")')
                    self.logger.info("已选择AI Agent")
                    await asyncio.sleep(2)
                except Exception as backup_e:
                    self.logger.error("无法选择 AI Agent", error=str(backup_e))
                    return TaskResult(
                        code=ErrorCode.WEB_INTERACTION_FAILED.value,
                        data=None,
                        message=f"无法选择 AI Agent: {str(backup_e)}",
                        error_details={"error": str(backup_e)}
                    )
            
            # 等待页面中的关键元素加载完成 - 提示词输入框
            textarea_selector = 'textarea.lv-textarea'
            await self.page.wait_for_selector(textarea_selector, timeout=30000)
            await asyncio.sleep(2)
            
            # 跳转后尝试滚动到底部，确保最新生成区域可见
            try:
                await self.scroll_to_bottom_safe()
                self.did_scroll_bottom = True
            except Exception as e:
                self.logger.debug(f"页面跳转后滚动失败: {e}")
            self.logger.info("已跳转到AI工具页面", tool_type=self.current_tool_type)
            return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="页面跳转成功")
        except Exception as e:
            self.logger.error("页面跳转失败", error=str(e))
            return TaskResult(
                code=ErrorCode.WEB_INTERACTION_FAILED.value,
                data=None,
                message="页面跳转失败",
                error_details={"error": str(e)}
            )
    
    async def input_prompt(self, prompt: str) -> TaskResult:
        """输入提示词"""
        try:
            if not prompt or (isinstance(prompt, str) and not prompt.strip()):
                return TaskResult(
                    code=ErrorCode.OTHER_ERROR.value,
                    data=None,
                    message="提示词不能为空",
                    error_details={"error": "empty_prompt"}
                )
            self.logger.info("输入提示词", prompt=prompt)
            # 查找提示词输入框
            textarea_selector = 'textarea.lv-textarea'
            await self.page.wait_for_selector(textarea_selector, timeout=10000)
            await self.page.fill(textarea_selector, prompt)
            await asyncio.sleep(2)
            return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="提示词输入成功")
        except Exception as e:
            self.logger.error("提示词输入失败", error=str(e))
            return TaskResult(
                code=ErrorCode.WEB_INTERACTION_FAILED.value,
                data=None,
                message="提示词输入失败",
                error_details={"error": str(e)}
            )

    async def upload_image(self, image_path: str) -> TaskResult:
        """上传图片（AI Agent模式下可选）"""
        try:
            self.logger.info("上传图片", image_path=image_path)
            
            # 优先使用隐藏的 file input 直接设置文件，不要求可见
            selectors = [
                'input[type="file"][accept*="image"]',
                'input[type="file"]',
                'input[class*="file-input"]',
            ]
            set_ok = False
            for sel in selectors:
                try:
                    await self.page.wait_for_selector(sel, state='attached', timeout=3000)
                    await self.page.set_input_files(sel, image_path)
                    set_ok = True
                    break
                except Exception:
                    pass
            if not set_ok:
                # 兜底：遍历所有 file input 逐个尝试
                try:
                    inputs = await self.page.query_selector_all('input[type="file"]')
                except Exception:
                    inputs = []
                for el in inputs or []:
                    try:
                        await el.set_input_files(image_path)
                        set_ok = True
                        break
                    except Exception:
                        pass
            if not set_ok:
                raise Exception("未找到可用的文件上传控件或设置文件失败")
            
            # 等待上传完成
            await asyncio.sleep(3)
            
            self.logger.info("图片上传成功")
            return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="图片上传成功")
            
        except Exception as e:
            self.logger.error("图片上传失败", error=str(e))
            return TaskResult(
                code=ErrorCode.WEB_INTERACTION_FAILED.value,
                data=None,
                message="图片上传失败",
                error_details={"error": str(e)}
            )
    
    async def select_model(self, model: str) -> TaskResult:
        """选择模型"""
        try:
            self.logger.info("选择模型", model=model)
            await self.page.click('div.lv-select[role="combobox"]:not([class*="type-select-"])')
            await asyncio.sleep(1)
            
            # 等待下拉菜单完全加载
            await self.page.wait_for_selector('div.lv-select-popup-inner[role="listbox"]', timeout=5000)
            await asyncio.sleep(1)
            
            # 查找并点击对应的模型选项
            try:
                option_elements = await self.page.query_selector_all('li[role="option"] [class*="option-label-"]')
                model_option_found = False
                
                for element in option_elements:
                    text_content = await element.text_content()
                    if model in text_content or text_content.strip() == model:
                        await element.click()
                        model_option_found = True
                        self.logger.info("已选择模型", model=model)
                        break
                
                if not model_option_found:
                    # 如果没有找到，尝试更通用的选择方法
                    # 针对Image 4.0等新模型的处理
                    self.logger.warning(f"未找到模型选项 {model}，尝试备用方法")
                    # 尝试查找包含该模型名的元素
                    await self.page.click(f'li[role="option"]:has-text("{model}")')
                    model_option_found = True
                    self.logger.info("已选择模型(备用方法)", model=model)
                    
            except Exception as e:
                self.logger.warning("未找到指定模型，尝试通用选择方式", model=model, error=str(e))
                # 尝试使用更具体的选择器
                try:
                    await self.page.click(f'span[class*="select-option-label-content"]:has-text("{model}")')
                    model_option_found = True
                except:
                    # 如果还是找不到，尝试通过值属性选择
                    await self.page.click(f'li[role="option"][value="{model}"]')
                    model_option_found = True
            
            if model_option_found:
                await asyncio.sleep(1)
                # 6分钟尚未获取到图片，执行一次刷新后继续等待
                try:
                    if self.generation_started_at and (time.time() - self.generation_started_at) >= 360 and not self.did_soft_refresh:
                        await self.soft_refresh_page()
                        try:
                            btn = self.page.locator('button:has-text("Go to bottom"), [role="button"]:has-text("Go to bottom")')
                            if await btn.count() > 0:
                                await btn.first.click()
                                self.did_scroll_bottom = True
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    btn = self.page.locator('button:has-text("Go to bottom"), [role="button"]:has-text("Go to bottom")')
                    if await btn.count() > 0:
                        await btn.first.click()
                        self.did_scroll_bottom = True
                except Exception:
                    pass
                return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="模型选择成功")
            else:
                raise Exception(f"未找到模型选项: {model}")
                
        except Exception as e:
            self.logger.error("模型选择失败", error=str(e))
            return TaskResult(
                code=ErrorCode.WEB_INTERACTION_FAILED.value,
                data=None,
                message="模型选择失败",
                error_details={"error": str(e)}
            )
    
    async def select_aspect_ratio(self, aspect_ratio: str, model: str = None) -> TaskResult:
        """选择比例"""
        try:
            self.logger.info("选择比例", aspect_ratio=aspect_ratio, model=model)
            
            # 重试机制，最多尝试3次
            max_retries = 3
            ratio_selected = False
            
            for attempt in range(max_retries):
                try:
                    self.logger.info(f"第 {attempt + 1} 次尝试选择比例")
                    
                    # 点击比例选择按钮
                    await self.page.click('button.lv-btn.lv-btn-secondary.lv-btn-size-default.lv-btn-shape-square:has([class*="button-text-"])')
                    await asyncio.sleep(1)
                    
                    # 定义比例选项的映射（从比例值到索引位置）
                    ratio_index_map = {
                        "21:9": 0,
                        "16:9": 1,
                        "3:2": 2,
                        "4:3": 3,
                        "1:1": 4,
                        "3:4": 5,
                        "2:3": 6,
                        "9:16": 7
                    }
                    
                    # 如果是Image 4.0模型，则所有索引需要往后挪一位（因为多了Auto选项）
                    is_image4_model = model and model == "Image 4.0"
                    if is_image4_model:
                        self.logger.info("检测到Image 4.0模型，比例索引将向后调整一位")
                    
                    # 获取对应比例的索引
                    if aspect_ratio in ratio_index_map:
                        ratio_index = ratio_index_map[aspect_ratio]
                        
                        # 对于Image 4.0模型，所有比例索引都要加1，因为前面多了一个Auto选项
                        if is_image4_model:
                            ratio_index += 1
                        
                        # 在弹出的比例选择框中选择对应位置的比例选项
                        # 根据新的HTML结构，点击包含对应value的label元素
                        await self.page.click(f'label.lv-radio:has(input[value="{aspect_ratio}"])')
                        await asyncio.sleep(1)
                    else:
                        # 如果找不到对应的比例，抛出异常
                        raise Exception(f"不支持的比例: {aspect_ratio}")

                    # 关闭选择 - 检查是否需要关闭选择框
                    # 在新版本中，点击选项后可能不需要手动关闭
                    await asyncio.sleep(1)
                    
                    # 检查是否选择成功 - 查找按钮中是否包含目标比例
                    button_element = await self.page.query_selector('button.lv-btn.lv-btn-secondary.lv-btn-size-default.lv-btn-shape-square:has([class*="button-text-"])')
                    if button_element:
                        button_text = await button_element.text_content()
                        if aspect_ratio in button_text:
                            self.logger.info("比例选择成功", aspect_ratio=aspect_ratio)
                            ratio_selected = True
                            break
                        else:
                            self.logger.warning("比例选择失败", current=button_text, expected=aspect_ratio)
                    else:
                        self.logger.warning("未找到比例按钮元素")
                        
                except Exception as e:
                    self.logger.warning(f"第 {attempt + 1} 次选择比例时出错", error=str(e))
                    
                await asyncio.sleep(1)
            
            # 如果3次尝试都失败，返回错误
            if not ratio_selected:
                self.logger.error(f"比例选择失败，已尝试 {max_retries} 次")
                return TaskResult(
                    code=ErrorCode.WEB_INTERACTION_FAILED.value,
                    data=None,
                    message=f"比例选择失败，已尝试 {max_retries} 次"
                )
            
            return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="比例选择成功")
            
        except Exception as e:
            self.logger.error("比例选择失败", error=str(e))
            return TaskResult(
                code=ErrorCode.WEB_INTERACTION_FAILED.value,
                data=None,
                message="比例选择失败",
                error_details={"error": str(e)}
            )

    async def select_quality(self, quality: str) -> TaskResult:
        """选择质量/分辨率"""
        try:
            self.logger.info("选择质量/分辨率", quality=quality)

            # 等待页面完全加载
            await asyncio.sleep(2)
            
            # 可能存在一个通用的下拉按钮来切换质量选项
            # 通常会有一个显示当前质量的按钮，点击后可以切换
            quality_toggle_selectors = [
                'button:has-text("High (2K)")',
                'button:has-text("Standard (1K)")',
                'button:has-text("Ultra (4K)")',
                'div:has-text("High (2K)")',
                'div:has-text("Standard (1K)")',
                'div:has-text("Ultra (4K)")',
                'button[class*="quality"]',
                'div[class*="quality"]',
                'button[class*="resolution"]',
                'div[class*="resolution"]',
                '[class*="commercial-option"]'
            ]
            
            quality_selected = False
            
            # 首先，尝试点击质量/分辨率选择按钮，打开质量选项
            # 检测质量选择按钮 - 通常这类按钮有特定的类名
            quality_button_selectors = [
                'button.lv-btn.lv-btn-secondary.lv-btn-size-default.lv-btn-shape-square:has-text("High (2K)")',
                'button.lv-btn.lv-btn-secondary.lv-btn-size-default.lv-btn-shape-square:has-text("Standard (1K)")',
                'button.lv-btn.lv-btn-secondary.lv-btn-size-default.lv-btn-shape-square:has-text("Ultra (4K)")',
                'button.lv-btn.lv-btn-secondary.lv-btn-size-default.lv-btn-shape-square.button-AsRw13'  # 特定类名
            ]
            
            quality_button = None
            for selector in quality_button_selectors:
                try:
                    quality_button = await self.page.query_selector(selector)
                    if quality_button:
                        break
                except:
                    continue
            
            if quality_button:
                # 点击质量按钮展开选项
                await quality_button.click()
                await asyncio.sleep(1)
                
                # 现在查找并点击目标质量选项
                # 质量值应该是 "1k", "2k", "4k"
                quality_map = {"1K": "1k", "2K": "2k", "4K": "4k"}
                target_quality_value = quality_map.get(quality, "1k")  # 默认为 "1k"
                
                # 在展开的选项中查找目标质量
                target_option = await self.page.query_selector(f'label.lv-radio:has(input[value="{target_quality_value}"])')
                
                if target_option:
                    # 检查是否已经是选中状态
                    is_checked = await target_option.get_attribute('class')
                    if is_checked and 'lv-radio-checked' in is_checked:
                        self.logger.info(f"已经是 {quality} 质量，无需更改")
                        # 关闭已打开的选项
                        await quality_button.click()
                        return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="质量已经是所需选项")
                    else:
                        # 点击目标选项
                        await target_option.click()
                        self.logger.info(f"已选择 {quality} 质量")
                        await asyncio.sleep(1)
                        quality_selected = True
                        # 关闭选项面板
                        await quality_button.click()
                else:
                    # 关闭选项面板
                    await quality_button.click()
                    
                    # 重新点击按钮再次尝试
                    await quality_button.click()
                    await asyncio.sleep(1)
                    
                    # 尝试使用更具体的选择器，确保在正确的区域内查找
                    # 根据您提供的HTML结构，质量选项在resolution-radio-group-WD9rqn中
                    target_option_in_group = await self.page.query_selector(f'div[class^="resolution-radio-group-"] label.lv-radio:has(input[value=\"{target_quality_value}\"])')
                    if target_option_in_group:
                        # 检查是否已经是选中状态
                        is_checked = await target_option_in_group.get_attribute('class')
                        if is_checked and 'lv-radio-checked' in is_checked:
                            self.logger.info(f"已经是 {quality} 质量，无需更改")
                            await quality_button.click()  # 再次关闭
                            return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="质量已经是所需选项")
                        else:
                            await target_option_in_group.click()
                            self.logger.info(f"已选择 {quality} 质量")
                            await asyncio.sleep(1)
                            quality_selected = True
                            await quality_button.click()  # 关闭
                    else:
                        # 如果还是找不到，在整个页面范围内尝试
                        general_target_option = await self.page.query_selector(f'label.lv-radio:has(input[value="{target_quality_value}"])')
                        if general_target_option:
                            # 检查是否已经是选中状态
                            is_checked = await general_target_option.get_attribute('class')
                            if is_checked and 'lv-radio-checked' in is_checked:
                                self.logger.info(f"已经是 {quality} 质量，无需更改")
                                await quality_button.click()  # 再次关闭
                                return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="质量已经是所需选项")
                            else:
                                await general_target_option.click()
                                self.logger.info(f"已选择 {quality} 质量")
                                await asyncio.sleep(1)
                                quality_selected = True
                                await quality_button.click()  # 关闭
                        else:
                            # 如果仍然找不到，说明面板可能还没完全加载，等待更多时间
                            await asyncio.sleep(2)
                            final_target_option = await self.page.query_selector(f'label.lv-radio:has(input[value="{target_quality_value}"])')
                            if final_target_option:
                                is_checked = await final_target_option.get_attribute('class')
                                if is_checked and 'lv-radio-checked' in is_checked:
                                    self.logger.info(f"已经是 {quality} 质量，无需更改")
                                    await quality_button.click()  # 再次关闭
                                    return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="质量已经是所需选项")
                                else:
                                    await final_target_option.click()
                                    self.logger.info(f"已选择 {quality} 质量")
                                    await asyncio.sleep(1)
                                    quality_selected = True
                                    await quality_button.click()  # 关闭
            else:
                self.logger.warning("未找到质量选择按钮，尝试备用方法")
                
                # 备用方法：通过文本内容检测
                for selector in quality_toggle_selectors:
                    try:
                        element = await self.page.query_selector(selector)
                        if element:
                            element_text = await element.text_content()
                            if quality == "1K" and "Standard (1K)" in element_text:
                                self.logger.info("已经是 Standard (1K) 质量，无需更改")
                                return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="质量已经是所需选项")
                            elif quality == "2K" and "High (2K)" in element_text:
                                self.logger.info("已经是 High (2K) 质量，无需更改")
                                return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="质量已经是所需选项")
                            elif quality == "4K" and "Ultra (4K)" in element_text:
                                self.logger.info("已经是 Ultra (4K) 质量，无需更改")
                                return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="质量已经是所需选项")
                    except:
                        continue

            # 如果通过上述方法没有成功选择质量，则使用原来的备用方法
            if not quality_selected:
                # 备用方法：通过文本内容检测
                for selector in quality_toggle_selectors:
                    try:
                        element = await self.page.query_selector(selector)
                        if element:
                            element_text = await element.text_content()
                            if quality == "1K" and "Standard (1K)" in element_text:
                                self.logger.info("已经是 Standard (1K) 质量，无需更改")
                                return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="质量已经是所需选项")
                            elif quality == "2K" and "High (2K)" in element_text:
                                self.logger.info("已经是 High (2K) 质量，无需更改")
                                return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="质量已经是所需选项")
                            elif quality == "4K" and "Ultra (4K)" in element_text:
                                self.logger.info("已经是 Ultra (4K) 质量，无需更改")
                                return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="质量已经是所需选项")
                    except:
                        continue
            
            # 如果当前质量不是所需的质量，则需要切换
            # 先尝试寻找一个切换质量的按钮（通常显示当前质量的按钮）
            for selector in quality_toggle_selectors:
                try:
                    quality_element = await self.page.query_selector(selector)
                    if quality_element:
                        element_text = await quality_element.text_content()
                        # 如果元素包含当前质量，点击它可能会展开选项
                        if "Standard" in element_text or "High" in element_text or "Ultra" in element_text:
                            await quality_element.click()
                            await asyncio.sleep(1)
                            
                            # 现在查找并点击所需的选项
                            if quality == "1K":
                                # 寻找 "Standard (1K)" 选项
                                standard_option = await self.page.query_selector('label.lv-radio:has(input[value="1k"])')
                                if standard_option:
                                    await standard_option.click()
                                    self.logger.info("已选择 Standard (1K) 质量选项")
                                    await asyncio.sleep(1)
                                    quality_selected = True
                                    break
                            elif quality == "2K":
                                # 寻找 "High (2K)" 选项
                                high_option = await self.page.query_selector('label.lv-radio:has(input[value="2k"])')
                                if high_option:
                                    await high_option.click()
                                    self.logger.info("已选择 High (2K) 质量选项")
                                    await asyncio.sleep(1)
                                    quality_selected = True
                                    break
                            elif quality == "4K":
                                # 寻找 "Ultra (4K)" 选项
                                ultra_option = await self.page.query_selector('label.lv-radio:has(input[value="4k"])')
                                if ultra_option:
                                    await ultra_option.click()
                                    self.logger.info("已选择 Ultra (4K) 质量选项")
                                    await asyncio.sleep(1)
                                    quality_selected = True
                                    break
                except Exception as e:
                    self.logger.debug(f"尝试选择器 {selector} 时出错: {str(e)}")
                    continue
            
            # 如果上面的方法没成功，尝试更广泛的搜索
            if not quality_selected:
                # 直接查找并点击质量选项 (label.lv-radio)
                if quality == "1K":
                    standard_option = await self.page.query_selector('label.lv-radio:has(input[value="1k"])')
                    if standard_option:
                        await standard_option.click()
                        self.logger.info("已选择 Standard (1K) 质量选项")
                        await asyncio.sleep(1)
                        quality_selected = True
                
                elif quality == "2K":
                    high_option = await self.page.query_selector('label.lv-radio:has(input[value="2k"])')
                    if high_option:
                        await high_option.click()
                        self.logger.info("已选择 High (2K) 质量选项")
                        await asyncio.sleep(1)
                        quality_selected = True
                
                elif quality == "4K":
                    ultra_option = await self.page.query_selector('label.lv-radio:has(input[value="4k"])')
                    if ultra_option:
                        await ultra_option.click()
                        self.logger.info("已选择 Ultra (4K) 质量选项")
                        await asyncio.sleep(1)
                        quality_selected = True

            if quality_selected:
                return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="质量选择成功")
            else:
                self.logger.warning("未找到质量选项", quality=quality)
                return TaskResult(
                    code=ErrorCode.WEB_INTERACTION_FAILED.value,
                    data=None,
                    message=f"未找到质量选项: {quality}"
                )

        except Exception as e:
            self.logger.error("质量选择失败", error=str(e))
            return TaskResult(
                code=ErrorCode.WEB_INTERACTION_FAILED.value,
                data=None,
                message="质量选择失败",
                error_details={"error": str(e)}
            )
    
    async def setup_response_listener(self):
        """设置响应监听器"""
        def _deep_find_task_id(obj: Any) -> Optional[str]:
            try:
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        kl = str(k).lower()
                        if kl in ("task_id", "taskid") and isinstance(v, (str, int)):
                            return str(v)
                        if kl == "task" and isinstance(v, dict):
                            val = v.get("task_id") or v.get("taskId")
                            if val:
                                return str(val)
                        found = _deep_find_task_id(v)
                        if found:
                            return found
                elif isinstance(obj, list):
                    for it in obj:
                        found = _deep_find_task_id(it)
                        if found:
                            return found
            except Exception:
                return None
            return None
        async def handle_request(request):
            try:
                url = request.url
                method = request.method
                post_data = None
                try:
                    post_data = request.post_data or ""
                except Exception:
                    post_data = ""
                if "generate" in url:
                    self.last_generate_request_url = url
                    self.last_generate_request_method = method
                    preview = post_data if isinstance(post_data, str) else str(post_data)
                    self.last_generate_request_payload_preview = preview[:1000]
                    self.logger.info("监测到生成请求", url=url, method=method)
                    if preview:
                        self.logger.debug("生成请求体预览", preview=self.last_generate_request_payload_preview)
            except Exception as e:
                self.logger.debug(f"请求监听异常: {e}")

        async def handle_response(response):
            # 添加更详细的日志来调试AI Agent模式
            if "aigc_draft/generate" in response.url:
                try:
                    status = response.status
                    headers = getattr(response, "headers", {})
                    content_type = headers.get("content-type") if isinstance(headers, dict) else None
                    self.logger.info("监测到生成请求响应", url=response.url, status=status, content_type=content_type)
                    data = None
                    try:
                        data = await response.json()
                    except Exception:
                        try:
                            text = await response.text()
                            preview_text = (text or "")[:1000]
                            self.logger.debug("生成响应文本预览", preview=preview_text)
                        except Exception:
                            pass
                    self.last_generate_response_status = status
                    preview = json.dumps(data, ensure_ascii=False)[:1000]
                    self.logger.debug("生成响应JSON预览", preview=preview)
                    if data.get("ret") == "0" and "data" in data and "aigc_data" in data["data"]:
                        self.task_id = data["data"]["aigc_data"]["task"]["task_id"]
                        self.logger.info("获取到任务ID", task_id=self.task_id)
                        self.last_generate_response_preview = preview
                    else:
                        self.logger.debug("生成响应未包含任务ID字段", keys=list(data.keys()))
                except Exception as e:
                    self.logger.debug(f"解析生成响应失败: {e}")
                    pass
            
            # AI Agent模式可能使用不同的API端点
            elif "aigc" in response.url and "generate" in response.url:
                try:
                    status = response.status
                    headers = getattr(response, "headers", {})
                    content_type = headers.get("content-type") if isinstance(headers, dict) else None
                    self.logger.info("监测到AI相关生成请求响应", url=response.url, status=status, content_type=content_type)
                    data = None
                    try:
                        data = await response.json()
                    except Exception:
                        try:
                            text = await response.text()
                            preview_text = (text or "")[:1000]
                            self.logger.debug("AI相关生成响应文本预览", preview=preview_text)
                        except Exception:
                            pass
                    self.last_generate_response_status = status
                    preview = json.dumps(data, ensure_ascii=False)[:1000]
                    self.logger.debug("AI相关生成响应JSON预览", preview=preview)
                    # 尝试从不同格式的响应中获取任务ID
                    if data.get("ret") == "0" and "data" in data:
                        if "task_id" in data["data"]:
                            self.task_id = data["data"]["task_id"]
                            self.logger.info("获取到AI Agent任务ID", task_id=self.task_id)
                            self.last_generate_response_preview = preview
                        elif "aigc_data" in data["data"] and "task" in data["data"]["aigc_data"]:
                            self.task_id = data["data"]["aigc_data"]["task"]["task_id"]
                            self.logger.info("获取到AI Agent任务ID", task_id=self.task_id)
                            self.last_generate_response_preview = preview
                        elif "task" in data and "task_id" in data["task"]:
                            self.task_id = data["task"]["task_id"]
                            self.logger.info("获取到任务ID", task_id=self.task_id)
                            self.last_generate_response_preview = preview
                        else:
                            self.logger.debug("AI相关生成响应未包含任务ID字段", keys=list(data["data"].keys()))
                except Exception as e:
                    self.logger.debug(f"解析AI Agent生成响应失败: {e}")
                    pass
            
            if "/v1/get_asset_list" in response.url:
                try:
                    status = response.status
                    headers = getattr(response, "headers", {})
                    content_type = headers.get("content-type") if isinstance(headers, dict) else None
                    self.logger.info("监测到资源列表响应", url=response.url, status=status, content_type=content_type, task_id=self.task_id)
                    data = None
                    try:
                        data = await response.json()
                    except Exception:
                        try:
                            text = await response.text()
                            preview_text = (text or "")[:1000]
                            self.logger.debug("资源列表响应文本预览", preview=preview_text)
                        except Exception:
                            pass
                    preview = json.dumps(data, ensure_ascii=False)[:1000]
                    self.logger.debug("资源列表响应JSON预览", preview=preview)
                    if "data" in data and "asset_list" in data["data"]:
                        asset_list = data["data"]["asset_list"]
                        self.logger.debug("资源列表数量", count=len(asset_list))
                        target_asset = None
                        if self.task_id:
                            for asset in asset_list:
                                if "id" in asset and asset.get("id") == self.task_id:
                                    target_asset = asset
                                    break
                        if not target_asset:
                            finished_assets = [a for a in asset_list if a.get("image", {}).get("finish_time", 0)]
                            finished_assets.sort(key=lambda x: x.get("image", {}).get("finish_time", 0), reverse=True)
                            if finished_assets:
                                target_asset = finished_assets[0]
                        if target_asset and target_asset.get("image", {}).get("finish_time", 0):
                            try:
                                self.image_urls = []
                                item_list = target_asset["image"].get("item_list", [])
                                self.logger.debug("匹配到任务条目，图片项数量", count=len(item_list))
                                for item in item_list:
                                    try:
                                        large_images = item.get("image", {}).get("large_images", [])
                                        if large_images:
                                            url = large_images[0].get("image_url")
                                            if url:
                                                self.image_urls.append(url)
                                    except Exception:
                                        pass
                                if self.image_urls:
                                    self.logger.info("图片生成完成", count=len(self.image_urls))
                                    for i, url in enumerate(self.image_urls):
                                        self.logger.info(f"图片{i+1} URL", url=url)
                                    self.generation_completed = True
                                else:
                                    self.logger.warning("图片已完成但无法获取任何URL")
                                    self.generation_completed = True
                            except Exception:
                                self.logger.warning("图片已完成但无法获取URL")
                                self.generation_completed = True
                        else:
                            self.logger.debug("图片生成尚未完成，继续等待")
                    else:
                        self.logger.debug("资源列表响应不包含 data.asset_list 字段")
                except:
                    pass
            try:
                headers = getattr(response, "headers", {})
                content_type = headers.get("content-type") if isinstance(headers, dict) else None
                if content_type and "application/json" in content_type:
                    try:
                        data_any = await response.json()
                        candidate = _deep_find_task_id(data_any)
                        if candidate and not self.task_id:
                            self.task_id = candidate
                            self.logger.info("泛化解析获取到任务ID", task_id=self.task_id, url=response.url)
                    except Exception:
                        pass
            except Exception:
                pass
        
        # 注册监听器
        self.page.on("request", handle_request)
        self.page.on("response", handle_response)
        def _ws_on_message(frame):
            try:
                if not isinstance(frame, str):
                    return
                text = frame.strip()
                if not (text.startswith("{") or text.startswith("[")):
                    return
                data = json.loads(text)
                candidate = _deep_find_task_id(data)
                if candidate and not self.task_id:
                    self.task_id = candidate
                    self.logger.info("WebSocket获取到任务ID", task_id=self.task_id)
            except Exception:
                pass
        def _ws_handler(ws):
            try:
                ws.on("framereceived", _ws_on_message)
                ws.on("framesent", _ws_on_message)
            except Exception:
                pass
        self.page.on("websocket", _ws_handler)
    
    async def start_generation(self) -> TaskResult:
        """点击生成按钮开始生成"""
        try:
            try:
                names = await self.page.evaluate('() => performance.getEntriesByType("resource").map(e => e.name)')
                self.pre_perf_names = set(names or [])
            except Exception:
                self.pre_perf_names = set()
            if self.send_via_enter:
                try:
                    self.logger.info("使用回车发送进行生成")
                    try:
                        await self.page.locator('textarea.lv-textarea').first.focus()
                    except Exception:
                        pass
                    await self.page.keyboard.press('Enter')
                    try:
                        await self.page.wait_for_function(
                            '''() => {
                                const stopBtn = document.querySelector('button:has-text("停止"), button:has-text("Stop")');
                                if (stopBtn) return true;
                                const sendBtn = document.querySelector('button.lv-btn.lv-btn-primary.lv-btn-size-default.lv-btn-shape-circle.lv-btn-icon-only.submit-button-_3B9GU.submit-button-FEaBl7');
                                if (!sendBtn) return false;
                                const dis = sendBtn.classList.contains('lv-btn-disabled') || sendBtn.getAttribute('disabled') !== null;
                                return !!dis;
                            }''', timeout=2000
                        )
                    except Exception:
                        self.logger.info("回车发送未生效，回退为按钮点击")
                        self.send_via_enter = False
                        await self.page.wait_for_selector('button.lv-btn.lv-btn-primary.lv-btn-size-default.lv-btn-shape-circle.lv-btn-icon-only.submit-button-_3B9GU.submit-button-FEaBl7:not(.lv-btn-disabled)', timeout=60000)
                        await self.page.evaluate('''() => { const b = document.querySelector('button.lv-btn.lv-btn-primary.lv-btn-size-default.lv-btn-shape-circle.lv-btn-icon-only.submit-button-_3B9GU.submit-button-FEaBl7:not(.lv-btn-disabled)'); if (b) b.click(); }''')
                    self.generation_started = True
                    self.generation_started_at = time.time()
                    try:
                        self.generation_started_perf = await self.page.evaluate('performance.now()')
                    except Exception:
                        self.generation_started_perf = None
                    try:
                        self.pre_gen_image_urls = await self.extract_all_images_from_dom()
                        self.logger.debug("记录生成前页面图片快照", count=len(self.pre_gen_image_urls))
                    except Exception as e:
                        self.logger.debug(f"生成前快照记录失败: {e}")
                    await asyncio.sleep(2)
                    return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="开始生成")
                except Exception as e:
                    self.logger.debug(f"回车发送失败，回退为按钮点击: {e}")
            self.logger.info("等待生成按钮可用并点击")
            await self.page.wait_for_selector('button.lv-btn.lv-btn-primary.lv-btn-size-default.lv-btn-shape-circle.lv-btn-icon-only.submit-button-_3B9GU.submit-button-FEaBl7:not(.lv-btn-disabled)', timeout=60000)
            
            # 使用JavaScript强制点击生成按钮
            self.logger.info("使用JavaScript强制点击生成按钮")
            await self.page.evaluate('''
                () => {
                    const button = document.querySelector('button.lv-btn.lv-btn-primary.lv-btn-size-default.lv-btn-shape-circle.lv-btn-icon-only.submit-button-_3B9GU.submit-button-FEaBl7:not(.lv-btn-disabled)');
                    if (button) {
                        button.click();
                        return true;
                    }
                    return false;
                }
            ''')
            
            self.logger.info("已点击生成按钮，开始生成图片")
            self.generation_started = True
            self.generation_started_at = time.time()
            try:
                self.generation_started_perf = await self.page.evaluate('performance.now()')
            except Exception:
                self.generation_started_perf = None
            # 记录生成开始时的容器图片快照，避免把历史图片当作本次结果
            try:
                self.pre_gen_image_urls = await self.extract_all_images_from_dom()
                self.logger.debug("记录生成前页面图片快照", count=len(self.pre_gen_image_urls))
            except Exception as e:
                self.logger.debug(f"生成前快照记录失败: {e}")
            await asyncio.sleep(2)
            return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="开始生成")
        except Exception as e:
            self.logger.error("点击生成按钮失败", error=str(e))
            return TaskResult(
                code=ErrorCode.WEB_INTERACTION_FAILED.value,
                data=None,
                message="点击生成按钮失败",
                error_details={"error": str(e)}
            )

    async def extract_fullsize_images_from_dom(self) -> List[str]:
        """专门提取1080:1080大图的版本"""
        try:
            urls = await self.page.evaluate(r'''() => {
                const results = new Set();
                
                // 方法1: 直接从图片查看器中获取大图
                const imagePlayers = Array.from(document.querySelectorAll('div[class*="image-player"]'));
                for (const player of imagePlayers) {
                    const imgs = Array.from(player.querySelectorAll('img[data-apm-action*="detail-card"], img[class*="image-"]'));
                    for (const img of imgs) {
                        const src = img.src || '';
                        // 只收集包含1080:1080的图片
                        if (src.includes('aigc_resize:1080:1080')) {
                            results.add(src);
                        }
                    }
                }
                
                // 方法2: 查找所有包含1080:1080的图片
                const allImgs = Array.from(document.querySelectorAll('img'));
                for (const img of allImgs) {
                    let src = img.src || '';
                    const srcset = img.getAttribute('srcset') || '';
                    
                    // 优先使用srcset中的1080:1080版本
                    if (srcset) {
                        try {
                            const candidates = srcset.split(',')
                                .map(s => s.trim().split(' ')[0])
                                .filter(Boolean)
                                .filter(url => url.includes('aigc_resize:1080:1080'));
                            if (candidates.length) {
                                src = candidates[candidates.length - 1];
                            }
                        } catch {}
                    }
                    
                    // 只添加1080:1080的图片
                    if (src.includes('aigc_resize:1080:1080') && 
                        (img.naturalWidth || 0) >= 1000 && (img.naturalHeight || 0) >= 1000) {
                        results.add(src);
                    }
                }
                
                return Array.from(results);
            }''')
            
            # 确保只返回1080:1080的图片
            filtered_urls = [url for url in (urls or []) if 'aigc_resize:1080:1080' in url]
            try:
                if self.pre_gen_image_urls:
                    prev = set(self.pre_gen_image_urls)
                    filtered_urls = [u for u in filtered_urls if u not in prev]
            except Exception:
                pass
            
            # 如果没有找到1080:1080的图片，尝试从网络请求中获取
            if not filtered_urls:
                filtered_urls = await self.extract_1080_images_from_network()
                
            return filtered_urls
            
        except Exception as e:
            self.logger.debug(f"提取1080:1080大图失败: {e}")
            return []

    async def extract_1080_images_from_network(self) -> List[str]:
        """从网络请求中专门提取1080:1080的大图"""
        try:
            resources = await self.page.evaluate('''() => {
                try {
                    const entries = performance.getEntriesByType('resource') || [];
                    return entries.filter(e => e.initiatorType === 'img').map(e => ({ name: e.name, startTime: e.startTime||0 }));
                } catch (e) { return []; }
            }''')
            urls = []
            try:
                for r in (resources or []):
                    n = (r.get('name') if isinstance(r, dict) else None)
                    st = (r.get('startTime') if isinstance(r, dict) else 0)
                    if not n:
                        continue
                    if 'aigc_resize:1080:1080' in n:
                        urls.append((n, st or 0))
            except Exception:
                urls = []
            try:
                if self.generation_started_perf:
                    urls = [u for (u, st) in urls if st >= (self.generation_started_perf or 0)]
                else:
                    base = set(self.pre_perf_names or [])
                    urls = [u for (u, _st) in urls if u not in base]
            except Exception:
                urls = [u for (u, _st) in urls]
            return list(dict.fromkeys(urls))
            
        except Exception as e:
            self.logger.debug(f"从网络请求提取1080大图失败: {e}")
            return []

    async def wait_for_1080_image_load(self, timeout: float = 10.0) -> List[str]:
        """等待1080:1080大图加载完成"""
        try:
            # 等待包含1080:1080的图片加载
            await self.page.wait_for_function(
                '''() => {
                    const imgs = Array.from(document.querySelectorAll('img'));
                    return imgs.some(img => {
                        const src = img.src || '';
                        return src.includes('aigc_resize:1080:1080') && 
                               img.complete && 
                               (img.naturalWidth || 0) > 0;
                    });
                }''',
                timeout=timeout * 1000
            )
            
            # 提取所有1080:1080图片
            return await self.extract_fullsize_images_from_dom()
            
        except Exception as e:
            self.logger.debug(f"等待1080图片加载超时: {e}")
            return []

    async def click_preview_and_get_1080_image(self):
        """严格顺序执行：
        预览图 → 中图 → 等待加载 → 点击中图 → 大图 → 获取URL → 关闭大图 → 关闭中图 → 下一张
        并包含完整日志（第几张 / 总数）
        """

        results = []

        # ================================
        # 0）获取所有预览图
        # ================================
        thumbs = self.page.locator(
            'img[data-apm-action*="record-card"], '
            'div[class*="image-card-container"] img, '
            'div[class*="responsive-common-grid-"] img'
        )
        try:
            count = await thumbs.count()
        except:
            count = 0

        self.logger.info(f"🔍 检测到预览图数量: {count}")

        if count == 0:
            self.logger.warning("⚠ 没有可点击的预览图，流程结束")
            return results

        # ================================
        # 循环处理每一张预览图
        # ================================
        for i in range(count):
            index = i + 1
            self.logger.info(f"➡ 开始处理第 {index} / {count} 张预览图")

            # 用于捕获 4096 大图的网络请求
            hd4096 = set()
            def on_resp(res):
                u = res.url
                if "aigc_resize:4096" in u or "/4096:" in u:
                    hd4096.add(u)
                    self.logger.info(f"📡 捕获到 4096 请求: {u}")

            try:
                self.page.on("response", on_resp)
            except:
                pass

            # ================================
            # 1）点击预览图
            # ================================
            try:
                el = thumbs.nth(i)
                await el.scroll_into_view_if_needed()
                await el.click()
                self.logger.info(f"🖱 点击第 {index} 张预览图成功")
            except Exception as e:
                self.logger.warning(f"⚠ 第 {index} 张预览图点击失败，将跳过该图: {e}")
                continue

            # ================================
            # 2）等待中图加载完成
            # ================================
            try:
                await self.page.locator('div[class*="image-player"]').first.wait_for(
                    state="visible", timeout=8000
                )
                await self.page.wait_for_function(r'''() => {
                    const img = document.querySelector('div[class*="image-player"] img');
                    if (!img) return false;
                    const s = img.getAttribute("src") || "";
                    return img.complete && (img.naturalWidth||0) > 0 && /^https?:/.test(s);
                }''', timeout=8000)
                self.logger.info(f"🖼 第 {index} 张中图加载完成")
            except:
                self.logger.warning(f"⚠ 第 {index} 张中图未正常加载，关闭后继续下一张")
                try: await self.page.keyboard.press("Escape")
                except: pass
                continue

            # ================================
            # 3）点击中图放大
            # ================================
            opened = False
            try:
                middle_img = self.page.locator(
                    'div[class*="image-player"] img[data-apm-action*="detail-card"], '
                    'div[class*="image-player"] img'
                ).first
                await middle_img.click()
                opened = True
                self.logger.info(f"🔍 第 {index} 张点击中图 → 放大成功")
            except:
                self.logger.warning(f"⚠ 第 {index} 张中图点击失败，将跳过该图")
                try: await self.page.keyboard.press("Escape")
                except: pass
                continue

            # ================================
            # 4）等待大图加载（优先监听 4096）
            # ================================
            picked = None
            start = time.time()
            while time.time() - start < 4:
                if hd4096:
                    picked = next(iter(hd4096))
                    self.logger.info(f"🎯 第 {index} 张成功捕获 4096 大图 URL")
                    break
                await asyncio.sleep(0.3)

            # 如果没捕获到 4096，尝试从 DOM 抓取
            if not picked:
                try:
                    urls = await self.extract_highres_from_player()
                    if urls:
                        picked = urls[0]
                        self.logger.info(f"📥 第 {index} 张从 DOM 提取到大图 URL: {picked}")
                except:
                    pass

            # ================================
            # 5）记录大图 URL
            # ================================
            if picked:
                try:
                    prev = set(self.pre_gen_image_urls or [])
                    if picked in prev:
                        picked = None
                except Exception:
                    pass
            if picked:
                results.append(picked)
            else:
                self.logger.warning(f"⚠ 第 {index} 张未获取到大图 URL")

            # ================================
            # 6）关闭大图
            # ================================
            try:
                await self.page.keyboard.press("Escape")
                await asyncio.sleep(0.2)
                self.logger.info(f"❌ 已关闭第 {index} 张的大图")
            except:
                pass

            # 7）等待 2 秒（避免卡顿）
            await asyncio.sleep(2)

            # 8）关闭中图
            try:
                await self.page.keyboard.press("Escape")
                await asyncio.sleep(0.2)
                self.logger.info(f"❌ 已关闭第 {index} 张的中图")
            except:
                pass

            self.logger.info(f"✅ 第 {index} / {count} 张预览图处理完成\n")

        # ================================
        # 全部结束
        # ================================
        self.logger.info(f"🎉 所有预览图处理完毕，共获取到 {len(results)} 张大图")

        return results


    async def extract_generated_images_from_dom(self) -> List[str]:
        """从 image-nodes-container-* 容器中提取生成图片URL（过滤图标/头像）"""
        try:
            urls = await self.page.evaluate(r'''() => {
                const results = new Set();
                const containers = Array.from(document.querySelectorAll('div[class^="nodes-container-"] , div[class^="image-nodes-container-"]'));
                const getBgUrl = (style) => {
                    try {
                        const m = /url\(["']?(.*?)["']?\)/.exec(style.backgroundImage || '');
                        return m ? m[1] : null;
                    } catch { return null; }
                };
                for (const c of containers) {
                    // 图片标签
                    const imgs = Array.from(c.querySelectorAll('img'));
                    for (const img of imgs) {
                        const w = img.naturalWidth || 0;
                        const h = img.naturalHeight || 0;
                        const src = img.src || '';
                        const srcset = img.getAttribute('srcset') || '';
                        let best = src;
                        if (srcset) {
                            try {
                                const candidates = srcset.split(',').map(s => s.trim().split(' ')[0]).filter(Boolean);
                                if (candidates.length) {
                                    best = candidates[candidates.length - 1];
                                }
                            } catch {}
                        }
                        if (w >= 256 && h >= 256 && best && !best.startsWith('data:image/png;base64,')) {
                            results.add(best);
                        }
                    }
                    // 背景图片样式
                    const styled = Array.from(c.querySelectorAll('*'));
                    for (const el of styled) {
                        const url = getBgUrl(getComputedStyle(el));
                        if (url) {
                            let u = url;
                            if (u.startsWith('//')) { u = window.location.protocol + u; }
                            if (u.startsWith('http') || u.startsWith('https')) {
                                results.add(u);
                            }
                        }
                    }
                }
                return Array.from(results);
            }''')
            urls = urls or []
            if self.pre_gen_image_urls:
                try:
                    prev = set(self.pre_gen_image_urls)
                    urls = [u for u in urls if u not in prev]
                except Exception:
                    pass
            return urls
        except Exception as e:
            self.logger.debug(f"DOM提取生成图片失败: {e}")
            return []

    async def extract_all_images_from_dom(self) -> List[str]:
        try:
            urls = await self.page.evaluate(r'''() => {
                const results = new Set();
                const getBgUrl = (style) => {
                    try {
                        const m = /url\(["']?(.*?)["']?\)/.exec(style.backgroundImage || '');
                        return m ? m[1] : null;
                    } catch { return null; }
                };
                const imgs = Array.from(document.querySelectorAll('img'));
                for (const img of imgs) {
                    const w = img.naturalWidth || 0;
                    const h = img.naturalHeight || 0;
                    const src = img.src || '';
                    const srcset = img.getAttribute('srcset') || '';
                    let best = src;
                    if (srcset) {
                        try {
                            const candidates = srcset.split(',').map(s => s.trim().split(' ')[0]).filter(Boolean);
                            if (candidates.length) {
                                best = candidates[candidates.length - 1];
                            }
                        } catch {}
                    }
                    if (w >= 256 && h >= 256 && best && !best.startsWith('data:image/png;base64,')) {
                        results.add(best);
                    }
                }
                const styled = Array.from(document.querySelectorAll('*'));
                for (const el of styled) {
                    const url = getBgUrl(getComputedStyle(el));
                    if (url) {
                        let u = url;
                        if (u.startsWith('//')) { u = window.location.protocol + u; }
                        if (u.startsWith('http') || u.startsWith('https')) {
                            results.add(u);
                        }
                    }
                }
                return Array.from(results);
            }''')
            return urls or []
        except Exception as e:
            self.logger.debug(f"全页DOM提取生成图片失败: {e}")
            return []

    async def soft_refresh_page(self):
        try:
            if self.did_soft_refresh:
                return
            self.logger.info("执行一次页面刷新用于补齐UI")
            await self.page.reload(timeout=60000)
            await self.page.wait_for_load_state('networkidle', timeout=60000)
            await asyncio.sleep(1)
            self.did_soft_refresh = True
        except Exception as e:
            self.logger.debug(f"页面刷新失败: {e}")

    async def scroll_to_bottom_safe(self):
        try:
            await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(0.3)
            self.logger.debug("已执行窗口滚动到底部")
        except Exception as e:
            self.logger.debug(f"滚动到底部失败: {e}")

    async def ensure_results_view(self):
        try:
            url = self.page.url or ""
            need_back = ("/ai-tool/personal" in url) or True
            if need_back:
                locator = self.page.locator('button:has-text("See results"), [role="button"]:has-text("See results"), button:has-text("查看结果"), [role="button"]:has-text("查看结果")')
                if await locator.count() > 0:
                    try:
                        await locator.first.click()
                    except Exception:
                        await locator.first.dispatch_event('click')
                    await self.page.wait_for_load_state('networkidle', timeout=60000)
                    try:
                        await self.page.wait_for_selector('div[class^="nodes-container-"]', timeout=10000)
                    except Exception:
                        pass
                    try:
                        await self.scroll_to_bottom_safe()
                        self.did_scroll_bottom = True
                    except Exception:
                        pass
        except Exception as e:
            self.logger.debug(f"返回结果视图失败: {e}")

    async def is_generation_ready_by_slots(self) -> bool:
        try:
            slots = self.page.locator('div[class^="record-bottom-slots-"]')
            if await slots.count() == 0:
                return False
            svg_in_slots = self.page.locator('div[class^="record-bottom-slots-"] svg')
            if await svg_in_slots.count() > 0:
                return True
            regen = self.page.locator('div[class*="card-bottom-button-view-"]:has-text("Regenerate"), button:has-text("Regenerate")')
            return (await regen.count()) > 0
        except Exception:
            return False

    async def scroll_to_bottom(self):
        try:
            btn = self.page.locator('button:has-text("Go to bottom"), [role="button"]:has-text("Go to bottom")')
            if await btn.count() > 0:
                try:
                    await btn.first.click()
                except Exception:
                    await btn.first.dispatch_event('click')
                await asyncio.sleep(0.3)
                self.logger.debug("已点击 Go to bottom 按钮")
                return
            clicked = await self.page.evaluate(r'''() => {
                const all = Array.from(document.querySelectorAll('*'));
                for (const el of all) {
                    const t = (el.innerText || el.textContent || '').trim();
                    if (/Go to bottom/i.test(t)) {
                        try { el.click(); return true; } catch { }
                    }
                }
                return false;
            }''')
            if clicked:
                await asyncio.sleep(0.3)
                self.logger.debug("已通过文本匹配点击 Go to bottom")
                return
            await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(0.3)
            self.logger.debug("已执行窗口滚动到底部")
        except Exception as e:
            self.logger.debug(f"滚动到底部失败: {e}")

    async def extract_new_images_by_performance(self) -> List[str]:
        try:
            if self.generation_started_perf is None:
                return []
            urls = await self.page.evaluate(r'''(since) => {
                try {
                    const entries = performance.getEntriesByType('resource') || [];
                    const results = new Set();
                    for (const e of entries) {
                        const t = (e.responseEnd || e.duration || 0);
                        const name = e.name || '';
                        const type = e.initiatorType || '';
                        if (t > since && name && (type === 'img' || name.match(/\.(png|jpg|jpeg|webp)(\?|$)/i))) {
                            if (name.startsWith('//')) {
                                results.add(location.protocol + name);
                            } else if (name.startsWith('http') || name.startsWith('https')) {
                                results.add(name);
                            }
                        }
                    }
                    return Array.from(results);
                } catch { return []; }
            }''', self.generation_started_perf)
            return urls or []
        except Exception as e:
            self.logger.debug(f"性能条目提取生成图片失败: {e}")
            return []

    async def extract_images_near_latest_regenerate(self) -> List[str]:
        try:
            urls = await self.page.evaluate(r'''() => {
                const collectFrom = (root) => {
                    const set = new Set();
                    const imgs = Array.from(root.querySelectorAll('img'));
                    for (const img of imgs) {
                        const src = img.getAttribute('src') || '';
                        const srcset = img.getAttribute('srcset') || '';
                        let best = src;
                        if (srcset) {
                            try {
                                const candidates = srcset.split(',').map(s => s.trim().split(' ')[0]).filter(Boolean);
                                if (candidates.length) best = candidates[candidates.length - 1];
                            } catch {}
                        }
                        if (best && (best.startsWith('http') || best.startsWith('https'))) set.add(best);
                    }
                    return Array.from(set);
                };
                // 优先使用最新的 nodes-container（当前生成分组容器）
                const nodes = Array.from(document.querySelectorAll('div[class^="nodes-container-"]'));
                if (nodes.length) {
                    const last = nodes[nodes.length - 1];
                    const grid = last.querySelector('div[class*="responsive-common-grid-"]') || last;
                    const thumbs = collectFrom(grid);
                    if (thumbs.length) return thumbs;
                }
                // 回退：根据 Regenerate 按钮向上找分组
                const btns = Array.from(document.querySelectorAll('button, [role="button"]'))
                    .filter(b => /Regenerate|重新生成/i.test(b.textContent || ''));
                if (btns.length) {
                    const lastBtn = btns[btns.length - 1];
                    let node = lastBtn;
                    for (let i = 0; i < 12 && node; i++) {
                        node = node.parentElement;
                        if (!node) break;
                        const thumbs = collectFrom(node);
                        if (thumbs.length) return thumbs;
                    }
                }
                return collectFrom(document.body);
            }''')
            return urls or []
        except Exception as e:
            self.logger.debug(f"邻近Regenerate提取生成图片失败: {e}")
            return []

    async def click_thumbs_and_collect_fullsize(self, thumb_urls: List[str]) -> List[str]:
        try:
            if not thumb_urls:
                return []
            results = []
            seen = set()
            # 尝试限定在最新 nodes-container 作用域内点击
            container = self.page.locator('div[class^="nodes-container-"]').last
            for u in thumb_urls:
                if not u:
                    continue
                token = None
                try:
                    last = u.split('/')[-1]
                    token = last.split('~')[0]
                except Exception:
                    token = None
                locator = None
                try:
                    if token:
                        locator = container.locator(f'img[src*="{token}"]') if container else None
                        if not locator or await locator.count() == 0:
                            locator = self.page.locator(f'img[src*="{token}"]')
                    else:
                        const_short = u[:64]
                        locator = container.locator(f'img[src*="{const_short}"]') if container else None
                        if not locator or await locator.count() == 0:
                            locator = self.page.locator(f'img[src*="{const_short}"]')
                    if await locator.count() == 0:
                        continue
                    el = locator.first
                    try:
                        await el.scroll_into_view_if_needed()
                    except Exception:
                        pass
                    try:
                        await el.click()
                    except Exception:
                        await el.dispatch_event('click')
                    try:
                        await self.page.locator('div[class*="image-player"]').first.wait_for(state='visible', timeout=8000)
                    except Exception:
                        pass
                    try:
                        await self.page.locator('div[class*="image-player"] img[data-apm-action*="detail-card"], div[class*="image-player"] img').first.wait_for(state='visible', timeout=8000)
                    except Exception:
                        pass
                    try:
                        await self.page.wait_for_function(r'''() => {
                            const root = document.querySelector('div[class*="image-player"]');
                            if (!root) return false;
                            const img = root.querySelector('img[data-apm-action*="detail-card"]') || root.querySelector('img');
                            if (!img) return false;
                            const s = img.getAttribute('src') || '';
                            return img.complete && (img.naturalWidth||0)>0 && /^https?:/.test(s);
                        }''', timeout=10000)
                    except Exception:
                        pass
                    try:
                        await self.page.evaluate(r'''() => {
                            const root = document.querySelector('div[class*="image-player"]');
                            if (root) { root.scrollTop = 0; root.scrollTop = root.scrollHeight; root.scrollTop = 0; }
                        }''')
                    except Exception:
                        pass
                    try:
                        detail = await self.wait_and_extract_detail_card_from_player(5.0)
                        for src in detail:
                            if src and (src.startswith('http') or src.startswith('https')) and src not in seen:
                                seen.add(src)
                                results.append(src)
                    except Exception:
                        pass
                except Exception:
                    pass
                try:
                    await self.page.keyboard.press('Escape')
                    await asyncio.sleep(0.3)
                except Exception:
                    pass
            return results
        except Exception as e:
            self.logger.debug(f"循环点击预览提取大图失败: {e}")
            return []

    async def collect_fullsize_from_nodes_container(self, max_click: int = 20) -> List[str]:
        try:
            results = []
            seen = set()
            container = self.page.locator('div[class^="nodes-container-"]').last
            if await container.count() == 0:
                return []
            thumbs = container.locator('img[data-apm-action*="record-card"]')
            if await thumbs.count() == 0:
                thumbs = container.locator('div[class*="image-card-container"] img')
            if await thumbs.count() == 0:
                thumbs = container.locator('div[class*="responsive-common-grid-"] img')
            if await thumbs.count() == 0:
                thumbs = container.locator('img')
            count = await thumbs.count()
            limit = min(count, max_click)
            for i in range(limit):
                el = thumbs.nth(i)
                try:
                    await el.scroll_into_view_if_needed()
                except Exception:
                    pass
                try:
                    await el.click()
                except Exception:
                    await el.dispatch_event('click')
                try:
                    await self.page.locator('div[class*="image-player"]').first.wait_for(state='visible', timeout=8000)
                except Exception:
                    pass
                try:
                    await self.page.locator('div[class*="image-player"] img[data-apm-action*="detail-card"], div[class*="image-player"] img').first.wait_for(state='visible', timeout=8000)
                except Exception:
                    pass
                try:
                    await self.page.wait_for_function(r'''() => {
                        const root = document.querySelector('div[class*="image-player"]');
                        if (!root) return false;
                        const img = root.querySelector('img[data-apm-action*="detail-card"]') || root.querySelector('img');
                        if (!img) return false;
                        const s = img.getAttribute('src') || '';
                        return img.complete && (img.naturalWidth||0)>0 && /^https?:/.test(s);
                    }''', timeout=10000)
                except Exception:
                    pass
                try:
                    await self.page.evaluate(r'''() => {
                        const root = document.querySelector('div[class*="image-player"]');
                        if (root) { root.scrollTop = 0; root.scrollTop = root.scrollHeight; root.scrollTop = 0; }
                    }''')
                except Exception:
                    pass
                prev_count = len(results)
                prev_count = len(results)
                try:
                    detail = await self.wait_and_extract_detail_card_from_player(5.0)
                    for src in detail:
                        if src and (src.startswith('http') or src.startswith('https')) and src not in seen:
                            seen.add(src)
                            results.append(src)
                except Exception:
                    pass
                try:
                    if len(results) == prev_count:
                        img_loaded = self.page.locator('div[class*\"image-player\"] img[data-apm-action*=\"detail-card\"], div[class*\"image-player\"] img').first
                        overlay = self.page.locator('div[class*\"image-player-image-\"]').first
                        if await overlay.count() > 0:
                            try:
                                await overlay.hover()
                            except Exception:
                                pass
                        if await img_loaded.count() > 0:
                            try:
                                await img_loaded.hover()
                            except Exception:
                                pass
                            try:
                                await overlay.click()
                            except Exception:
                                try:
                                    await img_loaded.click()
                                except Exception:
                                    await img_loaded.dispatch_event('click')
                            try:
                                again = await self.wait_and_extract_detail_card_from_player(4.0)
                                for src in again:
                                    if src and (src.startswith('http') or src.startswith('https')) and src not in seen:
                                        seen.add(src)
                                        results.append(src)
                            except Exception:
                                pass
                except Exception:
                    pass
                try:
                    if len(results) == prev_count:
                        img_loaded = self.page.locator('div[class*\"image-player\"] img[data-apm-action*=\"detail-card\"], div[class*\"image-player\"] img').first
                        overlay = self.page.locator('div[class*\"image-player-image-\"]').first
                        if await overlay.count() > 0:
                            try:
                                await overlay.hover()
                            except Exception:
                                pass
                        if await img_loaded.count() > 0:
                            try:
                                await img_loaded.hover()
                            except Exception:
                                pass
                            try:
                                await overlay.click()
                            except Exception:
                                try:
                                    await img_loaded.click()
                                except Exception:
                                    await img_loaded.dispatch_event('click')
                            try:
                                again = await self.wait_and_extract_detail_card_from_player(4.0)
                                for src in again:
                                    if src and (src.startswith('http') or src.startswith('https')) and src not in seen:
                                        seen.add(src)
                                        results.append(src)
                            except Exception:
                                pass
                except Exception:
                    pass
                
                try:
                    await self.page.keyboard.press('Escape')
                    await asyncio.sleep(0.2)
                except Exception:
                    pass
            return results
        except Exception as e:
            self.logger.debug(f"nodes容器内点击预览提取大图失败: {e}")
            return []

    async def collect_fullsize_from_current_dialog(self, max_click_per_container: int = 20) -> List[str]:
        try:
            dialog = self.page.locator('div[class*="agentic-record-content-"][class*="completed-"]').last
            if await dialog.count() == 0:
                dialog = self.page.locator('div[class*="agentic-record-"]').last
                if await dialog.count() == 0:
                    return []
            containers = dialog.locator('div[class^="nodes-container-"]')
            if await containers.count() == 0:
                containers = dialog.locator('div[class^="image-nodes-container-"]')
            total = await containers.count()
            if total == 0:
                return []
            results = []
            seen = set()
            limit_containers = total
            for ci in range(limit_containers):
                c = containers.nth(ci)
                thumbs = c.locator('img[data-apm-action*="record-card"]')
                if await thumbs.count() == 0:
                    thumbs = c.locator('div[class*="image-card-container"] img')
                if await thumbs.count() == 0:
                    thumbs = c.locator('div[class*="responsive-common-grid-"] img')
                if await thumbs.count() == 0:
                    thumbs = c.locator('img')
                count = await thumbs.count()
                click_limit = min(count, max_click_per_container)
                for i in range(click_limit):
                    el = thumbs.nth(i)
                    try:
                        await el.scroll_into_view_if_needed()
                    except Exception:
                        pass
                    try:
                        await el.click()
                    except Exception:
                        await el.dispatch_event('click')
                    try:
                        await self.page.locator('div[class*="image-player"]').first.wait_for(state='visible', timeout=8000)
                    except Exception:
                        pass
                    try:
                        await self.page.locator('div[class*="image-player"] img[data-apm-action*="detail-card"], div[class*="image-player"] img').first.wait_for(state='visible', timeout=8000)
                    except Exception:
                        pass
                    try:
                        await self.page.wait_for_function(r'''() => {
                            const root = document.querySelector('div[class*="image-player"]');
                            if (!root) return false;
                            const img = root.querySelector('img[data-apm-action*="detail-card"]') || root.querySelector('img');
                            if (!img) return false;
                            const s = img.getAttribute('src') || '';
                            return img.complete && (img.naturalWidth||0)>0 && /^https?:/.test(s);
                        }''', timeout=10000)
                    except Exception:
                        pass
                    try:
                        await self.page.evaluate(r'''() => {
                            const root = document.querySelector('div[class*="image-player"]');
                            if (root) { root.scrollTop = 0; root.scrollTop = root.scrollHeight; root.scrollTop = 0; }
                        }''')
                    except Exception:
                        pass
                try:
                    detail = await self.wait_and_extract_detail_card_from_player(5.0)
                    for src in detail:
                        if src and (src.startswith('http') or src.startswith('https')) and src not in seen:
                            seen.add(src)
                            results.append(src)
                except Exception:
                    pass
                    try:
                        await self.page.keyboard.press('Escape')
                        await asyncio.sleep(0.2)
                    except Exception:
                        pass
            return results
        except Exception as e:
            self.logger.debug(f"当前对话内点击预览提取大图失败: {e}")
            return []
    
    async def extract_highres_from_player(self) -> List[str]:
        try:
            urls = await self.page.evaluate(r'''() => {
                const root = document.querySelector('div[class*="image-player"]') || document.body;
                const detailImgs = Array.from(root.querySelectorAll('img[data-apm-action*="detail-card"]'));
                if (detailImgs.length) {
                    let best = null, area = 0;
                    for (const img of detailImgs) {
                        const src = img.getAttribute('src') || '';
                        const srcset = img.getAttribute('srcset') || '';
                        let u = src;
                        if (srcset) {
                            const candidates = srcset.split(',').map(s => s.trim().split(' ')[0]).filter(Boolean);
                            if (candidates.length) u = candidates[candidates.length - 1];
                        }
                        if (!u || !(u.startsWith('http') || u.startsWith('https'))) continue;
                        let a = (img.naturalWidth || 0) * (img.naturalHeight || 0);
                        const m = /aigc_resize:(\d+):(\d+)/.exec(u);
                        if (m) {
                            const w = parseInt(m[1], 10) || 0;
                            const h = parseInt(m[2], 10) || 0;
                            const parsed = w * h;
                            if (parsed > 0) a = Math.max(a, parsed);
                        }
                        if (a > area) { area = a; best = u; }
                    }
                    if (best) return [best];
                }
                const previews = Array.from(root.querySelectorAll('img[class^="preview-"][data-loaded="true"]'));
                if (previews.length) {
                    const u = previews[0].getAttribute('src') || '';
                    if (u && (u.startsWith('http') || u.startsWith('https'))) return [u];
                }
                const imgs = Array.from(root.querySelectorAll('img'));
                let best = null;
                let area = 0;
                for (const img of imgs) {
                    const src = img.getAttribute('src') || '';
                    if (!src || !(src.startsWith('http') || src.startsWith('https'))) continue;
                    const w = img.naturalWidth || 0;
                    const h = img.naturalHeight || 0;
                    const a = w * h;
                    if (a > area) { area = a; best = src; }
                }
                return best ? [best] : [];
            }''')
            urls = urls or []
            try:
                urls = [u for u in urls if self.is_highres_url(u)]
            except Exception:
                pass
            return urls
        except Exception:
            return []

    async def wait_and_extract_highres_from_player(self, min_wait: float = 3.0, max_wait: float = 5.0) -> List[str]:
        try:
            start = time.time()
            try:
                await asyncio.sleep(min_wait)
            except Exception:
                pass
            urls = await self.extract_highres_from_player()
            if urls:
                return urls
            while (time.time() - start) < max_wait:
                try:
                    await asyncio.sleep(0.5)
                except Exception:
                    pass
                urls = await self.extract_highres_from_player()
                if urls:
                    return urls
            return []
        except Exception:
            return []

    async def get_player_best_info(self) -> dict:
        try:
            info = await self.page.evaluate(r'''() => {
                const root = document.querySelector('div[class*="image-player"]') || document.body;
                const detailImgs = Array.from(root.querySelectorAll('img[data-apm-action*="detail-card"]'));
                let bestSrc = null;
                let bestArea = 0;
                if (detailImgs.length) {
                    for (const img of detailImgs) {
                        const src = img.getAttribute('src') || '';
                        if (!src || !(src.startsWith('http') || src.startsWith('https'))) continue;
                        let a = (img.naturalWidth || 0) * (img.naturalHeight || 0);
                        const m = /aigc_resize:(\d+):(\d+)/.exec(src);
                        if (m) {
                            const w = parseInt(m[1], 10) || 0;
                            const h = parseInt(m[2], 10) || 0;
                            const parsed = w * h;
                            if (parsed > 0) a = Math.max(a, parsed);
                        }
                        if (a > bestArea) { bestArea = a; bestSrc = src; }
                    }
                }
                const previews = Array.from(root.querySelectorAll('img[class^="preview-"][data-loaded="true"]'));
                if (previews.length && !bestSrc) {
                    const img = previews[0];
                    bestSrc = img.getAttribute('src') || '';
                    bestArea = (img.naturalWidth || 0) * (img.naturalHeight || 0);
                }
                const imgs = Array.from(root.querySelectorAll('img'));
                for (const img of imgs) {
                    const src = img.getAttribute('src') || '';
                    if (!src || !(src.startsWith('http') || src.startsWith('https'))) continue;
                    const a = (img.naturalWidth || 0) * (img.naturalHeight || 0);
                    if (a > bestArea) { bestArea = a; bestSrc = src; }
                }
                return { src: bestSrc, area: bestArea };
            }''')
            return info or { 'src': None, 'area': 0 }
        except Exception:
            return { 'src': None, 'area': 0 }

    async def zoom_in_player(self) -> None:
        try:
            candidates = [
                'div[class*="image-player"] button:has-text("放大")',
                'div[class*="image-player"] [role="button"]:has-text("放大")',
                'div[class*="image-player"] button[aria-label*="放大"]',
                'div[class*="image-player"] [role="button"][aria-label*="放大"]',
                'div[class*="image-player"] button:has-text("Zoom in")',
                'div[class*="image-player"] [role="button"]:has-text("Zoom in")',
                'div[class*="image-player"] button[aria-label*="Zoom in"]',
                'div[class*="image-player"] [role="button"][aria-label*="Zoom in"]',
                'div[class*="image-player"] button[class*="zoom"]',
                'div[class*="image-player"] [class*="zoom"]',
            ]
            clicked = False
            for sel in candidates:
                try:
                    loc_all = self.page.locator(sel)
                    if await loc_all.count() > 0:
                        try:
                            await loc_all.first.click()
                            clicked = True
                            break
                        except Exception:
                            pass
                except Exception:
                    pass
            if not clicked:
                try:
                    img = self.page.locator('div[class*="image-player"] img[class^="preview-"]').first
                    if await img.count() == 0:
                        img = self.page.locator('div[class*="image-player"] img').first
                    if await img.count() > 0:
                        try:
                            await img.dblclick()
                            clicked = True
                        except Exception:
                            try:
                                await img.click()
                                await asyncio.sleep(0.1)
                                await img.click()
                                clicked = True
                            except Exception:
                                pass
                except Exception:
                    pass
        except Exception:
            pass

    async def close_zoom_player(self) -> None:
        try:
            candidates = [
                'div[class*="image-player"] button:has-text("缩小")',
                'div[class*="image-player"] [role="button"]:has-text("缩小")',
                'div[class*="image-player"] button[aria-label*="缩小"]',
                'div[class*="image-player"] [role="button"][aria-label*="缩小"]',
                'div[class*="image-player"] button:has-text("Zoom out")',
                'div[class*="image-player"] [role="button"]:has-text("Zoom out")',
                'div[class*="image-player"] button[aria-label*="Zoom out"]',
                'div[class*="image-player"] [role="button"][aria-label*="Zoom out"]',
                'div[class*="image-player"] button[class*="zoom"]',
                'div[class*="image-player"] [class*="zoom"]',
            ]
            for sel in candidates:
                try:
                    loc_all = self.page.locator(sel)
                    if await loc_all.count() > 0:
                        try:
                            await loc_all.first.click()
                            return
                        except Exception:
                            pass
                except Exception:
                    pass
            try:
                img = self.page.locator('div[class*="image-player"] img[class^="preview-"]').first
                if await img.count() == 0:
                    img = self.page.locator('div[class*="image-player"] img').first
                if await img.count() > 0:
                    try:
                        await img.dblclick()
                        return
                    except Exception:
                        try:
                            await img.click()
                            await asyncio.sleep(0.1)
                            await img.click()
                        except Exception:
                            pass
            except Exception:
                pass
        except Exception:
            pass

    async def close_preview_modal(self, timeout: float = 6.0) -> bool:
        try:
            root = self.page.locator('div[class*="image-player"]').first
            if await root.count() == 0:
                return True
            candidates = [
                'div[class*="image-player"] button:has-text("关闭")',
                'div[class*="image-player"] [role="button"]:has-text("关闭")',
                'div[class*="image-player"] button[aria-label*="关闭"]',
                'div[class*="image-player"] [role="button"][aria-label*="关闭"]',
                'div[class*="image-player"] button:has-text("Close")',
                'div[class*="image-player"] [role="button"]:has-text("Close")',
                'div[class*="image-player"] button[aria-label*="Close"]',
                'div[class*="image-player"] [role="button"][aria-label*="Close"]',
                'div[class*="image-player"] [class*="close"]',
                'div[class*="image-player-overlay"]',
            ]
            clicked = False
            for sel in candidates:
                try:
                    loc = self.page.locator(sel)
                    if await loc.count() > 0:
                        try:
                            await loc.first.click()
                            clicked = True
                            break
                        except Exception:
                            pass
                except Exception:
                    pass
            try:
                await self.page.keyboard.press('Escape')
            except Exception:
                pass
            try:
                await root.wait_for(state='hidden', timeout=int(timeout*1000))
                return True
            except Exception:
                return False
        except Exception:
            return False

    async def wait_for_player_preview_loaded(self, timeout: float = 8.0) -> None:
        try:
            await self.page.wait_for_function(r'''() => {
                const root = document.querySelector('div[class*="image-player"]');
                if (!root) return false;
                const img = root.querySelector('img[class^="preview-"]') || root.querySelector('img');
                if (!img) return false;
                const s = img.getAttribute('src') || '';
                return img.complete && (img.naturalWidth||0)>0 && /^https?:/.test(s);
            }''', timeout=int(timeout*1000))
        except Exception:
            pass

    def is_highres_url(self, u: str) -> bool:
        try:
            if not u:
                return False
            if not (u.startswith('http') or u.startswith('https')):
                return False
            return (
                ('aigc_resize:4096' in u) or
                ('/4096:' in u) or
                ('aigc_resize' in u and '4096' in u) or
                ('aigc_resize:1080:1080' in u)
            )
        except Exception:
            return False

    async def zoom_and_wait_extract_highres_from_player(self, min_wait: float = 3.0, max_wait: float = 5.0) -> List[str]:
        try:
            baseline = await self.get_player_best_info()
            try:
                await asyncio.sleep(min_wait)
            except Exception:
                pass
            current = await self.get_player_best_info()
            if current and (current.get('src') and (current.get('src') != baseline.get('src') or current.get('area', 0) > baseline.get('area', 0))):
                urls = await self.extract_highres_from_player()
                if urls:
                    return urls
            start = time.time()
            while (time.time() - start) < (max_wait - min_wait):
                try:
                    await asyncio.sleep(0.5)
                except Exception:
                    pass
                current = await self.get_player_best_info()
                if current and (current.get('src') and (current.get('src') != baseline.get('src') or current.get('area', 0) > baseline.get('area', 0))):
                    urls = await self.extract_highres_from_player()
                    if urls:
                        return urls
            urls = await self.extract_highres_from_player()
            return urls or []
        except Exception:
            return []

    async def extract_detail_card_from_player(self) -> List[str]:
        try:
            urls = await self.page.evaluate(r'''() => {
                const root = document.querySelector('div[class*="image-player"]') || document.body;
                const imgs = Array.from(root.querySelectorAll('img[data-apm-action*="detail-card"]'));
                if (!imgs.length) return [];
                let best = null;
                let area = 0;
                for (const img of imgs) {
                    const src = img.getAttribute('src') || '';
                    const srcset = img.getAttribute('srcset') || '';
                    let u = src;
                    if (srcset) {
                        const candidates = srcset.split(',').map(s => s.trim().split(' ')[0]).filter(Boolean);
                        if (candidates.length) u = candidates[candidates.length - 1];
                    }
                    if (!u || !(u.startsWith('http') || u.startsWith('https'))) continue;
                    let a = (img.naturalWidth || 0) * (img.naturalHeight || 0);
                    try {
                        const m = /aigc_resize:(\d+):(\d+)/.exec(u);
                        if (m) {
                            const w = parseInt(m[1], 10) || 0;
                            const h = parseInt(m[2], 10) || 0;
                            const parsed = w * h;
                            if (parsed > 0) a = Math.max(a, parsed);
                        }
                    } catch (e) {}
                    if (a > area) { area = a; best = u; }
                }
                return best ? [best] : [];
            }''')
            urls = urls or []
            try:
                urls = [u for u in urls if self.is_highres_url(u)]
            except Exception:
                pass
            return urls
        except Exception:
            return []

    async def wait_and_extract_detail_card_from_player(self, wait_seconds: float = 5.0) -> List[str]:
        try:
            try:
                await self.page.wait_for_function(r'''() => {
                    const root = document.querySelector('div[class*="image-player"]');
                    if (!root) return false;
                    const img = root.querySelector('img[data-apm-action*="detail-card"]') || root.querySelector('img');
                    if (!img) return false;
                    const s = img.getAttribute('src') || '';
                    return img.complete && (img.naturalWidth||0)>0 && /^https?:/.test(s);
                }''', timeout=int(wait_seconds*1000))
            except Exception:
                try:
                    await asyncio.sleep(wait_seconds)
                except Exception:
                    pass
            urls = await self.extract_detail_card_from_player()
            return urls or []
        except Exception:
            return []
    
    async def check_generation_finished_by_button_state(self) -> bool:
        """根据"发送/停止"按钮状态判断生成是否已结束。
        使用 Playwright locator 文本匹配，避免 evaluate 中的无效选择器。
        额外增加"Regenerate/重新生成"按钮出现作为完成信号。
        """
        try:
            # 检查是否存在"停止/Stop"按钮（生成中）
            stop_count = await self.page.locator('button:has-text("停止"), button:has-text("Stop")').count()

            # 检查"发送/Send"按钮是否存在且为 disabled（生成已结束、输入为空）
            send_locator = self.page.locator('button:has-text("发送"), button:has-text("Send")')
            send_count = await send_locator.count()
            send_disabled = False
            if send_count > 0:
                first = send_locator.first
                try:
                    send_disabled = await first.is_disabled()
                except Exception:
                    # 兼容非标准禁用：disabled 属性、aria-disabled、类名 lv-btn-disabled
                    disabled_attr = await first.get_attribute('disabled')
                    aria_disabled = await first.get_attribute('aria-disabled')
                    classes = await first.get_attribute('class') or ''
                    send_disabled = (disabled_attr is not None) or (aria_disabled == 'true') or ('lv-btn-disabled' in classes)

            # 检测是否出现"Regenerate/重新生成"按钮（常见于生成完成后显示）
            regen_locator = self.page.locator('[role="button"]:has-text("Regenerate"), button:has-text("Regenerate"), [role="button"]:has-text("重新生成"), button:has-text("重新生成")')
            regen_count = await regen_locator.count()
            regen_visible = False
            if regen_count > 0:
                try:
                    regen_visible = await regen_locator.first.is_visible()
                except Exception:
                    regen_visible = True  # 若取可见性异常，存在即可视为强信号

            # 完成条件：出现 Regenerate 按钮，或 无停止按钮且发送按钮禁用
            return regen_visible or ((stop_count == 0) and send_disabled)
        except Exception as e:
            self.logger.debug(f"按钮状态检测失败: {e}")
            return False
    
    async def wait_for_generation_complete(self, max_wait_time: int = 3600, highres_timeout: int = 60) -> TaskResult:
        """等待任务生成完成并获取1080:1080大图"""
        start_time = time.time()
        try:
            # 阶段1：等待 task_id 或页面生成提示
            while True:
                if self.task_id:
                    break
                try:
                    # 直接查找1080大图
                    urls = await self.extract_fullsize_images_from_dom()
                    if urls:
                        self.image_urls = urls
                        self.generation_completed = True
                        return TaskResult(
                            code=ErrorCode.SUCCESS.value, 
                            data=self.image_urls, 
                            message="成功获取1080:1080大图"
                        )
                except Exception:
                    pass
                await asyncio.sleep(1)
                if (time.time() - start_time) > max_wait_time:
                    break

            # 阶段2：检测页面引号图标，确认图片生成完成
            if self.task_id:
                self.logger.info("任务ID已获取，开始检测页面引号图标...")
                quote_start = time.time()
                quote_refreshed = False
                image_wait_start = None
                while (time.time() - quote_start) < max_wait_time:
                    try:
                        # 检测 class 中包含 card-icon-button 的图标元素
                        icons = await self.page.query_selector_all('div[class*="card-icon-button"] svg, div[class*="card-icon-button"] [role="img"], div[class*="card-icon-button"] [aria-label*="quote"]')
                        if icons and len(icons) > 0:
                            self.logger.info("✅ 检测到引号图标，准备获取1080大图...")
                            if image_wait_start is None:
                                image_wait_start = time.time()
                            
                            # 方法1: 直接提取1080大图
                            urls = await self.extract_fullsize_images_from_dom()
                            if urls:
                                self.image_urls = urls
                                self.generation_completed = True
                                return TaskResult(
                                    code=ErrorCode.SUCCESS.value,
                                    data=self.image_urls,
                                    message="直接提取1080:1080大图成功"
                                )
                            
                            # 方法2: 点击预览图获取大图
                            self.logger.info("尝试点击预览图获取1080大图...")
                            click_urls = await self.click_preview_and_get_1080_image()
                            if click_urls:
                                self.image_urls = click_urls
                                self.generation_completed = True
                                return TaskResult(
                                    code=ErrorCode.SUCCESS.value,
                                    data=self.image_urls,
                                    message="点击预览图获取1080:1080大图成功"
                                )
                            # 检查高分辨率超时
                            if image_wait_start and (time.time() - image_wait_start) > highres_timeout:
                                return TaskResult(
                                    code=ErrorCode.GENERATION_FAILED.value,
                                    data=None,
                                    message="1分钟未检测到1080:1080大图，结束任务"
                                )
                                
                    except Exception as e:
                        self.logger.debug(f"检测引号图标出错: {e}")
                    await asyncio.sleep(2)
                    
                    # 6分钟未检测到刷新页面
                    if (not quote_refreshed) and ((time.time() - quote_start) >= 360):
                        self.logger.info("超过6分钟未检测到引号图标，刷新页面重试...")
                        try:
                            await self.page.reload()
                            await asyncio.sleep(3)
                        except Exception:
                            pass
                        quote_refreshed = True
                        quote_start = time.time()

            # 阶段3：兜底检测
            self.logger.info("执行兜底检测...")
            
            # 兜底方法1: 直接搜索1080大图
            urls = await self.extract_fullsize_images_from_dom()
            if urls:
                self.image_urls = urls
                self.generation_completed = True
                return TaskResult(
                    code=ErrorCode.SUCCESS.value,
                    data=self.image_urls,
                    message="兜底提取1080:1080大图成功"
                )
            
            # 兜底方法2: 从网络请求中获取
            network_urls = await self.extract_1080_images_from_network()
            if network_urls:
                self.image_urls = network_urls
                self.generation_completed = True
                return TaskResult(
                    code=ErrorCode.SUCCESS.value,
                    data=self.image_urls,
                    message="从网络请求中获取1080:1080大图成功"
                )

            return TaskResult(
                code=ErrorCode.TASK_ID_NOT_OBTAINED.value, 
                data=None, 
                message="等待超时：未检测到1080:1080大图"
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
        """执行文本生成图片任务"""
        start_time = time.time()
        
        # 提取参数
        prompt = kwargs.get('prompt')
        username = kwargs.get('username')
        password = kwargs.get('password')
        model = kwargs.get('model', 'Image 3.1')
        aspect_ratio = kwargs.get('aspect_ratio', '1:1')
        quality = kwargs.get('quality', '1K')
        cookies = kwargs.get('cookies')
        image_path = kwargs.get('image_path')  # 可选的图片路径参数
        
        if not prompt or (isinstance(prompt, str) and not prompt.strip()):
            return TaskResult(
                code=ErrorCode.OTHER_ERROR.value,
                data=None,
                message="缺少必要字段: prompt",
                error_details={"error": "missing_prompt"}
            )

        self.logger.info("开始执行文本生成图片任务", 
                        prompt=prompt, model=model, 
                        aspect_ratio=aspect_ratio, quality=quality, image_path=image_path)
        
        try:
            # 初始化浏览器
            init_result = await self.init_browser(cookies)
            if init_result.code != ErrorCode.SUCCESS.value:
                return init_result
            
            # 如果有cookies，先设置cookies并检查登录状态
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
            
            # 跳转到生成页面
            nav_result = await self.navigate_to_generation_page()
            if nav_result.code != ErrorCode.SUCCESS.value:
                return nav_result
            
            # 设置响应监听器
            await self.setup_response_listener()
            
            # AI Agent模式下的处理
            if self.current_tool_type == "AI Agent":
                self.logger.info("当前选择AI Agent，跳过模型、比例、质量选择")
                
                # 如果有图片路径参数，上传图片（可选）
                if image_path:
                    upload_result = await self.upload_image(image_path)
                    if upload_result.code != ErrorCode.SUCCESS.value:
                        self.logger.warning(f"图片上传失败，但继续生成", error=upload_result.message)
                        self.send_via_enter = False
                    else:
                        self.logger.info("图片上传成功")
                        self.send_via_enter = True
                prompt_result = await self.input_prompt(prompt)
                if prompt_result.code != ErrorCode.SUCCESS.value:
                    return prompt_result
                try:
                    await asyncio.sleep(5)
                    await self.scroll_to_bottom_safe()
                    self.did_scroll_bottom = True
                except Exception as e:
                    self.logger.debug(f"输入提示词后滚动失败: {e}")
                try:
                    await self.ensure_results_view()
                except Exception as e:
                    self.logger.debug(f"返回结果视图失败: {e}")
            else:
                # 选择模型
                model_result = await self.select_model(model)
                if model_result.code != ErrorCode.SUCCESS.value:
                    return model_result
                
                # 选择比例
                if model != 'Nano Banana':
                    ratio_result = await self.select_aspect_ratio(aspect_ratio, model)
                    if ratio_result.code != ErrorCode.SUCCESS.value:
                        return ratio_result
                else:
                    self.logger.info("Nano Banana模型，不选择比例")
                
                # 选择质量（如果参数中有指定）
                if quality:
                    quality_result = await self.select_quality(quality)
                    if quality_result.code != ErrorCode.SUCCESS.value:
                        self.logger.warning(f"质量选择失败，将继续生成", quality=quality, error=quality_result.message)
                prompt_result = await self.input_prompt(prompt)
                if prompt_result.code != ErrorCode.SUCCESS.value:
                    return prompt_result

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
            self.logger.error("生成图片时出错", error=error_msg)
            
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
                message=f"生成图片时出错: {error_msg}",
                execution_time=time.time() - start_time,
                error_details={"error": error_msg}
            )
        
        finally:
            await self.close_browser()

    async def run(self, **kwargs) -> TaskResult:
        """运行任务的入口方法"""
        return await self.execute(**kwargs)

# 兼容性函数，保持向后兼容
async def text2image(prompt, username, password, model="Image 3.1", aspect_ratio="1:1", quality="1K", headless=False, cookies=None):
    """
    兼容性函数，用于保持向后兼容
    """
    executor = JimengText2ImageExecutor(headless=headless)
    result = await executor.run(
        prompt=prompt,
        username=username,
        password=password,
        model=model,
        aspect_ratio=aspect_ratio,
        quality=quality,
        cookies=cookies
    )
    
    # 转换为旧格式的返回值
    return {
        "code": result.code,
        "data": result.data,
        "message": result.message
    }

class ImgURLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "img":
            d = dict(attrs)
            src = d.get("src")
            srcset = d.get("srcset")
            if srcset:
                try:
                    candidates = [p.strip().split(" ")[0] for p in srcset.split(",") if p.strip()]
                    if candidates:
                        self.urls.append(candidates[-1])
                except Exception:
                    pass
            if src:
                self.urls.append(src)

def extract_img_urls_from_html(html: str) -> List[str]:
    parser = ImgURLParser()
    parser.feed(html or "")
    seen = set()
    result = []
    for u in parser.urls:
        if u and (u.startswith("http://") or u.startswith("https://")) and u not in seen:
            seen.add(u)
            result.append(u)
    return result

async def extract_fullsize_urls_from_dom(page) -> List[str]:
    try:
        urls = await page.evaluate(r'''() => {
            const results = new Set();
            const scope = Array.from(document.querySelectorAll('div[class*="image-player"]'));
            const bestFromImg = (img) => {
                const src = img.getAttribute('src') || '';
                const srcset = img.getAttribute('srcset') || '';
                let u = src;
                if (srcset) {
                    const candidates = srcset.split(',').map(s => s.trim().split(' ')[0]).filter(Boolean);
                    if (candidates.length) u = candidates[candidates.length - 1];
                }
                return (/^https?:/.test(u)) ? u : '';
            };
            const collect = (root) => {
                const imgs = Array.from(root.querySelectorAll('img'));
                for (const img of imgs) {
                    const u = bestFromImg(img);
                    if (u) results.add(u);
                }
            };
            if (scope.length) {
                for (const s of scope) collect(s);
            } else {
                collect(document.body);
            }
            return Array.from(results);
        }''')
        return urls or []
    except Exception:
        return []

# 使用示例
if __name__ == "__main__":
    async def test():
        username = "hsabqiq2bqnr@maildrop.cc"
        password = "123456"
        prompt = "一只可爱的猫咪在阳光下玩耍"
        model = "Image 3.1"
        aspect_ratio = "1:1"
        quality = "1K"
        cookies = "faceu-commerce-user-info=U19xKzQpj3FOtLUIN8ecOFLt_kRh1dlEZ8xhDCSIc_CAhci-xH0kl4-B9p1k4QJDyb3bQXwRFulN9G8hgvgUPJ1Jw5GRFZoI5R29tuEC05uy7-AwMrbQmVmdtEwY0JEVMia9HzhByRVg1lDjtdCv8hzFv_djVRenN6fdMiWQWhwwOhS0cyv5NDat6Un-fwDv6aSv7bEQoxcgkHqUp5drJRr99Z-E9I_McJotKhNEZ9TCVSy4f1rKmVW5E-lQH4fuYWNONUy2aH6MtDBeoW2vNZLhwh05iHlaothh8GAXagxIhu3mGKOknoO22lXfdLPpiCUiU-AgfPFYwUeeIq_I3zLVWwl77ivxTHSZuvIdAZsnOFFouzqbrua1E-2_ga_R13M7NJQ9S=GS2.1.s1757648995$o1$g1$t1757649015$j40$l0$h0; uifid_temp=455d7194fb3030a9c1fd263cebe74df90113e22092f6daad0427de1b7f41a2e9b77c56e4177b112b8983ebd64cf5fc9d413f46625ce887736fbfbdba7df2af5fac8a459f6488ef3e1b07c8e0c56d47ba; fpk1=c40c6a0e21650f53942fb9038168e96a23e6ecd1a46982c8087cedb2c27da6c7cd83836ac8695e11d7c8057151c2695d; s_v_web_id=verify_mfgaur92_1vPUMg70_EZxG_4FDY_9flF_nbVDH5PwyLCF; passport_csrf_token=87cfb78370b506cc86b2a1ec199feb61; passport_csrf_token_default=87cfb78370b506cc86b2a1ec199feb61; sid_guard=5fe20bddb672d697c2bd8bbdf9ec3e12%7C1757649043%7C5184000%7CTue%2C+11-Nov-2025+03%3A50%3A43+GMT; uid_tt=4fcec1e103b7d8673099ca0df4fb961fc1c2acb03a3b7f8bc7629abe29f4ab14; uid_tt_ss=4fcec1e103b7d8673099ca0df4fb961fc1c2acb03a3b7f8bc7629abe29f4ab14; sid_tt=5fe20bddb672d697c2bd8bbdf9ec3e12; sessionid=5fe20bddb672d697c2bd8bbdf9ec3e12; sessionid_ss=5fe20bddb672d697c2bd8bbdf9ec3e12; sid_ucp_v1=1.0.0-KDkwMDgyOTlkYzY0YmY0NDNmODM5MmQyMTRhMjA0ZWQ0NWQxNDI3MGMKGQiQiJDsisrE22gQk7GOxgYY6awfOAFA6wcQAxoDbXkyIiA1ZmUyMGJkZGI2NzJkNjk3YzJiZDhiYmRmOWVjM2UxMg; ssid_ucp_v1=1.0.0-KDkwMDgyOTlkYzY0YmY0NDNmODM5MmQyMTRhMjA0ZWQ0NWQxNDI3MGMKGQiQiJDsisrE22gQk7GOxgYY6awfOAFA6wcQAxoDbXkyIiA1ZmUyMGJkZGI2NzJkNjk3YzJiZDhiYmRmOWVjM2UxMg; store-idc=alisg; store-country-code=tw; store-country-code-src=uid; cc-target-idc=alisg; tt-target-idc-sign=j1gi6RRElkOy2S8lFGZZOi6sgRdq3rvZxBsfxbUFPanUX4SS_7c2_H778z1E6VHTus_q5KIBd3-yUkH_7fHMfe9OgaVR-0u9VSYiXZEuECLbi6ws0dOZD1x9F53Ms8tV2G_FL2G114WtfmGLAnBszsba8bkwKHlmEMyEtuRjSgkTWKaJXefX8aSByZ8it8EJlWustQ9gyhaG4vLANRG9ViAf-Cz40TzhebioRwI6g-SIlmv0U89SW4lwKxXuBFSamz25LyD-XXO-xOfHOzkHpIP9ob-WAudufIbw8Pg8RmsQwwJ0-PmbF8fiWo43Tr2AnNsd0-CA2HU4iURscnosyK3GQbj9arTd9_7LN8v0Zbt"
        
        executor = JimengText2ImageExecutor(headless=False)
        result = await executor.run(
            prompt=prompt,
            username=username,
            password=password,
            model=model,
            aspect_ratio=aspect_ratio,
            quality=quality,
            cookies=cookies
        )
        
        if result.code == 200:
            print(f"生成成功，图片链接列表: {result.data}")
        else:
            print(f"生成失败: {result.message}")
    
    # 运行测试
    asyncio.run(test())