/**
 * @file About.vue
 * @path src/views/settings/
 * @description 关于页面 - 显示系统信息和版本详情
 * @author Agent
 * @date 2024-03-15
 * @version 3.5.1
 */

<script setup>
import { ref, onMounted } from 'vue';
import {
  ExperimentOutlined,
  MailOutlined,
  GlobalOutlined,
  CodeOutlined,
  BugOutlined,
  FileTextOutlined,
  TeamOutlined
} from '@ant-design/icons-vue';

/**
 * 系统信息
 */
const systemInfo = ref({
  version: '3.5.1',
  buildDate: '2024-03-15',
  vueVersion: '3.4.0',
  nodeVersion: '20.11.0',
  backendVersion: '3.5.0'
});

/**
 * 技术栈列表
 */
const techStack = [
  { name: 'Vue 3', description: '渐进式JavaScript框架', version: '3.4.0' },
  { name: 'Vite', description: '下一代前端构建工具', version: '5.0.0' },
  { name: 'Ant Design Vue', description: '企业级UI组件库', version: '4.0.0' },
  { name: 'Pinia', description: 'Vue官方状态管理库', version: '2.1.0' },
  { name: 'Vue Router', description: 'Vue官方路由管理器', version: '4.2.0' },
  { name: 'Axios', description: 'HTTP客户端', version: '1.6.0' },
  { name: 'ECharts', description: '数据可视化库', version: '5.4.0' },
  { name: 'WebSocket', description: '实时通信协议', version: '原生支持' }
];

/**
 * 功能特性列表
 */
const features = [
  { icon: ExperimentOutlined, title: '多设备支持', description: '支持电机、电磁铁、温控、压电陶瓷、微电流计等多种实验设备' },
  { icon: CodeOutlined, title: '实时数据', description: 'WebSocket实时推送实验数据，支持历史数据查询与分析' },
  { icon: BugOutlined, title: '故障诊断', description: '智能故障诊断系统，快速定位设备问题' },
  { icon: FileTextOutlined, title: '审计日志', description: '完整的操作审计日志，支持导出和查询' },
  { icon: TeamOutlined, title: '多用户支持', description: '支持多用户权限管理，满足不同角色需求' }
];

/**
 * 更新日志
 */
const changelog = [
  { version: 'v3.5.1', date: '2024-03-15', changes: ['UI/UX全面优化', '修复折叠按钮位置', '移除暗黑模式', '仅保留中文语言'] },
  { version: 'v3.5.0', date: '2024-03-07', changes: ['UI/UX全面升级', '新增设计系统', '完善WebSocket支持', '优化设备管理'] },
  { version: 'v3.0.0', date: '2024-01-15', changes: ['系统架构重构', '引入Pinia状态管理', '优化性能'] },
  { version: 'v2.0.0', date: '2023-11-20', changes: ['支持多设备类型', '新增数据分析模块'] },
  { version: 'v1.0.0', date: '2023-09-01', changes: ['初始版本发布', '基础实验控制功能'] }
];

onMounted(() => {
  // 获取系统信息
  systemInfo.value.vueVersion = window.Vue?.version || '3.4.0';
});
</script>

<template>
  <div class="about-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">
        关于系统
      </h1>
      <p class="page-subtitle">
        CAUC-SEP 科学实验平台版本信息与系统详情
      </p>
    </div>

    <!-- 系统概览卡片 -->
    <a-card
      class="overview-card"
      :bordered="false"
    >
      <div class="overview-content">
        <div class="logo-section">
          <div class="logo-icon">
            <ExperimentOutlined />
          </div>
          <div class="logo-text">
            <h2>CAUC-SEP</h2>
            <p>科学实验平台</p>
          </div>
        </div>
        <div class="version-section">
          <div class="version-item">
            <span class="version-label">前端版本</span>
            <span class="version-value">{{ systemInfo.version }}</span>
          </div>
          <div class="version-item">
            <span class="version-label">后端版本</span>
            <span class="version-value">{{ systemInfo.backendVersion }}</span>
          </div>
          <div class="version-item">
            <span class="version-label">构建日期</span>
            <span class="version-value">{{ systemInfo.buildDate }}</span>
          </div>
        </div>
      </div>
    </a-card>

    <!-- 功能特性 -->
    <a-row
      :gutter="[16, 16]"
      class="features-section"
    >
      <a-col
        v-for="(feature, index) in features"
        :key="index"
        :xs="24"
        :sm="12"
        :lg="8"
      >
        <a-card
          class="feature-card"
          :bordered="false"
        >
          <div class="feature-icon">
            <component :is="feature.icon" />
          </div>
          <h3 class="feature-title">
            {{ feature.title }}
          </h3>
          <p class="feature-description">
            {{ feature.description }}
          </p>
        </a-card>
      </a-col>
    </a-row>

    <!-- 技术栈 -->
    <a-card
      title="技术栈"
      class="tech-card"
      :bordered="false"
    >
      <a-row :gutter="[16, 16]">
        <a-col
          v-for="(tech, index) in techStack"
          :key="index"
          :xs="12"
          :sm="8"
          :md="6"
        >
          <div class="tech-item">
            <span class="tech-name">{{ tech.name }}</span>
            <span class="tech-version">{{ tech.version }}</span>
            <p class="tech-description">
              {{ tech.description }}
            </p>
          </div>
        </a-col>
      </a-row>
    </a-card>

    <!-- 更新日志 -->
    <a-card
      title="更新日志"
      class="changelog-card"
      :bordered="false"
    >
      <a-timeline mode="left">
        <a-timeline-item
          v-for="(log, index) in changelog"
          :key="index"
        >
          <template #label>
            <span class="changelog-date">{{ log.date }}</span>
          </template>
          <div class="changelog-content">
            <h4 class="changelog-version">
              {{ log.version }}
            </h4>
            <ul class="changelog-list">
              <li
                v-for="(change, cIndex) in log.changes"
                :key="cIndex"
              >
                {{ change }}
              </li>
            </ul>
          </div>
        </a-timeline-item>
      </a-timeline>
    </a-card>

    <!-- 联系信息 -->
    <a-card
      title="联系我们"
      class="contact-card"
      :bordered="false"
    >
      <a-row :gutter="[16, 16]">
        <a-col
          :xs="24"
          :sm="12"
        >
          <div class="contact-item">
            <GlobalOutlined class="contact-icon" />
            <div class="contact-info">
              <span class="contact-label">所属单位</span>
              <span class="contact-value">中国民航大学 理学院 材料物理</span>
            </div>
          </div>
        </a-col>
        <a-col
          :xs="24"
          :sm="12"
        >
          <div class="contact-item">
            <MailOutlined class="contact-icon" />
            <div class="contact-info">
              <span class="contact-label">联系邮箱</span>
              <span class="contact-value">cauc-sep@example.com</span>
            </div>
          </div>
        </a-col>
      </a-row>
    </a-card>

    <!-- 版权信息 -->
    <div class="copyright-section">
      <p>© 2024 中国民航大学 理学院 材料物理. All rights reserved.</p>
      <p>CAUC-SEP 科学实验平台 v{{ systemInfo.version }}</p>
    </div>
  </div>
</template>

<style scoped>
.about-page {
  padding: var(--spacing-6);
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: var(--spacing-6);
}

.page-title {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-2);
}

.page-subtitle {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
}

/* 概览卡片 */
.overview-card {
  margin-bottom: var(--spacing-6);
  background: linear-gradient(135deg, var(--color-primary-500) 0%, var(--color-primary-600) 100%);
  border-radius: var(--radius-xl);
}

.overview-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-4);
  color: white;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
}

.logo-icon {
  width: 64px;
  height: 64px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: var(--radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  backdrop-filter: blur(10px);
}

.logo-text h2 {
  font-size: var(--font-size-2xl);
  font-weight: var(--font-weight-bold);
  margin: 0;
}

.logo-text p {
  font-size: var(--font-size-base);
  opacity: 0.9;
  margin: var(--spacing-1) 0 0 0;
}

.version-section {
  display: flex;
  gap: var(--spacing-6);
}

.version-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-1);
}

.version-label {
  font-size: var(--font-size-sm);
  opacity: 0.8;
}

.version-value {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
}

/* 功能特性 */
.features-section {
  margin-bottom: var(--spacing-6);
}

.feature-card {
  text-align: center;
  padding: var(--spacing-4);
  height: 100%;
  transition: all var(--transition-fast);
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.feature-icon {
  width: 56px;
  height: 56px;
  background: var(--color-primary-50);
  border-radius: var(--radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto var(--spacing-4);
  font-size: 28px;
  color: var(--color-primary-500);
}

.feature-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-2);
}

.feature-description {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: var(--line-height-relaxed);
}

/* 技术栈 */
.tech-card {
  margin-bottom: var(--spacing-6);
}

.tech-item {
  padding: var(--spacing-3);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  text-align: center;
  transition: all var(--transition-fast);
}

.tech-item:hover {
  background: var(--color-primary-50);
  transform: translateY(-2px);
}

.tech-name {
  display: block;
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-1);
}

.tech-version {
  display: block;
  font-size: var(--font-size-xs);
  color: var(--color-primary-500);
  font-weight: var(--font-weight-medium);
  margin-bottom: var(--spacing-1);
}

.tech-description {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
  margin: 0;
}

/* 更新日志 */
.changelog-card {
  margin-bottom: var(--spacing-6);
}

.changelog-date {
  font-size: var(--font-size-sm);
  color: var(--color-text-tertiary);
}

.changelog-content {
  padding-left: var(--spacing-4);
}

.changelog-version {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-primary-500);
  margin-bottom: var(--spacing-2);
}

.changelog-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.changelog-list li {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  padding: var(--spacing-1) 0;
  position: relative;
  padding-left: var(--spacing-4);
}

.changelog-list li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 6px;
  height: 6px;
  background: var(--color-primary-500);
  border-radius: 50%;
}

/* 联系信息 */
.contact-card {
  margin-bottom: var(--spacing-6);
}

.contact-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-3);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
}

.contact-icon {
  font-size: 24px;
  color: var(--color-primary-500);
}

.contact-info {
  display: flex;
  flex-direction: column;
}

.contact-label {
  font-size: var(--font-size-xs);
  color: var(--color-text-tertiary);
}

.contact-value {
  font-size: var(--font-size-sm);
  color: var(--color-text-primary);
  font-weight: var(--font-weight-medium);
}

/* 版权信息 */
.copyright-section {
  text-align: center;
  padding: var(--spacing-6);
  color: var(--color-text-tertiary);
  font-size: var(--font-size-sm);
}

.copyright-section p {
  margin: var(--spacing-1) 0;
}

/* 响应式 */
@media (max-width: 768px) {
  .about-page {
    padding: var(--spacing-4);
  }

  .overview-content {
    flex-direction: column;
    gap: var(--spacing-4);
    text-align: center;
  }

  .version-section {
    flex-wrap: wrap;
    justify-content: center;
  }

  .page-title {
    font-size: var(--font-size-xl);
  }
}
</style>
