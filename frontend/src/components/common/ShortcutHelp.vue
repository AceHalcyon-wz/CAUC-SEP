<!--
  @file ShortcutHelp.vue
  @path src/components/
  @description 快捷键帮助面板组件，显示所有可用快捷键及其说明
  @author Agent
  @date 2024-03-07
-->

<script setup lang="ts">
/**
 * @file ShortcutHelp.vue
 * @path src/components/
 * @description 快捷键帮助面板组件，显示所有可用快捷键及其说明
 * @author Agent
 * @date 2024-03-07
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useKeyboardShortcuts, DEFAULT_SHORTCUTS } from '@/composables/useKeyboardShortcuts'

// === Props/Emits 定义 ===
const props = defineProps({
  /** 是否显示帮助面板 */
  visible: {
    type: Boolean,
    default: false
  },
  /** 是否显示搜索框 */
  showSearch: {
    type: Boolean,
    default: true
  },
  /** 是否显示分类 */
  showCategories: {
    type: Boolean,
    default: true
  },
  /** 自定义标题 */
  title: {
    type: String,
    default: '键盘快捷键'
  }
})

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
  (e: 'close'): void
  (e: 'shortcut-click', shortcutId: string): void
}>()

// === 组合式函数调用 ===
const { groupedShortcuts, registeredShortcuts, conflicts } = useKeyboardShortcuts()

// === 响应式状态 ===
/** 搜索关键词 */
const searchKeyword = ref('')
/** 当前选中的分类 */
const selectedCategory = ref('all')
/** 是否显示冲突提示 */
const showConflicts = ref(false)

// === 计算属性 ===
/** 所有分类 */
const categories = computed(() => {
  const cats = Object.keys(groupedShortcuts.value).map(key => ({
    key,
    label: getCategoryLabel(key),
    count: groupedShortcuts.value[key].length
  }))
  return [{ key: 'all', label: '全部', count: registeredShortcuts.value.length }, ...cats]
})

/** 过滤后的快捷键列表 */
const filteredShortcuts = computed(() => {
  let result = registeredShortcuts.value

  // 分类过滤
  if (selectedCategory.value !== 'all') {
    result = result.filter(s => s.id.startsWith(`${selectedCategory.value}.`))
  }

  // 搜索过滤
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(s =>
      s.description.toLowerCase().includes(keyword) ||
      s.id.toLowerCase().includes(keyword) ||
      s.key.toLowerCase().includes(keyword)
    )
  }

  return result
})

/** 按分类分组的过滤结果 */
const filteredGrouped = computed(() => {
  if (selectedCategory.value !== 'all') {
    return { [selectedCategory.value]: filteredShortcuts.value }
  }

  const groups = {}
  filteredShortcuts.value.forEach(shortcut => {
    const category = shortcut.id.split('.')[0]
    if (!groups[category]) {
      groups[category] = []
    }
    groups[category].push(shortcut)
  })
  return groups
})

/** 是否有冲突 */
const hasConflicts = computed(() => conflicts.value.length > 0)

// === 方法 ===
/**
 * 获取分类标签
 *
 * @param {string} key - 分类键
 * @returns {string} 分类标签
 */
function getCategoryLabel(key) {
  const labels = {
    global: '全局操作',
    device: '设备控制',
    experiment: '实验操作',
    data: '数据操作',
    view: '视图切换',
    history: '历史操作',
    ui: '界面操作',
    profile: '个人中心'
  }
  return labels[key] || key
}

/**
 * 格式化快捷键显示
 *
 * @param {Object} shortcut - 快捷键配置
 * @returns {string} 格式化后的快捷键
 */
function formatShortcut(shortcut) {
  const parts = []
  if (shortcut.ctrl) parts.push('Ctrl')
  if (shortcut.alt) parts.push('Alt')
  if (shortcut.shift) parts.push('Shift')
  if (shortcut.meta) parts.push('Meta')
  parts.push(shortcut.key.toUpperCase())
  return parts.join(' + ')
}

/**
 * 关闭面板
 */
function close() {
  emit('update:visible', false)
  emit('close')
}

/**
 * 点击快捷键
 *
 * @param {string} shortcutId - 快捷键ID
 */
function handleShortcutClick(shortcutId) {
  emit('shortcut-click', shortcutId)
}

/**
 * 键盘事件处理
 *
 * @param {KeyboardEvent} event - 键盘事件
 */
function handleKeydown(event) {
  if (event.key === 'Escape' && props.visible) {
    close()
  }
}

// === 生命周期 ===
onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="visible"
        class="shortcut-help-overlay"
        @click.self="close"
      >
        <div class="shortcut-help-panel">
          <!-- 头部 -->
          <header class="panel-header">
            <h2 class="panel-title">
              {{ title }}
            </h2>
            <button
              class="close-btn"
              aria-label="关闭"
              @click="close"
            >
              <svg
                viewBox="0 0 24 24"
                width="20"
                height="20"
              >
                <path
                  fill="currentColor"
                  d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"
                />
              </svg>
            </button>
          </header>

          <!-- 搜索和过滤 -->
          <div class="panel-toolbar">
            <div
              v-if="showSearch"
              class="search-box"
            >
              <svg
                class="search-icon"
                viewBox="0 0 24 24"
                width="18"
                height="18"
              >
                <path
                  fill="currentColor"
                  d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"
                />
              </svg>
              <input
                v-model="searchKeyword"
                type="text"
                placeholder="搜索快捷键..."
                class="search-input"
              >
            </div>

            <div
              v-if="showCategories"
              class="category-tabs"
            >
              <button
                v-for="cat in categories"
                :key="cat.key"
                :class="['category-tab', { active: selectedCategory === cat.key }]"
                @click="selectedCategory = cat.key"
              >
                {{ cat.label }}
                <span class="count">{{ cat.count }}</span>
              </button>
            </div>
          </div>

          <!-- 冲突提示 -->
          <div
            v-if="hasConflicts && showConflicts"
            class="conflicts-warning"
          >
            <svg
              viewBox="0 0 24 24"
              width="18"
              height="18"
            >
              <path
                fill="currentColor"
                d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"
              />
            </svg>
            <span>检测到 {{ conflicts.length }} 个快捷键冲突</span>
            <button
              class="view-conflicts-btn"
              @click="showConflicts = !showConflicts"
            >
              查看详情
            </button>
          </div>

          <!-- 快捷键列表 -->
          <div class="panel-content">
            <div
              v-for="(shortcuts, category) in filteredGrouped"
              :key="category"
              class="shortcut-group"
            >
              <h3
                v-if="selectedCategory === 'all'"
                class="group-title"
              >
                {{ getCategoryLabel(category) }}
              </h3>

              <div class="shortcut-list">
                <div
                  v-for="shortcut in shortcuts"
                  :key="shortcut.id"
                  class="shortcut-item"
                  @click="handleShortcutClick(shortcut.id)"
                >
                  <div class="shortcut-info">
                    <span class="shortcut-description">{{ shortcut.description }}</span>
                    <span class="shortcut-id">{{ shortcut.id }}</span>
                  </div>
                  <div class="shortcut-keys">
                    <kbd
                      v-for="(part, index) in formatShortcut(shortcut).split(' + ')"
                      :key="index"
                      class="key"
                    >
                      {{ part }}
                    </kbd>
                  </div>
                </div>
              </div>
            </div>

            <!-- 空状态 -->
            <div
              v-if="filteredShortcuts.length === 0"
              class="empty-state"
            >
              <svg
                viewBox="0 0 24 24"
                width="48"
                height="48"
              >
                <path
                  fill="currentColor"
                  d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"
                />
              </svg>
              <p>未找到匹配的快捷键</p>
            </div>
          </div>

          <!-- 底部提示 -->
          <footer class="panel-footer">
            <p class="tip">
              <kbd class="key small">Esc</kbd> 关闭此面板
            </p>
            <p class="tip">
              点击快捷键可执行对应操作
            </p>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped lang="scss">
.shortcut-help-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.shortcut-help-panel {
  background: var(--bg-color, #fff);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  width: 90%;
  max-width: 700px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-color, #e8e8e8);
}

.panel-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-color, #262626);
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  border-radius: 6px;
  cursor: pointer;
  color: var(--text-secondary, #8c8c8c);
  transition: all 0.2s;

  &:hover {
    background: var(--bg-secondary, #f5f5f5);
    color: var(--text-color, #262626);
  }
}

.panel-toolbar {
  padding: 12px 24px;
  border-bottom: 1px solid var(--border-color, #e8e8e8);
}

.search-box {
  position: relative;
  margin-bottom: 12px;
}

.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-secondary, #8c8c8c);
}

.search-input {
  width: 100%;
  padding: 8px 12px 8px 40px;
  border: 1px solid var(--border-color, #d9d9d9);
  border-radius: 6px;
  font-size: 14px;
  background: var(--bg-secondary, #f5f5f5);
  color: var(--text-color, #262626);
  transition: all 0.2s;

  &:focus {
    outline: none;
    border-color: var(--primary-color, #1890ff);
    box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
  }

  &::placeholder {
    color: var(--text-secondary, #8c8c8c);
  }
}

.category-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.category-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid var(--border-color, #d9d9d9);
  border-radius: 16px;
  background: transparent;
  font-size: 13px;
  color: var(--text-secondary, #8c8c8c);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--primary-color, #1890ff);
    color: var(--primary-color, #1890ff);
  }

  &.active {
    background: var(--primary-color, #1890ff);
    border-color: var(--primary-color, #1890ff);
    color: #fff;

    .count {
      background: rgba(255, 255, 255, 0.2);
    }
  }

  .count {
    padding: 2px 6px;
    background: var(--bg-secondary, #f5f5f5);
    border-radius: 10px;
    font-size: 11px;
  }
}

.conflicts-warning {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: #fff7e6;
  border-bottom: 1px solid #ffd591;
  color: #d46b08;
  font-size: 13px;
}

.view-conflicts-btn {
  margin-left: auto;
  padding: 4px 12px;
  border: 1px solid #ffd591;
  border-radius: 4px;
  background: transparent;
  color: #d46b08;
  font-size: 12px;
  cursor: pointer;

  &:hover {
    background: #fff1b8;
  }
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px;
}

.shortcut-group {
  margin-bottom: 24px;

  &:last-child {
    margin-bottom: 0;
  }
}

.group-title {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary, #8c8c8c);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.shortcut-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.shortcut-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--bg-secondary, #f5f5f5);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: var(--primary-color, #1890ff);

    .shortcut-description,
    .shortcut-id {
      color: #fff;
    }

    .key {
      background: rgba(255, 255, 255, 0.2);
      color: #fff;
    }
  }
}

.shortcut-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.shortcut-description {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-color, #262626);
}

.shortcut-id {
  font-size: 12px;
  color: var(--text-secondary, #8c8c8c);
  font-family: monospace;
}

.shortcut-keys {
  display: flex;
  gap: 4px;
}

.key {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  height: 24px;
  padding: 0 8px;
  background: #fff;
  border: 1px solid var(--border-color, #d9d9d9);
  border-radius: 4px;
  font-size: 12px;
  font-family: monospace;
  color: var(--text-color, #262626);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);

  &.small {
    min-width: auto;
    height: 20px;
    padding: 0 6px;
    font-size: 11px;
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  color: var(--text-secondary, #8c8c8c);

  svg {
    margin-bottom: 16px;
    opacity: 0.5;
  }

  p {
    margin: 0;
    font-size: 14px;
  }
}

.panel-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  border-top: 1px solid var(--border-color, #e8e8e8);
  background: var(--bg-secondary, #fafafa);
}

.tip {
  margin: 0;
  font-size: 12px;
  color: var(--text-secondary, #8c8c8c);
  display: flex;
  align-items: center;
  gap: 6px;
}

// 过渡动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;

  .shortcut-help-panel {
    transition: transform 0.2s ease;
  }
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;

  .shortcut-help-panel {
    transform: scale(0.95);
  }
}
</style>
