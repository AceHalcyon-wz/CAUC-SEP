<template>
  <el-card class="io-config-card">
    <template #header>
      <div class="card-header">
        <el-icon class="header-icon"><Setting /></el-icon>
        <span class="header-title">IO端口配置</span>
        <el-tag size="small" type="info">DM2C-RS556</el-tag>
      </div>
    </template>

    <div class="io-config-content">
      <el-tabs v-model="activeTab" class="io-tabs">
        <el-tab-pane label="数字输入(DI)" name="di">
          <div class="io-section">
            <div class="section-header">
              <span class="section-title">DI端口配置 (1-7)</span>
              <el-button size="small" @click="refreshDIStatus" :loading="loadingDI">
                <el-icon><Refresh /></el-icon>
                刷新状态
              </el-button>
            </div>

            <el-table :data="diPorts" stripe class="io-table">
              <el-table-column prop="port" label="端口" width="80" />
              <el-table-column label="功能配置" min-width="200">
                <template #default="{ row }">
                  <el-select
                    v-model="row.function"
                    placeholder="选择功能"
                    size="small"
                    @change="handleDIChange(row)"
                  >
                    <el-option-group label="常开模式">
                      <el-option
                        v-for="func in diFunctions"
                        :key="func.value"
                        :label="func.label"
                        :value="func.value"
                      />
                    </el-option-group>
                    <el-option-group label="常闭模式">
                      <el-option
                        v-for="func in diFunctions"
                        :key="func.value + 0x80"
                        :label="`${func.label} (常闭)`"
                        :value="func.value + 0x80"
                      />
                    </el-option-group>
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="当前状态" width="100">
                <template #default="{ row }">
                  <el-tag
                    :type="diStatus[`di${row.port}`] ? 'success' : 'info'"
                    size="small"
                  >
                    {{ diStatus[`di${row.port}`] ? '高电平' : '低电平' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button
                    type="primary"
                    size="small"
                    :loading="row.saving"
                    @click="saveDIConfig(row)"
                  >
                    应用
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <el-tab-pane label="数字输出(DO)" name="do">
          <div class="io-section">
            <div class="section-header">
              <span class="section-title">DO端口配置 (1-3)</span>
              <el-button size="small" @click="refreshDOStatus" :loading="loadingDO">
                <el-icon><Refresh /></el-icon>
                刷新状态
              </el-button>
            </div>

            <el-table :data="doPorts" stripe class="io-table">
              <el-table-column prop="port" label="端口" width="80" />
              <el-table-column label="功能配置" min-width="200">
                <template #default="{ row }">
                  <el-select
                    v-model="row.function"
                    placeholder="选择功能"
                    size="small"
                    @change="handleDOChange(row)"
                  >
                    <el-option-group label="常开模式">
                      <el-option
                        v-for="func in doFunctions"
                        :key="func.value"
                        :label="func.label"
                        :value="func.value"
                      />
                    </el-option-group>
                    <el-option-group label="常闭模式">
                      <el-option
                        v-for="func in doFunctions"
                        :key="func.value + 0x80"
                        :label="`${func.label} (常闭)`"
                        :value="func.value + 0x80"
                      />
                    </el-option-group>
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column label="当前状态" width="100">
                <template #default="{ row }">
                  <el-tag
                    :type="doStatus[`do${row.port}`] ? 'success' : 'info'"
                    size="small"
                  >
                    {{ doStatus[`do${row.port}`] ? '高电平' : '低电平' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button
                    type="primary"
                    size="small"
                    :loading="row.saving"
                    @click="saveDOConfig(row)"
                  >
                    应用
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>

      <el-divider />

      <div class="io-help">
        <el-alert
          title="IO配置说明"
          type="info"
          :closable="false"
        >
          <template #default>
            <ul class="help-list">
              <li><strong>常开模式</strong>：信号未触发时端口断开，触发时闭合</li>
              <li><strong>常闭模式</strong>：信号未触发时端口闭合，触发时断开</li>
              <li><strong>限位信号</strong>：建议配置为常闭模式，断线时触发保护</li>
              <li><strong>急停信号</strong>：必须配置为常闭模式，断线时触发急停</li>
            </ul>
          </template>
        </el-alert>
      </div>
    </div>
  </el-card>
</template>

<script setup>
/**
 * @file IOConfig.vue
 * @path src/components/
 * @description DM2C-RS556驱动器IO端口配置组件，支持DI/DO端口功能配置和状态监控
 * @author Agent
 * @date 2024-03-08
 */

import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { get, post } from '../utils/apiRequest'

const DEVICE_ID = 'stepper_01'

const activeTab = ref('di')

const loadingDI = ref(false)
const loadingDO = ref(false)

const diStatus = reactive({
  di1: false,
  di2: false,
  di3: false,
  di4: false,
  di5: false,
  di6: false,
  di7: false
})

const doStatus = reactive({
  do1: false,
  do2: false,
  do3: false
})

const diPorts = ref([
  { port: 1, function: 0, saving: false },
  { port: 2, function: 0, saving: false },
  { port: 3, function: 0, saving: false },
  { port: 4, function: 0, saving: false },
  { port: 5, function: 0, saving: false },
  { port: 6, function: 0, saving: false },
  { port: 7, function: 0, saving: false }
])

const doPorts = ref([
  { port: 1, function: 0, saving: false },
  { port: 2, function: 0, saving: false },
  { port: 3, function: 0, saving: false }
])

const diFunctions = [
  { value: 0x00, label: '无效输入' },
  { value: 0x07, label: '报警清除' },
  { value: 0x08, label: '使能' },
  { value: 0x20, label: '触发命令(CTRG)' },
  { value: 0x21, label: '回零触发(HOME)' },
  { value: 0x22, label: '强制急停(STP)' },
  { value: 0x23, label: '正向JOG(PJOG)' },
  { value: 0x24, label: '反向JOG(NJOG)' },
  { value: 0x25, label: '正向限位(POT)' },
  { value: 0x26, label: '反向限位(NOT)' },
  { value: 0x27, label: '原点信号(ORG)' },
  { value: 0x28, label: '路径地址0(ADDR0)' },
  { value: 0x29, label: '路径地址1(ADDR1)' },
  { value: 0x2A, label: '路径地址2(ADDR2)' },
  { value: 0x2B, label: '路径地址3(ADDR3)' },
  { value: 0x2C, label: 'JOG速度2' }
]

const doFunctions = [
  { value: 0x00, label: '无效输出' },
  { value: 0x20, label: '指令完成(CMD_OK)' },
  { value: 0x21, label: '路径完成(MC_OK)' },
  { value: 0x22, label: '回零完成(HOME_OK)' },
  { value: 0x23, label: '到位完成(INP)' },
  { value: 0x24, label: '抱闸输出(BRK)' },
  { value: 0x25, label: '报警输出(ALM)' }
]

function handleDIChange(row) {
  row.changed = true
}

function handleDOChange(row) {
  row.changed = true
}

async function saveDIConfig(row) {
  row.saving = true
  try {
    const result = await post(`/device/${DEVICE_ID}/io/di/configure`, {
      di_number: row.port,
      function: row.function
    })
    
    if (result.success && result.data?.success) {
      ElMessage.success(`DI${row.port}配置已应用`)
      row.changed = false
    } else {
      ElMessage.error(result.message || '配置失败')
    }
  } catch (error) {
    ElMessage.error(`配置失败: ${error.message}`)
  } finally {
    row.saving = false
  }
}

async function saveDOConfig(row) {
  row.saving = true
  try {
    const result = await post(`/device/${DEVICE_ID}/io/do/configure`, {
      do_number: row.port,
      function: row.function
    })
    
    if (result.success && result.data?.success) {
      ElMessage.success(`DO${row.port}配置已应用`)
      row.changed = false
    } else {
      ElMessage.error(result.message || '配置失败')
    }
  } catch (error) {
    ElMessage.error(`配置失败: ${error.message}`)
  } finally {
    row.saving = false
  }
}

async function refreshDIStatus() {
  loadingDI.value = true
  try {
    const result = await get(`/device/${DEVICE_ID}/io/di/status`)
    
    if (result.success && result.data) {
      Object.keys(diStatus).forEach(key => {
        diStatus[key] = result.data[key] || false
      })
    }
  } catch (error) {
    console.error('Failed to refresh DI status:', error)
  } finally {
    loadingDI.value = false
  }
}

async function refreshDOStatus() {
  loadingDO.value = true
  try {
    const result = await get(`/device/${DEVICE_ID}/io/do/status`)
    
    if (result.success && result.data) {
      Object.keys(doStatus).forEach(key => {
        doStatus[key] = result.data[key] || false
      })
    }
  } catch (error) {
    console.error('Failed to refresh DO status:', error)
  } finally {
    loadingDO.value = false
  }
}

async function loadDIConfigs() {
  for (const port of diPorts.value) {
    try {
      const result = await get(`/device/${DEVICE_ID}/io/di/${port.port}/config`)
      if (result.success && result.data?.success) {
        port.function = result.data.function
      }
    } catch (error) {
      console.error(`Failed to load DI${port.port} config:`, error)
    }
  }
}

async function loadDOConfigs() {
  for (const port of doPorts.value) {
    try {
      const result = await get(`/device/${DEVICE_ID}/io/do/${port.port}/config`)
      if (result.success && result.data?.success) {
        port.function = result.data.function
      }
    } catch (error) {
      console.error(`Failed to load DO${port.port} config:`, error)
    }
  }
}

onMounted(() => {
  loadDIConfigs()
  loadDOConfigs()
  refreshDIStatus()
  refreshDOStatus()
})
</script>

<style scoped lang="scss">
.io-config-card {
  margin-bottom: var(--spacing-6);
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.header-icon {
  font-size: var(--font-size-lg);
  color: var(--color-primary-500);
}

.header-title {
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  flex: 1;
}

.io-config-content {
  padding: var(--spacing-2) 0;
}

.io-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: var(--spacing-4);
  }
}

.io-section {
  padding: var(--spacing-2) 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-4);
}

.section-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
}

.io-table {
  width: 100%;
}

.io-help {
  margin-top: var(--spacing-4);
}

.help-list {
  margin: var(--spacing-2) 0;
  padding-left: var(--spacing-5);
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm);
  line-height: 1.8;
}

.help-list li {
  margin-bottom: var(--spacing-1);
}

.help-list strong {
  color: var(--color-text-primary);
}

@media (max-width: 768px) {
  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-2);
  }
  
  .io-table {
    :deep(.el-table__body-wrapper) {
      overflow-x: auto;
    }
  }
}
</style>
