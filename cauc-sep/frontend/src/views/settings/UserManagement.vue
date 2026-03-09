/**
 * @file UserManagement.vue
 * @path src/views/settings/
 * @description 用户管理页面，提供用户列表、用户编辑、权限设置等功能
 * @author Frontend Engineer Agent
 * @date 2026-03-08
 * @dependencies vue, element-plus, @element-plus/icons-vue, stores/user
 */

<template>
  <div class="user-management-page">
    <!-- 页面头部 -->
    <el-row class="page-header">
      <el-col :span="24">
        <div class="header-content">
          <div class="header-left">
            <el-icon class="header-icon">
              <UserFilled />
            </el-icon>
            <div class="header-text">
              <h1 class="page-title">
                用户管理
              </h1>
              <p class="page-subtitle">
                管理系统用户账户与权限设置
              </p>
            </div>
          </div>
          <div class="header-right">
            <el-button
              type="primary"
              class="action-btn"
              @click="handleAddUser"
            >
              <el-icon><Plus /></el-icon>
              添加用户
            </el-button>
            <el-button
              class="action-btn"
              @click="handleRefresh"
            >
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 主内容区域 -->
    <div class="management-content">
      <!-- 搜索和筛选区域 -->
      <el-card
        class="filter-card"
        shadow="hover"
      >
        <el-form
          :inline="true"
          :model="filterForm"
          class="filter-form"
        >
          <el-form-item label="用户名">
            <el-input
              v-model="filterForm.username"
              placeholder="请输入用户名"
              clearable
              @keyup.enter="handleSearch"
            />
          </el-form-item>
          <el-form-item label="角色">
            <el-select
              v-model="filterForm.role"
              placeholder="全部角色"
              clearable
            >
              <el-option
                label="管理员"
                value="admin"
              />
              <el-option
                label="操作员"
                value="operator"
              />
              <el-option
                label="观察者"
                value="viewer"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select
              v-model="filterForm.status"
              placeholder="全部状态"
              clearable
            >
              <el-option
                label="启用"
                value="active"
              />
              <el-option
                label="禁用"
                value="inactive"
              />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button
              type="primary"
              @click="handleSearch"
            >
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
            <el-button @click="handleResetFilter">
              <el-icon><RefreshLeft /></el-icon>
              重置
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 用户列表 -->
      <el-card
        class="user-list-card"
        shadow="hover"
      >
        <template #header>
          <div class="card-header">
            <div class="header-title">
              <span>用户列表</span>
              <el-tag
                type="info"
                size="small"
              >
                共 {{ pagination.total }} 个用户
              </el-tag>
            </div>
            <div class="header-actions">
              <el-button
                type="danger"
                text
                :disabled="selectedUsers.length === 0"
                @click="handleBatchDelete"
              >
                <el-icon><Delete /></el-icon>
                批量删除 ({{ selectedUsers.length }})
              </el-button>
            </div>
          </div>
        </template>

        <el-table
          ref="userTableRef"
          v-loading="loading"
          :data="userList"
          stripe
          @selection-change="handleSelectionChange"
        >
          <el-table-column
            type="selection"
            width="55"
          />

          <el-table-column
            prop="username"
            label="用户名"
            min-width="120"
          >
            <template #default="{ row }">
              <div class="user-info">
                <el-avatar
                  :size="32"
                  class="user-avatar"
                >
                  {{ getAvatarText(row.username) }}
                </el-avatar>
                <div class="user-detail">
                  <span class="username">{{ row.username }}</span>
                  <span class="user-id">ID: {{ row.id }}</span>
                </div>
              </div>
            </template>
          </el-table-column>

          <el-table-column
            prop="email"
            label="邮箱"
            min-width="180"
          >
            <template #default="{ row }">
              <span class="email-text">{{ row.email || '-' }}</span>
            </template>
          </el-table-column>

          <el-table-column
            prop="role"
            label="角色"
            width="120"
          >
            <template #default="{ row }">
              <el-tag
                :type="getRoleTagType(row.role)"
                size="small"
              >
                {{ getRoleLabel(row.role) }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column
            prop="status"
            label="状态"
            width="100"
          >
            <template #default="{ row }">
              <el-switch
                v-model="row.status"
                active-value="active"
                inactive-value="inactive"
                @change="handleStatusChange(row)"
              />
            </template>
          </el-table-column>

          <el-table-column
            prop="lastLogin"
            label="最后登录"
            width="160"
          >
            <template #default="{ row }">
              <span class="time-text">{{ formatDateTime(row.lastLogin) }}</span>
            </template>
          </el-table-column>

          <el-table-column
            prop="createdAt"
            label="创建时间"
            width="160"
          >
            <template #default="{ row }">
              <span class="time-text">{{ formatDateTime(row.createdAt) }}</span>
            </template>
          </el-table-column>

          <el-table-column
            label="操作"
            width="180"
            fixed="right"
          >
            <template #default="{ row }">
              <el-button
                type="primary"
                link
                size="small"
                @click="handleEditUser(row)"
              >
                编辑
              </el-button>
              <el-button
                type="primary"
                link
                size="small"
                @click="handleEditPermissions(row)"
              >
                权限
              </el-button>
              <el-button
                type="danger"
                link
                size="small"
                :disabled="row.role === 'admin'"
                @click="handleDeleteUser(row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="pagination.total"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handlePageSizeChange"
            @current-change="handlePageChange"
          />
        </div>
      </el-card>
    </div>

    <!-- 用户编辑对话框 -->
    <el-dialog
      v-model="userDialogVisible"
      :title="isEditing ? '编辑用户' : '添加用户'"
      width="600px"
      destroy-on-close
      class="user-dialog"
    >
      <el-form
        ref="userFormRef"
        :model="userForm"
        :rules="userRules"
        label-width="100px"
        class="user-form"
      >
        <el-form-item
          label="用户名"
          prop="username"
        >
          <el-input
            v-model="userForm.username"
            placeholder="请输入用户名"
            :disabled="isEditing"
          />
        </el-form-item>

        <el-form-item
          label="邮箱"
          prop="email"
        >
          <el-input
            v-model="userForm.email"
            placeholder="请输入邮箱"
          />
        </el-form-item>

        <el-form-item
          v-if="!isEditing"
          label="密码"
          prop="password"
        >
          <el-input
            v-model="userForm.password"
            type="password"
            placeholder="请输入密码"
            show-password
          />
        </el-form-item>

        <el-form-item
          v-if="!isEditing"
          label="确认密码"
          prop="confirmPassword"
        >
          <el-input
            v-model="userForm.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            show-password
          />
        </el-form-item>

        <el-form-item
          label="角色"
          prop="role"
        >
          <el-select
            v-model="userForm.role"
            placeholder="请选择角色"
          >
            <el-option
              label="管理员"
              value="admin"
            />
            <el-option
              label="操作员"
              value="operator"
            />
            <el-option
              label="观察者"
              value="viewer"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          label="状态"
          prop="status"
        >
          <el-radio-group v-model="userForm.status">
            <el-radio value="active">
              启用
            </el-radio>
            <el-radio value="inactive">
              禁用
            </el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="备注">
          <el-input
            v-model="userForm.remark"
            type="textarea"
            :rows="3"
            placeholder="请输入备注"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="userDialogVisible = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="saving"
          @click="handleSaveUser"
        >
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 权限设置对话框 -->
    <el-dialog
      v-model="permissionDialogVisible"
      title="权限设置"
      width="700px"
      destroy-on-close
      class="permission-dialog"
    >
      <div class="permission-header">
        <span class="user-name">用户: {{ currentUser?.username }}</span>
        <el-tag
          :type="getRoleTagType(currentUser?.role)"
          size="small"
        >
          {{ getRoleLabel(currentUser?.role) }}
        </el-tag>
      </div>

      <el-divider />

      <div class="permission-content">
        <div
          v-for="group in permissionGroups"
          :key="group.key"
          class="permission-group"
        >
          <h4 class="group-title">
            {{ group.label }}
          </h4>
          <div class="permission-list">
            <el-checkbox
              v-for="permission in group.permissions"
              :key="permission.key"
              v-model="permission.checked"
              :label="permission.key"
              :disabled="isPermissionDisabled(permission.key)"
            >
              {{ permission.label }}
            </el-checkbox>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="permissionDialogVisible = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="savingPermissions"
          @click="handleSavePermissions"
        >
          保存权限
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * @file UserManagement.vue
 * @path src/views/settings/
 * @description 用户管理页面，提供用户列表、用户编辑、权限设置等功能
 * @author Frontend Engineer Agent
 * @date 2026-03-08
 */

import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  UserFilled,
  Plus,
  Refresh,
  Search,
  RefreshLeft,
  Delete
} from '@element-plus/icons-vue'
import { useUserStore, USER_ROLES } from '@/stores/user'

// ==================== Store ====================

const userStore = useUserStore()

// ==================== 响应式状态 ====================

/** 加载状态 */
const loading = ref(false)

/** 保存状态 */
const saving = ref(false)

/** 保存权限状态 */
const savingPermissions = ref(false)

/** 用户列表 */
const userList = ref([])

/** 选中的用户 */
const selectedUsers = ref([])

/** 表格引用 */
const userTableRef = ref(null)

/** 表单引用 */
const userFormRef = ref(null)

/** 用户对话框可见性 */
const userDialogVisible = ref(false)

/** 权限对话框可见性 */
const permissionDialogVisible = ref(false)

/** 是否编辑模式 */
const isEditing = ref(false)

/** 当前编辑的用户 */
const currentUser = ref(null)

/** 分页信息 */
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

/** 筛选表单 */
const filterForm = reactive({
  username: '',
  role: '',
  status: ''
})

/** 用户表单 */
const userForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
  role: 'operator',
  status: 'active',
  remark: ''
})

/** 用户表单验证规则 */
const userRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 20, message: '用户名长度在 2 到 20 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 20, message: '密码长度在 6 到 20 个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== userForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'change' }
  ]
}

/** 权限组 */
const permissionGroups = ref([
  {
    key: 'experiment',
    label: '实验控制',
    permissions: [
      { key: 'experiment.control', label: '设备控制', checked: false },
      { key: 'experiment.config', label: '参数配置', checked: false },
      { key: 'experiment.start', label: '启动实验', checked: false },
      { key: 'experiment.stop', label: '停止实验', checked: false }
    ]
  },
  {
    key: 'data',
    label: '数据管理',
    permissions: [
      { key: 'data.view', label: '查看数据', checked: false },
      { key: 'data.export', label: '导出数据', checked: false },
      { key: 'data.delete', label: '删除数据', checked: false },
      { key: 'data.analysis', label: '数据分析', checked: false }
    ]
  },
  {
    key: 'system',
    label: '系统管理',
    permissions: [
      { key: 'system.config', label: '系统配置', checked: false },
      { key: 'system.user', label: '用户管理', checked: false },
      { key: 'system.log', label: '日志查看', checked: false },
      { key: 'system.backup', label: '数据备份', checked: false }
    ]
  }
])

// ==================== 生命周期 ====================

onMounted(() => {
  loadUserList()
})

// ==================== 方法 ====================

/**
 * 加载用户列表
 */
async function loadUserList() {
  loading.value = true
  try {
    // 模拟数据
    userList.value = [
      {
        id: '1',
        username: 'admin',
        email: 'admin@cauc.edu.cn',
        role: 'admin',
        status: 'active',
        lastLogin: new Date().toISOString(),
        createdAt: '2024-01-01T00:00:00.000Z'
      },
      {
        id: '2',
        username: 'operator1',
        email: 'operator1@cauc.edu.cn',
        role: 'operator',
        status: 'active',
        lastLogin: new Date(Date.now() - 86400000).toISOString(),
        createdAt: '2024-02-15T00:00:00.000Z'
      },
      {
        id: '3',
        username: 'viewer1',
        email: 'viewer1@cauc.edu.cn',
        role: 'viewer',
        status: 'active',
        lastLogin: null,
        createdAt: '2024-03-01T00:00:00.000Z'
      }
    ]
    pagination.total = userList.value.length
  } catch (error) {
    console.error('[UserManagement] Failed to load users:', error)
    ElMessage.error('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

/**
 * 搜索用户
 */
function handleSearch() {
  pagination.page = 1
  loadUserList()
}

/**
 * 重置筛选
 */
function handleResetFilter() {
  filterForm.username = ''
  filterForm.role = ''
  filterForm.status = ''
  pagination.page = 1
  loadUserList()
}

/**
 * 刷新列表
 */
function handleRefresh() {
  loadUserList()
}

/**
 * 添加用户
 */
function handleAddUser() {
  isEditing.value = false
  currentUser.value = null
  resetUserForm()
  userDialogVisible.value = true
}

/**
 * 编辑用户
 */
function handleEditUser(user) {
  isEditing.value = true
  currentUser.value = user
  Object.assign(userForm, {
    username: user.username,
    email: user.email,
    role: user.role,
    status: user.status,
    remark: user.remark || ''
  })
  userDialogVisible.value = true
}

/**
 * 保存用户
 */
async function handleSaveUser() {
  try {
    const valid = await userFormRef.value?.validate()
    if (!valid) return

    saving.value = true

    // 模拟保存
    await new Promise(resolve => setTimeout(resolve, 500))

    ElMessage.success(isEditing.value ? '用户更新成功' : '用户创建成功')
    userDialogVisible.value = false
    loadUserList()
  } catch (error) {
    console.error('[UserManagement] Failed to save user:', error)
  } finally {
    saving.value = false
  }
}

/**
 * 删除用户
 */
async function handleDeleteUser(user) {
  try {
    await ElMessageBox.confirm(
      `确定要删除用户 "${user.username}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    // 模拟删除
    await new Promise(resolve => setTimeout(resolve, 300))

    ElMessage.success('用户删除成功')
    loadUserList()
  } catch (error) {
    // 用户取消
  }
}

/**
 * 批量删除
 */
async function handleBatchDelete() {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedUsers.value.length} 个用户吗？此操作不可恢复。`,
      '确认批量删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    ElMessage.success('批量删除成功')
    selectedUsers.value = []
    loadUserList()
  } catch (error) {
    // 用户取消
  }
}

/**
 * 编辑权限
 */
function handleEditPermissions(user) {
  currentUser.value = user
  permissionDialogVisible.value = true
}

/**
 * 保存权限
 */
async function handleSavePermissions() {
  savingPermissions.value = true
  try {
    await new Promise(resolve => setTimeout(resolve, 500))
    ElMessage.success('权限保存成功')
    permissionDialogVisible.value = false
  } finally {
    savingPermissions.value = false
  }
}

/**
 * 状态变更
 */
async function handleStatusChange(user) {
  try {
    await new Promise(resolve => setTimeout(resolve, 300))
    ElMessage.success(`用户 ${user.username} 已${user.status === 'active' ? '启用' : '禁用'}`)
  } catch (error) {
    // 恢复原状态
    user.status = user.status === 'active' ? 'inactive' : 'active'
  }
}

/**
 * 选择变更
 */
function handleSelectionChange(selection) {
  selectedUsers.value = selection
}

/**
 * 页码变更
 */
function handlePageChange(page) {
  pagination.page = page
  loadUserList()
}

/**
 * 每页数量变更
 */
function handlePageSizeChange(size) {
  pagination.pageSize = size
  loadUserList()
}

/**
 * 重置用户表单
 */
function resetUserForm() {
  Object.assign(userForm, {
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    role: 'operator',
    status: 'active',
    remark: ''
  })
  userFormRef.value?.resetFields()
}

// ==================== 辅助方法 ====================

/**
 * 获取头像文本
 */
function getAvatarText(username) {
  return username?.substring(0, 2).toUpperCase() || 'U'
}

/**
 * 获取角色标签类型
 */
function getRoleTagType(role) {
  const types = {
    admin: 'danger',
    operator: 'primary',
    viewer: 'info'
  }
  return types[role] || 'info'
}

/**
 * 获取角色标签
 */
function getRoleLabel(role) {
  const labels = {
    admin: '管理员',
    operator: '操作员',
    viewer: '观察者'
  }
  return labels[role] || role
}

/**
 * 格式化日期时间
 */
function formatDateTime(datetime) {
  if (!datetime) return '-'
  const date = new Date(datetime)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

/**
 * 权限是否禁用
 */
function isPermissionDisabled(key) {
  if (currentUser.value?.role === 'admin') {
    return true // 管理员拥有所有权限
  }
  return false
}
</script>

<style scoped lang="scss">
.user-management-page {
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

.header-right {
  display: flex;
  gap: var(--spacing-3);
}

.action-btn {
  transition: var(--transition-all);
  border: 1px solid var(--color-border-primary);
}

.action-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--color-primary-300);
}

.action-btn:active:not(:disabled) {
  transform: translateY(0);
}

.header-right .el-button--primary {
  box-shadow: var(--shadow-glow-primary);
}

/* 内容区域 */
.management-content {
  flex: 1;
  max-width: var(--content-max-width);
  margin: 0 auto;
  width: 100%;
  padding: var(--spacing-6);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6);
}

/* 筛选卡片 */
.filter-card {
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);

  &:hover {
    box-shadow: var(--shadow-sm);
    border-color: var(--color-primary-200);
  }

  :deep(.el-card__body) {
    padding: var(--spacing-4) var(--spacing-6);
  }
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-2);
}

.filter-form :deep(.el-form-item__label) {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
}

.filter-form :deep(.el-button) {
  transition: var(--transition-all);
}

.filter-form :deep(.el-button:hover) {
  transform: translateY(-1px);
}

/* 用户列表卡片 */
.user-list-card {
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);

  &:hover {
    box-shadow: var(--shadow-md);
  }

  :deep(.el-card__header) {
    background-color: var(--color-bg-secondary);
    border-bottom: 1px solid var(--color-border-primary);
    padding: var(--spacing-4) var(--spacing-6);
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.header-actions :deep(.el-button) {
  transition: var(--transition-all);
}

.header-actions :deep(.el-button:hover:not(:disabled)) {
  transform: translateY(-1px);
}

/* 用户信息 */
.user-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.user-avatar {
  background: linear-gradient(
    135deg,
    var(--color-primary-500) 0%,
    var(--color-accent-500) 100%
  );
  color: var(--color-text-inverse);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
  transition: var(--transition-transform);
}

.user-info:hover .user-avatar {
  transform: scale(1.1);
}

.user-detail {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.username {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.user-id {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-family-mono);
}

.email-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.time-text {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-family: var(--font-family-mono);
}

/* 表格样式 */
:deep(.el-table) {
  border-radius: var(--radius-md);
  overflow: hidden;
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

:deep(.el-table__fixed-right) {
  box-shadow: -4px 0 8px rgba(0, 0, 0, 0.05);
}

:deep(.el-button.is-link) {
  transition: var(--transition-all);
}

:deep(.el-button.is-link:hover) {
  transform: translateX(2px);
}

/* 分页 */
.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--spacing-4);
  padding-top: var(--spacing-4);
  border-top: 1px solid var(--color-border-primary);
}

/* 对话框 */
.user-dialog,
.permission-dialog {
  border-radius: var(--radius-lg);
}

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
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-3);
}

.user-form {
  padding: var(--spacing-4) 0;
}

.user-form :deep(.el-form-item__label) {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
}

.user-form :deep(.el-input__wrapper) {
  transition: var(--transition-all);
}

.user-form :deep(.el-input__wrapper:focus-within) {
  box-shadow: 0 0 0 2px var(--color-primary-100);
}

.permission-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.user-name {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.permission-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-6);
}

.permission-group {
  padding: var(--spacing-4);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-secondary);
  transition: var(--transition-all);
}

.permission-group:hover {
  border-color: var(--color-primary-200);
  box-shadow: var(--shadow-sm);
}

.group-title {
  margin: 0 0 var(--spacing-3) 0;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.permission-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-4);
}

.permission-list :deep(.el-checkbox) {
  transition: var(--transition-all);
}

.permission-list :deep(.el-checkbox:hover) {
  transform: translateX(2px);
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

  .header-right {
    width: 100%;
    justify-content: flex-end;
    flex-wrap: wrap;
  }

  .action-btn {
    flex: 1;
    min-width: 100px;
  }

  .page-title {
    font-size: var(--font-size-xl);
  }

  .management-content {
    padding: var(--spacing-4);
  }

  .filter-form {
    :deep(.el-form-item) {
      margin-bottom: var(--spacing-3);
      width: 100%;
    }
  }

  .user-list-card {
    :deep(.el-card__header),
    :deep(.el-card__body) {
      padding: var(--spacing-4);
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

  .permission-group {
    padding: var(--spacing-3);
  }

  .permission-list {
    gap: var(--spacing-2);
  }
}
</style>
