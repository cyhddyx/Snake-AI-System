import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { authApi, type AuthUser, type LoginRequest, type RegisterRequest, userFavoritesApi } from '@/api/snake/auth'
import { setAuthToken } from '@/api/snake/snake'

const TOKEN_KEY = 'snake_ai_access_token'
const USER_KEY = 'snake_ai_current_user'
const FAVORITES_KEY = 'snake_ai_favorite_species_ids'

const readStoredUser = (): AuthUser | null => {
  try {
    const raw = localStorage.getItem(USER_KEY)
    if (!raw) return null
    return JSON.parse(raw) as AuthUser
  } catch {
    return null
  }
}

const safeLoadLocalFavoriteIds = (): number[] => {
  try {
    const raw = localStorage.getItem(FAVORITES_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter((item) => Number.isInteger(item) && item > 0)
  } catch {
    return []
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')
  const user = ref<AuthUser | null>(readStoredUser())
  const hydrating = ref(false)
  const favoriteIds = ref<number[]>([])

  setAuthToken(token.value)

  const isAuthenticated = computed(() => !!token.value && !!user.value)

  const persistAuth = () => {
    if (token.value) {
      localStorage.setItem(TOKEN_KEY, token.value)
    } else {
      localStorage.removeItem(TOKEN_KEY)
    }

    if (user.value) {
      localStorage.setItem(USER_KEY, JSON.stringify(user.value))
    } else {
      localStorage.removeItem(USER_KEY)
    }

    setAuthToken(token.value)
  }

  const clearAuth = () => {
    token.value = ''
    user.value = null
    favoriteIds.value = []
    persistAuth()
  }

  const refreshMe = async () => {
    if (!token.value) return null
    hydrating.value = true
    try {
      const me = await authApi.me()
      user.value = me
      persistAuth()
      return me
    } catch {
      clearAuth()
      return null
    } finally {
      hydrating.value = false
    }
  }

  const loadFavorites = async () => {
    if (!user.value) {
      favoriteIds.value = []
      return
    }
    const list = await userFavoritesApi.list(user.value.id)
    favoriteIds.value = list.map((item) => item.species_id)
  }

  const mergeLocalFavorites = async () => {
    if (!user.value) return
    const localIds = safeLoadLocalFavoriteIds()

    if (localIds.length === 0) {
      await loadFavorites()
      return
    }

    // Load current remote favorites first to avoid duplicates
    await loadFavorites()

    const newToSync = localIds.filter((id) => !favoriteIds.value.includes(id))
    if (newToSync.length > 0) {
      // Sync each new favorite to the server
      await Promise.allSettled(newToSync.map((id) => userFavoritesApi.add(user.value!.id, id)))
      // Reload after syncing everything
      await loadFavorites()
    }

    // Clear local favorites after successful merge
    localStorage.removeItem(FAVORITES_KEY)
  }

  const login = async (payload: LoginRequest) => {
    const res = await authApi.login(payload)
    token.value = res.access_token
    user.value = res.user
    persistAuth()
    await mergeLocalFavorites()
    return res.user
  }

  const register = async (payload: RegisterRequest) => {
    await authApi.register(payload)
    return login({
      username_or_email: payload.username,
      password: payload.password,
    })
  }

  const logout = () => {
    clearAuth()
  }

  const syncFavorite = async (speciesId: number) => {
    if (!user.value) return
    const exists = favoriteIds.value.includes(speciesId)
    if (exists) {
      await userFavoritesApi.remove(user.value.id, speciesId)
      favoriteIds.value = favoriteIds.value.filter((id) => id !== speciesId)
      return
    }
    await userFavoritesApi.add(user.value.id, speciesId)
    favoriteIds.value = [speciesId, ...favoriteIds.value]
  }

  return {
    token,
    user,
    hydrating,
    favoriteIds,
    isAuthenticated,
    login,
    register,
    logout,
    refreshMe,
    loadFavorites,
    syncFavorite,
    mergeLocalFavorites,
  }
})
