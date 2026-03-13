<script setup lang="ts">
/**
 * @file ChartToolbar.vue
 * @path src/components/
 * @description 图表工具栏组件，提供图表类型切换、缩放控制、标注工具和导出功能
 * @author Agent
 * @date 2024-03-07
 */

import { ref, computed } from 'vue';
import {
  ElButton,
  ElButtonGroup,
  ElTooltip,
  ElDropdown,
  ElDropdownMenu,
  ElDropdownItem,
  ElIcon,
  ElDivider,
  ElSwitch,
  ElInputNumber,
  ElMessage,
} from 'element-plus';
import {
  TrendCharts,
  DataLine,
  Histogram,
  DataAnalysis,
  Picture,
  ZoomIn,
  ZoomOut,
  RefreshRight,
  Location,
  Aim,
  Download,
  Upload,
  Setting,
  Grid,
  FullScreen,
  PictureFilled,
  Document,
  DataBoard,
} from '@element-plus/icons-vue';

/** 图表类型定义 */
interface ChartType {
  value: string;
  label: string;
  icon: any;
}

/** 标注类型定义 */
interface AnnotationType {
  value: string;
  label: string;
  icon: any;
}

/** Props定义 */
interface Props {
  /** 当前图表类型 */
  chartType?: string;
  /** 是否显示网格 */
  showGrid?: boolean;
  /** 是否启用缩放 */
  enableZoom?: boolean;
  /** 缩放比例 */
  zoomLevel?: number;
  /** 当前标注模式 */
  annotationMode?: string;
}

/** Emits定义 */
const emit = defineEmits<{
  (e: 'update:chartType', value: string): void;
  (e: 'update:showGrid', value: boolean): void;
  (e: 'update:enableZoom', value: boolean): void;
  (e: 'update:zoomLevel', value: number): void;
  (e: 'update:annotationMode', value: string): void;
  (e: 'zoomIn'): void;
  (e: 'zoomOut'): void;
  (e: 'resetView'): void;
  (e: 'exportImage', format: string): void;
  (e: 'exportConfig'): void;
  (e: 'importConfig'): void;
  (e: 'saveTemplate'): void;
  (e: 'toggleFullscreen'): void;
  (e: 'clearAnnotations'): void;
}>();

const props = withDefaults(defineProps<Props>(), {
  chartType: 'line',
  showGrid: true,
  enableZoom: true,
  zoomLevel: 100,
  annotationMode: 'none',
});

/** 图表类型列表 */
const chartTypes: ChartType[] = [
  { value: 'line', label: '折线图', icon: DataLine },
  { value: 'scatter', label: '散点图', icon: DataAnalysis },
  { value: 'bar', label: '柱状图', icon: Histogram },
  { value: 'area', label: '面积图', icon: Picture },
  { value: 'mixed', label: '混合图', icon: DataBoard },
];

/** 标注类型列表 */
const annotationTypes: AnnotationType[] = [
  { value: 'point', label: '点标注', icon: Location },
  { value: 'line', label: '线标注', icon: TrendCharts },
  { value: 'area', label: '区域标注', icon: Picture },
  { value: 'measure', label: '距离测量', icon: Aim },
];

/** 当前选中的图表类型 */
const currentChartType = computed({
  get: () => props.chartType,
  set: (value: string) => emit('update:chartType', value),
});

/** 显示网格 */
const gridVisible = computed({
  get: () => props.showGrid,
  set: (value: boolean) => emit('update:showGrid', value),
});

/** 启用缩放 */
const zoomEnabled = computed({
  get: () => props.enableZoom,
  set: (value: boolean) => emit('update:enableZoom', value),
});

/** 缩放级别 */
const currentZoomLevel = computed({
  get: () => props.zoomLevel,
  set: (value: number) => emit('update:zoomLevel', value),
});

/** 当前标注模式 */
const currentAnnotationMode = computed({
  get: () => props.annotationMode,
  set: (value: string) => emit('update:annotationMode', value),
});

/**
 * 处理图表类型切换
 * 
 * @param {string} type - 图表类型
 */
function handleChartTypeChange(type: string): void {
  currentChartType.value = type;
}

/**
 * 处理缩放放大
 */
function handleZoomIn(): void {
  if (currentZoomLevel.value < 500) {
    currentZoomLevel.value = Math.min(currentZoomLevel.value + 25, 500);
    emit('zoomIn');
  }
}

/**
 * 处理缩放缩小
 */
function handleZoomOut(): void {
  if (currentZoomLevel.value > 25) {
    currentZoomLevel.value = Math.max(currentZoomLevel.value - 25, 25);
    emit('zoomOut');
  }
}

/**
 * 重置视图
 */
function handleResetView(): void {
  currentZoomLevel.value = 100;
  emit('resetView');
}

/**
 * 导出图片
 * 
 * @param {string} format - 图片格式
 */
function handleExportImage(format: string): void {
  emit('exportImage', format);
  ElMessage.success(`正在导出${format.toUpperCase()}格式图片`);
}

/**
 * 导出配置
 */
function handleExportConfig(): void {
  emit('exportConfig');
}

/**
 * 导入配置
 */
function handleImportConfig(): void {
  emit('importConfig');
}

/**
 * 保存模板
 */
function handleSaveTemplate(): void {
  emit('saveTemplate');
  ElMessage.success('图表模板已保存');
}

/**
 * 切换全屏
 */
function handleToggleFullscreen(): void {
  emit('toggleFullscreen');
}

/**
 * 切换标注模式
 * 
 * @param {string} mode - 标注模式
 */
function handleAnnotationModeChange(mode: string): void {
  currentAnnotationMode.value = currentAnnotationMode.value === mode ? 'none' : mode;
}

/**
 * 清除标注
 */
function handleClearAnnotations(): void {
  emit('clearAnnotations');
  ElMessage.success('已清除所有标注');
}
</script>

<template>
  <div class="chart-toolbar">
    <!-- 图表类型选择 -->
    <div class="toolbar-section">
      <span class="section-label">图表类型</span>
      <ElButtonGroup>
        <ElTooltip
          v-for="type in chartTypes"
          :key="type.value"
          :content="type.label"
          placement="bottom"
        >
          <ElButton
            :type="currentChartType === type.value ? 'primary' : 'default'"
            :icon="type.icon"
            @click="handleChartTypeChange(type.value)"
          />
        </ElTooltip>
      </ElButtonGroup>
    </div>

    <ElDivider direction="vertical" />

    <!-- 缩放控制 -->
    <div class="toolbar-section">
      <span class="section-label">缩放控制</span>
      <ElButtonGroup>
        <ElTooltip
          content="放大"
          placement="bottom"
        >
          <ElButton
            :icon="ZoomIn"
            @click="handleZoomIn"
          />
        </ElTooltip>
        <ElTooltip
          content="缩小"
          placement="bottom"
        >
          <ElButton
            :icon="ZoomOut"
            @click="handleZoomOut"
          />
        </ElTooltip>
        <ElTooltip
          content="重置视图"
          placement="bottom"
        >
          <ElButton
            :icon="RefreshRight"
            @click="handleResetView"
          />
        </ElTooltip>
      </ElButtonGroup>
      <div class="zoom-level">
        <span>{{ currentZoomLevel }}%</span>
      </div>
    </div>

    <ElDivider direction="vertical" />

    <!-- 标注工具 -->
    <div class="toolbar-section">
      <span class="section-label">标注工具</span>
      <ElButtonGroup>
        <ElTooltip
          v-for="annotation in annotationTypes"
          :key="annotation.value"
          :content="annotation.label"
          placement="bottom"
        >
          <ElButton
            :type="currentAnnotationMode === annotation.value ? 'primary' : 'default'"
            :icon="annotation.icon"
            @click="handleAnnotationModeChange(annotation.value)"
          />
        </ElTooltip>
        <ElTooltip
          content="清除标注"
          placement="bottom"
        >
          <ElButton
            :icon="RefreshRight"
            @click="handleClearAnnotations"
          />
        </ElTooltip>
      </ElButtonGroup>
    </div>

    <ElDivider direction="vertical" />

    <!-- 显示设置 -->
    <div class="toolbar-section">
      <span class="section-label">显示设置</span>
      <div class="setting-item">
        <ElIcon><Grid /></ElIcon>
        <span>网格</span>
        <ElSwitch
          v-model="gridVisible"
          size="small"
        />
      </div>
      <div class="setting-item">
        <ElIcon><FullScreen /></ElIcon>
        <span>全屏</span>
        <ElButton
          :icon="FullScreen"
          size="small"
          @click="handleToggleFullscreen"
        />
      </div>
    </div>

    <ElDivider direction="vertical" />

    <!-- 导出功能 -->
    <div class="toolbar-section">
      <span class="section-label">导出</span>
      <ElDropdown @command="handleExportImage">
        <ElButton
          type="primary"
          :icon="Download"
        >
          导出图片 <ElIcon class="el-icon--right">
            <PictureFilled />
          </ElIcon>
        </ElButton>
        <template #dropdown>
          <ElDropdownMenu>
            <ElDropdownItem command="png">
              <ElIcon><PictureFilled /></ElIcon>
              PNG 格式
            </ElDropdownItem>
            <ElDropdownItem command="jpeg">
              <ElIcon><PictureFilled /></ElIcon>
              JPEG 格式
            </ElDropdownItem>
            <ElDropdownItem command="svg">
              <ElIcon><PictureFilled /></ElIcon>
              SVG 格式
            </ElDropdownItem>
          </ElDropdownMenu>
        </template>
      </ElDropdown>

      <ElDropdown>
        <ElButton :icon="Setting">
          配置管理 <ElIcon class="el-icon--right">
            <Setting />
          </ElIcon>
        </ElButton>
        <template #dropdown>
          <ElDropdownMenu>
            <ElDropdownItem @click="handleExportConfig">
              <ElIcon><Download /></ElIcon>
              导出配置
            </ElDropdownItem>
            <ElDropdownItem @click="handleImportConfig">
              <ElIcon><Upload /></ElIcon>
              导入配置
            </ElDropdownItem>
            <ElDropdownItem
              divided
              @click="handleSaveTemplate"
            >
              <ElIcon><Document /></ElIcon>
              保存为模板
            </ElDropdownItem>
          </ElDropdownMenu>
        </template>
      </ElDropdown>
    </div>
  </div>
</template>

<style scoped lang="scss">
.chart-toolbar {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
  padding: var(--spacing-4);
  background-color: var(--color-surface-primary);
  border-bottom: 1px solid var(--color-border-primary);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  flex-wrap: wrap;
}

.toolbar-section {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.section-label {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.zoom-level {
  display: flex;
  align-items: center;
  padding: 0 var(--spacing-3);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-primary-500);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
  height: 32px;
  min-width: 60px;
  justify-content: center;
}

.setting-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: 0 var(--spacing-2);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);

  .el-icon {
    font-size: var(--font-size-base);
  }

  span {
    white-space: nowrap;
  }
}

/* Element Plus 样式覆盖 */
:deep(.el-button-group) {
  display: flex;
}

:deep(.el-divider--vertical) {
  height: 24px;
  margin: 0 var(--spacing-2);
}

:deep(.el-button) {
  font-weight: var(--font-weight-medium);
}

/* 响应式优化 */
@media (max-width: 1200px) {
  .chart-toolbar {
    gap: var(--spacing-3);
  }

  .section-label {
    display: none;
  }

  .setting-item span {
    display: none;
  }
}

@media (max-width: 768px) {
  .chart-toolbar {
    padding: var(--spacing-3);
    gap: var(--spacing-2);
  }

  .el-divider--vertical {
    display: none;
  }

  .toolbar-section {
    flex-wrap: wrap;
  }
}
</style>
