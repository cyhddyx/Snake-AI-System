<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { usersApi } from '@/api/snake/users'
import type { AuthUser, UserRole } from '@/api/snake/auth'
import { useFlashMessage } from '@/composables/useFlashMessage'

const router = useRouter()
const authStore = useAuthStore()
const { success, error: showError } = useFlashMessage()

const loading = ref(true)
const users = ref<AuthUser[]>([])
const savingId = ref<number | null>(null)

const isAdmin = computed(() => authStore.user?.role === 'admin')

const roleOptions: { value: UserRole; label: string }[] = [
  { value: 'user', label: '普通用户' },
  { value: 'editor', label: '编辑者' },
  { value: 'admin', label: '管理员' },
]

const formatDate = (value: string) =>
  new Date(value).toLocaleString('zh-CN', { hour12: false })

const loadUsers = async () => {
  loading.value = true
  try {
    users.value = await usersApi.list()
  } catch (err) {
    console.error(err)
    showError('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

const updateRole = async (user: AuthUser, role: UserRole) => {
  if (role === user.role) return
  if (user.id === authStore.user?.id && role !== 'admin') {
    showError('不能删除自己的管理员权限')
    return
  }
  savingId.value = user.id
  try {
    const updated = await usersApi.update(user.id, { role })
    const idx = users.value.findIndex((u) => u.id === user.id)
    if (idx >= 0) users.value[idx] = updated
    success(`已将 ${user.username} 的角色更新为 ${roleOptions.find((o) => o.value === role)?.label}`)
  } catch (err) {
    console.error(err)
    showError('更新角色失败')
  } finally {
    savingId.value = null
  }
}

const toggleActive = async (user: AuthUser) => {
  if (user.id === authStore.user?.id) {
    showError('不能禁用自己的账号')
    return
  }
  savingId.value = user.id
  try {
    const updated = await usersApi.update(user.id, { is_active: !user.is_active })
    const idx = users.value.findIndex((u) => u.id === user.id)
    if (idx >= 0) users.value[idx] = updated
    success(updated.is_active ? `已启用 ${user.username}` : `已禁用 ${user.username}`)
  } catch (err) {
    console.error(err)
    showError('操作失败')
  } finally {
    savingId.value = null
  }
}

const removeUser = async (user: AuthUser) => {
  if (user.id === authStore.user?.id) {
    showError('不能删除自己的账号')
    return
  }
  if (!confirm(`确定删除用户「${user.username}」吗？此操作不可撤销。`)) return
  savingId.value = user.id
  try {
    await usersApi.remove(user.id)
    users.value = users.value.filter((u) => u.id !== user.id)
    success(`已删除用户 ${user.username}`)
  } catch (err) {
    console.error(err)
    showError('删除用户失败')
  } finally {
    savingId.value = null
  }
}

onMounted(() => {
  if (!isAdmin.value) {
    router.replace('/encyclopedia')
    return
  }
  loadUsers()
})
</script>

<template>
  <div class="user-management-page">
    <header class="page-header">
      <div class="header-left">
        <h1>用户管理</h1>
        <span class="user-count">{{ users.length }} 位用户</span>
      </div>
      <button class="refresh-btn" :disabled="loading" @click="loadUsers">
        {{ loading ? '加载中...' : '刷新列表' }}
      </button>
    </header>

    <div v-if="loading" class="loading-state">
      <div class="loader"></div>
      <p>用户数据加载中...</p>
    </div>

    <div v-else class="user-table-container">
      <table class="user-table">
        <thead>
          <tr>
            <th class="col-id">ID</th>
            <th class="col-name">用户名</th>
            <th class="col-email">邮箱</th>
            <th class="col-role">角色</th>
            <th class="col-status">状态</th>
            <th class="col-date">注册时间</th>
            <th class="col-actions">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id" :class="{ self: user.id === authStore.user?.id }">
            <td class="col-id">{{ user.id }}</td>
            <td class="col-name">
              <span class="username">{{ user.username }}</span>
            </td>
            <td class="col-email">
              <span class="email-text">{{ user.email }}</span>
            </td>
            <td class="col-role">
              <select
                class="role-select"
                :value="user.role"
                :disabled="savingId === user.id"
                @change="updateRole(user, ($event.target as HTMLSelectElement).value as UserRole)"
              >
                <option v-for="opt in roleOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </td>
            <td class="col-status">
              <button
                class="status-toggle"
                :class="{ active: user.is_active }"
                :disabled="savingId === user.id || user.id === authStore.user?.id"
                @click="toggleActive(user)"
              >
                {{ user.is_active ? '正常' : '已禁用' }}
              </button>
            </td>
            <td class="col-date">{{ formatDate(user.created_at) }}</td>
            <td class="col-actions">
              <button
                class="del-btn"
                :disabled="savingId === user.id || user.id === authStore.user?.id"
                @click="removeUser(user)"
              >
                删除
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="!users.length" class="empty-hint">暂无用户数据</div>
    </div>
  </div>
</template>

<style scoped>
.user-management-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 32px 24px 80px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 28px;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 14px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 800;
}

.user-count {
  font-size: 14px;
  color: var(--text-muted);
}

.refresh-btn {
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 10px 20px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-main);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  color: var(--text-muted);
  gap: 16px;
}

.loader {
  width: 36px;
  height: 36px;
  border: 3px solid var(--border-color);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.user-table-container {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.user-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.user-table th {
  background: var(--bg-color);
  padding: 14px 16px;
  text-align: left;
  font-size: 12px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-color);
}

.user-table td {
  padding: 14px 16px;
  border-bottom: 1px solid var(--bg-color);
  vertical-align: middle;
}

.user-table tr:last-child td {
  border-bottom: none;
}

.user-table tr.self td {
  background: var(--primary-soft);
}

.user-table tr.self td:first-child {
  border-left: 3px solid var(--primary-color);
}

.col-id { width: 50px; color: var(--text-muted); font-variant-numeric: tabular-nums; }
.col-name { min-width: 120px; }
.col-email { min-width: 160px; }
.col-role { width: 140px; }
.col-status { width: 100px; text-align: center; }
.col-date { width: 170px; white-space: nowrap; color: var(--text-muted); font-size: 13px; }
.col-actions { width: 80px; text-align: center; }

.username {
  font-weight: 700;
}

.email-text {
  color: var(--text-muted);
  font-size: 13px;
}

.role-select {
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  outline: none;
  cursor: pointer;
  width: 100%;
}

.role-select:focus {
  border-color: var(--primary-color);
}

.status-toggle {
  background: #fee2e2;
  color: #d64040;
  border: none;
  border-radius: 8px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.status-toggle.active {
  background: var(--primary-soft);
  color: var(--primary-dark);
}

.status-toggle:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.del-btn {
  background: #fee2e2;
  color: #d64040;
  border: none;
  border-radius: 8px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.del-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.empty-hint {
  padding: 40px;
  text-align: center;
  color: var(--text-muted);
  font-size: 14px;
}

@media (max-width: 820px) {
  .user-table {
    font-size: 13px;
  }
  .user-table th,
  .user-table td {
    padding: 10px 8px;
  }
  .col-email {
    display: none;
  }
  .col-date {
    display: none;
  }
}
</style>
