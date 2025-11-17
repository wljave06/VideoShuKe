## 目标
- 始终获取全屏详情图 `img[data-apm-action*="detail-card"]` 的 `src`（如 `...aigc_resize:1080:1080.webp...`），避免半屏/预览图。
- 解决图片容器与图片元素通过用户交互才懒加载的问题：在代码里可靠地触发加载并等待完成。

## 技术策略
1. 选择器稳健化
   - 全局把等值匹配改为包含匹配：
     - `img[data-apm-action="ai-generated-image-record-card"]` → `img[data-apm-action*="record-card"]`
     - `img[data-apm-action="ai-generated-image-detail-card"]` → `img[data-apm-action*="detail-card"]`
   - 容器沿用：`div[class*="image-player"]`、`div[class^="nodes-container-"]`、`div[class*="responsive-common-grid-"]`、`div[class*="card-icon-button"]`。

2. 懒加载处理（多层加载）
   - 先点击缩略图触发详情层：
     - 在当前对话或节点容器内点击第一个 `img[data-apm-action*="record-card"]`。
   - 等待玩家容器出现：
     - `page.locator('div[class*="image-player"]').first.wait_for(state='visible', timeout=8000)`。
   - 等待详情图真正加载（非空 `src` 且 `naturalWidth>0`）：
     - `page.wait_for_function(() => { const img = document.querySelector('div[class*="image-player"] img[data-apm-action*="detail-card"]'); return img && img.complete && img.naturalWidth>0 && /^https?:/.test(img.src); }, { timeout: 10000 })`。
   - 若仍未加载，主动触发可视化与滚动：
     - `element.scrollIntoView({block:'center'})`；对容器执行 `scrollTop` 来触发 IntersectionObserver。

3. 统一 URL 提取规则
   - 优先 `srcset` 最后一项，其次 `src`，仅保留 `http/https`；解析 `aigc_resize:w:h` 作为分辨率兜底。

4. 网络层兜底
   - 监听 `page.on('response')/wait_for_response`，抓取 `host ~ p16-dreamina-sign` 且路径含 `aigc_resize:` 与 `format=.webp` 的图片响应 URL，作为备选高分链接。

## 精确修改点（不改变整体结构）
- d:\VideoRobot2\backend\utils\jimeng_text2img.py
  - [1416] `click_thumbs_and_collect_fullsize`：点击缩略图选择器改为包含匹配，并在点击后等待 `image-player` 与详情图可见。
  - [1446–1535] `collect_fullsize_from_nodes_container` / `collect_fullsize_from_current_dialog`：
    - 优先点击 `img[data-apm-action*="record-card"]`，随后统一等待与提取逻辑（详情优先）。
  - [1549–1567] `extract_highres_from_player`：弃用“预览优先”，改为“详情优先，失败再回退预览或最大面积”。
  - [1597–1615] `get_player_best_info`：若存在详情图直接以详情图为 `bestSrc`；否则保留面积最大策略。
  - [1744–1765] `extract_detail_card_from_player`：增强为等待 `complete/naturalWidth>0` 与 `srcset` 解析，返回最优 URL。
  - [1821–1929] `wait_for_generation_complete`：
    - 保留 `div[class*="card-icon-button"] svg` 检测，同时增加 `aria-label`/`role="img"` 兜底。
  - [2131–2149] `extract_fullsize_urls_from_dom`：收集玩家范围所有 `img` 时，统一使用新的 URL 解析函数。

## 验证步骤
- 运行一次生成流程，自动点击缩略图，等待详情图加载。
- 断言返回 URL 包含 `aigc_resize:1080:1080` 或分辨率 ≥ 1080x1080，且来自 `p16-dreamina-sign-sg.ibyteimg.com`。
- 记录日志：选中的选择器、等待耗时与最终 URL。

## 交付结果
- 修改上述函数中的选择器与等待逻辑，保持原代码风格与 Playwright 用法。
- 不新增文件，仅更新现有函数。

请确认后我将按上述计划进行精确代码改动并回归验证。