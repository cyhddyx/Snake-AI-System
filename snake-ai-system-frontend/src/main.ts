import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

const authStore = useAuthStore(pinia)
void authStore.refreshMe().then(async () => {
  if (authStore.isAuthenticated) {
    await authStore.mergeLocalFavorites()
  }
})

app.mount('#app')
