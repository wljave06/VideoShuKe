<template>
  <div class="jimeng-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-content">
        <div class="title-section">
          <div class="title-icon">
            <el-icon size="32"><VideoPlay /></el-icon>
          </div>
          <h1 class="page-title">首尾帧图生视频</h1>
        </div>
        <div class="status-section">
          <!-- 创建任务按钮 -->
          <el-button
            class="btn-batch-add"
            size="large"
            @click="showCreateTaskDialog"
          >
            <el-icon><Plus /></el-icon> 创建任务
          </el-button>

          <!-- 导入表格按钮 -->
          <el-button
            class="btn-import"
            size="large"
            @click="showTableImportDialog"
            :disabled="tableImportLoading"
          >
            <el-icon><Upload /></el-icon> 导入表格
          </el-button>
        </div>
      </div>
    </div>

    <!-- 统计概览 -->
    <StatusCountDisplay :stats="normalizedStats" />

    <!-- 任务管理 -->
    <div class="task-management">
      <div class="panel-title">
        <h3>任务列表</h3>
        <div class="toolbar-actions">
          <el-select
            v-model="statusFilter"
            placeholder="筛选状态"
            clearable
            @change="handleStatusFilter"
            class="status-filter"
          >
            <el-option label="全部" :value="null" />
            <el-option label="排队中" value="0" />
            <el-option label="生成中" value="1" />
            <el-option label="已完成" value="2" />
            <el-option label="失败" value="3" />
          </el-select>
          <el-button
            class="btn-refresh"
            @click="refreshTasks"
            :disabled="loading"
          >
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
          <!-- 批量重试按钮 -->
          <el-button
            class="btn-batch-retry"
            @click="batchRetryFailedTasks"
            :disabled="batchRetryLoading"
          >
            <el-icon><RefreshRight /></el-icon> 批量重试
          </el-button>
          <!-- 批量操作按钮 -->
          <el-button
            class="btn-batch-delete"
            @click="batchDeleteTasks"
            :disabled="selectedTasks.length === 0"
          >
            <el-icon><Delete /></el-icon> 批量删除 ({{ selectedTasks.length }})
          </el-button>

          <el-button
            class="btn-batch-download"
            @click="batchDownloadVideos"
            :disabled="selectedCompletedTasks.length === 0 || batchDownloadLoading"
          >
            <el-icon><Download /></el-icon> 批量下载 ({{ selectedCompletedTasks.length }})
          </el-button>
          </div>
        </div>

      <!-- 任务表格 -->
      <div class="task-table-container">
        <el-table
          :data="tasks"
          v-loading="loading"
          @selection-change="handleSelectionChange"
          class="modern-table"
          stripe
          :header-cell-style="{ background: '#f8fafc', color: '#374151', fontWeight: '600' }"
        >
          <el-table-column
            type="selection"
            width="55"
            :selectable="isTaskSelectable"
          />
          <el-table-column prop="id" label="ID" width="80" align="center" />

          <el-table-column label="图片" width="200">
            <template #default="{ row }">
              <div class="input-images-preview">
                <!-- 首帧图片 -->
                <div class="input-image-item" v-if="row.first_frame_image_path">
                  <div v-if="getImageUrl(row.first_frame_image_path)" class="image-wrapper">
                    <el-image
                      :src="getImageUrl(row.first_frame_image_path)"
                      fit="cover"
                      class="input-image-thumb"
                      :preview-src-list="[getImageUrl(row.first_frame_image_path)]"
                    />
                  </div>
                  <div v-else class="local-file-indicator" :title="row.first_frame_image_path">
                    <el-icon size="16"><Picture /></el-icon>
                    <span class="filename-text">{{ getImageFilename(row.first_frame_image_path) }}</span>
                  </div>
                </div>
                <!-- 尾帧图片 -->
                <div class="input-image-item" v-if="row.last_frame_image_path">
                  <div v-if="getImageUrl(row.last_frame_image_path)" class="image-wrapper">
                    <el-image
                      :src="getImageUrl(row.last_frame_image_path)"
                      fit="cover"
                      class="input-image-thumb"
                      :preview-src-list="[getImageUrl(row.last_frame_image_path)]"
                    />
                  </div>
                  <div v-else class="local-file-indicator" :title="row.last_frame_image_path">
                    <el-icon size="16"><Picture /></el-icon>
                    <span class="filename-text">{{ getImageFilename(row.last_frame_image_path) }}</span>
                  </div>
                </div>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="提示词" min-width="250">
            <template #default="{ row }">
              <div class="prompt-cell">
                <el-tooltip :content="row.prompt || ''" placement="top">
                  <span class="prompt-text">{{ truncateText(row.prompt || '', 80) }}</span>
                </el-tooltip>
              </div>
            </template>
          </el-table-column>

          <el-table-column prop="model" label="模型" width="120" align="center">
            <template #default="{ row }">
              <el-tag class="model-tag">{{ row.model || 'Video 3.0' }}</el-tag>
            </template>
          </el-table-column>

          <el-table-column prop="second" label="时长" width="100" align="center">
            <template #default="{ row }">
              <el-tag type="warning" class="duration-tag">{{ row.second || 5 }}s</el-tag>
            </template>
          </el-table-column>

          <el-table-column prop="resolution" label="分辨率" width="120" align="center">
            <template #default="{ row }">
              <el-tag type="info" class="resolution-tag">{{ row.resolution || '1080p' }}</el-tag>
            </template>
          </el-table-column>

          <el-table-column prop="status" label="状态" width="120" align="center">
            <template #default="{ row }">
                  <el-tag
                :type="getStatusType(row.status)"
                :class="['status-tag', { 'processing-tag': row.status === 1 }]"
              >
                <el-icon v-if="row.status === 1" class="rotating-icon"><Loading /></el-icon>
                {{ row.status_text || '-' }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="200" fixed="right" align="center">
            <template #default="{ row }">
              <div class="action-buttons">
                <!-- 失败原因图标 -->
                <el-tooltip
                  v-if="row.status === 3"
                  placement="top"
                  :content="getFailureTooltipContent(row)"
                  raw-content
                >
                  <el-icon class="failure-icon" size="18">
                    <CircleCloseFilled />
                  </el-icon>
                </el-tooltip>

                <!-- 查看视频按钮 -->
                <el-button
                  v-if="row.video_url"
                  class="btn-view" size="small"
                  @click="previewVideo(row.video_url)"
                >
                  <el-icon><VideoPlay /></el-icon> 查看
                </el-button>

                <!-- 下载视频按钮 -->
                <el-button
                  v-if="row.video_url"
                  class="btn-download" size="small"
                  @click="downloadVideo(row)"
                >
                  <el-icon><Download /></el-icon> 下载
                </el-button>

                <!-- 重试按钮 -->
                <el-button
                  v-if="row.status === 3"
                  class="btn-retry" size="small"
                  :disabled="row.status === 1"
                  @click="retryTask(row.id)"
                >
                  <el-icon><RefreshRight /></el-icon> 重试
                </el-button>

                <!-- 删除按钮 -->
                <el-button
                  class="btn-delete" size="small"
                  :disabled="row.status === 1"
                  @click="deleteTask(row.id)"
                >
                  删除
                </el-button>
                </div>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-wrapper">
          <el-pagination
            :current-page="pagination.page"
            :page-size="pagination.page_size"
            :page-sizes="[10, 20, 50, 100, 1000]"
            :total="pagination.total"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
    </div>

    <!-- 图片预览对话框 -->
    <el-dialog
      v-model="imagePreviewVisible"
      title="图片预览"
      width="60%"
      @close="imagePreviewVisible = false"
    >
      <div class="image-preview">
        <img :src="previewImageUrl" alt="预览图片" style="max-width: 100%; height: auto;" />
            </div>
    </el-dialog>

    <!-- 视频预览对话框 -->
    <el-dialog
      v-model="videoPreviewVisible"
      title="视频预览"
      width="70%"
      @close="videoPreviewVisible = false"
    >
      <div class="video-preview">
        <video :src="previewVideoUrl" controls style="max-width: 100%; height: auto;">
          您的浏览器不支持视频播放
        </video>
              </div>
    </el-dialog>

    <!-- 创建任务对话框 -->
    <el-dialog
      v-model="createTaskDialogVisible"
      title="创建首尾帧图生视频任务"
      width="600px"
      destroy-on-close
      @close="resetCreateTaskDialog"
    >
      <el-form :model="createTaskForm" label-width="120px">
        <!-- 第一张图片上传 -->
        <el-form-item label="首帧图片" required>
          <div class="image-upload-container">
            <input
              ref="firstImageInput"
              type="file"
              accept="image/*"
              style="display: none"
              @change="handleFirstImageSelect"
            />
            <div
              v-if="!createTaskForm.firstImage"
              class="upload-placeholder"
              @click="triggerFirstImageInput"
            >
              <el-icon size="40"><Plus /></el-icon>
              <p>点击上传首帧图片</p>
            </div>
            <div v-else class="image-preview-container">
              <img :src="createTaskForm.firstImagePreview" alt="首帧图片" class="preview-image" />
              <div class="image-actions">
                <el-button size="small" type="danger" @click="removeFirstImage">删除</el-button>
              </div>
            </div>
          </div>
        </el-form-item>

        <!-- 第二张图片上传 -->
        <el-form-item label="尾帧图片" required>
          <div class="image-upload-container">
            <input
              ref="lastImageInput"
              type="file"
              accept="image/*"
              style="display: none"
              @change="handleLastImageSelect"
            />
            <div
              v-if="!createTaskForm.lastImage"
              class="upload-placeholder"
              @click="triggerLastImageInput"
            >
              <el-icon size="40"><Plus /></el-icon>
              <p>点击上传尾帧图片</p>
            </div>
            <div v-else class="image-preview-container">
              <img :src="createTaskForm.lastImagePreview" alt="尾帧图片" class="preview-image" />
              <div class="image-actions">
                <el-button size="small" type="danger" @click="removeLastImage">删除</el-button>
              </div>
            </div>
          </div>
        </el-form-item>

        <!-- 视频模型 -->
        <el-form-item label="视频模型">
          <el-select v-model="createTaskForm.model" placeholder="请选择视频模型">
            <el-option label="Video 3.0" value="Video 3.0" />
            <el-option label="Video 3.0 Pro" value="Video 3.0 Pro" />
            <el-option label="Video S2.0 Pro" value="Video S2.0 Pro" />
          </el-select>
        </el-form-item>

        <!-- 视频时长 -->
        <el-form-item label="视频时长">
          <el-select v-model="createTaskForm.second" placeholder="请选择视频时长">
            <el-option label="5秒" :value="5" />
            <el-option label="10秒" :value="10" />
          </el-select>
        </el-form-item>

        <!-- 分辨率 -->
        <el-form-item label="分辨率">
          <el-select v-model="createTaskForm.resolution" placeholder="请选择分辨率">
            <el-option label="720P" value="720p" />
            <el-option label="1080P" value="1080p" />
          </el-select>
        </el-form-item>

        <!-- 提示词 -->
        <el-form-item label="提示词">
          <el-input
            v-model="createTaskForm.prompt"
            type="textarea"
            :rows="4"
            placeholder="请输入提示词（可选）"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button class="cancel-button" @click="createTaskDialogVisible = false">取消</el-button>
          <el-button
            class="btn-batch-add"
            @click="submitCreateTask"
            :loading="createTaskLoading"
            :disabled="!createTaskForm.firstImage || !createTaskForm.lastImage"
          >
            创建任务
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 表格导入对话框 -->
    <el-dialog
      v-model="tableImportDialogVisible"
      title="导入表格"
      width="80%"
      max-width="1000px"
      destroy-on-close
      @close="resetTableImportDialog"
    >
      <div class="table-import-container">
        <!-- 文件选择区域 -->
        <div class="file-select-area" v-if="tableData.length === 0">
          <input
            ref="tableFileInput"
            type="file"
            accept=".csv,.xlsx,.xls"
            style="display: none"
            @change="handleTableFileSelect"
          />
          <div
            class="upload-drag-area"
            @click="triggerTableFileInput"
            @drop="handleTableFileDrop"
            @dragover.prevent
            @dragenter.prevent
          >
            <div class="upload-content">
              <el-icon size="64" class="upload-icon"><Upload /></el-icon>
              <div class="upload-text">
                <h3 class="primary-text">点击选择表格文件或拖拽到此处</h3>
                <p class="secondary-text">支持 CSV、Excel (.xlsx, .xls) 格式</p>
                <p class="hint-text">固定格式: 首帧图片 | 尾帧图片 | 提示词 | 秒数 | 分辨率</p>
                <div class="template-download">
                  <el-button
                    class="btn-download"
                    size="small"
                    @click.stop="downloadTemplate"
                    plain
                  >
                    <template #icon>
                      <el-icon><Download /></el-icon>
                    </template>
                    下载表格模板
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 数据预览区域 -->
        <div class="data-preview-area" v-if="tableData.length > 0">
          <!-- 数据预览 -->
          <div class="data-preview">
            <div class="preview-header">
              <h4>数据预览 (共 {{ tableData.length }} 行，显示前 10 行)</h4>
              <el-button class="btn-clear" size="small" @click="resetTableImportDialog">
                <template #icon>
                  <el-icon><Close /></el-icon>
                </template>
                重新选择文件
              </el-button>
            </div>

            <div class="preview-table">
              <el-table :data="previewData" border stripe max-height="300">
                <el-table-column
                  v-for="header in tableHeaders"
                  :key="header"
                  :prop="header"
                  :label="header"
                  min-width="120"
                  show-overflow-tooltip
                >
                  <template #default="{ row }">
                    <span>{{ row[header] }}</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button class="cancel-button" @click="tableImportDialogVisible = false">取消</el-button>
          <el-button
            class="btn-import"
            @click="submitTableImportTasks"
            :loading="tableImportLoading"
            :disabled="tableData.length === 0"
          >
            <template #icon>
              <el-icon><Plus /></el-icon>
            </template>
            创建任务 ({{ tableData.length }})
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onActivated, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  VideoPlay,
  Delete,
  Download,
  Refresh,
  RefreshRight,
  Plus,
  Upload,
  Close,
  CircleCloseFilled,
  Loading,
  Picture
} from '@element-plus/icons-vue'
import { firstLastFrameImg2videoAPI } from '@/utils/api'
import StatusCountDisplay from '@/components/StatusCountDisplay.vue'
import * as XLSX from 'xlsx'

// 响应式数据
const loading = ref(false)
const tasks = ref([])
const selectedTasks = ref([])
const statusFilter = ref(null)
const imageUrls = ref(new Map()) // 存储图片URL的映射
    const stats = reactive({
  total_tasks: 0,
  pending_tasks: 0,
  processing_tasks: 0,
  completed_tasks: 0,
  failed_tasks: 0
})

// 统一数据格式的计算属性
const normalizedStats = computed(() => ({
  total: stats.total_tasks || 0,
  queued: stats.pending_tasks || 0,
  processing: stats.processing_tasks || 0,
  completed: stats.completed_tasks || 0,
  failed: stats.failed_tasks || 0
}))

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
    })

// 批量下载相关状态
const batchDownloadLoading = ref(false)

// 批量重试状态
const batchRetryLoading = ref(false)

// 表格导入相关状态
const tableImportLoading = ref(false)
const tableImportDialogVisible = ref(false)
const tableFileInput = ref(null)
const tableData = ref([])
const tableHeaders = ref([])
const previewData = ref([])
const importSettings = reactive({
  model: 'Video 3.0',
  defaultDuration: 5
})

// 创建任务相关状态
const createTaskDialogVisible = ref(false)
const createTaskLoading = ref(false)
const firstImageInput = ref(null)
const lastImageInput = ref(null)
const createTaskForm = reactive({
  firstImage: null,
  firstImagePreview: '',
  lastImage: null,
  lastImagePreview: '',
  model: 'Video 3.0',
  second: 5,
  resolution: '1080p',
  prompt: ''
})



// 预览相关状态
const imagePreviewVisible = ref(false)
const previewImageUrl = ref('')
const videoPreviewVisible = ref(false)
const previewVideoUrl = ref('')

// 本地文件预览缓存
const localFileCache = ref(new Map())

// 计算属性
const selectedCompletedTasks = computed(() => {
  if (!selectedTasks.value || !Array.isArray(selectedTasks.value)) {
    return []
  }
  return selectedTasks.value.filter(task =>
    task &&
    task.status === 2 &&
    task.video_url &&
    task.video_url.trim() !== ''
  )
})

// 方法
const loadTasks = async () => {
  try {
    loading.value = true
    const params = {
      page: pagination.page,
      page_size: pagination.page_size
    }

    if (statusFilter.value !== null) {
      params.status = statusFilter.value
    }

    const response = await firstLastFrameImg2videoAPI.getTasks(params)

    if (response.data.success) {
      tasks.value = response.data.data || []
      pagination.total = response.data.pagination?.total || 0

      // 调试：打印第一个任务的数据结构
      if (tasks.value.length > 0) {
        console.log('第一个任务数据结构:', tasks.value[0])
        console.log('第一个任务的图片相关字段:', {
          first_frame_image_path: tasks.value[0].first_frame_image_path,
          last_frame_image_path: tasks.value[0].last_frame_image_path,
          first_image_path: tasks.value[0].first_image_path,
          last_image_path: tasks.value[0].last_image_path,
          firstImage: tasks.value[0].firstImage,
          lastImage: tasks.value[0].lastImage,
          image_path: tasks.value[0].image_path,
          input_images: tasks.value[0].input_images
        })
      }

      // 预加载图片URL
      await preloadImagesForTasks()
    } else {
      ElMessage.error(response.data.message || '加载任务列表失败')
    }
  } catch (error) {
    console.error('加载任务列表失败:', error)
    ElMessage.error('加载任务列表失败')
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    const response = await firstLastFrameImg2videoAPI.getStats()
    if (response.data.success) {
      Object.assign(stats, response.data.data)
    }
  } catch (error) {
    console.error('加载统计信息失败:', error)
  }
}

// 预加载任务的图片URL
const preloadImagesForTasks = async () => {
  const imagePromises = []

  tasks.value.forEach(task => {
    // 预加载首帧图片
    if (task.first_frame_image_path) {
      imagePromises.push(preloadImageUrl(task.first_frame_image_path))
    }
    // 预加载尾帧图片
    if (task.last_frame_image_path) {
      imagePromises.push(preloadImageUrl(task.last_frame_image_path))
    }
  })

  try {
    await Promise.allSettled(imagePromises)
    console.log('图片预加载完成')
  } catch (error) {
    console.error('图片预加载失败:', error)
  }
}



// 显示创建任务对话框
const showCreateTaskDialog = () => {
  createTaskDialogVisible.value = true
}

// 显示表格导入对话框
const showTableImportDialog = () => {
  tableImportDialogVisible.value = true
}

// 触发表格文件选择
const triggerTableFileInput = () => {
  tableFileInput.value?.click()
}

// 处理表格文件选择
const handleTableFileSelect = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return

  try {
    tableImportLoading.value = true
    await parseTableFile(file)
  } catch (error) {
    console.error('解析表格文件失败:', error)
    ElMessage.error('解析表格文件失败')
  } finally {
    tableImportLoading.value = false
    event.target.value = ''
  }
}

// 处理表格文件拖拽
const handleTableFileDrop = async (event) => {
  event.preventDefault()
  const files = event.dataTransfer?.files
  if (!files || files.length === 0) return

  const file = files[0]
  try {
    tableImportLoading.value = true
    await parseTableFile(file)
  } catch (error) {
    console.error('解析表格文件失败:', error)
    ElMessage.error('解析表格文件失败')
  } finally {
    tableImportLoading.value = false
  }
}

// 解析表格文件
const parseTableFile = async (file) => {
  const fileExtension = file.name.split('.').pop()?.toLowerCase()

  if (!['csv', 'xlsx', 'xls'].includes(fileExtension)) {
    throw new Error('不支持的文件格式，请选择CSV或Excel文件')
  }

  if (fileExtension === 'csv') {
    await parseCSVFile(file)
  } else {
    await parseExcelFile(file)
  }
}

// 解析CSV文件
const parseCSVFile = async (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const text = e.target?.result
        const lines = text.split('\n').filter(line => line.trim())

        if (lines.length < 2) {
          reject(new Error('表格数据不完整'))
          return
        }

        const headers = lines[0].split(',').map(h => h.trim().replace(/"/g, ''))
        const data = lines.slice(1).map(line => {
          const values = line.split(',').map(v => v.trim().replace(/"/g, ''))
          const row = {}
          headers.forEach((header, index) => {
            row[header] = values[index] || ''
          })
          return row
        })

        tableHeaders.value = headers
        tableData.value = data
        previewData.value = data.slice(0, 10) // 只预览前10行

        ElMessage.success(`成功解析 ${data.length} 行数据`)
        resolve(data)
      } catch (error) {
        reject(error)
      }
    }
    reader.onerror = () => reject(new Error('文件读取失败'))
    reader.readAsText(file, 'utf-8')
  })
}

// 解析Excel文件
const parseExcelFile = async (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const arrayBuffer = new Uint8Array(e.target?.result)
        const workbook = XLSX.read(arrayBuffer, { type: 'array' })

        // 获取第一个工作表
        const firstSheetName = workbook.SheetNames[0]
        if (!firstSheetName) {
          reject(new Error('Excel文件中没有找到工作表'))
          return
        }

        const worksheet = workbook.Sheets[firstSheetName]
        const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: '' })

        if (jsonData.length < 2) {
          reject(new Error('表格数据不完整'))
          return
        }

        // 获取表头和数据
        const headers = jsonData[0].map(h => String(h).trim())
        const rows = jsonData.slice(1).map(row => {
          const rowData = {}
          headers.forEach((header, index) => {
            rowData[header] = String(row[index] || '').trim()
          })
          return rowData
        }).filter(row => {
          // 过滤掉空行
          return Object.values(row).some(value => value !== '')
        })

        tableHeaders.value = headers
        tableData.value = rows
        previewData.value = rows.slice(0, 10) // 只预览前10行

        resolve()
      } catch (error) {
        reject(new Error('Excel文件解析失败: ' + error.message))
      }
    }
    reader.onerror = () => reject(new Error('文件读取失败'))
    reader.readAsArrayBuffer(file)
  })
}

// 重置表格导入对话框
const resetTableImportDialog = () => {
  tableData.value = []
  tableHeaders.value = []
  previewData.value = []
  importSettings.model = 'Video 3.0'
  importSettings.defaultDuration = 5
}

// 自动转换分辨率格式
const normalizeResolution = (resolution) => {
  if (!resolution || typeof resolution !== 'string') {
    return '1080p'  // 默认分辨率
  }

  const res = resolution.toString().toLowerCase().trim()

  // 如果已经是正确格式，直接返回
  if (res === '720p' || res === '1080p') {
    return res
  }

  // 转换数字格式
  if (res === '720' || res === '1080') {
    return res + 'p'
  }

  // 处理其他可能的格式
  if (res.includes('720')) {
    return '720p'
  } else if (res.includes('1080')) {
    return '1080p'
  }

  // 默认返回1080p
  return '1080p'
}

// 提交表格导入任务
const submitTableImportTasks = async () => {
  if (tableData.value.length === 0) {
    ElMessage.warning('请先选择并解析表格文件')
    return
  }

  if (tableHeaders.value.length < 4) {
    ElMessage.warning('表格至少需要4列：首帧图片、尾帧图片、提示词、秒数')
    return
  }

  try {
    tableImportLoading.value = true

    // 按固定格式构建任务列表：第1列首帧图片，第2列尾帧图片，第3列提示词，第4列秒数，第5列分辨率（可选）
    const tasks = tableData.value.map(row => {
      const rowValues = Object.values(row)
      const originalResolution = rowValues[4] || '1080p'
      const normalizedResolution = normalizeResolution(originalResolution)

      // 如果进行了格式转换，记录日志
      if (originalResolution && originalResolution !== normalizedResolution) {
        console.log(`分辨率格式自动转换: ${originalResolution} → ${normalizedResolution}`)
      }

      return {
        first_image_path: rowValues[0] || '',
        last_image_path: rowValues[1] || '',
        model: importSettings.model,
        prompt: rowValues[2] || '', // 第3列是提示词
        second: parseInt(rowValues[3]) || importSettings.defaultDuration, // 第4列是秒数
        resolution: normalizedResolution
      }
    }).filter(task => task.first_image_path.trim() !== '' && task.last_image_path.trim() !== '') // 过滤空的图片路径

    if (tasks.length === 0) {
      ElMessage.warning('没有有效的任务数据')
      return
    }

    // 调用API批量创建任务
    const response = await firstLastFrameImg2videoAPI.batchCreateTasksFromTable(tasks)

    if (response.data.success) {
      ElMessage.success(`成功创建 ${tasks.length} 个任务`)
      tableImportDialogVisible.value = false
      resetTableImportDialog()

      // 刷新任务列表
      setTimeout(() => {
        loadTasks()
        loadStats()
      }, 1000)
    } else {
      // 显示详细的错误信息
      const message = response.data.message || '创建任务失败'
      const failedTasks = response.data.data?.failed_tasks || []

      if (failedTasks.length > 0) {
        console.error('表格导入失败详情:', failedTasks)
        ElMessage.error(`${message}\n详细错误:\n${failedTasks.slice(0, 3).join('\n')}`)
      } else {
        ElMessage.error(message)
      }
    }
  } catch (error) {
    console.error('表格导入失败:', error)
    ElMessage.error('表格导入失败')
  } finally {
    tableImportLoading.value = false
  }
}

// 下载表格模板
const downloadTemplate = () => {
  // 创建CSV数据 - 只包含表头
  const headers = ['首帧图片路径', '尾帧图片路径', '提示词', '秒数', '分辨率']

  // 构建CSV内容 - 只有表头行，添加BOM以支持Excel正确显示中文
  const BOM = '\uFEFF'
  const csvContent = BOM + headers.join(',')

  // 创建Blob对象，使用UTF-8编码
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })

  // 创建下载链接
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', '首尾帧图生视频导入模板.csv')
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)

  ElMessage.success('模板下载成功')
}

// 重置文件选择器 - 简化版本，只清空value值
const resetFileInput = (inputRef) => {
  if (inputRef.value) {
    try {
      inputRef.value.value = ''
      console.log('文件选择器已重置')
    } catch (error) {
      console.error('重置文件选择器失败:', error)
    }
  }
}

// 触发第一张图片选择
const triggerFirstImageInput = () => {
  firstImageInput.value?.click()
}

// 触发第二张图片选择
const triggerLastImageInput = () => {
  lastImageInput.value?.click()
}

// 处理第一张图片选择
const handleFirstImageSelect = (event) => {
  try {
    const file = event.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      ElMessage.warning('请选择图片文件')
      // 重置文件选择器
      event.target.value = ''
      return
    }

    createTaskForm.firstImage = file
    createTaskForm.firstImagePreview = URL.createObjectURL(file)

    // 重置文件选择器确保下次选择时能触发change事件
    event.target.value = ''

    console.log('首帧图片上传成功:', file.name)
    ElMessage.success('首帧图片上传成功')
  } catch (error) {
    console.error('处理首帧图片选择时出错:', error)
    ElMessage.error('上传首帧图片失败')
  }
}

// 处理第二张图片选择
const handleLastImageSelect = (event) => {
  try {
    const file = event.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      ElMessage.warning('请选择图片文件')
      // 重置文件选择器
      event.target.value = ''
      return
    }

    createTaskForm.lastImage = file
    createTaskForm.lastImagePreview = URL.createObjectURL(file)

    // 重置文件选择器确保下次选择时能触发change事件
    event.target.value = ''

    console.log('尾帧图片上传成功:', file.name)
    ElMessage.success('尾帧图片上传成功')
  } catch (error) {
    console.error('处理尾帧图片选择时出错:', error)
    ElMessage.error('上传尾帧图片失败')
  }
}

// 删除第一张图片
const removeFirstImage = () => {
  try {
    if (createTaskForm.firstImagePreview) {
      URL.revokeObjectURL(createTaskForm.firstImagePreview)
    }
    createTaskForm.firstImage = null
    createTaskForm.firstImagePreview = ''

    // 重置对应的文件选择器
    setTimeout(() => {
      resetFileInput(firstImageInput)
    }, 50)
  } catch (error) {
    console.error('删除首帧图片时出错:', error)
    // 即使出错也要清空数据
    createTaskForm.firstImage = null
    createTaskForm.firstImagePreview = ''
  }
}

// 删除第二张图片
const removeLastImage = () => {
  try {
    if (createTaskForm.lastImagePreview) {
      URL.revokeObjectURL(createTaskForm.lastImagePreview)
    }
    createTaskForm.lastImage = null
    createTaskForm.lastImagePreview = ''

    // 重置对应的文件选择器
    setTimeout(() => {
      resetFileInput(lastImageInput)
    }, 50)
  } catch (error) {
    console.error('删除尾帧图片时出错:', error)
    // 即使出错也要清空数据
    createTaskForm.lastImage = null
    createTaskForm.lastImagePreview = ''
  }
}

// 重置创建任务对话框
const resetCreateTaskDialog = () => {
  try {
    // 删除图片预览和数据
    removeFirstImage()
    removeLastImage()

    // 重置表单数据
    createTaskForm.model = 'Video 3.0'
    createTaskForm.second = 5
    createTaskForm.resolution = '1080p'
    createTaskForm.prompt = ''

    // 延迟重置文件选择器，确保DOM还存在
    setTimeout(() => {
      resetFileInput(firstImageInput)
      resetFileInput(lastImageInput)
    }, 100)

    console.log('创建任务对话框已重置')
  } catch (error) {
    console.error('重置创建任务对话框时出错:', error)
    // 即使出错也要重置基本数据
    createTaskForm.model = 'Video 3.0'
    createTaskForm.second = 5
    createTaskForm.resolution = '1080p'
    createTaskForm.prompt = ''
  }
}

// 提交创建任务
const submitCreateTask = async () => {
  if (!createTaskForm.firstImage || !createTaskForm.lastImage) {
    ElMessage.warning('请上传首帧和尾帧图片')
    return
  }

  try {
    createTaskLoading.value = true

    // 创建FormData对象
    const formData = new FormData()
    formData.append('first_image', createTaskForm.firstImage)
    formData.append('last_image', createTaskForm.lastImage)
    formData.append('model', createTaskForm.model)
    formData.append('second', createTaskForm.second)
    formData.append('resolution', createTaskForm.resolution)
    formData.append('prompt', createTaskForm.prompt || '')

    const response = await firstLastFrameImg2videoAPI.createTask(formData)

    if (response.data.success) {
      ElMessage.success('任务创建成功')
      createTaskDialogVisible.value = false
      resetCreateTaskDialog()

      // 刷新任务列表
      setTimeout(() => {
        refreshTasks()
      }, 1000)
    } else {
      ElMessage.error(response.data.message || '创建任务失败')
    }
  } catch (error) {
    console.error('创建任务失败:', error)
    ElMessage.error('创建任务失败')
  } finally {
    createTaskLoading.value = false
  }
}

const handleSelectionChange = (selection) => {
  selectedTasks.value = selection || []
}

const batchDeleteTasks = async () => {
  if (!selectedTasks.value || selectedTasks.value.length === 0) {
    ElMessage.warning('请先选择要删除的任务')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedTasks.value.length} 个任务吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    const taskIds = selectedTasks.value.map(task => task.id)
    const response = await firstLastFrameImg2videoAPI.batchDeleteTasks(taskIds)

    if (response.data.success) {
      ElMessage.success(response.data.message || '批量删除成功')
      selectedTasks.value = []
      await loadTasks()
      await loadStats()
    } else {
      ElMessage.error(response.data.message || '批量删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error('批量删除失败')
    }
  }
}

const batchDownloadVideos = async () => {
  if (!selectedCompletedTasks.value || selectedCompletedTasks.value.length === 0) {
    ElMessage.warning('请先选择已完成的任务')
    return
  }

  try {
    batchDownloadLoading.value = true
    const taskIds = selectedCompletedTasks.value.map(task => task.id)
    const response = await firstLastFrameImg2videoAPI.batchDownload(taskIds)

    if (response.data.success) {
      ElMessage.success(response.data.message || '开始批量下载')
      ElMessage.info('请在桌面选择下载文件夹')
    } else {
      ElMessage.error(response.data.message || '批量下载失败')
    }
  } catch (error) {
    console.error('批量下载失败:', error)
    ElMessage.error('批量下载失败')
  } finally {
    batchDownloadLoading.value = false
  }
}

const deleteTask = async (taskId) => {
  try {
    await ElMessageBox.confirm('确定要删除这个任务吗？', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })

    const response = await firstLastFrameImg2videoAPI.deleteTask(taskId)
    if (response.data.success) {
      ElMessage.success('删除成功')
      await loadTasks()
      await loadStats()
    } else {
      ElMessage.error(response.data.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除任务失败:', error)
      ElMessage.error('删除任务失败')
    }
  }
}

const retryTask = async (taskId) => {
  try {
    const response = await firstLastFrameImg2videoAPI.retryTask(taskId)
    if (response.data.success) {
      ElMessage.success('任务已重新加入队列')
      await loadTasks()
      await loadStats()
    } else {
      ElMessage.error(response.data.message || '重试失败')
    }
  } catch (error) {
    console.error('重试任务失败:', error)
    ElMessage.error('重试任务失败')
  }
}

const previewImage = (imagePath) => {
  if (imagePath) {
    // 如果是本地路径，需要转换为可访问的URL
    if (imagePath.startsWith('/') || imagePath.includes(':\\')) {
      // 本地文件路径，无法直接预览
      ElMessage.warning('本地图片无法直接预览，请在文件管理器中查看')
      return
    }
    previewImageUrl.value = imagePath
    imagePreviewVisible.value = true
  }
}

const previewVideo = (videoUrl) => {
  if (videoUrl) {
    previewVideoUrl.value = videoUrl
    videoPreviewVisible.value = true
  }
}

const downloadVideo = async (row) => {
  if (!row.video_url) {
    ElMessage.warning('没有可下载的视频')
    return
  }

  try {
    // 调用系统文件夹选择器并下载
    await selectFolderAndDownloadVideo(row.video_url, `first_last_frame_video_${row.id}.mp4`)
  } catch (error) {
    console.error('下载视频失败:', error)
    ElMessage.error('下载视频失败')
  }
}

// 选择文件夹并下载视频 - 使用系统对话框
const selectFolderAndDownloadVideo = async (videoUrl, filename) => {
  try {
    // 调用后端API触发文件夹选择器
    const response = await firstLastFrameImg2videoAPI.downloadSingleVideo({
      video_url: videoUrl,
      filename: filename
    })

    if (response.data.success) {
      ElMessage.success('请在桌面选择下载文件夹')
    } else {
      // 如果后端调用失败，使用前端下载方式
      const link = document.createElement('a')
      link.href = videoUrl
      link.download = filename
      link.target = '_blank'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      ElMessage.success('开始下载视频')
    }
  } catch (error) {
    console.error('文件夹选择失败:', error)
    // 降级到前端下载方式
    const link = document.createElement('a')
    link.href = videoUrl
    link.download = filename
    link.target = '_blank'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    ElMessage.success('开始下载视频')
  }
}

const getImageFilename = (imagePath) => {
  if (!imagePath) return '-'
  return imagePath.split(/[/\\]/).pop() || imagePath
}

// 读取本地文件为Data URL
const readLocalFile = async (filePath) => {
  try {
    // 检查缓存
    if (localFileCache.value.has(filePath)) {
      const cached = localFileCache.value.get(filePath)
      // 如果缓存的是错误标记，直接返回null
      if (cached === 'ERROR') {
        return null
      }
      return cached
    }

    // 通过后端API读取本地文件
    const response = await firstLastFrameImg2videoAPI.getLocalFile({ path: filePath })

    if (response.data.success && response.data.data) {
      const dataUrl = response.data.data
      // 缓存成功结果
      localFileCache.value.set(filePath, dataUrl)
      return dataUrl
    } else {
      // 缓存失败结果，避免重复请求
      localFileCache.value.set(filePath, 'ERROR')
      console.warn('读取本地文件失败:', response.data.message || '未知错误')
    }
  } catch (error) {
    // 缓存错误结果，避免重复请求
    localFileCache.value.set(filePath, 'ERROR')
    console.error('读取本地文件失败:', error)
  }
  return null
}

// 预加载图片URL
const preloadImageUrl = async (imagePath) => {
  if (!imagePath) return null

  // 检查缓存
  if (imageUrls.value.has(imagePath)) {
    return imageUrls.value.get(imagePath)
  }

  let url = ''

  // 如果是远程URL（以http或https开头），直接返回
  if (imagePath.startsWith('http://') || imagePath.startsWith('https://')) {
    url = imagePath
  }
  // 检查是否是上传到后端的临时文件路径
  else if (imagePath.includes('tmp') && imagePath.includes('first_last_frame_upload')) {
    // 如果是上传到后端的临时文件，提取文件名并构建静态服务器URL
    let fileName = imagePath
    if (imagePath.includes('/')) {
      fileName = imagePath.split('/').pop()  // Unix风格路径
    } else if (imagePath.includes('\\')) {
      fileName = imagePath.split('\\').pop()  // Windows风格路径
    }

    // 构建为首尾帧图片的静态服务器URL
    url = `http://localhost:8888/static/first-last-frame-images/${fileName}`
  }
  // 对于表格导入的本地图片路径，增加更严格的判断，避免无效路径
  else if (imagePath.startsWith('/') || imagePath.includes(':\\')) {
    // 基本路径验证：检查是否为有效的图片文件扩展名
    const validExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    const hasValidExtension = validExtensions.some(ext =>
      imagePath.toLowerCase().endsWith(ext)
    )

    // 检查路径长度，避免明显无效的路径
    const isValidLength = imagePath.length > 5 && imagePath.length < 500

    if (hasValidExtension && isValidLength) {
      console.log('尝试读取本地文件:', imagePath)
      url = await readLocalFile(imagePath)
    } else {
      console.warn('跳过无效的本地图片路径:', imagePath)
      // 缓存null结果，避免重复检查
      imageUrls.value.set(imagePath, '')
    }
  }

  // 缓存结果
  if (url) {
    imageUrls.value.set(imagePath, url)
  }

  return url
}

// 获取图片URL（同步版本，用于模板）
const getImageUrl = (imagePath) => {
  return imageUrls.value.get(imagePath) || ''
}

const truncateText = (text, maxLength) => {
  if (!text) return ''
  return text.length > maxLength ? text.substring(0, maxLength) + '...' : text
}

const getStatusType = (status) => {
  const statusTypeMap = {
    0: 'info',     // 排队中
    1: 'warning',  // 生成中
    2: 'success',  // 已完成
    3: 'danger'    // 失败
  }
  return statusTypeMap[status] || 'info'
}

// 获取失败原因文本
const getFailureReasonText = (reason) => {
  switch (reason) {
    case 'WEB_INTERACTION_FAILED':
      return '网页交互失败'
    case 'TASK_ID_NOT_OBTAINED':
      return '任务ID获取失败'
    case 'GENERATION_FAILED':
      return '生成失败'
    case 'OTHER_ERROR':
      return '其他错误'
    default:
      return reason || '未知错误'
  }
}

// 获取失败原因tooltip内容
const getFailureTooltipContent = (row) => {
  const reasonText = getFailureReasonText(row.failure_reason)
  if (row.error_message) {
    return `<div><strong>失败原因:</strong> ${reasonText}</div><div><strong>详细信息:</strong> ${row.error_message}</div>`
  }
  return `<div><strong>失败原因:</strong> ${reasonText}</div>`
}

const handleSizeChange = (val) => {
  pagination.page_size = val
  pagination.page = 1
  loadTasks()
}

const handleCurrentChange = (val) => {
  pagination.page = val
  loadTasks()
}

const handleStatusFilter = () => {
  pagination.page = 1
  loadTasks()
}

const refreshTasks = () => {
  loadTasks()
  loadStats()
}

const isTaskSelectable = (row) => {
  return true // 所有任务都可以选择
}

    // 批量重试
const batchRetryFailedTasks = async () => {
  try {
    batchRetryLoading.value = true

    // 获取当前选中的失败任务
    const failedTaskIds = selectedTasks.value
      .filter(task => task.status === 3)
      .map(task => task.id)

    let response
    if (failedTaskIds.length > 0) {
      // 如果有选中的失败任务，只重试这些任务
      response = await firstLastFrameImg2videoAPI.batchRetryTasks(failedTaskIds)
      if (response.data.success) {
        ElMessage.success(`已重新加入队列 ${response.data.data.retry_count} 个任务`)
      } else {
        ElMessage.error(response.data.message || '批量重试失败')
      }
    } else {
      // 如果没有选中的失败任务，重试所有失败任务
      response = await firstLastFrameImg2videoAPI.batchRetryTasks()
      if (response.data.success) {
        ElMessage.success(`已重新加入队列 ${response.data.data.retry_count} 个任务`)
      } else {
        ElMessage.error(response.data.message || '批量重试失败')
      }
    }

    // 刷新任务列表
    refreshTasks()
  } catch (error) {
    console.error('批量重试失败:', error)
    ElMessage.error(error.response?.data?.message || '批量重试失败')
  } finally {
    batchRetryLoading.value = false
  }
}

// 生命周期
    onMounted(() => {
  loadTasks()
      loadStats()
    })

onActivated(() => {
  loadTasks()
  loadStats()
})

onUnmounted(() => {
  // 清理数据
  tasks.value = []
  selectedTasks.value = []
  Object.assign(stats, {
    total_tasks: 0,
    pending_tasks: 0,
    processing_tasks: 0,
    completed_tasks: 0,
    failed_tasks: 0
  })

  // 清理图片缓存
  imageUrls.value.clear()
  localFileCache.value.clear()
})

// 定时刷新
let refreshInterval = null
onMounted(() => {
  refreshInterval = setInterval(() => {
    loadStats()
    // 如果有处理中的任务，也刷新任务列表
    if (stats.processing_tasks > 0) {
      loadTasks()
    }
  }, 5000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
@import '../styles/jimeng-common.css';

/* 页面特定样式 */
.status-section {
  display: flex;
  align-items: center;
  gap: 16px;
}

/* 导入按钮特定样式 */
.import-btn.el-button--success {
  background: var(--success-gradient);
}

.import-btn.el-button--success:hover {
  background: var(--success-gradient);
}

/* 任务管理特定样式 */
.panel-title {
  padding: 24px 32px;
  background: var(--bg-secondary);
}

.refresh-btn {
  padding: 8px 16px;
}

.refresh-btn:hover {
  background-color: #ebb563;
  border-color: #ebb563;
}



/* 图生视频特定样式 */
.image-filename {
  font-size: 13px;
}

/* 输入图片预览样式 */
.input-images-preview {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.input-image-item {
  width: 40px;
  height: 40px;
  position: relative;
}

.input-image-thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 4px;
}

.local-file-indicator {
  width: 40px;
  height: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background-color: #f5f7fa;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  color: #909399;
  font-size: 8px;
  padding: 2px;
  text-align: center;
  cursor: help;
}

.local-file-indicator .el-icon {
  margin-bottom: 2px;
}

.filename-text {
  word-break: break-all;
  line-height: 1;
  max-width: 100%;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.prompt-text {
  font-size: 13px;
  line-height: 1.4;
}

.no-content {
  color: var(--text-muted);
  font-size: 12px;
}

/* 图生视频特定对话框样式 */
.task-item {
  display: flex;
  min-height: 280px;
  max-width: 600px;
  width: 95%;
  margin: 0 auto;
  align-items: stretch;
  box-sizing: border-box;
  gap: 16px;
  padding: 16px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: white;
}



/* 图生视频任务特定样式 */
.list-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e2e8f0;
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.navigation-hint {
  display: flex;
  align-items: center;
  gap: 12px;
}

.hint-text {
  font-size: 12px;
  color: #666;
  background: #f5f5f5;
  padding: 2px 8px;
  border-radius: 12px;
}

.current-page {
  font-size: 14px;
  color: #409eff;
  font-weight: 500;
}

.task-image-container {
  flex: 0 0 auto;
  max-width: 200px;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-right: 16px;
}

.task-image {
  max-width: 100%;
  max-height: 200px;
  width: auto;
  height: auto;
  object-fit: contain;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.task-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.ai-generate-btn {
  white-space: nowrap;
}

.delete-text-btn {
  color: #f56c6c;
  white-space: nowrap;
}

.delete-text-btn:hover {
  color: #f56c6c;
  background: rgba(245, 108, 108, 0.1);
}

/* 任务内容样式 */
.task-prompt {
  font-size: 14px;
  color: #333;
  margin-bottom: 8px;
  word-wrap: break-word;
}

.task-status {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 4px;
  display: inline-block;
}

.task-status.pending {
  background: #f0f9ff;
  color: #0369a1;
}

.task-status.processing {
  background: #fef3c7;
  color: #d97706;
}

.task-status.completed {
  background: #dcfce7;
  color: #166534;
}

.task-status.failed {
  background: #fee2e2;
  color: #dc2626;
}

.task-actions {
  display: flex;
  gap: 8px;
  margin-top: auto;
}

/* 图生视频分页特定样式 */
.task-pagination-container {
  height: 400px;
  overflow: hidden;
  touch-action: pan-y;
  position: relative;
}

.task-pagination-wrapper {
  height: 100%;
  transition: transform 0.3s ease-out;
  will-change: transform;
}

.task-page {
  height: 100%;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  box-sizing: border-box;
}

.swipe-indicators {
  position: absolute;
  bottom: 15px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 8px;
  z-index: 10;
}

.indicator-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.3);
  cursor: pointer;
  transition: all 0.3s ease;
}

.indicator-dot.active {
  background: #409eff;
  transform: scale(1.2);
}

.indicator-dot:hover {
  background: rgba(64, 158, 255, 0.7);
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding-top: 16px;
  border-top: 1px solid #e2e8f0;
}

/* 图生视频响应式样式 */
@media (max-width: 768px) {
  .task-item {
    flex-direction: column;
    align-items: center;
  }

  .task-image-container {
    margin-right: 0;
    margin-bottom: 16px;
    max-width: 280px;
  }

  .task-image {
    max-height: 280px;
  }

  .task-pagination-container {
    height: 500px;
  }

  .swipe-indicators {
    bottom: 10px;
  }

  .indicator-dot {
    width: 10px;
    height: 10px;
  }

  .navigation-hint {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .hint-text {
    font-size: 11px;
  }
}

/* 图生视频失败图标样式 */
.failure-icon {
  color: #f56c6c;
  cursor: help;
  transition: all 0.3s ease;
  border-radius: 50%;
  background: rgba(245, 108, 108, 0.1);
  padding: 2px;
}

.failure-icon:hover {
  color: #e74c3c;
  background: rgba(245, 108, 108, 0.2);
  transform: scale(1.1);
}

/* 操作列按钮布局 */
.action-buttons {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 6px;
}

/* 操作按钮样式 */
.action-btn {
  font-size: 12px;
  padding: 4px 8px;
  min-width: auto;
}

.action-btn .el-icon {
  margin-right: 4px;
}

/* 表格导入弹窗样式 */
.table-import-container {
  min-height: 200px;
}

.file-select-area {
  margin: 20px 0;
}

.upload-drag-area {
  border: 2px dashed #dcdfe6;
  border-radius: 12px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
  background: #fafbfc;
  min-height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-drag-area:hover {
  border-color: #409eff;
  background: #f5f7fa;
}

.upload-content {
  text-align: center;
  padding: 40px 20px;
}

.upload-icon {
  color: #c0c4cc;
  margin-bottom: 20px;
  transition: color 0.3s ease;
}

.upload-drag-area:hover .upload-icon {
  color: #409eff;
}

.upload-text {
  color: #606266;
}

.upload-text .primary-text {
  font-size: 18px;
  font-weight: 500;
  color: #303133;
  margin: 0 0 12px 0;
}

.upload-text .secondary-text {
  font-size: 14px;
  color: #909399;
  margin: 8px 0;
}

.upload-text .hint-text {
  font-size: 13px;
  color: #c0c4cc;
  margin: 8px 0 20px 0;
}

.template-download {
  margin-top: 16px;
}

.data-preview-area {
  margin-top: 20px;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e4e7ed;
}

.preview-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

.preview-table {
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

/* 图片上传容器样式 */
.image-upload-container {
  width: 100%;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-placeholder {
  width: 100%;
  height: 200px;
  border: 2px dashed #dcdfe6;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #fafbfc;
}

.upload-placeholder:hover {
  border-color: #409eff;
  background: #f5f7fa;
}

.upload-placeholder .el-icon {
  color: #c0c4cc;
  margin-bottom: 12px;
  transition: color 0.3s ease;
}

.upload-placeholder:hover .el-icon {
  color: #409eff;
}

.upload-placeholder p {
  margin: 0;
  color: #606266;
  font-size: 14px;
}

.image-preview-container {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.preview-image {
  max-width: 100%;
  max-height: 200px;
  width: auto;
  height: auto;
  object-fit: contain;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.image-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
}
</style>
