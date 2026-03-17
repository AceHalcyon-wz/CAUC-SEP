/**
 * @file index.js
 * @path src/router/
 * @description 路由配置 - IDE风格优化版（支持预加载、骨架屏、快速切换）
 * @author Agent
 * @date 2024-03-15
 * @version 3.6.0
 */

import { createRouter, createWebHistory } from 'vue-router'

const LayoutIDE = () => import('../views/LayoutIDE.vue')

const DeviceStatus = () => import('../views/device/Status.vue')
const MotorControl = () => import('../views/experiment/MotorControl.vue')
const ElectromagnetControl = () => import('../views/experiment/ElectromagnetControl.vue')
const TemperatureControl = () => import('../views/experiment/TemperatureControl.vue')
const PiezoControl = () => import('../views/experiment/PiezoControl.vue')
const AmmeterControl = () => import('../views/experiment/AmmeterControl.vue')
const RealtimeAnalysis = () => import('../views/analysis/Realtime.vue')
const HistoryAnalysis = () => import('../views/analysis/History.vue')
const ChartsAnalysis = () => import('../views/analysis/Charts.vue')
const SettingsAudit = () => import('../views/settings/Audit.vue')
const SettingsConfig = () => import('../views/settings/Config.vue')
const SettingsProfile = () => import('../views/settings/Profile.vue')
const SettingsAbout = () => import('../views/settings/About.vue')
const SettingsPerformance = () => import('../views/settings/Performance.vue')
const HelpDocs = () => import('../views/settings/HelpDocs.vue')
const UserManagement = () => import('../views/settings/UserManagement.vue')
const DeviceConnection = () => import('../views/device/Connection.vue')
const DevicePRPath = () => import('../views/device/PRPath.vue')
const SafetyPanel = () => import('../views/experiment/SafetyPanel.vue')
const NotFound = () => import('../views/NotFound.vue')

const routes = [
  {
    path: '/',
    component: LayoutIDE,
    redirect: '/device/status',
    children: [
      {
        path: 'device/status',
        name: 'DeviceStatus',
        component: DeviceStatus,
        meta: {
          title: '设备状态',
          icon: 'DashboardOutlined',
          preload: true,
          skeleton: 'default'
        }
      },
      {
        path: 'device/connection',
        name: 'DeviceConnection',
        component: DeviceConnection,
        meta: {
          title: '设备连接',
          icon: 'LinkOutlined',
          skeleton: 'default'
        }
      },
      {
        path: 'device/prpath',
        name: 'DevicePRPath',
        component: DevicePRPath,
        meta: {
          title: 'PR路径',
          icon: 'NodeIndexOutlined',
          skeleton: 'default'
        }
      },

      {
        path: 'experiment/motor',
        name: 'MotorControl',
        component: MotorControl,
        meta: {
          title: '电机控制',
          icon: 'ThunderboltOutlined',
          preload: true,
          skeleton: 'control'
        }
      },

      {
        path: 'experiment/electromagnet',
        name: 'ElectromagnetControl',
        component: ElectromagnetControl,
        meta: {
          title: '电磁铁控制',
          icon: 'AimOutlined',
          preload: true,
          skeleton: 'control'
        }
      },

      {
        path: 'experiment/temperature',
        name: 'TemperatureControl',
        component: TemperatureControl,
        meta: {
          title: '温度控制',
          icon: 'FireOutlined',
          preload: true,
          skeleton: 'control'
        }
      },

      {
        path: 'experiment/piezo',
        name: 'PiezoControl',
        component: PiezoControl,
        meta: {
          title: '压电陶瓷',
          icon: 'CompressOutlined',
          preload: true,
          skeleton: 'control'
        }
      },

      {
        path: 'experiment/ammeter',
        name: 'AmmeterControl',
        component: AmmeterControl,
        meta: {
          title: '微电流计',
          icon: 'LineChartOutlined',
          preload: true,
          skeleton: 'control'
        }
      },

      {
        path: 'experiment/safety',
        name: 'SafetyPanel',
        component: SafetyPanel,
        meta: {
          title: '安全面板',
          icon: 'SafetyOutlined',
          skeleton: 'default'
        }
      },

      {
        path: 'analysis/realtime',
        name: 'RealtimeAnalysis',
        component: RealtimeAnalysis,
        meta: {
          title: '实时分析',
          icon: 'LineChartOutlined',
          preload: true,
          skeleton: 'analysis'
        }
      },
      {
        path: 'analysis/history',
        name: 'HistoryAnalysis',
        component: HistoryAnalysis,
        meta: {
          title: '历史查询',
          icon: 'HistoryOutlined',
          skeleton: 'analysis'
        }
      },
      {
        path: 'analysis/charts',
        name: 'ChartsAnalysis',
        component: ChartsAnalysis,
        meta: {
          title: '图表分析',
          icon: 'BarChartOutlined',
          skeleton: 'analysis'
        }
      },

      {
        path: 'settings/audit',
        name: 'SettingsAudit',
        component: SettingsAudit,
        meta: {
          title: '审计日志',
          icon: 'FileTextOutlined',
          skeleton: 'settings'
        }
      },
      {
        path: 'settings/config',
        name: 'SettingsConfig',
        component: SettingsConfig,
        meta: {
          title: '系统配置',
          icon: 'SettingOutlined',
          skeleton: 'settings'
        }
      },
      {
        path: 'settings/profile',
        name: 'SettingsProfile',
        component: SettingsProfile,
        meta: {
          title: '个人资料',
          icon: 'UserOutlined',
          skeleton: 'settings'
        }
      },
      {
        path: 'settings/about',
        name: 'SettingsAbout',
        component: SettingsAbout,
        meta: {
          title: '关于系统',
          icon: 'InfoCircleOutlined',
          skeleton: 'default'
        }
      },
      {
        path: 'settings/performance',
        name: 'SettingsPerformance',
        component: SettingsPerformance,
        meta: {
          title: '性能监控',
          icon: 'DashboardOutlined',
          skeleton: 'default'
        }
      },
      {
        path: 'settings/help-docs',
        name: 'HelpDocs',
        component: HelpDocs,
        meta: {
          title: '帮助文档',
          icon: 'BookOutlined',
          skeleton: 'default'
        }
      },
      {
        path: 'settings/user-management',
        name: 'UserManagement',
        component: UserManagement,
        meta: {
          title: '用户管理',
          icon: 'TeamOutlined',
          skeleton: 'list'
        }
      }
    ]
  },

  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: {
      title: '登录',
      public: true
    }
  },

  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: NotFound,
    meta: {
      title: '页面未找到'
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  }
})

const componentCache = new Map()
const preloadQueue = []
let isPreloading = false

/**
 * 预加载组件
 */
function preloadComponent(component) {
  if (typeof component === 'function' && !componentCache.has(component)) {
    const promise = component()
    componentCache.set(component, promise)
    return promise
  }
  return Promise.resolve()
}

/**
 * 处理预加载队列
 */
function processPreloadQueue() {
  if (isPreloading || preloadQueue.length === 0) return

  isPreloading = true
  const component = preloadQueue.shift()

  preloadComponent(component)
    .catch(() => {})
    .finally(() => {
      isPreloading = false
      if (preloadQueue.length > 0) {
        requestIdleCallback(processPreloadQueue, { timeout: 100 })
      }
    })
}

/**
 * 添加到预加载队列
 */
function queuePreload(component) {
  if (component && !preloadQueue.includes(component)) {
    preloadQueue.push(component)
    requestIdleCallback(processPreloadQueue, { timeout: 100 })
  }
}

router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - CAUC-SEP` : 'CAUC-SEP'

  const token = localStorage.getItem('auth_token')
  const publicPages = ['/login', '/register', '/forgot-password']
  const isPublicPage = to.meta.public || publicPages.includes(to.path)
  const isDevelopment = import.meta.env.DEV
  
  if (!isPublicPage && !token) {
    if (isDevelopment) {
      next()
    } else {
      const currentPath = to.path
      next({ path: '/login', query: { redirect: currentPath } })
    }
  } else if (token && to.path === '/login') {
    next('/device/status')
  } else {
    next()
  }
})

router.afterEach((to) => {
  const currentRoute = routes[0].children.find(r => r.path === to.path.replace('/', ''))
  if (currentRoute && currentRoute.component) {
    preloadComponent(currentRoute.component)
  }

  setTimeout(() => {
    routes[0].children.forEach(route => {
      if (route.meta?.preload && route.component) {
        queuePreload(route.component)
      }
    })
  }, 1000)
})

export default router
