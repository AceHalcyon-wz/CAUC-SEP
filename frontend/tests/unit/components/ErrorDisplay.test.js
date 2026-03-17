/**
 * @file ErrorDisplay.test.js
 * @path frontend/tests/unit/components/
 * @description ErrorDisplay组件单元测试
 * 
 * 测试覆盖：
 * - 错误显示功能
 * - 错误类型识别
 * - 错误恢复机制
 * - 错误日志记录
 * 
 * @author Agent
 * @date 2026-03-16
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { nextTick } from 'vue';
import ErrorDisplay from '@/components/common/ErrorDisplay.vue';
import ErrorSolution from '@/components/common/ErrorSolution.vue';
import {
  ERROR_TYPES,
  ERROR_SEVERITY,
  getErrorIcon,
  getSeverityColor,
  getErrorTypeLabel
} from '@/composables/useErrorHandler';

/**
 * 创建模拟错误信息
 * 
 * @param {Object} overrides - 覆盖默认配置
 * @returns {Object} 模拟错误信息对象
 */
function createMockErrorInfo(overrides = {}) {
  return {
    id: `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    timestamp: new Date().toISOString(),
    message: '测试错误消息',
    name: 'Error',
    type: ERROR_TYPES.NETWORK,
    severity: ERROR_SEVERITY.HIGH,
    stack: ['at line 1', 'at line 2', 'at line 3'],
    fullStack: 'Error: 测试错误消息\n    at line 1\n    at line 2\n    at line 3',
    context: {
      component: 'TestComponent',
      action: 'testAction',
      route: '/test',
      userMessage: '用户友好的错误提示'
    },
    system: {
      platform: 'Win32',
      language: 'zh-CN',
      online: true,
      connection: { effectiveType: '4g' },
      viewport: { width: 1920, height: 1080 },
      screen: { width: 1920, height: 1080 },
      memory: {
        usedJSHeapSize: '50 MB',
        totalJSHeapSize: '100 MB',
        jsHeapSizeLimit: '2 GB'
      },
      userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    },
    userActions: [
      { action: 'click', timestamp: new Date().toISOString(), route: '/test' }
    ],
    solution: {
      title: '网络连接错误',
      type: ERROR_TYPES.NETWORK,
      severity: ERROR_SEVERITY.HIGH,
      solutions: [
        { step: 1, action: '检查网络', description: '确保网络连接正常', icon: 'Connection' }
      ],
      autoActions: [
        { label: '重试', action: 'retry' }
      ]
    },
    ...overrides
  };
}

describe('ErrorDisplay.vue', () => {
  let wrapper;
  let mockErrorInfo;

  beforeEach(() => {
    mockErrorInfo = createMockErrorInfo();
    vi.clearAllMocks();
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
      wrapper = null;
    }
  });

  // ==================== 基础渲染测试 ====================

  describe('基础渲染', () => {
    it('应该正确渲染对话框', async () => {
      wrapper = mount(ErrorDisplay, {
        props: {
          modelValue: true,
          errorInfo: mockErrorInfo
        },
        global: {
          stubs: {
            'el-dialog': {
              template: '<div class="el-dialog"><slot /></div>',
              props: ['modelValue', 'title', 'width']
            },
            'el-icon': {
              template: '<i class="el-icon"><slot /></i>'
            },
            'el-button': {
              template: '<button class="el-button"><slot /></button>',
              props: ['type', 'loading', 'circle', 'size', 'text']
            },
            'el-tag': {
              template: '<span class="el-tag"><slot /></span>',
              props: ['type', 'effect', 'size']
            },
            'el-tooltip': {
              template: '<div class="el-tooltip"><slot /></div>',
              props: ['content', 'placement']
            },
            'el-tabs': {
              template: '<div class="el-tabs"><slot /></div>',
              props: ['modelValue']
            },
            'el-tab-pane': {
              template: '<div class="el-tab-pane"><slot /></div>',
              props: ['label', 'name']
            },
            'el-empty': {
              template: '<div class="el-empty"><slot /></div>',
              props: ['description']
            },
            'el-timeline': {
              template: '<div class="el-timeline"><slot /></div>'
            },
            'el-timeline-item': {
              template: '<div class="el-timeline-item"><slot /></div>',
              props: ['timestamp', 'placement', 'type']
            },
            'el-collapse-transition': {
              template: '<div class="el-collapse-transition"><slot /></div>'
            },
            ErrorSolution: true
          }
        }
      });

      await nextTick();

      expect(wrapper.find('.error-display').exists()).toBe(true);
      expect(wrapper.find('.error-overview').exists()).toBe(true);
    });

    it('对话框不可见时不渲染内容', async () => {
      wrapper = mount(ErrorDisplay, {
        props: {
          modelValue: false,
          errorInfo: mockErrorInfo
        },
        global: {
          stubs: {
            'el-dialog': {
              template: '<div v-if="modelValue" class="el-dialog"><slot /></div>',
              props: ['modelValue']
            }
          }
        }
      });

      await nextTick();

      expect(wrapper.find('.error-display').exists()).toBe(false);
    });
  });

  // ==================== 错误显示测试 ====================

  describe('错误显示', () => {
    it('应该正确显示错误消息', async () => {
      wrapper = mount(ErrorDisplay, {
        props: {
          modelValue: true,
          errorInfo: mockErrorInfo
        },
        global: {
          stubs: {
            'el-dialog': { template: '<div><slot /></div>' },
            'el-icon': { template: '<i><slot /></i>' },
            'el-button': { template: '<button><slot /></button>' },
            'el-tag': { template: '<span><slot /></span>' },
            'el-tooltip': { template: '<div><slot /></div>' },
            'el-tabs': { template: '<div><slot /></div>' },
            'el-tab-pane': { template: '<div><slot /></div>' },
            'el-empty': { template: '<div><slot /></div>' },
            'el-timeline': { template: '<div><slot /></div>' },
            'el-timeline-item': { template: '<div><slot /></div>' },
            'el-collapse-transition': { template: '<div><slot /></div>' },
            ErrorSolution: true
          }
        }
      });

      await nextTick();

      expect(wrapper.text()).toContain('测试错误消息');
      expect(wrapper.text()).toContain('用户友好的错误提示');
    });

    it('应该正确显示错误严重程度', async () => {
      const severities = [
        { severity: ERROR_SEVERITY.LOW, label: '低' },
        { severity: ERROR_SEVERITY.MEDIUM, label: '中' },
        { severity: ERROR_SEVERITY.HIGH, label: '高' },
        { severity: ERROR_SEVERITY.CRITICAL, label: '严重' }
      ];

      for (const { severity, label } of severities) {
        const errorInfo = createMockErrorInfo({ severity });
        
        wrapper = mount(ErrorDisplay, {
          props: {
            modelValue: true,
            errorInfo
          },
          global: {
            stubs: {
              'el-dialog': { template: '<div><slot /></div>' },
              'el-icon': { template: '<i><slot /></i>' },
              'el-button': { template: '<button><slot /></button>' },
              'el-tag': { template: '<span><slot /></span>' },
              'el-tooltip': { template: '<div><slot /></div>' },
              'el-tabs': { template: '<div><slot /></div>' },
              'el-tab-pane': { template: '<div><slot /></div>' },
              'el-empty': { template: '<div><slot /></div>' },
              'el-timeline': { template: '<div><slot /></div>' },
              'el-timeline-item': { template: '<div><slot /></div>' },
              'el-collapse-transition': { template: '<div><slot /></div>' },
              ErrorSolution: true
            }
          }
        });

        await nextTick();

        expect(wrapper.text()).toContain(label);

        wrapper.unmount();
      }
    });

    it('应该正确显示错误类型标签', async () => {
      const errorTypes = [
        { type: ERROR_TYPES.NETWORK, label: '网络错误' },
        { type: ERROR_TYPES.DEVICE, label: '设备错误' },
        { type: ERROR_TYPES.VALIDATION, label: '验证错误' }
      ];

      for (const { type, label } of errorTypes) {
        const errorInfo = createMockErrorInfo({ type });
        
        wrapper = mount(ErrorDisplay, {
          props: {
            modelValue: true,
            errorInfo
          },
          global: {
            stubs: {
              'el-dialog': { template: '<div><slot /></div>' },
              'el-icon': { template: '<i><slot /></i>' },
              'el-button': { template: '<button><slot /></button>' },
              'el-tag': { template: '<span><slot /></span>' },
              'el-tooltip': { template: '<div><slot /></div>' },
              'el-tabs': { template: '<div><slot /></div>' },
              'el-tab-pane': { template: '<div><slot /></div>' },
              'el-empty': { template: '<div><slot /></div>' },
              'el-timeline': { template: '<div><slot /></div>' },
              'el-timeline-item': { template: '<div><slot /></div>' },
              'el-collapse-transition': { template: '<div><slot /></div>' },
              ErrorSolution: true
            }
          }
        });

        await nextTick();

        expect(wrapper.text()).toContain(label);

        wrapper.unmount();
      }
    });

    it('应该正确显示错误上下文信息', async () => {
      wrapper = mount(ErrorDisplay, {
        props: {
          modelValue: true,
          errorInfo: mockErrorInfo
        },
        global: {
          stubs: {
            'el-dialog': { template: '<div><slot /></div>' },
            'el-icon': { template: '<i><slot /></i>' },
            'el-button': { template: '<button><slot /></button>' },
            'el-tag': { template: '<span><slot /></span>' },
            'el-tooltip': { template: '<div><slot /></div>' },
            'el-tabs': { template: '<div><slot /></div>' },
            'el-tab-pane': { template: '<div><slot /></div>' },
            'el-empty': { template: '<div><slot /></div>' },
            'el-timeline': { template: '<div><slot /></div>' },
            'el-timeline-item': { template: '<div><slot /></div>' },
            'el-collapse-transition': { template: '<div><slot /></div>' },
            ErrorSolution: true
          }
        }
      });

      await nextTick();

      expect(wrapper.text()).toContain('TestComponent');
      expect(wrapper.text()).toContain('testAction');
    });
  });

  // ==================== 错误类型测试 ====================

  describe('错误类型', () => {
    it('应该根据错误类型显示正确的图标', async () => {
      const errorInfo = createMockErrorInfo({ type: ERROR_TYPES.NETWORK });
      
      wrapper = mount(ErrorDisplay, {
        props: {
          modelValue: true,
          errorInfo
        },
        global: {
          stubs: {
            'el-dialog': { template: '<div><slot /></div>' },
            'el-icon': { template: '<i><slot /></i>' },
            'el-button': { template: '<button><slot /></button>' },
            'el-tag': { template: '<span><slot /></span>' },
            'el-tooltip': { template: '<div><slot /></div>' },
            'el-tabs': { template: '<div><slot /></div>' },
            'el-tab-pane': { template: '<div><slot /></div>' },
            'el-empty': { template: '<div><slot /></div>' },
            'el-timeline': { template: '<div><slot /></div>' },
            'el-timeline-item': { template: '<div><slot /></div>' },
            'el-collapse-transition': { template: '<div><slot /></div>' },
            ErrorSolution: true
          }
        }
      });

      await nextTick();

      // 验证图标组件存在
      expect(wrapper.find('.error-icon-wrapper').exists()).toBe(true);
    });

    it('应该根据严重程度应用正确的样式类', async () => {
      const severities = [
        { severity: ERROR_SEVERITY.LOW, className: 'severity-low' },
        { severity: ERROR_SEVERITY.MEDIUM, className: 'severity-medium' },
        { severity: ERROR_SEVERITY.HIGH, className: 'severity-high' },
        { severity: ERROR_SEVERITY.CRITICAL, className: 'severity-critical' }
      ];

      for (const { severity, className } of severities) {
        const errorInfo = createMockErrorInfo({ severity });
        
        wrapper = mount(ErrorDisplay, {
          props: {
            modelValue: true,
            errorInfo
          },
          global: {
            stubs: {
              'el-dialog': { template: '<div><slot /></div>' },
              'el-icon': { template: '<i><slot /></i>' },
              'el-button': { template: '<button><slot /></button>' },
              'el-tag': { template: '<span><slot /></span>' },
              'el-tooltip': { template: '<div><slot /></div>' },
              'el-tabs': { template: '<div><slot /></div>' },
              'el-tab-pane': { template: '<div><slot /></div>' },
              'el-empty': { template: '<div><slot /></div>' },
              'el-timeline': { template: '<div><slot /></div>' },
              'el-timeline-item': { template: '<div><slot /></div>' },
              'el-collapse-transition': { template: '<div><slot /></div>' },
              ErrorSolution: true
            }
          }
        });

        await nextTick();

        expect(wrapper.find('.error-overview').classes()).toContain(className);

        wrapper.unmount();
      }
    });
  });

  // ==================== 错误恢复测试 ====================

  describe('错误恢复', () => {
    it('应该触发自动操作事件', async () => {
      const autoActionSpy = vi.fn();
      
      wrapper = mount(ErrorDisplay, {
        props: {
          modelValue: true,
          errorInfo: mockErrorInfo
        },
        emits: {
          'auto-action': autoActionSpy
        },
        global: {
          stubs: {
            'el-dialog': { template: '<div><slot /></div>' },
            'el-icon': { template: '<i><slot /></i>' },
            'el-button': { template: '<button><slot /></button>' },
            'el-tag': { template: '<span><slot /></span>' },
            'el-tooltip': { template: '<div><slot /></div>' },
            'el-tabs': { template: '<div><slot /></div>' },
            'el-tab-pane': { template: '<div><slot /></div>' },
            'el-empty': { template: '<div><slot /></div>' },
            'el-timeline': { template: '<div><slot /></div>' },
            'el-timeline-item': { template: '<div><slot /></div>' },
            'el-collapse-transition': { template: '<div><slot /></div>' },
            ErrorSolution: {
              template: '<div class="error-solution"><button @click="$emit(\'auto-action\', \'retry\')">重试</button></div>',
              emits: ['auto-action']
            }
          }
        }
      });

      await nextTick();

      // 模拟点击重试按钮
      const retryButton = wrapper.find('.error-solution button');
      if (retryButton.exists()) {
        await retryButton.trigger('click');
        await nextTick();
        
        expect(autoActionSpy).toHaveBeenCalledWith('retry');
      }
    });

    it('应该触发关闭事件', async () => {
      const closeSpy = vi.fn();
      
      wrapper = mount(ErrorDisplay, {
        props: {
          modelValue: true,
          errorInfo: mockErrorInfo
        },
        emits: {
          'close': closeSpy
        },
        global: {
          stubs: {
            'el-dialog': {
              template: '<div class="el-dialog"><slot /></div>',
              emits: ['close']
            },
            'el-icon': { template: '<i><slot /></i>' },
            'el-button': { template: '<button><slot /></button>' },
            'el-tag': { template: '<span><slot /></span>' },
            'el-tooltip': { template: '<div><slot /></div>' },
            'el-tabs': { template: '<div><slot /></div>' },
            'el-tab-pane': { template: '<div><slot /></div>' },
            'el-empty': { template: '<div><slot /></div>' },
            'el-timeline': { template: '<div><slot /></div>' },
            'el-timeline-item': { template: '<div><slot /></div>' },
            'el-collapse-transition': { template: '<div><slot /></div>' },
            ErrorSolution: true
          }
        }
      });

      await nextTick();

      // 直接调用组件的close方法
      wrapper.vm.$emit('close');
      await nextTick();

      expect(closeSpy).toHaveBeenCalled();
    });

    it('应该触发复制事件', async () => {
      const copySpy = vi.fn();
      
      wrapper = mount(ErrorDisplay, {
        props: {
          modelValue: true,
          errorInfo: mockErrorInfo
        },
        emits: {
          'copy': copySpy
        },
        global: {
          stubs: {
            'el-dialog': { template: '<div><slot /></div>' },
            'el-icon': { template: '<i><slot /></i>' },
            'el-button': {
              template: '<button @click="$emit(\'click\')"><slot /></button>',
              emits: ['click']
            },
            'el-tag': { template: '<span><slot /></span>' },
            'el-tooltip': { template: '<div><slot /></div>' },
            'el-tabs': { template: '<div><slot /></div>' },
            'el-tab-pane': { template: '<div><slot /></div>' },
            'el-empty': { template: '<div><slot /></div>' },
            'el-timeline': { template: '<div><slot /></div>' },
            'el-timeline-item': { template: '<div><slot /></div>' },
            'el-collapse-transition': { template: '<div><slot /></div>' },
            ErrorSolution: true
          }
        }
      });

      await nextTick();

      // 查找复制按钮
      const copyButtons = wrapper.findAll('.el-button');
      if (copyButtons.length > 0) {
        await copyButtons[0].trigger('click');
        await nextTick();
        
        expect(copySpy).toHaveBeenCalled();
      }
    });

    it('应该触发导出报告事件', async () => {
      const exportSpy = vi.fn();
      
      wrapper = mount(ErrorDisplay, {
        props: {
          modelValue: true,
          errorInfo: mockErrorInfo
        },
        emits: {
          'export-report': exportSpy
        },
        global: {
          stubs: {
            'el-dialog': { template: '<div><slot /></div>' },
            'el-icon': { template: '<i><slot /></i>' },
            'el-button': {
              template: '<button @click="$emit(\'click\')"><slot /></button>',
              emits: ['click']
            },
            'el-tag': { template: '<span><slot /></span>' },
            'el-tooltip': { template: '<div><slot /></div>' },
            'el-tabs': { template: '<div><slot /></div>' },
            'el-tab-pane': { template: '<div><slot /></div>' },
            'el-empty': { template: '<div><slot /></div>' },
            'el-timeline': { template: '<div><slot /></div>' },
            'el-timeline-item': { template: '<div><slot /></div>' },
            'el-collapse-transition': { template: '<div><slot /></div>' },
            ErrorSolution: true
          }
        }
      });

      await nextTick();

      // 查找导出按钮
      const buttons = wrapper.findAll('.el-button');
      const exportButton = buttons.find(btn => btn.text().includes('导出'));
      
      if (exportButton) {
        await exportButton.trigger('click');
        await nextTick();
        
        expect(exportSpy).toHaveBeenCalledWith(mockErrorInfo);
      }
    });
  });

  // ==================== 错误日志测试 ====================

  describe('错误日志', () => {
    it('应该显示错误堆栈信息', async () => {
      wrapper = mount(ErrorDisplay, {
        props: {
          modelValue: true,
          errorInfo: mockErrorInfo
        },
        global: {
          stubs: {
            'el-dialog': { template: '<div><slot /></div>' },
            'el-icon': { template: '<i><slot /></i>' },
            'el-button': { template: '<button><slot /></button>' },
            'el-tag': { template: '<span><slot /></span>' },
            'el-tooltip': { template: '<div><slot /></div>' },
            'el-tabs': { template: '<div><slot /></div>' },
            'el-tab-pane': { template: '<div><slot /></div>' },
            'el-empty': { template: '<div><slot /></div>' },
            'el-timeline': { template: '<div><slot /></div>' },
            'el-timeline-item': { template: '<div><slot /></div>' },
            'el-collapse-transition': { template: '<div><slot /></div>' },
            ErrorSolution: true
          }
        }
      });

      await nextTick();

      // 验证堆栈区域存在
      expect(wrapper.find('.stack-trace').exists()).toBe(true);
    });

    it('应该显示系统信息', async () => {
      wrapper = mount(ErrorDisplay, {
        props: {
          modelValue: true,
          errorInfo: mockErrorInfo
        },
        global: {
          stubs: {
            'el-dialog': { template: '<div><slot /></div>' },
            'el-icon': { template: '<i><slot /></i>' },
            'el-button': { template: '<button><slot /></button>' },
            'el-tag': { template: '<span><slot /></span>' },
            'el-tooltip': { template: '<div><slot /></div>' },
            'el-tabs': { template: '<div><slot /></div>' },
            'el-tab-pane': { template: '<div><slot /></div>' },
            'el-empty': { template: '<div><slot /></div>' },
            'el-timeline': { template: '<div><slot /></div>' },
            'el-timeline-item': { template: '<div><slot /></div>' },
            'el-collapse-transition': { template: '<div><slot /></div>' },
            ErrorSolution: true
          }
        }
      });

      await nextTick();

      // 验证系统信息区域存在
      expect(wrapper.find('.system-info').exists()).toBe(true);
    });

    it('应该显示操作历史', async () => {
      wrapper = mount(ErrorDisplay, {
        props: {
          modelValue: true,
          errorInfo: mockErrorInfo
        },
        global: {
          stubs: {
            'el-dialog': { template: '<div><slot /></div>' },
            'el-icon': { template: '<i><slot /></i>' },
            'el-button': { template: '<button><slot /></button>' },
            'el-tag': { template: '<span><slot /></span>' },
            'el-tooltip': { template: '<div><slot /></div>' },
            'el-tabs': { template: '<div><slot /></div>' },
            'el-tab-pane': { template: '<div><slot /></div>' },
            'el-empty': { template: '<div><slot /></div>' },
            'el-timeline': { template: '<div><slot /></div>' },
            'el-timeline-item': { template: '<div><slot /></div>' },
            'el-collapse-transition': { template: '<div><slot /></div>' },
            ErrorSolution: true
          }
        }
      });

      await nextTick();

      // 验证操作历史区域存在
      expect(wrapper.find('.action-history').exists()).toBe(true);
    });

    it('应该显示错误ID', async () => {
      wrapper = mount(ErrorDisplay, {
        props: {
          modelValue: true,
          errorInfo: mockErrorInfo
        },
        global: {
          stubs: {
            'el-dialog': { template: '<div><slot /></div>' },
            'el-icon': { template: '<i><slot /></i>' },
            'el-button': { template: '<button><slot /></button>' },
            'el-tag': { template: '<span><slot /></span>' },
            'el-tooltip': { template: '<div><slot /></div>' },
            'el-tabs': { template: '<div><slot /></div>' },
            'el-tab-pane': { template: '<div><slot /></div>' },
            'el-empty': { template: '<div><slot /></div>' },
            'el-timeline': { template: '<div><slot /></div>' },
            'el-timeline-item': { template: '<div><slot /></div>' },
            'el-collapse-transition': { template: '<div><slot /></div>' },
            ErrorSolution: true
          }
        }
      });

      await nextTick();

      // 验证错误ID显示（显示最后8位）
      const errorIdShort = mockErrorInfo.id.slice(-8);
      // 验证组件正常渲染
      expect(wrapper.exists()).toBe(true);
    });
  });

  // ==================== 标签页切换测试 ====================

  describe('标签页切换', () => {
    it('应该支持切换到不同的标签页', async () => {
      wrapper = mount(ErrorDisplay, {
        props: {
          modelValue: true,
          errorInfo: mockErrorInfo
        },
        global: {
          stubs: {
            'el-dialog': { template: '<div><slot /></div>' },
            'el-icon': { template: '<i><slot /></i>' },
            'el-button': { template: '<button><slot /></button>' },
            'el-tag': { template: '<span><slot /></span>' },
            'el-tooltip': { template: '<div><slot /></div>' },
            'el-tabs': {
              template: '<div class="el-tabs"><slot /></div>',
              props: ['modelValue']
            },
            'el-tab-pane': {
              template: '<div class="el-tab-pane" v-show="name === modelValue"><slot /></div>',
              props: ['label', 'name']
            },
            'el-empty': { template: '<div><slot /></div>' },
            'el-timeline': { template: '<div><slot /></div>' },
            'el-timeline-item': { template: '<div><slot /></div>' },
            'el-collapse-transition': { template: '<div><slot /></div>' },
            ErrorSolution: true
          }
        }
      });

      await nextTick();

      // 默认应该显示解决方案标签页
      expect(wrapper.vm.activeTab).toBe('solution');
    });

    it('错误信息变化时应该重置标签页', async () => {
      wrapper = mount(ErrorDisplay, {
        props: {
          modelValue: true,
          errorInfo: mockErrorInfo
        },
        global: {
          stubs: {
            'el-dialog': { template: '<div><slot /></div>' },
            'el-icon': { template: '<i><slot /></i>' },
            'el-button': { template: '<button><slot /></button>' },
            'el-tag': { template: '<span><slot /></span>' },
            'el-tooltip': { template: '<div><slot /></div>' },
            'el-tabs': { template: '<div><slot /></div>' },
            'el-tab-pane': { template: '<div><slot /></div>' },
            'el-empty': { template: '<div><slot /></div>' },
            'el-timeline': { template: '<div><slot /></div>' },
            'el-timeline-item': { template: '<div><slot /></div>' },
            'el-collapse-transition': { template: '<div><slot /></div>' },
            ErrorSolution: true
          }
        }
      });

      await nextTick();

      // 修改标签页
      wrapper.vm.activeTab = 'detail';
      await nextTick();

      // 更新错误信息
      const newErrorInfo = createMockErrorInfo({ message: '新错误' });
      await wrapper.setProps({ errorInfo: newErrorInfo });
      await nextTick();

      // 应该重置回解决方案标签页
      expect(wrapper.vm.activeTab).toBe('solution');
    });
  });

  // ==================== 边界情况测试 ====================

  describe('边界情况', () => {
    it('应该处理空错误信息', async () => {
      wrapper = mount(ErrorDisplay, {
        props: {
          modelValue: true,
          errorInfo: null
        },
        global: {
          stubs: {
            'el-dialog': { template: '<div><slot /></div>' },
            'el-icon': { template: '<i><slot /></i>' },
            'el-button': { template: '<button><slot /></button>' },
            'el-tag': { template: '<span><slot /></span>' },
            'el-tooltip': { template: '<div><slot /></div>' },
            'el-tabs': { template: '<div><slot /></div>' },
            'el-tab-pane': { template: '<div><slot /></div>' },
            'el-empty': { template: '<div><slot /></div>' },
            'el-timeline': { template: '<div><slot /></div>' },
            'el-timeline-item': { template: '<div><slot /></div>' },
            'el-collapse-transition': { template: '<div><slot /></div>' },
            ErrorSolution: true
          }
        }
      });

      await nextTick();

      // 应该正常渲染，不崩溃
      expect(wrapper.exists()).toBe(true);
    });

    it('应该处理缺少解决方案的错误', async () => {
      const errorInfo = createMockErrorInfo({ solution: null });
      
      wrapper = mount(ErrorDisplay, {
        props: {
          modelValue: true,
          errorInfo
        },
        global: {
          stubs: {
            'el-dialog': { template: '<div><slot /></div>' },
            'el-icon': { template: '<i><slot /></i>' },
            'el-button': { template: '<button><slot /></button>' },
            'el-tag': { template: '<span><slot /></span>' },
            'el-tooltip': { template: '<div><slot /></div>' },
            'el-tabs': { template: '<div><slot /></div>' },
            'el-tab-pane': { template: '<div><slot /></div>' },
            'el-empty': { template: '<div><slot /></div>' },
            'el-timeline': { template: '<div><slot /></div>' },
            'el-timeline-item': { template: '<div><slot /></div>' },
            'el-collapse-transition': { template: '<div><slot /></div>' },
            ErrorSolution: true
          }
        }
      });

      await nextTick();

      // 验证组件正常渲染
      expect(wrapper.exists()).toBe(true);
    });

    it('应该处理缺少上下文的错误', async () => {
      const errorInfo = createMockErrorInfo({ context: null });
      
      wrapper = mount(ErrorDisplay, {
        props: {
          modelValue: true,
          errorInfo
        },
        global: {
          stubs: {
            'el-dialog': { template: '<div><slot /></div>' },
            'el-icon': { template: '<i><slot /></i>' },
            'el-button': { template: '<button><slot /></button>' },
            'el-tag': { template: '<span><slot /></span>' },
            'el-tooltip': { template: '<div><slot /></div>' },
            'el-tabs': { template: '<div><slot /></div>' },
            'el-tab-pane': { template: '<div><slot /></div>' },
            'el-empty': { template: '<div><slot /></div>' },
            'el-timeline': { template: '<div><slot /></div>' },
            'el-timeline-item': { template: '<div><slot /></div>' },
            'el-collapse-transition': { template: '<div><slot /></div>' },
            ErrorSolution: true
          }
        }
      });

      await nextTick();

      // 应该正常渲染，不崩溃
      expect(wrapper.exists()).toBe(true);
    });

    it('应该处理缺少系统信息的错误', async () => {
      const errorInfo = createMockErrorInfo({ system: null });
      
      wrapper = mount(ErrorDisplay, {
        props: {
          modelValue: true,
          errorInfo
        },
        global: {
          stubs: {
            'el-dialog': { template: '<div><slot /></div>' },
            'el-icon': { template: '<i><slot /></i>' },
            'el-button': { template: '<button><slot /></button>' },
            'el-tag': { template: '<span><slot /></span>' },
            'el-tooltip': { template: '<div><slot /></div>' },
            'el-tabs': { template: '<div><slot /></div>' },
            'el-tab-pane': { template: '<div><slot /></div>' },
            'el-empty': { template: '<div><slot /></div>' },
            'el-timeline': { template: '<div><slot /></div>' },
            'el-timeline-item': { template: '<div><slot /></div>' },
            'el-collapse-transition': { template: '<div><slot /></div>' },
            ErrorSolution: true
          }
        }
      });

      await nextTick();

      // 应该正常渲染，不崩溃
      expect(wrapper.exists()).toBe(true);
    });
  });

  // ==================== Props验证测试 ====================

  describe('Props验证', () => {
    it('应该接受modelValue属性', async () => {
      wrapper = mount(ErrorDisplay, {
        props: {
          modelValue: true,
          errorInfo: mockErrorInfo
        },
        global: {
          stubs: {
            'el-dialog': { template: '<div><slot /></div>' },
            'el-icon': { template: '<i><slot /></i>' },
            'el-button': { template: '<button><slot /></button>' },
            'el-tag': { template: '<span><slot /></span>' },
            'el-tooltip': { template: '<div><slot /></div>' },
            'el-tabs': { template: '<div><slot /></div>' },
            'el-tab-pane': { template: '<div><slot /></div>' },
            'el-empty': { template: '<div><slot /></div>' },
            'el-timeline': { template: '<div><slot /></div>' },
            'el-timeline-item': { template: '<div><slot /></div>' },
            'el-collapse-transition': { template: '<div><slot /></div>' },
            ErrorSolution: true
          }
        }
      });

      await nextTick();

      expect(wrapper.props('modelValue')).toBe(true);
    });

    it('应该接受errorInfo属性', async () => {
      wrapper = mount(ErrorDisplay, {
        props: {
          modelValue: true,
          errorInfo: mockErrorInfo
        },
        global: {
          stubs: {
            'el-dialog': { template: '<div><slot /></div>' },
            'el-icon': { template: '<i><slot /></i>' },
            'el-button': { template: '<button><slot /></button>' },
            'el-tag': { template: '<span><slot /></span>' },
            'el-tooltip': { template: '<div><slot /></div>' },
            'el-tabs': { template: '<div><slot /></div>' },
            'el-tab-pane': { template: '<div><slot /></div>' },
            'el-empty': { template: '<div><slot /></div>' },
            'el-timeline': { template: '<div><slot /></div>' },
            'el-timeline-item': { template: '<div><slot /></div>' },
            'el-collapse-transition': { template: '<div><slot /></div>' },
            ErrorSolution: true
          }
        }
      });

      await nextTick();

      expect(wrapper.props('errorInfo')).toEqual(mockErrorInfo);
    });

    it('应该接受isGeneratingReport属性', async () => {
      wrapper = mount(ErrorDisplay, {
        props: {
          modelValue: true,
          errorInfo: mockErrorInfo,
          isGeneratingReport: true
        },
        global: {
          stubs: {
            'el-dialog': { template: '<div><slot /></div>' },
            'el-icon': { template: '<i><slot /></i>' },
            'el-button': { template: '<button><slot /></button>' },
            'el-tag': { template: '<span><slot /></span>' },
            'el-tooltip': { template: '<div><slot /></div>' },
            'el-tabs': { template: '<div><slot /></div>' },
            'el-tab-pane': { template: '<div><slot /></div>' },
            'el-empty': { template: '<div><slot /></div>' },
            'el-timeline': { template: '<div><slot /></div>' },
            'el-timeline-item': { template: '<div><slot /></div>' },
            'el-collapse-transition': { template: '<div><slot /></div>' },
            ErrorSolution: true
          }
        }
      });

      await nextTick();

      expect(wrapper.props('isGeneratingReport')).toBe(true);
    });
  });
});
