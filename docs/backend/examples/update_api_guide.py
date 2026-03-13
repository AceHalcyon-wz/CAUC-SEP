"""
自动更新系统 API 使用指南

功能：
- 版本检查与更新通知
- 增量更新包上传与应用
- 更新包校验与完整性验证
- 备份管理与回滚机制
- 更新历史查询

作者：Backend Engineer Agent
创建日期：2026-03-07
"""

# ============================================================================
# API 端点概览
# ============================================================================

"""
基础路径: /api/update

端点列表:
├── GET  /version              - 获取当前版本信息
├── POST /check                - 检查是否有可用更新
├── GET  /progress             - 获取当前更新进度
├── POST /apply                - 应用更新包
├── POST /upload               - 上传更新包
├── POST /rollback             - 回滚到指定版本
├── GET  /backups              - 列出所有备份
├── POST /backups              - 手动创建备份
├── DELETE /backups/{id}       - 删除指定备份
├── GET  /history              - 获取更新历史
├── POST /cleanup              - 清理旧备份
└── POST /verify               - 验证更新包完整性
"""

# ============================================================================
# 使用示例
# ============================================================================

# 1. 获取当前版本信息
"""
GET /api/update/version

响应示例:
{
    "version": "0.3.0",
    "build_number": 30000,
    "release_date": "2026-03-07",
    "release_notes": "CAUC-SEP 自旋电子实验平台",
    "changelog": [
        "新增自动更新系统",
        "优化设备状态推送",
        "增强安全中间件"
    ]
}
"""

# 2. 检查更新
"""
POST /api/update/check
Content-Type: application/json

请求体:
{
    "current_version": "0.3.0",
    "current_build": 30000,
    "channel": "stable"  // 可选: stable, beta, dev
}

响应示例:
{
    "has_update": true,
    "current_version": "0.3.0",
    "update_info": {
        "available": true,
        "latest_version": "0.3.2",
        "latest_build": 30200,
        "update_type": "hotfix",  // full, incremental, hotfix
        "priority": "low",  // low, medium, high, critical
        "release_date": "2026-03-07",
        "release_notes": "稳定版本 - 安全更新",
        "changelog": ["修复安全漏洞", "优化性能"],
        "package_size_mb": 45.2,
        "download_url": "/api/update/download/0.3.2",
        "checksum_sha256": "abc123def456..."
    },
    "checked_at": "2026-03-07T15:30:00"
}
"""

# 3. 上传更新包
"""
POST /api/update/upload
Content-Type: multipart/form-data

请求体:
file: <update_package.zip>

响应示例:
{
    "success": true,
    "message": "上传成功",
    "filename": "update_20260307_153000.zip",
    "filepath": "updates/update_20260307_153000.zip",
    "size_mb": 45.2,
    "checksum_sha256": "abc123def456..."
}

注意事项:
- 仅支持 .zip 格式
- 最大文件大小: 500MB
- 上传后会自动计算SHA256校验和
"""

# 4. 验证更新包
"""
POST /api/update/verify
Content-Type: application/json

请求体:
{
    "package_path": "updates/update_20260307_153000.zip",
    "checksum": "abc123def456..."
}

响应示例:
{
    "success": true,
    "message": "校验通过",
    "package_path": "updates/update_20260307_153000.zip",
    "expected_checksum": "abc123def456..."
}
"""

# 5. 应用更新
"""
POST /api/update/apply
Content-Type: application/json

请求体:
{
    "package_path": "updates/update_20260307_153000.zip",
    "checksum_sha256": "abc123def456...",
    "create_backup": true,  // 是否创建备份（推荐）
    "auto_rollback": true   // 失败时是否自动回滚（推荐）
}

响应示例:
{
    "success": true,
    "message": "更新应用成功，请重启服务",
    "backup_id": "backup_20260307_153100",
    "applied_at": "2026-03-07T15:31:00"
}

注意事项:
- 应用更新前会自动验证校验和
- 建议启用自动备份和自动回滚
- 更新完成后需要重启服务
"""

# 6. 查询更新进度
"""
GET /api/update/progress

响应示例:
{
    "status": "installing",  // idle, checking, downloading, verifying, installing, completed, failed, rolling_back
    "progress_percent": 75.5,
    "current_step": "正在应用更新...",
    "total_bytes": 47400000,
    "downloaded_bytes": 35700000,
    "started_at": "2026-03-07T15:30:00",
    "estimated_remaining_seconds": 30.5
}
"""

# 7. 创建手动备份
"""
POST /api/update/backups?description=手动备份

响应示例:
{
    "backup_id": "backup_20260307_153200",
    "version": "0.3.0",
    "created_at": "2026-03-07T15:32:00",
    "size_mb": 120.5,
    "file_count": 156,
    "checksum": "a1b2c3d4e5f6...",
    "description": "手动备份"
}
"""

# 8. 列出所有备份
"""
GET /api/update/backups

响应示例:
{
    "total": 3,
    "backups": [
        {
            "backup_id": "backup_20260307_153200",
            "version": "0.3.0",
            "created_at": "2026-03-07T15:32:00",
            "size_mb": 120.5,
            "file_count": 156,
            "checksum": "a1b2c3d4e5f6...",
            "description": "手动备份"
        },
        // ... 更多备份
    ]
}
"""

# 9. 回滚到指定版本
"""
POST /api/update/rollback
Content-Type: application/json

请求体:
{
    "backup_id": "backup_20260307_153200",
    "verify_integrity": true  // 是否验证备份完整性
}

响应示例:
{
    "success": true,
    "message": "回滚成功，请重启服务",
    "rolled_back_to": "0.3.0",
    "rolled_back_at": "2026-03-07T15:35:00"
}

注意事项:
- 回滚后需要重启服务
- 建议启用完整性验证
"""

# 10. 删除备份
"""
DELETE /api/update/backups/backup_20260307_153200

响应示例:
{
    "success": true,
    "message": "备份 backup_20260307_153200 已删除"
}
"""

# 11. 查询更新历史
"""
GET /api/update/history

响应示例:
{
    "total": 5,
    "records": [
        {
            "record_id": "update_20260307_153100",
            "from_version": "0.3.0",
            "to_version": "0.3.2",
            "update_type": "hotfix",
            "status": "success",
            "applied_at": "2026-03-07T15:31:00",
            "duration_seconds": 45.5,
            "backup_id": "backup_20260307_153100",
            "notes": ""
        },
        // ... 更多记录
    ]
}
"""

# 12. 清理旧备份
"""
POST /api/update/cleanup?max_count=5

响应示例:
{
    "success": true,
    "message": "已清理 2 个旧备份",
    "deleted_count": 2
}

说明:
- 默认保留最近5个备份
- 可通过 max_count 参数调整
"""

# ============================================================================
# 更新包格式规范
# ============================================================================

"""
更新包必须是 ZIP 格式，包含以下内容:

update_package.zip
├── update_manifest.json    # 更新清单（必需）
├── api/                    # 更新的API文件
├── core/                   # 更新的核心文件
├── drivers/                # 更新的驱动文件
└── ...

更新清单格式 (update_manifest.json):
{
    "version": "1.0",
    "target_version": "0.3.2",
    "files": [
        {
            "path": "api/update.py",
            "action": "add",      // add, modify, delete
            "checksum": "sha256..."
        },
        {
            "path": "core/new_feature.py",
            "action": "add"
        },
        {
            "path": "old_file.py",
            "action": "delete"
        }
    ],
    "scripts": {
        "pre_update": "scripts/pre_update.py",
        "post_update": "scripts/post_update.py"
    }
}
"""

# ============================================================================
# 错误处理
# ============================================================================

"""
常见错误码:

400 - 请求参数错误
{
    "detail": "仅支持 .zip 格式的更新包"
}

404 - 资源不存在
{
    "detail": "备份不存在: backup_001"
}

413 - 文件过大
{
    "detail": "文件过大，最大支持 500MB"
}

500 - 服务器内部错误
{
    "detail": "更新应用失败: 校验和不匹配"
}
"""

# ============================================================================
# 最佳实践
# ============================================================================

"""
1. 更新前检查:
   - 调用 /check 检查是否有可用更新
   - 查看更新类型和优先级
   - 阅读发布说明和变更日志

2. 备份策略:
   - 应用更新前始终创建备份
   - 定期清理旧备份（保留5个即可）
   - 重要更新前手动创建备份

3. 更新验证:
   - 上传后验证校验和
   - 应用前再次验证
   - 启用自动回滚机制

4. 回滚准备:
   - 记录备份ID
   - 测试回滚流程
   - 准备应急恢复方案

5. 监控与日志:
   - 监控更新进度
   - 查看更新历史
   - 记录异常情况

6. 安全考虑:
   - 仅从可信来源获取更新包
   - 验证更新包签名
   - 限制更新API访问权限
"""

# ============================================================================
# 前端集成示例
# ============================================================================

"""
// Vue 3 组件示例
<template>
  <div class="update-manager">
    <h2>系统更新</h2>
    
    <!-- 当前版本 -->
    <div class="current-version">
      <p>当前版本: {{ currentVersion }}</p>
      <button @click="checkUpdate">检查更新</button>
    </div>
    
    <!-- 更新信息 -->
    <div v-if="updateInfo" class="update-info">
      <h3>发现新版本: {{ updateInfo.latest_version }}</h3>
      <p>更新类型: {{ updateInfo.update_type }}</p>
      <p>优先级: {{ updateInfo.priority }}</p>
      <p>大小: {{ updateInfo.package_size_mb }} MB</p>
      
      <h4>变更日志:</h4>
      <ul>
        <li v-for="change in updateInfo.changelog" :key="change">
          {{ change }}
        </li>
      </ul>
      
      <button @click="applyUpdate" :disabled="isUpdating">
        {{ isUpdating ? '更新中...' : '立即更新' }}
      </button>
    </div>
    
    <!-- 更新进度 -->
    <div v-if="isUpdating" class="update-progress">
      <p>状态: {{ progress.current_step }}</p>
      <progress :value="progress.progress_percent" max="100"></progress>
      <p>{{ progress.progress_percent.toFixed(1) }}%</p>
    </div>
    
    <!-- 备份管理 -->
    <div class="backup-manager">
      <h3>备份管理</h3>
      <button @click="createBackup">创建备份</button>
      <button @click="listBackups">查看备份</button>
      
      <ul v-if="backups.length > 0">
        <li v-for="backup in backups" :key="backup.backup_id">
          {{ backup.version }} - {{ backup.created_at }}
          <button @click="rollback(backup.backup_id)">回滚</button>
          <button @click="deleteBackup(backup.backup_id)">删除</button>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const currentVersion = ref('0.3.0')
const updateInfo = ref(null)
const isUpdating = ref(false)
const progress = ref({
  status: 'idle',
  progress_percent: 0,
  current_step: ''
})
const backups = ref([])

// 检查更新
async function checkUpdate() {
  try {
    const response = await axios.post('/api/update/check', {
      current_version: currentVersion.value,
      current_build: 30000,
      channel: 'stable'
    })
    
    if (response.data.has_update) {
      updateInfo.value = response.data.update_info
    } else {
      alert('已是最新版本')
    }
  } catch (error) {
    console.error('检查更新失败:', error)
    alert('检查更新失败')
  }
}

// 应用更新
async function applyUpdate() {
  if (!confirm('确定要更新吗？更新后需要重启服务。')) {
    return
  }
  
  isUpdating.value = true
  
  try {
    const response = await axios.post('/api/update/apply', {
      package_path: updateInfo.value.download_url,
      checksum_sha256: updateInfo.value.checksum_sha256,
      create_backup: true,
      auto_rollback: true
    })
    
    if (response.data.success) {
      alert('更新成功，请重启服务')
    }
  } catch (error) {
    console.error('更新失败:', error)
    alert('更新失败: ' + error.response?.data?.detail)
  } finally {
    isUpdating.value = false
  }
}

// 创建备份
async function createBackup() {
  try {
    const response = await axios.post('/api/update/backups', null, {
      params: { description: '手动备份' }
    })
    alert('备份创建成功: ' + response.data.backup_id)
  } catch (error) {
    console.error('创建备份失败:', error)
    alert('创建备份失败')
  }
}

// 列出备份
async function listBackups() {
  try {
    const response = await axios.get('/api/update/backups')
    backups.value = response.data.backups
  } catch (error) {
    console.error('获取备份列表失败:', error)
  }
}

// 回滚
async function rollback(backupId) {
  if (!confirm('确定要回滚吗？回滚后需要重启服务。')) {
    return
  }
  
  try {
    const response = await axios.post('/api/update/rollback', {
      backup_id: backupId,
      verify_integrity: true
    })
    
    if (response.data.success) {
      alert('回滚成功，请重启服务')
    }
  } catch (error) {
    console.error('回滚失败:', error)
    alert('回滚失败')
  }
}

// 删除备份
async function deleteBackup(backupId) {
  if (!confirm('确定要删除此备份吗？')) {
    return
  }
  
  try {
    await axios.delete(`/api/update/backups/${backupId}`)
    await listBackups()
  } catch (error) {
    console.error('删除备份失败:', error)
  }
}

// 轮询更新进度
let progressInterval = null

onMounted(() => {
  progressInterval = setInterval(async () => {
    if (isUpdating.value) {
      try {
        const response = await axios.get('/api/update/progress')
        progress.value = response.data
        
        if (response.data.status === 'completed' || response.data.status === 'failed') {
          isUpdating.value = false
        }
      } catch (error) {
        console.error('获取进度失败:', error)
      }
    }
  }, 1000)
})

// 清理定时器
onUnmounted(() => {
  if (progressInterval) {
    clearInterval(progressInterval)
  }
})
</script>
"""

# ============================================================================
# 生产环境部署建议
# ============================================================================

"""
1. 安全配置:
   - 启用HTTPS加密传输
   - 配置API访问认证（JWT Token）
   - 限制更新API的访问IP白名单
   - 验证更新包数字签名

2. 存储配置:
   - 使用独立磁盘存储更新包和备份
   - 配置自动清理策略（保留最近N个备份）
   - 监控磁盘空间使用情况

3. 监控告警:
   - 监控更新成功率
   - 监控回滚次数
   - 设置磁盘空间告警阈值
   - 记录所有更新操作日志

4. 灾备方案:
   - 定期备份到远程存储
   - 准备离线更新包
   - 制定应急恢复流程
   - 测试回滚流程

5. 性能优化:
   - 使用CDN分发更新包
   - 启用增量更新
   - 压缩更新包
   - 并行下载大文件

6. 合规要求:
   - 记录所有更新操作审计日志
   - 保留更新历史记录
   - 遵守数据保留政策
   - 定期审查更新策略
"""
