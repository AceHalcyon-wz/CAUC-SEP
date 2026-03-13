/**
 * @file UpdateNotification.test.js
 * @path src/components/__tests__/
 * @description UpdateNotification组件单元测试
 * @author Agent
 * @date 2026-03-07
 * @dependencies @vue/test-utils, vitest
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import UpdateNotification from '@/components/common/UpdateNotification.vue';

// Mock API模块
vi.mock('@/api/update', () => ({
  getCurrentVersion: vi.fn(() => Promise.resolve({
    version: '0.3.0',
    build_number: 30000,
    release_date: '2026-03-07'
  })),
  checkForUpdate: vi.fn(() => Promise.resolve({
    has_update: true,
    update_info: {
      latest_version: '0.3.2',
      latest_build: 30200,
      update_type: 'incremental',
      priority: 'medium',
      release_date: '2026-03-07',
      package_size_mb: 45.2,
      download_url: '/api/update/download/0.3.2',
      checksum_sha256: 'abc123',
      changelog: ['修复安全漏洞', '优化性能']
    }
  })),
  getUpdateProgress: vi.fn(() => Promise.resolve({
    status: 'downloading',
    progress_percent: 50,
    downloaded_bytes: 23654400,
    total_bytes: 47308800
  })),
  applyUpdate: vi.fn(() => Promise.resolve({
    success: true,
    message: '更新成功'
  }))
}));

describe('UpdateNotification.vue', () => {
  let wrapper;
  let pinia;

  beforeEach(() => {
    // 创建新的Pinia实例
    pinia = createPinia();
    setActivePinia(pinia);

    // 清除所有mock
    vi.clearAllMocks();
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
  });

  /**
   * 基础渲染测试
   */
  describe('基础渲染', () => {
    it('应该正确渲染组件', () => {
      wrapper = mount(UpdateNotification, {
        global: {
          plugins: [pinia]
        }
      });

      expect(wrapper.exists()).toBe(true);
    });

    it('默认应该隐藏通知', () => {
      wrapper = mount(UpdateNotification, {
        global: {
          plugins: [pinia]
        }
      });

      expect(wrapper.find('.update-notification').exists()).toBe(false);
    });

    it('应该接受props配置', () => {
      wrapper = mount(UpdateNotification, {
        props: {
          autoCheck: false,
          checkInterval: 60000,
          backgroundDownload: false,
          channel: 'beta'
        },
        global: {
          plugins: [pinia]
        }
      });

      expect(wrapper.props('autoCheck')).toBe(false);
      expect(wrapper.props('checkInterval')).toBe(60000);
      expect(wrapper.props('backgroundDownload')).toBe(false);
      expect(wrapper.props('channel')).toBe('beta');
    });
  });

  /**
   * 更新检查测试
   */
  describe('更新检查', () => {
    it('应该在挂载时自动检查更新（autoCheck=true）', async () => {
      const { checkForUpdate } = await import('../../api/update');

      wrapper = mount(UpdateNotification, {
        props: {
          autoCheck: true
        },
        global: {
          plugins: [pinia]
        }
      });

      // 等待异步操作
      await wrapper.vm.$nextTick();
      await new Promise(resolve => setTimeout(resolve, 100));

      expect(checkForUpdate).toHaveBeenCalled();
    });

    it('不应该在挂载时自动检查更新（autoCheck=false）', async () => {
      const { checkForUpdate } = await import('../../api/update');

      wrapper = mount(UpdateNotification, {
        props: {
          autoCheck: false
        },
        global: {
          plugins: [pinia]
        }
      });

      await wrapper.vm.$nextTick();

      expect(checkForUpdate).not.toHaveBeenCalled();
    });

    it('发现更新时应该显示通知', async () => {
      wrapper = mount(UpdateNotification, {
        global: {
          plugins: [pinia]
        }
      });

      // 手动触发检查
      await wrapper.vm.checkUpdate();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.visible).toBe(true);
      expect(wrapper.vm.status).toBe('available');
    });

    it('没有更新时应该隐藏通知', async () => {
      const { checkForUpdate } = await import('../../api/update');
      checkForUpdate.mockResolvedValueOnce({
        has_update: false
      });

      wrapper = mount(UpdateNotification, {
        global: {
          plugins: [pinia]
        }
      });

      await wrapper.vm.checkUpdate();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.visible).toBe(false);
      expect(wrapper.vm.status).toBe('idle');
    });
  });

  /**
   * UI交互测试
   */
  describe('UI交互', () => {
    beforeEach(async () => {
      wrapper = mount(UpdateNotification, {
        global: {
          plugins: [pinia]
        }
      });

      // 触发更新检查
      await wrapper.vm.checkUpdate();
      await wrapper.vm.$nextTick();
    });

    it('应该显示版本信息', () => {
      const versionItems = wrapper.findAll('.version-item');
      expect(versionItems.length).toBeGreaterThan(0);
    });

    it('应该显示更新日志', () => {
      const changelog = wrapper.find('.changelog');
      expect(changelog.exists()).toBe(true);
    });

    it('应该显示操作按钮', () => {
      const buttons = wrapper.findAll('.btn');
      expect(buttons.length).toBeGreaterThan(0);
    });

    it('点击稍后提醒应该隐藏通知', async () => {
      const remindBtn = wrapper.findAll('.btn')[1]; // 第二个按钮是"稍后提醒"
      await remindBtn.trigger('click');

      expect(wrapper.vm.visible).toBe(false);
      expect(wrapper.vm.minimized).toBe(true);
    });

    it('点击关闭按钮应该关闭通知', async () => {
      const closeBtn = wrapper.find('.header-btn[title="关闭"]');
      await closeBtn.trigger('click');

      expect(wrapper.vm.visible).toBe(false);
    });

    it('点击最小化按钮应该最小化通知', async () => {
      const minimizeBtn = wrapper.find('.header-btn[title="最小化"]');
      await minimizeBtn.trigger('click');

      expect(wrapper.vm.minimized).toBe(true);
    });
  });

  /**
   * 进度显示测试
   */
  describe('进度显示', () => {
    it('下载中应该显示进度条', async () => {
      wrapper = mount(UpdateNotification, {
        global: {
          plugins: [pinia]
        }
      });

      wrapper.vm.status = 'downloading';
      wrapper.vm.downloadProgress = {
        percent: 50,
        downloadedMB: 22.6,
        totalMB: 45.2,
        speed: 1024
      };
      wrapper.vm.visible = true;

      await wrapper.vm.$nextTick();

      const progressBar = wrapper.find('.download-progress');
      expect(progressBar.exists()).toBe(true);
    });

    it('安装中应该显示安装进度', async () => {
      wrapper = mount(UpdateNotification, {
        global: {
          plugins: [pinia]
        }
      });

      wrapper.vm.status = 'installing';
      wrapper.vm.installProgress = {
        percent: 75,
        currentStep: '应用更新...'
      };
      wrapper.vm.visible = true;

      await wrapper.vm.$nextTick();

      const installProgress = wrapper.find('.install-progress');
      expect(installProgress.exists()).toBe(true);
    });
  });

  /**
   * 状态管理测试
   */
  describe('状态管理', () => {
    it('应该正确处理更新失败', async () => {
      const { checkForUpdate } = await import('../../api/update');
      checkForUpdate.mockRejectedValueOnce(new Error('网络错误'));

      wrapper = mount(UpdateNotification, {
        global: {
          plugins: [pinia]
        }
      });

      await wrapper.vm.checkUpdate();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.status).toBe('failed');
      expect(wrapper.vm.errorMessage).toBeTruthy();
    });

    it('应该正确处理更新完成', async () => {
      wrapper = mount(UpdateNotification, {
        global: {
          plugins: [pinia]
        }
      });

      wrapper.vm.status = 'completed';
      wrapper.vm.visible = true;

      await wrapper.vm.$nextTick();

      const completed = wrapper.find('.update-completed');
      expect(completed.exists()).toBe(true);
    });
  });

  /**
   * 事件发射测试
   */
  describe('事件发射', () => {
    it('发现更新时应该发射update-available事件', async () => {
      wrapper = mount(UpdateNotification, {
        global: {
          plugins: [pinia]
        }
      });

      await wrapper.vm.checkUpdate();
      await wrapper.vm.$nextTick();

      expect(wrapper.emitted('update-available')).toBeTruthy();
    });

    it('点击关闭时应该发射close事件', async () => {
      wrapper = mount(UpdateNotification, {
        global: {
          plugins: [pinia]
        }
      });

      wrapper.vm.visible = true;
      wrapper.vm.status = 'available';
      await wrapper.vm.$nextTick();

      const closeBtn = wrapper.find('.header-btn[title="关闭"]');
      await closeBtn.trigger('click');

      expect(wrapper.emitted('close')).toBeTruthy();
    });
  });

  /**
   * 定时器测试
   */
  describe('定时器', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('应该按间隔自动检查更新', async () => {
      const { checkForUpdate } = await import('../../api/update');

      wrapper = mount(UpdateNotification, {
        props: {
          autoCheck: true,
          checkInterval: 60000 // 1分钟
        },
        global: {
          plugins: [pinia]
        }
      });

      // 清除初始调用的计数
      checkForUpdate.mockClear();

      // 快进时间
      vi.advanceTimersByTime(60000);

      expect(checkForUpdate).toHaveBeenCalled();
    });

    it('卸载时应该清理定时器', async () => {
      wrapper = mount(UpdateNotification, {
        props: {
          autoCheck: true
        },
        global: {
          plugins: [pinia]
        }
      });

      const clearIntervalSpy = vi.spyOn(global, 'clearInterval');

      wrapper.unmount();

      expect(clearIntervalSpy).toHaveBeenCalled();
    });
  });

  /**
   * 边界情况测试
   */
  describe('边界情况', () => {
    it('处理空更新信息', async () => {
      const { checkForUpdate } = await import('../../api/update');
      checkForUpdate.mockResolvedValueOnce(null);

      wrapper = mount(UpdateNotification, {
        global: {
          plugins: [pinia]
        }
      });

      await wrapper.vm.checkUpdate();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.status).toBe('idle');
    });

    it('处理缺少下载URL的情况', async () => {
      const { checkForUpdate } = await import('../../api/update');
      checkForUpdate.mockResolvedValueOnce({
        has_update: true,
        update_info: {
          latest_version: '0.3.2',
          download_url: null
        }
      });

      wrapper = mount(UpdateNotification, {
        props: {
          backgroundDownload: true
        },
        global: {
          plugins: [pinia]
        }
      });

      await wrapper.vm.checkUpdate();
      await wrapper.vm.$nextTick();

      // 应该不会进入下载状态
      expect(wrapper.vm.status).toBe('available');
    });

    it('防止重复检查', async () => {
      wrapper = mount(UpdateNotification, {
        global: {
          plugins: [pinia]
        }
      });

      wrapper.vm.processing = true;

      await wrapper.vm.checkUpdate();
      await wrapper.vm.$nextTick();

      const { checkForUpdate } = await import('../../api/update');
      expect(checkForUpdate).not.toHaveBeenCalled();
    });
  });
});
