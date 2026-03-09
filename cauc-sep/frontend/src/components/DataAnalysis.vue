<template>
  <div class="data-analysis">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>数据分析</span>
          <div class="header-actions">
            <el-button 
              :type="showAnnotationPanel ? 'primary' : 'default'" 
              size="small" 
              @click="showAnnotationPanel = !showAnnotationPanel"
            >
              {{ showAnnotationPanel ? '关闭标注' : '开启标注' }}
            </el-button>
            <el-button 
              type="warning" 
              size="small"
              @click="showHistoryDialog = true"
            >
              历史记录
            </el-button>
            <el-dropdown
              style="margin-left: 10px;"
              @command="handleExportCommand"
            >
              <el-button
                type="success"
                size="small"
              >
                导出数据 <el-icon class="el-icon--right">
                  <arrow-down />
                </el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="csv">
                    导出为 CSV
                  </el-dropdown-item>
                  <el-dropdown-item command="png">
                    导出图表为 PNG
                  </el-dropdown-item>
                  <el-dropdown-item command="svg">
                    导出图表为 SVG
                  </el-dropdown-item>
                  <el-dropdown-item
                    divided
                    command="report-json"
                  >
                    导出报告 (JSON)
                  </el-dropdown-item>
                  <el-dropdown-item command="report-csv">
                    导出报告 (CSV)
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </template>

      <!-- 标注面板 -->
      <el-collapse-transition>
        <div
          v-show="showAnnotationPanel"
          class="annotation-panel"
        >
          <el-card shadow="hover">
            <template #header>
              <div class="panel-header">
                <span>标注工具</span>
                <el-button
                  type="danger"
                  size="small"
                  @click="clearAllMarks"
                >
                  清除所有标注
                </el-button>
              </div>
            </template>
            <el-form
              :inline="true"
              size="small"
            >
              <el-form-item label="标注类型">
                <el-radio-group v-model="annotationType">
                  <el-radio-button label="point">
                    标注点
                  </el-radio-button>
                  <el-radio-button label="line">
                    标注线
                  </el-radio-button>
                </el-radio-group>
              </el-form-item>
            </el-form>
            <el-alert 
              type="info" 
              :closable="false" 
              show-icon
              style="margin-top: 10px;"
            >
              <template #title>
                点击图表上的数据点即可添加{{ annotationType === 'point' ? '标注点' : '标注线' }}
              </template>
            </el-alert>
            <div
              v-if="markPoints.length > 0 || markLines.length > 0"
              class="marks-display"
            >
              <el-divider />
              <h4>已添加的标注</h4>
              <el-tag 
                v-for="(point, index) in markPoints" 
                :key="`point-${index}`"
                closable
                style="margin: 5px;"
                @close="removeMarkPoint(index)"
              >
                {{ point.name }}: {{ point.value }}
              </el-tag>
              <el-tag 
                v-for="(line, index) in markLines" 
                :key="`line-${index}`"
                type="warning"
                closable
                style="margin: 5px;"
                @close="removeMarkLine(index)"
              >
                {{ line.name }}: {{ line.yAxis?.toFixed(4) }}
              </el-tag>
            </div>
          </el-card>
        </div>
      </el-collapse-transition>

      <el-alert
        v-if="motorStore.alarmMessage"
        :title="motorStore.alarmMessage"
        type="error"
        :closable="true"
        style="margin-bottom: 20px"
        @close="motorStore.clearAlarm()"
      />

      <el-tabs
        v-model="activeTab"
        type="border-card"
      >
        <!-- 信号平滑标签页 -->
        <el-tab-pane
          label="信号平滑"
          name="smooth"
        >
          <el-row :gutter="20">
            <el-col :span="8">
              <el-card shadow="hover">
                <template #header>
                  <span>平滑参数</span>
                </template>
                <el-form label-width="120px">
                  <el-form-item label="平滑方法">
                    <el-select
                      v-model="smoothConfig.method"
                      placeholder="选择方法"
                    >
                      <el-option
                        label="Savitzky-Golay 滤波"
                        value="savitzky_golay"
                      />
                      <el-option
                        label="巴特沃斯低通滤波"
                        value="butterworth"
                      />
                    </el-select>
                  </el-form-item>
                  <template v-if="smoothConfig.method === 'savitzky_golay'">
                    <el-form-item label="窗口长度">
                      <el-input-number
                        v-model="smoothConfig.window_length"
                        :min="3"
                        :max="101"
                        :step="2"
                        style="width: 100%"
                      />
                    </el-form-item>
                    <el-form-item label="多项式阶数">
                      <el-input-number
                        v-model="smoothConfig.polyorder"
                        :min="1"
                        :max="7"
                        style="width: 100%"
                      />
                    </el-form-item>
                  </template>
                  <template v-if="smoothConfig.method === 'butterworth'">
                    <el-form-item label="截止频率">
                      <el-input-number
                        v-model="smoothConfig.butter_lowcut"
                        :min="0.01"
                        :max="10"
                        :step="0.01"
                        style="width: 100%"
                      />
                    </el-form-item>
                    <el-form-item label="滤波器阶数">
                      <el-input-number
                        v-model="smoothConfig.butter_order"
                        :min="1"
                        :max="10"
                        style="width: 100%"
                      />
                    </el-form-item>
                  </template>
                  <el-form-item>
                    <el-button
                      type="primary"
                      :loading="motorStore.loading.smooth"
                      style="width: 100%; margin-bottom: 10px;"
                      @click="generateDemoData"
                    >
                      生成示例数据
                    </el-button>
                    <el-button
                      type="success"
                      :loading="motorStore.loading.smooth"
                      :disabled="!rawData.length"
                      style="width: 100%"
                      @click="applySmooth"
                    >
                      应用平滑
                    </el-button>
                  </el-form-item>
                </el-form>
                <el-divider />
                <div
                  v-if="isLargeSmoothData"
                  class="optimization-info"
                >
                  <el-alert
                    type="warning"
                    :closable="false"
                    show-icon
                  >
                    <template #title>
                      大数据量优化已启用
                    </template>
                    数据已自动采样以提升性能
                  </el-alert>
                </div>
              </el-card>
            </el-col>
            <el-col :span="16">
              <el-card shadow="hover">
                <template #header>
                  <div class="chart-header">
                    <span>数据图表</span>
                    <div class="chart-tips">
                      <el-tag
                        size="small"
                        type="info"
                      >
                        滚轮缩放
                      </el-tag>
                      <el-tag
                        size="small"
                        type="info"
                        style="margin-left: 5px;"
                      >
                        拖拽平移
                      </el-tag>
                    </div>
                  </div>
                </template>
                <div
                  ref="smoothChartRef"
                  style="height: 450px;"
                />
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- 磁滞回线分析标签页 -->
        <el-tab-pane
          label="磁滞回线分析"
          name="hysteresis"
        >
          <el-row :gutter="20">
            <el-col :span="8">
              <el-card shadow="hover">
                <template #header>
                  <span>分析参数</span>
                </template>
                <el-form label-width="140px">
                  <el-form-item label="扣除背景">
                    <el-switch v-model="hysteresisConfig.subtract_background" />
                  </el-form-item>
                  <el-form-item label="饱和阈值">
                    <el-input-number
                      v-model="hysteresisConfig.saturation_threshold"
                      :min="0.5"
                      :max="1"
                      :step="0.01"
                      style="width: 100%"
                    />
                  </el-form-item>
                  <el-form-item>
                    <el-button
                      type="primary"
                      :loading="motorStore.loading.hysteresis"
                      style="width: 100%; margin-bottom: 10px;"
                      @click="generateHysteresisDemoData"
                    >
                      生成示例数据
                    </el-button>
                    <el-button
                      type="success"
                      :loading="motorStore.loading.hysteresis"
                      :disabled="!hysteresisData.x.length"
                      style="width: 100%"
                      @click="analyzeHysteresis"
                    >
                      分析磁滞回线
                    </el-button>
                  </el-form-item>
                </el-form>
                <el-divider />
                <div
                  v-if="hysteresisResult"
                  class="result-display"
                >
                  <h4>分析结果</h4>
                  <el-descriptions
                    :column="1"
                    border
                    size="small"
                  >
                    <el-descriptions-item label="矫顽力 (Hc)">
                      {{ hysteresisResult.Hc?.toFixed(4) }}
                    </el-descriptions-item>
                    <el-descriptions-item label="剩磁 (Mr)">
                      {{ hysteresisResult.Mr?.toFixed(4) }}
                    </el-descriptions-item>
                    <el-descriptions-item label="饱和磁矩 (Ms)">
                      {{ hysteresisResult.Ms?.toFixed(4) }}
                    </el-descriptions-item>
                  </el-descriptions>
                </div>
                <div
                  v-if="isLargeHysteresisData"
                  class="optimization-info"
                >
                  <el-alert
                    type="warning"
                    :closable="false"
                    show-icon
                    style="margin-top: 10px;"
                  >
                    <template #title>
                      大数据量优化已启用
                    </template>
                    数据已自动采样以提升性能
                  </el-alert>
                </div>
              </el-card>
            </el-col>
            <el-col :span="16">
              <el-card shadow="hover">
                <template #header>
                  <div class="chart-header">
                    <span>磁滞回线</span>
                    <div class="chart-tips">
                      <el-tag
                        size="small"
                        type="info"
                      >
                        滚轮缩放
                      </el-tag>
                      <el-tag
                        size="small"
                        type="info"
                        style="margin-left: 5px;"
                      >
                        拖拽平移
                      </el-tag>
                    </div>
                  </div>
                </template>
                <div
                  ref="hysteresisChartRef"
                  style="height: 450px;"
                />
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- 多模型对比标签页 -->
        <el-tab-pane
          label="多模型对比"
          name="multi-model"
        >
          <el-row :gutter="20">
            <el-col :span="8">
              <el-card shadow="hover">
                <template #header>
                  <span>模型选择</span>
                </template>
                <el-form label-width="120px">
                  <el-form-item label="选择模型">
                    <el-checkbox-group v-model="selectedModels">
                      <el-checkbox 
                        v-for="model in availableModels" 
                        :key="model.id" 
                        :label="model.id"
                      >
                        {{ model.name }}
                      </el-checkbox>
                    </el-checkbox-group>
                  </el-form-item>
                  <el-form-item>
                    <el-button 
                      type="primary" 
                      :loading="multiFitLoading" 
                      :disabled="!hysteresisData.x.length || selectedModels.length < 2"
                      style="width: 100%"
                      @click="runMultiModelFit"
                    >
                      执行多模型拟合
                    </el-button>
                  </el-form-item>
                </el-form>
                <el-divider />
                <div
                  v-if="bestModel"
                  class="result-display"
                >
                  <h4>最佳模型</h4>
                  <el-alert
                    type="success"
                    :closable="false"
                    show-icon
                  >
                    <template #title>
                      推荐使用: {{ getModelName(bestModel) }}
                    </template>
                    基于R²、AIC、BIC综合评估
                  </el-alert>
                </div>
              </el-card>
            </el-col>
            <el-col :span="16">
              <el-card shadow="hover">
                <template #header>
                  <div class="chart-header">
                    <span>模型对比结果</span>
                  </div>
                </template>
                <el-table 
                  v-if="multiFitResults.length > 0"
                  :data="multiFitResults" 
                  border 
                  stripe
                  style="width: 100%"
                >
                  <el-table-column
                    prop="model_name"
                    label="模型名称"
                    width="180"
                  />
                  <el-table-column
                    prop="r_squared"
                    label="R²"
                    width="120"
                  >
                    <template #default="{ row }">
                      <el-tag :type="getR2TagType(row.r_squared)">
                        {{ row.r_squared?.toFixed(4) }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column
                    prop="rmse"
                    label="RMSE"
                    width="120"
                  >
                    <template #default="{ row }">
                      {{ row.rmse?.toFixed(6) }}
                    </template>
                  </el-table-column>
                  <el-table-column
                    prop="aic"
                    label="AIC"
                    width="120"
                  >
                    <template #default="{ row }">
                      {{ row.aic?.toFixed(2) }}
                    </template>
                  </el-table-column>
                  <el-table-column
                    prop="bic"
                    label="BIC"
                    width="120"
                  >
                    <template #default="{ row }">
                      {{ row.bic?.toFixed(2) }}
                    </template>
                  </el-table-column>
                  <el-table-column
                    label="操作"
                    width="150"
                  >
                    <template #default="{ row }">
                      <el-button 
                        size="small" 
                        type="primary"
                        @click="viewModelDetails(row)"
                      >
                        查看详情
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
                <el-empty
                  v-else
                  description="请先执行多模型拟合"
                />
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>

        <!-- 分析报告标签页 -->
        <el-tab-pane
          label="分析报告"
          name="report"
        >
          <el-row :gutter="20">
            <el-col :span="8">
              <el-card shadow="hover">
                <template #header>
                  <span>报告配置</span>
                </template>
                <el-form label-width="140px">
                  <el-form-item label="包含原始数据">
                    <el-switch v-model="reportConfig.include_raw_data" />
                  </el-form-item>
                  <el-form-item>
                    <el-button 
                      type="primary" 
                      :loading="reportLoading"
                      :disabled="!hysteresisData.x.length"
                      style="width: 100%; margin-bottom: 10px;"
                      @click="generateReport"
                    >
                      生成报告
                    </el-button>
                    <el-dropdown 
                      style="width: 100%"
                      @command="exportReport"
                    >
                      <el-button 
                        type="success" 
                        :disabled="!reportData"
                        style="width: 100%"
                      >
                        导出报告 <el-icon class="el-icon--right">
                          <arrow-down />
                        </el-icon>
                      </el-button>
                      <template #dropdown>
                        <el-dropdown-menu>
                          <el-dropdown-item command="json">
                            JSON格式
                          </el-dropdown-item>
                          <el-dropdown-item command="csv">
                            CSV格式
                          </el-dropdown-item>
                        </el-dropdown-menu>
                      </template>
                    </el-dropdown>
                  </el-form-item>
                </el-form>
              </el-card>
            </el-col>
            <el-col :span="16">
              <el-card shadow="hover">
                <template #header>
                  <div class="chart-header">
                    <span>报告预览</span>
                  </div>
                </template>
                <div
                  v-if="reportData"
                  class="report-content"
                >
                  <div class="report-header">
                    <h3>磁滞回线分析报告</h3>
                    <p>实验ID: {{ reportData.experiment_id }}</p>
                    <p>分析时间: {{ formatTimestamp(reportData.timestamp) }}</p>
                  </div>
                  
                  <el-divider />
                  
                  <div class="report-section">
                    <h4>磁滞参数</h4>
                    <el-descriptions
                      :column="2"
                      border
                    >
                      <el-descriptions-item label="饱和磁感应强度 Bs">
                        {{ reportData.hysteresis_params?.Bs?.toFixed(4) }} T
                      </el-descriptions-item>
                      <el-descriptions-item label="矫顽力 Hc">
                        {{ reportData.hysteresis_params?.Hc?.toFixed(4) }} A/m
                      </el-descriptions-item>
                      <el-descriptions-item label="剩磁 Br">
                        {{ reportData.hysteresis_params?.Br?.toFixed(4) }} T
                      </el-descriptions-item>
                      <el-descriptions-item label="饱和磁场 Hs">
                        {{ reportData.hysteresis_params?.Hs?.toFixed(4) }} A/m
                      </el-descriptions-item>
                    </el-descriptions>
                  </div>
                  
                  <div
                    v-if="reportData.fit_results"
                    class="report-section"
                  >
                    <h4>拟合结果</h4>
                    <el-table
                      :data="reportData.fit_results"
                      border
                      size="small"
                    >
                      <el-table-column
                        prop="parameter"
                        label="参数"
                        width="150"
                      />
                      <el-table-column
                        prop="value"
                        label="数值"
                        width="150"
                      >
                        <template #default="{ row }">
                          {{ row.value?.toFixed(6) }}
                        </template>
                      </el-table-column>
                      <el-table-column
                        prop="unit"
                        label="单位"
                        width="100"
                      />
                      <el-table-column
                        prop="description"
                        label="描述"
                      />
                    </el-table>
                  </div>
                  
                  <div
                    v-if="reportData.quality_metrics"
                    class="report-section"
                  >
                    <h4>质量指标</h4>
                    <el-row :gutter="10">
                      <el-col
                        v-for="(value, key) in reportData.quality_metrics"
                        :key="key"
                        :span="6"
                      >
                        <el-statistic
                          :title="key"
                          :value="value"
                          :precision="4"
                        />
                      </el-col>
                    </el-row>
                  </div>
                  
                  <div
                    v-if="reportData.recommendations"
                    class="report-section"
                  >
                    <h4>分析建议</h4>
                    <el-alert 
                      v-for="(rec, index) in reportData.recommendations" 
                      :key="index"
                      :title="rec"
                      type="info"
                      :closable="false"
                      style="margin-bottom: 10px;"
                    />
                  </div>
                </div>
                <el-empty
                  v-else
                  description="请先生成分析报告"
                />
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 历史记录对话框 -->
    <el-dialog 
      v-model="showHistoryDialog" 
      title="分析历史记录" 
      width="70%"
      :close-on-click-modal="false"
    >
      <div class="history-toolbar">
        <el-button
          type="danger"
          size="small"
          @click="handleClearHistory"
        >
          清空历史
        </el-button>
      </div>
      <el-table
        :data="analysisHistory"
        border
        stripe
      >
        <el-table-column
          prop="timestamp"
          label="时间"
          width="180"
        >
          <template #default="{ row }">
            {{ formatTimestamp(row.timestamp) }}
          </template>
        </el-table-column>
        <el-table-column
          label="数据点数"
          width="120"
        >
          <template #default="{ row }">
            {{ row.result?.h_data?.length || 0 }}
          </template>
        </el-table-column>
        <el-table-column
          label="最佳模型"
          width="150"
        >
          <template #default="{ row }">
            {{ row.result?.best_model || '-' }}
          </template>
        </el-table-column>
        <el-table-column
          label="R²"
          width="120"
        >
          <template #default="{ row }">
            {{ row.result?.r_squared?.toFixed(4) || '-' }}
          </template>
        </el-table-column>
        <el-table-column
          label="操作"
          width="200"
        >
          <template #default="{ row }">
            <el-button
              size="small"
              type="primary"
              @click="loadHistoryRecord(row)"
            >
              加载
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="handleDeleteHistory(row.id)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 模型详情对话框 -->
    <el-dialog 
      v-model="showModelDetailDialog" 
      title="模型拟合详情" 
      width="60%"
    >
      <div
        v-if="selectedModelDetail"
        class="model-detail"
      >
        <el-descriptions
          :column="2"
          border
        >
          <el-descriptions-item label="模型名称">
            {{ selectedModelDetail.model_name }}
          </el-descriptions-item>
          <el-descriptions-item label="R²">
            {{ selectedModelDetail.r_squared?.toFixed(6) }}
          </el-descriptions-item>
          <el-descriptions-item label="RMSE">
            {{ selectedModelDetail.rmse?.toFixed(6) }}
          </el-descriptions-item>
          <el-descriptions-item label="AIC">
            {{ selectedModelDetail.aic?.toFixed(2) }}
          </el-descriptions-item>
          <el-descriptions-item label="BIC">
            {{ selectedModelDetail.bic?.toFixed(2) }}
          </el-descriptions-item>
        </el-descriptions>
        
        <div
          v-if="selectedModelDetail.parameters"
          style="margin-top: 20px;"
        >
          <h4>拟合参数</h4>
          <el-table
            :data="formatParameters(selectedModelDetail.parameters)"
            border
            size="small"
          >
            <el-table-column
              prop="name"
              label="参数名"
            />
            <el-table-column
              prop="value"
              label="数值"
            >
              <template #default="{ row }">
                {{ row.value?.toFixed(6) }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
/**
 * @file DataAnalysis.vue
 * @path src/components/
 * @description 数据分析组件，提供信号平滑、磁滞回线分析、多模型对比、报告生成等功能
 * @author Agent
 * @date 2024-03-07
 * @dependencies vue, pinia, element-plus, echarts, api/analysis
 */

import { ref, onMounted, onUnmounted, nextTick, computed, watch } from 'vue'
import { useMotorStore } from '../stores/motor'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import {
  downsampleArray,
  downsampleData,
  createZoomConfig,
  createMarkPointConfig,
  createMarkLineConfig,
  exportChartAsImage,
  exportChartAsSVG,
  createToolboxConfig,
  createTooltipConfig,
  getLargeDataOptimization,
  exportSmoothDataAsCSV,
  exportHysteresisDataAsCSV,
  smartSampling,
  BatchDataProcessor,
  FPSMonitor,
} from '../utils/chartUtils'
import {
  multiModelFit,
  generateAnalysisReport,
  exportAnalysisReport,
  getAnalysisHistory,
  saveAnalysisToHistory,
  deleteAnalysisHistory,
  clearAnalysisHistory,
} from '../api/analysis'

const motorStore = useMotorStore()

// ==================== 虚拟滚动和分页加载优化 ====================

/** 分页配置 */
const paginationConfig = ref({
  pageSize: 10000, // 每页数据量
  currentPage: 1,  // 当前页码
  total: 0,        // 总数据量
  totalPages: 0,   // 总页数
})

/** 是否正在加载数据 */
const isLoadingData = ref(false)

/** 数据缓冲区（用于分页加载） */
const dataBuffer = ref({
  raw: [],
  smoothed: [],
  hysteresisX: [],
  hysteresisY: [],
})

/** 虚拟滚动配置 */
const virtualScrollConfig = ref({
  enabled: true,        // 是否启用虚拟滚动
  visibleRange: 5000,   // 可见范围数据量
  bufferSize: 1000,     // 缓冲区大小
  threshold: 10000,     // 启用虚拟滚动的阈值
  overscan: 500,        // 预渲染数量
  debounceTime: 100,    // 滚动防抖时间
})

/** 是否需要虚拟滚动 */
const needsVirtualScroll = computed(() => {
  return virtualScrollConfig.value.enabled && 
         (rawData.value.length > virtualScrollConfig.value.threshold ||
          hysteresisData.value.x.length > virtualScrollConfig.value.threshold)
})

/** 当前可见的原始数据范围 */
const visibleDataRange = ref({
  start: 0,
  end: 5000,
})

/** 数据加载状态 */
const dataLoadState = ref({
  raw: { loaded: false, loading: false },
  smoothed: { loaded: false, loading: false },
  hysteresis: { loaded: false, loading: false },
})

/** 虚拟滚动性能监控 */
const virtualScrollMetrics = ref({
  renderTime: 0,
  itemCount: 0,
  fps: 60,
  lastUpdateTime: 0,
})

/** 数据分块缓存（用于快速访问） */
const dataChunkCache = ref(new Map())

/** 滚动防抖定时器 */
let scrollDebounceTimer = null

/**
 * 分页加载大数据
 * 
 * @param {string} dataType - 数据类型 ('raw' | 'smoothed' | 'hysteresis')
 * @param {number} page - 页码
 * @param {number} pageSize - 每页大小
 * @returns {Promise<Array>} 加载的数据
 */
async function loadPaginatedData(dataType, page = 1, pageSize = 10000) {
  const buffer = dataBuffer.value[dataType]
  if (!buffer || buffer.length === 0) return []
  
  const start = (page - 1) * pageSize
  const end = Math.min(start + pageSize, buffer.length)
  
  // 模拟异步加载（实际应用中可能是API请求）
  return new Promise(resolve => {
    setTimeout(() => {
      resolve(buffer.slice(start, end))
    }, 10)
  })
}

/**
 * 批量处理大数据
 * 
 * @param {Array} data - 原始数据
 * @param {Function} processor - 处理函数
 * @param {Function} onProgress - 进度回调
 * @returns {Promise<Array>} 处理后的数据
 */
async function processBatchData(data, processor, onProgress) {
  const batchProcessor = new BatchDataProcessor(1000, 16)
  return await batchProcessor.process(data, processor, onProgress)
}

/**
 * 更新可见数据范围（虚拟滚动）
 * 带防抖优化和性能监控
 * 
 * @param {number} start - 起始索引
 * @param {number} end - 结束索引
 * @param {boolean} immediate - 是否立即更新
 */
function updateVisibleRange(start, end, immediate = false) {
  const config = virtualScrollConfig.value
  
  // 添加预渲染范围
  const overscanStart = Math.max(0, start - config.overscan)
  const overscanEnd = end + config.overscan
  
  visibleDataRange.value = { start: overscanStart, end: overscanEnd }
  
  // 性能监控
  const updateStartTime = performance.now()
  
  // 使用防抖优化
  if (!immediate && config.debounceTime > 0) {
    if (scrollDebounceTimer) {
      clearTimeout(scrollDebounceTimer)
    }
    
    scrollDebounceTimer = setTimeout(() => {
      performChartUpdate()
      updatePerformanceMetrics(updateStartTime)
    }, config.debounceTime)
  } else {
    performChartUpdate()
    updatePerformanceMetrics(updateStartTime)
  }
}

/**
 * 执行图表更新
 */
function performChartUpdate() {
  if (activeTab.value === 'smooth') {
    updateSmoothChart()
  } else if (activeTab.value === 'hysteresis') {
    updateHysteresisChart()
  }
}

/**
 * 更新性能指标
 * 
 * @param {number} startTime - 开始时间
 */
function updatePerformanceMetrics(startTime) {
  const endTime = performance.now()
  virtualScrollMetrics.value.renderTime = endTime - startTime
  virtualScrollMetrics.value.lastUpdateTime = endTime
  
  // 更新数据项数量
  const range = visibleDataRange.value
  virtualScrollMetrics.value.itemCount = range.end - range.start
}

/**
 * 获取虚拟滚动的可见数据
 * 
 * @param {Array} data - 完整数据
 * @param {Object} range - 可见范围
 * @returns {Array} 可见数据
 */
function getVisibleData(data, range = visibleDataRange.value) {
  if (!data || data.length === 0) return []
  
  const { start, end } = range
  const visibleData = data.slice(start, end)
  
  return visibleData
}

/**
 * 预加载数据块（用于平滑滚动）
 * 
 * @param {string} dataType - 数据类型
 * @param {number} direction - 滚动方向 (1: 向下, -1: 向上)
 */
function preloadDataChunk(dataType, direction = 1) {
  const config = virtualScrollConfig.value
  const range = visibleDataRange.value
  
  // 计算预加载范围
  let preloadStart, preloadEnd
  
  if (direction > 0) {
    // 向下滚动，预加载下一块
    preloadStart = range.end
    preloadEnd = Math.min(range.end + config.bufferSize, getTotalDataLength(dataType))
  } else {
    // 向上滚动，预加载上一块
    preloadStart = Math.max(0, range.start - config.bufferSize)
    preloadEnd = range.start
  }
  
  // 检查缓存
  const cacheKey = `${dataType}_${preloadStart}_${preloadEnd}`
  if (dataChunkCache.value.has(cacheKey)) {
    return dataChunkCache.value.get(cacheKey)
  }
  
  // 加载数据
  const data = getDataByType(dataType)
  if (data && data.length > 0) {
    const chunk = data.slice(preloadStart, preloadEnd)
    dataChunkCache.value.set(cacheKey, chunk)
    
    // 限制缓存大小
    if (dataChunkCache.value.size > 100) {
      const firstKey = dataChunkCache.value.keys().next().value
      dataChunkCache.value.delete(firstKey)
    }
    
    return chunk
  }
  
  return []
}

/**
 * 获取数据总长度
 * 
 * @param {string} dataType - 数据类型
 * @returns {number} 数据长度
 */
function getTotalDataLength(dataType) {
  switch (dataType) {
    case 'raw':
      return rawData.value.length
    case 'smoothed':
      return smoothedData.value.length
    case 'hysteresisX':
      return hysteresisData.value.x.length
    case 'hysteresisY':
      return hysteresisData.value.y.length
    default:
      return 0
  }
}

/**
 * 根据类型获取数据
 * 
 * @param {string} dataType - 数据类型
 * @returns {Array} 数据数组
 */
function getDataByType(dataType) {
  switch (dataType) {
    case 'raw':
      return rawData.value
    case 'smoothed':
      return smoothedData.value
    case 'hysteresisX':
      return hysteresisData.value.x
    case 'hysteresisY':
      return hysteresisData.value.y
    default:
      return []
  }
}

/**
 * 处理图表数据缩放事件（虚拟滚动）
 * 
 * @param {Object} params - 缩放参数
 */
function handleDataZoom(params) {
  if (!needsVirtualScroll.value) return
  
  const { start, end } = params
  const totalLength = activeTab.value === 'smooth' 
    ? rawData.value.length 
    : hysteresisData.value.x.length
  
  const startIndex = Math.floor((start / 100) * totalLength)
  const endIndex = Math.ceil((end / 100) * totalLength)
  
  updateVisibleRange(startIndex, endIndex)
}

/**
 * 获取图表颜色配置
 * 返回图表使用的颜色方案
 */
function getChartThemeColors() {
  return {
    // 线条颜色
    rawLine: '#909399',
    smoothedLine: '#409eff',
    correctedLine: '#f56c6c',
    markPoint: '#f56c6c',
    
    // 背景色
    backgroundColor: '#ffffff',
    
    // 文字颜色
    textPrimary: '#1a202c',
    textSecondary: '#4a5568',
    
    // 坐标轴颜色
    axisLine: '#e2e8f0',
    splitLine: '#edf2f7',
    
    // 区域渐变
    areaGradient: {
      start: 'rgba(64, 158, 255, 0.3)',
      end: 'rgba(64, 158, 255, 0.05)'
    }
  }
}

/** 当前激活的标签页 */
const activeTab = ref('smooth')

/** 信号平滑图表容器引用 */
const smoothChartRef = ref(null)

/** 磁滞回线图表容器引用 */
const hysteresisChartRef = ref(null)

/** 信号平滑图表实例 */
let smoothChart = null

/** 磁滞回线图表实例 */
let hysteresisChart = null

/** 原始数据数组 */
const rawData = ref([])

/** 平滑后数据数组 */
const smoothedData = ref([])

/** 标注点数据 */
const markPoints = ref([])

/** 标注线数据 */
const markLines = ref([])

/** 是否显示标注面板 */
const showAnnotationPanel = ref(false)

/** 当前选中的标注类型 */
const annotationType = ref('point')

/** 信号平滑配置参数 */
const smoothConfig = ref({
  method: 'savitzky_golay',
  window_length: 11,
  polyorder: 3,
  butter_lowcut: 0.1,
  butter_order: 4
})

/** 磁滞回线数据 */
const hysteresisData = ref({ x: [], y: [] })

/** 磁滞回线分析结果 */
const hysteresisResult = ref(null)

/** 磁滞回线分析配置参数 */
const hysteresisConfig = ref({
  subtract_background: true,
  saturation_threshold: 0.9
})

/** 计算信号平滑数据是否为大数据量 */
const isLargeSmoothData = computed(() => rawData.value.length > 10000)

/** 计算磁滞回线数据是否为大数据量 */
const isLargeHysteresisData = computed(() => hysteresisData.value.x.length > 10000)

// ==================== 多模型对比功能 ====================

/** 可用模型列表 */
const availableModels = [
  { id: 'hyperbolic', name: '双曲正切模型' },
  { id: 'arctangent', name: '反正切模型' },
  { id: 'braunbeck', name: 'Braunbeck模型' },
  { id: 'langevin', name: 'Langevin模型' },
]

/** 选中的模型列表 */
const selectedModels = ref(['hyperbolic', 'arctangent', 'braunbeck'])

/** 多模型拟合结果 */
const multiFitResults = ref([])

/** 最佳模型 */
const bestModel = ref('')

/** 多模型拟合加载状态 */
const multiFitLoading = ref(false)

/** 模型详情对话框显示状态 */
const showModelDetailDialog = ref(false)

/** 选中的模型详情 */
const selectedModelDetail = ref(null)

// ==================== 分析报告功能 ====================

/** 报告数据 */
const reportData = ref(null)

/** 报告加载状态 */
const reportLoading = ref(false)

/** 报告配置 */
const reportConfig = ref({
  include_raw_data: false,
})

// ==================== 历史记录功能 ====================

/** 历史记录对话框显示状态 */
const showHistoryDialog = ref(false)

/** 分析历史记录 */
const analysisHistory = ref([])

/**
 * 生成信号平滑示例数据
 * 创建包含噪声的正弦波数据用于演示
 */
function generateDemoData() {
  const x = []
  const y = []
  // 生成大数据量以测试性能优化
  for (let i = 0; i < 50000; i++) {
    x.push(i)
    y.push(Math.sin(i * 0.01) + Math.random() * 0.3 - 0.15)
  }
  rawData.value = y
  smoothedData.value = []
  markPoints.value = []
  markLines.value = []
  ElMessage.success(`示例数据已生成 (${y.length} 个数据点)`)
  updateSmoothChart()
}

/**
 * 应用信号平滑处理
 * 调用后端API进行数据处理
 */
async function applySmooth() {
  if (!rawData.value.length) {
    ElMessage.warning('请先生成或加载数据')
    return
  }

  const config = {
    y_data: rawData.value,
    method: smoothConfig.value.method,
    window_length: smoothConfig.value.window_length,
    polyorder: smoothConfig.value.polyorder,
    butter_lowcut: smoothConfig.value.butter_lowcut,
    butter_order: smoothConfig.value.butter_order
  }

  const result = await motorStore.smoothSignal(config)
  if (result) {
    smoothedData.value = result.smoothed_data
    ElMessage.success('信号平滑完成')
    updateSmoothChart()
  }
}

/**
 * 更新信号平滑图表
 * 根据数据量自动优化渲染性能，支持虚拟滚动
 */
function updateSmoothChart() {
  if (!smoothChart) return

  const optimization = getLargeDataOptimization(rawData.value.length)
  const themeColors = getChartThemeColors()
  
  // 根据是否启用虚拟滚动选择数据
  let displayRawData, displaySmoothedData
  
  if (needsVirtualScroll.value) {
    // 虚拟滚动模式：只渲染可见区域的数据
    const range = visibleDataRange.value
    displayRawData = getVisibleData(rawData.value, range)
    displaySmoothedData = getVisibleData(smoothedData.value, range)
    
    // 预加载下一块数据
    requestIdleCallback(() => {
      preloadDataChunk('raw', 1)
      preloadDataChunk('smoothed', 1)
    })
  } else {
    // 传统模式：大数据量时进行采样
    displayRawData = optimization.isLargeData 
      ? downsampleArray(rawData.value, 5000)
      : rawData.value
    
    displaySmoothedData = optimization.isLargeData && smoothedData.value.length > 5000
      ? downsampleArray(smoothedData.value, 5000)
      : smoothedData.value
  }

  const series = []
  
  if (displayRawData.length) {
    series.push({
      name: '原始数据',
      type: 'line',
      data: displayRawData,
      symbol: 'none',
      lineStyle: { width: 1, color: themeColors.rawLine },
      // 大数据量优化
      animation: needsVirtualScroll.value ? false : optimization.animation,
      sampling: optimization.sampling,
      progressive: optimization.progressive,
      progressiveThreshold: optimization.progressiveThreshold,
      // 标注点
      markPoint: createMarkPointConfig(markPoints.value.filter(p => p.series === 'raw')),
      // 标注线
      markLine: createMarkLineConfig(markLines.value.filter(l => l.series === 'raw')),
    })
  }
  
  if (displaySmoothedData.length) {
    series.push({
      name: '平滑数据',
      type: 'line',
      data: displaySmoothedData,
      symbol: 'none',
      lineStyle: { width: 2, color: themeColors.smoothedLine },
      animation: needsVirtualScroll.value ? false : optimization.animation,
      sampling: optimization.sampling,
      progressive: optimization.progressive,
      progressiveThreshold: optimization.progressiveThreshold,
      markPoint: createMarkPointConfig(markPoints.value.filter(p => p.series === 'smoothed')),
      markLine: createMarkLineConfig(markLines.value.filter(l => l.series === 'smoothed')),
    })
  }

  // 计算X轴数据（考虑虚拟滚动的偏移）
  const xAxisData = needsVirtualScroll.value
    ? Array.from({ length: displayRawData.length }, (_, i) => visibleDataRange.value.start + i)
    : Array.from({ length: Math.max(displayRawData.length, displaySmoothedData.length) }, (_, i) => i)

  smoothChart.setOption({
    backgroundColor: themeColors.backgroundColor,
    title: { 
      text: '信号平滑对比',
      subtext: needsVirtualScroll.value 
        ? `虚拟滚动模式 (显示: ${displayRawData.length}/${rawData.value.length})`
        : optimization.isLargeData 
          ? `数据已采样显示 (原始: ${rawData.value.length})`
          : '',
      textStyle: { color: themeColors.textPrimary },
      subtextStyle: { color: themeColors.textSecondary }
    },
    tooltip: createTooltipConfig(),
    legend: { 
      data: ['原始数据', '平滑数据'], 
      top: optimization.isLargeData ? 50 : 30,
      textStyle: { color: themeColors.textSecondary }
    },
    grid: { 
      left: '3%', 
      right: '4%', 
      bottom: optimization.isLargeData ? '18%' : '10%', 
      top: optimization.isLargeData ? '20%' : '15%',
      containLabel: true 
    },
    xAxis: { 
      type: 'category', 
      data: xAxisData,
      name: '采样点',
      nameTextStyle: { color: themeColors.textSecondary },
      axisLine: { lineStyle: { color: themeColors.axisLine } },
      axisLabel: { color: themeColors.textSecondary },
      splitLine: { lineStyle: { color: themeColors.splitLine } }
    },
    yAxis: { 
      type: 'value',
      name: '幅值',
      nameTextStyle: { color: themeColors.textSecondary },
      axisLine: { lineStyle: { color: themeColors.axisLine } },
      axisLabel: { color: themeColors.textSecondary },
      splitLine: { lineStyle: { color: themeColors.splitLine } }
    },
    dataZoom: createZoomConfig({ 
      slider: optimization.isLargeData,
      start: needsVirtualScroll.value ? (visibleDataRange.value.start / rawData.value.length) * 100 : 0,
      end: needsVirtualScroll.value ? (visibleDataRange.value.end / rawData.value.length) * 100 : (optimization.isLargeData ? 10 : 100),
    }),
    toolbox: createToolboxConfig({ showDataView: true }),
    series
  }, true)
}

/**
 * 生成磁滞回线示例数据
 * 创建典型的磁滞回线数据用于演示
 */
function generateHysteresisDemoData() {
  const x = []
  const y = []

  // 生成更密集的数据点以测试性能
  for (let h = -1; h <= 1; h += 0.005) {
    x.push(h)
    y.push(Math.tanh(h * 5) + (h > 0 ? 0.1 : -0.1) + Math.random() * 0.05 - 0.025)
  }
  for (let h = 1; h >= -1; h -= 0.005) {
    x.push(h)
    y.push(Math.tanh(h * 5) + (h > 0 ? 0.1 : -0.1) + Math.random() * 0.05 - 0.025)
  }

  hysteresisData.value = { x, y }
  hysteresisResult.value = null
  markPoints.value = []
  markLines.value = []
  ElMessage.success(`磁滞回线示例数据已生成 (${x.length} 个数据点)`)
  updateHysteresisChart()
}

/**
 * 执行磁滞回线分析
 * 调用后端API进行分析计算
 */
async function analyzeHysteresis() {
  if (!hysteresisData.value.x.length) {
    ElMessage.warning('请先生成或加载数据')
    return
  }

  const config = {
    x_field: hysteresisData.value.x,
    y_moment: hysteresisData.value.y,
    subtract_background: hysteresisConfig.value.subtract_background,
    saturation_threshold: hysteresisConfig.value.saturation_threshold
  }

  const result = await motorStore.analyzeHysteresis(config)
  if (result) {
    hysteresisResult.value = result
    ElMessage.success('磁滞回线分析完成')
    updateHysteresisChart(result)
  }
}

/**
 * 更新磁滞回线图表
 * 
 * @param {Object|null} result - 分析结果数据
 */
function updateHysteresisChart(result = null) {
  if (!hysteresisChart) return

  const optimization = getLargeDataOptimization(hysteresisData.value.x.length)
  const themeColors = getChartThemeColors()
  
  // 大数据量时进行采样
  let displayData = hysteresisData.value.x.map((x, i) => [x, hysteresisData.value.y[i]])
  if (optimization.isLargeData) {
    displayData = downsampleData(displayData, 5000)
  }

  const series = [{
    name: '原始数据',
    type: 'line',
    data: displayData,
    symbol: 'circle',
    symbolSize: optimization.isLargeData ? 2 : 4,
    lineStyle: { width: 2, color: themeColors.smoothedLine },
    animation: optimization.animation,
    sampling: optimization.sampling,
    progressive: optimization.progressive,
    progressiveThreshold: optimization.progressiveThreshold,
    markPoint: createMarkPointConfig(markPoints.value.filter(p => p.series === 'hysteresis')),
    markLine: createMarkLineConfig(markLines.value.filter(l => l.series === 'hysteresis')),
  }]

  if (result && result.x_corrected) {
    let correctedData = result.x_corrected.map((x, i) => [x, result.y_corrected[i]])
    if (optimization.isLargeData && correctedData.length > 5000) {
      correctedData = downsampleData(correctedData, 5000)
    }
    
    series.push({
      name: '校正后数据',
      type: 'line',
      data: correctedData,
      symbol: 'none',
      lineStyle: { width: 2, color: themeColors.correctedLine },
      animation: optimization.animation,
      sampling: optimization.sampling,
    })
  }

  hysteresisChart.setOption({
    backgroundColor: themeColors.backgroundColor,
    title: { 
      text: '磁滞回线',
      subtext: optimization.isLargeData ? `数据已采样显示 (原始: ${hysteresisData.value.x.length})` : '',
      textStyle: { color: themeColors.textPrimary },
      subtextStyle: { color: themeColors.textSecondary }
    },
    tooltip: createTooltipConfig(),
    legend: { 
      data: ['原始数据', '校正后数据'], 
      top: optimization.isLargeData ? 50 : 30,
      textStyle: { color: themeColors.textSecondary }
    },
    grid: { 
      left: '3%', 
      right: '4%', 
      bottom: optimization.isLargeData ? '18%' : '10%', 
      top: optimization.isLargeData ? '20%' : '15%',
      containLabel: true 
    },
    xAxis: { 
      type: 'value', 
      name: '磁场 (H)',
      nameLocation: 'middle',
      nameGap: 30,
      nameTextStyle: { color: themeColors.textSecondary },
      axisLine: { lineStyle: { color: themeColors.axisLine } },
      axisLabel: { color: themeColors.textSecondary },
      splitLine: { lineStyle: { color: themeColors.splitLine } }
    },
    yAxis: { 
      type: 'value', 
      name: '磁矩 (M)',
      nameLocation: 'middle',
      nameGap: 40,
      nameTextStyle: { color: themeColors.textSecondary },
      axisLine: { lineStyle: { color: themeColors.axisLine } },
      axisLabel: { color: themeColors.textSecondary },
      splitLine: { lineStyle: { color: themeColors.splitLine } }
    },
    dataZoom: createZoomConfig({ 
      slider: optimization.isLargeData,
      xAxisIndex: 0,
      yAxisIndex: 0,
    }),
    toolbox: createToolboxConfig({ showDataView: true }),
    series
  }, true)
}

/**
 * 处理图表点击事件（用于添加标注）
 * 
 * @param {Object} params - 点击事件参数
 */
function handleChartClick(params) {
  if (!showAnnotationPanel.value) return
  
  const chartType = activeTab.value
  const seriesName = params.seriesName
  const themeColors = getChartThemeColors()
  
  if (annotationType.value === 'point') {
    // 添加标注点
    markPoints.value.push({
      series: chartType === 'smooth' ? (seriesName === '原始数据' ? 'raw' : 'smoothed') : 'hysteresis',
      name: `点${markPoints.value.length + 1}`,
      coord: [params.dataIndex, params.value],
      value: params.value.toFixed(4),
      color: themeColors.markPoint,
    })
    ElMessage.success(`已添加标注点: ${params.value.toFixed(4)}`)
  } else if (annotationType.value === 'line') {
    // 添加标注线
    markLines.value.push({
      series: chartType === 'smooth' ? (seriesName === '原始数据' ? 'raw' : 'smoothed') : 'hysteresis',
      name: `线${markLines.value.length + 1}`,
      yAxis: params.value,
    })
    ElMessage.success(`已添加标注线: ${params.value.toFixed(4)}`)
  }
  
  // 更新图表
  if (chartType === 'smooth') {
    updateSmoothChart()
  } else {
    updateHysteresisChart()
  }
}

/**
 * 清除所有标注
 */
function clearAllMarks() {
  markPoints.value = []
  markLines.value = []
  
  if (activeTab.value === 'smooth') {
    updateSmoothChart()
  } else {
    updateHysteresisChart()
  }
  
  ElMessage.success('已清除所有标注')
}

/**
 * 导出图表为 PNG 格式
 */
async function exportAsPNG() {
  const chartInstance = activeTab.value === 'smooth' ? smoothChart : hysteresisChart
  const fileName = activeTab.value === 'smooth' ? '信号平滑分析' : '磁滞回线分析'
  
  try {
    await exportChartAsImage(chartInstance, {
      fileName,
      type: 'png',
      pixelRatio: 2,
      backgroundColor: '#fff',
    })
    ElMessage.success('图表已导出为 PNG')
  } catch (error) {
    ElMessage.error('导出失败: ' + error.message)
  }
}

/**
 * 导出图表为 SVG 格式
 */
async function exportAsSVG() {
  const chartInstance = activeTab.value === 'smooth' ? smoothChart : hysteresisChart
  const fileName = activeTab.value === 'smooth' ? '信号平滑分析' : '磁滞回线分析'
  
  try {
    await exportChartAsSVG(chartInstance, fileName)
    ElMessage.success('图表已导出为 SVG')
  } catch (error) {
    ElMessage.error('导出失败: ' + error.message)
  }
}

/**
 * 导出数据为 CSV 格式
 */
async function exportAsCSV() {
  try {
    if (activeTab.value === 'smooth') {
      if (!rawData.value.length) {
        ElMessage.warning('没有数据可导出')
        return
      }
      await exportSmoothDataAsCSV(rawData.value, smoothedData.value, '信号平滑数据')
      ElMessage.success('数据已导出为 CSV')
    } else {
      if (!hysteresisData.value.x.length) {
        ElMessage.warning('没有数据可导出')
        return
      }
      await exportHysteresisDataAsCSV(
        hysteresisData.value.x, 
        hysteresisData.value.y, 
        hysteresisResult.value, 
        '磁滞回线数据'
      )
      ElMessage.success('数据已导出为 CSV')
    }
  } catch (error) {
    ElMessage.error('导出失败: ' + error.message)
  }
}

/**
 * 处理导出命令
 * 
 * @param {string} command - 导出命令类型
 */
function handleExportCommand(command) {
  if (command === 'csv') {
    exportAsCSV()
  } else if (command === 'png') {
    exportAsPNG()
  } else if (command === 'svg') {
    exportAsSVG()
  } else if (command === 'report-json') {
    exportReport('json')
  } else if (command === 'report-csv') {
    exportReport('csv')
  }
}

/**
 * 移除标注点
 * 
 * @param {number} index - 标注点索引
 */
function removeMarkPoint(index) {
  markPoints.value.splice(index, 1)
  
  if (activeTab.value === 'smooth') {
    updateSmoothChart()
  } else {
    updateHysteresisChart()
  }
}

/**
 * 移除标注线
 * 
 * @param {number} index - 标注线索引
 */
function removeMarkLine(index) {
  markLines.value.splice(index, 1)
  
  if (activeTab.value === 'smooth') {
    updateSmoothChart()
  } else {
    updateHysteresisChart()
  }
}

/**
 * 处理窗口大小变化
 * 调整图表尺寸以适应容器
 */
function handleResize() {
  if (smoothChart) {
    smoothChart.resize()
  }
  if (hysteresisChart) {
    hysteresisChart.resize()
  }
}

// ==================== 多模型对比功能 ====================

/**
 * 执行多模型拟合
 * 对比不同模型的拟合效果
 */
async function runMultiModelFit() {
  if (!hysteresisData.value.x.length) {
    ElMessage.warning('请先生成或加载数据')
    return
  }

  if (selectedModels.value.length < 2) {
    ElMessage.warning('请至少选择两个模型进行对比')
    return
  }

  multiFitLoading.value = true

  try {
    const result = await multiModelFit({
      h_data: hysteresisData.value.x,
      b_data: hysteresisData.value.y,
      models: selectedModels.value,
    })

    if (result) {
      multiFitResults.value = result.results || []
      bestModel.value = result.best_model || ''
      
      // 保存到历史记录
      saveAnalysisToHistory({
        h_data: hysteresisData.value.x,
        b_data: hysteresisData.value.y,
        best_model: bestModel.value,
        r_squared: multiFitResults.value[0]?.r_squared,
        results: multiFitResults.value,
      })
      
      ElMessage.success('多模型拟合完成')
    }
  } catch (error) {
    ElMessage.error('多模型拟合失败: ' + error.message)
  } finally {
    multiFitLoading.value = false
  }
}

/**
 * 获取模型名称
 * 
 * @param {string} modelId - 模型ID
 * @returns {string} 模型名称
 */
function getModelName(modelId) {
  const model = availableModels.find(m => m.id === modelId)
  return model ? model.name : modelId
}

/**
 * 获取R²值的标签类型
 * 
 * @param {number} r2 - R²值
 * @returns {string} 标签类型
 */
function getR2TagType(r2) {
  if (r2 >= 0.95) return 'success'
  if (r2 >= 0.90) return 'primary'
  if (r2 >= 0.80) return 'warning'
  return 'danger'
}

/**
 * 查看模型详情
 * 
 * @param {Object} model - 模型数据
 */
function viewModelDetails(model) {
  selectedModelDetail.value = model
  showModelDetailDialog.value = true
}

/**
 * 格式化参数为表格数据
 * 
 * @param {Object} parameters - 参数对象
 * @returns {Array} 格式化后的参数数组
 */
function formatParameters(parameters) {
  if (!parameters) return []
  return Object.entries(parameters).map(([name, value]) => ({
    name,
    value: typeof value === 'number' ? value : parseFloat(value),
  }))
}

// ==================== 分析报告功能 ====================

/**
 * 生成分析报告
 */
async function generateReport() {
  if (!hysteresisData.value.x.length) {
    ElMessage.warning('请先生成或加载数据')
    return
  }

  reportLoading.value = true

  try {
    const result = await generateAnalysisReport({
      h_data: hysteresisData.value.x,
      b_data: hysteresisData.value.y,
      include_raw_data: reportConfig.value.include_raw_data,
    })

    if (result) {
      reportData.value = result
      ElMessage.success('报告生成成功')
    }
  } catch (error) {
    ElMessage.error('报告生成失败: ' + error.message)
  } finally {
    reportLoading.value = false
  }
}

/**
 * 导出报告
 * 
 * @param {string} format - 导出格式 (json/csv)
 */
async function exportReport(format) {
  if (!reportData.value) {
    ElMessage.warning('请先生成报告')
    return
  }

  try {
    const blob = await exportAnalysisReport({
      h_data: hysteresisData.value.x,
      b_data: hysteresisData.value.y,
      format: format,
    })

    // 创建下载链接
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `analysis_report_${Date.now()}.${format}`
    link.click()
    window.URL.revokeObjectURL(url)

    ElMessage.success('报告导出成功')
  } catch (error) {
    ElMessage.error('报告导出失败: ' + error.message)
  }
}

/**
 * 格式化时间戳
 * 
 * @param {string} timestamp - ISO格式时间戳
 * @returns {string} 格式化后的时间字符串
 */
function formatTimestamp(timestamp) {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

// ==================== 历史记录功能 ====================

/**
 * 加载历史记录
 */
function loadHistory() {
  analysisHistory.value = getAnalysisHistory()
}

/**
 * 加载历史记录项
 * 
 * @param {Object} record - 历史记录项
 */
function loadHistoryRecord(record) {
  if (record.result) {
    if (record.result.h_data) {
      hysteresisData.value.x = record.result.h_data
    }
    if (record.result.b_data) {
      hysteresisData.value.y = record.result.b_data
    }
    if (record.result.results) {
      multiFitResults.value = record.result.results
    }
    if (record.result.best_model) {
      bestModel.value = record.result.best_model
    }
    
    updateHysteresisChart()
    showHistoryDialog.value = false
    ElMessage.success('历史记录已加载')
  }
}

/**
 * 删除历史记录项
 * 
 * @param {number} id - 记录ID
 */
function handleDeleteHistory(id) {
  const success = deleteAnalysisHistory(id)
  if (success) {
    loadHistory()
    ElMessage.success('记录已删除')
  } else {
    ElMessage.error('删除失败')
  }
}

/**
 * 清空所有历史记录
 */
function handleClearHistory() {
  const success = clearAnalysisHistory()
  if (success) {
    analysisHistory.value = []
    ElMessage.success('历史记录已清空')
  } else {
    ElMessage.error('清空失败')
  }
}

// ==================== 图表性能优化和内存管理 ====================

/** 图表性能监控器 */
let smoothChartPerformance = null
let hysteresisChartPerformance = null

/** 图表渲染队列（防止频繁更新） */
const chartUpdateQueue = ref({
  smooth: { pending: false, timer: null },
  hysteresis: { pending: false, timer: null },
})

/** 图表配置缓存（避免重复计算） */
const chartConfigCache = ref({
  smooth: null,
  hysteresis: null,
})

/**
 * 优化图表更新（防抖处理）
 * 
 * @param {string} chartType - 图表类型 ('smooth' | 'hysteresis')
 * @param {Function} updateFn - 更新函数
 * @param {number} delay - 延迟时间（毫秒）
 */
function optimizedChartUpdate(chartType, updateFn, delay = 100) {
  const queue = chartUpdateQueue.value[chartType]
  
  // 清除之前的定时器
  if (queue.timer) {
    clearTimeout(queue.timer)
  }
  
  // 标记为待更新
  queue.pending = true
  
  // 设置新的定时器
  queue.timer = setTimeout(() => {
    queue.pending = false
    queue.timer = null
    updateFn()
  }, delay)
}

/**
 * 清理图表内存
 * 释放不必要的缓存和数据
 */
function cleanupChartMemory() {
  // 清理配置缓存
  chartConfigCache.value.smooth = null
  chartConfigCache.value.hysteresis = null
  
  // 清理数据缓冲区（保留最近的数据）
  const maxBufferSize = 100000
  if (dataBuffer.value.raw.length > maxBufferSize) {
    dataBuffer.value.raw = dataBuffer.value.raw.slice(-maxBufferSize)
  }
  if (dataBuffer.value.smoothed.length > maxBufferSize) {
    dataBuffer.value.smoothed = dataBuffer.value.smoothed.slice(-maxBufferSize)
  }
  
  // 强制垃圾回收（如果可用）
  if (window.gc) {
    window.gc()
  }
  
  console.log('[DataAnalysis] 图表内存已清理')
}

/**
 * 监控图表性能
 * 
 * @param {string} chartType - 图表类型
 * @param {Object} chartInstance - 图表实例
 */
function monitorChartPerformance(chartType, chartInstance) {
  if (!chartInstance) return null
  
  const startTime = performance.now()
  let renderCount = 0
  
  const handleRendered = () => {
    renderCount++
    const endTime = performance.now()
    const renderTime = endTime - startTime
    
    console.log(`[${chartType}Chart] 渲染耗时: ${renderTime.toFixed(2)}ms, 渲染次数: ${renderCount}`)
    
    // 性能警告
    if (renderTime > 1000) {
      console.warn(`[${chartType}Chart] 渲染时间过长，建议优化数据量`)
    }
    
    // 更新性能指标
    if (chartType === 'smooth') {
      virtualScrollMetrics.value.renderTime = renderTime
    }
  }
  
  chartInstance.on('rendered', handleRendered)
  
  return {
    stop() {
      chartInstance.off('rendered', handleRendered)
    },
    getStats() {
      return { renderCount, startTime }
    }
  }
}

/**
 * 获取性能报告
 * 
 * @returns {Object} 性能报告
 */
function getPerformanceReport() {
  return {
    virtualScroll: {
      ...virtualScrollMetrics.value,
      enabled: needsVirtualScroll.value,
      config: virtualScrollConfig.value,
    },
    dataStats: {
      rawDataLength: rawData.value.length,
      smoothedDataLength: smoothedData.value.length,
      hysteresisDataLength: hysteresisData.value.x.length,
      visibleRange: visibleDataRange.value,
    },
    cacheStats: {
      chunkCacheSize: dataChunkCache.value.size,
      configCacheSize: chartConfigCache.value ? 1 : 0,
    },
    memory: getMemoryUsage(),
    timestamp: Date.now(),
  }
}

/**
 * 获取内存使用情况
 * 
 * @returns {Object|null} 内存使用情况
 */
function getMemoryUsage() {
  if (performance.memory) {
    return {
      usedJSHeapSize: (performance.memory.usedJSHeapSize / 1024 / 1024).toFixed(2) + ' MB',
      totalJSHeapSize: (performance.memory.totalJSHeapSize / 1024 / 1024).toFixed(2) + ' MB',
      jsHeapSizeLimit: (performance.memory.jsHeapSizeLimit / 1024 / 1024).toFixed(2) + ' MB',
    }
  }
  return null
}

/**
 * 导出性能报告
 */
function exportPerformanceReport() {
  const report = getPerformanceReport()
  const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `performance_report_${Date.now()}.json`
  link.click()
  URL.revokeObjectURL(url)
  
  ElMessage.success('性能报告已导出')
}

/**
 * 智能数据采样（根据性能自动调整）
 * 
 * @param {Array} data - 原始数据
 * @param {number} targetFps - 目标帧率
 * @returns {Array} 采样后的数据
 */
function smartAdaptiveSampling(data, targetFps = 30) {
  if (!data || data.length === 0) return data
  
  // 根据当前性能动态调整采样率
  const currentFps = getAverageFps()
  const performanceRatio = currentFps / targetFps
  
  // 性能良好，使用较少采样
  if (performanceRatio >= 1.2) {
    return data.length > 10000 ? downsampleArray(data, 8000) : data
  }
  
  // 性能一般，使用中等采样
  if (performanceRatio >= 0.8) {
    return data.length > 8000 ? downsampleArray(data, 5000) : data
  }
  
  // 性能较差，使用激进采样
  return data.length > 5000 ? downsampleArray(data, 3000) : data
}

/** FPS监控 */
let fpsMonitor = null
const fpsHistory = ref([])

/**
 * 获取平均FPS
 */
function getAverageFps() {
  if (fpsHistory.value.length === 0) return 60
  return fpsHistory.value.reduce((a, b) => a + b, 0) / fpsHistory.value.length
}

/**
 * 启动FPS监控
 */
function startFpsMonitor() {
  if (fpsMonitor) return
  
  fpsMonitor = new FPSMonitor()
  fpsMonitor.start()
  fpsMonitor.addListener((fps, history) => {
    fpsHistory.value = history.slice(-60) // 保留最近60秒
    
    // 性能过低时自动优化
    if (fps < 20) {
      console.warn('[DataAnalysis] FPS过低，自动优化图表')
      optimizeChartsForLowPerformance()
    }
  })
}

/**
 * 停止FPS监控
 */
function stopFpsMonitor() {
  if (fpsMonitor) {
    fpsMonitor.stop()
    fpsMonitor = null
  }
}

/**
 * 低性能时优化图表
 */
function optimizeChartsForLowPerformance() {
  // 降低采样率
  virtualScrollConfig.value.visibleRange = 3000
  
  // 禁用动画
  if (smoothChart) {
    const option = smoothChart.getOption()
    if (option.animation !== false) {
      smoothChart.setOption({ animation: false })
    }
  }
  
  if (hysteresisChart) {
    const option = hysteresisChart.getOption()
    if (option.animation !== false) {
      hysteresisChart.setOption({ animation: false })
    }
  }
}

// 组件挂载时初始化图表
onMounted(() => {
  nextTick(() => {
    if (smoothChartRef.value) {
      smoothChart = echarts.init(smoothChartRef.value)
      updateSmoothChart()
      
      // 启动性能监控
      smoothChartPerformance = monitorChartPerformance('smooth', smoothChart)
      
      // 添加数据缩放事件监听
      smoothChart.on('datazoom', handleDataZoom)
    }
    if (hysteresisChartRef.value) {
      hysteresisChart = echarts.init(hysteresisChartRef.value)
      updateHysteresisChart()
      
      // 启动性能监控
      hysteresisChartPerformance = monitorChartPerformance('hysteresis', hysteresisChart)
      
      // 添加数据缩放事件监听
      hysteresisChart.on('datazoom', handleDataZoom)
    }
    window.addEventListener('resize', handleResize)
    
    // 添加图表点击事件用于标注
    if (smoothChart) {
      smoothChart.on('click', handleChartClick)
    }
    if (hysteresisChart) {
      hysteresisChart.on('click', handleChartClick)
    }
    
    // 加载历史记录
    loadHistory()
    
    // 启动FPS监控
    startFpsMonitor()
    
    // 定期清理内存（每5分钟）
    setInterval(cleanupChartMemory, 5 * 60 * 1000)
  })
})

// 组件卸载时清理资源
onUnmounted(() => {
  // 停止性能监控
  if (smoothChartPerformance) {
    smoothChartPerformance.stop()
  }
  if (hysteresisChartPerformance) {
    hysteresisChartPerformance.stop()
  }
  
  // 停止FPS监控
  stopFpsMonitor()
  
  // 清理图表更新队列
  Object.values(chartUpdateQueue.value).forEach(queue => {
    if (queue.timer) {
      clearTimeout(queue.timer)
    }
  })
  
  // 清理图表实例
  if (smoothChart) {
    smoothChart.off('click')
    smoothChart.off('datazoom')
    smoothChart.dispose()
    smoothChart = null
  }
  if (hysteresisChart) {
    hysteresisChart.off('click')
    hysteresisChart.off('datazoom')
    hysteresisChart.dispose()
    hysteresisChart = null
  }
  
  // 清理内存
  cleanupChartMemory()
  
  window.removeEventListener('resize', handleResize)
  
  console.log('[DataAnalysis] 组件已卸载，资源已清理')
})
</script>

<style scoped>
.data-analysis {
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-4);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.annotation-panel {
  margin-bottom: var(--spacing-5);
  animation: slideDown var(--transition-base);
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-4);
}

.marks-display h4 {
  margin: 0 0 var(--spacing-2) 0;
  color: var(--color-primary-500);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-4);
}

.chart-tips {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
}

.result-display h4 {
  margin-top: 0;
  margin-bottom: var(--spacing-3);
  color: var(--color-primary-500);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
}

.optimization-info {
  margin-top: var(--spacing-3);
}

/* 图表卡片优化 */
:deep(.el-card) {
  background-color: var(--color-surface-primary);
  border-color: var(--color-border-primary);
  border-radius: var(--radius-lg);
  transition: var(--transition-all);
}

:deep(.el-card:hover) {
  box-shadow: var(--shadow-lg);
}

:deep(.el-card__header) {
  padding: var(--spacing-4) var(--spacing-5);
  border-bottom: 1px solid var(--color-border-primary);
  background-color: var(--color-bg-secondary);
}

:deep(.el-card__body) {
  padding: var(--spacing-5);
}

/* 标签页优化 */
:deep(.el-tabs--border-card) {
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background-color: var(--color-surface-primary);
}

:deep(.el-tabs__header) {
  background-color: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border-primary);
}

:deep(.el-tabs__item) {
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
  transition: var(--transition-fast);
  padding: 0 var(--spacing-5);
  height: 44px;
  line-height: 44px;
}

:deep(.el-tabs__item:hover) {
  color: var(--color-primary-500);
  background-color: var(--color-interactive-hover);
}

:deep(.el-tabs__item.is-active) {
  color: var(--color-primary-500);
  background-color: var(--color-surface-primary);
  border-right-color: var(--color-border-primary);
  border-left-color: var(--color-border-primary);
}

:deep(.el-tabs__content) {
  padding: var(--spacing-5);
}

/* 参数面板优化 */
:deep(.el-form-item__label) {
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

:deep(.el-form-item) {
  margin-bottom: var(--spacing-4);
}

/* 分割线优化 */
:deep(.el-divider) {
  border-color: var(--color-border-primary);
  margin: var(--spacing-4) 0;
}

/* 标签优化 */
:deep(.el-tag) {
  border-radius: var(--radius-base);
  font-weight: var(--font-weight-medium);
}

/* 警告框优化 */
:deep(.el-alert) {
  border-radius: var(--radius-md);
}

/* 描述列表优化 */
:deep(.el-descriptions) {
  border-radius: var(--radius-md);
  overflow: hidden;
}

:deep(.el-descriptions__label) {
  background-color: var(--color-bg-secondary);
  color: var(--color-text-secondary);
  font-weight: var(--font-weight-medium);
}

:deep(.el-descriptions__content) {
  font-family: var(--font-family-mono);
  color: var(--color-text-primary);
}

/* 响应式优化 */
@media (max-width: 768px) {
  :deep(.el-card__header),
  :deep(.el-card__body),
  :deep(.el-tabs__content) {
    padding: var(--spacing-3);
  }
  
  .card-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .header-actions {
    width: 100%;
    justify-content: flex-end;
  }
}

/* 报告内容样式 */
.report-content {
  padding: var(--spacing-4);
}

.report-header {
  text-align: center;
  margin-bottom: var(--spacing-4);
}

.report-header h3 {
  margin: 0 0 var(--spacing-2) 0;
  color: var(--color-primary-500);
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
}

.report-header p {
  margin: var(--spacing-1) 0;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
}

.report-section {
  margin-bottom: var(--spacing-5);
}

.report-section h4 {
  margin: 0 0 var(--spacing-3) 0;
  color: var(--color-primary-500);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  padding-bottom: var(--spacing-2);
  border-bottom: 2px solid var(--color-border-primary);
}

/* 历史记录工具栏 */
.history-toolbar {
  margin-bottom: var(--spacing-3);
  display: flex;
  justify-content: flex-end;
}

/* 模型详情样式 */
.model-detail {
  padding: var(--spacing-4);
}

.model-detail h4 {
  margin: var(--spacing-4) 0 var(--spacing-3) 0;
  color: var(--color-primary-500);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
}

/* 统计卡片样式 */
:deep(.el-statistic) {
  text-align: center;
  padding: var(--spacing-3);
  background-color: var(--color-bg-secondary);
  border-radius: var(--radius-md);
}

:deep(.el-statistic__head) {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-2);
}

:deep(.el-statistic__content) {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary-500);
}
</style>
