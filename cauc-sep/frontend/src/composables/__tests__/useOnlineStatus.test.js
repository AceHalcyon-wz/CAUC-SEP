/**
 * @file useOnlineStatus.test.js
 * @path frontend/src/composables/__tests__/
 * @description useOnlineStatus组合式函数单元测试
 * @author Agent
 * @date 2024-03-07
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useOnlineStatus, getNetworkConnectionInfo, isNetworkInformationSupported } from '../useOnlineStatus';

describe('useOnlineStatus', () => {
  let onlineStatus;
  let eventListeners;

  beforeEach(() => {
    vi.useFakeTimers();
    
    eventListeners = {};
    
    window.addEventListener = vi.fn((event, handler) => {
      eventListeners[event] = handler;
    });
    
    window.removeEventListener = vi.fn((event, handler) => {
      delete eventListeners[event];
    });
    
    Object.defineProperty(navigator, 'onLine', {
      writable: true,
      value: true,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    
    if (onlineStatus) {
      // 清理定时器
      vi.runAllTimers();
    }
  });

  describe('初始化状态', () => {
    it('应该检测在线状态', () => {
      navigator.onLine = true;
      onlineStatus = useOnlineStatus();

      expect(onlineStatus.isOnline.value).toBe(true);
      expect(onlineStatus.isOffline.value).toBe(false);
    });

    it('应该检测离线状态', () => {
      navigator.onLine = false;
      onlineStatus = useOnlineStatus();

      expect(onlineStatus.isOnline.value).toBe(false);
      expect(onlineStatus.isOffline.value).toBe(true);
    });

    it('应该初始化网络信息', () => {
      onlineStatus = useOnlineStatus();

      expect(onlineStatus.connectionType.value).toBeDefined();
      expect(onlineStatus.downlinkSpeed.value).toBeDefined();
      expect(onlineStatus.networkQuality.value).toBeDefined();
    });
  });

  describe('事件监听', () => {
    it('应该响应online事件', () => {
      navigator.onLine = false;
      onlineStatus = useOnlineStatus();

      expect(onlineStatus.isOnline.value).toBe(false);

      // 触发online事件
      navigator.onLine = true;
      eventListeners.online();

      expect(onlineStatus.isOnline.value).toBe(true);
      expect(onlineStatus.lastOnlineTime.value).toBeInstanceOf(Date);
    });

    it('应该响应offline事件', () => {
      navigator.onLine = true;
      onlineStatus = useOnlineStatus();

      expect(onlineStatus.isOnline.value).toBe(true);

      // 触发offline事件
      navigator.onLine = false;
      eventListeners.offline();

      expect(onlineStatus.isOnline.value).toBe(false);
      expect(onlineStatus.lastOfflineTime.value).toBeInstanceOf(Date);
    });

    it('应该在上线时调用回调', () => {
      const onOnline = vi.fn();
      navigator.onLine = false;
      onlineStatus = useOnlineStatus({ onOnline });

      eventListeners.online();

      expect(onOnline).toHaveBeenCalled();
    });

    it('应该在离线时调用回调', () => {
      const onOffline = vi.fn();
      navigator.onLine = true;
      onlineStatus = useOnlineStatus({ onOffline });

      eventListeners.offline();

      expect(onOffline).toHaveBeenCalled();
    });

    it('应该在状态变更时调用回调', () => {
      const onStatusChange = vi.fn();
      navigator.onLine = true;
      onlineStatus = useOnlineStatus({ onStatusChange });

      eventListeners.offline();

      expect(onStatusChange).toHaveBeenCalledWith(
        expect.objectContaining({
          status: 'offline',
          previousStatus: 'online',
        })
      );
    });
  });

  describe('离线持续时间', () => {
    it('应该计算离线持续时间', () => {
      navigator.onLine = true;
      onlineStatus = useOnlineStatus();

      // 触发离线
      eventListeners.offline();
      
      // 模拟时间流逝
      vi.advanceTimersByTime(5000);

      expect(onlineStatus.offlineDuration.value).toBe(5000);
    });

    it('应该格式化离线持续时间', () => {
      navigator.onLine = true;
      onlineStatus = useOnlineStatus();

      eventListeners.offline();
      
      // 30秒
      vi.advanceTimersByTime(30000);
      expect(onlineStatus.formattedOfflineDuration.value).toBe('30秒');

      // 5分钟
      vi.advanceTimersByTime(300000);
      expect(onlineStatus.formattedOfflineDuration.value).toContain('分钟');

      // 2小时
      vi.advanceTimersByTime(7200000);
      expect(onlineStatus.formattedOfflineDuration.value).toContain('小时');
    });

    it('应该在上线时重置离线持续时间', () => {
      navigator.onLine = false;
      onlineStatus = useOnlineStatus();

      vi.advanceTimersByTime(5000);
      expect(onlineStatus.offlineDuration.value).toBe(5000);

      // 上线
      eventListeners.online();
      expect(onlineStatus.offlineDuration.value).toBe(0);
    });
  });

  describe('网络质量评估', () => {
    it('应该评估4G网络质量', () => {
      navigator.connection = {
        effectiveType: '4g',
        downlink: 10,
        rtt: 50,
        saveData: false,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      };

      onlineStatus = useOnlineStatus();

      expect(onlineStatus.networkQualityLevel.value).toBe('excellent');
      expect(onlineStatus.networkQualityLabel.value).toBe('优秀');
    });

    it('应该评估3G网络质量', () => {
      navigator.connection = {
        effectiveType: '3g',
        downlink: 1.5,
        rtt: 100,
        saveData: false,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      };

      onlineStatus = useOnlineStatus();

      expect(onlineStatus.networkQualityLevel.value).toBe('fair');
      expect(onlineStatus.networkQualityLabel.value).toBe('一般');
    });

    it('应该评估2G网络质量', () => {
      navigator.connection = {
        effectiveType: '2g',
        downlink: 0.5,
        rtt: 300,
        saveData: false,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      };

      onlineStatus = useOnlineStatus();

      expect(onlineStatus.networkQualityLevel.value).toBe('poor');
      expect(onlineStatus.networkQualityLabel.value).toBe('较差');
    });
  });

  describe('健康检查', () => {
    it('应该执行健康检查', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        status: 200,
      });

      onlineStatus = useOnlineStatus({
        checkUrl: '/api/health',
        timeout: 5000,
      });

      const result = await onlineStatus.performHealthCheck();

      expect(result.success).toBe(true);
      expect(result.status).toBe(200);
    });

    it('应该处理健康检查超时', async () => {
      global.fetch = vi.fn().mockImplementation(() => 
        new Promise((_, reject) => {
          setTimeout(() => reject(new Error('Timeout')), 10000);
        })
      );

      onlineStatus = useOnlineStatus({
        timeout: 100,
      });

      const result = await onlineStatus.performHealthCheck();

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });

    it('应该处理健康检查失败', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      onlineStatus = useOnlineStatus();

      const result = await onlineStatus.performHealthCheck();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Network error');
    });

    it('应该防止并发健康检查', async () => {
      global.fetch = vi.fn().mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({ status: 200 }), 100))
      );

      onlineStatus = useOnlineStatus();

      const check1 = onlineStatus.performHealthCheck();
      const check2 = onlineStatus.performHealthCheck();

      const [result1, result2] = await Promise.all([check1, check2]);

      // 第二次检查应该返回第一次的结果
      expect(result1).toBe(result2);
    });
  });

  describe('状态历史', () => {
    it('应该记录状态变更历史', () => {
      navigator.onLine = true;
      onlineStatus = useOnlineStatus();

      eventListeners.offline();
      eventListeners.online();
      eventListeners.offline();

      expect(onlineStatus.statusHistory.value.length).toBeGreaterThanOrEqual(3);
    });

    it('应该限制历史记录数量', () => {
      navigator.onLine = true;
      onlineStatus = useOnlineStatus();

      // 触发多次状态变更
      for (let i = 0; i < 60; i++) {
        eventListeners.offline();
        eventListeners.online();
      }

      expect(onlineStatus.statusHistory.value.length).toBeLessThanOrEqual(50);
    });
  });

  describe('离线统计', () => {
    it('应该计算离线统计信息', () => {
      navigator.onLine = true;
      onlineStatus = useOnlineStatus();

      // 模拟多次离线
      eventListeners.offline();
      vi.advanceTimersByTime(1000);
      eventListeners.online();

      eventListeners.offline();
      vi.advanceTimersByTime(2000);
      eventListeners.online();

      const stats = onlineStatus.offlineStats.value;

      expect(stats.totalOfflineCount).toBeGreaterThan(0);
    });
  });
});

describe('getNetworkConnectionInfo', () => {
  it('应该返回网络连接信息', () => {
    navigator.connection = {
      type: 'wifi',
      effectiveType: '4g',
      downlink: 10,
      rtt: 50,
      saveData: false,
    };

    const info = getNetworkConnectionInfo();

    expect(info.available).toBe(true);
    expect(info.type).toBe('wifi');
    expect(info.effectiveType).toBe('4g');
    expect(info.downlink).toBe(10);
  });

  it('应该在API不可用时返回默认值', () => {
    delete navigator.connection;
    delete navigator.mozConnection;
    delete navigator.webkitConnection;

    const info = getNetworkConnectionInfo();

    expect(info.available).toBe(false);
    expect(info.type).toBe('unknown');
    expect(info.effectiveType).toBe('unknown');
    expect(info.downlink).toBe(0);
  });
});

describe('isNetworkInformationSupported', () => {
  it('应该检测API支持', () => {
    navigator.connection = {};
    
    expect(isNetworkInformationSupported()).toBe(true);
  });

  it('应该检测API不支持', () => {
    delete navigator.connection;
    delete navigator.mozConnection;
    delete navigator.webkitConnection;
    
    expect(isNetworkInformationSupported()).toBe(false);
  });
});
