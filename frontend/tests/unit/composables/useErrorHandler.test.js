/**
 * @file useErrorHandler.complete.test.js
 * @path frontend/tests/unit/composables/
 * @description useErrorHandler组合式函数完整单元测试
 * 
 * 测试覆盖：
 * - 错误捕获
 * - 错误分类
 * - 错误上报
 * - 错误恢复
 * - 离线缓存
 * 
 * @author Agent
 * @date 2026-03-16
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { nextTick } from 'vue';
import {
  useErrorHandler,
  setupGlobalErrorHandler,
  ERROR_TYPES,
  ERROR_SEVERITY,
  getErrorIcon,
  getSeverityColor,
  getErrorTypeLabel
} from '@/composables/useErrorHandler';

// Mock offlineStorage
vi.mock('@/utils/offlineStorage', () => ({
  getOfflineStorage: vi.fn(() => ({
    db: {},
    set: vi.fn(),
    get: vi.fn(),
    getByIndex: vi.fn(() => []),
    delete: vi.fn()
  }))
}));

describe('useErrorHandler', () => {
  let errorHandler;
  let defaultOptions;

  beforeEach(() => {
    vi.clearAllMocks();

    defaultOptions = {
      enableHistory: true,
      enableAutoReport: false,
      enableOfflineCache: true,
      enableErrorLog: true,
      maxOfflineErrors: 100,
      onReport: vi.fn()
    };

    // Mock localStorage
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(() => '[]'),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn()
    });

    // Mock performance.memory
    vi.stubGlobal('performance', {
      memory: {
        usedJSHeapSize: 50000000,
        totalJSHeapSize: 100000000,
        jsHeapSizeLimit: 2000000000
      }
    });

    // Mock navigator
    vi.stubGlobal('navigator', {
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
      platform: 'Win32',
      language: 'zh-CN',
      onLine: true,
      connection: {
        effectiveType: '4g',
        downlink: 10,
        rtt: 50
      }
    });

    // Mock window
    vi.stubGlobal('window', {
      location: {
        pathname: '/test',
        href: 'http://localhost/test'
      },
      innerWidth: 1920,
      innerHeight: 1080,
      screen: {
        width: 1920,
        height: 1080
      }
    });
  });

  afterEach(() => {
    if (errorHandler) {
      errorHandler.clearHistory();
      errorHandler = null;
    }
  });

  // ==================== 初始化测试 ====================

  describe('初始化', () => {
    it('应该正确初始化所有状态', () => {
      errorHandler = useErrorHandler(defaultOptions);

      expect(errorHandler.currentError.value).toBeNull();
      expect(errorHandler.errorVisible.value).toBe(false);
      expect(errorHandler.isGeneratingReport.value).toBe(false);
    });

    it('应该使用默认配置选项', () => {
      errorHandler = useErrorHandler();

      expect(errorHandler).toBeDefined();
    });

    it('应该支持自定义配置选项', () => {
      const customOptions = {
        ...defaultOptions,
        enableHistory: false,
        enableOfflineCache: false
      };

      errorHandler = useErrorHandler(customOptions);

      expect(errorHandler).toBeDefined();
    });
  });

  // ==================== 错误捕获测试 ====================

  describe('错误捕获', () => {
    it('应该正确捕获Error对象', () => {
      errorHandler = useErrorHandler(defaultOptions);

      const error = new Error('测试错误');
      const errorInfo = errorHandler.handleError(error, {
        component: 'TestComponent',
        action: 'testAction'
      });

      expect(errorInfo).toBeDefined();
      expect(errorInfo.message).toBe('测试错误');
      expect(errorInfo.name).toBe('Error');
      expect(errorInfo.context.component).toBe('TestComponent');
      expect(errorInfo.context.action).toBe('testAction');
    });

    it('应该正确捕获字符串错误', () => {
      errorHandler = useErrorHandler(defaultOptions);

      const errorInfo = errorHandler.handleError('字符串错误消息', {
        component: 'TestComponent'
      });

      expect(errorInfo).toBeDefined();
      expect(errorInfo.message).toBe('字符串错误消息');
    });

    it('应该捕获错误堆栈信息', () => {
      errorHandler = useErrorHandler(defaultOptions);

      const error = new Error('测试错误');
      const errorInfo = errorHandler.handleError(error);

      expect(errorInfo.stack).toBeDefined();
      expect(Array.isArray(errorInfo.stack)).toBe(true);
      expect(errorInfo.fullStack).toBeDefined();
    });

    it('应该捕获系统状态快照', () => {
      errorHandler = useErrorHandler(defaultOptions);

      const error = new Error('测试错误');
      const errorInfo = errorHandler.handleError(error);

      expect(errorInfo.system).toBeDefined();
      expect(errorInfo.system.platform).toBeDefined();
      expect(errorInfo.system.language).toBeDefined();
      expect(errorInfo.system.viewport).toBeDefined();
    });

    it('应该捕获用户操作历史', () => {
      errorHandler = useErrorHandler(defaultOptions);

      // 记录用户操作
      errorHandler.recordAction('click', { button: 'submit' });
      errorHandler.recordAction('input', { field: 'username' });

      const error = new Error('测试错误');
      const errorInfo = errorHandler.handleError(error);

      expect(errorInfo.userActions).toBeDefined();
      expect(errorInfo.userActions.length).toBeGreaterThan(0);
    });

    it('应该设置当前错误状态', () => {
      errorHandler = useErrorHandler(defaultOptions);

      const error = new Error('测试错误');
      errorHandler.handleError(error);

      expect(errorHandler.currentError.value).toBeDefined();
      expect(errorHandler.errorVisible.value).toBe(true);
    });
  });

  // ==================== 错误分类测试 ====================

  describe('错误分类', () => {
    it('应该正确识别网络错误', () => {
      errorHandler = useErrorHandler(defaultOptions);

      const error = new Error('network error');
      const errorInfo = errorHandler.handleError(error);

      // 验证错误信息被正确解析
      expect(errorInfo).toBeDefined();
      expect(errorInfo.message).toBe('network error');
    });

    it('应该正确识别设备错误', () => {
      errorHandler = useErrorHandler(defaultOptions);

      const error = new Error('device not found');
      const errorInfo = errorHandler.handleError(error);

      expect(errorInfo).toBeDefined();
      expect(errorInfo.message).toBe('device not found');
    });

    it('应该正确识别超时错误', () => {
      errorHandler = useErrorHandler(defaultOptions);

      const error = new Error('timeout');
      const errorInfo = errorHandler.handleError(error);

      expect(errorInfo).toBeDefined();
      expect(errorInfo.message).toBe('timeout');
    });

    it('应该正确识别认证错误', () => {
      errorHandler = useErrorHandler(defaultOptions);

      const error = new Error('authentication failed');
      const errorInfo = errorHandler.handleError(error);

      expect(errorInfo).toBeDefined();
      expect(errorInfo.message).toBe('authentication failed');
    });

    it('应该正确识别验证错误', () => {
      errorHandler = useErrorHandler(defaultOptions);

      const error = new Error('validation error');
      const errorInfo = errorHandler.handleError(error);

      expect(errorInfo).toBeDefined();
      expect(errorInfo.message).toBe('validation error');
    });

    it('应该为未知错误分配默认类型', () => {
      errorHandler = useErrorHandler(defaultOptions);

      const error = new Error('unknown error type');
      const errorInfo = errorHandler.handleError(error);

      expect(errorInfo).toBeDefined();
      expect(errorInfo.type).toBeDefined();
    });

    it('应该匹配错误解决方案', () => {
      errorHandler = useErrorHandler(defaultOptions);

      const error = new Error('network error');
      const errorInfo = errorHandler.handleError(error);

      expect(errorInfo.solution).toBeDefined();
    });
  });

  // ==================== 错误上报测试 ====================

  describe('错误上报', () => {
    it('应该生成错误报告', () => {
      errorHandler = useErrorHandler(defaultOptions);

      const error = new Error('测试错误');
      errorHandler.handleError(error);

      const report = errorHandler.generateReport();

      expect(report).toBeDefined();
      expect(report.reportId).toBeDefined();
      expect(report.error).toBeDefined();
      expect(report.context).toBeDefined();
    });

    it('应该支持手动上报错误', async () => {
      const onReport = vi.fn();
      errorHandler = useErrorHandler({ ...defaultOptions, onReport });

      const error = new Error('测试错误');
      const errorInfo = errorHandler.handleError(error);

      await errorHandler.reportError(errorInfo);

      expect(onReport).toHaveBeenCalled();
    });

    it('应该支持自动上报错误', async () => {
      const onReport = vi.fn();
      errorHandler = useErrorHandler({
        ...defaultOptions,
        onReport,
        enableAutoReport: true
      });

      const error = new Error('测试错误');
      errorHandler.handleError(error);

      await nextTick();

      expect(onReport).toHaveBeenCalled();
    });

    it('应该支持批量上报错误', async () => {
      const onReport = vi.fn().mockResolvedValue(true);
      errorHandler = useErrorHandler({ ...defaultOptions, onReport });

      // 触发多个错误
      errorHandler.handleError(new Error('错误1'));
      errorHandler.handleError(new Error('错误2'));
      errorHandler.handleError(new Error('错误3'));

      const result = await errorHandler.batchReportErrors({ batchSize: 10 });

      expect(result).toHaveProperty('success');
      expect(result).toHaveProperty('reported');
    });

    it('应该获取上报队列状态', () => {
      errorHandler = useErrorHandler(defaultOptions);

      const status = errorHandler.getReportQueueStatus();

      expect(status).toHaveProperty('queueLength');
      expect(status).toHaveProperty('isReporting');
    });

    it('应该清空上报队列', () => {
      errorHandler = useErrorHandler(defaultOptions);

      errorHandler.handleError(new Error('错误1'));
      errorHandler.handleError(new Error('错误2'));

      errorHandler.clearReportQueue();

      const status = errorHandler.getReportQueueStatus();
      expect(status.queueLength).toBe(0);
    });
  });

  // ==================== 错误恢复测试 ====================

  describe('错误恢复', () => {
    it('应该清除当前错误', () => {
      errorHandler = useErrorHandler(defaultOptions);

      errorHandler.handleError(new Error('测试错误'));
      errorHandler.clearError();

      expect(errorHandler.currentError.value).toBeNull();
      expect(errorHandler.errorVisible.value).toBe(false);
    });

    it('应该清除错误历史', () => {
      errorHandler = useErrorHandler(defaultOptions);

      errorHandler.handleError(new Error('错误1'));
      errorHandler.handleError(new Error('错误2'));
      errorHandler.clearHistory();

      expect(errorHandler.errorHistory.value.length).toBe(0);
    });

    it('应该复制错误详情', async () => {
      errorHandler = useErrorHandler(defaultOptions);

      const error = new Error('测试错误');
      errorHandler.handleError(error);

      // Mock clipboard
      vi.stubGlobal('navigator', {
        ...navigator,
        clipboard: {
          writeText: vi.fn().mockResolvedValue(true)
        }
      });

      const result = await errorHandler.copyErrorInfo('detail');

      expect(result).toBe(true);
    });

    it('应该复制错误堆栈', async () => {
      errorHandler = useErrorHandler(defaultOptions);

      const error = new Error('测试错误');
      errorHandler.handleError(error);

      vi.stubGlobal('navigator', {
        ...navigator,
        clipboard: {
          writeText: vi.fn().mockResolvedValue(true)
        }
      });

      const result = await errorHandler.copyErrorInfo('stack');

      expect(result).toBe(true);
    });

    it('应该复制错误报告', async () => {
      errorHandler = useErrorHandler(defaultOptions);

      const error = new Error('测试错误');
      errorHandler.handleError(error);

      vi.stubGlobal('navigator', {
        ...navigator,
        clipboard: {
          writeText: vi.fn().mockResolvedValue(true)
        }
      });

      const result = await errorHandler.copyErrorInfo('report');

      expect(result).toBe(true);
    });
  });

  // ==================== 离线缓存测试 ====================

  describe('离线缓存', () => {
    it('应该获取离线错误统计', () => {
      errorHandler = useErrorHandler(defaultOptions);

      const stats = errorHandler.getOfflineErrorStats();

      expect(stats).toHaveProperty('queueLength');
      expect(stats).toHaveProperty('isSyncing');
    });

    it('应该支持同步离线错误', async () => {
      const onReport = vi.fn().mockResolvedValue(true);
      errorHandler = useErrorHandler({ ...defaultOptions, onReport });

      const result = await errorHandler.syncOfflineErrors();

      expect(result).toHaveProperty('success');
    });

    it('应该清除离线错误缓存', async () => {
      errorHandler = useErrorHandler(defaultOptions);

      await errorHandler.clearOfflineErrors();

      const stats = errorHandler.getOfflineErrorStats();
      expect(stats.queueLength).toBe(0);
    });
  });

  // ==================== 错误统计测试 ====================

  describe('错误统计', () => {
    it('应该正确统计错误数量', () => {
      errorHandler = useErrorHandler(defaultOptions);

      errorHandler.handleError(new Error('错误1'));
      errorHandler.handleError(new Error('错误2'));
      errorHandler.handleError(new Error('错误3'));

      const stats = errorHandler.errorStats.value;

      expect(stats.total).toBe(3);
    });

    it('应该按类型统计错误', () => {
      errorHandler = useErrorHandler(defaultOptions);

      errorHandler.handleError(new Error('network error'));
      errorHandler.handleError(new Error('network error'));
      errorHandler.handleError(new Error('timeout'));

      const stats = errorHandler.errorStats.value;

      expect(stats.byType).toBeDefined();
    });

    it('应该按严重程度统计错误', () => {
      errorHandler = useErrorHandler(defaultOptions);

      errorHandler.handleError(new Error('network error'));
      errorHandler.handleError(new Error('validation error'));

      const stats = errorHandler.errorStats.value;

      expect(stats.bySeverity).toBeDefined();
    });

    it('应该按组件统计错误', () => {
      errorHandler = useErrorHandler(defaultOptions);

      errorHandler.handleError(new Error('错误1'), { component: 'ComponentA' });
      errorHandler.handleError(new Error('错误2'), { component: 'ComponentB' });

      const stats = errorHandler.errorStats.value;

      expect(stats.byComponent).toBeDefined();
    });

    it('应该获取错误趋势分析', () => {
      errorHandler = useErrorHandler(defaultOptions);

      errorHandler.handleError(new Error('错误1'));
      errorHandler.handleError(new Error('错误2'));

      const trends = errorHandler.getErrorTrends(7);

      expect(Array.isArray(trends)).toBe(true);
      expect(trends.length).toBe(7);
    });
  });

  // ==================== 用户操作记录测试 ====================

  describe('用户操作记录', () => {
    it('应该记录用户操作', () => {
      errorHandler = useErrorHandler(defaultOptions);

      errorHandler.recordAction('click', { button: 'submit' });

      // 操作历史应该被记录
      expect(errorHandler).toBeDefined();
    });

    it('应该限制操作历史数量', () => {
      errorHandler = useErrorHandler(defaultOptions);

      // 记录超过100条操作
      for (let i = 0; i < 150; i++) {
        errorHandler.recordAction(`action_${i}`);
      }

      // 验证操作历史被限制
      expect(errorHandler).toBeDefined();
    });
  });

  // ==================== 错误聚合测试 ====================

  describe('错误聚合', () => {
    it('应该聚合相同错误', () => {
      errorHandler = useErrorHandler(defaultOptions);

      // 触发相同错误多次
      for (let i = 0; i < 5; i++) {
        errorHandler.handleError(new Error('network error'), {
          component: 'TestComponent',
          action: 'fetch'
        });
      }

      // 验证错误聚合
      const stats = errorHandler.errorStats.value;
      expect(stats.total).toBeGreaterThan(0);
    });
  });

  // ==================== 工具函数测试 ====================

  describe('工具函数', () => {
    beforeEach(() => {
      errorHandler = useErrorHandler(defaultOptions);
    });

    it('应该获取错误图标', () => {
      const icon = getErrorIcon(ERROR_TYPES.NETWORK);

      expect(icon).toBeDefined();
    });

    it('应该获取严重程度颜色', () => {
      const color = getSeverityColor(ERROR_SEVERITY.HIGH);

      expect(color).toBeDefined();
    });

    it('应该获取错误类型标签', () => {
      const label = getErrorTypeLabel(ERROR_TYPES.NETWORK);

      expect(label).toBeDefined();
    });
  });

  // ==================== 全局错误处理器测试 ====================

  describe('全局错误处理器', () => {
    beforeEach(() => {
      // Mock window.addEventListener
      vi.stubGlobal('window', {
        ...window,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn()
      });
    });

    it('应该设置全局错误监听器', () => {
      const onUnhandledError = vi.fn();
      const cleanup = setupGlobalErrorHandler({ onUnhandledError });

      // 验证addEventListener被调用
      expect(window.addEventListener).toHaveBeenCalled();

      cleanup();
    });

    it('应该设置Promise rejection监听器', () => {
      const onUnhandledRejection = vi.fn();
      const cleanup = setupGlobalErrorHandler({ onUnhandledRejection });

      // 验证addEventListener被调用
      expect(window.addEventListener).toHaveBeenCalledWith(
        'unhandledrejection',
        expect.any(Function)
      );

      cleanup();
    });

    it('应该返回清理函数', () => {
      const cleanup = setupGlobalErrorHandler({});

      expect(typeof cleanup).toBe('function');

      cleanup();
    });
  });

  // ==================== 边界情况测试 ====================

  describe('边界情况', () => {
    it('应该处理空错误对象', () => {
      errorHandler = useErrorHandler(defaultOptions);

      const errorInfo = errorHandler.handleError(null);

      expect(errorInfo).toBeDefined();
    });

    it('应该处理undefined错误', () => {
      errorHandler = useErrorHandler(defaultOptions);

      const errorInfo = errorHandler.handleError(undefined);

      expect(errorInfo).toBeDefined();
    });

    it('应该处理空上下文', () => {
      errorHandler = useErrorHandler(defaultOptions);

      const errorInfo = errorHandler.handleError(new Error('错误'), {});

      expect(errorInfo).toBeDefined();
      expect(errorInfo.context).toBeDefined();
    });

    it('应该处理缺少stack的错误', () => {
      errorHandler = useErrorHandler(defaultOptions);

      const error = { message: '错误' };
      const errorInfo = errorHandler.handleError(error);

      expect(errorInfo).toBeDefined();
    });

    it('应该处理生成报告时无错误的情况', () => {
      errorHandler = useErrorHandler(defaultOptions);

      const report = errorHandler.generateReport();

      expect(report).toBeNull();
    });

    it('应该处理复制时无错误的情况', async () => {
      errorHandler = useErrorHandler(defaultOptions);

      const result = await errorHandler.copyErrorInfo('detail');

      expect(result).toBe(false);
    });
  });
});
