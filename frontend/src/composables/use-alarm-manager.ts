/**
 * @file use-alarm-manager.ts
 * @path src/composables/use-alarm-manager.ts
 * @description 报警管理组合式函数
 * @author Agent
 * @date 2026-03-25
 * @safety: 报警信息必须实时显示，支持一键清除报警
 */

import { ref, computed, type Ref, type ComputedRef } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'

/**
 * 报警信息
 */
export interface AlarmInfo {
  /** 报警ID */
  id: string
  /** 报警代码 */
  code: number
  /** 报警消息 */
  message: string
  /** 报警级别 */
  level: 'info' | 'warning' | 'danger' | 'critical'
  /** 报警时间 */
  timestamp: Date
  /** 设备名称 */
  deviceName?: string
  /** 是否已确认 */
  acknowledged: boolean
}

/**
 * 报警管理选项
 */
export interface UseAlarmManagerOptions {
  /** 最大报警数量 */
  maxAlarms?: number
  /** 是否显示通知 */
  showNotification?: boolean
  /** 是否播放声音 */
  playSound?: boolean
}

/**
 * 报警管理返回值
 */
export interface UseAlarmManagerReturn {
  /** 报警列表 */
  alarms: Ref<AlarmInfo[]>
  /** 是否有报警 */
  hasAlarms: ComputedRef<boolean>
  /** 最高报警级别 */
  highestLevel: ComputedRef<AlarmInfo['level'] | null>
  /** 未确认报警数量 */
  unacknowledgedCount: ComputedRef<number>
  /** 添加报警 */
  addAlarm: (alarm: Omit<AlarmInfo, 'id' | 'timestamp' | 'acknowledged'>) => void
  /** 确认报警 */
  acknowledgeAlarm: (alarmId: string) => void
  /** 清除报警 */
  clearAlarm: (alarmId: string) => void
  /** 清除所有报警 */
  clearAllAlarms: () => void
  /** 确认所有报警 */
  acknowledgeAllAlarms: () => void
}

let alarmIdCounter = 0

/**
 * 报警管理组合式函数
 * 
 * @param options - 配置选项
 * @returns 报警管理方法和状态
 */
export function useAlarmManager(options: UseAlarmManagerOptions = {}): UseAlarmManagerReturn {
  const {
    maxAlarms = 50,
    showNotification = true,
    playSound = false,
  } = options

  const alarms = ref<AlarmInfo[]>([])

  const hasAlarms = computed(() => alarms.value.length > 0)

  const highestLevel = computed((): AlarmInfo['level'] | null => {
    if (alarms.value.length === 0) return null

    const levelPriority: Record<AlarmInfo['level'], number> = {
      info: 0,
      warning: 1,
      danger: 2,
      critical: 3,
    }

    return alarms.value.reduce((highest, alarm) => {
      return levelPriority[alarm.level] > levelPriority[highest] ? alarm.level : highest
    }, 'info' as AlarmInfo['level'])
  })

  const unacknowledgedCount = computed(() => {
    return alarms.value.filter((a) => !a.acknowledged).length
  })

  function addAlarm(alarm: Omit<AlarmInfo, 'id' | 'timestamp' | 'acknowledged'>): void {
    const newAlarm: AlarmInfo = {
      ...alarm,
      id: `alarm-${++alarmIdCounter}`,
      timestamp: new Date(),
      acknowledged: false,
    }

    if (alarms.value.length >= maxAlarms) {
      alarms.value.shift()
    }

    alarms.value.push(newAlarm)

    if (showNotification) {
      const title = alarm.deviceName ? `${alarm.deviceName} 报警` : '设备报警'
      ElNotification({
        title,
        message: `[${alarm.code}] ${alarm.message}`,
        type: alarm.level === 'critical' || alarm.level === 'danger' ? 'error' : 'warning',
        duration: alarm.level === 'critical' ? 0 : 5000,
      })
    }

    if (playSound) {
      playAlarmSound(alarm.level)
    }
  }

  function acknowledgeAlarm(alarmId: string): void {
    const alarm = alarms.value.find((a) => a.id === alarmId)
    if (alarm) {
      alarm.acknowledged = true
    }
  }

  function clearAlarm(alarmId: string): void {
    const index = alarms.value.findIndex((a) => a.id === alarmId)
    if (index !== -1) {
      alarms.value.splice(index, 1)
    }
  }

  function clearAllAlarms(): void {
    alarms.value = []
    ElMessage.success('已清除所有报警')
  }

  function acknowledgeAllAlarms(): void {
    alarms.value.forEach((alarm) => {
      alarm.acknowledged = true
    })
    ElMessage.success('已确认所有报警')
  }

  function playAlarmSound(level: AlarmInfo['level']): void {
    // TODO: 实现报警声音播放
    console.log(`[useAlarmManager] 播放报警声音: ${level}`)
  }

  return {
    alarms,
    hasAlarms,
    highestLevel,
    unacknowledgedCount,
    addAlarm,
    acknowledgeAlarm,
    clearAlarm,
    clearAllAlarms,
    acknowledgeAllAlarms,
  }
}

export default useAlarmManager
