<template>
  <div class="settings-profile-page">
    <!-- 页面头部 -->
    <el-row class="page-header">
      <el-col :span="24">
        <div class="header-content">
          <div class="header-left">
            <el-icon class="header-icon"><User /></el-icon>
            <div class="header-text">
              <h1 class="page-title">个人中心</h1>
              <p class="page-subtitle">管理您的账户信息、偏好设置与操作历史</p>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 标签页内容 -->
    <div class="profile-content">
      <el-tabs v-model="activeTab" class="profile-tabs" @tab-change="handleTabChange">
        <!-- 个人信息标签页 -->
        <el-tab-pane label="个人信息" name="profile">
          <div class="tab-content">
            <!-- 用户头像卡片 -->
            <el-card class="profile-card avatar-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span>头像设置</span>
                </div>
              </template>
              <div class="avatar-section">
                <div class="avatar-display">
                  <el-avatar :size="100" class="user-avatar">
                    {{ userStore.avatarText }}
                  </el-avatar>
                  <div class="avatar-info">
                    <p class="avatar-tip">支持 JPG、PNG 格式，大小不超过 2MB</p>
                    <el-upload
                      ref="avatarUploadRef"
                      class="avatar-upload"
                      action="#"
                      :auto-upload="false"
                      :show-file-list="false"
                      :on-change="handleAvatarChange"
                      accept="image/jpeg,image/png"
                    >
                      <el-button type="primary" size="small">
                        <el-icon><Upload /></el-icon>
                        上传头像
                      </el-button>
                    </el-upload>
                  </div>
                </div>
              </div>
            </el-card>

            <!-- 基本信息 -->
            <el-card class="profile-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span>基本信息</span>
                  <el-button
                    v-if="!isEditingProfile"
                    type="primary"
                    text
                    @click="startEditProfile"
                  >
                    <el-icon><Edit /></el-icon>
                    编辑
                  </el-button>
                  <template v-else>
                    <el-button text @click="cancelEditProfile">取消</el-button>
                    <el-button type="primary" @click="saveProfile">保存</el-button>
                  </template>
                </div>
              </template>
              <el-form
                ref="profileFormRef"
                :model="profileForm"
                :rules="profileRules"
                label-width="100px"
                :disabled="!isEditingProfile"
              >
                <el-form-item label="用户名" prop="username">
                  <el-input v-model="profileForm.username" placeholder="请输入用户名" />
                </el-form-item>
                <el-form-item label="邮箱" prop="email">
                  <el-input v-model="profileForm.email" placeholder="请输入邮箱" />
                </el-form-item>
                <el-form-item label="角色">
                  <el-tag :type="getRoleTagType(userStore.currentUser?.role)">
                    {{ userStore.roleLabel }}
                  </el-tag>
                </el-form-item>
                <el-form-item label="注册时间">
                  <span class="info-text">{{ formatDateTime(userStore.currentUser?.createdAt) }}</span>
                </el-form-item>
              </el-form>
            </el-card>

            <!-- 密码修改 -->
            <el-card class="profile-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span>密码修改</span>
                </div>
              </template>
              <el-form
                ref="passwordFormRef"
                :model="passwordForm"
                :rules="passwordRules"
                label-width="100px"
              >
                <el-form-item label="当前密码" prop="oldPassword">
                  <el-input
                    v-model="passwordForm.oldPassword"
                    type="password"
                    placeholder="请输入当前密码"
                    show-password
                  />
                </el-form-item>
                <el-form-item label="新密码" prop="newPassword">
                  <el-input
                    v-model="passwordForm.newPassword"
                    type="password"
                    placeholder="请输入新密码"
                    show-password
                  />
                </el-form-item>
                <el-form-item label="确认密码" prop="confirmPassword">
                  <el-input
                    v-model="passwordForm.confirmPassword"
                    type="password"
                    placeholder="请再次输入新密码"
                    show-password
                  />
                </el-form-item>
                <el-form-item>
                  <el-button
                    type="primary"
                    :loading="passwordLoading"
                    @click="handleChangePassword"
                  >
                    修改密码
                  </el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </div>
        </el-tab-pane>

        <!-- 偏好设置标签页 -->
        <el-tab-pane label="偏好设置" name="preferences">
          <div class="tab-content">
            <!-- 通知设置 -->
            <el-card class="profile-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span>通知设置</span>
                </div>
              </template>
              <el-form label-width="120px">
                <el-form-item label="启用通知">
                  <el-switch
                    v-model="preferencesForm.notification.enabled"
                    @change="handlePreferencesChange"
                  />
                </el-form-item>
                <el-form-item label="声音提示">
                  <el-switch
                    v-model="preferencesForm.notification.sound"
                    :disabled="!preferencesForm.notification.enabled"
                    @change="handlePreferencesChange"
                  />
                </el-form-item>
                <el-form-item label="邮件通知">
                  <el-switch
                    v-model="preferencesForm.notification.email"
                    :disabled="!preferencesForm.notification.enabled"
                    @change="handlePreferencesChange"
                  />
                </el-form-item>
                <el-form-item label="桌面通知">
                  <el-switch
                    v-model="preferencesForm.notification.desktop"
                    :disabled="!preferencesForm.notification.enabled"
                    @change="handlePreferencesChange"
                  />
                </el-form-item>
              </el-form>
            </el-card>

            <!-- 显示选项 -->
            <el-card class="profile-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span>显示选项</span>
                </div>
              </template>
              <el-form label-width="120px">
                <el-form-item label="数据刷新频率">
                  <el-select
                    v-model="preferencesForm.display.refreshInterval"
                    placeholder="请选择刷新频率"
                    @change="handlePreferencesChange"
                  >
                    <el-option label="500ms" :value="500" />
                    <el-option label="1秒" :value="1000" />
                    <el-option label="2秒" :value="2000" />
                    <el-option label="5秒" :value="5000" />
                  </el-select>
                </el-form-item>
                <el-form-item label="图表默认类型">
                  <el-select
                    v-model="preferencesForm.display.chartDefaultType"
                    placeholder="请选择图表类型"
                    @change="handlePreferencesChange"
                  >
                    <el-option label="折线图" value="line" />
                    <el-option label="柱状图" value="bar" />
                    <el-option label="散点图" value="scatter" />
                    <el-option label="面积图" value="area" />
                  </el-select>
                </el-form-item>
                <el-form-item label="图表动画">
                  <el-switch
                    v-model="preferencesForm.display.chartAnimation"
                    @change="handlePreferencesChange"
                  />
                </el-form-item>
                <el-form-item label="小数位数">
                  <el-input-number
                    v-model="preferencesForm.display.decimalPlaces"
                    :min="0"
                    :max="6"
                    @change="handlePreferencesChange"
                  />
                </el-form-item>
              </el-form>
            </el-card>

            <!-- 语言设置 -->
            <el-card class="profile-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span>语言设置</span>
                </div>
              </template>
              <el-form label-width="120px">
                <el-form-item label="界面语言">
                  <el-select
                    v-model="preferencesForm.language"
                    placeholder="请选择语言"
                    @change="handlePreferencesChange"
                  >
                    <el-option label="简体中文" value="zh-CN" />
                    <el-option label="English" value="en-US" />
                  </el-select>
                </el-form-item>
                <el-form-item label="主题">
                  <el-radio-group
                    v-model="preferencesForm.theme"
                    @change="handlePreferencesChange"
                  >
                    <el-radio value="light">浅色</el-radio>
                    <el-radio value="dark">深色</el-radio>
                  </el-radio-group>
                </el-form-item>
              </el-form>
            </el-card>
          </div>
        </el-tab-pane>

        <!-- 操作历史标签页 -->
        <el-tab-pane label="操作历史" name="history">
          <div class="tab-content">
            <!-- 筛选区域 -->
            <el-card class="profile-card filter-card" shadow="hover">
              <el-form :inline="true" :model="historyFilter">
                <el-form-item label="时间范围">
                  <el-date-picker
                    v-model="historyFilter.dateRange"
                    type="daterange"
                    range-separator="至"
                    start-placeholder="开始日期"
                    end-placeholder="结束日期"
                    value-format="YYYY-MM-DD"
                    @change="handleHistoryFilter"
                  />
                </el-form-item>
                <el-form-item label="操作类型">
                  <el-select
                    v-model="historyFilter.type"
                    placeholder="全部类型"
                    clearable
                    @change="handleHistoryFilter"
                  >
                    <el-option label="登录" value="login" />
                    <el-option label="登出" value="logout" />
                    <el-option label="更新信息" value="update_profile" />
                    <el-option label="修改密码" value="change_password" />
                    <el-option label="更新设置" value="update_preferences" />
                    <el-option label="设备操作" value="device_operation" />
                    <el-option label="数据导出" value="data_export" />
                    <el-option label="配置变更" value="config_change" />
                  </el-select>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="handleHistoryFilter">
                    <el-icon><Search /></el-icon>
                    查询
                  </el-button>
                  <el-button @click="resetHistoryFilter">
                    <el-icon><Refresh /></el-icon>
                    重置
                  </el-button>
                </el-form-item>
              </el-form>
            </el-card>

            <!-- 操作历史列表 -->
            <el-card class="profile-card" shadow="hover">
              <template #header>
                <div class="card-header">
                  <span>操作记录</span>
                  <el-button
                    type="danger"
                    text
                    @click="handleClearHistory"
                  >
                    <el-icon><Delete /></el-icon>
                    清除历史
                  </el-button>
                </div>
              </template>
              <el-table
                v-loading="historyLoading"
                :data="userStore.operationHistory"
                stripe
                style="width: 100%"
              >
                <el-table-column prop="timestamp" label="时间" width="180">
                  <template #default="{ row }">
                    {{ formatDateTime(row.timestamp) }}
                  </template>
                </el-table-column>
                <el-table-column prop="type" label="操作类型" width="120">
                  <template #default="{ row }">
                    <el-tag :type="getOperationTagType(row.type)" size="small">
                      {{ getOperationTypeLabel(row.type) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="description" label="操作描述" min-width="200" />
                <el-table-column prop="metadata" label="详情" width="100">
                  <template #default="{ row }">
                    <el-button
                      v-if="row.metadata && Object.keys(row.metadata).length > 0"
                      type="primary"
                      text
                      size="small"
                      @click="showOperationDetail(row)"
                    >
                      查看详情
                    </el-button>
                    <span v-else class="text-muted">-</span>
                  </template>
                </el-table-column>
              </el-table>

              <!-- 分页 -->
              <div class="pagination-container">
                <el-pagination
                  v-model:current-page="historyPagination.page"
                  v-model:page-size="historyPagination.pageSize"
                  :page-sizes="[10, 20, 50, 100]"
                  :total="historyPagination.total"
                  layout="total, sizes, prev, pager, next, jumper"
                  @size-change="handlePageSizeChange"
                  @current-change="handlePageChange"
                />
              </div>
            </el-card>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 操作详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="操作详情"
      width="500px"
    >
      <el-descriptions :column="1" border>
        <el-descriptions-item
          v-for="(value, key) in currentOperationDetail"
          :key="key"
          :label="key"
        >
          {{ typeof value === 'object' ? JSON.stringify(value, null, 2) : value }}
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * @file Profile.vue
 * @path src/views/settings/
 * @description 个人中心页面，包含个人信息管理、偏好设置、操作历史三个标签页
 * @author Frontend Engineer Agent
 * @date 2026-03-07
 * @dependencies vue, element-plus, @/stores/user, @/composables/useErrorHandler
 */

import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  User,
  Edit,
  Upload,
  Search,
  Refresh,
  Delete
} from '@element-plus/icons-vue'
import { useUserStore, USER_ROLES, OPERATION_TYPES } from '@/stores/user'
import { useErrorHandler } from '@/composables/useErrorHandler'

// ==================== 组合式函数 ====================

const userStore = useUserStore()
const { handleError } = useErrorHandler()

// ==================== 响应式状态 ====================

/** 当前激活的标签页 */
const activeTab = ref('profile')

/** 是否正在编辑个人信息 */
const isEditingProfile = ref(false)

/** 个人信息表单 */
const profileForm = reactive({
  username: '',
  email: ''
})

/** 密码表单 */
const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

/** 偏好设置表单 */
const preferencesForm = reactive({
  notification: {
    enabled: true,
    sound: true,
    email: false,
    desktop: false
  },
  display: {
    refreshInterval: 1000,
    chartDefaultType: 'line',
    chartAnimation: true,
    decimalPlaces: 2
  },
  language: 'zh-CN',
  theme: 'light'
})

/** 操作历史筛选 */
const historyFilter = reactive({
  dateRange: null,
  type: null
})

/** 密码修改加载状态 */
const passwordLoading = ref(false)

/** 操作历史加载状态 */
const historyLoading = ref(false)

/** 操作详情对话框可见性 */
const detailDialogVisible = ref(false)

/** 当前操作详情 */
const currentOperationDetail = ref({})

/** 表单引用 */
const profileFormRef = ref(null)
const passwordFormRef = ref(null)
const avatarUploadRef = ref(null)

// ==================== 表单验证规则 ====================

/** 个人信息验证规则 */
const profileRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 20, message: '用户名长度在 2 到 20 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ]
}

/** 密码验证规则 */
const passwordRules = {
  oldPassword: [
    { required: true, message: '请输入当前密码', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度在 6 到 20 个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.newPassword) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// ==================== 计算属性 ====================

/** 操作历史分页 */
const historyPagination = computed(() => userStore.historyPagination)

// ==================== 生命周期 ====================

onMounted(() => {
  initProfileForm()
  initPreferencesForm()
})

// ==================== 方法 ====================

/**
 * 初始化个人信息表单
 */
function initProfileForm() {
  if (userStore.currentUser) {
    profileForm.username = userStore.currentUser.username || ''
    profileForm.email = userStore.currentUser.email || ''
  }
}

/**
 * 初始化偏好设置表单
 */
function initPreferencesForm() {
  Object.assign(preferencesForm.notification, userStore.preferences.notification)
  Object.assign(preferencesForm.display, userStore.preferences.display)
  preferencesForm.language = userStore.preferences.language
  preferencesForm.theme = userStore.preferences.theme
}

/**
 * 处理标签页切换
 *
 * @param {string} tabName - 标签页名称
 */
function handleTabChange(tabName) {
  if (tabName === 'history') {
    loadOperationHistory()
  }
}

/**
 * 开始编辑个人信息
 */
function startEditProfile() {
  isEditingProfile.value = true
  initProfileForm()
}

/**
 * 取消编辑个人信息
 */
function cancelEditProfile() {
  isEditingProfile.value = false
  initProfileForm()
  profileFormRef.value?.resetFields()
}

/**
 * 保存个人信息
 */
async function saveProfile() {
  try {
    const valid = await profileFormRef.value?.validate()
    if (!valid) return

    const result = await userStore.updateProfile({
      username: profileForm.username,
      email: profileForm.email
    })

    if (result.success) {
      ElMessage.success('个人信息更新成功')
      isEditingProfile.value = false
    } else {
      ElMessage.error(result.message || '更新失败')
    }
  } catch (error) {
    handleError(error, { action: '保存个人信息' })
  }
}

/**
 * 处理头像变更
 *
 * @param {Object} file - 上传的文件
 */
function handleAvatarChange(file) {
  const maxSize = 2 * 1024 * 1024 // 2MB
  if (file.raw.size > maxSize) {
    ElMessage.error('头像大小不能超过 2MB')
    return
  }

  // 这里可以调用上传接口
  ElMessage.info('头像上传功能开发中...')
}

/**
 * 修改密码
 */
async function handleChangePassword() {
  try {
    const valid = await passwordFormRef.value?.validate()
    if (!valid) return

    passwordLoading.value = true

    const result = await userStore.changePassword(
      passwordForm.oldPassword,
      passwordForm.newPassword
    )

    if (result.success) {
      ElMessage.success(result.message || '密码修改成功')
      // 清空表单
      passwordForm.oldPassword = ''
      passwordForm.newPassword = ''
      passwordForm.confirmPassword = ''
      passwordFormRef.value?.resetFields()
    } else {
      ElMessage.error(result.message || '密码修改失败')
    }
  } catch (error) {
    handleError(error, { action: '修改密码' })
  } finally {
    passwordLoading.value = false
  }
}

/**
 * 处理偏好设置变更
 */
async function handlePreferencesChange() {
  try {
    const result = await userStore.updatePreferences({
      notification: { ...preferencesForm.notification },
      display: { ...preferencesForm.display },
      language: preferencesForm.language,
      theme: preferencesForm.theme
    })

    if (result.success) {
      ElMessage.success('偏好设置已保存')
    } else {
      ElMessage.error(result.message || '保存失败')
    }
  } catch (error) {
    handleError(error, { action: '保存偏好设置' })
  }
}

/**
 * 加载操作历史
 */
async function loadOperationHistory() {
  historyLoading.value = true

  try {
    await userStore.fetchOperationHistory({
      page: historyPagination.value.page,
      pageSize: historyPagination.value.pageSize,
      type: historyFilter.type,
      startDate: historyFilter.dateRange?.[0],
      endDate: historyFilter.dateRange?.[1]
    })
  } catch (error) {
    handleError(error, { action: '加载操作历史' })
  } finally {
    historyLoading.value = false
  }
}

/**
 * 处理操作历史筛选
 */
function handleHistoryFilter() {
  historyPagination.value.page = 1
  loadOperationHistory()
}

/**
 * 重置操作历史筛选
 */
function resetHistoryFilter() {
  historyFilter.dateRange = null
  historyFilter.type = null
  historyPagination.value.page = 1
  loadOperationHistory()
}

/**
 * 处理分页大小变更
 *
 * @param {number} size - 每页数量
 */
function handlePageSizeChange(size) {
  historyPagination.value.pageSize = size
  loadOperationHistory()
}

/**
 * 处理页码变更
 *
 * @param {number} page - 页码
 */
function handlePageChange(page) {
  historyPagination.value.page = page
  loadOperationHistory()
}

/**
 * 清除操作历史
 */
async function handleClearHistory() {
  try {
    await ElMessageBox.confirm(
      '确定要清除所有操作历史吗？此操作不可恢复。',
      '确认清除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const success = await userStore.clearOperationHistory()

    if (success) {
      ElMessage.success('操作历史已清除')
    } else {
      ElMessage.error('清除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      handleError(error, { action: '清除操作历史' })
    }
  }
}

/**
 * 显示操作详情
 *
 * @param {Object} operation - 操作记录
 */
function showOperationDetail(operation) {
  currentOperationDetail.value = operation.metadata || {}
  detailDialogVisible.value = true
}

/**
 * 获取角色标签类型
 *
 * @param {string} role - 角色标识
 * @returns {string} 标签类型
 */
function getRoleTagType(role) {
  const typeMap = {
    [USER_ROLES.ADMIN]: 'danger',
    [USER_ROLES.OPERATOR]: 'primary',
    [USER_ROLES.VIEWER]: 'info'
  }
  return typeMap[role] || 'info'
}

/**
 * 获取操作类型标签类型
 *
 * @param {string} type - 操作类型
 * @returns {string} 标签类型
 */
function getOperationTagType(type) {
  const typeMap = {
    [OPERATION_TYPES.LOGIN]: 'success',
    [OPERATION_TYPES.LOGOUT]: 'info',
    [OPERATION_TYPES.UPDATE_PROFILE]: 'warning',
    [OPERATION_TYPES.CHANGE_PASSWORD]: 'danger',
    [OPERATION_TYPES.UPDATE_PREFERENCES]: '',
    [OPERATION_TYPES.DEVICE_OPERATION]: 'primary',
    [OPERATION_TYPES.DATA_EXPORT]: '',
    [OPERATION_TYPES.CONFIG_CHANGE]: 'warning'
  }
  return typeMap[type] || ''
}

/**
 * 获取操作类型标签
 *
 * @param {string} type - 操作类型
 * @returns {string} 操作类型标签
 */
function getOperationTypeLabel(type) {
  const labelMap = {
    [OPERATION_TYPES.LOGIN]: '登录',
    [OPERATION_TYPES.LOGOUT]: '登出',
    [OPERATION_TYPES.UPDATE_PROFILE]: '更新信息',
    [OPERATION_TYPES.CHANGE_PASSWORD]: '修改密码',
    [OPERATION_TYPES.UPDATE_PREFERENCES]: '更新设置',
    [OPERATION_TYPES.DEVICE_OPERATION]: '设备操作',
    [OPERATION_TYPES.DATA_EXPORT]: '数据导出',
    [OPERATION_TYPES.CONFIG_CHANGE]: '配置变更'
  }
  return labelMap[type] || type
}

/**
 * 格式化日期时间
 *
 * @param {string|Date} datetime - 日期时间
 * @returns {string} 格式化后的字符串
 */
function formatDateTime(datetime) {
  if (!datetime) return '-'
  const date = new Date(datetime)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 监听用户信息变化
watch(
  () => userStore.currentUser,
  (newUser) => {
    if (newUser) {
      initProfileForm()
    }
  },
  { deep: true }
)

// 监听偏好设置变化
watch(
  () => userStore.preferences,
  (newPreferences) => {
    initPreferencesForm()
  },
  { deep: true }
)
</script>

<style scoped lang="scss">
.settings-profile-page {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  background-color: var(--color-bg-secondary);
}

/* 页面头部 */
.page-header {
  background-color: var(--color-surface-primary);
  border-bottom: 1px solid var(--color-border-primary);
  padding: var(--spacing-6);
  margin-bottom: var(--spacing-4);
}

.header-content {
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
  font-size: 32px;
  color: var(--color-primary-500);
  padding: var(--spacing-3);
  background-color: var(--color-primary-50);
  border-radius: var(--radius-lg);
  transition: var(--transition-all);
}

.header-icon:hover {
  background-color: var(--color-primary-100);
  transform: scale(1.05);
}

.header-text {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.page-title {
  margin: 0;
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  line-height: var(--line-height-tight);
}

.page-subtitle {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

/* 内容区域 */
.profile-content {
  flex: 1;
  max-width: var(--content-max-width);
  margin: 0 auto;
  width: 100%;
  padding: 0 var(--spacing-6) var(--spacing-6);
}

.profile-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: var(--spacing-4);
    border-bottom: 2px solid var(--color-border-primary);
  }

  :deep(.el-tabs__nav-wrap)::after {
    display: none;
  }

  :deep(.el-tabs__item) {
    font-weight: var(--font-weight-medium);
    transition: var(--transition-all);
    padding: 0 var(--spacing-6);
    height: 48px;
    line-height: 48px;
  }

  :deep(.el-tabs__item:hover) {
    color: var(--color-primary-500);
  }

  :deep(.el-tabs__item.is-active) {
    color: var(--color-primary-500);
    font-weight: var(--font-weight-semibold);
  }

  :deep(.el-tabs__active-bar) {
    height: 3px;
    background-color: var(--color-primary-500);
  }
}

.tab-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-4);
}

/* 卡片样式 */
.profile-card {
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);

  :deep(.el-card__header) {
    padding: var(--spacing-4) var(--spacing-6);
    border-bottom: 1px solid var(--color-border-primary);
    background-color: var(--color-bg-secondary);
  }

  :deep(.el-card__body) {
    padding: var(--spacing-6);
  }
}

.profile-card:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--color-primary-200);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  font-size: var(--font-size-lg);
}

/* 头像区域 */
.avatar-section {
  display: flex;
  align-items: center;
}

.avatar-display {
  display: flex;
  align-items: center;
  gap: var(--spacing-6);
}

.user-avatar {
  background: linear-gradient(
    135deg,
    var(--color-primary-500) 0%,
    var(--color-accent-500) 100%
  );
  color: var(--color-text-inverse);
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  transition: var(--transition-transform);
}

.avatar-card:hover .user-avatar {
  transform: scale(1.05);
}

.avatar-info {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
}

.avatar-tip {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

/* 表单样式 */
.profile-card :deep(.el-form-item__label) {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
}

.profile-card :deep(.el-input__wrapper) {
  transition: var(--transition-all);
}

.profile-card :deep(.el-input__wrapper:focus-within) {
  box-shadow: 0 0 0 2px var(--color-primary-100);
}

.info-text {
  color: var(--color-text-primary);
  font-size: var(--font-size-sm);
}

.text-muted {
  color: var(--color-text-secondary);
}

/* 筛选卡片 */
.filter-card {
  :deep(.el-card__body) {
    padding: var(--spacing-4) var(--spacing-6);
  }
}

.filter-card :deep(.el-form-item) {
  margin-bottom: 0;
}

/* 表格样式 */
:deep(.el-table) {
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--color-border-primary);
}

:deep(.el-table th.el-table__cell) {
  background-color: var(--color-bg-secondary);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell) {
  background-color: var(--color-bg-tertiary);
}

:deep(.el-table__row) {
  transition: var(--transition-all);
}

:deep(.el-table__row:hover > td.el-table__cell) {
  background-color: var(--color-interactive-hover) !important;
}

/* 分页容器 */
.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--spacing-4);
  padding-top: var(--spacing-4);
  border-top: 1px solid var(--color-border-primary);
}

/* 对话框样式 */
:deep(.el-dialog) {
  border-radius: var(--radius-lg);
}

:deep(.el-dialog__header) {
  border-bottom: 1px solid var(--color-border-secondary);
  padding: var(--spacing-4) var(--spacing-6);
}

:deep(.el-dialog__body) {
  padding: var(--spacing-6);
}

:deep(.el-dialog__footer) {
  border-top: 1px solid var(--color-border-secondary);
  padding: var(--spacing-4) var(--spacing-6);
}

/* 按钮交互 */
.profile-card :deep(.el-button) {
  transition: var(--transition-all);
}

.profile-card :deep(.el-button:hover) {
  transform: translateY(-1px);
}

.profile-card :deep(.el-button--primary) {
  box-shadow: var(--shadow-glow-primary);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .page-header {
    padding: var(--spacing-4);
  }

  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-4);
  }

  .page-title {
    font-size: var(--font-size-xl);
  }

  .profile-content {
    padding: 0 var(--spacing-4) var(--spacing-4);
  }

  .avatar-display {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-4);
  }

  .profile-card {
    :deep(.el-card__header),
    :deep(.el-card__body) {
      padding: var(--spacing-4);
    }
  }

  .filter-card {
    :deep(.el-form-item) {
      margin-bottom: var(--spacing-3);
    }
  }

  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-2);
  }

  .pagination-container {
    flex-wrap: wrap;
    justify-content: center;
  }
}
</style>
