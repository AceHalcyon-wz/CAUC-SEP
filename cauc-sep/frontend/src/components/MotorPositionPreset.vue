<template>
  <el-card class="position-preset-card">
    <template #header>
      <div class="card-header">
        <div class="header-left">
          <el-icon class="header-icon">
            <Collection />
          </el-icon>
          <span class="header-title">位置预设</span>
        </div>
        <el-button
          type="primary"
          size="small"
          :icon="Plus"
          @click="showAddDialog"
        >
          添加预设
        </el-button>
      </div>
    </template>

    <div class="preset-content">
      <!-- 预设列表 -->
      <div
        v-if="motorStore.positionPresets.length > 0"
        class="preset-list"
      >
        <div
          v-for="preset in motorStore.positionPresets"
          :key="preset.id"
          class="preset-item"
          :class="{ 'preset-active': activePresetId === preset.id }"
        >
          <div class="preset-info">
            <div class="preset-header">
              <el-icon class="preset-icon">
                <Location />
              </el-icon>
              <span class="preset-name">{{ preset.name }}</span>
            </div>
            <div class="preset-details">
              <span class="detail-item">
                <el-icon><Position /></el-icon>
                {{ preset.position }} mm
              </span>
              <span class="detail-item">
                <el-icon><Odometer /></el-icon>
                {{ preset.velocity }} mm/s
              </span>
            </div>
            <div
              v-if="preset.description"
              class="preset-description"
            >
              {{ preset.description }}
            </div>
          </div>

          <div class="preset-actions">
            <el-button
              type="success"
              size="small"
              :disabled="!motorStore.canControl"
              @click="applyPreset(preset.id)"
            >
              <el-icon><VideoPlay /></el-icon>
              应用
            </el-button>
            <el-button
              type="primary"
              size="small"
              @click="editPreset(preset)"
            >
              <el-icon><Edit /></el-icon>
            </el-button>
            <el-popconfirm
              title="确定要删除此预设吗？"
              confirm-button-text="确定"
              cancel-button-text="取消"
              @confirm="deletePreset(preset.id)"
            >
              <template #reference>
                <el-button
                  type="danger"
                  size="small"
                >
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-popconfirm>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <el-empty
        v-else
        description="暂无位置预设"
        :image-size="120"
        class="empty-state"
      >
        <el-button
          type="primary"
          @click="showAddDialog"
        >
          添加第一个预设
        </el-button>
      </el-empty>
    </div>

    <!-- 添加/编辑预设对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? '编辑预设' : '添加预设'"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="presetFormRef"
        :model="presetForm"
        :rules="presetRules"
        label-width="100px"
      >
        <el-form-item
          label="预设名称"
          prop="name"
        >
          <el-input
            v-model="presetForm.name"
            placeholder="请输入预设名称"
            maxlength="20"
            show-word-limit
          />
        </el-form-item>

        <el-form-item
          label="目标位置"
          prop="position"
        >
          <el-input-number
            v-model="presetForm.position"
            :min="motorStore.limits.negative_mm"
            :max="motorStore.limits.positive_mm"
            :precision="3"
            :step="0.1"
            style="width: 100%"
          />
          <span class="unit-label">mm</span>
        </el-form-item>

        <el-form-item
          label="运动速度"
          prop="velocity"
        >
          <el-input-number
            v-model="presetForm.velocity"
            :min="1"
            :max="50"
            :precision="1"
            :step="1"
            style="width: 100%"
          />
          <span class="unit-label">mm/s</span>
        </el-form-item>

        <el-form-item label="描述">
          <el-input
            v-model="presetForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入预设描述（可选）"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="当前位置">
          <el-tag
            type="info"
            size="large"
          >
            {{ motorStore.positionMm.toFixed(3) }} mm
          </el-tag>
          <el-button
            type="text"
            size="small"
            @click="useCurrentPosition"
          >
            使用当前位置
          </el-button>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">
          取消
        </el-button>
        <el-button
          type="primary"
          :loading="saving"
          @click="savePreset"
        >
          {{ isEditing ? '保存' : '添加' }}
        </el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
/**
 * @file MotorPositionPreset.vue
 * @path src/components/
 * @description 电机位置预设管理组件，支持添加、编辑、删除和应用位置预设
 * @author Agent
 * @date 2024-03-07
 */

import { ref, reactive } from 'vue'
import { useMotorStore } from '../stores/motor'
import { ElMessage } from 'element-plus'
import {
  Plus,
  Edit,
  Delete,
  VideoPlay,
  Collection,
  Location,
  Position,
  Odometer
} from '@element-plus/icons-vue'

const motorStore = useMotorStore()

// ============ 响应式状态 ============

/** 对话框显示状态 */
const dialogVisible = ref(false)

/** 是否为编辑模式 */
const isEditing = ref(false)

/** 当前编辑的预设ID */
const editingId = ref(null)

/** 保存中状态 */
const saving = ref(false)

/** 当前激活的预设ID */
const activePresetId = ref(null)

/** 表单引用 */
const presetFormRef = ref(null)

/** 预设表单数据 */
const presetForm = reactive({
  name: '',
  position: 0,
  velocity: 10,
  description: ''
})

/** 表单验证规则 */
const presetRules = {
  name: [
    { required: true, message: '请输入预设名称', trigger: 'blur' },
    { min: 1, max: 20, message: '长度在 1 到 20 个字符', trigger: 'blur' }
  ],
  position: [
    { required: true, message: '请输入目标位置', trigger: 'blur' }
  ],
  velocity: [
    { required: true, message: '请输入运动速度', trigger: 'blur' }
  ]
}

// ============ 方法 ============

/**
 * 显示添加预设对话框
 */
function showAddDialog() {
  isEditing.value = false
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

/**
 * 编辑预设
 * 
 * @param {Object} preset - 预设对象
 */
function editPreset(preset) {
  isEditing.value = true
  editingId.value = preset.id
  presetForm.name = preset.name
  presetForm.position = preset.position
  presetForm.velocity = preset.velocity
  presetForm.description = preset.description || ''
  dialogVisible.value = true
}

/**
 * 使用当前位置
 */
function useCurrentPosition() {
  presetForm.position = motorStore.positionMm
}

/**
 * 重置表单
 */
function resetForm() {
  presetForm.name = ''
  presetForm.position = 0
  presetForm.velocity = 10
  presetForm.description = ''
  presetFormRef.value?.clearValidate()
}

/**
 * 保存预设
 */
async function savePreset() {
  if (!presetFormRef.value) return

  await presetFormRef.value.validate(async (valid) => {
    if (!valid) return

    saving.value = true

    try {
      let success
      if (isEditing.value) {
        success = motorStore.updatePositionPreset(editingId.value, {
          name: presetForm.name,
          position: presetForm.position,
          velocity: presetForm.velocity,
          description: presetForm.description
        })
        if (success) {
          ElMessage.success('预设更新成功')
        }
      } else {
        success = motorStore.addPositionPreset({
          name: presetForm.name,
          position: presetForm.position,
          velocity: presetForm.velocity,
          description: presetForm.description
        })
        if (success) {
          ElMessage.success('预设添加成功')
        }
      }

      if (success) {
        dialogVisible.value = false
        resetForm()
      } else {
        ElMessage.error('操作失败')
      }
    } catch (error) {
      ElMessage.error('操作失败: ' + error.message)
    } finally {
      saving.value = false
    }
  })
}

/**
 * 删除预设
 * 
 * @param {number} id - 预设ID
 */
function deletePreset(id) {
  const success = motorStore.deletePositionPreset(id)
  if (success) {
    ElMessage.success('预设删除成功')
    if (activePresetId.value === id) {
      activePresetId.value = null
    }
  } else {
    ElMessage.error('删除失败')
  }
}

/**
 * 应用预设
 * 
 * @param {number} id - 预设ID
 */
async function applyPreset(id) {
  activePresetId.value = id
  const success = await motorStore.applyPositionPreset(id)
  
  if (success) {
    ElMessage.success('运动指令已发送')
  } else {
    activePresetId.value = null
  }
}
</script>

<style scoped>
.position-preset-card {
  margin-bottom: var(--spacing-6);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
}

.position-preset-card:hover {
  box-shadow: var(--shadow-md);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.header-icon {
  font-size: var(--font-size-lg);
  color: var(--color-primary-500);
}

.header-title {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.preset-content {
  padding: var(--spacing-2) 0;
}

.preset-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
}

.preset-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-4);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
}

.preset-item:hover {
  border-color: var(--color-primary-300);
  box-shadow: var(--shadow-sm);
}

.preset-item.preset-active {
  border-color: var(--color-success-500);
  background-color: var(--color-success-light);
  box-shadow: var(--shadow-glow-success);
}

.preset-info {
  flex: 1;
}

.preset-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-2);
}

.preset-icon {
  font-size: var(--font-size-lg);
  color: var(--color-primary-500);
}

.preset-name {
  font-weight: var(--font-weight-semibold);
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
}

.preset-details {
  display: flex;
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-2);
}

.detail-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.detail-item .el-icon {
  font-size: var(--font-size-sm);
}

.preset-description {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-top: var(--spacing-1);
}

.preset-actions {
  display: flex;
  gap: var(--spacing-2);
}

.empty-state {
  padding: var(--spacing-8) 0;
}

.unit-label {
  margin-left: var(--spacing-2);
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

/* 响应式优化 */
@media (max-width: 768px) {
  .preset-item {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-3);
  }

  .preset-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .preset-details {
    flex-direction: column;
    gap: var(--spacing-1);
  }
}
</style>
