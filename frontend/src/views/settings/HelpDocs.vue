<!--
  @file HelpDocs.vue
  @path src/views/settings/
  @description 帮助文档页面，加载 technical-docs 目录下的 Markdown 文档
  @author Agent
  @date 2026-03-15
-->

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import {
  BookOutlined,
  FileTextOutlined,
  FolderOutlined,
  FolderOpenOutlined,
  SearchOutlined,
  HomeOutlined,
  LeftOutlined,
  RightOutlined,
  ReloadOutlined,
  ExpandOutlined,
  CompressOutlined
} from '@ant-design/icons-vue'
import { marked } from 'marked'

marked.setOptions({
  breaks: true,
  gfm: true
})

const loading = ref(false)
const searchQuery = ref('')
const expandedKeys = ref(['00-索引与导航', '01-项目概述'])
const selectedDoc = ref(null)
const docContent = ref('')
const sidebarCollapsed = ref(false)
const fullscreen = ref(false)

const docTree = ref([
  {
    key: '00-索引与导航',
    title: '索引与导航',
    icon: FolderOutlined,
    children: [
      { key: '00-索引与导航/README', title: '文档导航', icon: FileTextOutlined },
      { key: '00-索引与导航/CHANGELOG', title: '更新日志', icon: FileTextOutlined }
    ]
  },
  {
    key: '01-项目概述',
    title: '项目概述',
    icon: FolderOutlined,
    children: [
      { key: '01-项目概述/项目背景与目标', title: '项目背景与目标', icon: FileTextOutlined },
      { key: '01-项目概述/技术栈说明', title: '技术栈说明', icon: FileTextOutlined },
      { key: '01-项目概述/项目目录结构', title: '项目目录结构', icon: FileTextOutlined },
      { key: '01-项目概述/支持设备清单', title: '支持设备清单', icon: FileTextOutlined }
    ]
  },
  {
    key: '02-快速开始',
    title: '快速开始',
    icon: FolderOutlined,
    children: [
      { key: '02-快速开始/环境要求', title: '环境要求', icon: FileTextOutlined },
      { key: '02-快速开始/安装配置', title: '安装配置', icon: FileTextOutlined },
      { key: '02-快速开始/验证测试', title: '验证测试', icon: FileTextOutlined }
    ]
  },
  {
    key: '03-系统架构',
    title: '系统架构',
    icon: FolderOutlined,
    children: [
      { key: '03-系统架构/整体架构设计', title: '整体架构设计', icon: FileTextOutlined },
      { key: '03-系统架构/前端架构', title: '前端架构', icon: FileTextOutlined },
      { key: '03-系统架构/后端架构', title: '后端架构', icon: FileTextOutlined },
      { key: '03-系统架构/数据流设计', title: '数据流设计', icon: FileTextOutlined }
    ]
  },
  {
    key: '04-核心模块',
    title: '核心模块',
    icon: FolderOutlined,
    children: [
      { key: '04-核心模块/硬件抽象层', title: '硬件抽象层', icon: FileTextOutlined },
      { key: '04-核心模块/步进电机控制', title: '步进电机控制', icon: FileTextOutlined },
      { key: '04-核心模块/电磁铁控制', title: '电磁铁控制', icon: FileTextOutlined },
      { key: '04-核心模块/温度控制', title: '温度控制', icon: FileTextOutlined },
      { key: '04-核心模块/压电控制', title: '压电控制', icon: FileTextOutlined },
      { key: '04-核心模块/皮安表采集', title: '皮安表采集', icon: FileTextOutlined },
      { key: '04-核心模块/数据分析引擎', title: '数据分析引擎', icon: FileTextOutlined }
    ]
  },
  {
    key: '05-数据库设计',
    title: '数据库设计',
    icon: FolderOutlined,
    children: [
      { key: '05-数据库设计/存储方案', title: '存储方案', icon: FileTextOutlined },
      { key: '05-数据库设计/数据模型', title: '数据模型', icon: FileTextOutlined }
    ]
  },
  {
    key: '06-通信协议',
    title: '通信协议',
    icon: FolderOutlined,
    children: [
      { key: '06-通信协议/REST-API设计', title: 'REST API设计', icon: FileTextOutlined },
      { key: '06-通信协议/WebSocket协议', title: 'WebSocket协议', icon: FileTextOutlined },
      { key: '06-通信协议/Modbus协议', title: 'Modbus协议', icon: FileTextOutlined }
    ]
  },
  {
    key: '07-API参考',
    title: 'API参考',
    icon: FolderOutlined,
    children: [
      { key: '07-API参考/设备控制API', title: '设备控制API', icon: FileTextOutlined },
      { key: '07-API参考/数据分析API', title: '数据分析API', icon: FileTextOutlined },
      { key: '07-API参考/用户管理API', title: '用户管理API', icon: FileTextOutlined },
      { key: '07-API参考/系统监控API', title: '系统监控API', icon: FileTextOutlined }
    ]
  },
  {
    key: '08-前端组件',
    title: '前端组件',
    icon: FolderOutlined,
    children: [
      { key: '08-前端组件/组件库概览', title: '组件库概览', icon: FileTextOutlined },
      { key: '08-前端组件/布局组件', title: '布局组件', icon: FileTextOutlined },
      { key: '08-前端组件/设备控制组件', title: '设备控制组件', icon: FileTextOutlined },
      { key: '08-前端组件/数据可视化组件', title: '数据可视化组件', icon: FileTextOutlined },
      { key: '08-前端组件/组合式函数', title: '组合式函数', icon: FileTextOutlined }
    ]
  },
  {
    key: '09-开发指南',
    title: '开发指南',
    icon: FolderOutlined,
    children: [
      { key: '09-开发指南/开发环境搭建', title: '开发环境搭建', icon: FileTextOutlined },
      { key: '09-开发指南/代码规范', title: '代码规范', icon: FileTextOutlined },
      { key: '09-开发指南/测试指南', title: '测试指南', icon: FileTextOutlined },
      { key: '09-开发指南/调试技巧', title: '调试技巧', icon: FileTextOutlined }
    ]
  },
  {
    key: '10-部署运维',
    title: '部署运维',
    icon: FolderOutlined,
    children: [
      { key: '10-部署运维/部署配置', title: '部署配置', icon: FileTextOutlined },
      { key: '10-部署运维/打包发布', title: '打包发布', icon: FileTextOutlined },
      { key: '10-部署运维/监控告警', title: '监控告警', icon: FileTextOutlined }
    ]
  },
  {
    key: '11-用户手册',
    title: '用户手册',
    icon: FolderOutlined,
    children: [
      { key: '11-用户手册/快速入门', title: '快速入门', icon: FileTextOutlined },
      { key: '11-用户手册/功能操作', title: '功能操作', icon: FileTextOutlined },
      { key: '11-用户手册/常见问题', title: '常见问题', icon: FileTextOutlined }
    ]
  },
  {
    key: '12-开发者指南',
    title: '开发者指南',
    icon: FolderOutlined,
    children: [
      { key: '12-开发者指南/模块开发', title: '模块开发', icon: FileTextOutlined },
      { key: '12-开发者指南/API扩展', title: 'API扩展', icon: FileTextOutlined },
      { key: '12-开发者指南/性能优化', title: '性能优化', icon: FileTextOutlined }
    ]
  },
  {
    key: '附录',
    title: '附录',
    icon: FolderOutlined,
    children: [
      { key: '附录/术语表', title: '术语表', icon: FileTextOutlined },
      { key: '附录/故障排除', title: '故障排除', icon: FileTextOutlined },
      { key: '附录/更新日志', title: '更新日志', icon: FileTextOutlined }
    ]
  }
])

const flatDocList = computed(() => {
  const list = []
  docTree.value.forEach(category => {
    category.children?.forEach(doc => {
      list.push({ ...doc, category: category.title })
    })
  })
  return list
})

const filteredDocs = computed(() => {
  if (!searchQuery.value.trim()) return docTree.value
  
  const query = searchQuery.value.toLowerCase()
  return docTree.value
    .map(category => {
      const filteredChildren = category.children?.filter(doc => 
        doc.title.toLowerCase().includes(query)
      )
      if (filteredChildren?.length > 0) {
        return { ...category, children: filteredChildren }
      }
      return null
    })
    .filter(Boolean)
})

const currentDocIndex = computed(() => {
  if (!selectedDoc.value) return -1
  return flatDocList.value.findIndex(doc => doc.key === selectedDoc.value)
})

const prevDoc = computed(() => {
  if (currentDocIndex.value <= 0) return null
  return flatDocList.value[currentDocIndex.value - 1]
})

const nextDoc = computed(() => {
  if (currentDocIndex.value < 0 || currentDocIndex.value >= flatDocList.value.length - 1) return null
  return flatDocList.value[currentDocIndex.value + 1]
})

async function loadDocument(docKey) {
  if (!docKey) return
  
  loading.value = true
  selectedDoc.value = docKey
  
  try {
    const basePath = '/docs/technical-docs/'
    const docPath = `${basePath}${docKey}.md`
    
    const response = await fetch(docPath)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    let content = await response.text()
    content = parseMarkdown(content)
    docContent.value = content
    
    if (!expandedKeys.value.includes(docKey.split('/')[0])) {
      expandedKeys.value.push(docKey.split('/')[0])
    }
  } catch (error) {
    console.error('[HelpDocs] 加载文档失败:', error)
    docContent.value = `
      <div class="doc-error">
        <h2>文档加载失败</h2>
        <p>无法加载文档: ${docKey}</p>
        <p>请确保文档文件存在: docs/technical-docs/${docKey}.md</p>
      </div>
    `
  } finally {
    loading.value = false
  }
}

function parseMarkdown(content) {
  try {
    return marked.parse(content)
  } catch (error) {
    console.error('[HelpDocs] Markdown 解析失败:', error)
    return `<pre>${content}</pre>`
  }
}

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

function toggleFullscreen() {
  fullscreen.value = !fullscreen.value
}

function handleSearch() {
  if (searchQuery.value.trim()) {
    expandedKeys.value = filteredDocs.value.map(d => d.key)
  }
}

function goHome() {
  loadDocument('00-索引与导航/README')
}

function goToPrevDoc() {
  if (prevDoc.value) {
    loadDocument(prevDoc.value.key)
  }
}

function goToNextDoc() {
  if (nextDoc.value) {
    loadDocument(nextDoc.value.key)
  }
}

function handleKeydown(event) {
  if (event.key === 'ArrowLeft' && prevDoc.value) {
    goToPrevDoc()
  } else if (event.key === 'ArrowRight' && nextDoc.value) {
    goToNextDoc()
  }
}

onMounted(() => {
  loadDocument('00-索引与导航/README')
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})

watch(searchQuery, handleSearch)
</script>

<template>
  <div
    class="help-docs-page"
    :class="{ 'is-fullscreen': fullscreen }"
  >
    <div class="docs-container">
      <aside
        class="docs-sidebar"
        :class="{ 'is-collapsed': sidebarCollapsed }"
      >
        <div class="sidebar-header">
          <div
            v-if="!sidebarCollapsed"
            class="header-title"
          >
            <BookOutlined class="header-icon" />
            <span>技术文档</span>
          </div>
          <button
            class="collapse-btn"
            @click="toggleSidebar"
          >
            <LeftOutlined v-if="!sidebarCollapsed" />
            <RightOutlined v-else />
          </button>
        </div>

        <div
          v-if="!sidebarCollapsed"
          class="sidebar-search"
        >
          <a-input
            v-model:value="searchQuery"
            placeholder="搜索文档..."
            allow-clear
          >
            <template #prefix>
              <SearchOutlined />
            </template>
          </a-input>
        </div>

        <nav
          v-if="!sidebarCollapsed"
          class="sidebar-nav"
        >
          <ul class="nav-tree">
            <li
              v-for="category in (searchQuery ? filteredDocs : docTree)"
              :key="category.key"
              class="nav-category"
            >
              <div
                class="category-header"
                :class="{ 'is-expanded': expandedKeys.includes(category.key) }"
                @click="expandedKeys.includes(category.key) 
                  ? expandedKeys = expandedKeys.filter(k => k !== category.key)
                  : expandedKeys.push(category.key)"
              >
                <component
                  :is="expandedKeys.includes(category.key) ? FolderOpenOutlined : FolderOutlined"
                  class="category-icon"
                />
                <span class="category-title">{{ category.title }}</span>
              </div>
              
              <Transition name="expand">
                <ul
                  v-show="expandedKeys.includes(category.key)"
                  class="nav-children"
                >
                  <li
                    v-for="doc in category.children"
                    :key="doc.key"
                    class="nav-item"
                    :class="{ 'is-active': selectedDoc === doc.key }"
                    @click="loadDocument(doc.key)"
                  >
                    <FileTextOutlined class="item-icon" />
                    <span class="item-title">{{ doc.title }}</span>
                  </li>
                </ul>
              </Transition>
            </li>
          </ul>
        </nav>
      </aside>

      <main class="docs-content">
        <header class="content-header">
          <div class="header-left">
            <button
              class="nav-btn"
              :disabled="!prevDoc"
              @click="goToPrevDoc"
            >
              <LeftOutlined />
            </button>
            <button
              class="nav-btn"
              :disabled="!nextDoc"
              @click="goToNextDoc"
            >
              <RightOutlined />
            </button>
            <button
              class="nav-btn"
              @click="goHome"
            >
              <HomeOutlined />
            </button>
          </div>
          
          <div class="header-center">
            <span
              v-if="selectedDoc"
              class="current-doc-title"
            >
              {{ flatDocList.find(d => d.key === selectedDoc)?.title || '文档' }}
            </span>
          </div>
          
          <div class="header-right">
            <button
              class="nav-btn"
              @click="loadDocument(selectedDoc)"
            >
              <ReloadOutlined />
            </button>
            <button
              class="nav-btn"
              @click="toggleFullscreen"
            >
              <CompressOutlined v-if="fullscreen" />
              <ExpandOutlined v-else />
            </button>
          </div>
        </header>

        <div
          v-if="loading"
          class="content-loading"
        >
          <a-spin size="large" />
          <p>加载中...</p>
        </div>

        <article
          v-else
          class="content-body"
          v-html="docContent"
        />

        <footer class="content-footer">
          <div class="footer-nav">
            <button
              v-if="prevDoc"
              class="footer-nav-btn prev"
              @click="goToPrevDoc"
            >
              <LeftOutlined />
              <span>{{ prevDoc.title }}</span>
            </button>
            <button
              v-if="nextDoc"
              class="footer-nav-btn next"
              @click="goToNextDoc"
            >
              <span>{{ nextDoc.title }}</span>
              <RightOutlined />
            </button>
          </div>
        </footer>
      </main>
    </div>
  </div>
</template>

<style scoped lang="scss">
.help-docs-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-secondary);
  
  &.is-fullscreen {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 9999;
  }
}

.docs-container {
  display: flex;
  height: 100%;
  overflow: hidden;
}

.docs-sidebar {
  width: 280px;
  background: var(--color-surface-primary);
  border-right: 1px solid var(--color-border-primary);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  
  &.is-collapsed {
    width: 48px;
  }
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-3) var(--spacing-4);
  border-bottom: 1px solid var(--color-border-primary);
  min-height: 56px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.header-icon {
  font-size: 18px;
  color: var(--color-primary-500);
}

.collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
  
  &:hover {
    background: var(--color-interactive-hover);
    color: var(--color-primary-500);
  }
}

.sidebar-search {
  padding: var(--spacing-3) var(--spacing-4);
  border-bottom: 1px solid var(--color-border-primary);
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-2) 0;
}

.nav-tree {
  list-style: none;
  margin: 0;
  padding: 0;
}

.nav-category {
  margin-bottom: var(--spacing-1);
}

.category-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-4);
  cursor: pointer;
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
  transition: all var(--transition-fast);
  
  &:hover {
    background: var(--color-interactive-hover);
  }
  
  &.is-expanded {
    color: var(--color-primary-500);
  }
}

.category-icon {
  font-size: 16px;
  color: var(--color-text-tertiary);
}

.category-title {
  flex: 1;
  font-size: var(--font-size-sm);
}

.nav-children {
  list-style: none;
  margin: 0;
  padding: 0;
  background: var(--color-bg-secondary);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-4) var(--spacing-2) var(--spacing-8);
  cursor: pointer;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  transition: all var(--transition-fast);
  
  &:hover {
    background: var(--color-interactive-hover);
    color: var(--color-text-primary);
  }
  
  &.is-active {
    background: var(--color-primary-50);
    color: var(--color-primary-600);
    border-right: 3px solid var(--color-primary-500);
  }
}

.item-icon {
  font-size: 14px;
  opacity: 0.6;
}

.item-title {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.docs-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--color-surface-primary);
}

.content-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-2) var(--spacing-4);
  border-bottom: 1px solid var(--color-border-primary);
  background: var(--color-surface-primary);
  min-height: 48px;
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.header-center {
  flex: 1;
  text-align: center;
}

.current-doc-title {
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.nav-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--color-border-primary);
  background: var(--color-surface-primary);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
  
  &:hover:not(:disabled) {
    background: var(--color-interactive-hover);
    color: var(--color-primary-500);
    border-color: var(--color-primary-300);
  }
  
  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
}

.content-loading {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-4);
  color: var(--color-text-secondary);
}

.content-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-6) var(--spacing-8);
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
  
  :deep(h1) {
    font-size: var(--font-size-3xl);
    font-weight: var(--font-weight-bold);
    color: var(--color-text-primary);
    margin-bottom: var(--spacing-6);
    padding-bottom: var(--spacing-4);
    border-bottom: 2px solid var(--color-border-primary);
  }
  
  :deep(h2) {
    font-size: var(--font-size-2xl);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-primary);
    margin-top: var(--spacing-8);
    margin-bottom: var(--spacing-4);
  }
  
  :deep(h3) {
    font-size: var(--font-size-xl);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text-primary);
    margin-top: var(--spacing-6);
    margin-bottom: var(--spacing-3);
  }
  
  :deep(p) {
    font-size: var(--font-size-base);
    line-height: 1.8;
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-4);
  }
  
  :deep(code) {
    background: var(--color-bg-tertiary);
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    font-family: var(--font-family-mono);
    font-size: var(--font-size-sm);
    color: var(--color-primary-600);
  }
  
  :deep(pre) {
    background: var(--color-bg-tertiary);
    padding: var(--spacing-4);
    border-radius: var(--radius-md);
    overflow-x: auto;
    margin-bottom: var(--spacing-4);
    
    code {
      background: transparent;
      padding: 0;
      color: var(--color-text-primary);
    }
  }
  
  :deep(a) {
    color: var(--color-primary-500);
    text-decoration: none;
    
    &:hover {
      text-decoration: underline;
    }
  }
  
  :deep(ul), :deep(ol) {
    padding-left: var(--spacing-6);
    margin-bottom: var(--spacing-4);
    
    li {
      margin-bottom: var(--spacing-2);
      color: var(--color-text-secondary);
    }
  }
  
  :deep(img) {
    max-width: 100%;
    border-radius: var(--radius-md);
    margin: var(--spacing-4) 0;
  }
  
  :deep(table) {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: var(--spacing-4);
    
    th, td {
      border: 1px solid var(--color-border-primary);
      padding: var(--spacing-2) var(--spacing-3);
      text-align: left;
    }
    
    th {
      background: var(--color-bg-secondary);
      font-weight: var(--font-weight-semibold);
    }
  }
  
  :deep(.doc-error) {
    text-align: center;
    padding: var(--spacing-8);
    
    h2 {
      color: var(--color-error);
      margin-bottom: var(--spacing-4);
    }
    
    p {
      color: var(--color-text-secondary);
    }
  }
}

.content-footer {
  padding: var(--spacing-4) var(--spacing-8);
  border-top: 1px solid var(--color-border-primary);
  background: var(--color-surface-primary);
}

.footer-nav {
  display: flex;
  justify-content: space-between;
  max-width: 900px;
  margin: 0 auto;
}

.footer-nav-btn {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-4);
  border: 1px solid var(--color-border-primary);
  background: var(--color-surface-primary);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
  
  &:hover {
    background: var(--color-interactive-hover);
    color: var(--color-primary-500);
    border-color: var(--color-primary-300);
  }
  
  &.next {
    margin-left: auto;
  }
}

.expand-enter-active,
.expand-leave-active {
  transition: all 0.3s ease;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}

.expand-enter-to,
.expand-leave-from {
  max-height: 500px;
}

@media (max-width: 768px) {
  .docs-sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: 100;
    transform: translateX(-100%);
    
    &:not(.is-collapsed) {
      transform: translateX(0);
    }
  }
  
  .content-body {
    padding: var(--spacing-4);
  }
}
</style>
