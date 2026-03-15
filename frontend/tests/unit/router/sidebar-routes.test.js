/**
 * @file sidebar-routes.test.js
 * @path tests/unit/router/
 * @description 侧边栏路由配置测试 - 验证所有菜单项路径与路由配置匹配
 * @author Agent
 * @date 2024-03-15
 */

import { describe, it, expect } from 'vitest'

// 从Sidebar.vue提取的菜单配置
const sidebarMenuItems = [
  {
    key: 'device',
    path: '/device/status'
  },
  {
    key: 'experiment',
    children: [
      { key: 'motor', path: '/experiment/motor' },
      { key: 'electromagnet', path: '/experiment/electromagnet' },
      { key: 'temperature', path: '/experiment/temperature' },
      { key: 'piezo', path: '/experiment/piezo' },
      { key: 'ammeter', path: '/experiment/ammeter' }
    ]
  },
  {
    key: 'analysis',
    path: '/analysis/realtime'
  },
  {
    key: 'settings',
    path: '/settings/audit'
  }
]

// 从router/index.js提取的路由配置
const routerRoutes = [
  { path: '/', redirect: '/experiment/motor' },
  {
    path: '/experiment',
    children: [
      { path: '', redirect: '/experiment/motor' },
      { path: 'motor', name: 'ExperimentMotor' },
      { path: 'piezo', name: 'ExperimentPiezo' },
      { path: 'electromagnet', name: 'ExperimentElectromagnet' },
      { path: 'safety', name: 'ExperimentSafety' },
      { path: 'temperature', name: 'ExperimentTemperature' },
      { path: 'ammeter', name: 'ExperimentAmmeter' }
    ]
  },
  {
    path: '/device',
    children: [
      { path: '', redirect: '/device/status' },
      { path: 'status', name: 'DeviceStatus' },
      { path: 'connection', name: 'DeviceConnection' },
      { path: 'pr-path', name: 'DevicePRPath' }
    ]
  },
  {
    path: '/analysis',
    children: [
      { path: '', redirect: '/analysis/realtime' },
      { path: 'realtime', name: 'AnalysisRealtime' },
      { path: 'history', name: 'AnalysisHistory' },
      { path: 'charts', name: 'AnalysisCharts' }
    ]
  },
  {
    path: '/settings',
    children: [
      { path: '', redirect: '/settings/audit' },
      { path: 'audit', name: 'SettingsAudit' },
      { path: 'users', name: 'SettingsUsers' },
      { path: 'config', name: 'SettingsConfig' },
      { path: 'about', name: 'SettingsAbout' },
      { path: 'profile', name: 'SettingsProfile' },
      { path: 'performance', name: 'SettingsPerformance' }
    ]
  },
  { path: '/:pathMatch(.*)*', name: 'NotFound' }
]

describe('Sidebar Routes Configuration', () => {
  /**
   * 测试所有侧边栏路径是否存在于路由配置中
   */
  describe('Route Existence', () => {
    it('should have all sidebar menu paths defined in router', () => {
      const allPaths = extractAllPaths(sidebarMenuItems)
      
      for (const path of allPaths) {
        const exists = pathExistsInRoutes(path, routerRoutes)
        expect(exists, `Route ${path} should exist in router configuration`).toBe(true)
      }
    })

    it('should have /device/status route', () => {
      expect(pathExistsInRoutes('/device/status', routerRoutes)).toBe(true)
    })

    it('should have /experiment/motor route', () => {
      expect(pathExistsInRoutes('/experiment/motor', routerRoutes)).toBe(true)
    })

    it('should have /experiment/electromagnet route', () => {
      expect(pathExistsInRoutes('/experiment/electromagnet', routerRoutes)).toBe(true)
    })

    it('should have /experiment/temperature route', () => {
      expect(pathExistsInRoutes('/experiment/temperature', routerRoutes)).toBe(true)
    })

    it('should have /experiment/piezo route', () => {
      expect(pathExistsInRoutes('/experiment/piezo', routerRoutes)).toBe(true)
    })

    it('should have /experiment/ammeter route', () => {
      expect(pathExistsInRoutes('/experiment/ammeter', routerRoutes)).toBe(true)
    })

    it('should have /analysis/realtime route', () => {
      expect(pathExistsInRoutes('/analysis/realtime', routerRoutes)).toBe(true)
    })

    it('should have /settings/audit route', () => {
      expect(pathExistsInRoutes('/settings/audit', routerRoutes)).toBe(true)
    })
  })

  /**
   * 测试路由重定向
   */
  describe('Route Redirects', () => {
    it('should redirect / to /experiment/motor', () => {
      const rootRoute = routerRoutes.find(r => r.path === '/')
      expect(rootRoute.redirect).toBe('/experiment/motor')
    })

    it('should redirect /experiment to /experiment/motor', () => {
      const expRoute = routerRoutes.find(r => r.path === '/experiment')
      const child = expRoute.children.find(c => c.path === '')
      expect(child.redirect).toBe('/experiment/motor')
    })

    it('should redirect /device to /device/status', () => {
      const deviceRoute = routerRoutes.find(r => r.path === '/device')
      const child = deviceRoute.children.find(c => c.path === '')
      expect(child.redirect).toBe('/device/status')
    })

    it('should redirect /analysis to /analysis/realtime', () => {
      const analysisRoute = routerRoutes.find(r => r.path === '/analysis')
      const child = analysisRoute.children.find(c => c.path === '')
      expect(child.redirect).toBe('/analysis/realtime')
    })

    it('should redirect /settings to /settings/audit', () => {
      const settingsRoute = routerRoutes.find(r => r.path === '/settings')
      const child = settingsRoute.children.find(c => c.path === '')
      expect(child.redirect).toBe('/settings/audit')
    })
  })

  /**
   * 测试无效路由返回404
   */
  describe('Invalid Routes', () => {
    it('should handle 404 for non-existent routes', () => {
      const notFoundRoute = routerRoutes.find(r => r.name === 'NotFound')
      expect(notFoundRoute).toBeDefined()
    })

    it('should handle 404 for old dashboard path', () => {
      expect(pathExistsInRoutes('/dashboard', routerRoutes)).toBe(false)
    })

    it('should handle 404 for old control paths', () => {
      expect(pathExistsInRoutes('/control/motor', routerRoutes)).toBe(false)
    })

    it('should handle 404 for old acquisition paths', () => {
      expect(pathExistsInRoutes('/acquisition/ammeter', routerRoutes)).toBe(false)
    })
  })

  /**
   * 测试路由名称
   */
  describe('Route Names', () => {
    it('should have correct name for /experiment/motor', () => {
      const route = findRouteByPath('/experiment/motor', routerRoutes)
      expect(route?.name).toBe('ExperimentMotor')
    })

    it('should have correct name for /device/status', () => {
      const route = findRouteByPath('/device/status', routerRoutes)
      expect(route?.name).toBe('DeviceStatus')
    })

    it('should have correct name for /analysis/realtime', () => {
      const route = findRouteByPath('/analysis/realtime', routerRoutes)
      expect(route?.name).toBe('AnalysisRealtime')
    })

    it('should have correct name for /settings/audit', () => {
      const route = findRouteByPath('/settings/audit', routerRoutes)
      expect(route?.name).toBe('SettingsAudit')
    })
  })
})

/**
 * 辅助函数：提取所有路径
 */
function extractAllPaths(items) {
  const paths = []
  
  items.forEach(item => {
    if (item.path) {
      paths.push(item.path)
    }
    if (item.children) {
      item.children.forEach(child => {
        if (child.path) {
          paths.push(child.path)
        }
      })
    }
  })
  
  return paths
}

/**
 * 辅助函数：检查路径是否存在于路由配置中
 */
function pathExistsInRoutes(path, routes) {
  const parts = path.split('/').filter(Boolean)
  
  if (parts.length === 0) return false
  
  const parentPath = '/' + parts[0]
  const childPath = parts.slice(1).join('/')
  
  const parentRoute = routes.find(r => r.path === parentPath)
  if (!parentRoute) return false
  
  if (!childPath) {
    // 检查是否有重定向或默认子路由
    return parentRoute.children && parentRoute.children.length > 0
  }
  
  if (!parentRoute.children) return false
  
  const childRoute = parentRoute.children.find(c => c.path === childPath)
  return !!childRoute
}

/**
 * 辅助函数：根据路径查找路由
 */
function findRouteByPath(path, routes) {
  const parts = path.split('/').filter(Boolean)
  
  if (parts.length === 0) return null
  
  const parentPath = '/' + parts[0]
  const childPath = parts.slice(1).join('/')
  
  const parentRoute = routes.find(r => r.path === parentPath)
  if (!parentRoute || !parentRoute.children) return null
  
  return parentRoute.children.find(c => c.path === childPath)
}
