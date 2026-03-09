<template>
  <div class="pr-path-config">
    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <div class="header-title">
            <el-icon class="header-icon">
              <Setting />
            </el-icon>
            <span>PR 路径配置</span>
          </div>
          <el-button 
            type="primary" 
            :loading="loading" 
            class="save-all-btn" 
            @click="saveAllPaths"
          >
            <el-icon><Check /></el-icon>
            保存所有配置
          </el-button>
        </div>
      </template>

      <el-alert
        v-if="motorStore.alarmMessage"
        :title="motorStore.alarmMessage"
        type="error"
        :closable="true"
        class="alarm-alert"
        @close="motorStore.clearAlarm()"
      />

      <el-tabs
        v-model="activePath"
        type="card"
        class="path-tabs"
      >
        <el-tab-pane 
          v-for="pathNum in 16" 
          :key="pathNum" 
          :label="`路径 ${pathNum}`" 
          :name="String(pathNum)"
        >
          <div class="path-config-form">
            <el-form 
              :model="pathConfigs[pathNum - 1]" 
              label-width="140px"
              :class="{ 'form-saving': motorStore.loading.prConfig }"
            >
              <el-row :gutter="24">
                <el-col :span="12">
                  <el-form-item
                    label="运行模式"
                    class="form-item"
                  >
                    <el-select 
                      v-model="pathConfigs[pathNum - 1].mode" 
                      placeholder="选择模式"
                      class="form-select"
                    >
                      <el-option
                        label="绝对位置"
                        :value="0"
                      />
                      <el-option
                        label="增量位置"
                        :value="1"
                      />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item
                    label="目标位置"
                    class="form-item"
                  >
                    <div class="input-with-unit">
                      <el-input-number 
                        v-model="pathConfigs[pathNum - 1].position_mm" 
                        :min="-50" 
                        :max="50" 
                        :step="0.1" 
                        :precision="2"
                        class="form-number"
                      />
                      <span class="unit-label">mm</span>
                    </div>
                  </el-form-item>
                </el-col>
              </el-row>
              
              <el-row :gutter="24">
                <el-col :span="12">
                  <el-form-item
                    label="速度"
                    class="form-item"
                  >
                    <div class="input-with-unit">
                      <el-input-number 
                        v-model="pathConfigs[pathNum - 1].velocity_mm_s" 
                        :min="0.1" 
                        :max="50" 
                        :step="0.1"
                        :precision="1"
                        class="form-number"
                      />
                      <span class="unit-label">mm/s</span>
                    </div>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item
                    label="加速时间"
                    class="form-item"
                  >
                    <div class="input-with-unit">
                      <el-input-number 
                        v-model="pathConfigs[pathNum - 1].accel_time" 
                        :min="1" 
                        :max="10000" 
                        :step="10"
                        class="form-number"
                      />
                      <span class="unit-label">ms</span>
                    </div>
                  </el-form-item>
                </el-col>
              </el-row>
              
              <el-row :gutter="24">
                <el-col :span="12">
                  <el-form-item
                    label="减速时间"
                    class="form-item"
                  >
                    <div class="input-with-unit">
                      <el-input-number 
                        v-model="pathConfigs[pathNum - 1].decel_time" 
                        :min="1" 
                        :max="10000" 
                        :step="10"
                        class="form-number"
                      />
                      <span class="unit-label">ms</span>
                    </div>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item
                    label="停留时间"
                    class="form-item"
                  >
                    <div class="input-with-unit">
                      <el-input-number 
                        v-model="pathConfigs[pathNum - 1].dwell_time" 
                        :min="0" 
                        :max="60000" 
                        :step="100"
                        class="form-number"
                      />
                      <span class="unit-label">ms</span>
                    </div>
                  </el-form-item>
                </el-col>
              </el-row>
              
              <el-row :gutter="24">
                <el-col :span="12">
                  <el-form-item
                    label="特殊参数"
                    class="form-item"
                  >
                    <el-input-number 
                      v-model="pathConfigs[pathNum - 1].special_param" 
                      :min="0" 
                      :max="65535" 
                      :step="1"
                      class="form-number"
                    />
                  </el-form-item>
                </el-col>
              </el-row>
              
              <el-form-item class="action-buttons">
                <el-button 
                  type="success" 
                  :loading="motorStore.loading.prConfig" 
                  class="action-btn"
                  @click="savePath(pathNum)"
                >
                  <el-icon><Check /></el-icon>
                  保存路径 {{ pathNum }}
                </el-button>
                <el-button 
                  type="primary" 
                  :loading="motorStore.loading.prTrigger" 
                  :disabled="!motorStore.canControl"
                  class="action-btn trigger-btn"
                  @click="triggerPath(pathNum)"
                >
                  <el-icon><VideoPlay /></el-icon>
                  触发路径 {{ pathNum }}
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
/**
 * @file PRPathConfig.vue
 * @path src/components/
 * @description PR路径配置组件，支持16条路径的参数配置与触发控制
 * @author Agent
 * @date 2024-03-07
 */

import { ref, reactive } from 'vue'
import { useMotorStore } from '../stores/motor'
import { ElMessage } from 'element-plus'

const motorStore = useMotorStore()

const activePath = ref('1')
const loading = ref(false)

const pathConfigs = reactive(
  Array.from({ length: 16 }, (_, i) => ({
    path_number: i + 1,
    mode: 0,
    position_mm: 0,
    velocity_mm_s: 10,
    accel_time: 100,
    decel_time: 100,
    dwell_time: 0,
    special_param: 0
  }))
)

/**
 * 保存单个路径配置
 * 
 * @param {number} pathNum - 路径编号
 */
async function savePath(pathNum) {
  const config = pathConfigs[pathNum - 1]
  const success = await motorStore.configurePRPath(config)
  if (success) {
    ElMessage.success(`路径 ${pathNum} 配置成功`)
  }
}

/**
 * 保存所有路径配置
 */
async function saveAllPaths() {
  loading.value = true
  let allSuccess = true
  for (let i = 1; i <= 16; i++) {
    const success = await motorStore.configurePRPath(pathConfigs[i - 1])
    if (!success) {
      allSuccess = false
    }
  }
  loading.value = false
  if (allSuccess) {
    ElMessage.success('所有路径配置成功')
  } else {
    ElMessage.warning('部分路径配置失败，请检查')
  }
}

/**
 * 触发路径执行
 * 
 * @param {number} pathNum - 路径编号
 */
async function triggerPath(pathNum) {
  const success = await motorStore.triggerPRPath(pathNum)
  if (success) {
    ElMessage.success(`路径 ${pathNum} 已触发`)
  }
}
</script>

<style scoped>
.pr-path-config {
  width: 100%;
}

.config-card {
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
}

.config-card:hover {
  box-shadow: var(--shadow-lg);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.header-icon {
  font-size: var(--font-size-xl);
  color: var(--color-primary-500);
}

.save-all-btn {
  transition: var(--transition-all);
}

.save-all-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.alarm-alert {
  margin-bottom: var(--spacing-4);
  border-radius: var(--radius-md);
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.path-tabs {
  margin-top: var(--spacing-2);
}

.path-config-form {
  padding: var(--spacing-4);
  background-color: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  transition: var(--transition-all);
}

.form-item {
  margin-bottom: var(--spacing-4);
  transition: var(--transition-all);
}

.form-item:hover {
  background-color: var(--color-interactive-hover);
  border-radius: var(--radius-sm);
}

.form-select,
.form-number {
  width: 100%;
  transition: var(--transition-all);
}

.input-with-unit {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.input-with-unit .form-number {
  flex: 1;
}

.unit-label {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  min-width: 40px;
  padding: var(--spacing-1) var(--spacing-2);
  background-color: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
  text-align: center;
}

.action-buttons {
  margin-top: var(--spacing-6);
  padding-top: var(--spacing-4);
  border-top: 1px solid var(--color-border-primary);
}

.action-btn {
  min-width: 140px;
  transition: var(--transition-all);
}

.action-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.trigger-btn {
  margin-left: var(--spacing-3);
}

/* 表单保存动画 */
.form-saving {
  opacity: 0.7;
  pointer-events: none;
}

/* Element Plus 样式覆盖 */
:deep(.el-tabs__header) {
  margin-bottom: var(--spacing-4);
}

:deep(.el-tabs__item) {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-sm);
  padding: 0 var(--spacing-4);
  transition: var(--transition-all);
}

:deep(.el-tabs__item.is-active) {
  background-color: var(--color-primary-500);
  color: var(--color-text-inverse);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
}

:deep(.el-tabs__item:hover) {
  color: var(--color-primary-500);
}

:deep(.el-form-item__label) {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
}

:deep(.el-input-number) {
  width: 100%;
}

:deep(.el-input-number .el-input__wrapper) {
  background-color: var(--color-surface-primary);
  transition: var(--transition-all);
}

:deep(.el-input-number .el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--color-primary-400) inset;
}

:deep(.el-input-number .el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 2px var(--color-primary-500) inset;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .card-header {
    flex-direction: column;
    gap: var(--spacing-3);
    align-items: flex-start;
  }
  
  .save-all-btn {
    width: 100%;
  }
  
  .action-buttons {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-2);
  }
  
  .action-btn {
    width: 100%;
    margin-left: 0;
  }
  
  .trigger-btn {
    margin-left: 0;
  }
}
</style>
