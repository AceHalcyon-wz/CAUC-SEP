<template>
  <div class="not-found-page">
    <el-result
      icon="warning"
      title="404"
      sub-title="抱歉，您访问的页面不存在"
    >
      <template #icon>
        <el-icon class="error-icon"><WarningFilled /></el-icon>
      </template>
      <template #extra>
        <el-button type="primary" @click="goHome">
          返回首页
        </el-button>
      </template>
    </el-result>
  </div>
</template>

<script setup>
/**
 * @file NotFound.vue
 * @path src/views/
 * @description 404页面
 * @author Agent
 * @date 2024-03-07
 */

import { useRouter } from 'vue-router'

const router = useRouter()

function goHome() {
  router.push('/')
}
</script>

<style scoped>
.not-found-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 64px);
  background-color: var(--color-bg-secondary);
}

.error-icon {
  font-size: 80px;
  color: var(--color-warning);
  animation: shake 0.5s ease-in-out;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-10px); }
  75% { transform: translateX(10px); }
}
</style>
