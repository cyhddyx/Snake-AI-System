<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { speciesApi, type IUCNStatus, type Species, type ToxicityLevel } from '@/api/snake/species'
import { familiesApi, type Family } from '@/api/snake/families'
import { generaApi, type Genus } from '@/api/snake/genera'
import { speciesImagesApi } from '@/api/snake/speciesImages'
import { useAuthStore } from '@/stores/auth'
import { useFlashMessage } from '@/composables/useFlashMessage'
import AppIcon from '@/components/icons/AppIcon.vue'

const router = useRouter()
const authStore = useAuthStore()
const { error: showError } = useFlashMessage()

const loading = ref(true)
const allSpecies = ref<Species[]>([])
const families = ref<Family[]>([])
const genera = ref<Genus[]>([])
const coverImageMap = ref<Record<number, string>>({})
const imageLoadingSet = new Set<number>()

const genusById = computed(() => {
  const map = new Map<number, Genus>()
  genera.value.forEach((item) => map.set(item.id, item))
  return map
})

const familyById = computed(() => {
  const map = new Map<number, Family>()
  families.value.forEach((item) => map.set(item.id, item))
  return map
})

const favoriteSpecies = computed(() => {
  const favoriteSet = new Set(authStore.favoriteIds)
  return allSpecies.value
    .filter((item) => favoriteSet.has(item.id))
    .sort((a, b) => authStore.favoriteIds.indexOf(a.id) - authStore.favoriteIds.indexOf(b.id))
})

const loadData = async () => {
  loading.value = true
  try {
    const [speciesData, familyData, genusData] = await Promise.all([
      speciesApi.list(),
      familiesApi.list(),
      generaApi.list(),
    ])
    allSpecies.value = speciesData
    families.value = familyData
    genera.value = genusData
  } catch (err) {
    console.error('Failed to load favorites page data', err)
    showError('加载收藏页失败')
  } finally {
    loading.value = false
  }
}

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

const getIUCNText = (status?: IUCNStatus) => {
  const map: Record<IUCNStatus, string> = {
    EX: '已灭绝',
    EW: '野外灭绝',
    CR: '极危',
    EN: '濒危',
    VU: '易危',
    NT: '近危',
    LC: '无危',
    DD: '数据不足',
    NE: '未评估',
  }
  return status ? map[status] : ''
}

const getToxicityColor = (toxicity?: ToxicityLevel) => {
  switch (toxicity) {
    case '极毒':
    case '剧毒':
      return '#d64040'
    case '有毒':
      return '#dc7f2c'
    case '微毒':
      return '#b99b3a'
    case '无毒':
      return '#3f9468'
    default:
      return '#89919c'
  }
}

const openSpecies = (speciesId: number) => {
  router.push({ name: 'species-detail', params: { id: String(speciesId) } })
}

const toggleFavorite = async (speciesId: number) => {
  try {
    await authStore.syncFavorite(speciesId)
  } catch (err) {
    console.error('Failed to toggle favorite', err)
    showError('收藏同步失败')
  }
}

watch(
  favoriteSpecies,
  (list) => {
    list.forEach((item) => void ensureCoverLoaded(item.id))
  },
  { immediate: true },
)

onMounted(() => {
  void loadData()
})
</script>

<template>
  <div class="favorites-page">
    <header class="favorites-header">
      <div>
        <p class="kicker">Personal Collection</p>
        <h1>我的收藏</h1>
        <p class="subtitle">集中查看你标记过的物种，支持继续进入详情页浏览。</p>
      </div>
      <div class="header-count">
        <AppIcon name="heart" :size="16" />
        {{ favoriteSpecies.length }} 项
      </div>
    </header>

    <div v-if="loading" class="state-wrap">
      <div class="loader"></div>
      <p>正在加载收藏...</p>
    </div>

    <div v-else-if="favoriteSpecies.length === 0" class="empty-state">
      <AppIcon name="heart" :size="42" class="empty-icon" />
      <h2>你还没有收藏物种</h2>
      <p>可以去识别页或物种详情页点收藏，之后会统一出现在这里。</p>
      <button class="jump-btn" @click="router.push('/encyclopedia')">去图鉴看看</button>
    </div>

    <section v-else class="favorites-grid">
      <article v-for="item in favoriteSpecies" :key="item.id" class="favorite-card">
        <button class="card-media" type="button" @click="openSpecies(item.id)">
          <img v-if="coverImageMap[item.id]" :src="coverImageMap[item.id]" :alt="item.chinese_name" />
          <div v-else class="placeholder">暂无图片</div>
        </button>

        <div class="card-body">
          <div class="title-row">
            <div>
              <h2>{{ item.chinese_name }}</h2>
              <p class="latin">{{ item.latin_name }}</p>
            </div>
            <button class="favorite-toggle active" type="button" @click="toggleFavorite(item.id)">
              <AppIcon name="heart" :size="16" />
            </button>
          </div>

          <p class="meta">
            {{ genusById.get(item.genus_id)?.chinese_name || '未知属' }}
            ·
            {{ familyById.get(genusById.get(item.genus_id)?.family_id || 0)?.chinese_name || '未知科' }}
          </p>

          <div class="tag-row">
            <span v-if="item.toxicity" class="tag" :style="{ borderColor: getToxicityColor(item.toxicity), color: getToxicityColor(item.toxicity) }">
              {{ item.toxicity }}
            </span>
            <span v-if="item.iucn_status" class="tag neutral">
              {{ item.iucn_status }} {{ getIUCNText(item.iucn_status) }}
            </span>
          </div>

          <p v-if="item.basic_intro" class="intro">{{ item.basic_intro }}</p>

          <button class="detail-btn" type="button" @click="openSpecies(item.id)">查看详情</button>
        </div>
      </article>
    </section>
  </div>
</template>

<style scoped>
.favorites-page { max-width: 1280px; margin: 0 auto; padding: 24px; min-height: 100vh; }
.favorites-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; margin-bottom: 28px; }
.kicker { font-size: 12px; font-weight: 800; color: var(--primary-color); text-transform: uppercase; letter-spacing: 0.14em; margin: 0 0 6px; }
.favorites-header h1 { margin: 0; font-size: 30px; }
.subtitle { margin: 10px 0 0; color: var(--text-muted); max-width: 560px; line-height: 1.6; }
.header-count { display: inline-flex; align-items: center; gap: 8px; padding: 10px 14px; border-radius: 999px; background: var(--card-bg); border: 1px solid var(--border-color); font-weight: 700; color: var(--text-main); }

.favorites-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 22px; }
.favorite-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 24px; overflow: hidden; box-shadow: var(--shadow-sm); }
.card-media { width: 100%; aspect-ratio: 16 / 10; border: none; padding: 0; background: var(--bg-color); cursor: pointer; }
.card-media img { width: 100%; height: 100%; object-fit: cover; display: block; }
.placeholder { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: var(--text-muted); font-size: 14px; }
.card-body { padding: 18px; }
.title-row { display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; }
.title-row h2 { margin: 0; font-size: 21px; line-height: 1.2; }
.latin { margin: 6px 0 0; color: var(--text-muted); font-style: italic; font-size: 14px; }
.favorite-toggle { width: 40px; height: 40px; border-radius: 12px; border: 1px solid var(--border-color); background: var(--card-bg); color: var(--text-muted); cursor: pointer; flex-shrink: 0; }
.favorite-toggle.active { color: #d64040; background: #fff1f1; border-color: #f4b0b0; }
.meta { margin: 14px 0 0; color: var(--text-muted); font-size: 13px; }
.tag-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
.tag { padding: 5px 10px; border-radius: 999px; border: 1px solid currentColor; font-size: 12px; font-weight: 700; background: transparent; }
.tag.neutral { color: var(--text-main); border-color: var(--border-color); }
.intro { margin: 14px 0 0; color: var(--text-main); line-height: 1.7; font-size: 14px; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.detail-btn { margin-top: 16px; height: 40px; border-radius: 12px; border: none; background: var(--primary-color); color: #fff; padding: 0 16px; font-weight: 700; cursor: pointer; }

.state-wrap,
.empty-state { min-height: 420px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 14px; color: var(--text-muted); text-align: center; }
.empty-icon { color: #d64040; opacity: 0.7; }
.jump-btn { margin-top: 8px; height: 42px; padding: 0 18px; border-radius: 12px; border: none; background: var(--primary-color); color: #fff; font-weight: 700; cursor: pointer; }
.loader { width: 40px; height: 40px; border: 3px solid #eee; border-top-color: var(--primary-color); border-radius: 50%; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 720px) {
  .favorites-page { padding: 18px; }
  .favorites-header { flex-direction: column; }
  .favorites-grid { grid-template-columns: 1fr; }
}
</style>
