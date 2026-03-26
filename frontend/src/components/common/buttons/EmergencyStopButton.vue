<script setup lang="ts">
/**
 * @file EmergencyStopButton.vue
 * @path src/components/common/buttons/EmergencyStopButton.vue
 * @description 紧急停止按钮组件，全局安全组件，最高优先级执行
 * @author Agent
 * @date 2026-03-25
 * @safety: 急停指令必须优先执行，跳过请求队列，保障最高优先级
 */

import { ref, computed } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { emergencyStopAll } from '@/api/device-api'

interface Props {
  size?: 'small' | 'default' | 'large'
  disabled?: boolean
  showConfirm?: boolean
  confirmMessage?: string
}

const props = withDefaults(defineProps<Props>(), {
  size: 'default',
  disabled: false,
  showConfirm: true,
  confirmMessage: '确定要执行紧急停止吗？所有设备将立即停止运行！',
})

const emit = defineEmits<{
  (e: 'stop-success'): void
  (e: 'stop-error', error: Error): void
}>()

const isLoading = ref(false)

const buttonSize = computed(() => {
  const sizeMap = {
    small: { width: '80px', height: '40px', fontSize: '14px' },
    default: { width: '120px', height: '60px', fontSize: '18px' },
    large: { width: '160px', height: '80px', fontSize: '22px' },
  }
  return sizeMap[props.size]
})

async function handleEmergencyStop(): Promise<void> {
  if (props.showConfirm) {
    try {
      await ElMessageBox.confirm(props.confirmMessage, '紧急停止确认', {
        confirmButtonText: '确认急停',
        cancelButtonText: '取消',
        type: 'warning',
        customClass: 'emergency-stop-confirm-dialog',
      })
    } catch {
      return
    }
  }

  isLoading.value = true
  try {
    await emergencyStopAll()
    ElMessage.success('紧急停止指令已下发')
    emit('stop-success')
  } catch (error) {
    ElMessage.error(`紧急停止失败: ${(error as Error).message || '未知错误'}`)
    emit('stop-error', error as Error)
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <el-button
    class="emergency-stop-button"
    :style="buttonSize"
    type="danger"
    :loading="isLoading"
    :disabled="disabled"
    @click="handleEmergencyStop"
  >
    <span class="stop-icon">⏻</span>
    <span class="stop-text">紧急停止</span>
  </el-button>
</template>

<style scoped lang="scss">
.emergency-stop-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: linear-gradient(145deg, #ff4444, #cc0000) !important;
  border: 4px solid #8b0000 !important;
  box-shadow:
    0 4px 15px rgba(255, 0, 0, 0.4),
    inset 0 2px 4px rgba(255, 255, 255, 0.2);
  transition: all 0.2s ease;
  cursor: pointer;

  &:hover:not(:disabled) {
    transform: scale(1.05);
    box-shadow:
      0 6px 20px rgba(255, 0, 0, 0.6),
      inset 0 2px 4px rgba(255, 255, 255, 0.3);
  }

  &:active:not(:disabled) {
    transform: scale(0.95);
    box-shadow:
      0 2px 10px rgba(255, 0, 0, 0.4),
      inset 0 2px 4px rgba(0, 0, 0, 0.2);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .stop-icon {
    font-size: v-bind('buttonSize.fontSize');
    margin-bottom: 4px;
  }

  .stop-text {
    font-size: calc(v-bind('buttonSize.fontSize') * 0.7);
    font-weight: bold;
    color: #fff;
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
  }
}
</style>

<style lang="scss">
.emergency-stop-confirm-dialog {
  .el-message-box__header {
    background-color: #fef0f0;
  }
  .el-message-box__message {
    color: #f56c6c;
    font-weight: bold;
  }
  .el-button--primary {
    background-color: #f56c6c;
    border-color: #f56c6c;
  }
}
</style>
