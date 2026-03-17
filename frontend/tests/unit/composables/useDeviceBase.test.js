/**
 * @file useDeviceBase.complete.test.js
 * @path frontend/tests/unit/composables/
 * @description useDeviceBase组合式函数完整单元测试
 * 
 * 测试覆盖：
 * - 设备连接状态管理
 * - 状态更新
 * - 告警处理
 * - 数据新鲜度
 * 
 * @author Agent
 * @date 2026-03-16
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { nextTick } from 'vue';
import { useDeviceBase } from '@/composables/useDeviceBase';

// Mock useDataFreshness
vi.mock('@/composables/useDataFreshness', () => ({
  useDataFreshness: vi.fn(() => ({
    level: { value: 'fresh' },
    updateTimestamp: vi.fn(),
    checkFreshness: vi.fn(() => true),
    lastUpdate: { value: Date.now() }
  })),
  FRESHNESS_LEVEL: {
    FRESH: 'fresh',
    STALE: 'stale',
    OUTDATED: 'outdated'
  }
}));

describe('useDeviceBase', () => {
  let device;
  let defaultDeviceName;
  let defaultOptions;

  beforeEach(() => {
    vi.clearAllMocks();

    defaultDeviceName = 'TestDevice';
    defaultOptions = {
      freshnessConfig: {
        staleThreshold: 30000,
        outdatedThreshold: 60000
      }
    };
  });

  afterEach(() => {
    if (device) {
      device = null;
    }
  });

  // ==================== 初始化测试 ====================

  describe('初始化', () => {
    it('应该正确初始化所有状态', () => {
      device = useDeviceBase(defaultDeviceName, defaultOptions);

      expect(device.isConnected.value).toBe(false);
      expect(device.isConnecting.value).toBe(false);
      expect(device.status.value).toBe('disconnected');
      expect(device.alarmMessage.value).toBe('');
      expect(device.wsConnected.value).toBe(false);
    });

    it('应该使用默认配置选项', () => {
      device = useDeviceBase(defaultDeviceName);

      expect(device).toBeDefined();
    });

    it('应该初始化数据新鲜度管理', () => {
      device = useDeviceBase(defaultDeviceName, defaultOptions);

      expect(device.freshness).toBeDefined();
      expect(device.freshness.updateTimestamp).toBeDefined();
    });

    it('应该初始化加载状态', () => {
      device = useDeviceBase(defaultDeviceName, defaultOptions);

      expect(device.loading.value).toEqual({});
    });
  });

  // ==================== 连接状态测试 ====================

  describe('连接状态', () => {
    beforeEach(() => {
      device = useDeviceBase(defaultDeviceName, defaultOptions);
    });

    it('应该正确设置连接状态', () => {
      device.isConnected.value = true;

      expect(device.isConnected.value).toBe(true);
    });

    it('应该正确设置连接中状态', () => {
      device.isConnecting.value = true;

      expect(device.isConnecting.value).toBe(true);
    });

    it('应该正确设置WebSocket连接状态', () => {
      device.wsConnected.value = true;

      expect(device.wsConnected.value).toBe(true);
    });
  });

  // ==================== 状态管理测试 ====================

  describe('状态管理', () => {
    beforeEach(() => {
      device = useDeviceBase(defaultDeviceName, defaultOptions);
    });

    it('应该正确更新设备状态', () => {
      device.updateStatus('ready');

      expect(device.status.value).toBe('ready');
    });

    it('应该正确更新为忙碌状态', () => {
      device.updateStatus('busy');

      expect(device.status.value).toBe('busy');
    });

    it('应该正确更新为错误状态', () => {
      device.updateStatus('error');

      expect(device.status.value).toBe('error');
    });

    it('应该正确更新为连接中状态', () => {
      device.updateStatus('connecting');

      expect(device.status.value).toBe('connecting');
    });

    it('应该正确更新为断开连接状态', () => {
      device.updateStatus('ready');
      device.updateStatus('disconnected');

      expect(device.status.value).toBe('disconnected');
    });
  });

  // ==================== 计算属性测试 ====================

  describe('计算属性', () => {
    beforeEach(() => {
      device = useDeviceBase(defaultDeviceName, defaultOptions);
    });

    it('canControl应该在设备就绪时返回true', () => {
      device.isConnected.value = true;
      device.isConnecting.value = false;
      device.status.value = 'ready';

      expect(device.canControl.value).toBe(true);
    });

    it('canControl应该在设备未连接时返回false', () => {
      device.isConnected.value = false;
      device.status.value = 'ready';

      expect(device.canControl.value).toBe(false);
    });

    it('canControl应该在设备连接中时返回false', () => {
      device.isConnected.value = true;
      device.isConnecting.value = true;
      device.status.value = 'ready';

      expect(device.canControl.value).toBe(false);
    });

    it('canControl应该在设备忙碌时返回false', () => {
      device.isConnected.value = true;
      device.isConnecting.value = false;
      device.status.value = 'busy';

      expect(device.canControl.value).toBe(false);
    });

    it('statusType应该返回正确的类型', () => {
      const statusTypes = [
        { status: 'ready', type: 'success' },
        { status: 'busy', type: 'info' },
        { status: 'error', type: 'danger' },
        { status: 'emergency_stop', type: 'danger' },
        { status: 'connecting', type: 'warning' },
        { status: 'disconnected', type: 'info' }
      ];

      for (const { status, type } of statusTypes) {
        device.status.value = status;
        expect(device.statusType.value).toBe(type);
      }
    });

    it('statusText应该返回正确的文本', () => {
      const statusTexts = [
        { status: 'disconnected', text: '未连接' },
        { status: 'connecting', text: '连接中' },
        { status: 'ready', text: '就绪' },
        { status: 'busy', text: '忙碌' },
        { status: 'error', text: '错误' },
        { status: 'emergency_stop', text: '急停' }
      ];

      for (const { status, text } of statusTexts) {
        device.status.value = status;
        expect(device.statusText.value).toBe(text);
      }
    });
  });

  // ==================== 告警处理测试 ====================

  describe('告警处理', () => {
    beforeEach(() => {
      vi.useFakeTimers();
      device = useDeviceBase(defaultDeviceName, defaultOptions);
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('应该显示错误消息', () => {
      device.showError('测试错误消息');

      expect(device.alarmMessage.value).toBe('测试错误消息');
    });

    it('错误消息应该在5秒后自动清除', async () => {
      device.showError('测试错误消息');

      expect(device.alarmMessage.value).toBe('测试错误消息');

      // 快进5秒
      vi.advanceTimersByTime(5000);
      await nextTick();

      expect(device.alarmMessage.value).toBe('');
    });

    it('应该支持清除告警消息', () => {
      device.showError('测试错误消息');
      device.clearAlarm();

      expect(device.alarmMessage.value).toBe('');
    });
  });

  // ==================== 加载状态测试 ====================

  describe('加载状态', () => {
    beforeEach(() => {
      device = useDeviceBase(defaultDeviceName, defaultOptions);
    });

    it('应该设置加载状态', () => {
      device.setLoading('connect', true);

      expect(device.loading.value.connect).toBe(true);
    });

    it('应该清除加载状态', () => {
      device.setLoading('connect', true);
      device.setLoading('connect', false);

      expect(device.loading.value.connect).toBe(false);
    });

    it('应该支持多个加载状态', () => {
      device.setLoading('connect', true);
      device.setLoading('update', true);
      device.setLoading('fetch', false);

      expect(device.loading.value.connect).toBe(true);
      expect(device.loading.value.update).toBe(true);
      expect(device.loading.value.fetch).toBe(false);
    });
  });

  // ==================== 数据新鲜度测试 ====================

  describe('数据新鲜度', () => {
    beforeEach(() => {
      device = useDeviceBase(defaultDeviceName, defaultOptions);
    });

    it('应该更新数据时间戳', () => {
      device.freshness.updateTimestamp();

      expect(device.freshness.updateTimestamp).toHaveBeenCalled();
    });

    it('应该检查数据新鲜度', () => {
      const isFresh = device.freshness.checkFreshness();

      expect(typeof isFresh).toBe('boolean');
    });
  });

  // ==================== 连接流程测试 ====================

  describe('连接流程', () => {
    beforeEach(() => {
      device = useDeviceBase(defaultDeviceName, defaultOptions);
    });

    it('应该模拟完整的连接流程', async () => {
      // 开始连接
      device.isConnecting.value = true;
      device.updateStatus('connecting');

      expect(device.status.value).toBe('connecting');
      expect(device.isConnecting.value).toBe(true);

      // 连接成功
      device.isConnected.value = true;
      device.isConnecting.value = false;
      device.wsConnected.value = true;
      device.updateStatus('ready');

      expect(device.isConnected.value).toBe(true);
      expect(device.status.value).toBe('ready');
      expect(device.canControl.value).toBe(true);
    });

    it('应该模拟连接失败流程', async () => {
      // 开始连接
      device.isConnecting.value = true;
      device.updateStatus('connecting');

      // 连接失败
      device.isConnecting.value = false;
      device.updateStatus('error');
      device.showError('连接失败');

      expect(device.status.value).toBe('error');
      expect(device.alarmMessage.value).toBe('连接失败');
    });

    it('应该模拟断开连接流程', async () => {
      // 先连接
      device.isConnected.value = true;
      device.wsConnected.value = true;
      device.updateStatus('ready');

      // 断开连接
      device.isConnected.value = false;
      device.wsConnected.value = false;
      device.updateStatus('disconnected');

      expect(device.isConnected.value).toBe(false);
      expect(device.status.value).toBe('disconnected');
      expect(device.canControl.value).toBe(false);
    });
  });

  // ==================== 急停状态测试 ====================

  describe('急停状态', () => {
    beforeEach(() => {
      device = useDeviceBase(defaultDeviceName, defaultOptions);
    });

    it('应该正确处理急停状态', () => {
      device.isConnected.value = true;
      device.updateStatus('emergency_stop');

      expect(device.status.value).toBe('emergency_stop');
      expect(device.statusType.value).toBe('danger');
      expect(device.statusText.value).toBe('急停');
      expect(device.canControl.value).toBe(false);
    });
  });

  // ==================== 边界情况测试 ====================

  describe('边界情况', () => {
    it('应该处理空设备名称', () => {
      device = useDeviceBase('', defaultOptions);

      expect(device).toBeDefined();
    });

    it('应该处理空配置选项', () => {
      device = useDeviceBase(defaultDeviceName, undefined);

      expect(device).toBeDefined();
    });

    it('应该处理无效状态值', () => {
      device = useDeviceBase(defaultDeviceName, defaultOptions);

      device.updateStatus('invalid_status');

      expect(device.status.value).toBe('invalid_status');
    });

    it('应该处理空错误消息', () => {
      device = useDeviceBase(defaultDeviceName, defaultOptions);

      device.showError('');

      expect(device.alarmMessage.value).toBe('');
    });

    it('应该处理多次状态更新', () => {
      device = useDeviceBase(defaultDeviceName, defaultOptions);

      device.updateStatus('connecting');
      device.updateStatus('ready');
      device.updateStatus('busy');
      device.updateStatus('ready');

      expect(device.status.value).toBe('ready');
    });
  });

  // ==================== 响应式测试 ====================

  describe('响应式', () => {
    beforeEach(() => {
      device = useDeviceBase(defaultDeviceName, defaultOptions);
    });

    it('状态变化应该是响应式的', async () => {
      device.updateStatus('ready');
      await nextTick();

      expect(device.status.value).toBe('ready');
    });

    it('连接状态变化应该是响应式的', async () => {
      device.isConnected.value = true;
      await nextTick();

      expect(device.isConnected.value).toBe(true);
    });

    it('告警消息变化应该是响应式的', async () => {
      device.showError('测试消息');
      await nextTick();

      expect(device.alarmMessage.value).toBe('测试消息');
    });
  });
});
