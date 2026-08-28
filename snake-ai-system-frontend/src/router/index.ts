import { createRouter, createWebHistory } from 'vue-router'
import VisionPage from '@/views/VisionPage.vue'
import ChatLLM from '@/views/ChatLLM.vue'
import SnakeEncyclopedia from '@/views/SnakeEncyclopedia.vue'
import SnakeSpeciesDetail from '@/views/SnakeSpeciesDetail.vue'
import SnakeSpeciesEditor from '@/views/SnakeSpeciesEditor.vue'
import SnakeSpeciesSubmission from '@/views/SnakeSpeciesSubmission.vue'
import FavoritesPage from '@/views/FavoritesPage.vue'
import LoginPage from '@/views/LoginPage.vue'
import NotFoundPage from '@/views/NotFoundPage.vue'
import UserManagementPage from '@/views/UserManagementPage.vue'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/encyclopedia' },
    { path: '/login', name: 'login', component: LoginPage },
    { path: '/vision', name: 'vision', component: VisionPage },
    { path: '/chatLLM', name: 'chatLLM', component: ChatLLM },
    { path: '/encyclopedia', name: 'encyclopedia', component: SnakeEncyclopedia },
    { path: '/species/:id', name: 'species-detail', component: SnakeSpeciesDetail },
    { path: '/favorites', name: 'favorites', component: FavoritesPage, meta: { requiresAuth: true } },
    { path: '/editor', name: 'species-editor', component: SnakeSpeciesEditor, meta: { requiresAuth: true, reviewerOnly: true } },
    { path: '/submit', name: 'species-submit', component: SnakeSpeciesSubmission, meta: { requiresAuth: true } },
    { path: '/admin/users', name: 'admin-users', component: UserManagementPage, meta: { requiresAuth: true, adminOnly: true } },
    { path: '/:pathMatch(.*)*', name: 'not-found', component: NotFoundPage },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()
  const requiresAuth = Boolean(to.meta.requiresAuth)
  const reviewerOnly = Boolean(to.meta.reviewerOnly)
  const adminOnly = Boolean(to.meta.adminOnly)

  if (!requiresAuth) {
    return true
  }

  if (!authStore.isAuthenticated && authStore.token) {
    await authStore.refreshMe()
  }

  if (!authStore.isAuthenticated) {
    return {
      path: '/login',
      query: { redirect: to.fullPath },
    }
  }

  if (adminOnly && authStore.user?.role !== 'admin') {
    return '/encyclopedia'
  }

  if (reviewerOnly && !['admin', 'editor'].includes(authStore.user?.role || '')) {
    return '/submit'
  }

  return true
})

export default router
