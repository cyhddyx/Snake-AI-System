<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useFlashMessage } from '@/composables/useFlashMessage'
import AppIcon from '@/components/icons/AppIcon.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const { messages, removeMessage } = useFlashMessage()

const isMenuOpen = ref(false)

const authLabel = computed(() => {
  const name = authStore.user?.username
  if (!name) return '登录'
  return name.length > 10 ? name.slice(0, 8) + '...' : name
})

const isReviewer = computed(() => ['admin', 'editor'].includes(authStore.user?.role || ''))
const isAdmin = computed(() => authStore.user?.role === 'admin')
const contributionLabel = computed(() => (isReviewer.value ? '编辑台' : '投稿'))

const isContributionActive = computed(() => {
  return route.path === '/submit' || route.path.startsWith('/editor')
})

const toggleMenu = () => {
  isMenuOpen.value = !isMenuOpen.value
}

const handleAuthAction = () => {
  isMenuOpen.value = false
  if (authStore.isAuthenticated) {
    if (confirm('确定要退出当前登录状态吗？')) {
      authStore.logout()
      void router.push('/encyclopedia')
    }
    return
  }
  void router.push('/login')
}

const openContribution = () => {
  isMenuOpen.value = false
  const target = isReviewer.value ? '/editor' : '/submit'
  if (authStore.isAuthenticated) {
    void router.push(target)
    return
  }
  void router.push({ path: '/login', query: { redirect: target } })
}

router.afterEach(() => {
  isMenuOpen.value = false
})
</script>

<template>
  <div class="app-shell" :class="{ 'menu-open': isMenuOpen }">
    <header class="top-nav">
      <div class="nav-container">
        <router-link to="/encyclopedia" class="brand">
          <img src="@/assets/brand-logo.svg" alt="Logo" class="brand-logo-img" />
          <span>Snake iAtlas</span>
        </router-link>
        
        <button class="menu-toggle" :class="{ active: isMenuOpen }" @click="toggleMenu" aria-label="Toggle Menu">
          <span class="icon-bar"></span>
          <span class="icon-bar"></span>
          <span class="icon-bar"></span>
        </button>

        <div class="nav-right" :class="{ open: isMenuOpen }">
          <nav class="main-nav">
            <router-link to="/encyclopedia">
              <AppIcon name="book" :size="16" class="nav-icon" />
              图鉴
            </router-link>
            <router-link to="/favorites">
              <AppIcon name="heart" :size="16" class="nav-icon" />
              收藏
            </router-link>
            <button 
              class="nav-btn" 
              :class="{ active: isContributionActive }" 
              @click="openContribution"
            >
              <AppIcon name="plus" :size="16" class="nav-icon" />
              {{ contributionLabel }}
            </button>
            <router-link v-if="isAdmin" to="/admin/users">
              <AppIcon name="user" :size="16" class="nav-icon" />
              用户
            </router-link>
            <router-link to="/vision">
              <AppIcon name="camera" :size="16" class="nav-icon" />
              识别
            </router-link>
            <router-link to="/chatLLM">
              <AppIcon name="chat" :size="16" class="nav-icon" />
              问答
            </router-link>
          </nav>
          
          <button 
            class="auth-btn" 
            :class="{ authenticated: authStore.isAuthenticated }" 
            @click="handleAuthAction"
          >
            <AppIcon name="user" :size="16" class="user-icon" />
            <span class="user-label">{{ authStore.isAuthenticated ? `${authLabel} · 退出` : authLabel }}</span>
          </button>
        </div>
      </div>
    </header>

    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <div class="toast-container">
      <transition-group name="toast">
        <div 
          v-for="msg in messages" 
          :key="msg.id" 
          class="toast-item" 
          :class="msg.type"
          @click="removeMessage(msg.id)"
        >
          <span class="toast-icon">
            <AppIcon v-if="msg.type === 'success'" name="check" :size="18" />
            <AppIcon v-else-if="msg.type === 'error'" name="error" :size="18" />
            <AppIcon v-else-if="msg.type === 'warning'" name="warning" :size="18" />
            <AppIcon v-else name="info" :size="18" />
          </span>
          <p>{{ msg.text }}</p>
        </div>
      </transition-group>
    </div>
  </div>
</template>

<style>
:root {
  --primary-color: #74ac00;
  --primary-dark: #5c8a00;
  --primary-soft: #eaf6d6;
  --bg-color: #f3f4f5;
  --card-bg: #ffffff;
  --text-main: #243326;
  --text-muted: #6a7280;
  --border-color: #dde1e5;
  --nav-bg: #1e2b1b;
  --nav-text: #ced8c8;
  --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 8px 24px rgba(0, 0, 0, 0.08);
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg-color: #121812;
    --card-bg: #1c241c;
    --text-main: #e2e8e2;
    --text-muted: #a0aaa0;
    --border-color: #2d382d;
    --nav-bg: #0a0e0a;
    --nav-text: #b0baa0;
    --primary-soft: #243015;
  }
}

* { box-sizing: border-box; }
html, body, #app { margin: 0; min-height: 100%; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg-color); color: var(--text-main); transition: background 0.3s, color 0.3s; }

.top-nav { height: 68px; background: var(--nav-bg); border-bottom: 1px solid var(--border-color); position: sticky; top: 0; z-index: 1000; display: flex; align-items: center; }
.nav-container { width: min(100%, 1280px); margin: 0 auto; padding: 0 24px; display: flex; justify-content: space-between; align-items: center; }

.brand { color: #fff; text-decoration: none; font-size: 20px; font-weight: 800; letter-spacing: -0.01em; display: flex; align-items: center; gap: 10px; }
.brand-logo-img { height: 28px; width: auto; }

.nav-right { display: flex; align-items: center; gap: 24px; }
.main-nav { display: flex; gap: 4px; }
.main-nav a, .nav-btn { height: 38px; padding: 0 16px; border-radius: 12px; display: inline-flex; align-items: center; gap: 8px; color: var(--nav-text); text-decoration: none; font-size: 14px; font-weight: 600; background: transparent; border: none; cursor: pointer; transition: all 0.2s; }
.main-nav a:hover, .nav-btn:hover { color: #fff; background: rgba(255,255,255,0.08); }
.main-nav a.router-link-active, .nav-btn.active { background: var(--primary-color); color: #fff; }

.auth-btn { height: 38px; padding: 0 16px; border-radius: 12px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: #fff; cursor: pointer; display: flex; align-items: center; gap: 8px; font-size: 13px; transition: all 0.2s; }
.auth-btn.authenticated { border-color: var(--primary-color); background: rgba(116, 172, 0, 0.1); }

.menu-toggle { display: none; flex-direction: column; gap: 5px; background: transparent; border: none; cursor: pointer; padding: 8px; }
.icon-bar { width: 22px; height: 2px; background: #fff; border-radius: 2px; transition: all 0.3s; }
.menu-toggle.active .icon-bar:nth-child(1) { transform: translateY(7px) rotate(45deg); }
.menu-toggle.active .icon-bar:nth-child(2) { opacity: 0; }
.menu-toggle.active .icon-bar:nth-child(3) { transform: translateY(-7px) rotate(-45deg); }

.app-main { min-height: calc(100vh - 68px); }

.toast-container { position: fixed; bottom: 32px; left: 50%; transform: translateX(-50%); z-index: 2000; display: flex; flex-direction: column; gap: 10px; width: min(90vw, 400px); }
.toast-item { background: var(--card-bg); color: var(--text-main); padding: 14px 20px; border-radius: 16px; box-shadow: var(--shadow-md); border: 1px solid var(--border-color); display: flex; align-items: center; gap: 12px; cursor: pointer; }
.toast-item.success { border-left: 4px solid var(--primary-color); }
.toast-item.error { border-left: 4px solid #d64040; }
.toast-item p { margin: 0; font-size: 14px; font-weight: 600; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.toast-enter-active { animation: toast-in 0.3s ease-out; }
.toast-leave-active { animation: toast-in 0.2s ease-in reverse; }
@keyframes toast-in { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

@media (max-width: 820px) {
  .menu-toggle { display: flex; z-index: 1001; }
  .nav-right { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: var(--nav-bg); flex-direction: column; padding: 100px 24px; gap: 40px; transform: translateX(100%); opacity: 0; transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); z-index: 1000; }
  .nav-right.open { transform: translateX(0); opacity: 1; pointer-events: auto; }
  .main-nav { flex-direction: column; width: 100%; gap: 16px; }
  .main-nav a, .nav-btn { width: 100%; height: 54px; justify-content: center; font-size: 18px; border-radius: 16px; }
  .auth-btn { width: 100%; height: 54px; justify-content: center; font-size: 16px; border-radius: 16px; }
}
</style>
