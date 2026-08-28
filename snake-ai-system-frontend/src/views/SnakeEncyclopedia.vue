<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { familiesApi, type Family } from '@/api/snake/families'
import { generaApi, type Genus } from '@/api/snake/genera'
import { speciesApi, type IUCNStatus, type Species, type ToxicityLevel } from '@/api/snake/species'
import { speciesImagesApi, type SpeciesImage } from '@/api/snake/speciesImages'
import SearchableSelect from '@/components/SearchableSelect.vue'
import AppIcon from '@/components/icons/AppIcon.vue'

type ViewMode = 'grid' | 'list'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref<string | null>(null)
const loadingElapsedSeconds = ref(0)
const activeLoadRequestId = ref(0)
const isFilterPanelOpen = ref(false)

const species = ref<Species[]>([])
const families = ref<Family[]>([])
const genera = ref<Genus[]>([])

const VIEW_MODE_KEY = 'snake_ai_encyclopedia_view_mode'

const searchQuery = ref('')
const viewMode = ref<ViewMode>((localStorage.getItem(VIEW_MODE_KEY) as ViewMode) || 'grid')
const selectedFamilyId = ref<'all' | number>(route.query.familyId ? Number(route.query.familyId) : 'all')
const selectedGenusId = ref<number | null>(route.query.genusId ? Number(route.query.genusId) : null)
const selectedToxicity = ref<'all' | ToxicityLevel>('all')
const selectedIUCN = ref<'all' | IUCNStatus>('all')

const coverImageMap = ref<Record<number, string>>({})
const imageLoadingSet = new Set<number>()

const toxicityOptions: Array<'all' | ToxicityLevel> = ['all', '无毒', '微毒', '有毒', '剧毒', '极毒']
const iucnOptions: Array<'all' | IUCNStatus> = ['all', 'LC', 'NT', 'VU', 'EN', 'CR', 'DD', 'NE', 'EW', 'EX']

let loadingTimer: ReturnType<typeof setInterval> | null = null

const startLoadingFeedback = () => {
  if (loadingTimer) clearInterval(loadingTimer)
  loadingElapsedSeconds.value = 0
  loadingTimer = setInterval(() => { loadingElapsedSeconds.value += 1 }, 1000)
}

const stopLoadingFeedback = () => {
  if (loadingTimer) {
    clearInterval(loadingTimer)
    loadingTimer = null
  }
}

const loadData = async () => {
  const requestId = ++activeLoadRequestId.value
  try {
    loading.value = true
    error.value = null
    startLoadingFeedback()
    const [familyData, genusData, speciesData] = await Promise.all([
      familiesApi.list(),
      generaApi.list(),
      speciesApi.list(),
    ])
    if (requestId !== activeLoadRequestId.value) return
    families.value = familyData
    genera.value = genusData
    species.value = speciesData
  } catch (err) {
    console.error(err)
    if (requestId === activeLoadRequestId.value) error.value = '加载图鉴数据失败'
  } finally {
    if (requestId === activeLoadRequestId.value) {
      stopLoadingFeedback()
      loading.value = false
    }
  }
}

const genusById = computed(() => {
  const map: Record<number, Genus> = {}
  for (const item of genera.value) map[item.id] = item
  return map
})

const familyById = computed(() => {
  const map: Record<number, Family> = {}
  for (const item of families.value) map[item.id] = item
  return map
})

const filteredGenera = computed(() => {
  if (selectedFamilyId.value === 'all') return []
  return genera.value.filter((item) => item.family_id === selectedFamilyId.value)
})

const filteredSpecies = computed(() => {
  const keyword = searchQuery.value.trim().toLowerCase()
  return species.value.filter((item) => {
    if (selectedGenusId.value !== null && item.genus_id !== selectedGenusId.value) return false
    if (selectedFamilyId.value !== 'all') {
      const genus = genusById.value[item.genus_id]
      if (!genus || genus.family_id !== selectedFamilyId.value) return false
    }
    if (selectedToxicity.value !== 'all' && item.toxicity !== selectedToxicity.value) return false
    if (selectedIUCN.value !== 'all' && item.iucn_status !== selectedIUCN.value) return false
    if (!keyword) return true
    return (
      item.chinese_name.toLowerCase().includes(keyword) ||
      item.latin_name.toLowerCase().includes(keyword) ||
      (item.aliases?.some(a => a.toLowerCase().includes(keyword)))
    )
  })
})

const activeFilterCount = computed(() => {
  let count = 0
  if (selectedFamilyId.value !== 'all') count++
  if (selectedGenusId.value !== null) count++
  if (selectedToxicity.value !== 'all') count++
  if (selectedIUCN.value !== 'all') count++
  return count
})

const ensureCoverLoaded = async (speciesId: number) => {
  if (coverImageMap.value[speciesId] !== undefined || imageLoadingSet.has(speciesId)) return
  imageLoadingSet.add(speciesId)
  try {
    const images = await speciesImagesApi.list(speciesId)
    const cover = images.find((item) => item.is_cover) || images[0]
    coverImageMap.value = { ...coverImageMap.value, [speciesId]: cover?.thumbnail_url || cover?.image_url || '' }
  } catch {
    coverImageMap.value = { ...coverImageMap.value, [speciesId]: '' }
  } finally {
    imageLoadingSet.delete(speciesId)
  }
}

const resetFilters = () => {
  searchQuery.value = ''
  selectedFamilyId.value = 'all'
  selectedGenusId.value = null
  selectedToxicity.value = 'all'
  selectedIUCN.value = 'all'
}

const getCoverUrl = (speciesId: number) => coverImageMap.value[speciesId] || ''

const getIUCNFullText = (status?: IUCNStatus) => {
  const map: Record<string, string> = {
    EX: '已灭绝', EW: '野外灭绝', CR: '极危', EN: '濒危', VU: '易危', NT: '近危', LC: '无危', DD: '数据不足', NE: '未评估'
  }
  return status ? `${status} (${map[status] || status})` : ''
}

const getPlaceholderStyle = (genusId: number) => {
  const genus = genusById.value[genusId]
  const familyId = genus?.family_id || 0
  const colors = [
    'linear-gradient(135deg, #e1ecd1 0%, #c5d9b0 100%)',
    'linear-gradient(135deg, #d1e1ec 0%, #b0c5d9 100%)',
    'linear-gradient(135deg, #ecd1e1 0%, #d9b0c5 100%)',
    'linear-gradient(135deg, #ece1d1 0%, #d9c5b0 100%)',
    'linear-gradient(135deg, #d1ece1 0%, #b0d9c5 100%)'
  ]
  return { background: colors[familyId % colors.length] }
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

const getIUCNColor = (status?: IUCNStatus) => {
  const map: Record<string, string> = {
    EX: '#60646d', EW: '#6c707b', CR: '#d64040', EN: '#e46a2f', VU: '#dc9e2c', NT: '#9ea748', LC: '#45a76f', DD: '#9399a6', NE: '#b0b5bf'
  }
  return status ? map[status] : '#b0b5bf'
}

watch(viewMode, (val) => localStorage.setItem(VIEW_MODE_KEY, val))
watch(selectedFamilyId, (v) => { if (v === 'all') selectedGenusId.value = null })

watch(filteredSpecies, (list) => {
  list.slice(0, 48).forEach(item => void ensureCoverLoaded(item.id))
}, { immediate: true })

onMounted(loadData)
onBeforeUnmount(stopLoadingFeedback)
</script>

<template>
  <div class="inat-page">
    <header class="inat-header">
      <div class="header-content">
        <p class="brand-kicker">Digital Compendium</p>
        <h1 class="brand-title">蛇类图鉴</h1>
        <p class="brand-subtitle">探索全球蛇类物种，包含分类、毒性及保护现状。点击卡片查看深度百科。</p>
      </div>
    </header>

    <div class="toolbar-sticky">
      <div class="toolbar">
        <div class="search-bar">
          <AppIcon name="search" :size="18" class="search-icon" />
          <input v-model="searchQuery" type="text" placeholder="搜索中文名、拉丁名..." />
          <button v-if="searchQuery" class="clear-search" @click="searchQuery = ''">✕</button>
        </div>
        
        <div class="toolbar-actions">
          <button class="filter-toggle" :class="{ active: activeFilterCount > 0 }" @click="isFilterPanelOpen = true">
            <span>筛选</span>
            <span v-if="activeFilterCount" class="filter-badge">{{ activeFilterCount }}</span>
          </button>
          
          <div class="view-switch">
            <button :class="{ active: viewMode === 'grid' }" @click="viewMode = 'grid'" title="网格视图">
              <AppIcon name="grid" :size="18" />
            </button>
            <button :class="{ active: viewMode === 'list' }" @click="viewMode = 'list'" title="列表视图">
              <AppIcon name="list" :size="18" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="main-container">
      <div v-if="loading" class="state-wrap">
        <div class="loader"></div>
        <p>同步数据中...</p>
      </div>

      <div v-else-if="error" class="state-wrap error">
        <p>{{ error }}</p>
        <button class="retry-btn" @click="loadData">重试</button>
      </div>

      <div v-else class="content-layout">
        <aside class="filter-panel" :class="{ open: isFilterPanelOpen }">
          <div class="filter-backdrop" @click="isFilterPanelOpen = false"></div>
          <div class="filter-sheet">
            <div class="filter-header">
              <h2>筛选条件</h2>
              <button class="close-sheet" @click="isFilterPanelOpen = false">✕</button>
            </div>
            
            <div class="filter-scroll-area">
              <div class="filter-group">
                <label>科 / 属</label>
                <div class="searchable-group">
                  <SearchableSelect
                    v-model="selectedFamilyId"
                    :options="families"
                    placeholder="全部科"
                    search-placeholder="搜索科名..."
                    allow-all
                  />
                  <SearchableSelect
                    v-model="selectedGenusId"
                    :options="filteredGenera"
                    :disabled="selectedFamilyId === 'all'"
                    :placeholder="selectedFamilyId === 'all' ? '请先选择科' : '全部属'"
                    search-placeholder="搜索属名..."
                    allow-all
                  />
                </div>
              </div>

              <div class="filter-group">
                <label>毒性等级</label>
                <div class="chip-grid">
                  <button v-for="opt in toxicityOptions" :key="opt" class="chip" :class="{ active: selectedToxicity === opt }" @click="selectedToxicity = opt">{{ opt === 'all' ? '全部' : opt }}</button>
                </div>
              </div>

              <div class="filter-group">
                <label>保护现状 (IUCN)</label>
                <div class="chip-grid">
                  <button v-for="opt in iucnOptions" :key="opt" class="chip" :class="{ active: selectedIUCN === opt }" @click="selectedIUCN = opt">{{ opt === 'all' ? '全部' : opt }}</button>
                </div>
              </div>
            </div>

            <div class="filter-footer">
              <button class="reset-btn" @click="resetFilters">清空筛选</button>
              <button class="apply-btn" @click="isFilterPanelOpen = false">查看结果</button>
            </div>
          </div>
        </aside>

        <section class="results-area">
          <div v-if="!filteredSpecies.length" class="empty-state">没有找到符合条件的物种</div>
          
          <transition-group :name="viewMode === 'grid' ? 'grid' : 'list'" tag="div" :class="viewMode === 'grid' ? 'species-grid' : 'species-list'">
            <router-link
              v-for="item in filteredSpecies"
              :key="item.id"
              :to="{ name: 'species-detail', params: { id: String(item.id) } }"
              :class="viewMode === 'grid' ? 'species-card' : 'list-row'"
            >
              <div class="media-container" :style="!getCoverUrl(item.id) ? getPlaceholderStyle(item.genus_id) : {}">
                <img v-if="getCoverUrl(item.id)" :src="getCoverUrl(item.id)" :alt="item.chinese_name" loading="lazy" />
                <div v-else class="placeholder-icon-wrap">
                  <img src="@/assets/snake-placeholder.svg" alt="Placeholder" class="placeholder-svg" />
                </div>
                <div class="badge-overlay">
                  <span v-if="item.toxicity" class="dot-badge" :style="{ backgroundColor: getToxicityColor(item.toxicity) }" :title="item.toxicity"></span>
                </div>
              </div>

              <div class="card-content">
                <div class="names-row">
                  <h3>{{ item.chinese_name }}</h3>
                  <p class="latin">{{ item.latin_name }}</p>
                </div>
                <p class="meta">
                  {{ genusById[item.genus_id]?.chinese_name || '未知属' }} · 
                  {{ familyById[genusById[item.genus_id]?.family_id || 0]?.chinese_name || '未知科' }}
                </p>
                
                <div class="tags-row">
                  <span v-if="item.iucn_status" class="iucn-tag" :style="{ color: getIUCNColor(item.iucn_status) }" :title="getIUCNFullText(item.iucn_status)">
                    {{ getIUCNFullText(item.iucn_status) }}
                  </span>
                </div>
              </div>
            </router-link>
          </transition-group>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.inat-page { min-height: 100vh; display: flex; flex-direction: column; }
.inat-header { background: var(--nav-bg); color: #fff; padding: 40px 24px; text-align: center; }
.brand-kicker { font-size: 12px; text-transform: uppercase; letter-spacing: 0.2em; color: var(--primary-color); font-weight: 700; margin-bottom: 8px; }
.brand-title { font-size: 32px; font-weight: 800; margin: 0; }
.brand-subtitle { font-size: 14px; color: var(--nav-text); margin-top: 12px; max-width: 600px; margin-left: auto; margin-right: auto; opacity: 0.8; }

.toolbar-sticky { position: sticky; top: 68px; z-index: 900; background: var(--bg-color); border-bottom: 1px solid var(--border-color); padding: 12px 0; }
.toolbar { width: min(100%, 1280px); margin: 0 auto; padding: 0 24px; display: flex; gap: 16px; align-items: center; }
.search-bar { flex: 1; height: 42px; background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; display: flex; align-items: center; padding: 0 12px; gap: 10px; box-shadow: var(--shadow-sm); }
.search-icon { color: var(--text-muted); }
.search-bar input { flex: 1; border: none; background: transparent; outline: none; font-size: 14px; color: var(--text-main); }
.clear-search { border: none; background: transparent; cursor: pointer; color: var(--text-muted); }
.toolbar-actions { display: flex; gap: 12px; }
.filter-toggle { height: 42px; padding: 0 16px; border-radius: 12px; border: 1px solid var(--border-color); background: var(--card-bg); color: var(--text-main); display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 14px; cursor: pointer; box-shadow: var(--shadow-sm); }
.filter-badge { background: var(--primary-color); color: #fff; font-size: 11px; min-width: 18px; height: 18px; border-radius: 9px; display: flex; align-items: center; justify-content: center; }
.view-switch { display: flex; background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; overflow: hidden; box-shadow: var(--shadow-sm); }
.view-switch button { width: 42px; height: 42px; border: none; background: transparent; color: var(--text-muted); cursor: pointer; display: flex; align-items: center; justify-content: center; }
.view-switch button.active { background: var(--primary-soft); color: var(--primary-color); }
.main-container { flex: 1; width: min(100%, 1280px); margin: 0 auto; padding: 24px; }

.searchable-group { display: flex; flex-direction: column; gap: 10px; }

.species-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 24px; }
.species-card { text-decoration: none; background: var(--card-bg); border-radius: 16px; overflow: hidden; border: 1px solid var(--border-color); transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.species-card:hover { transform: translateY(-4px); box-shadow: var(--shadow-md); border-color: var(--primary-color); }
.media-container { aspect-ratio: 3 / 4; position: relative; overflow: hidden; background: #eee; }
.media-container img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.5s; }
.species-card:hover .media-container img { transform: scale(1.05); }

.placeholder-icon-wrap { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; }
.placeholder-svg { width: 92%; height: 92%; object-fit: contain; opacity: 0.15; filter: grayscale(1); }

.badge-overlay { position: absolute; top: 12px; right: 12px; }
.dot-badge { width: 12px; height: 12px; border-radius: 50%; display: block; border: 2px solid #fff; }
.card-content { padding: 16px; }
.names-row h3 { margin: 0; font-size: 17px; font-weight: 800; color: var(--text-main); line-height: 1.2; }
.latin { font-size: 13px; font-style: italic; color: var(--text-muted); margin: 4px 0 0; line-height: 1.2; }
.meta { font-size: 12px; color: var(--text-muted); margin: 12px 0 0; opacity: 0.7; }
.tags-row { margin-top: 12px; display: flex; align-items: center; }
.iucn-tag { font-size: 11px; font-weight: 900; letter-spacing: 0.05em; }

.species-list { display: flex; flex-direction: column; gap: 12px; }
.list-row { display: flex; align-items: center; background: var(--card-bg); border-radius: 16px; border: 1px solid var(--border-color); text-decoration: none; overflow: hidden; padding: 12px; gap: 20px; }
.list-row .media-container { width: 80px; height: 100px; border-radius: 8px; flex-shrink: 0; }
.list-row .card-content { padding: 0; flex: 1; }
.list-row .names-row { display: flex; align-items: baseline; gap: 12px; }

.grid-enter-active, .grid-leave-active, .list-enter-active, .list-leave-active { transition: all 0.4s ease; }
.grid-enter-from, .grid-leave-to, .list-enter-from, .list-leave-to { opacity: 0; transform: scale(0.95); }

@media (max-width: 820px) {
  .filter-panel { position: fixed; inset: 0; z-index: 2000; visibility: hidden; transition: visibility 0.3s; }
  .filter-panel.open { visibility: visible; }
  .filter-backdrop { position: absolute; inset: 0; background: rgba(0,0,0,0.5); opacity: 0; transition: opacity 0.3s; }
  .filter-panel.open .filter-backdrop { opacity: 1; }
  .filter-sheet { position: absolute; bottom: 0; left: 0; right: 0; background: var(--bg-color); height: 80vh; display: flex; flex-direction: column; transform: translateY(100%); transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1); border-top-left-radius: 24px; border-top-right-radius: 24px; }
  .filter-panel.open .filter-sheet { transform: translateY(0); }
  .filter-header { padding: 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); }
  .filter-scroll-area { flex: 1; overflow-y: auto; padding: 20px; }
  .filter-footer { padding: 20px; border-top: 1px solid var(--border-color); display: grid; grid-template-columns: 1fr 1fr; gap: 12px; background: var(--card-bg); }
  .reset-btn { height: 48px; border-radius: 12px; border: 1px solid var(--border-color); background: #fff; }
  .apply-btn { height: 48px; border-radius: 12px; background: var(--primary-color); color: #fff; border: none; font-weight: 700; }
  .toolbar-sticky { top: 58px; }
}

@media (min-width: 821px) {
  .content-layout { display: grid; grid-template-columns: 280px 1fr; gap: 32px; }
  .filter-sheet { position: sticky; top: 130px; height: fit-content; }
  .filter-header, .close-sheet, .apply-btn { display: none; }
  .filter-footer { margin-top: 24px; }
  .reset-btn { width: 100%; height: 40px; border-radius: 10px; border: 1px solid var(--border-color); cursor: pointer; }
}

.filter-group { margin-bottom: 24px; }
.filter-group label { display: block; font-size: 12px; font-weight: 800; text-transform: uppercase; color: var(--text-muted); margin-bottom: 12px; }
.chip-grid { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { padding: 6px 12px; border-radius: 8px; border: 1px solid var(--border-color); background: var(--card-bg); color: var(--text-main); font-size: 13px; cursor: pointer; }
.chip.active { background: var(--primary-color); color: #fff; border-color: var(--primary-color); }

.state-wrap { min-height: 400px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; color: var(--text-muted); }
.loader { width: 40px; height: 40px; border: 3px solid #eee; border-top-color: var(--primary-color); border-radius: 50%; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
