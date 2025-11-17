<template>
  <div class="jimeng-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-content">
        <div class="title-section">
          <div class="title-icon">
            <el-icon size="32"><VideoCamera /></el-icon>
          </div>
          <h1 class="page-title">即梦文生视频</h1>
        </div>
        <div class="status-section">
          <el-button
            class="btn-create" size="large"
            @click="showAddTaskDialog = true"
          >
            <el-icon><Plus /></el-icon> 创建任务
          </el-button>

          <el-button
            class="btn-batch-add" size="large"
            @click="showBatchAddDialog = true"
          >
            <el-icon><FolderAdd /></el-icon> 批量添加
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
            <el-icon><Download /></el-icon> 批量下载
          </el-button>

          <el-button
            class="btn-batch-delete"
            @click="batchDeleteTasks"
            :disabled="selectedTasks.length === 0"
          >
            <el-icon><Delete /></el-icon> 批量删除
          </el-button>
            
            <el-button 
              v-for="action in customActions"
              :key="action.key"
              :type="action.type || 'default'"
              :disabled="selectedCompletedTasks.length === 0 && selectedTasks.length === 0"
              @click="handleCustomAction(action.key)"
            >
              <template #icon v-if="action.icon">
                <component :is="action.icon" />
              </template>
              {{ action.text }}
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
          
          <el-table-column label="提示词" min-width="250">
            <template #default="{ row }">
              <div class="prompt-cell">
                <el-tooltip :content="row.prompt || ''" placement="top">
                  <span class="prompt-text">{{ truncateText(row.prompt || '', 80) }}</span>
                </el-tooltip>
              </div>
            </template>
          </el-table-column>

          <el-table-column prop="model" label="模型" width="140" align="center">
            <template #default="{ row }">
              <el-tag class="model-tag">{{ row.model || '-' }}</el-tag>
            </template>
          </el-table-column>

          <el-table-column prop="ratio" label="比例" width="100" align="center">
            <template #default="{ row }">
              <el-tag type="info" class="ratio-tag">{{ row.ratio || '1:1' }}</el-tag>
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

          <el-table-column label="操作" width="250" fixed="right" align="center">
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
                    <InfoFilled />
                  </el-icon>
                </el-tooltip>
                
                <!-- 重试按钮 -->
                <el-button 
                  v-if="row.status === 3"
                  class="btn-retry" size="small"
                  @click="retryTask(row)"
                >
                  <span >
                    <RefreshRight />
                  </span>
                  重试
                </el-button>
                
                <!-- 查看按钮 -->
                <el-button 
                  v-if="row.status === 2 && row.video_url"
                  class="btn-view" size="small"
                  @click="viewResult(row)"
                >
                  <span >
                    <View />
                  </span>
                  查看
                </el-button>
                
                <!-- 下载按钮 -->
                <el-button 
                  v-if="row.status === 2 && row.video_url"
                  class="btn-download" size="small"
                  @click="downloadSingleTask(row)"
                >
                  <span >
                    <Download />
                  </span>
                  下载
                </el-button>
                
                <!-- 删除按钮 -->
                <el-button 
                  class="btn-delete" size="small"
                  :disabled="row.status === 1"
                  @click="deleteTask(row.id)"
                >
                  <span >
                    <Delete />
                  </span>
                  删除
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-wrapper">
          <el-pagination
            :current-page="currentPage"
            :page-size="pageSize"
            :page-sizes="[10, 20, 50, 100, 1000]"
            :total="pagination.total"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
    </div>

    <!-- 添加任务对话框 -->
    <el-dialog
      v-model="showAddTaskDialog"
      title="创建文生视频任务"
      width="600px"
      class="modern-dialog"
    >
      <el-form 
        :model="taskForm" 
        :rules="taskRules" 
        ref="taskFormRef" 
        label-width="120px"
        class="task-form"
      >
          <el-form-item label="提示词" prop="prompt">
            <el-input
            v-model="taskForm.prompt"
              type="textarea"
              :rows="4"
            placeholder="请输入视频描述提示词..."
            maxlength="1000"
              show-word-limit
            />
          </el-form-item>
          
        <el-form-item label="模型选择" prop="model">
          <el-select v-model="taskForm.model" placeholder="选择生成模型" class="full-width">
            <el-option label="Video 3.0" value="Video 3.0" />
            <el-option label="Video 3.0 Pro" value="Video 3.0 Pro" />
            <el-option label="Video S2.0 Pro" value="Video S2.0 Pro" />
                </el-select>
              </el-form-item>

        <el-form-item label="视频时长" prop="second">
          <el-select v-model="taskForm.second" placeholder="选择视频时长" class="full-width">
            <el-option label="5秒" :value="5" />
            <el-option v-if="taskForm.model === 'Video 3.0' || taskForm.model === 'Video 3.0 Pro'" label="10秒" :value="10" />
          </el-select>
        </el-form-item>

        <el-form-item label="视频比例" prop="ratio">
          <el-select v-model="taskForm.ratio" placeholder="选择视频比例" class="full-width">
            <el-option label="21:9 超宽屏" value="21:9" />
            <el-option label="16:9 横屏" value="16:9" />
            <el-option label="4:3 传统" value="4:3" />
            <el-option label="1:1 正方形" value="1:1" />
            <el-option label="3:4 肖像" value="3:4" />
            <el-option label="9:16 竖屏" value="9:16" />
          </el-select>
        </el-form-item>

        <el-form-item label="视频分辨率" prop="resolution">
          <el-select v-model="taskForm.resolution" placeholder="选择视频分辨率" class="full-width">
            <el-option label="720P (1280x720)" value="720p" />
            <el-option v-if="taskForm.model === 'Video 3.0'" label="1080P (1920x1080)" value="1080p" />
          </el-select>
        </el-form-item>

        </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showAddTaskDialog = false" class="cancel-button">
            取消
          </el-button>
          <el-button
            class="btn-create"
            @click="addTask"
            :loading="addTaskLoading"
            :disabled="!taskForm.prompt"
          >
            <template #icon>
              <Plus />
            </template>
            创建任务
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 批量添加对话框 -->
    <el-dialog
      v-model="showBatchAddDialog"
      title="批量添加任务"
      width="700px"
      class="modern-dialog"
    >
      <div class="batch-add-content">
        <div class="tips-section">
          <el-alert
            title="批量添加说明"
            type="info"
            :closable="false"
            show-icon
          >
            <template #default>
              <p>每行一个提示词，将自动创建多个任务</p>
              <p>支持最多10000个任务同时创建，支持最大500000字符</p>
            </template>
          </el-alert>
        </div>

        <el-form :model="batchForm" ref="batchFormRef" label-width="120px">
          <el-form-item label="提示词列表" prop="prompts">
          <el-input
              v-model="batchForm.prompts"
            type="textarea"
              :rows="10"
              placeholder="请输入提示词，每行一个..."
              maxlength="500000"
            show-word-limit
            />
          </el-form-item>

          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="模型" prop="model">
                <el-select v-model="batchForm.model" class="full-width">
                  <el-option label="Video 3.0" value="Video 3.0" />
                  <el-option label="Video 3.0 Pro" value="Video 3.0 Pro" />
                  <el-option label="Video S2.0 Pro" value="Video S2.0 Pro" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="时长" prop="second">
                <el-select v-model="batchForm.second" class="full-width">
                  <el-option label="5秒" :value="5" />
                  <el-option v-if="batchForm.model === 'Video 3.0' || batchForm.model === 'Video 3.0 Pro'" label="10秒" :value="10" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="比例" prop="ratio">
                <el-select v-model="batchForm.ratio" class="full-width">
                  <el-option label="21:9" value="21:9" />
                  <el-option label="16:9" value="16:9" />
                  <el-option label="4:3" value="4:3" />
                  <el-option label="1:1" value="1:1" />
                  <el-option label="3:4" value="3:4" />
                  <el-option label="9:16" value="9:16" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="分辨率" prop="resolution">
                <el-select v-model="batchForm.resolution" class="full-width">
                  <el-option label="720P" value="720p" />
                  <el-option v-if="batchForm.model === 'Video 3.0'" label="1080P" value="1080p" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showBatchAddDialog = false" class="cancel-button">
            取消
          </el-button>
          <el-button
            class="btn-batch-create"
            @click="batchAddTasks"
            :loading="batchAddLoading"
            :disabled="!batchForm.prompts"
          >
            <template #icon>
              <Document />
            </template>
            批量创建
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 查看结果对话框 -->
    <el-dialog
      v-model="showResultDialog"
      :title="`任务 #${currentTask?.id} 生成结果`"
      width="800px"
      class="modern-dialog result-dialog"
    >
      <div class="result-content" v-if="currentTask">
        <div class="result-info">
          <h4>任务信息</h4>
          <p><strong>提示词：</strong>{{ currentTask.prompt || '-' }}</p>
          <p><strong>模型：</strong>{{ currentTask.model || '-' }}</p>
          <p><strong>比例：</strong>{{ currentTask.ratio || '1:1' }}</p>
          <p><strong>时长：</strong>{{ currentTask.second || 5 }}秒</p>
          <p><strong>分辨率：</strong>{{ currentTask.resolution || '720p' }}</p>
        </div>
        
        <div class="result-video" v-if="currentTask.video_url">
          <h4>生成视频</h4>
          <video :src="currentTask.video_url" controls class="result-video-preview" />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, onActivated, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  VideoCamera,
  Plus,
  WarningFilled,
  Refresh,
  Delete,
  RefreshRight,
  View,
  InfoFilled,
  Picture,
  Download,
  FolderAdd,
  Document
} from '@element-plus/icons-vue'
import { text2videoAPI } from '../utils/api'
import StatusCountDisplay from '@/components/StatusCountDisplay.vue'

export default {
  name: 'JimengText2Video',
  components: {
    VideoCamera,
    Plus,
    WarningFilled,
    Refresh,
    Delete,
    RefreshRight,
    View,
    InfoFilled,
    Picture,
    Download,
    FolderAdd,
    Document,
    StatusCountDisplay
  },
  setup() {
    // 响应式数据
    const loading = ref(false)
    const tasks = ref([])
    const selectedTasks = ref([])
    const statusFilter = ref(null)
    const currentPage = ref(1)
    const pageSize = ref(20)
    const pagination = ref({
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 0
    })

    // 统计数据
    const stats = ref({
      total: 0,
      queued: 0,
      processing: 0,
      completed: 0,
      failed: 0
    })

    // 对话框状态
    const showAddTaskDialog = ref(false)
    const showBatchAddDialog = ref(false)
    const showResultDialog = ref(false)
    const addTaskLoading = ref(false)
    const batchAddLoading = ref(false)
    const batchDownloadLoading = ref(false)

    // 表单数据
    const taskForm = reactive({
      prompt: '',
      model: 'Video 3.0',
      second: 5,
      ratio: '1:1',
      resolution: '720p'
    })

    const batchForm = reactive({
      prompts: '',
      model: 'Video 3.0',
      second: 5,
      ratio: '1:1',
      resolution: '720p'
    })

    const currentTask = ref(null)

    // 监听模型变化，更新秒数选项
    watch(() => taskForm.model, (newModel) => {
      if (newModel !== 'Video 3.0' && newModel !== 'Video 3.0 Pro' && taskForm.second !== 5) {
        taskForm.second = 5
      }
    })

    watch(() => batchForm.model, (newModel) => {
      if (newModel !== 'Video 3.0' && newModel !== 'Video 3.0 Pro' && batchForm.second !== 5) {
        batchForm.second = 5
      }
    })

    // 表单验证规则
    const taskRules = computed(() => {
      const rules = {
        prompt: [
          { required: true, message: '请输入提示词', trigger: 'blur' },
          { min: 5, message: '提示词至少5个字符', trigger: 'blur' }
        ],
        model: [
          { required: true, message: '请选择模型', trigger: 'change' }
        ],
        ratio: [
          { required: true, message: '请选择视频比例', trigger: 'change' }
        ],
        second: [
          { required: true, message: '请选择视频时长', trigger: 'change' }
        ],
        resolution: [
          { required: true, message: '请选择分辨率', trigger: 'change' }
        ]
      }
      
      return rules
    })

    const taskFormRef = ref()
    const batchFormRef = ref()

    // 获取任务列表
    const fetchTasks = async () => {
      loading.value = true
      try {
        const params = {
          page: currentPage.value,
          page_size: pageSize.value
        }
        if (statusFilter.value !== null) {
          params.status = statusFilter.value
        }

        const response = await text2videoAPI.getTasks(params)
        if (response.data.success) {
          tasks.value = response.data.data
          pagination.value = response.data.pagination
        } else {
          ElMessage.error(response.data.message)
        }
      } catch (error) {
        console.error('获取任务失败:', error)
        ElMessage.error('获取任务失败，请检查网络连接')
      } finally {
        loading.value = false
      }
    }

    // 获取统计信息
    const fetchStats = async () => {
      try {
        const response = await text2videoAPI.getStats()
        console.log('文生视频统计API响应:', response) // 调试日志
        if (response && response.data && response.data.success) {
          const data = response.data.data
          console.log('文生视频统计API返回数据:', data) // 调试日志
          // 确保API返回的数据正确映射到stats对象的字段
          stats.value.total = typeof data.total !== 'undefined' ? data.total : (data.total_tasks || 0)
          stats.value.queued = typeof data.queued !== 'undefined' ? data.queued : (data.today || data.pending_tasks || 0)
          stats.value.processing = typeof data.processing !== 'undefined' ? data.processing : (data.in_progress || data.processing_tasks || 0)
          stats.value.completed = typeof data.completed !== 'undefined' ? data.completed : (data.completed_tasks || 0)
          stats.value.failed = typeof data.failed !== 'undefined' ? data.failed : (data.failed_tasks || 0)
          console.log('设置的stats值:', stats.value) // 调试日志
        } else {
          console.error('获取统计信息失败:', response?.data?.message || '未知错误')
          // 如果API响应失败，设置默认值
          stats.value = {
            total: 0,
            queued: 0,
            processing: 0,
            completed: 0,
            failed: 0
          }
        }
      } catch (error) {
        console.error('获取统计信息失败:', error)
        // 如果出现异常，设置默认值
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
      await fetchStats() // 确保统计数据先加载
      await fetchTasks()
    }

    // 添加单个任务
    const addTask = async () => {
      try {
        await taskFormRef.value.validate()
        addTaskLoading.value = true

        // 准备任务数据
        const taskData = { ...taskForm }

        const response = await text2videoAPI.createTask(taskData)
        if (response.data.success) {
          ElMessage.success('任务创建成功')
          showAddTaskDialog.value = false
          resetTaskForm()
          refreshTasks()
        } else {
          ElMessage.error(response.data.message)
        }
      } catch (error) {
        console.error('创建任务失败:', error)
        ElMessage.error('创建任务失败')
      } finally {
        addTaskLoading.value = false
      }
    }

    // 批量添加任务
    const batchAddTasks = async () => {
      if (!batchForm.prompts.trim()) {
        ElMessage.warning('请输入提示词列表')
        return
      }

      batchAddLoading.value = true
      const prompts = batchForm.prompts.trim().split('\n').filter(line => line.trim())
      let successCount = 0
      let errorCount = 0

      try {
        for (const prompt of prompts) {
          const taskData = {
            prompt: prompt.trim(),
            model: batchForm.model,
            ratio: batchForm.ratio,
            second: batchForm.second,
            resolution: batchForm.resolution
          }

          try {
            const response = await text2videoAPI.createTask(taskData)
            if (response.data.success) {
              successCount++
            } else {
              errorCount++
            }
          } catch (error) {
            errorCount++
          }
        }

        ElMessage.success(`批量创建完成：成功 ${successCount} 个，失败 ${errorCount} 个`)
        if (successCount > 0) {
          showBatchAddDialog.value = false
          resetBatchForm()
          refreshTasks()
        }
      } catch (error) {
        console.error('批量创建失败:', error)
        ElMessage.error('批量创建失败')
      } finally {
        batchAddLoading.value = false
      }
    }

    // 删除任务
    const deleteTask = async (taskId) => {
      try {
        const response = await text2videoAPI.deleteTask(taskId)
        if (response.data.success) {
          ElMessage.success(response.data.message)
          refreshTasks()
        } else {
          ElMessage.error(response.data.message)
        }
      } catch (error) {
        console.error('删除任务失败:', error)
        ElMessage.error('删除任务失败')
      }
    }

    // 批量删除任务
    const batchDeleteTasks = async () => {
      if (selectedTasks.value.length === 0) {
        ElMessage.warning('请选择要删除的任务')
        return
      }

      try {
        const taskIds = selectedTasks.value.map(task => task.id)
        const response = await text2videoAPI.batchDeleteTasks(taskIds)
        if (response.data.success) {
          ElMessage.success(response.data.message)
          selectedTasks.value = []
          refreshTasks()
        } else {
          ElMessage.error(response.data.message)
        }
      } catch (error) {
        console.error('批量删除失败:', error)
        ElMessage.error('批量删除失败')
      }
    }

    // 重试任务
    const retryTask = async (task) => {
      try {
        const response = await text2videoAPI.retryTask(task.id)
        if (response.data.success) {
          ElMessage.success(response.data.message || '任务已重新加入队列')
          refreshTasks()
        } else {
          ElMessage.error(response.data.message)
        }
      } catch (error) {
        console.error('重试任务失败:', error)
        ElMessage.error(error.response?.data?.message || '重试任务失败')
      }
    }

    // 查看结果
    const viewResult = (task) => {
      currentTask.value = task
      showResultDialog.value = true
    }

    // 处理选择变化
    const handleSelectionChange = (selection) => {
      selectedTasks.value = selection
    }

    // 判断任务是否可选择（生成中的任务不可选择）
    const isTaskSelectable = (row) => {
      return row.status !== 1
    }

    // 计算已完成且有视频的选中任务
    const selectedCompletedTasks = computed(() => {
      if (!selectedTasks.value || !Array.isArray(selectedTasks.value)) {
        return []
      }
      return selectedTasks.value.filter(task => 
        task && task.status === 2 && task.video_url && task.video_url.trim() !== ''
      )
    })

    // 状态筛选
    const handleStatusFilter = () => {
      currentPage.value = 1
      fetchTasks()
    }

    // 分页处理
    const handleCurrentChange = (page) => {
      currentPage.value = page
      fetchTasks()
    }

    const handleSizeChange = (size) => {
      pageSize.value = size
      currentPage.value = 1
      fetchTasks()
    }

    // 重置添加表单
    const resetTaskForm = () => {
      Object.assign(taskForm, {
        prompt: '',
        model: 'Video 3.0',
        second: 5,
        ratio: '1:1',
        resolution: '720p'
      })
      if (taskFormRef.value) {
        taskFormRef.value.resetFields()
      }
    }

    // 重置批量添加表单
    const resetBatchForm = () => {
      Object.assign(batchForm, {
        prompts: '',
        model: 'Video 3.0',
        second: 5,
        ratio: '1:1',
        resolution: '720p'
      })
      if (batchFormRef.value) {
        batchFormRef.value.resetFields()
      }
    }

    // 工具函数
    const truncateText = (text, length) => {
      if (!text) return ''
      return text.length > length ? text.substring(0, length) + '...' : text
    }

    const getStatusType = (status) => {
      const statusTypes = {
        0: 'warning',  // 排队中
        1: 'primary',  // 生成中
        2: 'success',  // 已完成
        3: 'danger'    // 失败
      }
      return statusTypes[status] || 'info'
    }



    // 批量下载视频
    const batchDownloadVideos = async () => {
      if (selectedCompletedTasks.value.length === 0) {
        ElMessage.warning('请选择已完成的任务')
        return
      }

      batchDownloadLoading.value = true
      try {
        const taskIds = selectedCompletedTasks.value.map(task => task.id)
        
        ElMessage.info(`准备下载 ${selectedCompletedTasks.value.length} 个任务的视频，请在弹出的对话框中选择文件夹...`)
        
        const response = await text2videoAPI.batchDownload(taskIds)
        
        if (response.data.success) {
          ElMessage.success(response.data.message)
        } else {
          ElMessage.error(response.data.message)
        }
      } catch (error) {
        console.error('批量下载失败:', error)
        ElMessage.error(error.response?.data?.message || '批量下载失败')
      } finally {
        batchDownloadLoading.value = false
      }
    }

    // 单个任务下载
    const downloadSingleTask = async (task) => {
      try {
        ElMessage.info('准备下载任务视频，请在弹出的对话框中选择文件夹...')
        
        const response = await text2videoAPI.batchDownload([task.id])
        
        if (response.data.success) {
          ElMessage.success(response.data.message)
        } else {
          ElMessage.error(response.data.message)
        }
      } catch (error) {
        console.error('下载失败:', error)
        ElMessage.error(error.response?.data?.message || '下载失败')
      }
    }

    // 批量重试状态
    const batchRetryLoading = ref(false)

    // 自定义操作
    const customActions = ref([
      {
        key: 'batch-retry',
        text: '批量重试',
        icon: 'el-icon-refresh-right',
        type: 'warning',
        tooltip: '重试所有失败的任务',
        loading: false
      }
    ])

    // 处理自定义操作
    const handleCustomAction = (actionKey) => {
      switch (actionKey) {
        case 'batch-retry':
          batchRetryFailedTasks()
          break
        default:
          ElMessage.info(`执行操作: ${actionKey}`)
      }
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
          response = await text2videoAPI.batchRetryTasks(failedTaskIds)
          if (response.data.success) {
            ElMessage.success(`已重新加入队列 ${response.data.data.retry_count} 个任务`)
          } else {
            ElMessage.error(response.data.message || '批量重试失败')
          }
        } else {
          // 如果没有选中的失败任务，重试所有失败任务
          response = await text2videoAPI.batchRetryTasks()
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

    // 定时刷新相关变量
    let refreshInterval = null

    // 生命周期
    onMounted(() => {
      refreshTasks()
      
      // 设置定时刷新：每5秒刷新一次统计数据，如果存在处理中的任务则刷新任务列表
      refreshInterval = setInterval(() => {
        fetchStats()
        // 如果有处理中的任务，也刷新任务列表
        if (stats.value.processing > 0) {
          fetchTasks()
        }
      }, 5000)
    })

    onActivated(() => {
      refreshTasks()
    })

    onUnmounted(() => {
      // 清理定时器
      if (refreshInterval) {
        clearInterval(refreshInterval)
      }
      
      // 清理数据，避免内存泄漏
      tasks.value = []
      selectedTasks.value = []
      currentTask.value = null
    })

    return {
      loading,
      tasks,
      selectedTasks,
      statusFilter,
      currentPage,
      pageSize,
      pagination,
      stats,
      showAddTaskDialog,
      showBatchAddDialog,
      showResultDialog,
      addTaskLoading,
      batchAddLoading,
      taskForm,
      taskRules,
      taskFormRef,
      batchForm,
      batchFormRef,
      currentTask,
      fetchTasks,
      refreshTasks,
      addTask,
      batchAddTasks,
      deleteTask,
      batchDeleteTasks,
      retryTask,
      viewResult,
      handleSelectionChange,
      isTaskSelectable,
      handleStatusFilter,
      handleCurrentChange,
      handleSizeChange,
      resetTaskForm,
      resetBatchForm,
      truncateText,
      getStatusType,
      selectedCompletedTasks,
      batchDownloadVideos,
      downloadSingleTask,
      batchDownloadLoading,
            batchRetryFailedTasks,
      batchRetryLoading,
      getFailureReasonText,
      getFailureTooltipContent,
      customActions,
      handleCustomAction
    }
  }
}
</script>

<style scoped>
@import '../styles/jimeng-common.css';

/* 页面特定样式 */
.status-section {
  display: flex;
  align-items: center;
  gap: 16px;
}

/* 按钮样式覆盖 */
.batch-add-btn {
  background-color: #67C23A;
  border-color: #67C23A;
}

.batch-add-btn:hover {
  background-color: #85ce61;
  border-color: #85ce61;
}

.batch-download-btn {
  background-color: #409EFF;
  border-color: #409EFF;
}

.batch-download-btn:hover {
  background-color: #66b1ff;
  border-color: #66b1ff;
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

.refresh-btn {
  background-color: #E6A23C;
  border-color: #E6A23C;
}

.refresh-btn:hover {
  background-color: #ebb563;
  border-color: #ebb563;
}

/* 表格特定样式 */
.task-table-container {
  overflow-x: auto;
  width: 100%;
}

.task-table-container .el-table {
  width: 100%;
  min-width: 100%;
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

.prompt-cell {
  max-width: 250px;
}

.prompt-text {
  cursor: pointer;
  color: #606266;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.model-tag, .ratio-tag, .quality-tag {
  font-size: 12px;
  font-weight: 500;
}

.model-tag {
  background-color: #e1f3d8;
  color: #67c23a;
  border-color: #e1f3d8;
}

.ratio-tag {
  background-color: #fde2e2;
  color: #f56c6c;
  border-color: #fde2e2;
}

.quality-tag {
  background-color: #e1f3d8;
  color: #67c23a;
  border-color: #e1f3d8;
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

.status-tag.warning {
  background-color: #fde2e2;
  color: #f56c6c;
  border-color: #fde2e2;
}

.status-tag.success {
  background-color: #e1f3d8;
  color: #67c23a;
  border-color: #e1f3d8;
}

.status-tag.danger {
  background-color: #fde2e2;
  color: #f56c6c;
  border-color: #fde2e2;
}

.rotating-icon {
  animation: rotate 2s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 分页样式 */
.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding-top: 16px;
  border-top: 1px solid #e2e8f0;
}

/* 对话框特定样式 */
.modern-dialog {
  border-radius: 12px;
}

.modern-dialog :deep(.el-dialog__header) {
  padding: 20px 24px 16px;
  border-bottom: 1px solid #e4e7ed;
  background: #fafafa;
}

.modern-dialog :deep(.el-dialog__title) {
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
}

.modern-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.task-form, .batch-add-content {
  padding: 24px;
}

.task-form .el-form-item, .batch-add-content .el-form-item {
  margin-bottom: 20px;
}

.task-form .el-textarea, .batch-add-content .el-textarea {
  resize: vertical;
}

.task-form .el-select, .batch-add-content .el-select {
  width: 100%;
}

.task-form .full-width .el-input__inner, .batch-add-content .full-width .el-input__inner {
  width: 100%;
}

.form-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  color: #909399;
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

.cancel-btn {
  background-color: #f8f9fa;
  border-color: #e4e7ed;
  color: #606266;
}

.cancel-btn:hover {
  background-color: #f8f9fa;
  border-color: #e4e7ed;
  color: #409EFF;
}

.confirm-btn {
  background-color: #409EFF;
  border-color: #409EFF;
}

.confirm-btn:hover {
  background-color: #66b1ff;
  border-color: #66b1ff;
}

.format-guide {
  line-height: 1.6;
}

.format-guide p {
  margin: 6px 0;
}

.example-list {
  background: #f8f9fa;
  padding: 12px;
  border-radius: 6px;
  margin-top: 8px;
}

.example-list p {
  margin: 4px 0;
  font-family: monospace;
  color: #495057;
}

.batch-add-form {
  padding: 0;
}

.batch-stats {
  margin-top: 12px;
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.result-content {
  text-align: left;
}

.result-info h4 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #2c3e50;
  font-size: 16px;
  font-weight: 600;
}

.result-info p {
  margin: 8px 0;
  color: #606266;
  font-size: 14px;
}

.result-info strong {
  color: #374151;
  font-weight: 500;
}

.result-video {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.result-video h4 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #2c3e50;
  font-size: 16px;
  font-weight: 600;
}

.result-video-preview {
  width: 100%;
  max-width: 600px;
  height: auto;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
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

/* 操作按钮样式 */
.action-btn {
  font-size: 12px;
  padding: 4px 8px;
  min-width: auto;
}

.action-btn .el-icon {
  margin-right: 4px;
}

.btn-download {
  color: #409eff;
  border-color: #409eff;
  background-color: rgba(64, 158, 255, 0.1);
}

.btn-download:hover {
  color: #ffffff;
  background-color: #409eff;
  border-color: #409eff;
}

/* 页面特定响应式样式 */
@media (max-width: 768px) {
  .toolbar-actions {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }
}
</style>