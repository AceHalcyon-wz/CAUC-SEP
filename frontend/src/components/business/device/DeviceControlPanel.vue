<script setup lang="ts">
/**
 * @file DeviceControlPanel.vue
 * @path src/components/business/device/DeviceControlPanel.vue
 * @description 设备控制面板业务组件
 * @author Agent
 * @date 2026-03-25
 * @safety: 控制操作需包含二次确认，异常时需显示明确错误信息
 */

import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { GlassCard } from '@/components/common/cards'
import { LoadingOverlay } from '@/components/common/feedback'
import { EmergencyStopButton } from '@/components/common/buttons'
import type { DeviceInfo, DeviceControlAction } from '@/types/device'

interface Props {
  device: DeviceInfo
  actions: DeviceControlAction[]
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
})

const emit = defineEmits<{
  (e: 'action', actionId: string, params: Record<string, unknown>): void
  (e: 'emergency-stop'): void
}>()

const loadingActions = ref<Set<string>>(new Set())

function isActionLoading(actionId: string): boolean {
  return loadingActions.value.has(actionId)
}

async function handleAction(action: DeviceControlAction): Promise<void> {
  if (props.disabled || loadingActions.value.has(action.id)) return

  if (action.requireConfirm) {
    try {
      await ElMessageBox.confirm(action.confirmMessage || `确定要执行 ${action.name} 吗？`, '操作确认', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: action.dangerous ? 'warning' : 'info',
      })
    } catch {
      return
    }
  }

  loadingActions.value.add(action.id)
  try {
    emit('action', action.id, action.params || {})
    ElMessage.success(`${action.name} 执行成功`)
  } catch (error) {
    ElMessage.error(`${action.name} 执行失败: ${(error as Error).message || '未知错误'}`)
  } finally {
    loadingActions.value.delete(action.id)
  }
}

function handleEmergencyStop(): void {
  emit('emergency-stop')
}
</script>

<template>
  <GlassCard class="device-control-panel">
    <template #header>
      <div class="panel-header">
        <h4 class="header-title">{{ device.name }} 控制</h4>
        <EmergencyStopButton size="small" :show-confirm="true" @stop-success="handleEmergencyStop" />
      </div>
    </template>

    <div class="action-grid">
      <el-button
        v-for="action in actions"
        :key="action.id"
        :type="action.type || 'default'"
        :loading="isActionLoading(action.id)"
        :disabled="disabled || action.disabled"
        :danger="action.dangerous"
        @click="handleAction(action)"
      >
        <span v-if="action.icon" class="action-icon">{{ action.icon }}</span>
        {{ action.name }}
      </el-button>
    </div>

    <slot />

    <LoadingOverlay :visible="loadingActions.size > 0" text="执行中..." />
  </GlassCard>
</template>

<style scoped lang="scss">
.device-control-panel {
  position: relative;

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;

    .header-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--color-text-primary);
      margin: 0;
    }
  }

  .action-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 12px;

    .el-button {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;

      .action-icon {
        font-size: 16px;
      }
    }
  }
}
</style>
