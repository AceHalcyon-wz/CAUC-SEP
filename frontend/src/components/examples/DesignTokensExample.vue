/**
 * @file DesignTokensExample.vue
 * @path src/components/
 * @description 设计令牌使用示例 - 展示如何在组件中使用设计系统
 * @author Agent
 * @date 2024-03-07
 */

<script setup>
import { ref } from 'vue'

const measurementData = ref({
  voltage: 3.14159,
  current: 0.0025,
  resistance: 1256.64,
  temperature: 298.15,
  status: 'measuring'
})
</script>

<template>
  <div class="example-container">
    <!-- 标题区域 -->
    <header class="example-header">
      <h1 class="title">
        设计令牌示例
      </h1>
    </header>

    <!-- 数据面板示例 -->
    <section class="data-section">
      <h2 class="section-title">
        数据面板
      </h2>
      
      <div class="data-grid">
        <!-- 数值显示 -->
        <div class="data-panel">
          <div class="param-label">
            电压 (V)
          </div>
          <div class="numeric-display">
            {{ measurementData.voltage.toFixed(3) }}
            <span class="unit">V</span>
          </div>
        </div>

        <div class="data-panel">
          <div class="param-label">
            电流 (A)
          </div>
          <div class="numeric-display numeric-display--small">
            {{ measurementData.current.toFixed(4) }}
            <span class="unit">A</span>
          </div>
        </div>

        <div class="data-panel">
          <div class="param-label">
            电阻 (Ω)
          </div>
          <div class="numeric-display">
            {{ measurementData.resistance.toFixed(2) }}
            <span class="unit">Ω</span>
          </div>
        </div>

        <div class="data-panel">
          <div class="param-label">
            温度 (K)
          </div>
          <div class="numeric-display numeric-display--large">
            {{ measurementData.temperature.toFixed(2) }}
            <span class="unit">K</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 状态指示器示例 -->
    <section class="status-section">
      <h2 class="section-title">
        状态指示器
      </h2>
      
      <div class="status-grid">
        <div class="status-item">
          <span class="status-indicator status-indicator--online">
            在线
          </span>
        </div>
        <div class="status-item">
          <span class="status-indicator status-indicator--offline">
            离线
          </span>
        </div>
        <div class="status-item">
          <span class="status-indicator status-indicator--warning">
            警告
          </span>
        </div>
        <div class="status-item">
          <span class="status-indicator status-indicator--error">
            错误
          </span>
        </div>
        <div class="status-item">
          <span class="status-indicator status-indicator--measuring">
            测量中
          </span>
        </div>
      </div>
    </section>

    <!-- 颜色系统示例 -->
    <section class="colors-section">
      <h2 class="section-title">
        颜色系统
      </h2>
      
      <div class="color-group">
        <h3 class="group-title">
          主色系
        </h3>
        <div class="color-swatches">
          <div
            class="swatch"
            style="background: var(--color-primary-500)"
          >
            <span class="swatch-label">Primary 500</span>
          </div>
          <div
            class="swatch"
            style="background: var(--color-primary-600)"
          >
            <span class="swatch-label">Primary 600</span>
          </div>
          <div
            class="swatch"
            style="background: var(--color-accent-500)"
          >
            <span class="swatch-label">Accent 500</span>
          </div>
          <div
            class="swatch"
            style="background: var(--color-accent-600)"
          >
            <span class="swatch-label">Accent 600</span>
          </div>
        </div>
      </div>

      <div class="color-group">
        <h3 class="group-title">
          数据色
        </h3>
        <div class="color-swatches">
          <div
            class="swatch"
            style="background: var(--color-data-blue)"
          >
            <span class="swatch-label">Blue</span>
          </div>
          <div
            class="swatch"
            style="background: var(--color-data-cyan)"
          >
            <span class="swatch-label">Cyan</span>
          </div>
          <div
            class="swatch"
            style="background: var(--color-data-green)"
          >
            <span class="swatch-label">Green</span>
          </div>
          <div
            class="swatch"
            style="background: var(--color-data-yellow)"
          >
            <span class="swatch-label">Yellow</span>
          </div>
          <div
            class="swatch"
            style="background: var(--color-data-orange)"
          >
            <span class="swatch-label">Orange</span>
          </div>
          <div
            class="swatch"
            style="background: var(--color-data-red)"
          >
            <span class="swatch-label">Red</span>
          </div>
          <div
            class="swatch"
            style="background: var(--color-data-purple)"
          >
            <span class="swatch-label">Purple</span>
          </div>
          <div
            class="swatch"
            style="background: var(--color-data-pink)"
          >
            <span class="swatch-label">Pink</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 间距系统示例 -->
    <section class="spacing-section">
      <h2 class="section-title">
        间距系统
      </h2>
      
      <div class="spacing-demo">
        <div
          class="spacing-item"
          style="width: var(--spacing-1); height: var(--spacing-1)"
        >
          <span>4px</span>
        </div>
        <div
          class="spacing-item"
          style="width: var(--spacing-2); height: var(--spacing-2)"
        >
          <span>8px</span>
        </div>
        <div
          class="spacing-item"
          style="width: var(--spacing-4); height: var(--spacing-4)"
        >
          <span>16px</span>
        </div>
        <div
          class="spacing-item"
          style="width: var(--spacing-6); height: var(--spacing-6)"
        >
          <span>24px</span>
        </div>
        <div
          class="spacing-item"
          style="width: var(--spacing-8); height: var(--spacing-8)"
        >
          <span>32px</span>
        </div>
      </div>
    </section>

    <!-- 发光效果示例 -->
    <section class="glow-section">
      <h2 class="section-title">
        发光效果
      </h2>
      
      <div class="glow-grid">
        <div class="glow-box glow-primary">
          Primary Glow
        </div>
        <div class="glow-box glow-accent">
          Accent Glow
        </div>
        <div class="glow-box glow-success">
          Success Glow
        </div>
        <div class="glow-box glow-warning">
          Warning Glow
        </div>
        <div class="glow-box glow-error">
          Error Glow
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.example-container {
  padding: var(--spacing-6);
  max-width: 1200px;
  margin: 0 auto;
}

.example-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-8);
  padding-bottom: var(--spacing-4);
  border-bottom: 1px solid var(--color-border-primary);
}

.title {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
}

.section-title {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-4);
}

.data-section,
.status-section,
.colors-section,
.spacing-section,
.glow-section {
  margin-bottom: var(--spacing-8);
}

.data-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--spacing-4);
}

.status-grid {
  display: flex;
  gap: var(--spacing-4);
  flex-wrap: wrap;
}

.status-item {
  padding: var(--spacing-3);
  background-color: var(--color-surface-secondary);
  border-radius: var(--radius-md);
}

.color-group {
  margin-bottom: var(--spacing-6);
}

.group-title {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-3);
}

.color-swatches {
  display: flex;
  gap: var(--spacing-3);
  flex-wrap: wrap;
}

.swatch {
  width: 80px;
  height: 80px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding-bottom: var(--spacing-2);
  box-shadow: var(--shadow-md);
}

.swatch-label {
  font-size: var(--font-size-xs);
  color: white;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
}

.spacing-demo {
  display: flex;
  align-items: flex-end;
  gap: var(--spacing-4);
  padding: var(--spacing-4);
  background-color: var(--color-surface-secondary);
  border-radius: var(--radius-md);
}

.spacing-item {
  background-color: var(--color-primary-500);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
}

.spacing-item span {
  font-size: var(--font-size-xs);
  color: white;
  white-space: nowrap;
}

.glow-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--spacing-4);
}

.glow-box {
  padding: var(--spacing-4);
  background-color: var(--color-surface-primary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-md);
  text-align: center;
  font-weight: var(--font-weight-medium);
  color: var(--color-text-primary);
  transition: var(--transition-all);
}

.info-card {
  padding: var(--spacing-4);
  background-color: var(--color-surface-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-primary);
}

.info-card p {
  margin-bottom: var(--spacing-2);
  color: var(--color-text-secondary);
}

.info-card p:last-child {
  margin-bottom: 0;
}
</style>
