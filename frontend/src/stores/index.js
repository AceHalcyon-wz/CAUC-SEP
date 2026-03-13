/**
 * @file index.js
 * @path src/stores/
 * @description Pinia Stores统一导出文件，提供所有状态管理的集中访问点
 * @author Agent
 * @date 2024-03-07
 * @dependencies pinia, ./motor, ./devices, ./electromagnet, ./piezo, ./temperature, ./ammeter, ./experiment, ./audit, ./layout
 */

// ==================== 设备控制相关Stores ====================

/**
 * 电机控制Store
 * @description 管理电机位置、速度、PR路径等状态
 */
export { useMotorStore } from './motor'

/**
 * 统一设备状态Store
 * @description 聚合管理所有设备的连接状态、运行状态
 */
export { useDevicesStore } from './devices'

/**
 * 电磁铁控制Store
 * @description 管理电流、磁场强度、扫描模式等状态
 */
export { useElectromagnetStore } from './electromagnet'

/**
 * 压电陶瓷控制Store
 * @description 管理电压、位移、校准等状态
 */
export { usePiezoStore } from './piezo'

/**
 * 温度控制Store
 * @description 管理温度、PID参数、程序控温等状态
 */
export { useTemperatureStore } from './temperature'

/**
 * 微电流采集Store
 * @description 管理数据采集、通道配置、实时监控等状态
 */
export { useAmmeterStore } from './ammeter'

// ==================== 实验管理相关Stores ====================

/**
 * 实验管理Store
 * @description 管理实验创建、控制、数据导出等状态
 */
export { useExperimentStore } from './experiment'

// ==================== 系统管理相关Stores ====================

/**
 * 审计日志Store
 * @description 管理日志查询、统计、导出等状态
 */
export { useAuditStore } from './audit'

/**
 * 系统配置Store
 * @description 管理系统配置的增删改查、导入导出、历史记录等功能
 */
export { useSettingsStore } from './settings'

/**
 * 布局状态Store
 * @description 管理侧边栏、顶部栏、状态栏等UI状态
 */
export { useLayoutStore } from './layout'

/**
 * 实时数据分析Store
 * @description 管理多设备数据同步、通道过滤、统计指标和导出功能
 */
export { useAnalysisStore } from './analysis'

/**
 * 操作反馈Store
 * @description 管理操作进度、成功/失败提示、撤销队列等状态
 */
export { useOperationStore } from './operation'

/**
 * 自动更新Store
 * @description 管理版本检查、更新下载、安装进度、备份管理等状态
 */
export { useUpdateStore, UPDATE_STATUS, UPDATE_PRIORITY } from './update'

// ==================== Store初始化辅助函数 ====================

/**
 * 初始化所有设备相关Stores
 * @description 在应用启动时调用，建立WebSocket连接并获取初始状态
 * @param {Object} options - 初始化选项
 * @param {boolean} options.autoConnect - 是否自动连接设备（默认false）
 * @returns {Promise<void>}
 */
export async function initializeDeviceStores(options = { autoConnect: false }) {
  const { autoConnect } = options

  // 动态导入stores（避免循环依赖）
  const { useDevicesStore } = await import('./devices')
  const { useMotorStore } = await import('./motor')
  const { useElectromagnetStore } = await import('./electromagnet')
  const { usePiezoStore } = await import('./piezo')
  const { useTemperatureStore } = await import('./temperature')
  const { useAmmeterStore } = await import('./ammeter')

  // 初始化统一设备状态Store
  const devicesStore = useDevicesStore()
  devicesStore.init()

  // 初始化各设备Store
  const motorStore = useMotorStore()
  const electromagnetStore = useElectromagnetStore()
  const piezoStore = usePiezoStore()
  const temperatureStore = useTemperatureStore()
  const ammeterStore = useAmmeterStore()

  // 调用各Store的init方法
  motorStore.init()
  electromagnetStore.init()
  piezoStore.init()
  temperatureStore.init()
  ammeterStore.init()

  // 如果配置了自动连接，则连接所有设备
  if (autoConnect) {
    try {
      await Promise.all([
        motorStore.connectMotor(),
        electromagnetStore.connectElectromagnet(),
        piezoStore.connect(),
        temperatureStore.connect()
      ])
    } catch (error) {
      console.error('[Stores] Auto-connect failed:', error)
    }
  }
}

/**
 * 初始化实验和系统Stores
 * @description 初始化实验管理、审计日志和系统配置
 * @returns {Promise<void>}
 */
export async function initializeSystemStores() {
  const { useExperimentStore } = await import('./experiment')
  const { useAuditStore } = await import('./audit')
  const { useSettingsStore } = await import('./settings')

  const experimentStore = useExperimentStore()
  const auditStore = useAuditStore()
  const settingsStore = useSettingsStore()

  experimentStore.init()
  await auditStore.init()
  await settingsStore.init()
}

/**
 * 清理所有Stores
 * @description 在应用卸载时调用，断开连接并清理资源
 * @returns {void}
 */
export function cleanupAllStores() {
  // 动态导入并清理所有stores
  import('./motor').then(({ useMotorStore }) => {
    useMotorStore().cleanup()
  })
  import('./devices').then(({ useDevicesStore }) => {
    useDevicesStore().cleanup()
  })
  import('./electromagnet').then(({ useElectromagnetStore }) => {
    useElectromagnetStore().cleanup()
  })
  import('./piezo').then(({ usePiezoStore }) => {
    usePiezoStore().cleanup()
  })
  import('./temperature').then(({ useTemperatureStore }) => {
    useTemperatureStore().cleanup()
  })
  import('./ammeter').then(({ useAmmeterStore }) => {
    useAmmeterStore().cleanup()
  })
  import('./experiment').then(({ useExperimentStore }) => {
    useExperimentStore().cleanup()
  })
  import('./audit').then(({ useAuditStore }) => {
    useAuditStore().cleanup()
  })
  import('./settings').then(({ useSettingsStore }) => {
    useSettingsStore().cleanup()
  })
}

/**
 * 重置所有设备状态
 * @description 在需要重置系统状态时调用
 * @returns {void}
 */
export function resetAllDeviceStates() {
  import('./motor').then(({ useMotorStore }) => {
    const store = useMotorStore()
    store.disconnectMotor()
  })
  import('./electromagnet').then(({ useElectromagnetStore }) => {
    const store = useElectromagnetStore()
    store.disconnectElectromagnet()
  })
  import('./piezo').then(({ usePiezoStore }) => {
    const store = usePiezoStore()
    store.disconnect()
  })
  import('./temperature').then(({ useTemperatureStore }) => {
    const store = useTemperatureStore()
    store.disconnect()
  })
}

/**
 * 获取所有设备的连接状态
 * @description 用于状态栏显示
 * @returns {Object} 设备连接状态映射
 */
export function getAllDeviceConnectionStatus() {
  const { useDevicesStore } = require('./devices')
  const devicesStore = useDevicesStore()

  return {
    motor: devicesStore.devices.motor?.isConnected || false,
    electromagnet: devicesStore.devices.electromagnet?.isConnected || false,
    piezo: devicesStore.devices.piezo?.isConnected || false,
    temperature: devicesStore.devices.temperature?.isConnected || false,
    ammeter: devicesStore.devices.ammeter?.isConnected || false,
    allConnected: devicesStore.allConnected,
    connectedCount: devicesStore.connectedCount,
    totalDevicesCount: devicesStore.totalDevicesCount
  }
}
