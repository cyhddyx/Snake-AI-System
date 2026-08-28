<script setup lang="ts">
import axios from 'axios'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { predictCandidates, type Candidate } from '@/api/vision'
import { speciesApi, type Species, type ToxicityLevel } from '@/api/snake/species'
import { generaApi, type Genus } from '@/api/snake/genera'
import { familiesApi, type Family } from '@/api/snake/families'
import { useAuthStore } from '@/stores/auth'
import AppIcon from '@/components/icons/AppIcon.vue'

const router = useRouter()
const authStore = useAuthStore()

const fileInput = ref<HTMLInputElement | null>(null)
const previewUrl = ref<string | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const candidates = ref<Candidate[]>([])
const isDragging = ref(false)

const allSpecies = ref<Species[]>([])
const genera = ref<Genus[]>([])
const families = ref<Family[]>([])
const speciesIndex = ref<Map<string, Species>>(new Map())

const ONBOARDING_KEY = 'snake_ai_vision_onboarding_hidden'
const isOnboardingVisible = ref(!localStorage.getItem(ONBOARDING_KEY))

const hideOnboarding = () => {
  isOnboardingVisible.value = false
  localStorage.setItem(ONBOARDING_KEY, 'true')
}

const RECENT_KEY = 'snake_ai_recent_viewed_ids'
const recentIds = ref<number[]>(JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'))

const loadInitialData = async () => {
  try {
    const [list, genusList, familyList] = await Promise.all([
      speciesApi.list(),
      generaApi.list(),
      familiesApi.list(),
    ])
    allSpecies.value = list
    genera.value = genusList
    families.value = familyList

    const map = new Map<string, Species>()
    const normalize = (s: string) => s.replace(/\s+/g, '').toLowerCase()
    list.forEach((item) => {
      map.set(normalize(item.chinese_name), item)
      map.set(normalize(item.latin_name), item)
      item.aliases?.forEach((alias) => map.set(normalize(alias), item))
    })
    speciesIndex.value = map
  } catch (err) {
    console.error('Failed to load species index', err)
  }
}

const matchedCandidates = computed(() => {
  const normalize = (s: string) => s.replace(/\s+/g, '').toLowerCase()
  return candidates.value.map((c) => {
    const species = speciesIndex.value.get(normalize(c.species))
    const genus = species ? genera.value.find((g) => g.id === species.genus_id) : null
    const family = genus ? families.value.find((f) => f.id === genus.family_id) : null
    return { candidate: c, species, genus, family }
  })
})

const favoriteSpecies = computed(() => {
  const favoriteSet = new Set(authStore.favoriteIds)
  return allSpecies.value.filter((s) => favoriteSet.has(s.id))
})

const recentSpecies = computed(() => {
  return recentIds.value
    .map((id) => allSpecies.value.find((s) => s.id === id))
    .filter((s): s is Species => !!s)
})

const handleFile = async (file: File) => {
  if (!file.type.startsWith('image/')) {
    error.value = '请上传有效的图片文件。'
    return
  }

  previewUrl.value = URL.createObjectURL(file)
  candidates.value = []
  error.value = null
  loading.value = true

  try {
    const result = await predictCandidates(file)
    candidates.value = result.candidates
    if (isOnboardingVisible.value) hideOnboarding()
  } catch (err) {
    error.value = '识别失败，请检查网络或更换图片重试。'
  } finally {
    loading.value = false
  }
}

const onFileChange = (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) handleFile(file)
}

const onDrop = (e: DragEvent) => {
  isDragging.value = false
  const file = e.dataTransfer?.files[0]
  if (file) handleFile(file)
}

const toggleFavorite = async (speciesId: number) => {
  if (!authStore.isAuthenticated) {
    error.value = '请先登录后再收藏。'
    return
  }
  try {
    await authStore.syncFavorite(speciesId)
  } catch {
    error.value = '收藏同步失败。'
  }
}

const pushRecent = (id: number) => {
  const next = [id, ...recentIds.value.filter((i) => i !== id)].slice(0, 10)
  recentIds.value = next
  localStorage.setItem(RECENT_KEY, JSON.stringify(next))
}

const goDetail = (s: Species) => {
  pushRecent(s.id)
  router.push({ name: 'species-detail', params: { id: String(s.id) } })
}

const getConfidenceColor = (score: number) => {
  if (score > 0.8) return 'var(--primary-color)'
  if (score > 0.5) return '#ca8a04'
  return '#d64040'
}

onMounted(() => {
  loadInitialData()
})
</script>

<template>
  <div class="vision-page">
    <header class="vision-header">
      <div class="header-left">
        <p class="kicker">AI Vision Intelligence</p>
        <h1>智能识别</h1>
        <p class="subtitle">上传照片，利用计算机视觉模型快速锁定蛇类物种。</p>
      </div>
      <button v-if="!isOnboardingVisible" class="show-help" @click="isOnboardingVisible = true">
        <AppIcon name="info" :size="14" />
        使用帮助
      </button>
    </header>

    <transition name="fade-height">
      <section v-if="isOnboardingVisible" class="onboarding-panel">
        <div class="onboarding-grid">
          <div class="guide-card">
            <AppIcon name="camera" :size="32" class="guide-icon" />
            <h3>推荐上传</h3>
            <p>清晰、光线充足、且主体处于画面中央的近距离特写照片。</p>
          </div>
          <div class="guide-card">
            <AppIcon name="error" :size="32" class="guide-icon error" />
            <h3>尽量避免</h3>
            <p>过于模糊、遮挡严重或主体比例过小的照片，这会降低准确度。</p>
          </div>
          <div class="guide-card">
            <AppIcon name="book" :size="32" class="guide-icon" />
            <h3>多维评估</h3>
            <p>AI 结果仅供参考。请结合地理分布、形态特征及专家意见确认。</p>
          </div>
        </div>
        <button class="close-onboarding" @click="hideOnboarding">知道了，开始识别</button>
      </section>
    </transition>

    <div class="vision-layout">
      <div class="vision-main">
        <section
          class="drop-area"
          :class="{ 'is-dragging': isDragging, 'has-preview': !!previewUrl }"
          @dragover.prevent="isDragging = true"
          @dragleave.prevent="isDragging = false"
          @drop.prevent="onDrop"
          @click="fileInput?.click()"
        >
          <input ref="fileInput" type="file" accept="image/*" hidden @change="onFileChange" />

          <div v-if="!previewUrl" class="upload-prompt">
            <div class="upload-icon-wrap">
              <AppIcon name="upload" :size="64" class="upload-icon" />
            </div>
            <p>点击或拖拽照片到此处识别</p>
            <span class="upload-hint">支持 JPG, PNG, WEBP (最大 10MB)</span>
          </div>

          <div v-else class="preview-container">
            <img :src="previewUrl" class="preview-img" alt="识别预览" />
            <div class="re-upload">更换照片</div>
            <div v-if="loading" class="analysis-overlay">
              <div class="scanner-bar"></div>
              <p>AI 模型正在分析中...</p>
            </div>
          </div>
        </section>

        <section class="result-section">
          <h2>识别结果</h2>

          <div v-if="!candidates.length && !loading && !error" class="result-placeholder">
            <AppIcon name="search" :size="48" class="placeholder-icon" />
            <p>识别结果将在这里按置信度排序显示</p>
          </div>

          <div v-else-if="error" class="result-error">{{ error }}</div>

          <div v-else class="result-list">
            <div
              v-for="(item, index) in matchedCandidates"
              :key="item.candidate.species"
              class="result-item"
              :class="{ 'is-top-match': index === 0 , 'has-species': !!item.species }"
              @click="item.species && goDetail(item.species)"
            >
              <div class="result-header">
                <div class="rank-badge">#{{ index + 1 }}</div>
                <div class="result-names">
                  <h3 v-if="item.species" class="clickable-name" @click="goDetail(item.species)">
                    {{ item.candidate.species }}
                  </h3>
                  <h3 v-else>{{ item.candidate.species }}</h3>
                  <p class="latin-meta">{{ item.genus?.chinese_name }} · {{ item.family?.chinese_name }}</p>
                </div>

                <div class="result-actions">
                  <button
                    v-if="item.species"
                    class="fav-btn"
                    :class="{ active: authStore.favoriteIds.includes(item.species.id) }"
                    @click="toggleFavorite(item.species.id)"
                  >
                    ★
                  </button>
                </div>
              </div>

              <div class="confidence-container">
                <div class="confidence-info">
                  <span>置信度</span>
                  <strong>{{ (item.candidate.confidence * 1).toFixed(1) }}%</strong>
                </div>
                <div class="confidence-bar-bg">
                  <div
                    class="confidence-bar-fill"
                    :style="{
                      width: `${item.candidate.confidence * 100}%`,
                      backgroundColor: getConfidenceColor(item.candidate.confidence)
                    }"
                  ></div>
                </div>
              </div>

              <div v-if="item.species" class="quick-tags">
                <span v-if="item.species.toxicity" class="q-tag toxicity">{{ item.species.toxicity }}</span>
                <span v-if="item.species.iucn_status" class="q-tag iucn">{{ item.species.iucn_status }}</span>
              </div>
            </div>
          </div>
        </section>
      </div>

      <aside class="vision-sidebar">
        <section class="sidebar-block">
          <h3>我的收藏</h3>
          <div v-if="!authStore.isAuthenticated" class="sidebar-empty">登录以同步收藏</div>
          <div v-else-if="!favoriteSpecies.length" class="sidebar-empty">暂无收藏物种</div>
          <div v-else class="sidebar-list">
            <div v-for="s in favoriteSpecies.slice(0, 5)" :key="s.id" class="mini-card" @click="goDetail(s)">
              <strong>{{ s.chinese_name }}</strong>
              <span>{{ s.latin_name }}</span>
            </div>
          </div>
        </section>

        <section class="sidebar-block">
          <h3>最近浏览</h3>
          <div v-if="!recentSpecies.length" class="sidebar-empty">近期没有查看过物种</div>
          <div v-else class="sidebar-list">
            <div v-for="s in recentSpecies" :key="s.id" class="mini-card" @click="goDetail(s)">
              <strong>{{ s.chinese_name }}</strong>
              <span>{{ s.latin_name }}</span>
            </div>
          </div>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.vision-page { padding: 24px; min-height: 100vh; max-width: 1400px; margin: 0 auto; }
.vision-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.kicker { font-size: 12px; font-weight: 800; color: var(--primary-color); text-transform: uppercase; margin-bottom: 4px; }
.vision-header h1 { margin: 0; font-size: 28px; }
.subtitle { color: var(--text-muted); font-size: 14px; margin: 8px 0 0; }
.show-help { background: var(--card-bg); border: 1px solid var(--border-color); padding: 8px 16px; border-radius: 999px; cursor: pointer; font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 8px; }

.onboarding-panel { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 24px; padding: 32px; margin-bottom: 32px; box-shadow: var(--shadow-sm); overflow: hidden; }
.onboarding-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 32px; margin-bottom: 24px; }
.guide-card { display: flex; flex-direction: column; gap: 12px; }
.guide-icon { color: var(--primary-color); opacity: 0.8; }
.guide-icon.error { color: #d64040; }
.guide-card h3 { margin: 0; font-size: 16px; font-weight: 700; }
.guide-card p { margin: 0; font-size: 14px; color: var(--text-muted); line-height: 1.6; }
.close-onboarding { width: 100%; height: 48px; border-radius: 14px; background: var(--primary-color); color: #fff; border: none; cursor: pointer; font-weight: 700; font-size: 15px; }

.vision-layout { display: grid; grid-template-columns: 1fr 320px; gap: 32px; }

.drop-area { background: var(--card-bg); border: 2px dashed var(--border-color); border-radius: 28px; height: 380px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.3s; position: relative; overflow: hidden; }
.drop-area.is-dragging { border-color: var(--primary-color); background: var(--primary-soft); transform: scale(1.01); }
.upload-icon { color: var(--primary-color); opacity: 0.3; }
.upload-prompt { text-align: center; color: var(--text-muted); }

.preview-img { width: 100%; height: 100%; object-fit: contain; }
.analysis-overlay { position: absolute; inset: 0; background: rgba(255,255,255,0.85); display: flex; flex-direction: column; align-items: center; justify-content: center; z-index: 10; color: var(--primary-dark); font-weight: 700; }
@media (prefers-color-scheme: dark) { .analysis-overlay { background: rgba(0,0,0,0.7); } }

.result-placeholder { text-align: center; padding: 60px 0; color: var(--text-muted); opacity: 0.5; }
.placeholder-icon { margin-bottom: 16px; }

.result-item { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 20px; padding: 24px; transition: transform 0.2s; margin-bottom: 16px; }
.result-item.is-top-match { border-width: 2px; border-color: var(--primary-color); box-shadow: var(--shadow-md); }
.rank-badge { width: 36px; height: 36px; border-radius: 50%; background: var(--bg-color); display: flex; align-items: center; justify-content: center; font-weight: 900; font-size: 14px; flex-shrink: 0; }
.is-top-match .rank-badge { background: var(--primary-color); color: #fff; }

.fav-btn { border: 1px solid var(--border-color); background: var(--card-bg); width: 40px; height: 40px; border-radius: 12px; cursor: pointer; font-size: 18px; color: var(--text-muted); }
.fav-btn.active { color: #ca8a04; border-color: #fde047; background: #fefce8; }

.sidebar-block { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 24px; padding: 24px; margin-bottom: 24px; }
.sidebar-block h3 { margin: 0 0 20px; font-size: 14px; text-transform: uppercase; letter-spacing: 0.15em; color: var(--text-muted); font-weight: 800; }
.mini-card { padding: 14px; background: var(--bg-color); border-radius: 14px; cursor: pointer; transition: all 0.2s; margin-bottom: 10px; }
.mini-card:hover { transform: translateX(6px); background: var(--primary-soft); }

@media (max-width: 900px) {
  .vision-layout { grid-template-columns: 1fr; }
  .onboarding-grid { grid-template-columns: 1fr; }
}
</style>
