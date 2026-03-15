/**
 * @file Login.vue
 * @path src/views/
 * @description 登录页面组件 - 支持快速登录、传统登录和访客模式
 * @author Agent
 * @date 2024-03-15
 * @version 4.0.0
 */

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  UserOutlined,
  TeamOutlined,
  SafetyOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  EyeOutlined
} from '@ant-design/icons-vue'
import { useUserStore } from '../stores/user'
import {
  PRESET_ACCOUNTS,
  LoginMode,
  getAvailableAccounts,
  getModeConfig
} from '../config/loginConfig'
import {
  quickLogin,
  guestLogin,
  saveToken,
  TokenType
} from '../utils/tokenAuth'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const loading = ref(false)
const selectedAccount = ref(null)
const currentMode = ref(LoginMode.QUICK)

/**
 * 当前登录模式配置
 */
const modeConfig = computed(() => getModeConfig(currentMode.value))

/**
 * 可用账号列表
 */
const availableAccounts = computed(() => getAvailableAccounts(currentMode.value))

/**
 * 处理快速登录
 */
async function handleQuickLogin(account) {
  if (loading.value) return

  selectedAccount.value = account.id
  loading.value = true

  try {
    const result = quickLogin(account)
    
    if (result.success) {
      message.success(`欢迎回来，${account.displayName}！`)
      
      const redirect = route.query.redirect || '/'
      await router.push(redirect)
    } else {
      message.error(result.message || '登录失败，请稍后重试')
      selectedAccount.value = null
    }
  } catch (error) {
    console.error('[Login] 快速登录错误:', error)
    message.error(error.message || '登录失败，请稍后重试')
    selectedAccount.value = null
  } finally {
    loading.value = false
  }
}

/**
 * 处理传统登录（兼容模式）
 */
async function handleTraditionalLogin(account) {
  if (loading.value) return

  selectedAccount.value = account.id
  loading.value = true

  try {
    const result = await userStore.login({
      username: account.username,
      password: account.password
    })

    if (result && result.success) {
      message.success(`欢迎回来，${account.displayName}！`)
      
      const redirect = route.query.redirect || '/'
      await router.push(redirect)
    } else {
      message.error(result?.message || '登录失败，请稍后重试')
      selectedAccount.value = null
    }
  } catch (error) {
    console.error('[Login] 传统登录错误:', error)
    message.error(error.message || '登录失败，请稍后重试')
    selectedAccount.value = null
  } finally {
    loading.value = false
  }
}

/**
 * 处理访客登录
 */
async function handleGuestLogin() {
  if (loading.value) return

  loading.value = true

  try {
    const result = guestLogin()
    
    if (result.success) {
      message.success('已进入访客模式，仅可查看内容')
      
      const redirect = route.query.redirect || '/'
      await router.push(redirect)
    } else {
      message.error(result.message || '登录失败，请稍后重试')
    }
  } catch (error) {
    console.error('[Login] 访客登录错误:', error)
    message.error(error.message || '登录失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

/**
 * 处理账号选择
 */
function handleAccountClick(account) {
  if (currentMode === LoginMode.GUEST) {
    handleGuestLogin()
  } else if (currentMode === LoginMode.QUICK) {
    handleQuickLogin(account)
  } else {
    handleTraditionalLogin(account)
  }
}

/**
 * 切换登录模式
 */
function switchMode(mode) {
  if (mode === currentMode.value) return
  currentMode.value = mode
  selectedAccount.value = null
  message.info(`已切换到${getModeConfig(mode).title}`)
}

onMounted(() => {
  document.title = 'CAUC-SEP 登录'
})
</script>

<template>
  <div class="login-page">
    <!-- 背景装饰 -->
    <div class="login-page__bg">
      <div class="bg-circle bg-circle--1" />
      <div class="bg-circle bg-circle--2" />
      <div class="bg-circle bg-circle--3" />
    </div>

    <!-- 主内容 -->
    <div class="login-page__content">
      <!-- 登录卡片 -->
      <div class="login-card">
        <!-- Logo -->
        <div class="login-card__logo">
          <ThunderboltOutlined class="login-card__logo-icon" />
        </div>

        <!-- 标题 -->
        <h1 class="login-card__title">
          CAUC-SEP
        </h1>
        <p class="login-card__subtitle">
          自旋电子器件实验平台
        </p>

        <!-- 登录模式切换 -->
        <div class="login-card__modes">
          <button
            class="mode-btn"
            :class="{ 'mode-btn--active': currentMode === LoginMode.QUICK }"
            @click="switchMode(LoginMode.QUICK)"
          >
            <ThunderboltOutlined />
            <span>快速登录</span>
          </button>
          <button
            class="mode-btn"
            :class="{ 'mode-btn--active': currentMode === LoginMode.PASSWORD }"
            @click="switchMode(LoginMode.PASSWORD)"
          >
            <UserOutlined />
            <span>账号密码</span>
          </button>
          <button
            v-if="currentMode !== LoginMode.GUEST"
            class="mode-btn mode-btn--guest"
            :class="{ 'mode-btn--active': currentMode === LoginMode.GUEST }"
            @click="switchMode(LoginMode.GUEST)"
          >
            <EyeOutlined />
            <span>访客模式</span>
          </button>
        </div>

        <!-- 账号选择区域 -->
        <div class="login-card__accounts">
          <h3 class="accounts-title">
            <component :is="modeConfig.icon" />
            <span>{{ modeConfig.title }}</span>
          </h3>
          <p class="accounts-subtitle">{{ modeConfig.subtitle }}</p>

          <div class="accounts-list">
            <button
              v-for="account in availableAccounts"
              :key="account.id"
              class="account-card"
              :class="{
                'account-card--selected': selectedAccount === account.id,
                'account-card--loading': loading && selectedAccount === account.id
              }"
              :style="{
                '--account-color': account.color,
                '--account-bg': account.bgColor
              }"
              :disabled="loading"
              @click="handleAccountClick(account)"
            >
              <div class="account-card__icon">
                <component :is="account.icon" />
              </div>
              <div class="account-card__info">
                <span class="account-card__name">{{ account.displayName }}</span>
                <span class="account-card__desc">{{ account.description }}</span>
              </div>
              <div class="account-card__action">
                <CheckCircleOutlined v-if="selectedAccount === account.id && !loading" />
                <span
                  v-else-if="loading && selectedAccount === account.id"
                  class="loading-spinner"
                />
                <span
                  v-else
                  class="action-text"
                >{{ currentMode === LoginMode.GUEST ? '进入' : '登录' }}</span>
              </div>
            </button>
          </div>
        </div>

        <!-- 底部信息 -->
        <div class="login-card__footer">
          <p class="login-card__info">
            <SafetyOutlined /> {{ modeConfig.description }}
          </p>
        </div>
      </div>

      <!-- 版权信息 -->
      <div class="login-page__copyright">
        <p>© 2024-2026 CAUC-SEP 自旋电子器件实验平台</p>
        <p>中国民航大学 · 材料物理专业</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 页面容器 */
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  position: relative;
  overflow: hidden;
}

/* 背景装饰 */
.login-page__bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

.bg-circle {
  position: absolute;
  border-radius: 50%;
  opacity: 0.1;
}

.bg-circle--1 {
  width: 600px;
  height: 600px;
  background: linear-gradient(135deg, #0077ff, #00c6ff);
  top: -200px;
  right: -100px;
  animation: float 20s ease-in-out infinite;
}

.bg-circle--2 {
  width: 400px;
  height: 400px;
  background: linear-gradient(135deg, #00c6ff, #0077ff);
  bottom: -100px;
  left: -100px;
  animation: float 15s ease-in-out infinite reverse;
}

.bg-circle--3 {
  width: 300px;
  height: 300px;
  background: linear-gradient(135deg, #764ba2, #667eea);
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation: pulse 10s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(30px, -30px); }
}

@keyframes pulse {
  0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.1; }
  50% { transform: translate(-50%, -50%) scale(1.1); opacity: 0.15; }
}

/* 主内容 */
.login-page__content {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  padding: 20px;
}

/* 登录卡片 */
.login-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
}

/* Logo */
.login-card__logo {
  width: 80px;
  height: 80px;
  margin: 0 auto 20px;
  background: linear-gradient(135deg, #0077ff 0%, #00c6ff 100%);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 30px rgba(0, 119, 255, 0.3);
}

.login-card__logo-icon {
  font-size: 40px;
  color: white;
}

/* 标题 */
.login-card__title {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
  margin: 0 0 8px;
  text-align: center;
  letter-spacing: 2px;
}

.login-card__subtitle {
  font-size: 14px;
  color: #666;
  margin: 0 0 30px;
  text-align: center;
}

/* 登录模式切换 */
.login-card__modes {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #eee;
}

.mode-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 8px;
  background: #f5f5f5;
  border: 2px solid transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 13px;
  color: #666;
}

.mode-btn:hover {
  background: #e6f7ff;
  border-color: #1890ff;
  color: #1890ff;
}

.mode-btn--active {
  background: #e6f7ff;
  border-color: #1890ff;
  color: #1890ff;
}

.mode-btn .anticon {
  font-size: 20px;
}

.mode-btn--guest {
  background: #fff7e6;
  border-color: #faad14;
  color: #faad14;
}

.mode-btn--guest:hover {
  background: #fffbe6;
}

.mode-btn--guest.mode-btn--active {
  background: #fffbe6;
  border-color: #faad14;
  color: #faad14;
}

/* 账号选择区域 */
.login-card__accounts {
  margin-bottom: 20px;
}

.accounts-subtitle {
  font-size: 13px;
  color: #999;
  margin: 8px 0 16px;
  text-align: center;
}

.accounts-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin: 0 0 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #eee;
}

.accounts-title :deep(.anticon) {
  color: #0077ff;
}

/* 账号列表 */
.accounts-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 账号卡片 */
.account-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: var(--account-bg);
  border: 2px solid transparent;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: left;
  width: 100%;
}

.account-card:hover {
  border-color: var(--account-color);
  transform: translateX(4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.account-card--selected {
  border-color: var(--account-color);
  background: var(--account-bg);
}

.account-card--loading {
  pointer-events: none;
}

.account-card:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

/* 账号图标 */
.account-card__icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: var(--account-color);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.account-card__icon :deep(.anticon) {
  font-size: 24px;
  color: white;
}

/* 账号信息 */
.account-card__info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.account-card__name {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
}

.account-card__desc {
  font-size: 12px;
  color: #666;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 操作区域 */
.account-card__action {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 50px;
}

.account-card__action :deep(.anticon) {
  font-size: 24px;
  color: var(--account-color);
}

.action-text {
  font-size: 14px;
  font-weight: 500;
  color: var(--account-color);
}

/* 加载动画 */
.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--account-color);
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 底部信息 */
.login-card__footer {
  text-align: center;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.login-card__info {
  font-size: 13px;
  color: #888;
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.login-card__info :deep(.anticon) {
  color: #52c41a;
}

/* 版权信息 */
.login-page__copyright {
  margin-top: 30px;
  text-align: center;
}

.login-page__copyright p {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  margin: 0;
  line-height: 1.8;
}

/* 响应式 */
@media (max-width: 480px) {
  .login-card {
    padding: 30px 20px;
  }

  .login-card__title {
    font-size: 24px;
  }

  .login-card__logo {
    width: 60px;
    height: 60px;
  }

  .login-card__logo-icon {
    font-size: 30px;
  }

  .account-card {
    padding: 12px;
  }

  .account-card__icon {
    width: 40px;
    height: 40px;
  }

  .account-card__icon :deep(.anticon) {
    font-size: 20px;
  }
}
</style>
