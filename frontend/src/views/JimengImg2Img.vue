<template>
  <div class="jimeng-page jimeng-img2img-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-content">
        <div class="title-section">
          <div class="title-icon">
            <el-icon size="32"><Picture /></el-icon>
          </div>
          <h1 class="page-title">即梦图生图</h1>
        </div>
        <div class="status-section">
          <!-- 导入文件夹按钮 -->
          <el-button
            class="btn-folder"
            size="large"
            @click="showImportFolderDialog"
            :disabled="importFolderLoading"
          >
            <el-icon><FolderOpened /></el-icon> 导入文件夹
          </el-button>

          <el-button
            class="btn-create" size="large"
            @click="showAddTaskDialog = true"
          >
            <el-icon><Plus /></el-icon> 创建任务
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
            class="btn-batch-delete"
            @click="handleBatchDelete"
            :disabled="selectedTasks.length === 0"
          >
            <el-icon><Delete /></el-icon> 批量删除
          </el-button>
          
          <el-button
            class="btn-batch-download"
            @click="handleBatchDownload"
            :disabled="selectedTasks.length === 0"
          >
            <el-icon><Download /></el-icon> 批量下载
          </el-button>
          
          <el-button
            class="btn-batch-retry"
            @click="batchRetryFailedTasks"
            :disabled="batchRetryLoading"
          >
            <el-icon><RefreshRight /></el-icon> 批量重试
          </el-button>
        </div>
      </div>

      <!-- 任务列表 -->
      <div class="task-list">
        <el-table
          :data="tasks"
          v-loading="loading"
          @selection-change="handleSelectionChange"
          class="task-table"
          empty-text="暂无任务"
        >
          <el-table-column type="selection" width="55" />
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column label="输入图片" width="120">
            <template #default="scope">
              <div class="input-images-preview">
                <div 
                  v-for="(image, index) in (scope.row.input_images || [])" 
                  :key="index"
                  class="input-image-item"
                >
                  <el-image
                    :src="getImageUrl(image)"
                    fit="cover"
                    class="input-image-thumb"
                    :preview-src-list="[getImageUrl(image)]"
                  />
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="prompt" label="提示词" min-width="200">
            <template #default="scope">
              <div class="prompt-text">{{ scope.row.prompt }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="model" label="模型" width="120" />
          <el-table-column prop="ratio" label="比例" width="80" />
          <el-table-column label="状态" width="100">
            <template #default="scope">
              <el-tag 
                :type="getStatusType(scope.row.status)"
                effect="dark"
              >
                {{ scope.row.status_text }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="生成结果" width="200">
            <template #default="scope">
              <div v-if="scope.row.output_images && scope.row.output_images.length > 0" class="image-gallery">
                <div 
                  v-for="(image, index) in (scope.row.output_images || [])" 
                  :key="index"
                  class="image-item-table"
                >
                  <el-image
                    :src="getImageUrl(image)"
                    fit="cover"
                    class="result-image-table"
                    :preview-src-list="(scope.row.output_images || []).map(img => getImageUrl(img))"
                  />
                </div>
              </div>
              <span v-else class="no-result">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="create_at" label="创建时间" width="160" />
          <el-table-column label="操作" width="200">
            <template #default="scope">
              <div class="action-buttons">
                <!-- 查看结果图片按钮 -->
                <el-button 
                  v-if="scope.row.output_images && scope.row.output_images.length > 0"
                  class="action-btn"
                  type="primary" 
                  size="small" 
                  @click="viewResult(scope.row)"
                >
                  <template #icon>
                    <el-icon><Picture /></el-icon>
                  </template>
                  查看
                </el-button>
                
                <!-- 下载结果图片按钮 -->
                <el-button 
                  v-if="scope.row.output_images && scope.row.output_images.length > 0"
                  class="action-btn"
                  type="success" 
                  size="small" 
                  @click="downloadSingleTaskImages(scope.row)"
                >
                  <template #icon>
                    <el-icon><Download /></el-icon>
                  </template>
                  下载
                </el-button>
                
                <!-- 失败原因图标 -->
                <el-tooltip 
                  v-if="scope.row.status === 3" 
                  placement="top" 
                  :content="getFailureTooltipContent(scope.row)" 
                  raw-content
                >
                  <el-icon class="failure-icon" size="18">
                    <InfoFilled />
                  </el-icon>
                </el-tooltip>
                
                <!-- 重试按钮 -->
                <el-button 
                  v-if="scope.row.status === 3 && (scope.row.retry_count || 0) < (scope.row.max_retry || 3)"
                  class="action-btn"
                  type="warning" 
                  size="small" 
                  @click="retryTask(scope.row.id)"
                >
                  <template #icon>
                    <el-icon><RefreshRight /></el-icon>
                  </template>
                  重试
                </el-button>
                
                <!-- 删除按钮 -->
                <el-button 
                  class="action-btn btn-delete"
                  size="small" 
                  :disabled="scope.row.status === 1"
                  @click="deleteTask(scope.row.id)"
                >
                  <template #icon>
                    <el-icon><Delete /></el-icon>
                  </template>
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
            :total="total"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
    </div>

    <!-- 创建任务对话框 -->
    <el-dialog
      v-model="showAddTaskDialog"
      title="创建图生图任务"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="taskFormRef"
        :model="taskForm"
        :rules="taskFormRules"
        label-width="120px"
      >
        <el-form-item label="输入图片" prop="images" required>
          <el-upload
            ref="uploadRef"
            :file-list="taskForm.images"
            :on-change="handleImageChange"
            :on-remove="handleImageRemove"
            :before-upload="beforeImageUpload"
            :auto-upload="false"
            list-type="picture-card"
            accept="image/*"
            multiple
            :limit="maxImageCount"
            drag
            class="upload-drag"
          >
            <el-icon><Plus /></el-icon>
            <template #tip>
              <div class="el-upload__tip">
                {{ uploadTipText }}
              </div>
            </template>
          </el-upload>
        </el-form-item>

        <el-form-item label="提示词" prop="prompt" required>
          <el-input
            v-model="taskForm.prompt"
            type="textarea"
            :rows="4"
            placeholder="请输入描述图片的提示词..."
            maxlength="1000"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="模型" prop="model">
          <el-select v-model="taskForm.model" placeholder="选择模型" @change="handleModelChange">
            <el-option label="Nano Banana" value="Nano Banana" />
            <el-option label="Image 2.0 Pro" value="Image 2.0 Pro" />
            <el-option label="Image 3.0" value="Image 3.0" />
            <el-option label="Image 4.0" value="Image 4.0" />
          </el-select>
        </el-form-item>

        <el-form-item label="分辨率比例" prop="aspect_ratio" v-if="shouldShowRatio">
          <el-select v-model="taskForm.aspect_ratio" placeholder="选择分辨率比例">
            <el-option label="1:1 (正方形)" value="1:1" />
            <el-option label="16:9 (横屏)" value="16:9" />
            <el-option label="9:16 (竖屏)" value="9:16" />
            <el-option label="4:3 (标准)" value="4:3" />
            <el-option label="3:4 (竖屏标准)" value="3:4" />
          </el-select>
        </el-form-item>

        <el-form-item label="图像质量" prop="quality">
          <el-select v-model="taskForm.quality" placeholder="选择图像质量" class="full-width">
            <el-option 
              v-for="qualityOption in getQualityOptions(taskForm.model)" 
              :key="qualityOption.value" 
              :label="qualityOption.label" 
              :value="qualityOption.value" 
            />
          </el-select>
        </el-form-item>

        <el-form-item label="同任务创建次数" prop="repeat_count">
          <el-input-number
            v-model="taskForm.repeat_count"
            :min="1"
            :max="50"
            placeholder="请输入创建次数"
            controls-position="right"
            style="width: 100%;"
          />
          <template #label>
            <div class="flex-center">
              同任务创建次数
              <el-tooltip content="设置相同的任务重复创建的次数，范围1-50次" placement="top">
                <el-icon class="info-icon"><QuestionFilled /></el-icon>
              </el-tooltip>
            </div>
          </template>
        </el-form-item>

      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button type="info" @click="showAddTaskDialog = false">
            取消
          </el-button>
          <el-button 
            class="btn-create"
            @click="submitTask"
            :disabled="submitting"
          >
            创建任务
          </el-button>
        </span>
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
          <p><strong>比例：</strong>{{ currentTask.ratio || currentTask.aspect_ratio || '-' }}</p>
          <p><strong>质量：</strong>{{ currentTask.quality || '-' }}</p>
        </div>
        
        <div class="result-images" v-if="currentTask.output_images && currentTask.output_images.length > 0">
          <h4>生成图像</h4>
          <div class="image-grid">
            <div 
              v-for="(url, index) in currentTask.output_images" 
              :key="index"
              class="image-item"
            >
              <el-image
                :src="getImageUrl(url)"
                :preview-src-list="currentTask.output_images.map(img => getImageUrl(img))"
                :initial-index="index"
                fit="cover"
                class="result-image"
                :loading="'lazy'"
              >
                <template #error>
                  <div class="image-error">
                    <el-icon><Picture /></el-icon>
                    <p>图片加载失败</p>
                  </div>
                </template>
              </el-image>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 导入文件夹设置对话框 -->
    <el-dialog
      v-model="importFolderDialogVisible"
      title="导入文件夹设置"
      width="400px"
      destroy-on-close
    >
      <el-form :model="importFolderForm" label-width="100px">
        <el-form-item label="图片模型">
          <el-select v-model="importFolderForm.model" placeholder="请选择图片模型" @change="handleImportModelChange">
            <el-option label="Nano Banana" value="Nano Banana" />
            <el-option label="Image 2.0 Pro" value="Image 2.0 Pro" />
            <el-option label="Image 3.0" value="Image 3.0" />
            <el-option label="Image 4.0" value="Image 4.0" />
          </el-select>
        </el-form-item>

        <el-form-item label="图片质量">
          <el-select v-model="importFolderForm.quality" placeholder="请选择图片质量">
            <el-option
              v-for="qualityOption in getQualityOptions(importFolderForm.model)"
              :key="qualityOption.value"
              :label="qualityOption.label"
              :value="qualityOption.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="图片比例" v-if="importFolderForm.model !== 'Nano Banana'">
          <el-select v-model="importFolderForm.aspect_ratio" placeholder="请选择图片比例">
            <el-option label="21:9 超宽屏" value="21:9" />
            <el-option label="16:9 横屏" value="16:9" />
            <el-option label="3:2 经典" value="3:2" />
            <el-option label="4:3 传统" value="4:3" />
            <el-option label="1:1 正方形" value="1:1" />
            <el-option label="3:4 肖像" value="3:4" />
            <el-option label="2:3 竖版" value="2:3" />
            <el-option label="9:16 竖屏" value="9:16" />
          </el-select>
        </el-form-item>

        <el-form-item label="添加提示词">
          <el-switch v-model="importFolderForm.usePrompt" />
        </el-form-item>

        <el-form-item v-if="importFolderForm.usePrompt" label="提示词内容">
          <el-input
            v-model="importFolderForm.prompt"
            type="textarea"
            :rows="4"
            placeholder="请输入提示词，将应用于本次导入的所有任务"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>

        <!-- 注意事项 -->
        <el-alert
          title="注意事项"
          type="warning"
          :closable="false"
          show-icon
          class="import-notice"
        >
          <template #default>
            <p>只支持单张图</p>
          </template>
        </el-alert>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button class="cancel-button" @click="importFolderDialogVisible = false">取消</el-button>
          <el-button class="btn-create" @click="confirmImportFolder" :loading="importFolderLoading">
            确认并选择文件夹
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted, onUnmounted, computed, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  Refresh,
  RefreshRight,
  Delete,
  Download,
  Picture,
  ZoomIn,
  QuestionFilled,
  CircleCheck,
  InfoFilled,
  FolderOpened
} from '@element-plus/icons-vue'
import axios from 'axios'
import { img2imgAPI, accountAPI } from '@/utils/api'
import StatusCountDisplay from '@/components/StatusCountDisplay.vue'


export default {
  name: 'JimengImg2Img',
  components: {
    Plus,
    Refresh,
    RefreshRight,
    Delete,
    Download,
    Picture,
    StatusCountDisplay,
    QuestionFilled,
    CircleCheck,
    InfoFilled,
    FolderOpened
  },
  setup() {
    // 响应式数据
    const tasks = ref([])
    const stats = ref({
      total: 0,
      queued: 0,
      processing: 0,
      completed: 0,
      failed: 0
    })
    const accounts = ref([])
    const loading = ref(false)
    const submitting = ref(false)
    const showAddTaskDialog = ref(false)
    const selectedTasks = ref([])
    
    // 批量重试状态
    const batchRetryLoading = ref(false)

    // 导入文件夹相关状态
    const importFolderLoading = ref(false)
    const importFolderDialogVisible = ref(false)
    const importFolderForm = reactive({
      model: 'Nano Banana',
      quality: '1K',
      aspect_ratio: '1:1',
      usePrompt: false,
      prompt: ''
    })
    
    // 分页数据
    const currentPage = ref(1)
    const pageSize = ref(10)
    const total = ref(0)
    const statusFilter = ref(null)
    
    // 表单数据
    const taskForm = reactive({
      prompt: '',
      model: 'Nano Banana',
      aspect_ratio: '',  // NanoBanana模型默认不设置比例
      quality: '1K',  // 默认质量为1K
      images: [],
      repeat_count: 1  // 同任务创建次数，默认为1次
    })
    
    // 表单验证规则
    const taskFormRules = {
      prompt: [
        { required: true, message: '请输入提示词', trigger: 'blur' },
        { min: 1, max: 1000, message: '提示词长度应在1-1000字符之间', trigger: 'blur' }
      ],
      images: [
        { required: true, message: '请选择输入图片', trigger: 'change' }
      ],
      quality: [
        { required: true, message: '请选择清晰度', trigger: 'change' }
      ],
      repeat_count: [
        { required: true, message: '请输入同任务创建次数', trigger: 'blur' },
        { type: 'number', min: 1, max: 50, message: '同任务创建次数必须在1-50之间', trigger: 'blur' }
      ]
    }
    
    const taskFormRef = ref(null)
    const uploadRef = ref(null)
    
    // 计算属性 - 最大图片数量
    const maxImageCount = computed(() => {
      if (taskForm.model === 'Nano Banana') {
        return 3  // Nano Banana模型支持最多3张图片
      } else if (taskForm.model === 'Image 4.0') {
        return 6  // Image 4.0模型支持最多6张图片
      } else {
        return 1  // 其他模型支持1张图片
      }
    })
    
    // 计算属性 - 上传提示文本
    const uploadTipText = computed(() => {
      const maxCount = maxImageCount.value
      const countText = maxCount === 1 ? '1张图片' : `1-${maxCount}张图片`
      return `支持JPG、PNG、GIF等格式，最多上传${countText}，每张不超过10MB`
    })
    
    // 计算属性 - 是否显示分辨率比例选择
    const shouldShowRatio = computed(() => {
      return taskForm.model !== 'Nano Banana'
    })
    
    // 获取任务列表
    const getTasks = async () => {
      loading.value = true
      try {
        const params = {
          page: currentPage.value,
          page_size: pageSize.value
        }
        if (statusFilter.value !== null) {
          params.status = statusFilter.value
        }
        
        const response = await img2imgAPI.getTasks(params)
        if (response.data.success) {
          tasks.value = response.data.data.tasks
          total.value = response.data.data.total
        }
      } catch (error) {
        console.error('获取任务列表失败:', error)
        ElMessage.error('获取任务列表失败')
      } finally {
        loading.value = false
      }
    }
    
    // 获取统计信息
    const getStats = async () => {
      try {
        const response = await img2imgAPI.getStats()
        if (response.data.success) {
          stats.value = response.data.data
        }
      } catch (error) {
        console.error('获取统计信息失败:', error)
      }
    }
    
    // 获取账号列表
    const getAccounts = async () => {
      try {
        const response = await accountAPI.getAccounts()
        if (response.data.success) {
          accounts.value = response.data.data
        }
      } catch (error) {
        console.error('获取账号列表失败:', error)
      }
    }
    
    // 模型变更处理
    const handleModelChange = (value) => {
      let maxCount = 1; // 默认为1张图片
      if (value === 'Nano Banana') {
        maxCount = 3;  // Nano Banana模型支持3张图片
      } else if (value === 'Image 4.0') {
        maxCount = 6;  // Image 4.0模型支持6张图片
      }
      
      // 如果当前图片数量超过新模型的限制，移除多余的图片
      if (taskForm.images.length > maxCount) {
        taskForm.images = taskForm.images.slice(0, maxCount)
        if (uploadRef.value) {
          // 更新上传组件的文件列表
          uploadRef.value.clearFiles()
          taskForm.images.forEach(fileItem => {
            uploadRef.value.handleStart(fileItem.raw)
          })
        }
      }
    }
    
    // 图片上传处理
    const handleImageChange = (file, fileList) => {
      taskForm.images = fileList
    }
    
    const handleImageRemove = (file, fileList) => {
      taskForm.images = fileList
    }
    
    const beforeImageUpload = (file) => {
      const isImage = file.type.startsWith('image/')
      const isLt10M = file.size / 1024 / 1024 < 10
      
      if (!isImage) {
        ElMessage.error('只能上传图片文件!')
        return false
      }
      if (!isLt10M) {
        ElMessage.error('图片大小不能超过10MB!')
        return false
      }
      return false // 阻止自动上传
    }
    
    // 提交任务
    const submitTask = async () => {
      if (!taskFormRef.value) return
      
      try {
        await taskFormRef.value.validate()
        
        if (taskForm.images.length === 0) {
          ElMessage.error('请选择输入图片')
          return
        }
        
        submitting.value = true
        
        const formData = new FormData()
        formData.append('prompt', taskForm.prompt)
        formData.append('model', taskForm.model)
        formData.append('quality', taskForm.quality)
        formData.append('repeat_count', parseInt(taskForm.repeat_count))  // 添加重复次数参数
        
        // 只有当显示比例选择框时才添加aspect_ratio参数
        if (shouldShowRatio.value && taskForm.aspect_ratio) {
        formData.append('aspect_ratio', taskForm.aspect_ratio)
        }
        
        // 添加图片文件
        taskForm.images.forEach(fileItem => {
          formData.append('images', fileItem.raw)
        })
        
        const response = await img2imgAPI.createTask(formData)
        
        if (response.data.success) {
          ElMessage.success(response.data.message || `成功创建 ${response.data.count || 1} 个任务`)
          showAddTaskDialog.value = false
          resetForm()
          getTasks()
          getStats()
        } else {
          ElMessage.error(response.data.message || '创建任务失败')
        }
      } catch (error) {
        console.error('创建任务失败:', error)
        ElMessage.error('创建任务失败')
      } finally {
        submitting.value = false
      }
    }
    
    // 重置表单
    const resetForm = () => {
      Object.assign(taskForm, {
        prompt: '',
        model: 'Nano Banana',
        aspect_ratio: '',  // NanoBanana模型不设置默认比例
        quality: '1K',  // 默认质量为1K
        images: [],
        repeat_count: 1  // 重置重复次数为默认值
      })
      if (uploadRef.value) {
        uploadRef.value.clearFiles()
      }
      if (taskFormRef.value) {
        taskFormRef.value.clearValidate()
      }
    }
    
    // 删除任务
    const deleteTask = async (taskId) => {
      try {
        await ElMessageBox.confirm('确定要删除这个任务吗？', '提示', {
          type: 'warning'
        })
        
        const response = await img2imgAPI.deleteTask(taskId)
        if (response.data.success) {
          ElMessage.success('删除成功')
          getTasks()
          getStats()
        } else {
          ElMessage.error(response.data.message || '删除失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('删除任务失败:', error)
          ElMessage.error('删除失败')
        }
      }
    }
    
    // 重试任务
    const retryTask = async (taskId) => {
      try {
        const response = await img2imgAPI.retryTask(taskId)
        if (response.data.success) {
          ElMessage.success('任务已重新排队')
          getTasks()
          getStats()
        } else {
          ElMessage.error(response.data.message || '重试失败')
        }
      } catch (error) {
        console.error('重试任务失败:', error)
        ElMessage.error('重试失败')
      }
    }
    
    // 批量删除
    const handleBatchDelete = async () => {
      if (selectedTasks.value.length === 0) {
        ElMessage.warning('请选择要删除的任务')
        return
      }
      
      try {
        await ElMessageBox.confirm(`确定要删除选中的 ${selectedTasks.value.length} 个任务吗？`, '批量删除', {
          type: 'warning'
        })
        
        const taskIds = selectedTasks.value.map(task => task.id)
        const response = await img2imgAPI.batchDeleteTasks(taskIds)
        
        if (response.data.success) {
          ElMessage.success(response.data.message)
          getTasks()
          getStats()
          selectedTasks.value = []
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
    
    // 批量下载
    const handleBatchDownload = async () => {
      if (selectedTasks.value.length === 0) {
        ElMessage.warning('请选择要下载的任务')
        return
      }
      
      const completedTasks = selectedTasks.value.filter(task => task.status === 2)
      if (completedTasks.length === 0) {
        ElMessage.warning('选中的任务中没有已完成的任务')
        return
      }
      
      try {
        ElMessage.info('准备下载任务图片，请在弹出的对话框中选择文件夹...')
        const taskIds = selectedTasks.value.map(task => task.id)
        const response = await img2imgAPI.batchDownload(taskIds)
        if (response.data.success) {
          ElMessage.success(response.data.message)
        } else {
          ElMessage.error(response.data.message)
        }
      } catch (error) {
        console.error('批量下载失败:', error)
        ElMessage.error(error.response?.data?.message || '批量下载失败')
      }
    }
    
    // 选择变化处理
    const handleSelectionChange = (selection) => {
      selectedTasks.value = selection
    }
    
    // 状态筛选
    const handleStatusFilter = () => {
      currentPage.value = 1
      getTasks()
    }
    
    // 分页处理
    const handleSizeChange = (size) => {
      pageSize.value = size
      currentPage.value = 1
      getTasks()
    }
    
    const handleCurrentChange = (page) => {
      currentPage.value = page
      getTasks()
    }
    
    // 刷新任务
    const refreshTasks = () => {
      getTasks()
      getStats()
    }
    
    // 获取状态类型
    const getStatusType = (status) => {
      const statusTypes = {
        0: 'info',     // 排队中
        1: 'warning',  // 生成中
        2: 'success',  // 已完成
        3: 'danger'    // 失败
      }
      return statusTypes[status] || 'info'
    }
    
    // 响应式数据
    const showResultDialog = ref(false)
    const currentTask = ref(null)
    
    // 根据模型获取质量选项
    const getQualityOptions = (model) => {
      if (model === 'Image 4.0') {
        // Image 4.0 模型只支持 2K 和 4K
        return [
          { label: 'High (2K)', value: '2K' },
          { label: 'Ultra (4K)', value: '4K' }
        ]
      } else {
        // 其他模型支持 1K 和 2K
        return [
          { label: 'Standard (1K)', value: '1K' },
          { label: 'High (2K)', value: '2K' }
        ]
      }
    }
    
    // 预览图片 - 现在使用对话框形式
    const previewImages = (task) => {
      currentTask.value = task
      showResultDialog.value = true
    }
    
    // 查看任务结果
    const viewResult = (task) => {
      previewImages(task)
    }
    
    // 下载单个任务的图片
    const downloadSingleTaskImages = async (task) => {
      try {
        ElMessage.info('准备下载任务图片，请在弹出的对话框中选择文件夹...')
        const response = await img2imgAPI.batchDownload([task.id])
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
    
    // 下载图片（保留原有方法，用于其他用途）
    const downloadImages = (imageList, taskId) => {
      imageList.forEach((img, index) => {
        const url = getImageUrl(img)  // 使用getImageUrl方法处理URL
        const link = document.createElement('a')
        link.href = url
        link.download = `img2img_task_${taskId}_${index + 1}.${getFileExtension(img)}`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      })
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
    
    // 获取文件扩展名
    const getFileExtension = (filename) => {
      const parts = filename.split('.')
      if (parts.length > 1) {
        return parts[parts.length - 1].toLowerCase()
      }
      return 'jpg' // 默认扩展名
    }
    
    // 获取图片URL，判断是本地路径还是远程URL
    const getImageUrl = (imagePath) => {
      if (!imagePath) return ''
      
      // 如果是远程URL（以http或https开头），直接返回
      if (imagePath.startsWith('http://') || imagePath.startsWith('https://')) {
        return imagePath
      }
      
      // 如果是本地文件完整路径，提取文件名
      let fileName = imagePath
      if (imagePath.includes('/')) {
        fileName = imagePath.split('/').pop()  // Unix风格路径
      } else if (imagePath.includes('\\')) {
        fileName = imagePath.split('\\').pop()  // Windows风格路径
      }
      
      // 构建为静态服务器URL
      return `http://localhost:8888/static/images/${fileName}`
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
          response = await img2imgAPI.batchRetryTasks(failedTaskIds)
          if (response.data.success) {
            ElMessage.success(`已重新加入队列 ${response.data.data.retry_count} 个任务`)
          } else {
            ElMessage.error(response.data.message || '批量重试失败')
          }
        } else {
          // 如果没有选中的失败任务，重试所有失败任务
          response = await img2imgAPI.batchRetryTasks()
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

    // 导入文件夹相关函数
    const showImportFolderDialog = () => {
      importFolderDialogVisible.value = true
    }

    const handleImportModelChange = (modelValue) => {
      // 当切换到Nano Banana时，重置比例为默认值
      if (modelValue === 'Nano Banana') {
        importFolderForm.aspect_ratio = '1:1'
      }
      // 如果切换到其他模型且比例为空，设置默认比例
      else if (!importFolderForm.aspect_ratio) {
        importFolderForm.aspect_ratio = '1:1'
      }
    }

    const confirmImportFolder = async () => {
      try {
        importFolderLoading.value = true

        const params = {
          model: importFolderForm.model,
          quality: importFolderForm.quality,
          usePrompt: importFolderForm.usePrompt,
          prompt: importFolderForm.prompt
        }

        // 只有非Nano Banana模型才添加aspect_ratio参数
        if (importFolderForm.model !== 'Nano Banana') {
          params.aspect_ratio = importFolderForm.aspect_ratio
        }

        const response = await img2imgAPI.importFolder(params)

        if (response.data.success) {
          ElMessage.success("文件选择器已调用打开，请小化浏览器返回桌面选择文件夹")
          ElMessage.info(`使用模型: ${params.model}，质量: ${params.quality}${params.aspect_ratio ? `，比例: ${params.aspect_ratio}` : ''}${params.usePrompt ? '，添加提示词' : ''}`)
          if (params.prompt) {
            ElMessage.info(`提示词: ${params.prompt}`)
          }
          // 延迟刷新任务列表
          setTimeout(() => {
            refreshTasks()
          }, 2000)
          importFolderDialogVisible.value = false
        } else {
          ElMessage.error(response.data.message || '导入文件夹失败')
        }
      } catch (error) {
        console.error('导入文件夹失败:', error)
        ElMessage.error('导入文件夹失败')
      } finally {
        importFolderLoading.value = false
      }
    }
    
    // 定时刷新
    let refreshInterval = null
    
    // 组件挂载时初始化
    onMounted(() => {
      getTasks()
      getStats()
      getAccounts()
      
      // 定时刷新 - 与其他页面保持一致的刷新策略
      refreshInterval = setInterval(() => {
        getStats()
        // 如果有处理中的任务，也刷新任务列表
        if (stats.value.processing > 0) {
          getTasks()
        }
      }, 5000)
    })
    
    onUnmounted(() => {
      if (refreshInterval) {
        clearInterval(refreshInterval)
      }
    })
    
    return {
      // 数据
      tasks,
      stats,
      accounts,
      loading,
      submitting,
      showAddTaskDialog,
      selectedTasks,
      currentPage,
      pageSize,
      total,
      statusFilter,
      taskForm,
      taskFormRules,
      taskFormRef,
      uploadRef,
      maxImageCount,
      uploadTipText,
      shouldShowRatio,

      // 导入文件夹相关数据
      importFolderLoading,
      importFolderDialogVisible,
      importFolderForm,

      // 方法
      getTasks,
      getStats,
      getAccounts,
      handleModelChange,
      handleImageChange,
      handleImageRemove,
      beforeImageUpload,
      submitTask,
      resetForm,
      deleteTask,
      retryTask,
      handleBatchDelete,
      handleBatchDownload,
      handleSelectionChange,
      handleStatusFilter,
      handleSizeChange,
      handleCurrentChange,
      refreshTasks,
      getStatusType,
      getQualityOptions,

      // 数据
      showResultDialog,
      currentTask,

      // 方法
      previewImages,
      viewResult,
      downloadImages,
      downloadSingleTaskImages,
      getFileExtension,
      getImageUrl,

      // 导入文件夹相关方法
      showImportFolderDialog,
      handleImportModelChange,
      confirmImportFolder,

      // 批量重试相关
      batchRetryLoading,
      batchRetryFailedTasks,

      // 失败原因相关
      getFailureReasonText,
      getFailureTooltipContent,
      nextTick
    }
  }
}
</script>

<style scoped>
.jimeng-img2img-page {
  padding: 24px;
  background: #f5f7fa;
  min-height: 100vh;
}

/* 结果对话框样式 */
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

.result-images {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.result-images h4 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #2c3e50;
  font-size: 16px;
  font-weight: 600;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
  width: 100%;
  max-width: 500px;
  margin: 0 auto;
}

.image-item {
  position: relative;
  width: 100%;
  aspect-ratio: 1 / 1; /* 维持正方形比例 */
  border-radius: 8px;
  overflow: hidden;
  background-color: #f0f2f5;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 120px; /* 最小高度 */
}

.result-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.image-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #909399;
  font-size: 14px;
}

.image-error .el-icon {
  font-size: 30px;
  margin-bottom: 8px;
}

/* 失败原因图标样式 */
.failure-icon {
  color: #e6a23c;
  margin-right: 8px;
  cursor: pointer;
  vertical-align: middle;
}

.page-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  padding: 32px;
  margin-bottom: 24px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-section {
  display: flex;
  align-items: center;
  gap: 16px;
}

.title-icon {
  width: 64px;
  height: 64px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.page-title {
  color: white;
  font-size: 32px;
  font-weight: 600;
  margin: 0;
}

.add-task-btn {
  height: 48px;
  padding: 0 24px;
  border-radius: 24px;
  font-size: 16px;
  font-weight: 500;
}

.task-management {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.panel-title {
  padding: 24px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.panel-title h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #2d3748;
}

.toolbar-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.status-filter {
  width: 120px;
}

.task-list {
  padding: 24px;
}

.task-table {
  margin-bottom: 24px;
}

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

.prompt-text {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.image-gallery {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.image-item-table {
  width: 40px;
  height: 40px;
  position: relative;
  display: inline-block;
  margin-right: 2px;
}

.result-image-table {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 4px;
}

.no-result {
  color: #a0aec0;
}

.action-buttons {
  display: flex;
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

.pagination-wrapper {
  display: flex;
  justify-content: center;
  padding-top: 16px;
  border-top: 1px solid #e2e8f0;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.upload-drag {
  width: 100%;
}

.upload-drag :deep(.el-upload-dragger) {
  width: 100%;
  height: 180px;
  border: 2px dashed #dcdfe6;
  border-radius: 8px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  transition: border-color 0.3s;
}

.upload-drag :deep(.el-upload-dragger:hover) {
  border-color: #409eff;
}

.upload-drag :deep(.el-upload-dragger .el-icon) {
  font-size: 67px;
  color: #c0c4cc;
  margin: 40px 0 16px;
  line-height: 50px;
}

.upload-drag :deep(.el-upload__text) {
  color: #606266;
  font-size: 14px;
  text-align: center;
}

.flex-center {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 导入文件夹按钮样式 */
.btn-folder {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  border: none;
  color: white;
  font-weight: 500;
  transition: all 0.3s ease;
}

.btn-folder:hover {
  background: linear-gradient(135deg, #059669 0%, #047857 100%);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.btn-folder:disabled {
  background: #9ca3af;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* 导入文件夹对话框样式 */
.import-notice {
  margin-top: 16px;
}

.import-notice p {
  margin: 0;
  font-weight: 500;
}
</style> 