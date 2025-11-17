"""
即梦平台自动化模块 - 图生图
based on BaseTaskExecutor refactoring version
"""

import asyncio
import time
from typing import Optional, List, Dict, Any
from backend.utils.base_task_executor import BaseTaskExecutor, TaskResult, ErrorCode, TaskLogger

class JimengImg2ImgExecutor(BaseTaskExecutor):
    """即梦图生图执行器"""
    
    def __init__(self, headless: bool = False):
        super().__init__(headless)
        self.task_id = None
        self.image_urls = []
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
                        copy_link_button = await self.page.query_selector('button.lv-btn.lv-btn-primary.lv-btn-size-default.lv-btn-shape-square.app-download-button-gIF_OD')
                        if copy_link_button:
                            await copy_link_button.click()
                            self.logger.info("已点击Copy link按钮")
                            await asyncio.sleep(2)
                except Exception as e:
                    # 静默处理异常，不输出警告
                    pass
            
            self.logger.info("弹窗检测和处理完成，继续执行")
            
            # 选择AI Image选项
            self.logger.info("尝试选择AI Image选项")
            try:
                # 检查是否存在新的tabs节点
                tabs_selector = 'div.tabs-dTWN8k'
                tabs_element = await self.page.query_selector(tabs_selector)
                
                if tabs_element:
                    self.logger.info("发现新的tabs界面，使用新方式选择AI Image")
                    # 使用新的tabs方式选择AI Image
                    await self.page.click('button.tab-YSwCEn:has-text("AI Image")')
                    await asyncio.sleep(2)
                else:
                    self.logger.info("未发现新tabs界面，使用传统下拉框方式")
                    # 点击类型选择下拉框
                    await self.page.click('div.lv-select[role="combobox"][class*="type-select-"]')
                    await asyncio.sleep(1)
                    
                    # 选择AI Image选项
                    await self.page.click('span[class*="select-option-label-content"]:has-text("AI Image")')
                    await asyncio.sleep(2)
                    
            except Exception as e:
                self.logger.warning("选择AI Image时出错，尝试备用方法", error=str(e))
                # 备用方法：直接尝试传统下拉框方式
                try:
                    await self.page.click('div.lv-select[role="combobox"][class*="type-select-"]')
                    await asyncio.sleep(1)
                    await self.page.click('span[class*="select-option-label-content"]:has-text("AI Image")')
                    await asyncio.sleep(2)
                except Exception as backup_e:
                    self.logger.error("无法选择AI Image选项", error=str(backup_e))
                    return TaskResult(
                        code=ErrorCode.WEB_INTERACTION_FAILED.value,
                        data=None,
                        message=f"无法选择AI Image选项: {str(backup_e)}",
                        error_details={"error": str(backup_e)}
                    )
            
            # 等待页面中的关键元素加载完成 - 提示词输入框
            textarea_selector = 'textarea.lv-textarea'
            await self.page.wait_for_selector(textarea_selector, timeout=30000)
            await asyncio.sleep(2)
            
            self.logger.info("已跳转到AI工具页面")
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
                    if model in text_content:
                        await element.click()
                        model_option_found = True
                        self.logger.info("已选择模型", model=model)
                        break
                
                if not model_option_found:
                    raise Exception("未找到模型选项")
                    
            except Exception as e:
                self.logger.warning("未找到指定模型，尝试通用选择方式", model=model, error=str(e))
                await self.page.click(f'span[class*="select-option-label-content"]:has-text("{model}")')
            
            await asyncio.sleep(1)
            return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="模型选择成功")
            
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

                    # 关闭选择
                    await self.page.click('button.lv-btn.lv-btn-secondary.lv-btn-size-default.lv-btn-shape-square:has([class*="button-text-"])')
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
                    target_option_in_group = await self.page.query_selector(f'div.resolution-radio-group-WD9rqn label.lv-radio:has(input[value="{target_quality_value}"])')
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
            
            # 如果上面的方法没成功，尝试更广泛的搜索
            if not quality_selected:
                # 直接查找并点击质量选项 (div.resolution-commercial-option-KnAlMo)
                if quality == "1K":
                    standard_option = await self.page.query_selector('div.resolution-commercial-option-KnAlMo:has-text("Standard (1K)")')
                    if standard_option:
                        await standard_option.click()
                        self.logger.info("已选择 Standard (1K) 质量选项")
                        await asyncio.sleep(1)
                        quality_selected = True
                
                elif quality == "2K":
                    high_option = await self.page.query_selector('div.resolution-commercial-option-KnAlMo:has-text("High (2K)")')
                    if high_option:
                        await high_option.click()
                        self.logger.info("已选择 High (2K) 质量选项")
                        await asyncio.sleep(1)
                        quality_selected = True
                
                elif quality == "4K":
                    ultra_option = await self.page.query_selector('div.resolution-commercial-option-KnAlMo:has-text("Ultra (4K)")')
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
                                if "image" in asset and asset["image"].get("finish_time", 0) != 0:
                                    try:
                                        self.image_urls = []
                                        for i in range(4):
                                            try:
                                                url = asset["image"]["item_list"][i]["image"]["large_images"][0]["image_url"]
                                                self.image_urls.append(url)
                                            except (KeyError, IndexError):
                                                self.logger.debug(f"无法获取第{i+1}张图片URL")
                                        
                                        if self.image_urls:
                                            self.logger.info("图片生成完成", count=len(self.image_urls))
                                            for i, url in enumerate(self.image_urls):
                                                self.logger.info(f"图片{i+1} URL", url=url)
                                            self.generation_completed = True
                                        else:
                                            self.logger.warning("图片已完成但无法获取任何URL")
                                            self.generation_completed = True  # 标记为完成，即使没有URL
                                    except (KeyError, IndexError):
                                        self.logger.warning("图片已完成但无法获取URL")
                                        self.generation_completed = True  # 标记为完成，即使没有URL
                                else:
                                    self.logger.debug("图片生成尚未完成，继续等待")
                except:
                    pass
        
        # 注册响应监听器
        self.page.on("response", handle_response)
    
    async def start_generation(self) -> TaskResult:
        """点击生成按钮开始生成"""
        try:
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
                
            # 等待图片生成完成
            self.logger.info("已获取任务ID，等待图片生成完成", task_id=self.task_id)
            start_time = time.time()
            
            while not self.generation_completed and time.time() - start_time < max_wait_time:
                elapsed = time.time() - start_time
                self.logger.debug(f"等待图片生成中，已等待 {elapsed:.1f} 秒")
                await self.page.reload()
                self.logger.debug("刷新页面，检查图片生成状态")
                await asyncio.sleep(5)
            
            if self.generation_completed and self.image_urls:
                self.logger.info("图片生成成功", total_time=f"{time.time() - start_time:.1f}秒", count=len(self.image_urls))
                for i, url in enumerate(self.image_urls):
                    self.logger.info(f"图片{i+1} URL", url=url)
                return TaskResult(
                    code=ErrorCode.SUCCESS.value,
                    data=self.image_urls,
                    message="图片生成成功"
                )
            elif self.generation_completed and not self.image_urls:
                self.logger.error("任务已完成但未获取到图片URL", task_id=self.task_id, wait_time=f"{time.time() - start_time:.1f}秒")
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
    
    async def upload_input_images(self, input_images: List[str]) -> TaskResult:
        """上传输入图片"""
        try:
            self.logger.info("开始上传输入图片", input_images=input_images, count=len(input_images))
            
            # 根据图片数量选择不同的上传方式
            for i, input_image in enumerate(input_images):
                self.logger.info(f"上传第{i+1}张图片", image=input_image)
                
                # 查找文件上传输入框 - 使用通用的选择器
                upload_selector = 'input[type="file"][accept*="image"]'
                
                # 等待上传控件出现
                await self.page.wait_for_selector(upload_selector, timeout=10000, state='attached')
                
                # 上传图片文件
                await self.page.set_input_files(upload_selector, input_image)
                self.logger.info(f"第{i+1}张图片上传成功")
                
                # 等待上传完成
                await asyncio.sleep(2)
                
            self.logger.info("所有输入图片上传完成", total_count=len(input_images))
            return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="输入图片上传成功")
            
        except Exception as e:
            self.logger.error("上传输入图片失败", error=str(e))
            return TaskResult(code=ErrorCode.OTHER_ERROR.value, data=None, message="上传输入图片失败", error_details={"error": str(e)})

    async def handle_reference_image_interface(self, model: str = None) -> TaskResult:
        """处理参考图像界面，点击Done按钮"""
        try:
            # 对于Nano Banana和Image 4.0模型，跳过参考图像界面处理
            if model in ['Nano Banana', 'Image 4.0']:
                self.logger.info(f"模型 {model} 无需处理参考图像界面，跳过")
                return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="模型无需处理参考图像界面")
            
            self.logger.info("检查是否需要处理参考图像界面")
            
            # 等待最多6秒检查"Done"按钮
            done_button = await self.page.wait_for_selector('div.save-YNJf9P:has-text("Done")', timeout=6000)
            if done_button:
                self.logger.info("检测到参考图像界面，点击Done按钮")
                await done_button.click()
                await asyncio.sleep(2)  # 等待界面切换
                return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="参考图像界面处理完成")
            else:
                self.logger.info("未检测到参考图像界面，继续执行")
                return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="无需处理参考图像界面")

        except Exception as e:
            # 对于特定模型，超时是正常的（因为它们没有参考图像界面）
            if model in ['Nano Banana', 'Image 4.0']:
                self.logger.info(f"模型 {model} 无参考图像界面，继续执行")
                return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="模型无需处理参考图像界面")
            else:
                self.logger.error("处理参考图像界面时出错", error=str(e))
                return TaskResult(
                    code=ErrorCode.WEB_INTERACTION_FAILED.value,
                    data=None,
                    message="处理参考图像界面失败",
                    error_details={"error": str(e)}
                )

    async def execute(self, **kwargs) -> TaskResult:
        """执行图生图任务"""
        start_time = time.time()
        
        # 提取参数
        prompt = kwargs.get('prompt')
        username = kwargs.get('username')
        password = kwargs.get('password')
        model = kwargs.get('model', 'Nano Banana')
        aspect_ratio = kwargs.get('aspect_ratio', None)
        quality = kwargs.get('quality', '1K')  # 默认为1K
        cookies = kwargs.get('cookies')
        input_images = kwargs.get('input_images', [])
        
        self.logger.info("开始执行图生图任务", 
                        prompt=prompt, model=model, 
                        aspect_ratio=aspect_ratio, quality=quality,
                        input_images_count=len(input_images))
        
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
            
            # 输入提示词
            prompt_result = await self.input_prompt(prompt)
            if prompt_result.code != ErrorCode.SUCCESS.value:
                return prompt_result
            
            # 选择模型
            model_result = await self.select_model(model)
            if model_result.code != ErrorCode.SUCCESS.value:
                return model_result
            
            # 选择比例（如果提供了比例参数）
            if aspect_ratio:
                ratio_result = await self.select_aspect_ratio(aspect_ratio, model)
                if ratio_result.code != ErrorCode.SUCCESS.value:
                    return ratio_result
            
            # 选择质量（如果参数中有指定）
            if quality:
                quality_result = await self.select_quality(quality)
                if quality_result.code != ErrorCode.SUCCESS.value:
                    self.logger.warning(f"质量选择失败，将继续生成", quality=quality, error=quality_result.message)

            # 上传输入图片
            upload_result = await self.upload_input_images(input_images)
            if upload_result.code != ErrorCode.SUCCESS.value:
                return upload_result

            # 等待参考图像界面并点击"Done"按钮（如果出现）
            await self.handle_reference_image_interface(model)

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

    async def run(self, input_images: List[str] = None, **kwargs) -> TaskResult:
        """运行任务的入口方法"""
        if input_images is None:
            input_images = []
        
        # 根据模型确定最大图片数量
        model = kwargs.get('model', 'Nano Banana')
        if model == 'Image 4.0':
            max_images = 6  # Image 4.0模型支持最多6张图片
        elif model == 'Nano Banana':
            max_images = 3  # Nano Banana模型支持最多3张图片
        else:
            max_images = 1  # 其他模型支持1张图片
        
        # 限制输入图片数量不超过模型支持的最大值
        input_images = input_images[:max_images]
        kwargs['input_images'] = input_images
        return await self.execute(**kwargs)

# 兼容性函数，保持向后兼容
async def img2img(prompt, username, password, input_images=None, model="Nano Banana", aspect_ratio=None, headless=False, cookies=None):
    """
    兼容性函数，用于保持向后兼容
    """
    executor = JimengImg2ImgExecutor(headless=headless)
    result = await executor.run(
        prompt=prompt,
        username=username,
        password=password,
        model=model,
        aspect_ratio=aspect_ratio,
        input_images=input_images,
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
        username = "hsabqiq2bqnr@maildrop.cc"
        password = "123456"
        prompt = "一只可爱的猫咪在阳光下玩耍"
        model = "Nano Banana"
        aspect_ratio = None
        input_images = ["/Users/chaiyapeng/Downloads/jimeng_images_20250916_224801/task_442_image_1.jpg", 
        "/Users/chaiyapeng/Downloads/jimeng_images_20250916_224801/task_442_image_2.jpg",
        "/Users/chaiyapeng/Downloads/jimeng_images_20250916_224801/task_442_image_3.jpg"]

        
        executor = JimengImg2ImgExecutor(headless=False)
        result = await executor.run(
            input_images=input_images,
            prompt=prompt,
            username=username,
            password=password,
            model=model,
            aspect_ratio=aspect_ratio,
            cookies=None
        )
        
        if result.code == 200:
            print(f"生成成功，图片链接列表: {result.data}")
        else:
            print(f"生成失败: {result.message}")
    
    # 运行测试
    asyncio.run(test())