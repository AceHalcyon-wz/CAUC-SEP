/**
 * @file setup.js
 * @path frontend/src/tests/
 * @description Vitest测试环境设置文件
 * 
 * 本配置文件用于设置Vitest单元测试的运行环境，包括：
 * - Vue Test Utils全局配置
 * - Element Plus组件库注册
 * - IndexedDB Mock实现（使用fake-indexeddb）
 * - HTMLCanvasElement Mock实现
 * - window.matchMedia Mock实现
 * - ResizeObserver和IntersectionObserver Mock实现
 * - navigator.connection Mock实现
 * - localStorage Mock实现
 * - console方法Mock实现
 * - 测试后清理机制
 * 
 * @author Agent
 * @date 2024-03-07
 * @updated 2026-03-16 添加fake-indexeddb支持
 * @dependencies @vue/test-utils, vitest, element-plus, fake-indexeddb
 */

import { config } from '@vue/test-utils';
import { vi, afterEach } from 'vitest';
import ElementPlus from 'element-plus';
import 'fake-indexeddb/auto';

/**
 * 注册Element Plus为全局插件
 * 所有组件测试将自动获得Element Plus组件支持
 */
config.global.plugins = [ElementPlus];

/**
 * Mock HTMLCanvasElement.getContext方法
 * 
 * 由于jsdom环境不支持Canvas API，需要模拟完整的Canvas上下文
 * 包括绑定、填充、描边、文本测量等常用方法
 */
HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
  fillRect: vi.fn(),
  clearRect: vi.fn(),
  getImageData: vi.fn(() => ({
    data: new Uint8ClampedArray(4),
  })),
  putImageData: vi.fn(),
  createImageData: vi.fn(() => ({
    data: new Uint8ClampedArray(4),
  })),
  setTransform: vi.fn(),
  drawImage: vi.fn(),
  save: vi.fn(),
  restore: vi.fn(),
  scale: vi.fn(),
  rotate: vi.fn(),
  translate: vi.fn(),
  transform: vi.fn(),
  beginPath: vi.fn(),
  moveTo: vi.fn(),
  lineTo: vi.fn(),
  closePath: vi.fn(),
  stroke: vi.fn(),
  fill: vi.fn(),
  arc: vi.fn(),
  rect: vi.fn(),
  clip: vi.fn(),
  measureText: vi.fn(() => ({ width: 0 })),
  fillText: vi.fn(),
  strokeText: vi.fn(),
  createLinearGradient: vi.fn(() => ({
    addColorStop: vi.fn(),
  })),
  createRadialGradient: vi.fn(() => ({
    addColorStop: vi.fn(),
  })),
  createPattern: vi.fn(),
  setLineDash: vi.fn(),
  getLineDash: vi.fn(() => []),
  lineDashOffset: 0,
  font: '',
  textAlign: '',
  textBaseline: '',
  fillStyle: '',
  strokeStyle: '',
  lineWidth: 1,
  lineCap: '',
  lineJoin: '',
  globalAlpha: 1,
  globalCompositeOperation: '',
}));

/**
 * Mock HTMLCanvasElement.toDataURL方法
 * 用于图表导出功能测试
 */
HTMLCanvasElement.prototype.toDataURL = vi.fn(() => 'data:image/png;base64,mock');

/**
 * Mock window.matchMedia方法
 * 
 * 模拟CSS媒体查询功能，用于响应式设计测试
 * 返回一个包含完整API的mock对象
 * 
 * @param {string} query - 媒体查询字符串
 * @returns {Object} MediaQueryList对象
 */
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

/**
 * Mock ResizeObserver API
 * 
 * 模拟元素尺寸变化观察功能，用于响应式布局测试
 * 
 * @returns {ResizeObserver} ResizeObserver实例
 */
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

/**
 * Mock IntersectionObserver API
 * 
 * 模拟元素可见性观察功能，用于懒加载和虚拟滚动测试
 * 
 * @returns {IntersectionObserver} IntersectionObserver实例
 */
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

/**
 * Mock navigator.connection API
 * 
 * 模拟网络连接信息API，用于网络状态检测功能测试
 * 包含网络类型、下行速度、往返时间等信息
 */
Object.defineProperty(navigator, 'connection', {
  writable: true,
  value: {
    effectiveType: '4g',
    downlink: 10,
    rtt: 50,
    saveData: false,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  },
});

/**
 * Mock navigator.onLine属性
 * 
 * 模拟在线状态，用于离线功能测试
 */
Object.defineProperty(navigator, 'onLine', {
  writable: true,
  value: true,
});

/**
 * Mock localStorage API
 * 
 * 模拟本地存储功能，用于持久化数据测试
 * 
 * @type {Object}
 */
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

/**
 * Mock console方法
 * 
 * 屏蔽测试过程中的控制台输出，保持测试输出清洁
 * 保留部分console方法用于调试
 */
global.console = {
  ...console,
  error: vi.fn(),
  warn: vi.fn(),
  log: vi.fn(),
};

/**
 * 测试后清理钩子
 * 
 * 每个测试用例执行后自动清理所有mock
 * 确保测试之间的隔离性和独立性
 */
afterEach(() => {
  vi.clearAllMocks();
});
