<template>
  <div class="jimeng-page jimeng-digital-human-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-content">
        <div class="title-section">
          <div class="title-icon">
            <el-icon size="32"><Avatar /></el-icon>
          </div>
          <h1 class="page-title">即梦数字人</h1>
        </div>
        <div class="status-section">
          <el-button
            class="btn-create" size="large"
            @click="showUploadDialog = true"
          >
            <el-icon><Plus /></el-icon> 创建任务
          </el-button>
          
          <el-button
            class="btn-import"
            size="large"
            @click="showTableImportDialog = true"
            :disabled="tableImportLoading"
          >
            <el-icon><Upload /></el-icon> 表格导入
          </el-button>
        </div>
      </div>
    </div>

    <!-- 统计概览 -->
    <StatusCountDisplay :stats="stats" />

    <!-- 任务管理 -->
    <div class="task-management">
      <div class="panel-title">
        <h3>任务列表</h3>
        <div class="toolbar-actions">
          <el-select 
            v-model="statusFilter" 
            placeholder="筛选状态"
            clearable
            @change="loadTasks"
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
          <el-button
            class="btn-batch-retry"
            @click="batchRetryFailedTasks"
          >
            <el-icon><RefreshRight /></el-icon> 批量重试
          </el-button>
          <el-button
            class="btn-batch-download"
            @click="batchDownloadVideos"
            :disabled="selectedCompletedTasks.length === 0 || batchDownloadLoading"
          >
            <el-icon><Download /></el-icon> 批量下载 ({{ selectedCompletedTasks.length }})
          </el-button>
          <el-popconfirm
            title="确定要批量删除选中的任务吗？"
            @confirm="batchDeleteSelected"
          >
            <template #reference>
              <el-button
                class="btn-batch-delete"
                :disabled="selectedTasks.length === 0"
              >
                <el-icon><Delete /></el-icon> 批量删除 ({{ selectedTasks.length }})
              </el-button>
            </template>
          </el-popconfirm>
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
          :header-cell-style="{ background: 'var(--bg-light)', color: 'var(--text-primary)', fontWeight: '600' }"
          empty-text="暂无数字人任务"
        >
          <el-table-column 
            type="selection" 
            width="55"
          />
          <el-table-column prop="id" label="ID" width="80" align="center" />
          
          <el-table-column label="图片名称" min-width="200" align="left">
            <template #default="{ row }">
              <div class="file-name-cell">
                <el-icon class="file-icon"><Picture /></el-icon>
                <el-tooltip :content="getImageFileName(row.image_path)" placement="top">
                  <span class="file-name">{{ truncateFileName(getImageFileName(row.image_path), 25) }}</span>
                </el-tooltip>
          </div>
            </template>
          </el-table-column>

          <el-table-column label="音频名称" min-width="200" align="left">
            <template #default="{ row }">
              <div class="file-name-cell">
                <el-icon class="file-icon"><Microphone /></el-icon>
                <el-tooltip :content="getAudioFileName(row.audio_path)" placement="top">
                  <span class="file-name">{{ truncateFileName(getAudioFileName(row.audio_path), 25) }}</span>
                </el-tooltip>
            </div>
            </template>
          </el-table-column>

          <el-table-column label="动作描述" min-width="250" align="left">
            <template #default="{ row }">
              <div class="action-description-cell">
                <el-icon class="action-icon"><EditPen /></el-icon>
                <el-tooltip
                  :content="row.action_description || '无动作描述'"
                  placement="top"
                  :disabled="!row.action_description"
                >
                  <span class="action-description">
                    {{ truncateActionDescription(row.action_description, 35) }}
                  </span>
                </el-tooltip>
              </div>
            </template>
          </el-table-column>

          <el-table-column prop="status" label="状态" width="120" align="center">
            <template #default="{ row }">
              <el-tag 
                :type="getStatusType(row.status)"
                :class="['status-tag', { 'processing-tag': row.status === 1 }]"
              >
                <el-icon v-if="row.status === 1" class="rotating-icon"><Loading /></el-icon>
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="280" fixed="right" align="center">
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
                  v-if="row.status === 2 && row.video_url"
                  class="btn-view" size="small"
                  @click="previewVideo(row.video_url)"
                >
                  <el-icon><View /></el-icon> 查看
                </el-button>
                
                <!-- 下载视频按钮 -->
                <el-button
                  v-if="row.status === 2 && row.video_url"
                  class="btn-download" size="small"
                  @click="downloadVideo(row.video_url)"
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
                  <el-icon><Delete /></el-icon> 删除
                </el-button>
            </div>
            </template>
          </el-table-column>
        </el-table>
          </div>

      <!-- 分页 -->
              <div class="pagination-wrapper">
          <el-pagination
            :current-page="currentPage"
            :page-size="pageSize"
            :page-sizes="[10, 20, 50, 100, 1000]"
            :total="totalTasks"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
            </div>

    <!-- 创建任务对话框 -->
    <el-dialog
      v-model="showUploadDialog"
      title="创建数字人任务"
      width="900px"
      :before-close="resetUploadForm"
      class="create-task-dialog"
    >
      <div class="dialog-content">
        <!-- 左侧预览区域 -->
        <div class="preview-panel">
          <div class="panel-header">
            <h4><el-icon><View /></el-icon> 文件预览</h4>
          </div>

          <!-- 图片预览 -->
          <div class="preview-section">
            <div class="preview-item">
              <div class="preview-header">
                <el-icon><Picture /></el-icon>
                <span>头像图片</span>
                <el-tag v-if="imageFileList.length > 0" type="success" size="small">
                  <el-icon><CircleCheck /></el-icon>
                  已上传
                </el-tag>
            </div>
              
              <div class="preview-content">
                <div v-if="imageFileList.length > 0" class="image-preview-container">
                  <img :src="getPreviewImageUrl(imageFileList[0])" alt="预览图片" />
                  <div class="file-info">
                    <div class="file-name">{{ imageFileList[0].name }}</div>
                    <div class="file-size">{{ formatFileSize(imageFileList[0].size) }}</div>
                  </div>
                </div>
                <div v-else class="empty-preview">
                  <el-icon><Picture /></el-icon>
                  <span>未选择图片</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 音频预览 -->
          <div class="preview-section">
            <div class="preview-item">
              <div class="preview-header">
                <el-icon><Microphone /></el-icon>
                <span>语音文件</span>
                <el-tag v-if="audioFileList.length > 0" type="success" size="small">
                  <el-icon><CircleCheck /></el-icon>
                  已上传
                </el-tag>
            </div>
              
              <div class="preview-content">
                <div v-if="audioFileList.length > 0" class="audio-preview-container">
                  <div class="audio-icon">
                    <el-icon><Microphone /></el-icon>
                  </div>
                  <div class="audio-info">
                    <div class="file-name">{{ audioFileList[0].name }}</div>
                    <div class="file-details">
                      <span class="file-size">{{ formatFileSize(audioFileList[0].size) }}</span>
                      <span v-if="audioInfo.duration" class="duration">{{ audioInfo.duration }}秒</span>
                    </div>
                    <div v-if="audioInfo.duration > 30" class="warning-text">
                      <el-icon><Warning /></el-icon>
                      音频时长超过30秒限制
                    </div>
                  </div>
                </div>
                <div v-else class="empty-preview">
                  <el-icon><Microphone /></el-icon>
                  <span>未选择音频</span>
                </div>
              </div>
            </div>
            </div>
          </div>

        <!-- 右侧上传区域 -->
        <div class="upload-panel">
          <div class="panel-header">
            <h4><el-icon><UploadFilled /></el-icon> 文件上传</h4>
            </div>
          
          <!-- 图片上传 -->
          <div class="upload-section">
            <div class="upload-label">
              <el-icon><Picture /></el-icon>
              头像图片
            </div>
            <el-upload
              ref="imageUploadRef"
              class="upload-area"
              drag
              :auto-upload="false"
              :limit="1"
              accept="image/*"
              :on-change="handleImageChange"
              :on-remove="handleImageRemove"
              :file-list="imageFileList"
              :show-file-list="false"
            >
              <el-icon class="upload-icon"><UploadFilled /></el-icon>
              <div class="upload-text">
                将图片拖到此处，或<em>点击上传</em>
          </div>
              <template #tip>
                <div class="upload-tip">
                  支持 JPG、PNG 格式，文件大小不超过 10MB
                </div>
              </template>
            </el-upload>
        </div>

          <!-- 音频上传 -->
          <div class="upload-section">
            <div class="upload-label">
              <el-icon><Microphone /></el-icon>
              语音文件
            </div>
            <el-upload
              ref="audioUploadRef"
              class="upload-area"
              drag
              :auto-upload="false"
              :limit="1"
              accept="audio/*"
              :on-change="handleAudioChange"
              :on-remove="handleAudioRemove"
              :file-list="audioFileList"
              :show-file-list="false"
            >
              <el-icon class="upload-icon"><UploadFilled /></el-icon>
              <div class="upload-text">
                将音频拖到此处，或<em>点击上传</em>
          </div>
              <template #tip>
                <div class="upload-tip">
                  支持 MP3、WAV、M4A 格式，时长不超过 30 秒
        </div>
              </template>
            </el-upload>
      </div>

          <!-- 动作描述输入 -->
          <div class="upload-section">
            <div class="upload-label">
              <el-icon><EditPen /></el-icon>
              动作描述 <span class="optional-text">(可选)</span>
            </div>
            <el-input
              v-model="actionDescription"
              type="textarea"
              :rows="4"
              maxlength="1000"
              show-word-limit
              placeholder="请输入动作描述，例如：挥手、点头、微笑等动作。最多1000字符。"
              class="action-description-input"
              resize="vertical"
            />
            <div class="upload-tip">
              可选项：用于描述数字人的动作行为，如手势、表情等。留空则使用默认动作。
            </div>
          </div>
    </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button type="info" @click="resetUploadForm">
            取消
          </el-button>
          <el-button
            class="btn-create" size="large"
            @click="createTask"
            :disabled="uploading || audioInfo.duration > 30 || imageFileList.length === 0 || audioFileList.length === 0"
          >
            <el-icon><Plus /></el-icon> {{ uploading ? '创建中...' : '创建任务' }}
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 视频预览对话框 -->
    <el-dialog
      v-model="showPreviewDialog"
      title="视频预览"
      width="800px"
    >
      <div class="video-preview-container">
        <video 
          v-if="previewVideoUrl" 
          :src="previewVideoUrl" 
          controls 
          style="width: 100%; max-height: 400px;"
        >
          您的浏览器不支持视频播放
        </video>
      </div>
    </el-dialog>

    <!-- 表格导入对话框 -->
    <el-dialog
      v-model="showTableImportDialog"
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
                <p class="hint-text">固定格式: 图片路径 | 音频路径 | 动作描述（可选）</p>
                <div class="template-download">
                  <el-button
                    class="btn-download"
                    size="small"
                    @click="downloadTemplate"
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
          <el-button class="cancel-button" @click="showTableImportDialog = false">取消</el-button>
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

<script>
import { ref, reactive, computed, onMounted, onActivated, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  Refresh,
  Delete,
  Picture,
  Microphone,
  RefreshRight,
  DataAnalysis,
  Calendar,
  UploadFilled,
  Avatar,
  VideoPlay,
  Download,
  View,
  Warning,
  CircleCheck,
  CircleCloseFilled,
  Upload,
  Close,
  EditPen
} from '@element-plus/icons-vue'
import { digitalHumanAPI } from '../utils/api.js'
import StatusCountDisplay from '@/components/StatusCountDisplay.vue'
import * as XLSX from 'xlsx'


export default {
  name: 'JimengDigitalHuman',
  components: {
    Plus,
    Refresh,
    Delete,
    Picture,
    Microphone,
    RefreshRight,
    DataAnalysis,
    Calendar,
    UploadFilled,
    Avatar,
    VideoPlay,
    Download,
    View,
    Warning,
    CircleCheck,
    CircleCloseFilled,
    Upload,
    Close,
    EditPen,
    StatusCountDisplay
  },
  setup() {
    // 响应式数据
    const tasks = ref([])
    const loading = ref(false)
    const uploading = ref(false)
    
    // 统计数据 - 使用StatusCountDisplay组件期望的字段名
    const stats = ref({
      total: 0,
      queued: 0,
      processing: 0,
      completed: 0,
      failed: 0
    })
    
    // 对话框状态
    const showUploadDialog = ref(false)
    const showPreviewDialog = ref(false)
    const previewVideoUrl = ref('')
    
    // 分页相关
    const currentPage = ref(1)
    const pageSize = ref(20)
    const totalTasks = ref(0)
    const statusFilter = ref(null)
    const selectedTasks = ref([])
    
    // 上传相关
    const imageUploadRef = ref()
    const audioUploadRef = ref()
    
    // 上传文件列表
    const imageFileList = ref([])
    const audioFileList = ref([])

    // 音频信息
    const audioInfo = reactive({
      duration: 0,
      error: ''
    })

    // 动作描述
    const actionDescription = ref('')

    // 表格导入相关
    const tableImportLoading = ref(false)
    const showTableImportDialog = ref(false)
    const tableFileInput = ref(null)
    const tableData = ref([])
    const tableHeaders = ref([])
    const previewData = ref([])

    
    // 批量下载相关
    const batchDownloadLoading = ref(false)

    // 状态相关方法
    const getStatusType = (status) => {
      const typeMap = {
        0: 'info',     // 排队中
        1: 'warning',  // 生成中
        2: 'success',  // 已完成
        3: 'danger'    // 失败
      }
      return typeMap[status] || 'info'
    }

    const getStatusIcon = (status) => {
      const iconMap = {
        0: Clock,
        1: Loading,
        2: CircleCheckFilled,
        3: CircleCloseFilled
      }
      return iconMap[status] || Clock
    }

    const getStatusText = (status) => {
      const statusMap = {
        0: '排队中',
        1: '生成中',
        2: '已完成',
        3: '失败'
      }
      return statusMap[status] || '未知状态'
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

    // 截断文本函数
    const truncateText = (text, maxLength) => {
      if (!text) return ''
      return text.length > maxLength ? text.substring(0, maxLength) + '...' : text
    }

    // 截断动作描述函数
    const truncateActionDescription = (description, maxLength) => {
      if (!description) return '无'
      return description.length > maxLength ? description.substring(0, maxLength) + '...' : description
    }

    // 获取失败原因tooltip内容
    const getFailureTooltipContent = (row) => {
      const reasonText = getFailureReasonText(row.failure_reason)
      if (row.error_message) {
        return `<div><strong>失败原因:</strong> ${reasonText}</div><div><strong>详细信息:</strong> ${row.error_message}</div>`
      }
      return `<div><strong>失败原因:</strong> ${reasonText}</div>`
    }

    const formatDateTime = (timestamp) => {
      if (!timestamp) return '-'
      const date = new Date(timestamp)
      const year = date.getFullYear()
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')
      const hours = String(date.getHours()).padStart(2, '0')
      const minutes = String(date.getMinutes()).padStart(2, '0')
      return `${year}-${month}-${day} ${hours}:${minutes}`
    }

    const getImageUrl = (path) => {
      if (!path) return ''
      // 如果路径已经是完整URL，直接返回
      if (path.startsWith('http://') || path.startsWith('https://')) {
        return path
      }
      // 构建本地静态文件URL
      const baseUrl = import.meta.env?.VITE_BACKEND_URL || 'http://localhost:8888'
      return `${baseUrl}/static/${path}`
    }

    const getPreviewImageUrl = (file) => {
      if (!file) return ''
      if (file.raw) {
        // 为本地文件创建预览URL
        return URL.createObjectURL(file.raw)
      }
      if (file.url) {
        return file.url
      }
      return ''
    }

    const handleImageError = (e) => {
      e.target.src = 'https://via.placeholder.com/150' // Fallback image
    }

    // 处理图片上传变化
    const handleImageChange = (file) => {
      if (file.status === 'ready') {
        imageFileList.value = [file]
      } else if (file.status === 'success') {
        imageFileList.value = [file]
      } else if (file.status === 'error') {
        ElMessage.error(`图片上传失败: ${file.response?.message || file.error?.message}`)
        imageFileList.value = []
      }
    }

    // 处理图片移除
    const handleImageRemove = (file) => {
      imageFileList.value = []
    }

    // 处理音频上传变化
    const handleAudioChange = (file) => {
      if (file.status === 'ready') {
        audioFileList.value = [file]
        // 检测音频时长
        getAudioDuration(file.raw)
      } else if (file.status === 'success') {
        audioFileList.value = [file]
      } else if (file.status === 'error') {
        ElMessage.error(`音频上传失败: ${file.response?.message || file.error?.message}`)
        audioFileList.value = []
        audioInfo.duration = 0
      }
    }

    // 处理音频移除
    const handleAudioRemove = (file) => {
      audioFileList.value = []
      audioInfo.duration = 0
      audioInfo.error = ''
    }

    // 获取音频时长
    const getAudioDuration = (file) => {
      const audio = new Audio()
      const url = URL.createObjectURL(file)
      
      audio.addEventListener('loadedmetadata', () => {
        const duration = Math.round(audio.duration * 10) / 10 // 保留一位小数
        audioInfo.duration = duration
        
        if (duration > 30) {
          audioInfo.error = '音频时长超过30秒限制'
          ElMessage.warning('音频时长超过30秒，请选择更短的音频文件')
        } else {
          audioInfo.error = ''
        }
        
        URL.revokeObjectURL(url)
      })
      
      audio.addEventListener('error', () => {
        audioInfo.duration = 0
        audioInfo.error = '无法读取音频文件'
        ElMessage.error('无法读取音频文件信息')
        URL.revokeObjectURL(url)
      })
      
      audio.src = url
    }

    // 加载任务列表
    const loadTasks = async () => {
      try {
        loading.value = true
        const params = {
          page: currentPage.value,
          per_page: pageSize.value
        }
        
        if (statusFilter.value !== null) {
          params.status = statusFilter.value
        }
        
        const response = await digitalHumanAPI.getTasks(params)
        
        if (response.data.success) {
          // 适配新的数据结构
          tasks.value = response.data.data.tasks || []
          totalTasks.value = response.data.data.total || 0
        } else {
          ElMessage.error(response.data.message || '获取任务列表失败')
          tasks.value = []
          totalTasks.value = 0
        }
      } catch (error) {
        console.error('获取任务列表失败:', error)
        ElMessage.error('获取任务列表失败')
        tasks.value = []
        totalTasks.value = 0
      } finally {
        loading.value = false
      }
    }

    // 加载统计数据
    const loadStats = async () => {
      try {
        const response = await digitalHumanAPI.getStats()
        if (response.data.success) {
          // 直接使用API返回的数据，StatusCountDisplay组件期望的字段名
          const data = response.data.data
          // 修复：明确使用正确的字段映射，确保排队中的任务数量正确
          stats.value = {
            total: data.total || 0,
            queued: data.queued !== undefined ? data.queued : (data.waiting || 0),  // 优先使用queued字段，否则使用waiting字段
            processing: data.processing || data.in_progress || data.running || 0,  // 尝试使用多个可能的字段名
            completed: data.completed || data.finished || 0,
            failed: data.failed || data.error || 0
          }
        } else {
          console.error('获取统计数据失败:', response.data.message || '未知错误')
          stats.value = {
            total: 0,
            queued: 0,
            processing: 0,
            completed: 0,
            failed: 0
          }
        }
      } catch (error) {
        console.error('获取统计数据失败:', error)
        stats.value = {
          total: 0,
          queued: 0,
          processing: 0,
          completed: 0,
          failed: 0
        }
      }
    }

    // 刷新任务
    const refreshTasks = async () => {
      await loadTasks()
      await loadStats() // 确保统计数据也被加载
    }

    // 创建任务
    const createTask = async () => {
      if (imageFileList.value.length === 0) {
        ElMessage.warning('请选择头像图片')
        return
      }

      if (audioFileList.value.length === 0) {
        ElMessage.warning('请选择语音文件')
        return
      }

      if (audioInfo.duration > 30) {
        ElMessage.warning('音频时长超过30秒，请重新选择')
        return
      }

      uploading.value = true
      try {
        const formData = new FormData()
        formData.append('image', imageFileList.value[0].raw)
        formData.append('audio', audioFileList.value[0].raw)

        // 添加动作描述（如果有）
        if (actionDescription.value.trim()) {
          formData.append('action_description', actionDescription.value.trim())
        }

        const response = await digitalHumanAPI.createTask(formData)
        if (response.data.success) {
          ElMessage.success(response.data.message)
          showUploadDialog.value = false
          resetUploadForm()
          refreshTasks()
          // 刷新统计数据，确保统计面板显示正确
          await loadStats()
        } else {
          ElMessage.error(response.data.message)
        }
      } catch (error) {
        console.error('创建任务失败:', error)
        ElMessage.error('创建任务失败')
      } finally {
        uploading.value = false
      }
    }

    // 重置上传表单
    const resetUploadForm = () => {
      showUploadDialog.value = false
      imageUploadRef.value?.clearFiles()
      audioUploadRef.value?.clearFiles()
      imageFileList.value = []
      audioFileList.value = []
      audioInfo.duration = 0
      audioInfo.error = ''
      actionDescription.value = ''
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
            
            ElMessage.success(`成功解析 ${rows.length} 行数据`)
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
    }

    // 提交表格导入任务
    const submitTableImportTasks = async () => {
      console.log('=== 开始提交表格导入任务 ===')
      console.log('当前tableData.value内容:', tableData.value)
      console.log('当前tableHeaders.value内容:', tableHeaders.value)

      if (tableData.value.length === 0) {
        ElMessage.warning('请先选择并解析表格文件')
        return
      }
      
      if (tableHeaders.value.length < 2) {
        ElMessage.warning('表格至少需要2列：图片路径、音频路径（第3列动作为可选）')
        return
      }
      
      try {
        tableImportLoading.value = true
        
        // 按表头构建任务列表：图片路径、音频路径、动作描述（可选）
        const tasks = tableData.value.map((row, index) => {
          const task = {
            image_path: row['图片路径'] || '',
            audio_path: row['音频路径'] || '',
            action_description: row['动作描述'] ? row['动作描述'].trim() : null // 动作描述为可选
          }
          return task
        }).filter(task => task.image_path.trim() !== '' && task.audio_path.trim() !== '') // 过滤空的图片路径和音频路径
        
        if (tasks.length === 0) {
          ElMessage.warning('没有有效的任务数据')
          return
        }
        
        // 首先尝试使用批量API（需要后端支持）
        try {
          const response = await digitalHumanAPI.batchCreateTasksFromTable(tasks)
          
          if (response.data.success) {
            ElMessage.success(`成功创建 ${tasks.length} 个任务`)
            showTableImportDialog.value = false
            resetTableImportDialog()
            
            // 刷新任务列表
            setTimeout(() => {
              refreshTasks()
            }, 1000)
            return
          } else {
            // 如果批量API不成功，可能是后端未实现，转为逐个创建
            console.log('批量API失败，尝试逐个创建')
          }
        } catch (batchError) {
          console.log('批量API不可用，尝试逐个创建任务')
        }
        
        // 如果批量API失败或不可用，尝试逐个创建任务
        let successCount = 0
        let errorCount = 0
        for (const task of tasks) {
          try {
            // 检查路径类型，URL 或本地路径
            if (task.image_path.startsWith('http') || task.audio_path.startsWith('http')) {
              // 如果是URL，提示用户当前后端可能不支持
              ElMessage.warning('检测到URL路径，当前后端可能不支持直接通过URL创建任务');
              errorCount++
              continue
            } else {
              // 对于本地路径，创建一个FormData对象
              const formData = new FormData()
              formData.append('image_path', task.image_path)
              formData.append('audio_path', task.audio_path)

              // 添加动作描述（如果有）
              if (task.action_description && task.action_description !== 'None') {
                formData.append('action_description', task.action_description)
              }
              const response = await digitalHumanAPI.createTask(formData)
              if (response.data.success) {
                successCount++
              } else {
                errorCount++
              }
            }
          } catch (error) {
            errorCount++
            console.error('创建单个任务失败:', error)
          }
        }
        
        if (successCount > 0) {
          ElMessage.success(`成功创建 ${successCount} 个任务，${errorCount} 个失败`)
          showTableImportDialog.value = false
          resetTableImportDialog()
          
          // 刷新任务列表
          setTimeout(() => {
            refreshTasks()
            loadStats() // 刷新统计数据
          }, 1000)
        } else if (errorCount > 0) {
          ElMessage.error(`任务创建失败，${errorCount} 个任务未能创建。请确认后端已支持表格导入功能。`)
        } else {
          ElMessage.info('没有任务被创建')
        }
      } catch (error) {
        console.error('表格导入失败:', error)
        ElMessage.error('表格导入失败，请确认后端支持相应功能')
      } finally {
        tableImportLoading.value = false
      }
    }

    // 下载表格模板
    const downloadTemplate = () => {
      // 创建CSV数据 - 包含表头
      const headers = ['图片路径', '音频路径', '动作描述']

      // 构建CSV内容 - 只有表头行，添加BOM以支持Excel正确显示中文
      const BOM = '\uFEFF'
      const csvContent = BOM + headers.join(',')
      
      // 创建Blob对象，使用UTF-8编码
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      
      // 创建下载链接
      const link = document.createElement('a')
      const url = URL.createObjectURL(blob)
      link.setAttribute('href', url)
      link.setAttribute('download', '数字人任务导入模板.csv')
      link.style.visibility = 'hidden'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      
      ElMessage.success('模板下载成功')
    }

    // 删除任务
    const deleteTask = async (taskId) => {
      try {
        await ElMessageBox.confirm('确定删除这个任务吗？', '确认删除', {
          type: 'warning'
        })
        
        const response = await digitalHumanAPI.deleteTask(taskId)
        if (response.data.success) {
          ElMessage.success('任务删除成功')
          refreshTasks()
          // 刷新统计数据，确保统计面板显示正确
          await loadStats()
        } else {
          ElMessage.error(response.data.message)
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('删除任务失败:', error)
          ElMessage.error('删除任务失败')
        }
      }
    }

    // 重试任务
    const retryTask = async (taskId) => {
      try {
        const response = await digitalHumanAPI.retryTask(taskId)
        if (response.data.success) {
          ElMessage.success('任务已重新排队')
          refreshTasks()
          // 刷新统计数据，确保统计面板显示正确
          await loadStats()
        } else {
          ElMessage.error(response.data.message)
        }
      } catch (error) {
        console.error('重试任务失败:', error)
        ElMessage.error('重试任务失败')
      }
    }

    // 批量重试
    const batchRetryFailedTasks = async () => {
      try {
        await ElMessageBox.confirm('确定重试所有失败的任务吗？', '确认重试', {
          type: 'warning'
        })
        
        const response = await digitalHumanAPI.batchRetryTasks()
        if (response.data.success) {
          ElMessage.success(response.data.message)
          refreshTasks()
          // 刷新统计数据，确保统计面板显示正确
          await loadStats()
        } else {
          ElMessage.error(response.data.message)
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('批量重试失败:', error)
          ElMessage.error('批量重试失败')
        }
      }
    }

    // 计算已完成的任务
    const selectedCompletedTasks = computed(() => {
      return selectedTasks.value.filter(task => task.status === 2 && task.video_url)
    })

    // 批量下载视频
    const batchDownloadVideos = async () => {
      if (selectedCompletedTasks.value.length === 0) {
        ElMessage.warning('请先选择已完成的任务')
        return
      }
      
      try {
        batchDownloadLoading.value = true
        
        // 调用后端API批量下载
        const taskIds = selectedCompletedTasks.value.map(task => task.id)
        const response = await digitalHumanAPI.batchDownload(taskIds)
        
        if (response.data.success) {
          ElMessage.success(response.data.message || '开始批量下载，请选择保存文件夹')
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

    // 批量删除选中任务
    const batchDeleteSelected = async () => {
      if (selectedTasks.value.length === 0) {
        ElMessage.warning('请选择要删除的任务')
        return
      }

      try {
        await ElMessageBox.confirm(`确定删除选中的 ${selectedTasks.value.length} 个任务吗？`, '确认删除', {
          type: 'warning'
        })
        
        const taskIds = selectedTasks.value.map(task => task.id)
        const response = await digitalHumanAPI.batchDeleteTasks(taskIds)
        if (response.data.success) {
          ElMessage.success(response.data.message)
          selectedTasks.value = []
          refreshTasks()
          // 刷新统计数据，确保统计面板显示正确
          await loadStats()
        } else {
          ElMessage.error(response.data.message)
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('批量删除失败:', error)
          ElMessage.error('批量删除失败')
        }
      }
    }



    // 预览视频
    const previewVideo = (videoUrl) => {
      previewVideoUrl.value = videoUrl
      showPreviewDialog.value = true
    }

    // 下载视频
    const downloadVideo = async (videoUrl) => {
      if (!videoUrl) {
        ElMessage.warning('没有可下载的视频')
        return
      }

      try {
        // 调用后端API来触发文件夹选择器并下载
        const response = await digitalHumanAPI.downloadSingleVideo({
          video_url: videoUrl,
          filename: `digital_human_video_${Date.now()}.mp4`
        })

        if (response.data.success) {
          ElMessage.success('请在桌面选择下载文件夹')
        } else {
          // 如果后端调用失败，使用前端下载方式
          const link = document.createElement('a')
          link.href = videoUrl
          link.download = `digital_human_video_${Date.now()}.mp4`
          link.target = '_blank'
          document.body.appendChild(link)
          link.click()
          document.body.removeChild(link)
          ElMessage.success('开始下载视频')
        }
      } catch (error) {
        console.error('下载视频失败:', error)
        // 降级到前端下载方式
        try {
          const link = document.createElement('a')
          link.href = videoUrl
          link.download = `digital_human_video_${Date.now()}.mp4`
          link.target = '_blank'
          document.body.appendChild(link)
          link.click()
          document.body.removeChild(link)
          ElMessage.success('开始下载视频')
        } catch (downloadError) {
          console.error('下载视频失败:', downloadError)
          ElMessage.error('下载视频失败')
        }
      }
    }

    // 表格选择变化
    const handleSelectionChange = (selection) => {
      selectedTasks.value = selection
    }

    // 分页大小变化
    const handleSizeChange = (newSize) => {
      pageSize.value = newSize
      currentPage.value = 1
      loadTasks()
    }

    // 当前页变化
    const handleCurrentChange = (newPage) => {
      currentPage.value = newPage
      loadTasks()
    }

    // 格式化文件大小
    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 Bytes';
      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // 截断文件名
    const truncateFileName = (name, maxLength) => {
      if (name.length <= maxLength) {
        return name;
      }
      const truncated = name.substring(0, maxLength);
      return `${truncated}...`;
    }

    // 获取图片文件名
    const getImageFileName = (path) => {
      if (!path) return '未选择图片';
      const lastSlashIndex = path.lastIndexOf('/');
      return path.substring(lastSlashIndex + 1);
    }

    // 获取音频文件名
    const getAudioFileName = (path) => {
      if (!path) return '未选择音频';
      const lastSlashIndex = path.lastIndexOf('/');
      return path.substring(lastSlashIndex + 1);
    }

    // 获取自定义操作按钮
    const getCustomActions = (row) => {
      const actions = [];
      
      // 下载按钮（当任务完成且有视频URL时）
      if (row.status === 2 && row.video_url) {
        actions.push({
          key: 'download',
          text: '下载',
          icon: 'el-icon-download',
          type: 'success',
          tooltip: '下载视频'
        });
      }
      
      return actions;
    }

    // 处理自定义操作
    const handleCustomAction = (row, actionKey) => {
      switch (actionKey) {
        case 'download':
          downloadVideo(row.video_url);
          break;
        default:
          console.warn('未知的操作:', actionKey);
      }
    }

    // 定时刷新任务和统计数据
    let refreshInterval = null
    
    const startAutoRefresh = () => {
      // 每10秒自动刷新一次统计数据和任务列表，确保排队中的数量得到实时更新
      refreshInterval = setInterval(() => {
        loadStats()
        // 同时刷新任务列表以确保任务状态同步
        loadTasks()
      }, 10000) // 10秒刷新一次
    }
    
    const stopAutoRefresh = () => {
      if (refreshInterval) {
        clearInterval(refreshInterval)
        refreshInterval = null
      }
    }

    // 生命周期
    onMounted(() => {
      refreshTasks()
      startAutoRefresh() // 开始自动刷新
    })

    onActivated(() => {
      refreshTasks()
      startAutoRefresh() // 开始自动刷新
    })
    
    // 组件卸载时停止定时器
    onBeforeUnmount(() => {
      stopAutoRefresh()
    })

    return {
      tasks,
      loading,
      uploading,
      stats,
      showUploadDialog,
      showPreviewDialog,
      previewVideoUrl,
      currentPage,
      pageSize,
      totalTasks,
      statusFilter,
      selectedTasks,
      imageUploadRef,
      audioUploadRef,
      imageFileList,
      audioFileList,
      audioInfo,
      actionDescription,
      batchDownloadLoading,
      selectedCompletedTasks,
      getStatusType,
      getStatusIcon,
      getStatusText,
      getFailureReasonText,
      getFailureTooltipContent,
      truncateText,
      truncateActionDescription,
      formatDateTime,
      getImageUrl,
      getPreviewImageUrl,
      handleImageError,
      handleImageChange,
      handleImageRemove,
      handleAudioChange,
      handleAudioRemove,
      getAudioDuration,
      loadTasks,
      loadStats,
      refreshTasks,
      createTask,
      resetUploadForm,
      deleteTask,
      retryTask,
      batchRetryFailedTasks,
      batchDownloadVideos,
      batchDeleteSelected,
      previewVideo,
      downloadVideo,
      handleSelectionChange,
      handleSizeChange,
      handleCurrentChange,
      formatFileSize,
      truncateFileName,
      getImageFileName,
      getAudioFileName,
      getCustomActions,
      handleCustomAction,
      // 表格导入相关
      tableImportLoading,
      showTableImportDialog,
      tableFileInput,
      tableData,
      tableHeaders,
      previewData,
      triggerTableFileInput,
      handleTableFileSelect,
      handleTableFileDrop,
      parseTableFile,
      parseCSVFile,
      parseExcelFile,
      resetTableImportDialog,
      submitTableImportTasks,
      downloadTemplate
    }
  }
}
</script>

<style scoped>
@import '../styles/jimeng-common.css';

/* 页面特定样式 */



.status-filter .el-select {
  width: 150px;
}

.refresh-btn {
  background-color: #E6A23C;
  border-color: #E6A23C;
}

.refresh-btn:hover {
  background-color: #ebb563;
  border-color: #ebb563;
}

.batch-retry-btn {
  background-color: #E6A23C;
  border-color: #E6A23C;
}

.batch-retry-btn:hover {
  background-color: #ebb563;
  border-color: #ebb563;
}



.batch-delete-btn {
  background-color: #F56C6C;
  border-color: #F56C6C;
}

.batch-delete-btn:hover {
  background-color: #f78989;
  border-color: #f78989;
}

.task-table-container {
  overflow-x: auto;
}

.modern-table {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #e4e7ed;
}

.modern-table :deep(.el-table__header-wrapper th) {
  background-color: #f8fafc;
  color: #374151;
  font-weight: 600;
}

.modern-table :deep(.el-table__header-wrapper th:first-child) {
  border-top-left-radius: 12px;
}

.modern-table :deep(.el-table__header-wrapper th:last-child) {
  border-top-right-radius: 12px;
}

.modern-table :deep(.el-table__body-wrapper tr:last-child td:first-child) {
  border-bottom-left-radius: 12px;
}

.modern-table :deep(.el-table__body-wrapper tr:last-child td:last-child) {
  border-bottom-right-radius: 12px;
}

.file-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #606266;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-icon {
  color: #409eff;
  font-size: 16px;
}

.file-name {
  cursor: pointer;
  color: #606266;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.action-description-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-icon {
  color: #67c23a;
  font-size: 16px;
  flex-shrink: 0;
}

.action-description {
  color: #606266;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-tag {
  font-size: 12px;
  font-weight: 500;
  border-radius: 6px;
  padding: 4px 8px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.status-tag.processing-tag {
  background-color: #e1f3d8;
  color: #67c23a;
  border-color: #e1f3d8;
}

.rotating-icon {
  animation: rotate 2s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.action-buttons {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.action-buttons .el-button {
  margin: 0;
  padding: 6px 12px;
  font-size: 12px;
  border-radius: var(--radius-sm);
}

/* 分页样式 */
.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding-top: 16px;
  border-top: 1px solid #e2e8f0;
}

/* 对话框样式 */
.create-task-dialog {
  border-radius: 12px;
}

.create-task-dialog :deep(.el-dialog__header) {
  padding: 20px 24px 16px;
  border-bottom: 1px solid var(--border-light);
  background: var(--bg-light);
}

.create-task-dialog :deep(.el-dialog__title) {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.create-task-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.dialog-content {
  display: flex;
  gap: 20px;
  width: 100%;
  padding: 24px;
}

.preview-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #303133;
  font-weight: 600;
  margin-bottom: 12px;
}

.preview-section {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 15px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.preview-item {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.preview-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #303133;
  font-weight: 600;
  width: 100%;
  justify-content: space-between;
}

.preview-header .el-tag {
  margin-left: auto;
}

.preview-content {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.image-preview-container {
  position: relative;
  width: 150px;
  height: 150px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e4e7ed;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #f5f7fa;
}

.image-preview-container img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-preview-container .file-info {
  position: absolute;
  bottom: 0;
  left: 0;
  background: rgba(0, 0, 0, 0.5);
  color: white;
  padding: 4px 8px;
  border-radius: 0 0 8px 8px;
  font-size: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.empty-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: #909399;
  font-size: 14px;
}

.empty-preview .el-icon {
  font-size: 36px;
}

.audio-preview-container {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
}

.audio-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #409eff;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 20px;
}

.audio-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.audio-info .file-name {
  font-weight: 600;
  color: #303133;
}

.audio-info .file-details {
  font-size: 12px;
  color: #909399;
  display: flex;
  gap: 8px;
}

.audio-info .duration {
  color: #409eff;
  font-weight: 500;
}

.audio-info .warning-text {
  color: #f56c6c;
  font-weight: bold;
  display: flex;
  align-items: center;
  gap: 4px;
}

.upload-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.upload-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.upload-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #303133;
  font-weight: 600;
}

.upload-area {
  width: 100%;
}

.upload-area .el-upload {
  width: 100%;
}

.upload-area .el-upload-dragger {
  width: 100%;
  height: 120px;
}

.upload-area .el-upload-dragger .el-icon {
  font-size: 40px;
  color: #c0c4cc;
}

.upload-area .el-upload-dragger .el-upload__text {
  font-size: 14px;
  color: #606266;
}

.upload-area .el-upload-dragger .el-upload__tip {
  font-size: 12px;
  color: #909399;
}

.upload-area .el-upload-list {
  display: none;
}

.upload-icon {
  font-size: 40px;
  color: #c0c4cc;
}

.upload-text {
  font-size: 14px;
  color: #606266;
}

.upload-tip {
  font-size: 12px;
  color: #909399;
}

.optional-text {
  font-size: 12px;
  color: #909399;
  font-weight: normal;
  margin-left: 4px;
}

.action-description-input {
  width: 100%;
}

.action-description-input :deep(.el-textarea__inner) {
  border-radius: 8px;
  border: 1px solid #dcdfe6;
  transition: all 0.3s ease;
  font-size: 14px;
  line-height: 1.5;
}

.action-description-input :deep(.el-textarea__inner):focus {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

.action-description-input :deep(.el-input__count) {
  background: rgba(255, 255, 255, 0.9);
  border-radius: 4px;
  padding: 0 8px;
  font-size: 12px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #e4e7ed;
  background: #fafafa;
}

.dialog-footer .el-button {
  background-color: #f8f9fa;
  border-color: #e4e7ed;
  color: #606266;
}

.dialog-footer .el-button:hover {
  background-color: #f8f9fa;
  border-color: #e4e7ed;
  color: #409EFF;
}

.dialog-footer .el-button--primary {
  background-color: #409EFF;
  border-color: #409EFF;
}

.dialog-footer .el-button--primary:hover {
  background-color: #66b1ff;
  border-color: #66b1ff;
}

.video-preview-container {
  display: flex;
  justify-content: center;
  align-items: center;
  background: #f5f7fa;
  border-radius: 8px;
  padding: 20px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .jimeng-digital-human-page {
    padding: 16px;
  }
  
  .header-content {
    flex-direction: column;
    text-align: center;
    gap: 16px;
    padding: 20px 24px;
  }
  
  .page-title {
    font-size: 28px;
  }
  

  
  .task-management {
    padding: 24px;
  }
  
  .toolbar-actions {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }
  
  .status-filter .el-select {
    width: 100%;
  }
}

@media (max-width: 480px) {
  .page-title {
    font-size: 24px;
  }
  

}

/* 失败原因图标样式 */
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

.action-buttons {
  display: flex;
  flex-direction: row;
  gap: 6px;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
}

/* 按钮样式已移至全局样式 */

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
</style>