"""
即梦平台自动化模块 - 图片生成视频
based on BaseTaskExecutor refactoring version
"""

import asyncio
import time
from typing import Optional, List, Dict, Any
from backend.utils.base_task_executor import BaseTaskExecutor, TaskResult, ErrorCode, TaskLogger

class JimengImage2VideoExecutor(BaseTaskExecutor):
    """即梦图片生成视频执行器"""
    
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

    async def navigate_to_image2video_page(self) -> TaskResult:
        """跳转到图片生成视频页面"""
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
            
            # 选择AI Video选项
            self.logger.info("尝试选择AI Video选项")
            try:
                # 检查是否存在新的tabs节点
                tabs_selector = 'div.tabs-dTWN8k'
                tabs_element = await self.page.query_selector(tabs_selector)
                
                if tabs_element:
                    self.logger.info("发现新的tabs界面，使用新方式选择AI Video")
                    # 使用新的tabs方式选择AI Video
                    await self.page.click('button.tab-YSwCEn:has-text("AI Video")')
                    await asyncio.sleep(2)
                else:
                    self.logger.info("未发现新tabs界面，使用传统下拉框方式")
                    # 点击类型选择下拉框
                    await self.page.click('div.lv-select[role="combobox"][class*="type-select-"]')
                    await asyncio.sleep(1)
                    
                    # 选择AI Video选项
                    await self.page.click('span[class*="select-option-label-content"]:has-text("AI Video")')
                    await asyncio.sleep(2)
                    
            except Exception as e:
                self.logger.warning("选择AI Video时出错，尝试备用方法", error=str(e))
                # 备用方法：直接尝试传统下拉框方式
                try:
                    await self.page.click('div.lv-select[role="combobox"][class*="type-select-"]')
                    await asyncio.sleep(1)
                    await self.page.click('span[class*="select-option-label-content"]:has-text("AI Video")')
                    await asyncio.sleep(2)
                except Exception as backup_e:
                    self.logger.error("无法选择AI Video选项", error=str(backup_e))
                    return TaskResult(
                        code=ErrorCode.WEB_INTERACTION_FAILED.value,
                        data=None,
                        message=f"无法选择AI Video选项: {str(backup_e)}",
                        error_details={"error": str(backup_e)}
                    )
            
            self.logger.info("已跳转到图片生成视频页面并选择AI Video")
            return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="页面跳转成功")
        except Exception as e:
            self.logger.error("页面跳转失败", error=str(e))
            return TaskResult(
                code=ErrorCode.WEB_INTERACTION_FAILED.value,
                data=None,
                message="页面跳转失败",
                error_details={"error": str(e)}
            )

    async def select_video_model(self, model: str = "Video 3.0") -> TaskResult:
        """选择视频模型"""
        try:
            self.logger.info("选择视频模型", model=model)
            
            # 点击视频模型选择下拉框（第一个非类型选择的下拉框）
            video_model_selectors = await self.page.query_selector_all('div.lv-select[role="combobox"]:not([class*="type-select-"])')
            if len(video_model_selectors) >= 1:
                await video_model_selectors[0].click()
                await asyncio.sleep(1)
                
                # 等待下拉菜单出现
                await self.page.wait_for_selector('div.lv-select-popup-inner[role="listbox"]', timeout=5000)
                await asyncio.sleep(1)
                
                # 获取所有可选的模型选项
                options = await self.page.query_selector_all('li[role="option"]')
                if not options:
                    self.logger.error("未找到视频模型选项")
                    return TaskResult(
                        code=ErrorCode.WEB_INTERACTION_FAILED.value,
                        data=None,
                        message="未找到视频模型选项",
                        error_details={"error": "未找到视频模型选项"}
                    )
                
                # 处理不同的模型选择需求
                selected = False
                model_found = False
                
                # 处理不同的模型选择需求
                for i, option in enumerate(options):
                    option_text = await option.text_content()
                    option_text = option_text.strip()
                    
                    # 优先精确匹配
                    if model == option_text or (model == "Video 3.0" and option_text.startswith("Video 3.0\n") and "Creates multiple scenes with one detailed prompt." in option_text):
                        await option.click()
                        self.logger.info(f"已选择视频模型: {option_text}")
                        selected = True
                        model_found = True
                        break
                    # 次要模糊匹配 - 检查是否包含指定模型名
                    elif model == "Video 3.0" and "Video 3.0" in option_text and "Pro" not in option_text and "Fast" not in option_text and "Creates multiple scenes with one detailed prompt." in option_text:
                        # 匹配 "Video 3.0" 包含特定描述的选项
                        await option.click()
                        self.logger.info(f"已选择视频模型: {option_text}")
                        selected = True
                        model_found = True
                        break
                    elif model == "Video 3.0 Pro" and "Video 3.0 Pro" in option_text and "Best-in-class" in option_text:
                        # 选择 "Video 3.0 Pro" 版本 (带有 "Best-in-class performance" 描述的版本)
                        await option.click()
                        self.logger.info(f"已选择视频模型: {option_text}")
                        selected = True
                        model_found = True
                        break
                    elif model == "Video S2.0 Pro" and "Video S2.0 Pro" in option_text:
                        # 选择 "Video S2.0 Pro" 版本
                        await option.click()
                        self.logger.info(f"已选择视频模型: {option_text}")
                        selected = True
                        model_found = True
                        break
                
                # 如果没有找到指定模型，尝试使用最接近的模型
                if not model_found:
                    if model == "Video 3.0":
                        # 对于"Video 3.0"，寻找基础版本（不带Pro或Fast，但包含特定描述）
                        for option in options:
                            option_text = await option.text_content()
                            option_text = option_text.strip()
                            if "Video 3.0" in option_text and "Pro" not in option_text and "Fast" not in option_text and "Creates multiple scenes with one detailed prompt." in option_text:
                                await option.click()
                                self.logger.info(f"已选择基础视频模型: {option_text}")
                                selected = True
                                model_found = True
                                break
                    
                    if not model_found:
                        self.logger.warning(f"未找到指定的模型 '{model}'，使用默认模型")
                        # 选择第一个选项作为默认模型
                        first_option = options[0]
                        first_option_text = await first_option.text_content()
                        first_option_text = first_option_text.strip()
                        await first_option.click()
                        self.logger.info(f"已选择默认视频模型: {first_option_text}")
                        selected = True
                
                if selected:
                    await asyncio.sleep(2)
                    return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="视频模型选择成功")
                else:
                    self.logger.error("无法选择视频模型")
                    return TaskResult(
                        code=ErrorCode.WEB_INTERACTION_FAILED.value,
                        data=None,
                        message="无法选择视频模型",
                        error_details={"error": "点击模型选项失败"}
                    )
            else:
                self.logger.error("未找到视频模型选择下拉框")
                return TaskResult(
                    code=ErrorCode.WEB_INTERACTION_FAILED.value,
                    data=None,
                    message="未找到视频模型选择下拉框",
                    error_details={"error": "未找到视频模型选择下拉框"}
                )
                
        except Exception as e:
            self.logger.error("选择视频模型时出错", error=str(e))
            return TaskResult(
                code=ErrorCode.WEB_INTERACTION_FAILED.value,
                data=None,
                message="选择视频模型失败",
                error_details={"error": str(e)}
            )

    async def select_video_duration(self, second: int = 5) -> TaskResult:
        """选择视频时长"""
        try:
            self.logger.info("选择视频时长", second=second)
            
            # 点击时长选择下拉框（根据页面结构，时长选择器通常包含秒数如 "5s"、"10s"）
            duration_selectors = await self.page.query_selector_all('div.lv-select[role="combobox"]:not([class*="type-select-"])')
            
            # 查找包含 "s" 但不包含 "frame" 的下拉框，这通常是时长选择器
            duration_selector_found = False
            target_selector = None
            target_index = -1
            for i, selector in enumerate(duration_selectors):
                try:
                    # 获取当前下拉框的值文本
                    value_text = await selector.text_content()
                    if 's' in value_text and 'frame' not in value_text.lower():  # 包含 "s" 但不是 "frames"，通常是时长选择器
                        target_selector = selector
                        target_index = i
                        duration_selector_found = True
                        break
                except:
                    continue
            
            # 如果没找到合适的，尝试根据HTML结构定位最可能的时长选择器
            if not duration_selector_found:
                for i, selector in enumerate(duration_selectors):
                    try:
                        # 获取按钮内文本
                        button_text = await selector.text_content()
                        # 检查是否更像时长选择器（包含 "s" 并且看起来像时间）
                        if any(time_str in button_text for time_str in ["5s", "10s", "3s", "7s"]):
                            target_selector = selector
                            target_index = i
                            duration_selector_found = True
                            break
                    except:
                        continue
            
            # 如果根据内容仍未找到，使用索引方式（最后一个下拉框通常是时长）
            if not duration_selector_found:
                if len(duration_selectors) > 0:
                    # 通常时长选择器是最后一个包含 "s" 的选择器
                    # 从后向前搜索
                    for i in range(len(duration_selectors)-1, -1, -1):
                        try:
                            button_text = await duration_selectors[i].text_content()
                            if 's' in button_text:
                                target_selector = duration_selectors[i]
                                target_index = i
                                duration_selector_found = True
                                break
                        except:
                            continue

            # 如果找到了目标选择器，先滚动到它确保可见，再点击
            if duration_selector_found and target_selector:
                try:
                    # 滚动到元素可见位置
                    await target_selector.scroll_into_view_if_needed(timeout=3000)
                    await asyncio.sleep(0.5)  # 等待滚动完成
                    # 确保元素可见和可点击
                    await target_selector.wait_for_element_state("visible", timeout=3000)
                    await target_selector.wait_for_element_state("enabled", timeout=3000)
                    # 点击元素
                    await target_selector.click()
                    self.logger.info(f"点击第{target_index+1}个下拉框作为时长选择器: {await target_selector.text_content()}")
                except Exception as e:
                    self.logger.warning(f"直接点击失败: {str(e)}, 尝试JavaScript点击")
                    # 如果直接点击失败，尝试使用JavaScript点击
                    await self.page.evaluate("(element) => { element.scrollIntoView({behavior: 'smooth', block: 'center'}); setTimeout(() => { element.click(); }, 100); }", target_selector)
                    await asyncio.sleep(1)
                    self.logger.info(f"通过JavaScript点击第{target_index+1}个下拉框作为时长选择器")
            
            if duration_selector_found:
                await asyncio.sleep(2)  # 增加等待时间，确保页面元素完全渲染
                
                # 等待一段时间确保下拉框状态稳定
                await asyncio.sleep(1)
                
                # 先检查下拉框是否已展开（aria-expanded="true"）
                try:
                    # 等待时长选择弹窗出现
                    await self.page.wait_for_selector('div.lv-select-popup-inner[role="listbox"]', timeout=5000)
                except:
                    # 弹窗可能因为页面变化没有立即出现，再点击一次下拉框
                    for i, selector in enumerate(duration_selectors):
                        try:
                            value_text = await selector.text_content()
                            if 's' in value_text and 'frame' not in value_text.lower():
                                await selector.click()
                                self.logger.info(f"重新点击第{i+1}个下拉框以打开选项")
                                await asyncio.sleep(1)  # 点击后等待弹窗出现
                                break
                        except:
                            continue
                    await self.page.wait_for_selector('div.lv-select-popup-inner[role="listbox"]', timeout=5000)
                
                await asyncio.sleep(1)
                
                # 根据second参数选择对应的时长
                try:
                    if second == 5:
                        # 选择5s选项
                        await self.page.click('li[role="option"] span:has-text("5s")')
                        self.logger.info("已选择时长: 5s")
                    elif second == 10:
                        # 选择10s选项
                        await self.page.click('li[role="option"] span:has-text("10s")')
                        self.logger.info("已选择时长: 10s")
                    else:
                        # 默认选择5s
                        await self.page.click('li[role="option"] span:has-text("5s")')
                        self.logger.info("使用默认时长: 5s")
                except Exception as inner_e:
                    # 如果精确匹配失败，尝试模糊匹配
                    self.logger.warning("精确时长匹配失败，尝试模糊匹配", error=str(inner_e))
                    if second == 10:
                        await self.page.click('li[role="option"]:has-text("10s")')
                        self.logger.info("通过模糊匹配选择时长: 10s")
                    else:
                        await self.page.click('li[role="option"]:has-text("5s")')
                        self.logger.info("通过模糊匹配选择时长: 5s")
                
                await asyncio.sleep(2)
                return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="视频时长选择成功")
                
            else:
                self.logger.error("未找到时长选择下拉框")
                return TaskResult(
                    code=ErrorCode.WEB_INTERACTION_FAILED.value,
                    data=None,
                    message="未找到时长选择下拉框",
                    error_details={"error": "未找到时长选择下拉框"}
                )
                
        except Exception as e:
            self.logger.error("选择视频时长失败", error=str(e))
            return TaskResult(
                code=ErrorCode.WEB_INTERACTION_FAILED.value,
                data=None,
                message="选择视频时长失败",
                error_details={"error": str(e)}
            )

    async def upload_image(self, image_path: str) -> TaskResult:
        """上传图片"""
        try:
            self.logger.info("上传图片", image_path=image_path)

            # 查找文件上传输入框
            upload_selector = 'input[type="file"][accept*="image"]'
            await self.page.wait_for_selector(upload_selector, timeout=10000, state='attached')

            # 上传图片文件
            await self.page.set_input_files(upload_selector, image_path)
            self.logger.info("图片上传成功")
            await asyncio.sleep(3)
            return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="图片上传成功")
        except Exception as e:
            self.logger.error("图片上传失败", error=str(e))
            return TaskResult(
                code=ErrorCode.WEB_INTERACTION_FAILED.value,
                data=None,
                message="图片上传失败",
                error_details={"error": str(e)}
            )

    async def upload_last_frame_image(self, image_path: str) -> TaskResult:
        """上传尾帧图片（Last frame）"""
        try:
            self.logger.info("上传尾帧图片", image_path=image_path)

            # 查找文件上传输入框（完全使用和第一张图片相同的选择器）
            upload_selector = 'input[type="file"][accept*="image"]'
            await self.page.wait_for_selector(upload_selector, timeout=10000, state='attached')

            # 上传尾帧图片文件（完全使用和第一张图片相同的逻辑）
            await self.page.set_input_files(upload_selector, image_path)
            self.logger.info("尾帧图片上传成功")

            # 等待文件上传完成（和第一张图片相同的等待时间）
            await asyncio.sleep(3)
            return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="尾帧图片上传成功")
        except Exception as e:
            self.logger.error("尾帧图片上传失败", error=str(e))
            return TaskResult(
                code=ErrorCode.WEB_INTERACTION_FAILED.value,
                data=None,
                message="尾帧图片上传失败",
                error_details={"error": str(e)}
            )

    async def select_video_resolution(self, resolution: str = "1080p") -> TaskResult:
        """选择视频分辨率（使用正确的HTML结构来定位单选按钮）"""
        try:
            self.logger.info("选择视频分辨率", resolution=resolution)
            
            # 根据提供的HTML代码，分辨率和比例选择是通过同一个按钮控制的
            # 按钮内部显示格式为 "比例/分辨率"，如 "16:9" 和 "720P"
            resolution_button_selector = 'button.lv-btn.lv-btn-secondary.lv-btn-size-default.lv-btn-shape-square.button-oBBmQ2'
            
            # 等待按钮出现
            await self.page.wait_for_selector(resolution_button_selector, timeout=5000)
            
            # 点击分辨率/比例选择按钮
            await self.page.click(resolution_button_selector)
            self.logger.info("已点击分辨率/比例选择按钮")
            await asyncio.sleep(2)
            
            # 查找分辨率单选组
            try:
                # 等待分辨率单选组出现
                await self.page.wait_for_selector('div.lv-radio-group.resolution-radio-group-dpSFzU', timeout=5000)
                
                # 根据分辨率参数选择对应的单选按钮
                if resolution.lower() == '720p':
                    # 选择720p单选按钮，其input的value为"720p"
                    resolution_radio_selector = 'input[type="radio"][value="720p"]'
                    # 使用JavaScript强制点击，因为元素可能被隐藏
                    await self.page.evaluate(f'''
                        () => {{
                            const element = document.querySelector('{resolution_radio_selector}');
                            if (element) {{
                                element.click();
                                return true;
                            }}
                            return false;
                        }}
                    ''')
                    self.logger.info("已选择分辨率: 720P")
                elif resolution.lower() == '1080p':
                    # 选择1080p单选按钮，其input的value为"1080p"
                    resolution_radio_selector = 'input[type="radio"][value="1080p"]'
                    # 使用JavaScript强制点击，因为元素可能被隐藏
                    await self.page.evaluate(f'''
                        () => {{
                            const element = document.querySelector('{resolution_radio_selector}');
                            if (element) {{
                                element.click();
                                return true;
                            }}
                            return false;
                        }}
                    ''')
                    self.logger.info("已选择分辨率: 1080P")
                else:
                    # 默认选择1080p
                    resolution_radio_selector = 'input[type="radio"][value="1080p"]'
                    # 使用JavaScript强制点击，因为元素可能被隐藏
                    await self.page.evaluate(f'''
                        () => {{
                            const element = document.querySelector('{resolution_radio_selector}');
                            if (element) {{
                                element.click();
                                return true;
                            }}
                            return false;
                        }}
                    ''')
                    self.logger.info("使用默认分辨率: 1080P")
                
                await asyncio.sleep(2)
                return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="视频分辨率选择成功")
                
            except Exception as e:
                # 如果精确选择器失败，尝试使用更通用的选择器
                self.logger.warning("精确分辨率选择器未找到，尝试备用选择器", error=str(e))
                
                # 尝试选择分辨率组中的选项
                try:
                    # 查找分辨率选项容器
                    resolution_option = None
                    if resolution.lower() == '720p':
                        resolution_option = await self.page.query_selector('label:has-text("720P")')
                        if not resolution_option:
                            resolution_option = await self.page.query_selector('label input[value="720p"]')
                    elif resolution.lower() == '1080p':
                        resolution_option = await self.page.query_selector('label:has-text("1080P")')
                        if not resolution_option:
                            resolution_option = await self.page.query_selector('label input[value="1080p"]')
                    else:
                        resolution_option = await self.page.query_selector('label:has-text("1080P")')
                        if not resolution_option:
                            resolution_option = await self.page.query_selector('label input[value="1080p"]')
                    
                    if resolution_option:
                        # 如果找到的是input元素，尝试JavaScript点击
                        if await resolution_option.get_attribute('type') == 'radio':
                            await self.page.evaluate('''
                                (element) => {
                                    element.click();
                                    return true;
                                }
                            ''', resolution_option)
                        else:
                            # 如果是label，点击内部的input
                            input_element = await resolution_option.query_selector('input[type="radio"]')
                            if input_element:
                                await self.page.evaluate('''
                                    (element) => {
                                        element.click();
                                        return true;
                                    }
                                ''', input_element)
                        
                        selected_resolution = resolution if resolution.lower() in ['720p', '1080p'] else '1080P'
                        self.logger.info(f"使用备用选择器选择了分辨率: {selected_resolution}")
                    else:
                        self.logger.warning(f"未找到分辨率选项: {resolution}，保持默认选项")
                        
                except Exception as backup_error:
                    self.logger.warning("备用选择器也失败", error=str(backup_error))
                
                await asyncio.sleep(2)
                return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="视频分辨率选择成功")
                
        except Exception as e:
            self.logger.error("选择视频分辨率失败", error=str(e))
            # 不是致命错误，继续执行
            return TaskResult(code=ErrorCode.SUCCESS.value, data=None, message="视频分辨率选择完成（忽略错误）")

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
                                # 检查视频生成是否完成
                                if "video" in asset and asset["video"].get("finish_time", 0) != 0:
                                    try:
                                        # 获取视频URL
                                        if "item_list" in asset["video"] and len(asset["video"]["item_list"]) > 0:
                                            video_item = asset["video"]["item_list"][0]
                                            if "video" in video_item and "transcoded_video" in video_item["video"]:
                                                transcoded = video_item["video"]["transcoded_video"]
                                                if "origin" in transcoded and "video_url" in transcoded["origin"]:
                                                    self.video_url = transcoded["origin"]["video_url"]
                                        
                                        if self.video_url:
                                            self.logger.info("视频生成完成", video_url=self.video_url)
                                            self.generation_completed = True
                                        else:
                                            self.logger.warning("视频已完成但无法获取URL")
                                            self.generation_completed = True  # 标记为完成，即使没有URL
                                    except (KeyError, IndexError):
                                        self.logger.warning("视频已完成但无法获取URL")
                                        self.generation_completed = True  # 标记为完成，即使没有URL
                                else:
                                    self.logger.debug("视频生成尚未完成，继续等待")
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
                            self.logger.info("已点击生成按钮，开始生成视频")
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
                
            # 等待视频生成完成
            self.logger.info("已获取任务ID，等待视频生成完成", task_id=self.task_id)
            start_time = time.time()
            
            while not self.generation_completed and time.time() - start_time < max_wait_time:
                elapsed = time.time() - start_time
                self.logger.debug(f"等待视频生成中，已等待 {elapsed:.1f} 秒")
                await self.page.reload()
                self.logger.debug("刷新页面，检查视频生成状态")
                await asyncio.sleep(5)
            
            if self.generation_completed and self.video_url:
                self.logger.info("视频生成成功", total_time=f"{time.time() - start_time:.1f}秒", video_url=self.video_url)
                return TaskResult(
                    code=ErrorCode.SUCCESS.value,
                    data=self.video_url,
                    message="视频生成成功"
                )
            elif self.generation_completed and not self.video_url:
                self.logger.error("任务已完成但未获取到视频URL", task_id=self.task_id, wait_time=f"{time.time() - start_time:.1f}秒")
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
        """执行图片生成视频任务"""
        start_time = time.time()

        # 提取参数
        image_path = kwargs.get('image_path')
        last_frame_image_path = kwargs.get('last_frame_image_path')  # 新增：尾帧图片路径
        prompt = kwargs.get('prompt', '')
        model = kwargs.get('model', 'Video 3.0')
        second = kwargs.get('second', 5)
        resolution = kwargs.get('resolution', '1080p')  # 添加分辨率参数
        username = kwargs.get('username')
        password = kwargs.get('password')
        cookies = kwargs.get('cookies')

        self.logger.info("开始执行图片生成视频任务",
                        image_path=image_path, last_frame_image_path=last_frame_image_path,
                        prompt=prompt, model=model, second=second, resolution=resolution)
        
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
            else:
                # 如果有cookies，直接设置
                await self.handle_cookies(cookies)
            
            # 跳转到图片生成视频页面
            nav_result = await self.navigate_to_image2video_page()
            if nav_result.code != ErrorCode.SUCCESS.value:
                return nav_result
            
            # 设置响应监听器
            await self.setup_response_listener()
            
            # 选择视频模型
            model_result = await self.select_video_model(model)
            if model_result.code != ErrorCode.SUCCESS.value:
                return model_result
            
            # 选择视频时长
            duration_result = await self.select_video_duration(second)
            if duration_result.code != ErrorCode.SUCCESS.value:
                return duration_result
            
            # 上传图片
            upload_result = await self.upload_image(image_path)
            if upload_result.code != ErrorCode.SUCCESS.value:
                return upload_result

            # 如果有尾帧图片，上传尾帧图片
            if last_frame_image_path:
                last_frame_upload_result = await self.upload_last_frame_image(last_frame_image_path)
                if last_frame_upload_result.code != ErrorCode.SUCCESS.value:
                    return last_frame_upload_result

            # 选择视频分辨率（在上传图片之后）
            resolution_result = await self.select_video_resolution(resolution)
            if resolution_result.code != ErrorCode.SUCCESS.value:
                return resolution_result
            
            # 输入提示词（如果有）
            if prompt:
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
            self.logger.error("生成视频时出错", error=error_msg)
            
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
                message=f"生成视频时出错: {error_msg}",
                execution_time=time.time() - start_time,
                error_details={"error": error_msg}
            )
        
        finally:
            await self.close_browser()

    async def run(self, **kwargs) -> TaskResult:
        """运行任务的入口方法"""
        return await self.execute(**kwargs)