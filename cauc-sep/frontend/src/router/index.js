/**
 * @file index.js
 * @path src/router/
 * @description 自旋电子实验平台路由配置，支持懒加载和预加载
 * @author Agent
 * @date 2024-03-08
 * @dependencies vue-router
 */

import { createRouter, createWebHistory } from 'vue-router'
import { 
  lazyRoute, 
  preloadRoute, 
  PreloadStrategy, 
  preloadByStrategy 
} from './lazy'

/**
 * 路由配置
 * 
 * 结构说明：
 * - 使用路由懒加载优化首屏性能
 * - 嵌套路由实现模块化布局
 * - 默认重定向到实验控制模块
 * - 支持路由预加载策略
 */
const routes = [
  // 根路径重定向
  {
    path: '/',
    redirect: '/experiment/motor'
  },

  // ==================== 实验控制模块 ====================
  {
    path: '/experiment',
    component: () => import('@/views/Layout.vue'),
    meta: {
      title: '实验控制',
      icon: 'Setting',
      preload: true // 标记为预加载模块
    },
    children: [
      {
        path: '',
        redirect: '/experiment/motor'
      },
      {
        path: 'motor',
        name: 'ExperimentMotor',
        component: lazyRoute(() => import('@/views/experiment/MotorControl.vue'), {
          preload: true,
          preloadDelay: 1000
        }),
        meta: {
          title: '电机控制',
          icon: 'Connection',
          breadcrumb: ['实验控制', '电机控制'],
          preload: true,
          preloadPriority: 3 // 高优先级
        }
      },
      {
        path: 'piezo',
        name: 'ExperimentPiezo',
        component: lazyRoute(() => import('@/views/experiment/PiezoControl.vue'), {
          preload: true,
          preloadDelay: 2000
        }),
        meta: {
          title: '压电陶瓷',
          icon: 'Grid',
          breadcrumb: ['实验控制', '压电陶瓷'],
          preload: true,
          preloadPriority: 2
        }
      },
      {
        path: 'electromagnet',
        name: 'ExperimentElectromagnet',
        component: lazyRoute(() => import('@/views/experiment/ElectromagnetControl.vue')),
        meta: {
          title: '电磁铁',
          icon: 'Cpu',
          breadcrumb: ['实验控制', '电磁铁']
        }
      },
      {
        path: 'safety',
        name: 'ExperimentSafety',
        component: lazyRoute(() => import('@/views/experiment/SafetyPanel.vue')),
        meta: {
          title: '安全面板',
          icon: 'Warning',
          breadcrumb: ['实验控制', '安全面板']
        }
      },
      {
        path: 'temperature',
        name: 'ExperimentTemperature',
        component: lazyRoute(() => import('@/views/experiment/TemperatureControl.vue'), {
          preload: true,
          preloadDelay: 3000
        }),
        meta: {
          title: '温度控制',
          icon: 'Sunny',
          breadcrumb: ['实验控制', '温度控制'],
          preload: true,
          preloadPriority: 1
        }
      },
      {
        path: 'ammeter',
        name: 'ExperimentAmmeter',
        component: lazyRoute(() => import('@/views/experiment/AmmeterControl.vue')),
        meta: {
          title: '微电流',
          icon: 'Aim',
          breadcrumb: ['实验控制', '微电流']
        }
      }
    ]
  },

  // ==================== 设备管理模块 ====================
  {
    path: '/device',
    component: () => import('@/views/Layout.vue'),
    meta: {
      title: '设备管理',
      icon: 'Monitor',
      preload: true
    },
    children: [
      {
        path: '',
        redirect: '/device/status'
      },
      {
        path: 'status',
        name: 'DeviceStatus',
        component: lazyRoute(() => import('@/views/device/Status.vue'), {
          preload: true,
          preloadDelay: 1500
        }),
        meta: {
          title: '设备状态',
          icon: 'DataBoard',
          breadcrumb: ['设备管理', '设备状态'],
          preload: true,
          preloadPriority: 3
        }
      },
      {
        path: 'connection',
        name: 'DeviceConnection',
        component: lazyRoute(() => import('@/views/device/Connection.vue')),
        meta: {
          title: '连接配置',
          icon: 'Link',
          breadcrumb: ['设备管理', '连接配置']
        }
      },
      {
        path: 'pr-path',
        name: 'DevicePRPath',
        component: lazyRoute(() => import('@/views/device/PRPath.vue')),
        meta: {
          title: 'PR路径配置',
          icon: 'Route',
          breadcrumb: ['设备管理', 'PR路径配置']
        }
      }
    ]
  },

  // ==================== 数据分析模块 ====================
  {
    path: '/analysis',
    component: () => import('@/views/Layout.vue'),
    meta: {
      title: '数据分析',
      icon: 'DataAnalysis',
      preload: true
    },
    children: [
      {
        path: '',
        redirect: '/analysis/realtime'
      },
      {
        path: 'realtime',
        name: 'AnalysisRealtime',
        component: lazyRoute(() => import('@/views/analysis/Realtime.vue'), {
          preload: true,
          preloadDelay: 2000
        }),
        meta: {
          title: '实时数据',
          icon: 'TrendCharts',
          breadcrumb: ['数据分析', '实时数据'],
          preload: true,
          preloadPriority: 2
        }
      },
      {
        path: 'history',
        name: 'AnalysisHistory',
        component: lazyRoute(() => import('@/views/analysis/History.vue')),
        meta: {
          title: '历史数据',
          icon: 'Clock',
          breadcrumb: ['数据分析', '历史数据']
        }
      },
      {
        path: 'charts',
        name: 'AnalysisCharts',
        component: lazyRoute(() => import('@/views/analysis/Charts.vue')),
        meta: {
          title: '图表分析',
          icon: 'PieChart',
          breadcrumb: ['数据分析', '图表分析']
        }
      }
    ]
  },

  // ==================== 系统设置模块 ====================
  {
    path: '/settings',
    component: () => import('@/views/Layout.vue'),
    meta: {
      title: '系统设置',
      icon: 'Tools'
    },
    children: [
      {
        path: '',
        redirect: '/settings/audit'
      },
      {
        path: 'audit',
        name: 'SettingsAudit',
        component: lazyRoute(() => import('@/views/settings/Audit.vue')),
        meta: {
          title: '审计日志',
          icon: 'Document',
          breadcrumb: ['系统设置', '审计日志']
        }
      },
      {
        path: 'users',
        name: 'SettingsUsers',
        component: lazyRoute(() => import('@/views/settings/UserManagement.vue')),
        meta: {
          title: '用户管理',
          icon: 'UserFilled',
          breadcrumb: ['系统设置', '用户管理']
        }
      },
      {
        path: 'config',
        name: 'SettingsConfig',
        component: lazyRoute(() => import('@/views/settings/Config.vue')),
        meta: {
          title: '系统配置',
          icon: 'Setting',
          breadcrumb: ['系统设置', '系统配置']
        }
      },
      {
        path: 'about',
        name: 'SettingsAbout',
        component: lazyRoute(() => import('@/views/settings/About.vue')),
        meta: {
          title: '关于',
          icon: 'InfoFilled',
          breadcrumb: ['系统设置', '关于']
        }
      },
      {
        path: 'profile',
        name: 'SettingsProfile',
        component: lazyRoute(() => import('@/views/settings/Profile.vue')),
        meta: {
          title: '个人中心',
          icon: 'User',
          breadcrumb: ['系统设置', '个人中心']
        }
      },
      {
        path: 'performance',
        name: 'SettingsPerformance',
        component: lazyRoute(() => import('@/views/settings/Performance.vue')),
        meta: {
          title: '性能分析',
          icon: 'DataAnalysis',
          breadcrumb: ['系统设置', '性能分析']
        }
      }
    ]
  },

  // ==================== 测试页面 ====================
  {
    path: '/test',
    component: () => import('@/views/Layout.vue'),
    meta: {
      title: '测试',
      icon: 'Test'
    },
    children: [
      {
        path: '',
        name: 'TestLayout',
        component: lazyRoute(() => import('@/views/TestLayout.vue')),
        meta: {
          title: '布局测试',
          breadcrumb: ['测试', '布局测试']
        }
      },
      {
        path: 'operation-feedback',
        name: 'TestOperationFeedback',
        component: lazyRoute(() => import('@/views/test/OperationFeedbackTest.vue')),
        meta: {
          title: '操作反馈测试',
          breadcrumb: ['测试', '操作反馈测试']
        }
      }
    ]
  },

  // ==================== 404 页面 ====================
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: lazyRoute(() => import('@/views/NotFound.vue')),
    meta: {
      title: '页面未找到'
    }
  }
]

/**
 * 创建路由实例
 */
const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

/**
 * 全局路由守卫
 * 
 * 设置页面标题、面包屑，并同步布局Store状态
 * 支持路由预加载和加载状态管理
 */
router.beforeEach(async (to, from, next) => {
  // 设置页面标题
  const title = to.meta?.title || '自旋电子实验平台'
  document.title = `${title} - 自旋电子实验平台`
  
  // 设置加载状态
  import('@/stores/layout').then(({ useLayoutStore }) => {
    const layoutStore = useLayoutStore()
    layoutStore.setRouteLoading(true)
    layoutStore.setActiveByPath(to.path)
  }).catch(err => {
    console.warn('[Router] Failed to sync layout store:', err)
  })
  
  next()
})

/**
 * 路由后置守卫
 * 用于页面切换后的清理工作和预加载
 */
router.afterEach((to, from) => {
  // 清除加载状态
  import('@/stores/layout').then(({ useLayoutStore }) => {
    const layoutStore = useLayoutStore()
    layoutStore.setRouteLoading(false)
  }).catch(err => {
    console.warn('[Router] Failed to clear loading state:', err)
  })
  
  // 预加载相邻路由
  preloadAdjacentRoutes(to)
})

/**
 * 预加载相邻路由
 * 
 * @param {Object} currentRoute - 当前路由对象
 */
function preloadAdjacentRoutes(currentRoute) {
  // 获取当前路由的所有兄弟路由
  const parentPath = currentRoute.matched[currentRoute.matched.length - 1]?.path
  const currentName = currentRoute.name
  
  if (!parentPath || !currentName) return
  
  // 查找同级路由
  const siblingRoutes = routes.find(r => r.path === parentPath)?.children || []
  const currentIndex = siblingRoutes.findIndex(r => r.name === currentName)
  
  if (currentIndex === -1) return
  
  // 预加载下一个路由
  if (currentIndex < siblingRoutes.length - 1) {
    const nextRoute = siblingRoutes[currentIndex + 1]
    if (nextRoute?.meta?.preload && nextRoute.component) {
      preloadRoute(nextRoute.name, nextRoute.component, {
        priority: nextRoute.meta.preloadPriority || 1,
        delay: 1000
      })
    }
  }
  
  // 预加载上一个路由（优先级较低）
  if (currentIndex > 0) {
    const prevRoute = siblingRoutes[currentIndex - 1]
    if (prevRoute?.meta?.preload && prevRoute.component) {
      preloadRoute(prevRoute.name, prevRoute.component, {
        priority: (prevRoute.meta.preloadPriority || 1) - 1,
        delay: 2000
      })
    }
  }
}

/**
 * 初始化路由预加载
 * 在应用启动时预加载常用路由
 */
export function initRoutePreload() {
  // 预加载常用路由
  const commonRoutes = [
    { name: 'ExperimentMotor', loader: () => import('@/views/experiment/MotorControl.vue'), priority: 3 },
    { name: 'DeviceStatus', loader: () => import('@/views/device/Status.vue'), priority: 2 },
    { name: 'AnalysisRealtime', loader: () => import('@/views/analysis/Realtime.vue'), priority: 2 }
  ]
  
  commonRoutes.forEach(({ name, loader, priority }) => {
    preloadRoute(name, loader, { priority, delay: 3000 })
  })
}

export default router
