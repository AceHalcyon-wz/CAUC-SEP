<template>
  <div class="settings-performance-page">
    <!-- 页面头部 -->
    <el-row class="page-header">
      <el-col :span="24">
        <div class="header-content">
          <div class="header-left">
            <el-icon class="header-icon">
              <DataAnalysis />
            </el-icon>
            <div class="header-text">
              <h1 class="page-title">
                性能分析
              </h1>
              <p class="page-subtitle">
                系统性能监控与资源使用分析
              </p>
            </div>
          </div>
          <div class="header-right">
            <el-button
              class="action-btn"
              :loading="loading"
              @click="refreshData"
            >
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button
              class="action-btn"
              @click="generateReport"
            >
              <el-icon><Document /></el-icon>
              生成报告
            </el-button>
            <el-button
              class="action-btn"
              @click="handleExportReport"
            >
              <el-icon><Download /></el-icon>
              导出报告
            </el-button>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 性能摘要卡片 -->
    <el-row
      :gutter="24"
      class="summary-row"
    >
      <el-col
        :xs="24"
        :sm="12"
        :lg="6"
      >
        <el-card class="summary-card cpu-card">
          <div class="summary-content">
            <div class="summary-icon">
              <el-icon><Cpu /></el-icon>
            </div>
            <div class="summary-info">
              <div class="summary-value">
                {{ systemSummary.cpu_percent?.toFixed(1) || 0 }}%
              </div>
              <div class="summary-label">
                CPU使用率
              </div>
            </div>
          </div>
          <el-progress 
            :percentage="systemSummary.cpu_percent || 0" 
            :color="getProgressColor(systemSummary.cpu_percent)"
            :show-text="false"
          />
        </el-card>
      </el-col>

      <el-col
        :xs="24"
        :sm="12"
        :lg="6"
      >
        <el-card class="summary-card memory-card">
          <div class="summary-content">
            <div class="summary-icon">
              <el-icon><Coin /></el-icon>
            </div>
            <div class="summary-info">
              <div class="summary-value">
                {{ systemSummary.memory_percent?.toFixed(1) || 0 }}%
              </div>
              <div class="summary-label">
                内存使用率
              </div>
            </div>
          </div>
          <el-progress 
            :percentage="systemSummary.memory_percent || 0" 
            :color="getProgressColor(systemSummary.memory_percent)"
            :show-text="false"
          />
        </el-card>
      </el-col>

      <el-col
        :xs="24"
        :sm="12"
        :lg="6"
      >
        <el-card class="summary-card function-card">
          <div class="summary-content">
            <div class="summary-icon">
              <el-icon><Operation /></el-icon>
            </div>
            <div class="summary-info">
              <div class="summary-value">
                {{ functionSummary.tracked_count || 0 }}
              </div>
              <div class="summary-label">
                追踪函数数
              </div>
            </div>
          </div>
          <div class="summary-detail">
            总调用: {{ functionSummary.total_calls || 0 }} 次
          </div>
        </el-card>
      </el-col>

      <el-col
        :xs="24"
        :sm="12"
        :lg="6"
      >
        <el-card class="summary-card time-card">
          <div class="summary-content">
            <div class="summary-icon">
              <el-icon><Timer /></el-icon>
            </div>
            <div class="summary-info">
              <div class="summary-value">
                {{ (functionSummary.total_time_sec || 0).toFixed(3) }}s
              </div>
              <div class="summary-label">
                总执行时间
              </div>
            </div>
          </div>
          <div class="summary-detail">
            峰值内存: {{ (memorySummary.peak_memory_mb || 0).toFixed(2) }} MB
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 详细信息标签页 -->
    <el-card class="detail-card">
      <el-tabs
        v-model="activeTab"
        @tab-click="handleTabClick"
      >
        <!-- 系统资源 -->
        <el-tab-pane
          label="系统资源"
          name="system"
        >
          <div class="tab-content">
            <el-row :gutter="24">
              <el-col
                :xs="24"
                :lg="12"
              >
                <div class="section-title">
                  <el-icon><Monitor /></el-icon>
                  <span>CPU信息</span>
                </div>
                <el-descriptions
                  :column="1"
                  border
                  class="info-descriptions"
                >
                  <el-descriptions-item label="CPU使用率">
                    <el-tag :type="getTagType(systemInfo.cpu?.percent)">
                      {{ (systemInfo.cpu?.percent || 0).toFixed(1) }}%
                    </el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="CPU核心数">
                    {{ systemInfo.cpu?.cpu_count || 0 }}
                  </el-descriptions-item>
                </el-descriptions>
              </el-col>

              <el-col
                :xs="24"
                :lg="12"
              >
                <div class="section-title">
                  <el-icon><Coin /></el-icon>
                  <span>内存信息</span>
                </div>
                <el-descriptions
                  :column="1"
                  border
                  class="info-descriptions"
                >
                  <el-descriptions-item label="总内存">
                    {{ (systemInfo.memory?.total_mb || 0).toFixed(0) }} MB
                  </el-descriptions-item>
                  <el-descriptions-item label="已用内存">
                    <el-tag :type="getTagType(systemInfo.memory?.percent)">
                      {{ (systemInfo.memory?.used_mb || 0).toFixed(0) }} MB
                    </el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="可用内存">
                    {{ (systemInfo.memory?.available_mb || 0).toFixed(0) }} MB
                  </el-descriptions-item>
                  <el-descriptions-item label="使用率">
                    <el-progress 
                      :percentage="systemInfo.memory?.percent || 0" 
                      :color="getProgressColor(systemInfo.memory?.percent)"
                    />
                  </el-descriptions-item>
                </el-descriptions>
              </el-col>
            </el-row>

            <el-row
              :gutter="24"
              style="margin-top: 24px;"
            >
              <el-col
                :xs="24"
                :lg="12"
              >
                <div class="section-title">
                  <el-icon><Folder /></el-icon>
                  <span>磁盘信息</span>
                </div>
                <el-descriptions
                  :column="1"
                  border
                  class="info-descriptions"
                >
                  <el-descriptions-item label="总容量">
                    {{ (systemInfo.disk?.total_gb || 0).toFixed(2) }} GB
                  </el-descriptions-item>
                  <el-descriptions-item label="已用空间">
                    {{ (systemInfo.disk?.used_gb || 0).toFixed(2) }} GB
                  </el-descriptions-item>
                  <el-descriptions-item label="可用空间">
                    {{ (systemInfo.disk?.free_gb || 0).toFixed(2) }} GB
                  </el-descriptions-item>
                  <el-descriptions-item label="使用率">
                    <el-progress 
                      :percentage="systemInfo.disk?.percent || 0" 
                      :color="getProgressColor(systemInfo.disk?.percent)"
                    />
                  </el-descriptions-item>
                </el-descriptions>
              </el-col>

              <el-col
                :xs="24"
                :lg="12"
              >
                <div class="section-title">
                  <el-icon><User /></el-icon>
                  <span>进程信息</span>
                </div>
                <el-descriptions
                  :column="1"
                  border
                  class="info-descriptions"
                >
                  <el-descriptions-item label="进程ID">
                    {{ systemInfo.process?.pid || 0 }}
                  </el-descriptions-item>
                  <el-descriptions-item label="进程CPU">
                    {{ (systemInfo.process?.cpu_percent || 0).toFixed(1) }}%
                  </el-descriptions-item>
                  <el-descriptions-item label="进程内存">
                    {{ (systemInfo.process?.memory_mb || 0).toFixed(2) }} MB
                  </el-descriptions-item>
                  <el-descriptions-item label="线程数">
                    {{ systemInfo.process?.num_threads || 0 }}
                  </el-descriptions-item>
                </el-descriptions>
              </el-col>
            </el-row>
          </div>
        </el-tab-pane>

        <!-- 函数性能 -->
        <el-tab-pane
          label="函数性能"
          name="functions"
        >
          <div class="tab-content">
            <div class="tab-header">
              <div class="tab-actions">
                <el-button
                  type="primary"
                  size="small"
                  :loading="profiling"
                  @click="startProfiling"
                >
                  开始分析
                </el-button>
                <el-button
                  size="small"
                  :disabled="!profiling"
                  @click="stopProfiling"
                >
                  停止分析
                </el-button>
                <el-button
                  size="small"
                  @click="loadFunctionProfiles"
                >
                  刷新数据
                </el-button>
              </div>
            </div>

            <el-table 
              v-loading="loadingFunctions" 
              :data="functionProfiles" 
              stripe
              style="width: 100%"
              max-height="500"
            >
              <el-table-column
                prop="function_name"
                label="函数名"
                min-width="200"
                show-overflow-tooltip
              />
              <el-table-column
                prop="total_calls"
                label="调用次数"
                width="100"
                align="right"
              />
              <el-table-column
                prop="total_time"
                label="总时间(s)"
                width="120"
                align="right"
              >
                <template #default="{ row }">
                  {{ row.total_time.toFixed(6) }}
                </template>
              </el-table-column>
              <el-table-column
                prop="avg_time"
                label="平均时间(s)"
                width="120"
                align="right"
              >
                <template #default="{ row }">
                  <el-tag
                    :type="getAvgTimeTagType(row.avg_time)"
                    size="small"
                  >
                    {{ row.avg_time.toFixed(6) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column
                prop="min_time"
                label="最小时间(s)"
                width="120"
                align="right"
              >
                <template #default="{ row }">
                  {{ row.min_time.toFixed(6) }}
                </template>
              </el-table-column>
              <el-table-column
                prop="max_time"
                label="最大时间(s)"
                width="120"
                align="right"
              >
                <template #default="{ row }">
                  {{ row.max_time.toFixed(6) }}
                </template>
              </el-table-column>
              <el-table-column
                prop="cumulative_time"
                label="累计时间(s)"
                width="120"
                align="right"
              >
                <template #default="{ row }">
                  {{ row.cumulative_time.toFixed(6) }}
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <!-- 性能热点 -->
        <el-tab-pane
          label="性能热点"
          name="hotspots"
        >
          <div class="tab-content">
            <div class="tab-header">
              <div class="filter-group">
                <span class="filter-label">时间阈值:</span>
                <el-input-number 
                  v-model="hotspotThreshold" 
                  :min="1" 
                  :max="1000" 
                  :step="10"
                  size="small"
                  style="width: 120px;"
                />
                <span class="filter-unit">ms</span>
                <el-button
                  size="small"
                  style="margin-left: 16px;"
                  @click="loadHotspots"
                >
                  应用筛选
                </el-button>
              </div>
            </div>

            <el-table 
              v-loading="loadingHotspots" 
              :data="hotspots" 
              stripe
              style="width: 100%"
              max-height="500"
            >
              <el-table-column
                type="index"
                label="#"
                width="50"
              />
              <el-table-column
                prop="function_name"
                label="函数名"
                min-width="200"
                show-overflow-tooltip
              />
              <el-table-column
                prop="total_calls"
                label="调用次数"
                width="100"
                align="right"
              />
              <el-table-column
                prop="avg_time"
                label="平均时间(ms)"
                width="120"
                align="right"
              >
                <template #default="{ row }">
                  <el-tag
                    type="danger"
                    size="small"
                  >
                    {{ (row.avg_time * 1000).toFixed(3) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column
                prop="total_time"
                label="总时间(ms)"
                width="120"
                align="right"
              >
                <template #default="{ row }">
                  {{ (row.total_time * 1000).toFixed(3) }}
                </template>
              </el-table-column>
              <el-table-column
                prop="file_path"
                label="文件路径"
                min-width="200"
                show-overflow-tooltip
              />
              <el-table-column
                prop="line_number"
                label="行号"
                width="80"
                align="right"
              />
            </el-table>

            <el-empty
              v-if="hotspots.length === 0 && !loadingHotspots"
              description="暂无性能热点数据"
            />
          </div>
        </el-tab-pane>

        <!-- 内存分析 -->
        <el-tab-pane
          label="内存分析"
          name="memory"
        >
          <div class="tab-content">
            <div class="tab-header">
              <div class="tab-actions">
                <el-button
                  type="primary"
                  size="small"
                  :loading="memoryTracking"
                  @click="startMemoryTracking"
                >
                  开始追踪
                </el-button>
                <el-button
                  size="small"
                  :disabled="!memoryTracking"
                  @click="stopMemoryTracking"
                >
                  停止追踪
                </el-button>
                <el-button
                  size="small"
                  @click="loadMemorySnapshots"
                >
                  刷新数据
                </el-button>
              </div>
            </div>

            <el-row :gutter="24">
              <el-col
                v-for="(snapshot, index) in memorySnapshots"
                :key="index"
                :xs="24"
                :lg="12"
              >
                <el-card class="memory-snapshot-card">
                  <template #header>
                    <div class="snapshot-header">
                      <span>快照 #{{ index + 1 }}</span>
                      <span class="snapshot-time">{{ snapshot.timestamp }}</span>
                    </div>
                  </template>
                  <el-descriptions
                    :column="1"
                    border
                  >
                    <el-descriptions-item label="当前内存">
                      {{ snapshot.current_memory_mb.toFixed(2) }} MB
                    </el-descriptions-item>
                    <el-descriptions-item label="峰值内存">
                      <el-tag type="warning">
                        {{ snapshot.peak_memory_mb.toFixed(2) }} MB
                      </el-tag>
                    </el-descriptions-item>
                    <el-descriptions-item label="内存块数">
                      {{ snapshot.memory_blocks }}
                    </el-descriptions-item>
                  </el-descriptions>

                  <div
                    v-if="snapshot.top_allocations && snapshot.top_allocations.length > 0"
                    style="margin-top: 16px;"
                  >
                    <div class="section-title">
                      <el-icon><Top /></el-icon>
                      <span>TOP内存分配</span>
                    </div>
                    <el-table
                      :data="snapshot.top_allocations.slice(0, 5)"
                      size="small"
                    >
                      <el-table-column
                        prop="file"
                        label="位置"
                        show-overflow-tooltip
                      />
                      <el-table-column
                        prop="size_mb"
                        label="大小(MB)"
                        width="100"
                        align="right"
                      >
                        <template #default="{ row }">
                          {{ row.size_mb.toFixed(2) }}
                        </template>
                      </el-table-column>
                      <el-table-column
                        prop="count"
                        label="次数"
                        width="80"
                        align="right"
                      />
                    </el-table>
                  </div>
                </el-card>
              </el-col>
            </el-row>

            <el-empty
              v-if="memorySnapshots.length === 0 && !loadingMemory"
              description="暂无内存快照数据"
            />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
/**
 * @file Performance.vue
 * @path src/views/settings/
 * @description 性能分析页面组件
 * @author Agent
 * @date 2026-03-07
 */

import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  DataAnalysis,
  Refresh,
  Document,
  Download,
  Cpu,
  Coin,
  Operation,
  Timer,
  Monitor,
  Folder,
  User,
  Top
} from '@element-plus/icons-vue'
import { apiRequest } from '@/utils/apiRequest'

// ==================== 响应式状态 ====================

const loading = ref(false)
const loadingFunctions = ref(false)
const loadingHotspots = ref(false)
const loadingMemory = ref(false)
const profiling = ref(false)
const memoryTracking = ref(false)
const activeTab = ref('system')

// 系统信息
const systemInfo = ref({
  cpu: {},
  memory: {},
  disk: {},
  process: {}
})

// 性能摘要
const systemSummary = ref({})
const functionSummary = ref({})
const memorySummary = ref({})

// 函数性能
const functionProfiles = ref([])

// 性能热点
const hotspots = ref([])
const hotspotThreshold = ref(10)

// 内存快照
const memorySnapshots = ref([])

// 自动刷新定时器
let autoRefreshTimer = null

// ==================== API调用 ====================

/**
 * 加载系统信息
 */
async function loadSystemInfo() {
  try {
    const data = await apiRequest('/api/v1/performance/system')
    systemInfo.value = data
  } catch (error) {
    console.error('[Performance] Failed to load system info:', error)
  }
}

/**
 * 加载性能摘要
 */
async function loadSummary() {
  try {
    const data = await apiRequest('/api/v1/performance/summary')
    systemSummary.value = data.system || {}
    functionSummary.value = data.functions || {}
    memorySummary.value = data.memory || {}
  } catch (error) {
    console.error('[Performance] Failed to load summary:', error)
  }
}

/**
 * 加载函数性能数据
 */
async function loadFunctionProfiles() {
  loadingFunctions.value = true
  try {
    const data = await apiRequest('/api/v1/performance/functions')
    functionProfiles.value = data.function_profiles || []
  } catch (error) {
    console.error('[Performance] Failed to load function profiles:', error)
    ElMessage.error('加载函数性能数据失败')
  } finally {
    loadingFunctions.value = false
  }
}

/**
 * 加载性能热点
 */
async function loadHotspots() {
  loadingHotspots.value = true
  try {
    const data = await apiRequest(
      `/api/v1/performance/hotspots?threshold_ms=${hotspotThreshold.value}&limit=50`
    )
    hotspots.value = data.hotspots || []
  } catch (error) {
    console.error('[Performance] Failed to load hotspots:', error)
    ElMessage.error('加载性能热点失败')
  } finally {
    loadingHotspots.value = false
  }
}

/**
 * 加载内存快照
 */
async function loadMemorySnapshots() {
  loadingMemory.value = true
  try {
    const data = await apiRequest('/api/v1/performance/memory/snapshots')
    memorySnapshots.value = data.snapshots || []
  } catch (error) {
    console.error('[Performance] Failed to load memory snapshots:', error)
    ElMessage.error('加载内存快照失败')
  } finally {
    loadingMemory.value = false
  }
}

/**
 * 开始性能分析
 */
async function startProfiling() {
  try {
    await apiRequest('/api/v1/performance/profile/start', { method: 'POST' })
    profiling.value = true
    ElMessage.success('性能分析已开始')
  } catch (error) {
    console.error('[Performance] Failed to start profiling:', error)
    ElMessage.error('启动性能分析失败')
  }
}

/**
 * 停止性能分析
 */
async function stopProfiling() {
  try {
    const data = await apiRequest('/api/v1/performance/profile/stop', { method: 'POST' })
    profiling.value = false
    ElMessage.success(`性能分析已停止，分析了 ${data.result?.total_functions || 0} 个函数`)
    // 自动刷新函数列表
    await loadFunctionProfiles()
  } catch (error) {
    console.error('[Performance] Failed to stop profiling:', error)
    ElMessage.error('停止性能分析失败')
  }
}

/**
 * 开始内存追踪
 */
async function startMemoryTracking() {
  try {
    await apiRequest('/api/v1/performance/memory/track/start', { method: 'POST' })
    memoryTracking.value = true
    ElMessage.success('内存追踪已开始')
  } catch (error) {
    console.error('[Performance] Failed to start memory tracking:', error)
    ElMessage.error('启动内存追踪失败')
  }
}

/**
 * 停止内存追踪
 */
async function stopMemoryTracking() {
  try {
    const data = await apiRequest('/api/v1/performance/memory/track/stop', { method: 'POST' })
    memoryTracking.value = false
    ElMessage.success(`内存追踪已停止，峰值内存: ${data.peak_memory_mb?.toFixed(2) || 0} MB`)
    // 自动刷新内存快照
    await loadMemorySnapshots()
  } catch (error) {
    console.error('[Performance] Failed to stop memory tracking:', error)
    ElMessage.error('停止内存追踪失败')
  }
}

/**
 * 生成性能报告
 */
async function generateReport() {
  try {
    const data = await apiRequest(
      '/api/v1/performance/report/generate?include_functions=true&include_memory=true&include_system=true',
      { method: 'POST' }
    )
    ElMessage.success('性能报告已生成')
    console.log('[Performance] Report generated:', data.report)
  } catch (error) {
    console.error('[Performance] Failed to generate report:', error)
    ElMessage.error('生成性能报告失败')
  }
}

/**
 * 导出性能报告
 */
async function handleExportReport() {
  try {
    const data = await apiRequest(
      '/api/v1/performance/report/export?format=pdf',
      { method: 'POST' }
    )
    ElMessage.success('性能报告已导出')
    console.log('[Performance] Report exported:', data)
  } catch (error) {
    console.error('[Performance] Failed to export report:', error)
    ElMessage.error('导出性能报告失败')
  }
}

/**
 * 刷新所有数据
 */
async function refreshData() {
  loading.value = true
  try {
    await Promise.all([
      loadSystemInfo(),
      loadSummary(),
      loadFunctionProfiles(),
      loadHotspots(),
      loadMemorySnapshots()
    ])
    ElMessage.success('数据已刷新')
  } catch (error) {
    console.error('[Performance] Failed to refresh data:', error)
  } finally {
    loading.value = false
  }
}

/**
 * 标签页切换处理
 */
function handleTabClick(tab) {
  // 根据标签页加载对应数据
  switch (tab.paneName) {
    case 'system':
      loadSystemInfo()
      break
    case 'functions':
      loadFunctionProfiles()
      break
    case 'hotspots':
      loadHotspots()
      break
    case 'memory':
      loadMemorySnapshots()
      break
  }
}

// ==================== 工具函数 ====================

/**
 * 获取进度条颜色
 */
function getProgressColor(percent) {
  if (percent >= 90) return '#f56c6c'
  if (percent >= 70) return '#e6a23c'
  return '#67c23a'
}

/**
 * 获取标签类型
 */
function getTagType(percent) {
  if (percent >= 90) return 'danger'
  if (percent >= 70) return 'warning'
  return 'success'
}

/**
 * 获取平均时间标签类型
 */
function getAvgTimeTagType(avgTime) {
  if (avgTime >= 0.1) return 'danger'
  if (avgTime >= 0.01) return 'warning'
  return 'success'
}

// ==================== 生命周期 ====================

onMounted(() => {
  // 初始加载数据
  refreshData()

  // 设置自动刷新（每10秒）
  autoRefreshTimer = setInterval(() => {
    loadSummary()
    if (activeTab.value === 'system') {
      loadSystemInfo()
    }
  }, 10000)
})

onUnmounted(() => {
  // 清理定时器
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer)
    autoRefreshTimer = null
  }
})
</script>

<style scoped lang="scss">
.settings-performance-page {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  background-color: var(--color-bg-secondary);
}

/* 页面头部 */
.page-header {
  background-color: var(--color-surface-primary);
  border-bottom: 1px solid var(--color-border-primary);
  padding: var(--spacing-6);
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  max-width: var(--content-max-width);
  margin: 0 auto;
  width: 100%;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
}

.header-icon {
  font-size: 32px;
  color: var(--color-primary-500);
  padding: var(--spacing-3);
  background-color: var(--color-primary-50);
  border-radius: var(--radius-lg);
  transition: var(--transition-all);
}

.header-icon:hover {
  background-color: var(--color-primary-100);
  transform: scale(1.05);
}

.header-text {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-1);
}

.page-title {
  margin: 0;
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  line-height: var(--line-height-tight);
}

.page-subtitle {
  margin: 0;
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.header-right {
  display: flex;
  gap: var(--spacing-3);
}

.action-btn {
  transition: var(--transition-all);
  border: 1px solid var(--color-border-primary);
}

.action-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--color-primary-300);
}

.action-btn:active:not(:disabled) {
  transform: translateY(0);
}

/* 摘要卡片行 */
.summary-row {
  margin-bottom: var(--spacing-6);
  padding: 0 var(--spacing-6);
  max-width: var(--content-max-width);
  margin-left: auto;
  margin-right: auto;
  width: 100%;
}

.summary-card {
  border-radius: var(--radius-lg);
  transition: var(--transition-all);
  border: 1px solid var(--color-border-primary);
  overflow: hidden;

  &:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-lg);
    border-color: var(--color-primary-200);
  }
}

.summary-content {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-4);
}

.summary-icon {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  color: white;
  transition: var(--transition-transform);
}

.summary-card:hover .summary-icon {
  transform: scale(1.1);
}

.cpu-card .summary-icon {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.memory-card .summary-icon {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.function-card .summary-icon {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.time-card .summary-icon {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
}

.summary-info {
  flex: 1;
}

.summary-value {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  line-height: var(--line-height-tight);
  font-family: var(--font-family-mono);
}

.summary-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-top: var(--spacing-1);
}

.summary-detail {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin-top: var(--spacing-2);
  font-family: var(--font-family-mono);
}

/* 详细信息卡片 */
.detail-card {
  border-radius: var(--radius-lg);
  margin: 0 var(--spacing-6);
  max-width: var(--content-max-width);
  margin-left: auto;
  margin-right: auto;
  width: 100%;
  border: 1px solid var(--color-border-primary);
  box-shadow: var(--shadow-sm);
}

/* 标签页内容 */
.tab-content {
  padding: var(--spacing-6) 0;
}

.tab-header {
  margin-bottom: var(--spacing-6);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-4);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-secondary);
}

.tab-actions {
  display: flex;
  gap: var(--spacing-3);
}

.tab-actions .el-button {
  transition: var(--transition-all);
}

.tab-actions .el-button:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.filter-group {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.filter-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

.filter-unit {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

/* 区块标题 */
.section-title {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  margin-bottom: var(--spacing-4);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  padding-bottom: var(--spacing-2);
  border-bottom: 2px solid var(--color-primary-100);
}

.section-title .el-icon {
  color: var(--color-primary-500);
}

.info-descriptions {
  margin-bottom: var(--spacing-6);
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--color-border-primary);
}

.info-descriptions :deep(.el-descriptions__label) {
  background-color: var(--color-bg-secondary);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
}

.info-descriptions :deep(.el-descriptions__content) {
  background-color: var(--color-surface-primary);
}

/* 内存快照卡片 */
.memory-snapshot-card {
  margin-bottom: var(--spacing-6);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-primary);
  transition: var(--transition-all);
}

.memory-snapshot-card:hover {
  box-shadow: var(--shadow-md);
  border-color: var(--color-primary-200);
}

.snapshot-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.snapshot-time {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  font-family: var(--font-family-mono);
}

/* 表格样式 */
:deep(.el-table) {
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--color-border-primary);
}

:deep(.el-table th.el-table__cell) {
  background-color: var(--color-bg-secondary);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-semibold);
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell) {
  background-color: var(--color-bg-tertiary);
}

:deep(.el-table__row) {
  transition: var(--transition-all);
}

:deep(.el-table__row:hover > td.el-table__cell) {
  background-color: var(--color-interactive-hover) !important;
}

/* 标签页样式 */
:deep(.el-tabs__header) {
  margin-bottom: 0;
  border-bottom: 2px solid var(--color-border-primary);
}

:deep(.el-tabs__nav-wrap)::after {
  display: none;
}

:deep(.el-tabs__item) {
  font-weight: var(--font-weight-medium);
  transition: var(--transition-all);
  padding: 0 var(--spacing-6);
  height: 48px;
  line-height: 48px;
}

:deep(.el-tabs__item:hover) {
  color: var(--color-primary-500);
}

:deep(.el-tabs__item.is-active) {
  color: var(--color-primary-500);
  font-weight: var(--font-weight-semibold);
}

:deep(.el-tabs__active-bar) {
  height: 3px;
  background-color: var(--color-primary-500);
}

/* 响应式适配 */
@media (max-width: 768px) {
  .page-header {
    padding: var(--spacing-4);
  }

  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-4);
  }

  .header-right {
    width: 100%;
    justify-content: flex-end;
    flex-wrap: wrap;
  }

  .action-btn {
    flex: 1;
    min-width: 100px;
  }

  .page-title {
    font-size: var(--font-size-xl);
  }

  .summary-row {
    padding: 0 var(--spacing-4);
  }

  .detail-card {
    margin: 0 var(--spacing-4);
  }

  .summary-row {
    .el-col {
      margin-bottom: var(--spacing-4);
    }
  }

  .tab-header {
    flex-direction: column;
    gap: var(--spacing-3);
    align-items: flex-start;
  }

  .tab-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .filter-group {
    flex-wrap: wrap;
  }

  .summary-value {
    font-size: var(--font-size-2xl);
  }
}
</style>
