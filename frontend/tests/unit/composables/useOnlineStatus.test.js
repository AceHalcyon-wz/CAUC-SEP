/**
 * @file useOnlineStatus.test.js
 * @path frontend/src/composables/__tests__/
 * @description useOnlineStatus组合式函数单元测试
 * @author Agent
 * @date 2024-03-07
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useOnlineStatus, getNetworkConnectionInfo, isNetworkInformationSupported } from '@/composables/useOnlineStatus';

describe('useOnlineStatus', () => {
  let onlineStatus;

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    onlineStatus = null;
  });

  describe('初始化状态', () => {
    it('应该检测在线状态', () => {
      onlineStatus = useOnlineStatus();

      expect(typeof onlineStatus.isOnline.value).toBe('boolean');
      expect(typeof onlineStatus.isOffline.value).toBe('boolean');
    });

    it('应该初始化网络信息', () => {
      onlineStatus = useOnlineStatus();

      expect(onlineStatus.connectionType.value).toBeDefined();
      expect(onlineStatus.downlinkSpeed.value).toBeDefined();
      expect(onlineStatus.networkQuality.value).toBeDefined();
    });
  });

  describe('网络质量评估', () => {
    it('应该评估网络质量', () => {
      onlineStatus = useOnlineStatus();

      expect(onlineStatus.networkQualityLevel.value).toBeDefined();
      expect(onlineStatus.networkQualityLabel.value).toBeDefined();
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

    it('应该处理健康检查失败', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      onlineStatus = useOnlineStatus();

      const result = await onlineStatus.performHealthCheck();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Network error');
    });
  });
});

describe('getNetworkConnectionInfo', () => {
  it('应该返回网络连接信息', () => {
    const info = getNetworkConnectionInfo();

    expect(info).toBeDefined();
    expect(typeof info.available).toBe('boolean');
    expect(info.type).toBeDefined();
    expect(info.effectiveType).toBeDefined();
  });
});

describe('isNetworkInformationSupported', () => {
  it('应该检测API支持', () => {
    const result = isNetworkInformationSupported();
    
    expect(typeof result).toBe('boolean');
  });
});
