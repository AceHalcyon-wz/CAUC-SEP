/**
 * @file design-system-examples.vue
 * @path src/components/
 * @description CAUC-SEP 设计系统使用示例组件
 * @author Agent
 * @date 2026-03-08
 */

<template>
  <div class="design-system-examples">
    <!-- 色彩系统示例 -->
    <section class="example-section">
      <h2 class="section-title">
        色彩系统
      </h2>
      
      <!-- 主色 -->
      <div class="color-group">
        <h3 class="group-title">
          主色（Primary）
        </h3>
        <div class="color-swatches">
          <div 
            v-for="level in [50, 100, 200, 300, 400, 500, 600, 700, 800, 900]" 
            :key="level"
            class="color-swatch"
            :style="{ backgroundColor: `var(--color-primary-${level})` }"
          >
            <span :class="{ 'light-text': level < 400 }">{{ level }}</span>
          </div>
        </div>
      </div>
      
      <!-- 辅助色 -->
      <div class="color-group">
        <h3 class="group-title">
          辅助色（Secondary）
        </h3>
        <div class="color-swatches">
          <div 
            v-for="level in [50, 100, 200, 300, 400, 500, 600, 700, 800, 900]" 
            :key="level"
            class="color-swatch"
            :style="{ backgroundColor: `var(--color-secondary-${level})` }"
          >
            <span :class="{ 'light-text': level < 400 }">{{ level }}</span>
          </div>
        </div>
      </div>
      
      <!-- 功能色 -->
      <div class="color-group">
        <h3 class="group-title">
          功能色
        </h3>
        <div class="color-swatches">
          <div
            class="color-swatch"
            style="background-color: var(--color-success)"
          >
            <span class="light-text">成功</span>
          </div>
          <div
            class="color-swatch"
            style="background-color: var(--color-warning)"
          >
            <span>警告</span>
          </div>
          <div
            class="color-swatch"
            style="background-color: var(--color-error)"
          >
            <span class="light-text">错误</span>
          </div>
          <div
            class="color-swatch"
            style="background-color: var(--color-info)"
          >
            <span class="light-text">信息</span>
          </div>
        </div>
      </div>
    </section>
    
    <!-- 间距系统示例 -->
    <section class="example-section">
      <h2 class="section-title">
        间距系统
      </h2>
      <div class="spacing-examples">
        <div 
          v-for="level in [1, 2, 3, 4, 5, 6, 8, 10, 12]" 
          :key="level"
          class="spacing-item"
        >
          <div class="spacing-label">
            spacing-{{ level }}
          </div>
          <div 
            class="spacing-box"
            :style="{ width: `var(--spacing-${level})`, height: `var(--spacing-${level})` }"
          />
          <div class="spacing-value">
            {{ getSpacingValue(level) }}
          </div>
        </div>
      </div>
    </section>
    
    <!-- 圆角系统示例 -->
    <section class="example-section">
      <h2 class="section-title">
        圆角系统
      </h2>
      <div class="radius-examples">
        <div 
          v-for="size in ['xs', 'sm', 'base', 'md', 'lg', 'xl', '2xl', 'full']" 
          :key="size"
          class="radius-item"
          :style="{ borderRadius: `var(--radius-${size})` }"
        >
          <span>radius-{{ size }}</span>
        </div>
      </div>
    </section>
    
    <!-- 阴影系统示例 -->
    <section class="example-section">
      <h2 class="section-title">
        阴影系统
      </h2>
      <div class="shadow-examples">
        <div 
          v-for="size in ['sm', 'md', 'lg', 'xl']" 
          :key="size"
          class="shadow-item"
          :style="{ boxShadow: `var(--shadow-${size})` }"
        >
          <span>shadow-{{ size }}</span>
        </div>
      </div>
    </section>
    
    <!-- 字体系统示例 -->
    <section class="example-section">
      <h2 class="section-title">
        字体系统
      </h2>
      
      <div class="font-examples">
        <h3 class="group-title">
          字体大小
        </h3>
        <div 
          v-for="size in ['xs', 'sm', 'base', 'lg', 'xl', '2xl', '3xl', '4xl', '5xl']" 
          :key="size"
          class="font-size-item"
          :style="{ fontSize: `var(--font-size-${size})` }"
        >
          font-size-{{ size }} - 自旋电子器件实验平台
        </div>
      </div>
      
      <div class="font-examples">
        <h3 class="group-title">
          字重
        </h3>
        <div 
          v-for="weight in ['light', 'normal', 'medium', 'semibold', 'bold']" 
          :key="weight"
          class="font-weight-item"
          :style="{ fontWeight: `var(--font-weight-${weight})` }"
        >
          font-weight-{{ weight }} - CAUC-SEP 实验平台
        </div>
      </div>
      
      <div class="font-examples">
        <h3 class="group-title">
          字体族
        </h3>
        <div
          class="font-family-item"
          style="font-family: var(--font-family-chinese)"
        >
          中文字体：自旋电子器件实验平台
        </div>
        <div
          class="font-family-item"
          style="font-family: var(--font-family-english)"
        >
          English Font: Spintronic Device Platform
        </div>
        <div
          class="font-family-item"
          style="font-family: var(--font-family-mono)"
        >
          Mono Font: 12345.67890
        </div>
      </div>
    </section>
    
    <!-- 动画过渡示例 -->
    <section class="example-section">
      <h2 class="section-title">
        动画过渡
      </h2>
      
      <div class="transition-examples">
        <div class="transition-item">
          <div class="transition-label">
            transition-fast (150ms)
          </div>
          <div
            class="transition-box"
            style="transition: all var(--transition-fast)"
          />
        </div>
        <div class="transition-item">
          <div class="transition-label">
            transition-base (200ms)
          </div>
          <div
            class="transition-box"
            style="transition: all var(--transition-base)"
          />
        </div>
        <div class="transition-item">
          <div class="transition-label">
            transition-slow (300ms)
          </div>
          <div
            class="transition-box"
            style="transition: all var(--transition-slow)"
          />
        </div>
      </div>
    </section>
    
    <!-- 状态指示器示例 -->
    <section class="example-section">
      <h2 class="section-title">
        状态指示器
      </h2>
      
      <div class="status-examples">
        <div class="status-item status-online">
          在线
        </div>
        <div class="status-item status-offline">
          离线
        </div>
        <div class="status-item status-warning">
          警告
        </div>
        <div class="status-item status-error">
          错误
        </div>
        <div class="status-item status-measuring">
          测量中
        </div>
        <div class="status-item status-standby">
          待机
        </div>
      </div>
    </section>
    
    <!-- 数值显示示例 -->
    <section class="example-section">
      <h2 class="section-title">
        数值显示
      </h2>
      
      <div class="numeric-examples">
        <div class="numeric-item">
          <div class="numeric-label">
            小号数值
          </div>
          <div class="numeric-display numeric-display--small">
            1234.56
          </div>
        </div>
        <div class="numeric-item">
          <div class="numeric-label">
            标准数值
          </div>
          <div class="numeric-display">
            7890.12
          </div>
        </div>
        <div class="numeric-item">
          <div class="numeric-label">
            大号数值
          </div>
          <div class="numeric-display numeric-display--large">
            3456.78
          </div>
        </div>
      </div>
    </section>
    
    <!-- 按钮示例 -->
    <section class="example-section">
      <h2 class="section-title">
        按钮样式
      </h2>
      
      <div class="button-examples">
        <el-button type="primary">
          主按钮
        </el-button>
        <el-button type="success">
          成功按钮
        </el-button>
        <el-button type="warning">
          警告按钮
        </el-button>
        <el-button type="danger">
          危险按钮
        </el-button>
        <el-button type="info">
          信息按钮
        </el-button>
      </div>
      
      <div class="button-examples">
        <el-button>默认按钮</el-button>
        <el-button
          type="primary"
          plain
        >
          朴素按钮
        </el-button>
        <el-button
          type="primary"
          round
        >
          圆角按钮
        </el-button>
        <el-button
          type="primary"
          circle
          :icon="Plus"
        />
      </div>
    </section>
    
    <!-- 卡片示例 -->
    <section class="example-section">
      <h2 class="section-title">
        卡片样式
      </h2>
      
      <div class="card-examples">
        <el-card class="example-card">
          <template #header>
            <div class="card-header">
              <span>标准卡片</span>
              <el-button
                type="primary"
                size="small"
              >
                操作
              </el-button>
            </div>
          </template>
          <div class="card-content">
            这是一个标准卡片示例，使用了设计系统的颜色、间距、圆角和阴影变量。
          </div>
        </el-card>
        
        <div class="data-panel">
          <div class="panel-header">
            数据面板
          </div>
          <div class="panel-content">
            <div class="data-row">
              <span class="param-label">温度</span>
              <span class="param-value">25.6<span class="unit">°C</span></span>
            </div>
            <div class="data-row">
              <span class="param-label">磁场强度</span>
              <span class="param-value">1.23<span class="unit">T</span></span>
            </div>
            <div class="data-row">
              <span class="param-label">电压</span>
              <span class="param-value">3.45<span class="unit">V</span></span>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { Plus } from '@element-plus/icons-vue';

/**
 * 获取间距值
 */
function getSpacingValue(level) {
  const values = {
    1: '4px',
    2: '8px',
    3: '12px',
    4: '16px',
    5: '20px',
    6: '24px',
    8: '32px',
    10: '40px',
    12: '48px'
  };
  return values[level] || '';
}
</script>

<style scoped lang="scss">
.design-system-examples {
  max-width: var(--content-max-width);
  margin: 0 auto;
  padding: var(--spacing-6);
}

.example-section {
  margin-bottom: var(--spacing-8);
  padding: var(--spacing-6);
  background-color: var(--color-surface-primary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-lg);
}

.section-title {
  margin: 0 0 var(--spacing-6) 0;
  padding-bottom: var(--spacing-4);
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  border-bottom: 2px solid var(--color-primary-500);
}

.group-title {
  margin: 0 0 var(--spacing-4) 0;
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-secondary);
}

// 色彩系统
.color-group {
  margin-bottom: var(--spacing-6);
}

.color-swatches {
  display: flex;
  gap: var(--spacing-2);
  flex-wrap: wrap;
}

.color-swatch {
  width: 80px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  color: #ffffff;
  
  &.light-text {
    color: var(--color-text-primary);
  }
}

// 间距系统
.spacing-examples {
  display: flex;
  gap: var(--spacing-4);
  flex-wrap: wrap;
}

.spacing-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-2);
}

.spacing-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.spacing-box {
  background-color: var(--color-primary-500);
  border-radius: var(--radius-sm);
}

.spacing-value {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  font-family: var(--font-family-mono);
}

// 圆角系统
.radius-examples {
  display: flex;
  gap: var(--spacing-4);
  flex-wrap: wrap;
}

.radius-item {
  width: 100px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-primary-100);
  color: var(--color-primary-700);
  font-size: var(--font-size-sm);
  border: 2px solid var(--color-primary-300);
}

// 阴影系统
.shadow-examples {
  display: flex;
  gap: var(--spacing-6);
  flex-wrap: wrap;
}

.shadow-item {
  width: 120px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-surface-primary);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

// 字体系统
.font-examples {
  margin-bottom: var(--spacing-6);
}

.font-size-item,
.font-weight-item,
.font-family-item {
  padding: var(--spacing-2) 0;
  color: var(--color-text-primary);
  border-bottom: 1px solid var(--color-border-secondary);
}

// 动画过渡
.transition-examples {
  display: flex;
  gap: var(--spacing-6);
}

.transition-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-2);
}

.transition-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.transition-box {
  width: 60px;
  height: 60px;
  background-color: var(--color-primary-500);
  border-radius: var(--radius-md);
  
  &:hover {
    transform: scale(1.2);
    background-color: var(--color-primary-400);
  }
}

// 状态指示器
.status-examples {
  display: flex;
  gap: var(--spacing-4);
  flex-wrap: wrap;
}

.status-item {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: var(--spacing-2) var(--spacing-4);
  border-radius: var(--radius-full);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  
  &::before {
    content: '';
    width: 8px;
    height: 8px;
    border-radius: var(--radius-full);
  }
  
  &.status-online {
    background-color: rgba(82, 196, 26, 0.1);
    color: var(--color-success);
    
    &::before {
      background-color: var(--color-success);
      box-shadow: 0 0 8px var(--color-success);
      animation: pulse 2s ease-in-out infinite;
    }
  }
  
  &.status-offline {
    background-color: rgba(140, 140, 140, 0.1);
    color: var(--color-neutral-500);
    
    &::before {
      background-color: var(--color-neutral-500);
    }
  }
  
  &.status-warning {
    background-color: rgba(250, 173, 20, 0.1);
    color: var(--color-warning);
    
    &::before {
      background-color: var(--color-warning);
      box-shadow: 0 0 8px var(--color-warning);
      animation: pulse 2s ease-in-out infinite;
    }
  }
  
  &.status-error {
    background-color: rgba(255, 77, 79, 0.1);
    color: var(--color-error);
    
    &::before {
      background-color: var(--color-error);
      box-shadow: 0 0 8px var(--color-error);
      animation: pulse 1s ease-in-out infinite;
    }
  }
  
  &.status-measuring {
    background-color: rgba(24, 144, 255, 0.1);
    color: var(--color-primary-500);
    
    &::before {
      background-color: var(--color-primary-500);
      box-shadow: 0 0 8px var(--color-primary-500);
      animation: pulse 1s ease-in-out infinite;
    }
  }
  
  &.status-standby {
    background-color: rgba(114, 46, 209, 0.1);
    color: #722ed1;
    
    &::before {
      background-color: #722ed1;
    }
  }
}

// 数值显示
.numeric-examples {
  display: flex;
  gap: var(--spacing-6);
}

.numeric-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
  padding: var(--spacing-4);
  background-color: var(--color-bg-tertiary);
  border-radius: var(--radius-md);
}

.numeric-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.numeric-display {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  letter-spacing: 0.05em;
  
  &.numeric-display--small {
    font-size: var(--font-size-lg);
  }
  
  &.numeric-display--large {
    font-size: var(--font-size-3xl);
  }
}

// 按钮示例
.button-examples {
  display: flex;
  gap: var(--spacing-3);
  margin-bottom: var(--spacing-4);
  flex-wrap: wrap;
}

// 卡片示例
.card-examples {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--spacing-4);
}

.example-card {
  border-radius: var(--radius-lg);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-content {
  color: var(--color-text-secondary);
  line-height: var(--line-height-relaxed);
}

.data-panel {
  background-color: var(--color-surface-primary);
  border: 1px solid var(--color-border-primary);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.panel-header {
  padding: var(--spacing-4);
  background-color: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border-primary);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
}

.panel-content {
  padding: var(--spacing-4);
}

.data-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-2) 0;
  border-bottom: 1px solid var(--color-border-secondary);
  
  &:last-child {
    border-bottom: none;
  }
}

.param-label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.param-value {
  font-family: var(--font-family-mono);
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
}

.unit {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
  margin-left: var(--spacing-1);
}

// 动画
@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(1.1);
  }
}
</style>
