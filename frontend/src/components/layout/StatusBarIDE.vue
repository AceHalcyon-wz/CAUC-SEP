/**
 * @file StatusBarIDE.vue
 * @path src/components/layout/
 * @description IDE风格底部状态栏组件 - 参考VS Code/PyCharm状态栏设计
 * @author Agent
 * @date 2024-03-15
 * @version 3.5.2
 */

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  WarningOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
  ApiOutlined,
  BranchesOutlined,
  ClockCircleOutlined,
  BellOutlined,
  SettingOutlined,
  BugOutlined,
  ThunderboltOutlined,
  SafetyOutlined,
  GlobalOutlined,
  SyncOutlined,
  WifiOutlined
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { useDevicesStore } from '../../stores/devices'
import { wsClient } from '../../api/websocket'

const route = useRoute()
const router = useRouter()
const devicesStore = useDevicesStore()

const currentTime = ref('')
const cpuUsage = ref(0)
const memoryUsage = ref(0)
let timeInterval = null

/**
 * WebSocket连接状态
 */
const wsStatus = computed(() => {
  if (devicesStore.wsConnected) {
    return { icon: CheckCircleOutlined, text: 'WS已连接', type: 'success' }
  }
  return { icon: CloseCircleOutlined, text: 'WS未连接', type: 'error' }
})

/**
 * 设备连接状态
 */
const deviceStatus = computed(() => {
  const connected = devicesStore.connectedDevices?.length || 0
  const total = devicesStore.totalDevicesCount || 5
  const percentage = Math.round((connected / total) * 100)
  
  if (connected === total) {
    return { icon: CheckCircleOutlined, text: `${connected}/${total}`, type: 'success' }
  } else if (connected > 0) {
    return { icon: WarningOutlined, text: `${connected}/${total}`, type: 'warning' }
  }
  return { icon: CloseCircleOutlined, text: `${connected}/${total}`, type: 'error' }
})

/**
 * 系统健康状态
 */
const systemHealth = computed(() => {
  const health = devicesStore.systemHealth
  const healthMap = {
    excellent: { icon: SafetyOutlined, text: '系统健康', type: 'success' },
    good: { icon: SafetyOutlined, text: '系统良好', type: 'success' },
    warning: { icon: WarningOutlined, text: '系统警告', type: 'warning' },
    critical: { icon: CloseCircleOutlined, text: '系统异常', type: 'error' },
    unknown: { icon: WarningOutlined, text: '状态未知', type: 'default' }
  }
  return healthMap[health] || healthMap.unknown
})

/**
 * 告警数量
 */
const alarmCount = computed(() => devicesStore.unacknowledgedAlarmsCount || 0)

/**
 * 当前页面信息
 */
const pageInfo = computed(() => {
  return route.meta?.title || 'CAUC-SEP'
})

/**
 * 更新时间
 */
function updateTime() {
  currentTime.value = new Date().toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

/**
 * 模拟系统资源监控
 */
function updateSystemResources() {
  cpuUsage.value = Math.floor(Math.random() * 30) + 10
  memoryUsage.value = Math.floor(Math.random() * 40) + 30
}

/**
 * 重新连接WebSocket
 */
function reconnectWebSocket() {
  message.loading('正在重新连接...')
  wsClient.disconnect()
  setTimeout(() => {
    wsClient.connect()
      .then(() => message.success('连接成功'))
      .catch(() => message.error('连接失败'))
  }, 500)
}

/**
 * 打开设备连接页面
 */
function openDeviceConnection() {
  router.push('/device/connection')
}

/**
 * 打开设置页面
 */
function openSettings() {
  router.push('/settings/config')
}

/**
 * 查看告警
 */
function viewAlarms() {
  if (alarmCount.value > 0) {
    router.push('/experiment/safety')
  }
}

/**
 * 格式化数字
 */
function formatNumber(num) {
  return num.toString().padStart(2, '0')
}

onMounted(() => {
  updateTime()
  timeInterval = setInterval(updateTime, 1000)
  updateSystemResources()
  setInterval(updateSystemResources, 5000)
})

onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval)
  }
})
</script>

<template>
  <footer class="ide-statusbar">
    <!-- 左侧状态组 -->
    <div class="statusbar__left">
      <!-- 系统健康状态 -->
      <button
        class="status-item"
        :class="`status-item--${systemHealth.type}`"
        title="系统健康状态 - 点击查看详情"
        @click="openSettings"
      >
        <component :is="systemHealth.icon" />
        <span class="status-text">{{ systemHealth.text }}</span>
      </button>

      <!-- 设备状态 -->
      <button
        class="status-item"
        :class="`status-item--${deviceStatus.type}`"
        title="设备连接状态 - 点击管理设备"
        @click="openDeviceConnection"
      >
        <DatabaseOutlined />
        <span class="status-text">设备 {{ deviceStatus.text }}</span>
      </button>

      <!-- WebSocket状态 -->
      <button
        class="status-item"
        :class="`status-item--${wsStatus.type}`"
        :title="`WebSocket: ${wsStatus.text} - 点击重新连接`"
        @click="reconnectWebSocket"
      >
        <component :is="wsStatus.icon" />
        <span class="status-text">{{ wsStatus.text }}</span>
        <SyncOutlined
          v-if="!devicesStore.wsConnected"
          class="reconnect-icon"
        />
      </button>

      <!-- 告警 -->
      <button
        v-if="alarmCount > 0"
        class="status-item status-item--warning"
        title="未确认告警 - 点击查看"
        @click="viewAlarms"
      >
        <BellOutlined />
        <span class="status-text">{{ alarmCount }} 条告警</span>
      </button>
    </div>

    <!-- 中间信息 -->
    <div class="statusbar__center">
      <!-- 当前页面 -->
      <span class="status-item status-item--info">
        <span class="status-text">{{ pageInfo }}</span>
      </span>
    </div>

    <!-- 右侧状态组 -->
    <div class="statusbar__right">
      <!-- CPU使用率 -->
      <button
        class="status-item status-item--info"
        title="CPU使用率"
        @click="openSettings"
      >
        <ThunderboltOutlined />
        <span class="status-text">CPU {{ cpuUsage }}%</span>
      </button>

      <!-- 内存使用 -->
      <button
        class="status-item status-item--info"
        title="内存使用率"
        @click="openSettings"
      >
        <DatabaseOutlined />
        <span class="status-text">MEM {{ memoryUsage }}%</span>
      </button>

      <!-- 分隔线 -->
      <div class="statusbar__divider" />

      <!-- 语言 -->
      <button
        class="status-item status-item--info"
        title="语言设置"
        @click="openSettings"
      >
        <GlobalOutlined />
        <span class="status-text">简体中文</span>
      </button>

      <!-- 时间 -->
      <button class="status-item status-item--info">
        <ClockCircleOutlined />
        <span class="status-text">{{ currentTime }}</span>
      </button>
    </div>
  </footer>
</template>

<style scoped>
.ide-statusbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 24px;
  padding: 0 var(--spacing-3);
  background: var(--color-primary-600);
  color: white;
  font-size: 12px;
  user-select: none;
  position: sticky;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: var(--z-index-sticky);
  flex-shrink: 0;
}

.statusbar__left,
.statusbar__right {
  display: flex;
  align-items: center;
  gap: 0;
}

.statusbar__center {
  display: flex;
  align-items: center;
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.status-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
  padding: 0 var(--spacing-2);
  height: 24px;
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.85);
  font-size: 12px;
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.status-item:hover {
  background: rgba(255, 255, 255, 0.15);
  color: white;
}

.status-item--success {
  color: #86efac;
}

.status-item--success:hover {
  background: rgba(134, 239, 172, 0.15);
}

.status-item--warning {
  color: #fcd34d;
}

.status-item--warning:hover {
  background: rgba(252, 211, 77, 0.15);
}

.status-item--error {
  color: #fca5a5;
}

.status-item--error:hover {
  background: rgba(252, 165, 165, 0.15);
}

.status-item--info {
  color: rgba(255, 255, 255, 0.85);
}

.status-text {
  font-weight: var(--font-weight-medium);
}

.reconnect-icon {
  font-size: 10px;
  animation: spin 1s linear infinite;
  margin-left: 2px;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.statusbar__divider {
  width: 1px;
  height: 16px;
  background: rgba(255, 255, 255, 0.2);
  margin: 0 var(--spacing-1);
}

/* 响应式 */
@media (max-width: 768px) {
  .ide-statusbar {
    padding: 0 var(--spacing-2);
  }

  .status-text {
    display: none;
  }

  .statusbar__center {
    position: static;
    transform: none;
  }

  .statusbar__divider {
    display: none;
  }
}

@media (max-width: 480px) {
  .statusbar__left {
    gap: 0;
  }

  .status-item {
    padding: 0 var(--spacing-1);
  }
}
</style>
