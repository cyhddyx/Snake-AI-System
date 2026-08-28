<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useFlashMessage } from '@/composables/useFlashMessage'
import AppIcon from '@/components/icons/AppIcon.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const { error: showError } = useFlashMessage()

const mode = ref<'login' | 'register'>('login')
const loading = ref(false)
const localError = ref<string | null>(null)

const usernameOrEmail = ref('')
const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')

const isRegisterMode = computed(() => mode.value === 'register')
const pageTitle = computed(() => (isRegisterMode.value ? '加入蛇类百科' : '欢迎回来'))

const switchMode = (m: 'login' | 'register') => {
  mode.value = m
  localError.value = null
}

const submit = async () => {
  localError.value = null
  if (isRegisterMode.value && password.value !== confirmPassword.value) {
    localError.value = '两次输入的密码不一致'
    return
  }

  loading.value = true
  try {
    if (isRegisterMode.value) {
      await authStore.register({
        username: username.value,
        email: email.value,
        password: password.value,
      })
    } else {
      await authStore.login({
        username_or_email: usernameOrEmail.value,
        password: password.value,
      })
    }
    const redirect = route.query.redirect as string
    void router.push(redirect || '/encyclopedia')
  } catch (err: any) {
    localError.value = err.response?.data?.detail || '认证失败，请检查输入'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="brand-decoration">
      <img src="@/assets/login-bg.svg" alt="Background" class="snake-bg-img" />
      <div class="circles"><span></span><span></span></div>
    </div>

    <div class="login-container">
      <header class="login-brand">
        <p class="kicker">Snake iAtlas System</p>
        <h1>{{ pageTitle }}</h1>
      </header>

      <section class="login-card">
        <nav class="mode-tabs">
          <button :class="{ active: !isRegisterMode }" @click="switchMode('login')">登录</button>
          <button :class="{ active: isRegisterMode }" @click="switchMode('register')">快速注册</button>
        </nav>

        <transition name="fade">
          <div v-if="localError" class="top-error-box">{{ localError }}</div>
        </transition>

        <form class="auth-form" @submit.prevent="submit">
          <transition name="mode-fade" mode="out-in">
            <div :key="mode" class="form-fields">
              <template v-if="!isRegisterMode">
                <label class="field">
                  <span>用户名或邮箱</span>
                  <input v-model="usernameOrEmail" type="text" autocomplete="username" placeholder="输入账号" required />
                </label>
              </template>

              <template v-else>
                <label class="field">
                  <span>用户名</span>
                  <input v-model="username" type="text" autocomplete="username" placeholder="起个名字吧" required />
                </label>
                <label class="field">
                  <span>邮箱</span>
                  <input v-model="email" type="email" autocomplete="email" placeholder="example@mail.com" required />
                </label>
              </template>

              <label class="field">
                <span>密码</span>
                <input
                  v-model="password"
                  type="password"
                  :autocomplete="isRegisterMode ? 'new-password' : 'current-password'"
                  placeholder="不少于6位"
                  required
                />
              </label>

              <label v-if="isRegisterMode" class="field">
                <span>确认密码</span>
                <input v-model="confirmPassword" type="password" autocomplete="new-password" placeholder="再次输入密码" required />
              </label>
            </div>
          </transition>

          <button class="submit-btn" type="submit" :disabled="loading">
            {{ loading ? '处理中...' : (isRegisterMode ? '立即创建账号' : '开启探索') }}
          </button>
        </form>

        <footer class="card-footer">
          <p v-if="!isRegisterMode">忘记密码？请联系管理员重置</p>
          <router-link to="/encyclopedia" class="back-link">暂不登录，返回图鉴</router-link>
        </footer>
      </section>
    </div>
  </div>
</template>

<style scoped>
.login-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 24px; background: var(--bg-color); position: relative; overflow: hidden; }

.brand-decoration { position: absolute; inset: 0; pointer-events: none; z-index: 0; opacity: 0.15; }
.snake-bg-img { position: absolute; right: -100px; bottom: -100px; width: 600px; height: auto; transform: rotate(-15deg); }
.circles span { position: absolute; border-radius: 50%; border: 2px solid var(--primary-color); opacity: 0.2; }
.circles span:nth-child(1) { width: 300px; height: 300px; top: -150px; left: -100px; }
.circles span:nth-child(2) { width: 500px; height: 500px; bottom: -250px; right: -200px; }

.login-container { width: min(100%, 460px); position: relative; z-index: 10; }
.login-brand { text-align: center; margin-bottom: 32px; }
.kicker { font-size: 13px; font-weight: 800; color: var(--primary-color); text-transform: uppercase; letter-spacing: 0.2em; }
.login-brand h1 { font-size: 32px; margin: 8px 0 0; color: var(--text-main); font-weight: 800; }

.login-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 28px; box-shadow: var(--shadow-md); overflow: hidden; }

.mode-tabs { display: flex; background: var(--bg-color); padding: 6px; border-radius: 16px; margin: 24px 24px 0; }
.mode-tabs button { flex: 1; border: none; background: transparent; padding: 10px; border-radius: 12px; cursor: pointer; font-size: 14px; font-weight: 700; color: var(--text-muted); transition: all 0.2s; }
.mode-tabs button.active { background: var(--card-bg); color: var(--primary-color); box-shadow: var(--shadow-sm); }

.top-error-box { margin: 20px 24px 0; padding: 12px 16px; background: #fee2e2; color: #d64040; border-radius: 12px; font-size: 13px; font-weight: 600; text-align: center; }

.auth-form { padding: 24px; }
.form-fields { display: grid; gap: 20px; }
.field { display: flex; flex-direction: column; gap: 8px; }
.field span { font-size: 12px; font-weight: 800; color: var(--text-muted); text-transform: uppercase; }
.field input { height: 48px; border-radius: 14px; border: 1.5px solid var(--border-color); background: var(--bg-color); padding: 0 16px; font-size: 15px; outline: none; transition: all 0.2s; }
.field input:focus { border-color: var(--primary-color); background: var(--card-bg); box-shadow: 0 0 0 4px var(--primary-soft); }

.submit-btn { width: 100%; height: 52px; border-radius: 16px; background: var(--primary-color); color: #fff; border: none; font-size: 16px; font-weight: 800; cursor: pointer; margin-top: 32px; box-shadow: 0 8px 20px rgba(116, 172, 0, 0.3); transition: all 0.2s; }
.submit-btn:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 12px 24px rgba(116, 172, 0, 0.4); }
.submit-btn:disabled { opacity: 0.6; cursor: not-allowed; }

.card-footer { padding: 0 24px 24px; text-align: center; font-size: 13px; color: var(--text-muted); }
.back-link { display: block; margin-top: 16px; color: var(--primary-color); text-decoration: none; font-weight: 600; }

.mode-fade-enter-active, .mode-fade-leave-active { transition: all 0.3s ease; }
.mode-fade-enter-from { opacity: 0; transform: translateX(20px); }
.mode-fade-leave-to { opacity: 0; transform: translateX(-20px); }

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
