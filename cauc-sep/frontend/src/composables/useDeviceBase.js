/**
 * @file useDeviceBase.js
 * @path src/composables/
 * @description 设备状态管理通用组合式函数，封装设备连接、状态、告警、数据新鲜度等通用逻辑
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue
 */

import { ref, computed } from 'vue';
import { useDataFreshness, FRESHNESS_LEVEL } from './useDataFreshness';

/**
 * 设备状态管理组合式函数
 * 
 * @param {string} deviceName - 设备名称，用于日志和调试标识
 * @param {Object} options - 配置选项
 * @param {Object} [options.freshnessConfig] - 数据新鲜度配置
 * @returns {Object} 设备状态管理对象，包含响应式状态和操作方法
 * 
 * @example
 * ```javascript
 * const {
 *   isConnected,
 *   isConnecting,
 *   status,
 *   canControl,
 *   showError,
 *   updateStatus,
 *   freshness
 * } = useDeviceBase('TemperatureController')
 * 
 * // 更新设备状态
 * updateStatus('ready')
 * 
 * // 显示错误信息
 * showError('连接失败，请检查网络')
 * 
 * // 更新数据新鲜度
 * freshness.updateTimestamp()
 * ```
 */
export function useDeviceBase(deviceName, options = {}) {
  const {
    freshnessConfig = {}
  } = options;

  // ==================== 响应式状态 ====================

  /**
   * 设备连接状态
   * @type {import('vue').Ref<boolean>}
   */
  const isConnected = ref(false);

  /**
   * 设备正在连接中标志
   * @type {import('vue').Ref<boolean>}
   */
  const isConnecting = ref(false);

  /**
   * 设备当前状态
   * @type {import('vue').Ref<string>}
   * @description 可能的值: 'disconnected' | 'connecting' | 'ready' | 'busy' | 'error'
   */
  const status = ref('disconnected');

  /**
   * 告警消息内容
   * @type {import('vue').Ref<string>}
   */
  const alarmMessage = ref('');

  /**
   * WebSocket连接状态
   * @type {import('vue').Ref<boolean>}
   */
  const wsConnected = ref(false);

  /**
   * 加载状态集合
   * @type {import('vue').Ref<Object<string, boolean>>}
   * @description 用于管理多个操作的加载状态，如 { connect: true, update: false }
   */
  const loading = ref({});

  /**
   * 数据新鲜度管理
   */
  const freshness = useDataFreshness(freshnessConfig);

  // ==================== 计算属性 ====================

  /**
   * 是否允许控制设备
   * 
   * @type {import('vue').ComputedRef<boolean>}
   * @description 满足条件：已连接 && 非连接中 && 状态为ready
   */
  const canControl = computed(() => {
    return isConnected.value && !isConnecting.value && status.value === 'ready';
  });

  /**
   * 设备状态类型（用于UI样式）
   */
  const statusType = computed(() => {
    switch (status.value) {
      case 'ready':
        return 'success';
      case 'busy':
        return 'info';
      case 'error':
      case 'emergency_stop':
        return 'danger';
      case 'connecting':
        return 'warning';
      default:
        return 'info';
    }
  });

  /**
   * 设备状态文本
   */
  const statusText = computed(() => {
    const statusMap = {
      'disconnected': '未连接',
      'connecting': '连接中',
      'ready': '就绪',
      'busy': '忙碌',
      'error': '错误',
      'emergency_stop': '急停'
    };
    return statusMap[status.value] || status.value;
  });

  // ==================== 方法 ====================

  /**
   * 显示错误消息（5秒后自动清除）
   * 
   * @param {string} message - 错误消息内容
   * 
   * @example
   * showError('温度传感器读取失败')
   */
  function showError(message) {
    alarmMessage.value = message;
    
    // 5秒后自动清除告警（仅当消息未变更时）
    setTimeout(() => {
      if (alarmMessage.value === message) {
        alarmMessage.value = '';
      }
    }, 5000);
  }

  /**
   * 手动清除告警消息
   */
  function clearAlarm() {
    alarmMessage.value = '';
  }

  /**
   * 设置指定操作的加载状态
   * 
   * @param {string} key - 操作标识（如 'connect', 'update', 'fetch'）
   * @param {boolean} value - 加载状态
   * 
   * @example
   * setLoading('connect', true)
   * // 执行连接操作...
   * setLoading('connect', false)
   */
  function setLoading(key, value) {
    loading.value = { ...loading.value, [key]: value };
  }

  /**
   * 重置所有状态到初始值
   * 
   * @description 通常在设备断开连接或组件卸载时调用
   */
  function resetState() {
    isConnected.value = false;
    isConnecting.value = false;
    status.value = 'disconnected';
    alarmMessage.value = '';
    wsConnected.value = false;
    loading.value = {};
    freshness.reset();
  }

  /**
   * 更新设备状态
   * 
   * @param {string} newStatus - 新状态值
   * 
   * @description
   * - 自动同步 isConnected 状态
   * - 当状态为 'ready' 或 'busy' 时，isConnected 为 true
   * 
   * @example
   * updateStatus('ready')  // isConnected 自动变为 true
   * updateStatus('error')  // isConnected 自动变为 false
   */
  function updateStatus(newStatus) {
    status.value = newStatus;
    
    // 根据状态自动更新连接标志
    isConnected.value = newStatus === 'ready' || newStatus === 'busy';
  }

  /**
   * 更新数据时间戳（数据新鲜度）
   */
  function updateDataTimestamp(timestamp) {
    freshness.updateTimestamp(timestamp);
  }

  // ==================== 返回值 ====================

  return {
    // 基础状态
    isConnected,
    isConnecting,
    status,
    alarmMessage,
    wsConnected,
    loading,
    canControl,
    
    // 状态计算属性
    statusType,
    statusText,
    
    // 数据新鲜度
    freshness,
    freshnessLevel: freshness.freshnessLevel,
    freshnessText: freshness.freshnessText,
    freshnessStatusType: freshness.freshnessStatusType,
    isDataExpired: freshness.isExpired,
    needsFreshnessWarning: freshness.needsWarning,
    
    // 基础方法
    showError,
    clearAlarm,
    setLoading,
    resetState,
    updateStatus,
    updateDataTimestamp
  };
}
