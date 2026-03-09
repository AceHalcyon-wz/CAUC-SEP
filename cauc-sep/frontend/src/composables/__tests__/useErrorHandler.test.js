/**
 * @file useErrorHandler.test.js
 * @path src/composables/__tests__/
 * @description 错误处理组合式函数测试
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useErrorHandler, setupGlobalErrorHandler } from '../useErrorHandler'
import { ERROR_TYPES, ERROR_SEVERITY } from '../../utils/errorSolutions'

describe('useErrorHandler', () => {
  let errorHandler

  beforeEach(() => {
    errorHandler = useErrorHandler({
      enableHistory: true,
      enableAutoReport: false,
      enableOfflineCache: false,
      enableErrorLog: false
    })
    // 清理历史记录，避免测试间干扰
    errorHandler.clearHistory()
  })

  describe('handleError', () => {
    it('应该正确处理Error对象', () => {
      const error = new Error('测试错误')
      const errorInfo = errorHandler.handleError(error, {
        component: 'TestComponent',
        action: 'testAction',
        userMessage: '这是一个测试错误'
      })

      expect(errorInfo).toBeDefined()
      expect(errorInfo.message).toBe('测试错误')
      expect(errorInfo.context.component).toBe('TestComponent')
      expect(errorInfo.context.action).toBe('testAction')
      expect(errorInfo.context.userMessage).toBe('这是一个测试错误')
      expect(errorInfo.id).toMatch(/^error_/)
      expect(errorInfo.timestamp).toBeDefined()
    })

    it('应该正确处理字符串错误', () => {
      const errorInfo = errorHandler.handleError('字符串错误消息', {
        component: 'TestComponent'
      })

      expect(errorInfo.message).toBe('字符串错误消息')
    })

    it('应该匹配解决方案', () => {
      const error = new Error('network error')
      const errorInfo = errorHandler.handleError(error)

      expect(errorInfo.solution).toBeDefined()
      expect(errorInfo.solution.type).toBe(ERROR_TYPES.NETWORK)
      expect(errorInfo.solution.title).toBe('网络连接错误')
    })

    it('应该添加错误到历史记录', () => {
      const error1 = new Error('错误1')
      const error2 = new Error('错误2')

      errorHandler.handleError(error1)
      errorHandler.handleError(error2)

      expect(errorHandler.errorHistory.value.length).toBe(2)
    })
  })

  describe('clearError', () => {
    it('应该清除当前错误', () => {
      const error = new Error('测试错误')
      errorHandler.handleError(error)

      expect(errorHandler.currentError.value).not.toBeNull()
      expect(errorHandler.errorVisible.value).toBe(true)

      errorHandler.clearError()

      expect(errorHandler.currentError.value).toBeNull()
      expect(errorHandler.errorVisible.value).toBe(false)
    })
  })

  describe('clearHistory', () => {
    it('应该清除错误历史', () => {
      errorHandler.handleError(new Error('错误1'))
      errorHandler.handleError(new Error('错误2'))

      expect(errorHandler.errorHistory.value.length).toBe(2)

      errorHandler.clearHistory()

      expect(errorHandler.errorHistory.value.length).toBe(0)
    })
  })

  describe('recordAction', () => {
    it('应该记录用户操作', () => {
      errorHandler.recordAction('点击按钮', { buttonId: 'test' })
      errorHandler.recordAction('提交表单', { formId: 'userForm' })

      // 操作历史应该在错误信息中可见
      const error = new Error('测试错误')
      const errorInfo = errorHandler.handleError(error)

      expect(errorInfo.userActions.length).toBeGreaterThanOrEqual(2)
    })
  })

  describe('generateReport', () => {
    it('应该生成错误报告', () => {
      const error = new Error('测试错误')
      errorHandler.handleError(error)

      const report = errorHandler.generateReport()

      expect(report).toBeDefined()
      expect(report.reportId).toBeDefined()
      expect(report.error.message).toBe('测试错误')
      expect(report.context).toBeDefined()
      expect(report.system).toBeDefined()
    })
  })

  describe('errorStats', () => {
    it('应该正确统计错误信息', () => {
      errorHandler.handleError(new Error('network error'))
      errorHandler.handleError(new Error('timeout error'))
      errorHandler.handleError(new Error('network error'))

      const stats = errorHandler.errorStats.value

      expect(stats.total).toBe(3)
      // 错误类型由解决方案匹配决定
      expect(Object.keys(stats.byType).length).toBeGreaterThan(0)
      expect(Object.keys(stats.bySeverity).length).toBeGreaterThan(0)
    })
  })
})

describe('setupGlobalErrorHandler', () => {
  it('应该注册全局错误处理器', () => {
    const onUnhandledError = vi.fn()
    const cleanup = setupGlobalErrorHandler({
      onUnhandledError
    })

    expect(cleanup).toBeDefined()
    expect(typeof cleanup).toBe('function')

    // 清理
    cleanup()
  })
})

describe('错误类型和严重程度', () => {
  it('应该正确导出错误类型', () => {
    expect(ERROR_TYPES.NETWORK).toBe('network')
    expect(ERROR_TYPES.PERMISSION).toBe('permission')
    expect(ERROR_TYPES.VALIDATION).toBe('validation')
    expect(ERROR_TYPES.DEVICE).toBe('device')
    expect(ERROR_TYPES.WEBSOCKET).toBe('websocket')
    expect(ERROR_TYPES.TIMEOUT).toBe('timeout')
    expect(ERROR_TYPES.DATABASE).toBe('database')
    expect(ERROR_TYPES.STORAGE).toBe('storage')
    expect(ERROR_TYPES.AUTHENTICATION).toBe('authentication')
    expect(ERROR_TYPES.RATE_LIMIT).toBe('rate_limit')
    expect(ERROR_TYPES.UNKNOWN).toBe('unknown')
  })

  it('应该正确导出严重程度', () => {
    expect(ERROR_SEVERITY.LOW).toBe('low')
    expect(ERROR_SEVERITY.MEDIUM).toBe('medium')
    expect(ERROR_SEVERITY.HIGH).toBe('high')
    expect(ERROR_SEVERITY.CRITICAL).toBe('critical')
  })
})
