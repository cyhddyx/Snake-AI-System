<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { speciesApi, type IUCNStatus, type Species, type ToxicityLevel } from '@/api/snake/species'
import { speciesContentApi, type SpeciesContent } from '@/api/snake/speciesContent'
import { speciesImagesApi, type SpeciesImage } from '@/api/snake/speciesImages'
import { generaApi, type Genus } from '@/api/snake/genera'
import { familiesApi, type Family } from '@/api/snake/families'
import { useAuthStore } from '@/stores/auth'
import { useFlashMessage } from '@/composables/useFlashMessage'
import AppIcon from '@/components/icons/AppIcon.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { error: showError } = useFlashMessage()

const loading = ref(true)
const error = ref<string | null>(null)

const species = ref<Species | null>(null)
const content = ref<SpeciesContent | null>(null)
const images = ref<SpeciesImage[]>([])
const genus = ref<Genus | null>(null)
const family = ref<Family | null>(null)

const currentImageIndex = ref(0)
const showLightbox = ref(false)
const activeDetailRequest = ref(0)

const speciesId = computed(() => {
  const parsed = Number(route.params.id)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
})

const isReviewer = computed(() => ['admin', 'editor'].includes(authStore.user?.role || ''))
const contributionRoute = computed(() =>
  species.value
    ? isReviewer.value
      ? { name: 'species-editor', query: { id: String(species.value.id) } }
      : { name: 'species-submit', query: { species_id: String(species.value.id) } }
    : '/submit',
)
const contributionLabel = computed(() => (isReviewer.value ? '去纠错' : '提交纠错'))
const isFavorited = computed(() => {
  if (!species.value) return false
  return authStore.favoriteIds.includes(species.value.id)
})

const mainImage = computed(() => {
  const current = images.value[currentImageIndex.value]
  if (current) return current.image_url
  const preferred = images.value.find((item) => item.is_cover)
  if (preferred) return preferred.image_url
  return images.value[0]?.image_url || ''
})

const currentLightboxImage = computed(() => images.value[currentImageIndex.value] || null)

const fieldBlocks = computed(() => {
  const d = content.value
  return [
    { title: '形态特征', value: d?.morphology || '' },
    { title: '分类历史', value: d?.history || '' },
    { title: '分布地区', value: d?.distribution || '' },
    { title: '栖息环境', value: d?.habitat || '' },
    { title: '行为习性', value: d?.behavior || '' },
    { title: '繁殖', value: d?.reproduction || '' },
    { title: '保护状况', value: d?.conservation || '' },
    { title: '危险性', value: d?.hazard || '' },
  ].filter((item) => item.value.trim().length > 0)
})

const summaryFacts = computed(() => [
  { label: '图库总数', value: `${images.value.length} 张` },
  { label: '数据状态', value: species.value?.iucn_status ? getIUCNText(species.value.iucn_status) : '未评估' },
  { label: '发现者', value: species.value?.discoverer || '未知' },
  { label: '年份', value: species.value?.discover_year || '未知' },
])

const loadDetail = async (id: number | null) => {
  if (!id) {
    error.value = '无效的物种编号'
    loading.value = false
    return
  }

  const requestId = ++activeDetailRequest.value
  loading.value = true
  error.value = null

  try {
    const speciesData = await speciesApi.get(id)

    const [contentData, imageData, genusData] = await Promise.all([
      speciesContentApi.get(id).catch(() => null),
      speciesImagesApi.list(id).catch(() => []),
      generaApi.get(speciesData.genus_id).catch(() => null),
    ])

    const familyData = genusData?.family_id
      ? await familiesApi.get(genusData.family_id).catch(() => null)
      : null

    if (requestId !== activeDetailRequest.value) return

    species.value = speciesData
    content.value = contentData
    images.value = imageData
    genus.value = genusData
    family.value = familyData
    
    const coverIdx = imageData.findIndex((item) => item.is_cover)
    currentImageIndex.value = coverIdx >= 0 ? coverIdx : 0
  } catch (err) {
    console.error(err)
    if (requestId === activeDetailRequest.value) {
      error.value = '加载物种详情失败，请稍后重试'
    }
  } finally {
    if (requestId === activeDetailRequest.value) {
      loading.value = false
    }
  }
}

const openLightbox = (index: number) => {
  currentImageIndex.value = index
  showLightbox.value = true
}

const closeLightbox = () => {
  showLightbox.value = false
}

const toggleFavorite = async () => {
  if (!species.value) return
  if (!authStore.isAuthenticated) {
    router.push({ path: '/login', query: { redirect: route.fullPath } })
    return
  }
  try {
    await authStore.syncFavorite(species.value.id)
  } catch (err) {
    console.error('Failed to toggle favorite', err)
    showError('收藏同步失败')
  }
}

const showPrevImage = () => {
  if (images.value.length <= 1) return
  currentImageIndex.value =
    currentImageIndex.value > 0 ? currentImageIndex.value - 1 : images.value.length - 1
}

const showNextImage = () => {
  if (images.value.length <= 1) return
  currentImageIndex.value =
    currentImageIndex.value < images.value.length - 1 ? currentImageIndex.value + 1 : 0
}

const handleLightboxKeydown = (event: KeyboardEvent) => {
  if (!showLightbox.value) return
  if (event.key === 'Escape') closeLightbox()
  if (event.key === 'ArrowLeft') showPrevImage()
  if (event.key === 'ArrowRight') showNextImage()
}

const getToxicityColor = (toxicity?: ToxicityLevel) => {
  switch (toxicity) {
    case '极毒':
    case '剧毒': return '#d64040'
    case '有毒': return '#dc7f2c'
    case '微毒': return '#b99b3a'
    case '无毒': return '#3f9468'
    default: return '#89919c'
  }
}

const getIUCNText = (status?: IUCNStatus) => {
  const map: Record<IUCNStatus, string> = {
    EX: '已灭绝', EW: '野外灭绝', CR: '极危', EN: '濒危',
    VU: '易危', NT: '近危', LC: '无危', DD: '数据不足', NE: '未评估',
  }
  return status ? map[status] : ''
}

const getIUCNColor = (status?: IUCNStatus) => {
  const map: Record<IUCNStatus, string> = {
    EX: '#60646d', EW: '#6c707b', CR: '#d64040', EN: '#e46a2f',
    VU: '#dc9e2c', NT: '#9ea748', LC: '#45a76f', DD: '#9399a6', NE: '#b0b5bf',
  }
  return status ? map[status] : '#b0b5bf'
}

watch(() => speciesId.value, (id) => void loadDetail(id), { immediate: true })

window.addEventListener('keydown', handleLightboxKeydown)
onBeforeUnmount(() => window.removeEventListener('keydown', handleLightboxKeydown))
</script>

<template>
  <div class="species-page">
    <!-- State Handling -->
    <div v-if="loading" class="state-wrap">
      <div class="loader"></div>
      <p>正在加载详情...</p>
    </div>

    <div v-else-if="error" class="state-wrap error">
      <p>{{ error }}</p>
      <button class="retry-btn" @click="loadDetail(speciesId)">重试</button>
    </div>

    <div v-else-if="species" class="article-layout">
      <!-- 1. Header (Inside data block to fix positioning) -->
      <header class="species-header">
        <nav class="breadcrumb">
          <router-link to="/encyclopedia" class="crumb-link">图鉴首页</router-link>
          <span class="crumb-separator">/</span>
          <template v-if="family">
            <router-link :to="{ path: '/encyclopedia', query: { familyId: family.id } }" class="crumb-link">
              {{ family.chinese_name }}
            </router-link>
            <span class="crumb-separator">/</span>
          </template>
          <template v-if="genus">
            <router-link :to="{ path: '/encyclopedia', query: { familyId: genus.family_id, genusId: genus.id } }" class="crumb-link">
              {{ genus.chinese_name }}
            </router-link>
            <span class="crumb-separator">/</span>
          </template>
          <span class="crumb-current">{{ species.chinese_name }}</span>
        </nav>
        <div class="header-actions">
          <button class="action-btn favorite-btn" :class="{ active: isFavorited }" @click="toggleFavorite">
            <AppIcon name="heart" :size="15" />
            {{ isFavorited ? '已收藏' : '收藏' }}
          </button>
          <router-link :to="contributionRoute" class="action-btn secondary">
            {{ contributionLabel }}
          </router-link>
        </div>
      </header>

      <!-- 2. Immersive Hero Section -->
      <section class="hero-section" :class="{ 'no-image': !mainImage }" @click="mainImage ? openLightbox(currentImageIndex) : null">
        <div v-if="mainImage" class="hero-cover" :style="{ backgroundImage: `url(${mainImage})` }"></div>
        <div class="hero-overlay">
          <div class="hero-container">
            <div class="hero-content">
              <p class="hero-kicker">{{ family?.chinese_name }} / {{ genus?.chinese_name }}</p>
              <h1>{{ species.chinese_name }}</h1>
              <p class="latin">{{ species.latin_name }}</p>
              <div v-if="species.aliases?.length" class="aliases">
                又名：{{ species.aliases.join('、') }}
              </div>
              <div class="hero-bottom-row">
                <div class="hero-badges">
                  <span v-if="species.toxicity" class="badge" :style="{ backgroundColor: getToxicityColor(species.toxicity) }">
                    {{ species.toxicity }}
                  </span>
                  <span v-if="species.iucn_status" class="badge" :style="{ backgroundColor: getIUCNColor(species.iucn_status) }">
                    {{ getIUCNText(species.iucn_status) }}
                  </span>
                </div>
                <div v-if="images.length > 0" class="image-count-tag">
                  📸 {{ images.length }} 张图片
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div class="article-container">
        <!-- 3. Main Content Flow -->
        <main class="article-main">
          <section class="intro-block">
            <p class="abstract">{{ species.basic_intro }}</p>
          </section>

          <!-- Interspersed Gallery Mosaic -->
          <section v-if="images.length >= 2" class="image-mosaic" :class="`count-${Math.min(images.length, 3)}`">
            <div v-for="(img, index) in images.slice(0, 3)" :key="img.id" class="mosaic-item" @click="openLightbox(index)">
              <img :src="img.image_url" :alt="img.caption || species.chinese_name" />
              <p v-if="img.caption" class="mosaic-caption">{{ img.caption }}</p>
            </div>
          </section>
          
          <!-- If only 1 image, it's already in Hero, but let's show a link or small card if needed. 
               The requirement says 1 image should be interactive. Hero already handles this now. -->

          <div class="content-flow">
            <section v-for="block in fieldBlocks" :key="block.title" class="content-section">
              <h2>{{ block.title }}</h2>
              <div class="text-body">{{ block.value }}</div>
            </section>
          </div>

          <!-- Bottom Gallery for 4th+ images -->
          <section v-if="images.length > 3" class="bottom-gallery">
            <h3>更多图像</h3>
            <div class="thumb-grid">
              <button v-for="(img, index) in images" :key="img.id" class="thumb-btn" @click="openLightbox(index)">
                <img :src="img.thumbnail_url || img.image_url" alt="" />
              </button>
            </div>
          </section>
        </main>

        <!-- 4. Informational Sidebar -->
        <aside class="article-sidebar">
          <div class="sticky-sidebar">
            <section class="info-card">
              <h3>分类地位</h3>
              <div class="taxon-tree">
                <div class="taxon-item"><span class="label">界</span><strong>动物界 Animalia</strong></div>
                <div class="taxon-item"><span class="label">门</span><strong>脊索动物门 Chordata</strong></div>
                <div class="taxon-item"><span class="label">纲</span><strong>爬行纲 Reptilia</strong></div>
                <div class="taxon-item"><span class="label">目</span><strong>有鳞目 Squamata</strong></div>
                <div class="taxon-item"><span class="label">科</span><strong>{{ family?.chinese_name }} {{ family?.latin_name }}</strong></div>
                <div class="taxon-item"><span class="label">属</span><strong>{{ genus?.chinese_name }} {{ genus?.latin_name }}</strong></div>
              </div>
            </section>

            <section class="info-card">
              <h3>物种特征</h3>
              <div class="fact-list">
                <div class="fact-item" v-for="fact in summaryFacts" :key="fact.label">
                  <span class="label">{{ fact.label }}</span>
                  <strong>{{ fact.value }}</strong>
                </div>
              </div>
            </section>
          </div>
        </aside>
      </div>
    </div>

    <!-- 5. Lightbox -->
    <Transition name="fade">
      <div v-if="showLightbox && mainImage" class="lightbox" @click="closeLightbox">
        <button v-if="images.length > 1" class="lightbox-nav prev" @click.stop="showPrevImage">‹</button>
        <div class="lightbox-content">
          <img :src="currentLightboxImage?.image_url || ''" alt="" @click.stop />
          <p v-if="currentLightboxImage?.caption" class="lightbox-caption">{{ currentLightboxImage.caption }}</p>
        </div>
        <button v-if="images.length > 1" class="lightbox-nav next" @click.stop="showNextImage">›</button>
        <p class="lightbox-hint">第 {{ currentImageIndex + 1 }} / {{ images.length }} 张 · Esc 关闭</p>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.species-page {
  min-height: calc(100vh - 68px);
  background: var(--bg-color);
}

.article-layout {
  animation: fadeIn 0.4s ease-out;
  position: relative;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 1. Immersive Hero */
.hero-section {
  position: relative;
  height: 65vh;
  min-height: 480px;
  max-height: 800px;
  overflow: hidden;
  background-color: #1a241b; /* Fallback for no-image */
}

.hero-section.no-image {
  height: 40vh;
  min-height: 300px;
  background: linear-gradient(135deg, #253322 0%, #3a4d35 100%);
}

.hero-section:not(.no-image) {
  cursor: zoom-in;
}

.hero-cover {
  width: 100%;
  height: 100%;
  background-size: cover;
  background-position: center;
  /* background-attachment: fixed is removed to fix iOS issue */
}

.hero-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.9) 0%, rgba(0, 0, 0, 0.3) 50%, transparent 100%);
  display: flex;
  align-items: flex-end;
  padding-bottom: 80px;
}

.hero-container {
  width: min(100%, 1200px);
  margin: 0 auto;
  padding: 0 24px;
}

.hero-kicker {
  color: var(--primary-color);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  margin-bottom: 12px;
  font-size: 14px;
}

.hero-content h1 {
  font-size: clamp(36px, 6vw, 64px);
  color: #fff;
  margin: 0;
  line-height: 1.1;
  font-weight: 800;
  text-shadow: 0 2px 15px rgba(0,0,0,0.5);
}

.hero-content .latin {
  font-size: clamp(18px, 2.5vw, 26px);
  color: rgba(255, 255, 255, 0.85);
  font-style: italic;
  margin: 12px 0 16px;
  font-weight: 300;
}

.aliases {
  color: rgba(255,255,255,0.7);
  font-size: 14px;
  margin-bottom: 24px;
}

.hero-bottom-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.hero-badges {
  display: flex;
  gap: 12px;
}

.badge {
  padding: 8px 20px;
  border-radius: 999px;
  font-weight: 700;
  color: #fff;
  font-size: 14px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}

.image-count-tag {
  background: rgba(255,255,255,0.15);
  backdrop-filter: blur(8px);
  padding: 6px 14px;
  border-radius: 999px;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  border: 1px solid rgba(255,255,255,0.2);
}

/* 2. Article Container */
.article-container {
  width: min(100%, 1200px);
  margin: -60px auto 60px;
  padding: 0 24px;
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 48px;
  position: relative;
  z-index: 10;
}

.article-main {
  background: #fff;
  padding: 60px;
  border-radius: 24px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.08);
}

.intro-block {
  margin-bottom: 50px;
}

.abstract {
  font-size: 19px;
  line-height: 1.85;
  color: var(--text-main);
  font-weight: 400;
  border-left: 6px solid var(--primary-color);
  padding-left: 32px;
  margin: 0;
}

/* 3. Image Mosaic Grid Logic */
.image-mosaic {
  display: grid;
  gap: 16px;
  margin: 50px 0;
}

.image-mosaic.count-2 {
  grid-template-columns: 1fr 1fr;
  height: 300px;
}

.image-mosaic.count-3 {
  grid-template-columns: 1.8fr 1fr;
  grid-template-rows: 240px 240px;
}

.mosaic-item {
  position: relative;
  border-radius: 16px;
  overflow: hidden;
  cursor: zoom-in;
  box-shadow: 0 4px 15px rgba(0,0,0,0.1);
}

.image-mosaic.count-3 .mosaic-item:nth-child(1) {
  grid-row: span 2;
}

.mosaic-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.6s cubic-bezier(0.165, 0.84, 0.44, 1);
}

.mosaic-item:hover img {
  transform: scale(1.08);
}

.mosaic-caption {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.8));
  color: #fff;
  padding: 16px;
  font-size: 12px;
  margin: 0;
}

/* 4. Content Sections */
.content-section {
  margin-bottom: 50px;
}

.content-section h2 {
  font-size: 26px;
  color: var(--text-main);
  border-bottom: 3px solid var(--bg-color);
  padding-bottom: 16px;
  margin-bottom: 24px;
  font-weight: 700;
}

.text-body {
  font-size: 17px;
  line-height: 1.9;
  color: var(--text-main);
  white-space: pre-line;
}

/* 5. Bottom Gallery */
.bottom-gallery {
  margin-top: 60px;
  padding-top: 40px;
  border-top: 1px solid var(--border-color);
}

.thumb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px;
  margin-top: 24px;
}

.thumb-btn {
  aspect-ratio: 4 / 3;
  border-radius: 10px;
  overflow: hidden;
  border: 2px solid transparent;
  cursor: pointer;
  padding: 0;
  transition: all 0.2s;
}

.thumb-btn:hover {
  transform: translateY(-4px);
  border-color: var(--primary-color);
}

.thumb-btn img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 6. Sidebar */
.sticky-sidebar {
  position: sticky;
  top: 40px; /* Adjusted to balance article-container negative margin */
  display: grid;
  gap: 24px;
}

.info-card {
  background: #fff;
  padding: 32px;
  border-radius: 20px;
  border: 1px solid var(--border-color);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
}

.info-card h3 {
  margin: 0 0 20px;
  font-size: 14px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.15em;
  font-weight: 700;
}

.taxon-tree, .fact-list {
  display: grid;
  gap: 14px;
}

.taxon-item, .fact-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.label {
  font-size: 11px;
  color: #a3b1c2;
  font-weight: 800;
  text-transform: uppercase;
}

.taxon-item strong, .fact-item strong {
  font-size: 14px;
  color: var(--text-main);
}

/* Header & Breadcrumb */
.species-header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 40px;
  background: linear-gradient(rgba(0,0,0,0.6), transparent);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.breadcrumb {
  background: rgba(255, 255, 255, 0.12) !important;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2) !important;
  padding: 8px 18px !important;
  border-radius: 999px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.crumb-link {
  color: rgba(255, 255, 255, 0.85);
  text-decoration: none;
  font-size: 13px;
}

.crumb-link:hover { color: #fff; text-decoration: underline; }

.crumb-separator {
  color: rgba(255,255,255,0.4);
  font-size: 11px;
}

.crumb-current {
  color: #fff;
  font-size: 13px;
  font-weight: 600;
}

.action-btn {
  height: 38px;
  border-radius: 999px;
  padding: 0 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn.secondary {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.action-btn.secondary:hover { background: rgba(255, 255, 255, 0.3); }

.favorite-btn {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(12px);
  gap: 8px;
}

.favorite-btn.active {
  background: rgba(214, 64, 64, 0.2);
  border-color: rgba(255, 160, 160, 0.45);
}

/* State Wrap */
.state-wrap {
  min-height: 80vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  color: var(--text-muted);
}

.loader {
  width: 44px;
  height: 44px;
  border: 3px solid #eee;
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.retry-btn {
  height: 36px;
  padding: 0 20px;
  border: none;
  border-radius: 10px;
  background: var(--primary-color);
  color: #fff;
  cursor: pointer;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* Lightbox */
.lightbox {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.98);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.lightbox-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  max-width: 90vw;
}

.lightbox img {
  max-height: 85vh;
  object-fit: contain;
  box-shadow: 0 0 50px rgba(0,0,0,0.5);
}

.lightbox-caption {
  color: #fff;
  font-size: 14px;
  margin: 0;
  text-align: center;
}

.lightbox-nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 60px;
  height: 60px;
  border: none;
  background: rgba(255, 255, 255, 0.05);
  color: #fff;
  font-size: 40px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.3s;
}

.lightbox-nav:hover { background: rgba(255, 255, 255, 0.15); }
.lightbox-nav.prev { left: 40px; }
.lightbox-nav.next { right: 40px; }

.lightbox-hint {
  position: absolute;
  bottom: 30px;
  color: rgba(255,255,255,0.4);
  font-size: 13px;
}

@media (max-width: 1100px) {
  .article-container {
    grid-template-columns: 1fr;
    margin-top: -40px;
  }
  /* Sidebar now naturally falls below article-main */
  .sticky-sidebar { position: static; }
  .article-main { padding: 40px; }
}

@media (max-width: 600px) {
  .hero-section { height: 55vh; }
  .article-main { padding: 24px; border-radius: 0; margin: 0 -24px; }
  .article-container { padding: 0 16px; }
  .abstract { font-size: 17px; padding-left: 20px; }
  .image-mosaic.count-2, .image-mosaic.count-3 {
    grid-template-columns: 1fr;
    grid-template-rows: repeat(auto-fill, 240px);
    height: auto;
  }
  .image-mosaic.count-3 .mosaic-item:nth-child(1) { grid-row: span 1; }
  .hero-content h1 { font-size: 32px; }
  .species-header { padding: 16px 20px; }
  .header-actions { gap: 8px; }
  .action-btn { padding: 0 14px; }
}
</style>
