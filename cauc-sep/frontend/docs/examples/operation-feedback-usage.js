/**
 * @file operation-feedback-usage.js
 * @path docs/examples/
 * @description 操作反馈系统使用示例
 * @author Agent
 * @date 2024-03-07
 */

import { useOperationFeedback, createStepProgress, delay } from '../composables/useOperationFeedback'
import { OPERATION_TYPE } from '../stores/operation'

/**
 * 示例1: 基本操作执行
 */
export async function exampleBasicOperation() {
  const { execute } = useOperationFeedback()

  const result = await execute({
    type: OPERATION_TYPE.DEVICE_CONNECT,
    title: '连接电机设备',
    description: '正在建立与电机控制器的连接',
    steps: ['初始化连接', '验证设备', '加载配置'],
    action: async (updateProgress) => {
      updateProgress(0, 0, '正在初始化连接...')
      await delay(500)
      
      updateProgress(33, 1, '正在验证设备身份...')
      await delay(500)
      
      updateProgress(66, 2, '正在加载设备配置...')
      await delay(500)
      
      updateProgress(100, 2, '连接成功')
      
      return { deviceId: 'motor-001', status: 'connected' }
    },
    cancellable: true
  })

  if (result.success) {
    console.log('操作成功:', result.result)
  } else {
    console.error('操作失败:', result.error)
  }
}

/**
 * 示例2: 带撤销功能的操作
 */
export async function exampleUndoableOperation() {
  const { executeWithUndo } = useOperationFeedback()

  const result = await executeWithUndo({
    title: '删除配置文件',
    action: async () => {
      await delay(300)
      return { deletedFile: 'config.json' }
    },
    undo: async (metadata) => {
      console.log('撤销删除:', metadata)
      await delay(300)
      return { restoredFile: 'config.json' }
    },
    undoWindow: 15000
  })

  return result
}

/**
 * 示例3: 批量操作
 */
export async function exampleBatchOperation() {
  const { executeBatch } = useOperationFeedback()

  const devices = [
    { id: 'motor-001', name: '电机1' },
    { id: 'motor-002', name: '电机2' },
    { id: 'motor-003', name: '电机3' }
  ]

  const result = await executeBatch({
    title: '批量连接设备',
    items: devices,
    processItem: async (device, _index) => {
      await delay(500)
      console.log(`连接设备 ${device.name}...`)
      return { connected: true, deviceId: device.id }
    },
    onProgress: (completed, total, percentage) => {
      console.log(`进度: ${completed}/${total} (${percentage}%)`)
    },
    onItemComplete: (device, _result, _index) => {
      console.log(`设备 ${device.name} 连接成功`)
    },
    onItemError: (device, error, _index) => {
      console.error(`设备 ${device.name} 连接失败:`, error)
    },
    continueOnError: true
  })

  console.log('批量操作结果:', result)
  return result
}

/**
 * 示例4: 使用进度更新器
 */
export async function exampleWithStepProgress() {
  const { execute } = useOperationFeedback()

  const result = await execute({
    title: '数据导出',
    steps: ['查询数据', '格式转换', '生成文件', '下载'],
    action: async (updateProgress) => {
      const nextStep = createStepProgress(4, updateProgress)
      
      nextStep('正在查询数据库...')
      await delay(500)
      
      nextStep('正在转换数据格式...')
      await delay(500)
      
      nextStep('正在生成Excel文件...')
      await delay(500)
      
      nextStep('正在准备下载...')
      await delay(500)
      
      return { fileUrl: '/downloads/data.xlsx' }
    }
  })

  return result
}

/**
 * 示例5: 错误处理和重试
 */
export async function exampleWithErrorHandling() {
  const { execute, showError } = useOperationFeedback()

  let attemptCount = 0

  const result = await execute({
    title: '上传数据',
    action: async (updateProgress) => {
      attemptCount++
      updateProgress(0, 0, `正在上传 (尝试 ${attemptCount})...`)
      
      if (attemptCount === 1) {
        await delay(500)
        throw new Error('网络连接超时')
      }
      
      await delay(500)
      updateProgress(100, 0, '上传成功')
      
      return { uploaded: true }
    }
  })

  if (!result.success) {
    showError({
      title: '上传失败',
      error: result.error,
      retryable: true
    })
  }

  return result
}

/**
 * 示例6: 手动显示通知
 */
export function exampleManualNotifications() {
  const { showSuccess, showError, showWarning } = useOperationFeedback()

  showSuccess({
    title: '保存成功',
    message: '配置已保存到本地',
    duration: 3000
  })

  showError({
    title: '连接失败',
    error: new Error('无法连接到服务器'),
    retryable: true
  })

  showWarning({
    title: '注意',
    message: '设备温度过高，请注意散热'
  })
}

/**
 * 示例7: 包装异步函数
 */
export function exampleWrapAsync() {
  const { wrapAsync } = useOperationFeedback()

  async function fetchData(params) {
    const response = await fetch('/api/data', {
      method: 'POST',
      body: JSON.stringify(params)
    })
    return response.json()
  }

  const safeFetchData = wrapAsync(fetchData, {
    title: '获取数据',
    showErrorNotification: true
  })

  async function loadData() {
    const result = await safeFetchData({ id: 123 })
    if (result.success) {
      console.log('数据:', result.result)
    }
  }

  return { safeFetchData, loadData }
}

export default {
  exampleBasicOperation,
  exampleUndoableOperation,
  exampleBatchOperation,
  exampleWithStepProgress,
  exampleWithErrorHandling,
  exampleManualNotifications,
  exampleWrapAsync,
}
