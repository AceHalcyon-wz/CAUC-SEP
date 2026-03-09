<template>
  <div class="device-pr-path-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-main">
        <div class="header-left">
          <el-icon class="header-icon"><Setting /></el-icon>
          <div class="header-content">
            <h1 class="page-title">PR 路径配置</h1>
            <p class="page-subtitle">可视化配置和管理运动路径参数</p>
          </div>
        </div>
        <div class="header-right">
          <div class="action-buttons-group">
            <el-button 
              type="primary" 
              :icon="Download"
              @click="showExportDialog"
              class="action-button"
            >
              导出配置
            </el-button>
            <el-button 
              type="success" 
              :icon="Upload"
              @click="showImportDialog"
              class="action-button"
            >
              导入配置
            </el-button>
            <el-button 
              type="warning" 
              :icon="FolderOpened"
              @click="showTemplateDialog"
              class="action-button"
            >
              模板管理
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 主内容区：可视化编辑器 -->
    <div class="content-wrapper">
      <el-row :gutter="24" class="content-row">
        <el-col :span="24">
          <PRPathEditor 
            ref="pathEditorRef"
            :initial-path-points="currentPathPoints"
            @update:path-points="handlePathPointsUpdate"
            @save="handleSavePathPoints"
          />
        </el-col>
      </el-row>

      <!-- 路径选择器 -->
      <el-row :gutter="24" class="selector-row">
        <el-col :span="24">
          <el-card class="path-selector-card">
            <template #header>
              <div class="card-header">
                <div class="header-title-group">
                  <el-icon class="header-icon"><Grid /></el-icon>
                  <span class="header-title">路径选择</span>
                </div>
                <div class="header-actions">
                  <el-button 
                    type="primary" 
                    :icon="VideoPlay"
                    :disabled="!motorStore.canControl || !selectedPath"
                    @click="executeSelectedPath"
                    size="small"
                  >
                    执行选中路径
                  </el-button>
                  <el-button 
                    :icon="RefreshRight"
                    @click="resetCurrentPath"
                    size="small"
                  >
                    重置当前路径
                  </el-button>
                </div>
              </div>
            </template>

            <!-- 路径网格 -->
            <div class="path-grid">
              <div 
                v-for="i in 16" 
                :key="i" 
                class="path-item"
                :class="{ 
                  'active': selectedPath === i,
                  'configured': isPathConfigured(i)
                }"
                @click="selectPath(i)"
              >
                <div class="path-number">{{ i }}</div>
                <div class="path-status">
                  <el-icon v-if="isPathConfigured(i)" class="status-icon configured">
                    <CircleCheck />
                  </el-icon>
                  <el-icon v-else class="status-icon empty">
                    <CircleClose />
                  </el-icon>
                </div>
              </div>
            </div>

            <el-divider />

            <!-- 路径信息 -->
            <div class="path-info" v-if="selectedPath">
              <el-descriptions :column="4" border size="small">
                <el-descriptions-item label="路径编号">
                  <el-tag type="primary" effect="plain">{{ selectedPath }}</el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="配置状态">
                  <el-tag :type="isPathConfigured(selectedPath) ? 'success' : 'info'" effect="plain">
                    {{ isPathConfigured(selectedPath) ? '已配置' : '未配置' }}
                  </el-tag>
                </el-descriptions-item>
                <el-descriptions-item label="路径点数">
                  <span class="info-value">{{ currentPathPoints.length }}</span>
                </el-descriptions-item>
                <el-descriptions-item label="总距离">
                  <span class="info-value mono">{{ calculateTotalDistance(currentPathPoints).toFixed(2) }} mm</span>
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 导出配置对话框 -->
    <el-dialog
      v-model="exportDialogVisible"
      title="导出路径配置"
      width="600px"
      :close-on-click-modal="false"
      append-to-body
      :z-index="2000"
      destroy-on-close
    >
      <div class="export-dialog-content">
        <el-form label-width="100px">
          <el-form-item label="导出范围">
            <el-radio-group v-model="exportScope">
              <el-radio label="current">当前路径</el-radio>
              <el-radio label="all">所有路径</el-radio>
              <el-radio label="selected">选中路径</el-radio>
            </el-radio-group>
          </el-form-item>
          
          <el-form-item label="文件格式">
            <el-select v-model="exportFormat" style="width: 100%">
              <el-option label="JSON" value="json" />
              <el-option label="CSV" value="csv" />
            </el-select>
          </el-form-item>

          <el-form-item label="包含信息">
            <el-checkbox-group v-model="exportOptions">
              <el-checkbox label="metadata">元数据</el-checkbox>
              <el-checkbox label="timestamps">时间戳</el-checkbox>
              <el-checkbox label="descriptions">描述信息</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="handleExportDialogClose">取消</el-button>
        <el-button type="primary" :icon="Download" @click="handleExport">
          导出
        </el-button>
      </template>
    </el-dialog>

    <!-- 导入配置对话框 -->
    <el-dialog
      v-model="importDialogVisible"
      title="导入路径配置"
      width="600px"
      :close-on-click-modal="false"
      append-to-body
      :z-index="2000"
      destroy-on-close
    >
      <div class="import-dialog-content">
        <el-upload
          ref="uploadRef"
          :auto-upload="false"
          :limit="1"
          accept=".json,.csv"
          :on-change="handleFileChange"
          drag
        >
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">
            拖拽文件到此处或<em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              支持 JSON 和 CSV 格式，文件大小不超过 1MB
            </div>
          </template>
        </el-upload>

        <el-divider />

        <el-form v-if="importPreview" label-width="100px">
          <el-form-item label="文件信息">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="文件名">
                {{ importPreview.fileName }}
              </el-descriptions-item>
              <el-descriptions-item label="路径数量">
                {{ importPreview.pathCount }}
              </el-descriptions-item>
              <el-descriptions-item label="文件大小">
                {{ importPreview.fileSize }}
              </el-descriptions-item>
              <el-descriptions-item label="格式">
                {{ importPreview.format }}
              </el-descriptions-item>
            </el-descriptions>
          </el-form-item>

          <el-form-item label="导入策略">
            <el-radio-group v-model="importStrategy">
              <el-radio label="merge">合并（保留现有）</el-radio>
              <el-radio label="overwrite">覆盖（替换现有）</el-radio>
              <el-radio label="append">追加（添加到末尾）</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="handleImportDialogClose">取消</el-button>
        <el-button 
          type="primary" 
          :icon="Upload"
          :disabled="!importPreview"
          @click="handleImport"
        >
          导入
        </el-button>
      </template>
    </el-dialog>

    <!-- 模板管理对话框 -->
    <el-dialog
      v-model="templateDialogVisible"
      title="路径模板管理"
      width="900px"
      :close-on-click-modal="false"
      append-to-body
      :z-index="2000"
      destroy-on-close
    >
      <div class="template-dialog-content">
        <el-row :gutter="16">
          <!-- 模板列表 -->
          <el-col :span="12">
            <div class="template-list-section">
              <div class="section-header">
                <h3>模板列表</h3>
                <el-button 
                  type="primary" 
                  :icon="Plus"
                  @click="showCreateTemplateDialog"
                  size="small"
                >
                  新建模板
                </el-button>
              </div>

              <el-input
                v-model="templateSearchKeyword"
                placeholder="搜索模板..."
                :prefix-icon="Search"
                clearable
                class="search-input"
              />

              <div class="template-list">
                <div
                  v-for="template in filteredTemplates"
                  :key="template.id"
                  class="template-item"
                  :class="{ 'active': selectedTemplate?.id === template.id }"
                  @click="selectTemplate(template)"
                >
                  <div class="template-info">
                    <div class="template-name">{{ template.name }}</div>
                    <div class="template-meta">
                      <span>{{ template.points.length }} 个点</span>
                      <span>{{ formatDate(template.updatedAt) }}</span>
                    </div>
                  </div>
                  <div class="template-actions">
                    <el-button
                      type="primary"
                      :icon="Check"
                      circle
                      size="small"
                      @click.stop="applyTemplate(template)"
                      title="应用模板"
                    />
                    <el-button
                      type="warning"
                      :icon="Download"
                      circle
                      size="small"
                      @click.stop="exportTemplate(template)"
                      title="导出模板"
                    />
                    <el-button
                      type="danger"
                      :icon="Delete"
                      circle
                      size="small"
                      @click.stop="deleteTemplate(template.id)"
                      title="删除模板"
                    />
                  </div>
                </div>

                <el-empty 
                  v-if="filteredTemplates.length === 0"
                  description="暂无模板"
                  :image-size="80"
                />
              </div>
            </div>
          </el-col>

          <!-- 模板预览 -->
          <el-col :span="12">
            <div class="template-preview-section">
              <div class="section-header">
                <h3>模板预览</h3>
              </div>

              <div v-if="selectedTemplate" class="preview-content">
                <el-descriptions :column="1" border>
                  <el-descriptions-item label="模板名称">
                    {{ selectedTemplate.name }}
                  </el-descriptions-item>
                  <el-descriptions-item label="描述">
                    {{ selectedTemplate.description || '无描述' }}
                  </el-descriptions-item>
                  <el-descriptions-item label="创建时间">
                    {{ formatDate(selectedTemplate.createdAt) }}
                  </el-descriptions-item>
                  <el-descriptions-item label="更新时间">
                    {{ formatDate(selectedTemplate.updatedAt) }}
                  </el-descriptions-item>
                  <el-descriptions-item label="路径点数">
                    {{ selectedTemplate.points.length }}
                  </el-descriptions-item>
                  <el-descriptions-item label="总距离">
                    {{ calculateTotalDistance(selectedTemplate.points).toFixed(2) }} mm
                  </el-descriptions-item>
                </el-descriptions>

                <el-divider />

                <div class="points-preview">
                  <h4>路径点列表</h4>
                  <el-table 
                    :data="selectedTemplate.points" 
                    max-height="300"
                    size="small"
                  >
                    <el-table-column prop="mode" label="模式" width="80">
                      <template #default="{ row }">
                        <el-tag :type="row.mode === 0 ? 'primary' : 'success'" size="small">
                          {{ row.mode === 0 ? '绝对' : '增量' }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column prop="position_mm" label="位置(mm)" width="100" />
                    <el-table-column prop="velocity_mm_s" label="速度(mm/s)" width="110" />
                    <el-table-column prop="accel_time" label="加速(ms)" width="90" />
                    <el-table-column prop="decel_time" label="减速(ms)" width="90" />
                    <el-table-column prop="dwell_time" label="停留(ms)" width="90" />
                  </el-table>
                </div>
              </div>

              <el-empty 
                v-else
                description="选择一个模板查看详情"
                :image-size="120"
              />
            </div>
          </el-col>
        </el-row>
      </div>

      <template #footer>
        <el-button 
          type="primary" 
          :icon="Upload"
          @click="showImportTemplateDialog"
        >
          导入模板
        </el-button>
        <el-button @click="handleTemplateDialogClose">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 创建模板对话框 -->
    <el-dialog
      v-model="createTemplateDialogVisible"
      title="创建路径模板"
      width="500px"
      :close-on-click-modal="false"
      append-to-body
      :z-index="2100"
      destroy-on-close
    >
      <el-form 
        ref="templateFormRef"
        :model="newTemplate"
        :rules="templateRules"
        label-width="100px"
      >
        <el-form-item label="模板名称" prop="name">
          <el-input 
            v-model="newTemplate.name"
            placeholder="请输入模板名称"
            maxlength="50"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="模板描述" prop="description">
          <el-input
            v-model="newTemplate.description"
            type="textarea"
            :rows="3"
            placeholder="请输入模板描述（可选）"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="路径点">
          <el-alert
            :title="`将使用当前路径的 ${currentPathPoints.length} 个点创建模板`"
            type="info"
            :closable="false"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="handleCreateTemplateDialogClose">取消</el-button>
        <el-button 
          type="primary" 
          :icon="Check"
          @click="createTemplate"
        >
          创建
        </el-button>
      </template>
    </el-dialog>

    <!-- 导入模板对话框 -->
    <el-dialog
      v-model="importTemplateDialogVisible"
      title="导入路径模板"
      width="500px"
      :close-on-click-modal="false"
      append-to-body
      :z-index="2100"
      destroy-on-close
    >
      <el-upload
        ref="templateUploadRef"
        :auto-upload="false"
        :limit="1"
        accept=".json"
        :on-change="handleTemplateFileChange"
        drag
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          拖拽模板文件到此处或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            仅支持 JSON 格式的模板文件
          </div>
        </template>
      </el-upload>

      <template #footer>
        <el-button @click="handleImportTemplateDialogClose">取消</el-button>
        <el-button 
          type="primary" 
          :icon="Upload"
          :disabled="!templateImportFile"
          @click="importTemplate"
        >
          导入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * @file PRPath.vue
 * @path src/views/device/
 * @description PR路径配置页面，集成可视化编辑器、模板管理和导入导出功能
 * @author Agent
 * @date 2024-03-07
 */

import { ref, computed, onMounted } from 'vue'
import { useMotorStore } from '@/stores/motor'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Setting, Download, Upload, FolderOpened, Grid, VideoPlay, 
  RefreshRight, CircleCheck, CircleClose, Plus, Check, 
  Delete, Search, UploadFilled
} from '@element-plus/icons-vue'
import PRPathEditor from '@/components/PRPathEditor.vue'

const motorStore = useMotorStore()

// ==================== 响应式状态 ====================

const pathEditorRef = ref(null)
const selectedPath = ref(1)
const currentPathPoints = ref([])

// 导出对话框
const exportDialogVisible = ref(false)
const exportScope = ref('current')
const exportFormat = ref('json')
const exportOptions = ref(['metadata', 'timestamps'])

// 导入对话框
const importDialogVisible = ref(false)
const uploadRef = ref(null)
const importPreview = ref(null)
const importStrategy = ref('merge')
const importFile = ref(null)

// 模板管理对话框
const templateDialogVisible = ref(false)
const templateSearchKeyword = ref('')
const selectedTemplate = ref(null)

// 创建模板对话框
const createTemplateDialogVisible = ref(false)
const templateFormRef = ref(null)
const newTemplate = ref({
  name: '',
  description: ''
})

// 导入模板对话框
const importTemplateDialogVisible = ref(false)
const templateUploadRef = ref(null)
const templateImportFile = ref(null)

// ==================== 表单验证规则 ====================

const templateRules = {
  name: [
    { required: true, message: '请输入模板名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ]
}

// ==================== 计算属性 ====================

const filteredTemplates = computed(() => {
  if (!templateSearchKeyword.value) {
    return motorStore.pathTemplates
  }
  
  const keyword = templateSearchKeyword.value.toLowerCase()
  return motorStore.pathTemplates.filter(t => 
    t.name.toLowerCase().includes(keyword) ||
    (t.description && t.description.toLowerCase().includes(keyword))
  )
})

// ==================== 方法 ====================

/**
 * 选择路径
 * 
 * @param {number} pathNum - 路径编号
 */
function selectPath(pathNum) {
  selectedPath.value = pathNum
  // TODO: 从后端加载该路径的配置
  // 当前使用空数组或模拟数据
  currentPathPoints.value = []
}

/**
 * 判断路径是否已配置
 * 
 * @param {number} pathNum - 路径编号
 * @returns {boolean} 是否已配置
 */
function isPathConfigured(pathNum) {
  // TODO: 实际判断逻辑
  return false
}

/**
 * 执行选中的路径
 */
async function executeSelectedPath() {
  if (!selectedPath.value || !motorStore.canControl) return
  
  try {
    const success = await motorStore.triggerPRPath(selectedPath.value)
    if (success) {
      ElMessage.success(`路径 ${selectedPath.value} 已触发执行`)
    }
  } catch (error) {
    ElMessage.error(`执行失败: ${error.message}`)
  }
}

/**
 * 重置当前路径
 */
async function resetCurrentPath() {
  try {
    await ElMessageBox.confirm(
      '确定要重置当前路径配置吗？此操作将清除所有路径点！',
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    currentPathPoints.value = []
    ElMessage.success('路径已重置')
  } catch {
    // 用户取消
  }
}

/**
 * 处理路径点更新
 * 
 * @param {Array} points - 更新后的路径点
 */
function handlePathPointsUpdate(points) {
  currentPathPoints.value = points
}

/**
 * 处理保存路径点
 * 
 * @param {Array} points - 要保存的路径点
 */
async function handleSavePathPoints(points) {
  // TODO: 保存到后端
  ElMessage.success('路径配置已保存')
}

/**
 * 计算总距离
 * 
 * @param {Array} points - 路径点数组
 * @returns {number} 总距离
 */
function calculateTotalDistance(points) {
  if (!points || points.length === 0) return 0
  
  let distance = 0
  let currentPos = 0
  
  points.forEach(point => {
    if (point.mode === 0) {
      distance += Math.abs(point.position_mm - currentPos)
      currentPos = point.position_mm
    } else {
      distance += Math.abs(point.position_mm)
      currentPos += point.position_mm
    }
  })
  
  return distance
}

/**
 * 显示导出对话框
 */
function showExportDialog() {
  exportDialogVisible.value = true
}

/**
 * 关闭导出对话框
 */
function handleExportDialogClose() {
  exportDialogVisible.value = false
  // 重置导出配置
  exportScope.value = 'current'
  exportFormat.value = 'json'
  exportOptions.value = ['metadata', 'timestamps']
}

/**
 * 处理导出
 */
function handleExport() {
  let data = {}
  
  if (exportScope.value === 'current') {
    data = {
      pathNumber: selectedPath.value,
      points: currentPathPoints.value,
      exportedAt: new Date().toISOString()
    }
  } else if (exportScope.value === 'all') {
    data = {
      paths: [],
      exportedAt: new Date().toISOString()
    }
    // TODO: 收集所有路径配置
  }
  
  const content = JSON.stringify(data, null, 2)
  const blob = new Blob([content], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `pr-path-config-${Date.now()}.json`
  link.click()
  URL.revokeObjectURL(url)
  
  exportDialogVisible.value = false
  ElMessage.success('配置已导出')
}

/**
 * 显示导入对话框
 */
function showImportDialog() {
  importDialogVisible.value = true
  importPreview.value = null
  importFile.value = null
}

/**
 * 关闭导入对话框
 */
function handleImportDialogClose() {
  importDialogVisible.value = false
  // 清理导入相关状态
  importPreview.value = null
  importFile.value = null
  importStrategy.value = 'merge'
  // 清理上传组件
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
}

/**
 * 处理文件选择
 * 
 * @param {Object} file - 上传的文件
 */
function handleFileChange(file) {
  importFile.value = file.raw
  
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const content = e.target.result
      const data = JSON.parse(content)
      
      importPreview.value = {
        fileName: file.name,
        fileSize: `${(file.size / 1024).toFixed(2)} KB`,
        format: 'JSON',
        pathCount: data.paths ? data.paths.length : (data.points ? 1 : 0)
      }
    } catch (error) {
      ElMessage.error('文件解析失败')
      importPreview.value = null
    }
  }
  reader.readAsText(file.raw)
}

/**
 * 处理导入
 */
function handleImport() {
  if (!importFile.value) return
  
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const content = e.target.result
      const data = JSON.parse(content)
      
      if (data.points) {
        currentPathPoints.value = data.points
      }
      
      importDialogVisible.value = false
      ElMessage.success('配置已导入')
    } catch (error) {
      ElMessage.error('导入失败')
    }
  }
  reader.readAsText(importFile.value)
}

/**
 * 显示模板管理对话框
 */
function showTemplateDialog() {
  templateDialogVisible.value = true
  selectedTemplate.value = null
}

/**
 * 关闭模板管理对话框
 */
function handleTemplateDialogClose() {
  templateDialogVisible.value = false
  // 清理模板相关状态
  selectedTemplate.value = null
  templateSearchKeyword.value = ''
}

/**
 * 选择模板
 * 
 * @param {Object} template - 模板对象
 */
function selectTemplate(template) {
  selectedTemplate.value = template
}

/**
 * 应用模板
 * 
 * @param {Object} template - 模板对象
 */
async function applyTemplate(template) {
  try {
    await ElMessageBox.confirm(
      `确定要将模板 "${template.name}" 应用到当前路径吗？`,
      '应用模板',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )
    
    currentPathPoints.value = JSON.parse(JSON.stringify(template.points))
    ElMessage.success('模板已应用')
  } catch {
    // 用户取消
  }
}

/**
 * 导出模板
 * 
 * @param {Object} template - 模板对象
 */
function exportTemplate(template) {
  const content = motorStore.exportPathTemplate(template.id)
  const blob = new Blob([content], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `path-template-${template.name}.json`
  link.click()
  URL.revokeObjectURL(url)
  
  ElMessage.success('模板已导出')
}

/**
 * 删除模板
 * 
 * @param {number} templateId - 模板ID
 */
async function deleteTemplate(templateId) {
  try {
    await ElMessageBox.confirm(
      '确定要删除此模板吗？此操作不可恢复！',
      '删除模板',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const success = motorStore.deletePathTemplate(templateId)
    if (success) {
      if (selectedTemplate.value?.id === templateId) {
        selectedTemplate.value = null
      }
      ElMessage.success('模板已删除')
    }
  } catch {
    // 用户取消
  }
}

/**
 * 显示创建模板对话框
 */
function showCreateTemplateDialog() {
  newTemplate.value = {
    name: '',
    description: ''
  }
  createTemplateDialogVisible.value = true
}

/**
 * 关闭创建模板对话框
 */
function handleCreateTemplateDialogClose() {
  createTemplateDialogVisible.value = false
  // 重置表单
  newTemplate.value = {
    name: '',
    description: ''
  }
  if (templateFormRef.value) {
    templateFormRef.value.resetFields()
  }
}

/**
 * 创建模板
 */
async function createTemplate() {
  if (!templateFormRef.value) return
  
  await templateFormRef.value.validate((valid) => {
    if (valid) {
      if (currentPathPoints.value.length === 0) {
        ElMessage.warning('当前路径没有路径点，无法创建模板')
        return
      }
      
      const success = motorStore.addPathTemplate({
        name: newTemplate.value.name,
        description: newTemplate.value.description,
        points: currentPathPoints.value
      })
      
      if (success) {
        createTemplateDialogVisible.value = false
        ElMessage.success('模板创建成功')
      }
    }
  })
}

/**
 * 显示导入模板对话框
 */
function showImportTemplateDialog() {
  importTemplateDialogVisible.value = true
  templateImportFile.value = null
}

/**
 * 关闭导入模板对话框
 */
function handleImportTemplateDialogClose() {
  importTemplateDialogVisible.value = false
  // 清理导入状态
  templateImportFile.value = null
  // 清理上传组件
  if (templateUploadRef.value) {
    templateUploadRef.value.clearFiles()
  }
}

/**
 * 处理模板文件选择
 * 
 * @param {Object} file - 上传的文件
 */
function handleTemplateFileChange(file) {
  templateImportFile.value = file.raw
}

/**
 * 导入模板
 */
function importTemplate() {
  if (!templateImportFile.value) return
  
  const reader = new FileReader()
  reader.onload = (e) => {
    const content = e.target.result
    const success = motorStore.importPathTemplate(content)
    
    if (success) {
      importTemplateDialogVisible.value = false
      ElMessage.success('模板导入成功')
    }
  }
  reader.readAsText(templateImportFile.value)
}

/**
 * 格式化日期
 * 
 * @param {string} dateString - 日期字符串
 * @returns {string} 格式化后的日期
 */
function formatDate(dateString) {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// ==================== 生命周期 ====================

onMounted(() => {
  motorStore.loadPathTemplates()
})
</script>

<style scoped lang="scss">
/**
 * PR路径配置页面样式
 * 遵循 CAUC-SEP 设计系统规范
 */

.device-pr-path-page {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  background-color: var(--color-bg-secondary);
}

/* ==================== 页面头部 ==================== */

.page-header {
  background: linear-gradient(135deg, var(--color-primary-600) 0%, var(--color-primary-700) 100%);
  padding: var(--spacing-6);
  box-shadow: var(--shadow-lg);
}

.header-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: var(--content-max-width);
  margin: 0 auto;
  width: 100%;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
}

.header-icon {
  font-size: 48px;
  color: var(--color-text-inverse);
  opacity: 0.95;
  padding: var(--spacing-3);
  background: rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(10px);
}

.header-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-inverse);
  margin: 0;
  line-height: var(--line-height-tight);
}

.page-subtitle {
  font-size: var(--font-size-sm);
  color: rgba(255, 255, 255, 0.85);
  margin: 0;
}

.header-right {
  display: flex;
  gap: var(--spacing-3);
}

.action-buttons-group {
  display: flex;
  gap: var(--spacing-3);
}

.action-button {
  background: var(--color-text-inverse);
  color: var(--color-primary-600);
  border: none;
  font-weight: var(--font-weight-medium);
  transition: var(--transition-all);
  
  &:hover {
    background: var(--color-primary-50);
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }

  &:active {
    transform: translateY(0);
  }
}

/* ==================== 内容区域 ==================== */

.content-wrapper {
  flex: 1;
  max-width: var(--content-max-width);
  margin: 0 auto;
  width: 100%;
  padding: var(--spacing-6);
}

.content-row {
  margin-bottom: var(--spacing-6);
}

.selector-row {
  margin-bottom: var(--spacing-6);
}

/* ==================== 路径选择器卡片 ==================== */

.path-selector-card {
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  box-shadow: var(--shadow-md);
  transition: var(--transition-all);

  &:hover {
    box-shadow: var(--shadow-lg);
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title-group {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.header-icon {
  font-size: var(--font-size-lg);
  color: var(--color-primary-500);
}

.header-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.header-actions {
  display: flex;
  gap: var(--spacing-2);
}

/* ==================== 路径网格 ==================== */

.path-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: var(--spacing-4);
  padding: var(--spacing-4);
}

.path-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  aspect-ratio: 1;
  border-radius: var(--radius-lg);
  background: var(--color-bg-secondary);
  border: 2px solid var(--color-border-primary);
  cursor: pointer;
  transition: var(--transition-all);
  position: relative;
  overflow: hidden;
  
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg, transparent 0%, rgba(255, 255, 255, 0.05) 100%);
    opacity: 0;
    transition: var(--transition-all);
  }
  
  &:hover {
    background: var(--color-interactive-hover);
    border-color: var(--color-primary-400);
    transform: translateY(-4px);
    box-shadow: var(--shadow-md);

    &::before {
      opacity: 1;
    }
  }
  
  &.active {
    background: linear-gradient(135deg, var(--color-primary-500) 0%, var(--color-primary-600) 100%);
    border-color: var(--color-primary-500);
    box-shadow: 0 4px 12px rgba(24, 144, 255, 0.3);
    
    .path-number {
      color: var(--color-text-inverse);
      font-weight: var(--font-weight-bold);
    }
    
    .status-icon {
      color: var(--color-text-inverse);
    }
  }
  
  &.configured {
    border-color: var(--color-success);
    background: linear-gradient(135deg, var(--color-success-light) 0%, rgba(82, 196, 26, 0.1) 100%);
  }

  &.active.configured {
    background: linear-gradient(135deg, var(--color-primary-500) 0%, var(--color-primary-600) 100%);
    border-color: var(--color-primary-500);
  }
}

.path-number {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  font-family: var(--font-family-mono);
  margin-bottom: var(--spacing-1);
}

.path-status {
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-icon {
  font-size: var(--font-size-base);
  
  &.configured {
    color: var(--color-success);
  }
  
  &.empty {
    color: var(--color-text-tertiary);
  }
}

/* ==================== 路径信息 ==================== */

.path-info {
  padding: var(--spacing-3);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
}

.info-value {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.mono {
  font-family: var(--font-family-mono);
}

/* ==================== 对话框样式 ==================== */

.export-dialog-content,
.import-dialog-content {
  padding: var(--spacing-4);
}

.template-dialog-content {
  min-height: 500px;
}

.template-list-section,
.template-preview-section {
  height: 100%;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-4);
  
  h3 {
    margin: 0;
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-primary);
  }
}

.search-input {
  margin-bottom: var(--spacing-3);
}

.template-list {
  max-height: 400px;
  overflow-y: auto;
  padding-right: var(--spacing-2);
  
  /* 自定义滚动条 */
  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: var(--color-bg-secondary);
    border-radius: var(--radius-full);
  }

  &::-webkit-scrollbar-thumb {
    background: var(--color-border-primary);
    border-radius: var(--radius-full);
    transition: var(--transition-fast);

    &:hover {
      background: var(--color-primary-400);
    }
  }
}

.template-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-4);
  margin-bottom: var(--spacing-3);
  background: var(--color-bg-secondary);
  border: 2px solid var(--color-border-primary);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: var(--transition-all);
  
  &:hover {
    background: var(--color-interactive-hover);
    border-color: var(--color-primary-400);
    transform: translateX(4px);
  }
  
  &.active {
    background: var(--color-primary-50);
    border-color: var(--color-primary-500);
    box-shadow: 0 2px 8px rgba(24, 144, 255, 0.15);
  }
}

.template-info {
  flex: 1;
}

.template-name {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-1);
}

.template-meta {
  display: flex;
  gap: var(--spacing-3);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.template-actions {
  display: flex;
  gap: var(--spacing-2);
}

.preview-content {
  padding: var(--spacing-3);
}

.points-preview {
  h4 {
    margin: 0 0 var(--spacing-3) 0;
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-primary);
  }
}

/* ==================== 动画 ==================== */

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.8;
    transform: scale(1.05);
  }
}

/* ==================== 响应式设计 ==================== */

@media (max-width: 1200px) {
  .path-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (max-width: 768px) {
  .page-header {
    padding: var(--spacing-4);
  }

  .header-main {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-4);
  }

  .header-icon {
    font-size: 36px;
    padding: var(--spacing-2);
  }

  .page-title {
    font-size: var(--font-size-xl);
  }

  .header-right {
    width: 100%;
  }

  .action-buttons-group {
    width: 100%;
    flex-direction: column;
  }

  .action-button {
    width: 100%;
  }

  .content-wrapper {
    padding: var(--spacing-4);
  }

  .path-grid {
    grid-template-columns: repeat(4, 1fr);
    gap: var(--spacing-3);
    padding: var(--spacing-3);
  }

  .path-item {
    &:hover {
      transform: translateY(-2px);
    }
  }

  .path-number {
    font-size: var(--font-size-lg);
  }

  .template-dialog-content {
    min-height: auto;
  }

  .template-item {
    padding: var(--spacing-3);
  }
}

@media (max-width: 480px) {
  .path-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: var(--spacing-2);
  }

  .header-actions {
    flex-direction: column;
    width: 100%;

    .el-button {
      width: 100%;
    }
  }
}
</style>
