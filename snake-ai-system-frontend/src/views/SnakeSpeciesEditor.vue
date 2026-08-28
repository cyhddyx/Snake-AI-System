<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { imageServiceApi } from '@/api/imageService'
import { familiesApi, type Family } from '@/api/snake/families'
import { generaApi, type Genus } from '@/api/snake/genera'
import { speciesApi, type IUCNStatus, type Species, type SpeciesCreate, type ToxicityLevel } from '@/api/snake/species'
import { speciesContentApi, type SpeciesContentUpdate } from '@/api/snake/speciesContent'
import { speciesImagesApi, type SpeciesImage, type SpeciesImageUpdate } from '@/api/snake/speciesImages'
import { submissionsApi, type SpeciesSubmission } from '@/api/snake/submissions'
import GenusSelect from '@/components/GenusSelect.vue'
import { useFlashMessage } from '@/composables/useFlashMessage'

const route = useRoute()
const { success, error: showError } = useFlashMessage()

const isCatalogOpen = ref(true)
const activeTab = ref<'edit' | 'review' | 'families' | 'genera'>('edit')

const families = ref<Family[]>([])
const genera = ref<Genus[]>([])
const species = ref<Species[]>([])
const pendingSubmissions = ref<SpeciesSubmission[]>([])

const selectedSpeciesId = ref<number | null>(null)
const selectedSubmission = ref<SpeciesSubmission | null>(null)
const creatingSpecies = ref(false)

const detailLoading = ref(false)
const detailSaving = ref(false)
const reviewLoading = ref(false)
const reviewSubmitting = ref(false)
const imageUploading = ref(false)
const imageFileInputRef = ref<HTMLInputElement | null>(null)
let reviewRequestToken = 0

const expandedSections = ref<Set<string>>(new Set(['basic', 'taxonomy', 'content', 'images']))

const familyForm = ref({ chinese_name: '', latin_name: '', description: '' })
const editingFamilyId = ref<number | null>(null)
const familySaving = ref(false)

const genusForm = ref({ family_id: null as number | null, chinese_name: '', latin_name: '', description: '' })
const editingGenusId = ref<number | null>(null)
const genusSaving = ref(false)

const toxicityOptions: ToxicityLevel[] = ['无毒', '微毒', '有毒', '剧毒', '极毒']
const iucnOptions: { value: IUCNStatus; label: string }[] = [
  { value: 'EX', label: '已灭绝' }, { value: 'EW', label: '野外灭绝' },
  { value: 'CR', label: '极危' }, { value: 'EN', label: '濒危' },
  { value: 'VU', label: '易危' }, { value: 'NT', label: '近危' },
  { value: 'LC', label: '无危' }, { value: 'DD', label: '数据不足' },
  { value: 'NE', label: '未评估' },
]
const reviewContentLabels = {
  zoology: '动物学信息',
  history: '历史渊源',
  morphology: '形态特征',
  distribution: '地理分布',
  habitat: '栖息环境',
  behavior: '行为习性',
  reproduction: '繁殖方式',
  conservation: '保护现状',
  value: '生态与科研价值',
  hazard: '危险性说明',
} as const

type ReviewContentKey = keyof typeof reviewContentLabels

const form = ref({
  genus_id: null as number | null,
  chinese_name: '',
  latin_name: '',
  aliases: [] as string[],
  toxicity: '' as string,
  iucn_status: '' as string,
  discoverer: '',
  discover_year: '' as string,
  basic_intro: '',
})

const measurementRows = ref<Array<{ key: string; value: string }>>([])

const contentForm = ref<SpeciesContentUpdate>({})

type EditableSpeciesImage = SpeciesImage & { _editing: boolean }
type NewImageForm = {
  image_url: string
  thumbnail_url: string
  caption: string
  photographer: string
  image_type: string
  sort_order: number
  is_cover: boolean
}

const imageList = ref<Array<SpeciesImage & { _editing: boolean }>>([])
const newImage = ref<NewImageForm>({
  image_url: '', thumbnail_url: '', caption: '', photographer: '', image_type: '', sort_order: 0, is_cover: false,
})

const aliasInput = ref('')

const addAlias = () => {
  const val = aliasInput.value.trim()
  if (val && !form.value.aliases.includes(val)) {
    form.value.aliases.push(val)
    aliasInput.value = ''
  }
}

const toggleSection = (key: string) => {
  if (expandedSections.value.has(key)) expandedSections.value.delete(key)
  else expandedSections.value.add(key)
}

const addMeasurementRow = () => {
  measurementRows.value.push({ key: '', value: '' })
}

const removeMeasurementRow = (idx: number) => {
  measurementRows.value.splice(idx, 1)
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const measurementsToRecord = (): Record<string, any> | undefined => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const record: Record<string, any> = {}
  for (const row of measurementRows.value) {
    if (row.key.trim()) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let parsed: any = row.value
      if (row.value.trim() !== '' && !isNaN(Number(row.value))) {
        parsed = Number(row.value)
      }
      record[row.key.trim()] = parsed
    }
  }
  return Object.keys(record).length > 0 ? record : undefined
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const recordToRows = (record?: Record<string, any>) => {
  if (!record || typeof record !== 'object') return []
  return Object.entries(record).map(([key, value]) => ({
    key,
    value: String(value),
  }))
}

const formatDateTime = (value?: string | null) => (
  value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '未记录'
)

const getSubmissionGenus = (submission: SpeciesSubmission) => (
  genera.value.find((item) => item.id === submission.genus_id)
)

const getSubmissionFamily = (submission: SpeciesSubmission) => {
  const genus = getSubmissionGenus(submission)
  return genus ? families.value.find((item) => item.id === genus.family_id) : undefined
}

const getSubmissionTaxonomy = (submission: SpeciesSubmission) => {
  const family = getSubmissionFamily(submission)
  const genus = getSubmissionGenus(submission)
  const chineseNames = [family?.chinese_name, genus?.chinese_name].filter(Boolean)
  const latinNames = [family?.latin_name, genus?.latin_name].filter(Boolean)
  if (!chineseNames.length && !latinNames.length) return `属 #${submission.genus_id}`
  return latinNames.length
    ? `${chineseNames.join(' / ')} (${latinNames.join(' / ')})`
    : chineseNames.join(' / ')
}

const reviewMeasurementItems = computed(() => {
  const measurements = selectedSubmission.value?.measurements
  if (!measurements || typeof measurements !== 'object') return []
  return Object.entries(measurements).map(([key, value]) => ({
    key,
    value: String(value),
  }))
})

const reviewContentBlocks = computed(() => {
  const submission = selectedSubmission.value
  if (!submission) return []
  return (Object.entries(reviewContentLabels) as Array<[ReviewContentKey, string]>)
    .map(([key, label]) => ({
      key,
      label,
      value: submission[key],
    }))
    .filter((item): item is { key: ReviewContentKey; label: string; value: string } => (
      typeof item.value === 'string' && item.value.trim().length > 0
    ))
})

const resetFamilyForm = () => {
  familyForm.value = { chinese_name: '', latin_name: '', description: '' }
  editingFamilyId.value = null
}

const startEditFamily = (f: Family) => {
  editingFamilyId.value = f.id
  familyForm.value = { chinese_name: f.chinese_name, latin_name: f.latin_name, description: f.description || '' }
}

const cancelFamilyEdit = () => {
  resetFamilyForm()
}

const saveFamily = async () => {
  if (!familyForm.value.chinese_name.trim() || !familyForm.value.latin_name.trim()) {
    showError('中文名和拉丁名不能为空')
    return
  }
  familySaving.value = true
  try {
    if (editingFamilyId.value) {
      const updated = await familiesApi.update(editingFamilyId.value, familyForm.value)
      const idx = families.value.findIndex((f) => f.id === editingFamilyId.value)
      if (idx >= 0) {
        families.value[idx] = updated
      }
      success('科已更新')
    } else {
      const created = await familiesApi.create(familyForm.value)
      families.value.push(created)
      success('科已创建')
    }
    resetFamilyForm()
  } catch (err) {
    console.error(err)
    showError('保存科信息失败')
  } finally {
    familySaving.value = false
  }
}

const deleteFamily = async (id: number) => {
  if (!confirm('确定要删除该科吗？该操作可能影响下属和物种。')) return
  try {
    await familiesApi.delete(id)
    families.value = families.value.filter((f) => f.id !== id)
    success('科已删除')
  } catch (err) {
    console.error(err)
    showError('删除科失败')
  }
}

const resetGenusForm = () => {
  genusForm.value = { family_id: null, chinese_name: '', latin_name: '', description: '' }
  editingGenusId.value = null
}

const startEditGenus = (g: Genus) => {
  editingGenusId.value = g.id
  genusForm.value = { family_id: g.family_id, chinese_name: g.chinese_name, latin_name: g.latin_name, description: g.description || '' }
}

const cancelGenusEdit = () => {
  resetGenusForm()
}

const saveGenus = async () => {
  if (!genusForm.value.chinese_name.trim() || !genusForm.value.latin_name.trim()) {
    showError('中文名和拉丁名不能为空')
    return
  }
  if (!genusForm.value.family_id) {
    showError('请选择所属科')
    return
  }
  genusSaving.value = true
  try {
    if (editingGenusId.value) {
      const updateData = { ...genusForm.value, family_id: genusForm.value.family_id ?? undefined }
      const updated = await generaApi.update(editingGenusId.value, updateData)
      const idx = genera.value.findIndex((g) => g.id === editingGenusId.value)
      if (idx >= 0) {
        genera.value[idx] = updated
      }
      success('属已更新')
    } else {
      const created = await generaApi.create(genusForm.value as { family_id: number; chinese_name: string; latin_name: string; description: string })
      genera.value.push(created)
      success('属已创建')
    }
    resetGenusForm()
  } catch (err) {
    console.error(err)
    showError('保存属信息失败')
  } finally {
    genusSaving.value = false
  }
}

const deleteGenus = async (id: number) => {
  if (!confirm('确定要删除该属吗？该操作可能影响下属物种。')) return
  try {
    await generaApi.delete(id)
    genera.value = genera.value.filter((g) => g.id !== id)
    success('属已删除')
  } catch (err) {
    console.error(err)
    showError('删除属失败')
  }
}

const loadInitialData = async () => {
  try {
    const [f, g, s, sub] = await Promise.all([
      familiesApi.list(),
      generaApi.list(),
      speciesApi.list(),
      submissionsApi.list({ status: 'pending' }),
    ])
    families.value = f
    genera.value = g
    species.value = s
    pendingSubmissions.value = sub
  } catch (err) {
    console.error(err)
    showError('基础数据同步失败')
  }
}

const refreshPendingSubmissions = async () => {
  const submissions = await submissionsApi.list({ status: 'pending' })
  pendingSubmissions.value = submissions
  if (selectedSubmission.value && !submissions.some((item) => item.id === selectedSubmission.value?.id)) {
    selectedSubmission.value = null
  }
}

const loadSubmissionDetail = async (id: number) => {
  const currentToken = ++reviewRequestToken
  reviewLoading.value = true
  try {
    const submission = await submissionsApi.get(id)
    if (currentToken !== reviewRequestToken) return
    selectedSubmission.value = submission
    const idx = pendingSubmissions.value.findIndex((item) => item.id === id)
    if (idx >= 0) pendingSubmissions.value[idx] = submission
  } catch (err) {
    console.error(err)
    if (currentToken === reviewRequestToken) showError('加载投稿详情失败')
  } finally {
    if (currentToken === reviewRequestToken) reviewLoading.value = false
  }
}

const loadSpeciesDetail = async (id: number) => {
  detailLoading.value = true
  try {
    const [speciesData, contentData, imageData] = await Promise.all([
      speciesApi.get(id),
      speciesContentApi.get(id).catch(() => null),
      speciesImagesApi.list(id).catch(() => []),
    ])

    form.value = {
      genus_id: speciesData.genus_id,
      chinese_name: speciesData.chinese_name,
      latin_name: speciesData.latin_name,
      aliases: [...(speciesData.aliases || [])],
      toxicity: speciesData.toxicity || '',
      iucn_status: speciesData.iucn_status || '',
      discoverer: speciesData.discoverer || '',
      discover_year: speciesData.discover_year?.toString() || '',
      basic_intro: speciesData.basic_intro || '',
    }

    measurementRows.value = recordToRows(speciesData.measurements)

    contentForm.value = contentData
      ? {
          zoology: contentData.zoology || '',
          history: contentData.history || '',
          morphology: contentData.morphology || '',
          distribution: contentData.distribution || '',
          habitat: contentData.habitat || '',
          behavior: contentData.behavior || '',
          reproduction: contentData.reproduction || '',
          conservation: contentData.conservation || '',
          value: contentData.value || '',
          hazard: contentData.hazard || '',
        }
      : {}

    imageList.value = imageData.map((img) => ({ ...img, _editing: false }))
  } catch (err) {
    console.error(err)
    showError('加载物种详情失败')
  } finally {
    detailLoading.value = false
  }
}

const resetEditor = () => {
  form.value = {
    genus_id: null, chinese_name: '', latin_name: '', aliases: [],
    toxicity: '', iucn_status: '', discoverer: '', discover_year: '', basic_intro: '',
  }
  measurementRows.value = []
  contentForm.value = {}
  imageList.value = []
  newImage.value = { image_url: '', thumbnail_url: '', caption: '', photographer: '', image_type: '', sort_order: 0, is_cover: false }
}

const startCreateSpecies = () => {
  creatingSpecies.value = true
  selectedSpeciesId.value = null
  activeTab.value = 'edit'
  resetEditor()
}

const normalizeImageList = (images: EditableSpeciesImage[]) => {
  const coverIndex = images.findIndex((item) => item.is_cover)
  return images.map((item, index) => ({
    ...item,
    sort_order: index,
    image_type: item.image_type || 'gallery',
    is_cover: coverIndex >= 0 ? index === coverIndex : index === 0,
  }))
}

const resetNewImage = () => {
  newImage.value = { image_url: '', thumbnail_url: '', caption: '', photographer: '', image_type: '', sort_order: 0, is_cover: false }
}

const saveSpecies = async () => {
  if (!selectedSpeciesId.value && !creatingSpecies.value) return
  if (!form.value.chinese_name.trim()) {
    showError('物种中文名不能为空')
    return
  }
  if (!form.value.genus_id) {
    showError('请选择所属属')
    return
  }

  detailSaving.value = true
  try {
    const speciesUpdate: SpeciesCreate = {
      genus_id: form.value.genus_id,
      chinese_name: form.value.chinese_name,
      latin_name: form.value.latin_name,
      aliases: form.value.aliases,
      basic_intro: form.value.basic_intro || undefined,
      measurements: measurementsToRecord(),
    }
    if (form.value.toxicity) speciesUpdate.toxicity = form.value.toxicity as ToxicityLevel
    if (form.value.iucn_status) speciesUpdate.iucn_status = form.value.iucn_status as IUCNStatus
    if (form.value.discoverer) speciesUpdate.discoverer = form.value.discoverer
    if (form.value.discover_year) speciesUpdate.discover_year = Number(form.value.discover_year)

    let currentSpeciesId = selectedSpeciesId.value
    if (creatingSpecies.value) {
      const createdSpecies = await speciesApi.create(speciesUpdate)
      currentSpeciesId = createdSpecies.id
      selectedSpeciesId.value = createdSpecies.id
      species.value.push(createdSpecies)
      species.value.sort((a, b) => (
        a.chinese_name.localeCompare(b.chinese_name, 'zh-CN') ||
        a.latin_name.localeCompare(b.latin_name, 'en') ||
        a.id - b.id
      ))
    } else {
      await speciesApi.update(selectedSpeciesId.value!, speciesUpdate)
    }

    const contentUpdate: SpeciesContentUpdate = {}
    let hasContent = false
    for (const key of ['zoology', 'history', 'morphology', 'distribution', 'habitat', 'behavior', 'reproduction', 'conservation', 'value', 'hazard'] as const) {
      if (contentForm.value[key] !== undefined && contentForm.value[key] !== '') {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (contentUpdate as any)[key] = contentForm.value[key]
        hasContent = true
      }
    }
    if (hasContent) {
      if (creatingSpecies.value) {
        await speciesContentApi.create(currentSpeciesId!, contentUpdate)
      } else {
        await speciesContentApi.update(currentSpeciesId!, contentUpdate)
      }
    }

    const idx = species.value.findIndex((s) => s.id === currentSpeciesId)
    if (idx >= 0) {
      const current = species.value[idx]
      if (current) {
        species.value[idx] = {
          ...current,
          genus_id: form.value.genus_id,
          chinese_name: form.value.chinese_name,
          latin_name: form.value.latin_name,
          aliases: form.value.aliases,
          toxicity: form.value.toxicity ? form.value.toxicity as ToxicityLevel : undefined,
          iucn_status: form.value.iucn_status ? form.value.iucn_status as IUCNStatus : undefined,
          discoverer: form.value.discoverer || undefined,
          discover_year: form.value.discover_year ? Number(form.value.discover_year) : undefined,
          basic_intro: form.value.basic_intro || undefined,
          measurements: measurementsToRecord(),
        }
      }
    }

    creatingSpecies.value = false
    success(currentSpeciesId === selectedSpeciesId.value && !creatingSpecies.value ? '保存成功' : '物种已创建')
  } catch (err) {
    console.error(err)
    showError(creatingSpecies.value ? '创建物种失败' : '保存失败')
  } finally {
    detailSaving.value = false
  }
}

const addImage = async () => {
  if (!selectedSpeciesId.value || !newImage.value.image_url.trim()) return
  try {
    const created = await speciesImagesApi.create(selectedSpeciesId.value, {
      image_url: newImage.value.image_url,
      thumbnail_url: newImage.value.thumbnail_url || undefined,
      caption: newImage.value.caption || undefined,
      photographer: newImage.value.photographer || undefined,
      image_type: newImage.value.image_type || undefined,
      sort_order: newImage.value.sort_order || undefined,
      is_cover: newImage.value.is_cover || undefined,
    })
    imageList.value.push({ ...created, _editing: false })
    imageList.value = normalizeImageList(imageList.value)
    resetNewImage()
    success('图片已添加')
  } catch (err) {
    console.error(err)
    showError('添加图片失败')
  }
}

const openImagePicker = () => {
  if (!selectedSpeciesId.value || imageUploading.value) return
  imageFileInputRef.value?.click()
}

const uploadNewImageFile = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    showError('只能上传图片文件')
    if (imageFileInputRef.value) imageFileInputRef.value.value = ''
    return
  }

  imageUploading.value = true
  try {
    const asset = await imageServiceApi.upload(file)
    newImage.value.image_url = asset.url
    if (!newImage.value.thumbnail_url) newImage.value.thumbnail_url = asset.url
    success('图片上传成功')
  } catch (err) {
    console.error(err)
    showError('图片上传失败，请先启动 E:\\Project\\Snake-AI-System\\image\\server.py')
  } finally {
    imageUploading.value = false
    if (imageFileInputRef.value) imageFileInputRef.value.value = ''
  }
}

const updateImage = async (img: EditableSpeciesImage) => {
  try {
    const update: SpeciesImageUpdate = {
      image_url: img.image_url,
      caption: img.caption || undefined,
      photographer: img.photographer || undefined,
      image_type: img.image_type || undefined,
      sort_order: img.sort_order,
      is_cover: img.is_cover,
    }
    if (img.thumbnail_url) update.thumbnail_url = img.thumbnail_url
    const updated = await speciesImagesApi.update(img.id, update)
    const idx = imageList.value.findIndex((i) => i.id === img.id)
    if (idx >= 0) {
      imageList.value[idx] = { ...updated, _editing: false }
      imageList.value = normalizeImageList(imageList.value)
    }
    success('图片已更新')
  } catch (err) {
    console.error(err)
    showError('更新图片失败')
  }
}

const deleteImage = async (imgId: number) => {
  try {
    await speciesImagesApi.delete(imgId)
    imageList.value = normalizeImageList(imageList.value.filter((i) => i.id !== imgId))
    success('图片已删除')
  } catch (err) {
    console.error(err)
    showError('删除图片失败')
  }
}

const toggleCatalog = () => { isCatalogOpen.value = !isCatalogOpen.value }

const selectSpecies = (id: number) => {
  creatingSpecies.value = false
  selectedSpeciesId.value = id
  activeTab.value = 'edit'
}

const selectReview = async (sub: SpeciesSubmission) => {
  selectedSubmission.value = sub
  activeTab.value = 'review'
  await loadSubmissionDetail(sub.id)
}

const handleApprove = async () => {
  if (!selectedSubmission.value || reviewSubmitting.value) return
  const confirmed = window.confirm(`确认通过投稿「${selectedSubmission.value.chinese_name}」吗？`)
  if (!confirmed) return

  reviewSubmitting.value = true
  try {
    await submissionsApi.approve(selectedSubmission.value.id, {})
    selectedSubmission.value = null
    await loadInitialData()
    success('投稿已通过审核')
  } catch (err) {
    console.error(err)
    showError('投稿审核失败')
  } finally {
    reviewSubmitting.value = false
  }
}

const handleReject = async () => {
  if (!selectedSubmission.value || reviewSubmitting.value) return
  const reviewNote = window.prompt('可填写驳回原因（可留空）', '')
  if (reviewNote === null) return

  reviewSubmitting.value = true
  try {
    await submissionsApi.reject(
      selectedSubmission.value.id,
      reviewNote.trim() ? { review_note: reviewNote.trim() } : {},
    )
    selectedSubmission.value = null
    await loadInitialData()
    success('投稿已驳回')
  } catch (err) {
    console.error(err)
    showError('驳回投稿失败')
  } finally {
    reviewSubmitting.value = false
  }
}

watch(selectedSpeciesId, (id) => {
  if (id) loadSpeciesDetail(id)
  else if (!creatingSpecies.value) resetEditor()
})

watch(activeTab, (tab) => {
  if (tab !== 'review') return
  refreshPendingSubmissions().catch((err) => {
    console.error(err)
    showError('待审投稿刷新失败')
  })
})

watch(() => route.query.id, (id) => {
  const parsed = id ? Number(id) : null
  if (parsed && Number.isInteger(parsed) && parsed > 0) {
    selectedSpeciesId.value = parsed
    activeTab.value = 'edit'
  }
}, { immediate: true })

onMounted(loadInitialData)
</script>

<template>
  <div class="editor-page" :class="{ 'catalog-closed': !isCatalogOpen }">
    <aside class="catalog-sidebar">
      <header class="sidebar-header">
        <h2>物种目录</h2>
        <button class="icon-btn" @click="toggleCatalog">◂</button>
      </header>
      
      <div class="catalog-scroll">
        <div v-for="f in families" :key="f.id" class="family-group">
          <div class="f-name">{{ f.chinese_name }}</div>
          <div v-for="g in genera.filter(i => i.family_id === f.id)" :key="g.id" class="genus-group">
            <div class="g-name">{{ g.chinese_name }}</div>
            <div 
              v-for="s in species.filter(i => i.genus_id === g.id)" 
              :key="s.id" 
              class="species-item"
              :class="{ active: selectedSpeciesId === s.id }"
              @click="selectSpecies(s.id)"
            >
              {{ s.chinese_name }}
              <span class="latin-small">{{ s.latin_name }}</span>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <main class="workspace">
      <nav class="workspace-tabs">
        <button :class="{ active: activeTab === 'edit' }" @click="activeTab = 'edit'">
          物种编辑 {{ creatingSpecies ? '(新建)' : (selectedSpeciesId ? `(#${selectedSpeciesId})` : '') }}
        </button>
        <button :class="{ active: activeTab === 'review' }" @click="activeTab = 'review'">
          待审投稿 <span v-if="pendingSubmissions.length" class="count">{{ pendingSubmissions.length }}</span>
        </button>
        <button :class="{ active: activeTab === 'families' }" @click="activeTab = 'families'">
          科管理
        </button>
        <button :class="{ active: activeTab === 'genera' }" @click="activeTab = 'genera'">
          属管理
        </button>
        <button class="new-species-btn" @click="startCreateSpecies">+ 新建物种</button>
        <button v-if="!isCatalogOpen" class="open-catalog-btn" @click="toggleCatalog">展开目录 ▸</button>
      </nav>

      <div class="tab-content">
        <section v-if="activeTab === 'edit'" class="edit-module">
          <div v-if="!selectedSpeciesId && !creatingSpecies" class="module-placeholder">
            <div class="icon">📝</div>
            <p>从左侧目录选择一个物种进行编辑</p>
          </div>

          <div v-else-if="detailLoading && !creatingSpecies" class="module-placeholder">
            <div class="loader"></div>
            <p>加载中...</p>
          </div>

          <div v-else class="editor-scroll">
            <!-- Card 1: Basic -->
            <section class="form-card" :class="{ collapsed: !expandedSections.has('basic') }">
              <header class="card-header" @click="toggleSection('basic')">
                <div class="header-title">
                  <span class="step-num">1</span>
                  <h3>基础分类信息</h3>
                </div>
                <span class="chevron">{{ expandedSections.has('basic') ? '▲' : '▼' }}</span>
              </header>
              <div v-if="expandedSections.has('basic')" class="card-body">
                <div class="form-grid">
                  <label class="field">
                    <span>中文名 *</span>
                    <input v-model="form.chinese_name" type="text" placeholder="如：玉斑锦蛇" />
                  </label>
                  <label class="field">
                    <span>拉丁名</span>
                    <input v-model="form.latin_name" type="text" placeholder="如：Euprepiophis mandarinus" />
                  </label>
                  <div class="field full">
                    <span>所属科属</span>
                    <GenusSelect v-model="form.genus_id" :genera="genera" :families="families" placeholder="搜索科或属..." />
                  </div>
                  <div class="field full">
                    <span>别名</span>
                    <div class="tag-input">
                      <span v-for="a in form.aliases" :key="a" class="alias-tag">{{ a }} <button @click="form.aliases = form.aliases.filter(i => i !== a)">×</button></span>
                      <input v-model="aliasInput" @keydown.enter.prevent="addAlias" placeholder="按回车添加" />
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <!-- Card 2: Taxonomy & Protection -->
            <section class="form-card" :class="{ collapsed: !expandedSections.has('taxonomy') }">
              <header class="card-header" @click="toggleSection('taxonomy')">
                <div class="header-title">
                  <span class="step-num">2</span>
                  <h3>分类与保护</h3>
                </div>
                <span class="chevron">{{ expandedSections.has('taxonomy') ? '▲' : '▼' }}</span>
              </header>
              <div v-if="expandedSections.has('taxonomy')" class="card-body">
                <div class="form-grid">
                  <label class="field">
                    <span>毒性</span>
                    <select v-model="form.toxicity" class="select-input">
                      <option value="">未指定</option>
                      <option v-for="opt in toxicityOptions" :key="opt" :value="opt">{{ opt }}</option>
                    </select>
                  </label>
                  <label class="field">
                    <span>IUCN 保护状态</span>
                    <select v-model="form.iucn_status" class="select-input">
                      <option value="">未指定</option>
                      <option v-for="opt in iucnOptions" :key="opt.value" :value="opt.value">{{ opt.value }} - {{ opt.label }}</option>
                    </select>
                  </label>
                  <label class="field">
                    <span>发现者</span>
                    <input v-model="form.discoverer" type="text" placeholder="命名者" />
                  </label>
                  <label class="field">
                    <span>发现年份</span>
                    <input v-model="form.discover_year" type="number" placeholder="如：1864" />
                  </label>
                  <div class="field full">
                    <span>简评 (Abstract)</span>
                    <textarea v-model="form.basic_intro" placeholder="一句话描述该物种的核心特征..."></textarea>
                  </div>
                  <div class="field full">
                    <span>度量数据 (Measurements)</span>
                    <div class="kv-editor">
                      <div v-for="(row, idx) in measurementRows" :key="idx" class="kv-row">
                        <input v-model="row.key" type="text" placeholder="属性名" class="kv-key" />
                        <input v-model="row.value" type="text" placeholder="属性值" class="kv-value" />
                        <button class="kv-remove" @click="removeMeasurementRow(idx)">✕</button>
                      </div>
                      <button class="kv-add" @click="addMeasurementRow">+ 添加属性</button>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <!-- Card 3: Content -->
            <section class="form-card" :class="{ collapsed: !expandedSections.has('content') }">
              <header class="card-header" @click="toggleSection('content')">
                <div class="header-title">
                  <span class="step-num">3</span>
                  <h3>百科内容</h3>
                </div>
                <span class="chevron">{{ expandedSections.has('content') ? '▲' : '▼' }}</span>
              </header>
              <div v-if="expandedSections.has('content')" class="card-body">
                <div class="textarea-grid">
                  <label class="field"><span>动物学</span><textarea v-model="contentForm.zoology"></textarea></label>
                  <label class="field"><span>分类历史</span><textarea v-model="contentForm.history"></textarea></label>
                  <label class="field"><span>形态特征</span><textarea v-model="contentForm.morphology"></textarea></label>
                  <label class="field"><span>分布地区</span><textarea v-model="contentForm.distribution"></textarea></label>
                  <label class="field"><span>栖息环境</span><textarea v-model="contentForm.habitat"></textarea></label>
                  <label class="field"><span>行为习性</span><textarea v-model="contentForm.behavior"></textarea></label>
                  <label class="field"><span>繁殖</span><textarea v-model="contentForm.reproduction"></textarea></label>
                  <label class="field"><span>保护状况</span><textarea v-model="contentForm.conservation"></textarea></label>
                  <label class="field"><span>价值</span><textarea v-model="contentForm.value"></textarea></label>
                  <label class="field"><span>危险性</span><textarea v-model="contentForm.hazard"></textarea></label>
                </div>
              </div>
            </section>

            <!-- Card 4: Images -->
            <section class="form-card" :class="{ collapsed: !expandedSections.has('images') }">
              <header class="card-header" @click="toggleSection('images')">
                <div class="header-title">
                  <span class="step-num">4</span>
                  <h3>图片管理</h3>
                  <span v-if="imageList.length" class="count-tag">{{ imageList.length }} 张</span>
                </div>
                <span class="chevron">{{ expandedSections.has('images') ? '▲' : '▼' }}</span>
              </header>
              <div v-if="expandedSections.has('images')" class="card-body">
                <div v-if="imageList.length === 0" class="empty-hint">暂无图片，使用下方表单添加</div>
                <div v-else class="image-list">
                  <div v-for="img in imageList" :key="img.id" class="image-row">
                    <div class="image-thumb">
                      <img :src="img.thumbnail_url || img.image_url" alt="" />
                      <span v-if="img.is_cover" class="cover-badge">封面</span>
                    </div>
                    <div v-if="!img._editing" class="image-info">
                      <span class="img-filename">{{ img.caption || '无说明' }}</span>
                      <span class="img-meta">{{ img.photographer || '' }} {{ img.image_type || '' }}</span>
                    </div>
                    <div v-else class="image-edit-grid">
                      <label class="mini-field"><span>图片URL</span><input v-model="img.image_url" /></label>
                      <label class="mini-field"><span>缩略图URL</span><input v-model="img.thumbnail_url" /></label>
                      <label class="mini-field"><span>说明</span><input v-model="img.caption" /></label>
                      <label class="mini-field"><span>摄影师</span><input v-model="img.photographer" /></label>
                      <label class="mini-field"><span>类型</span><input v-model="img.image_type" /></label>
                      <label class="mini-field"><span>排序</span><input v-model.number="img.sort_order" type="number" /></label>
                      <label class="mini-field check-field"><input v-model="img.is_cover" type="checkbox" /><span>设为封面</span></label>
                    </div>
                    <div class="image-actions">
                      <button v-if="!img._editing" class="img-btn edit" @click="img._editing = true">编辑</button>
                      <button v-else class="img-btn save" @click="updateImage(img)">保存</button>
                      <button v-if="img._editing" class="img-btn cancel" @click="img._editing = false; loadSpeciesDetail(selectedSpeciesId!)">取消</button>
                      <button class="img-btn del" @click="deleteImage(img.id)">删除</button>
                    </div>
                  </div>
                </div>

                <div class="add-image-section">
                  <h4>添加新图片</h4>
                  <input ref="imageFileInputRef" type="file" accept="image/*" hidden @change="uploadNewImageFile" />
                  <p class="section-tip">先上传本地图片，服务会自动生成可用 URL；也可以手动调整说明、摄影师和排序。</p>
                  <div class="image-upload-actions">
                    <button class="upload-image-btn" type="button" :disabled="imageUploading || !selectedSpeciesId" @click="openImagePicker">
                      {{ imageUploading ? '上传中...' : '上传本地图片' }}
                    </button>
                    <span class="upload-url-preview">{{ newImage.image_url || '上传后会自动填充图片 URL' }}</span>
                  </div>
                  <div class="add-image-grid">
                    <label class="mini-field"><span>图片URL *</span><input v-model="newImage.image_url" placeholder="上传后自动填充" /></label>
                    <label class="mini-field"><span>缩略图URL</span><input v-model="newImage.thumbnail_url" /></label>
                    <label class="mini-field"><span>说明</span><input v-model="newImage.caption" /></label>
                    <label class="mini-field"><span>摄影师</span><input v-model="newImage.photographer" /></label>
                    <label class="mini-field"><span>类型</span><input v-model="newImage.image_type" placeholder="如：wild, captive" /></label>
                    <label class="mini-field"><span>排序</span><input v-model.number="newImage.sort_order" type="number" /></label>
                    <label class="mini-field check-field"><input v-model="newImage.is_cover" type="checkbox" /><span>设为封面</span></label>
                  </div>
                  <button class="add-image-submit" :disabled="!newImage.image_url.trim() || imageUploading" @click="addImage">添加图片</button>
                </div>
              </div>
            </section>

            <div class="form-footer">
              <button class="save-btn" :disabled="detailSaving" @click="saveSpecies">
                {{ detailSaving ? (creatingSpecies ? '创建中...' : '保存中...') : (creatingSpecies ? '创建物种' : '保存全部修改') }}
              </button>
              <button class="reset-btn" @click="creatingSpecies ? startCreateSpecies() : (selectedSpeciesId && loadSpeciesDetail(selectedSpeciesId))">放弃修改</button>
            </div>
          </div>
        </section>

        <section v-if="activeTab === 'review'" class="review-module">
          <div class="review-layout">
            <div class="pending-list">
              <div v-if="!pendingSubmissions.length" class="empty-hint">暂无待审投稿</div>
              <div 
                v-for="sub in pendingSubmissions" 
                :key="sub.id" 
                class="review-sub-card"
                :class="{ active: selectedSubmission?.id === sub.id }"
                @click="selectReview(sub)"
              >
                <div class="review-card-head">
                  <strong>{{ sub.chinese_name }}</strong>
                  <span class="review-kind">{{ sub.target_species_id ? '纠错投稿' : '新物种投稿' }}</span>
                </div>
                <span class="review-card-subline">{{ sub.latin_name || '未填写拉丁名' }}</span>
                <span class="review-card-meta">
                  提交者 #{{ sub.submitter_id }} · {{ formatDateTime(sub.updated_at || sub.created_at) }}
                </span>
              </div>
            </div>
            
            <div class="review-detail">
              <div v-if="!selectedSubmission" class="module-placeholder">选择一条投稿进行审核</div>
              <div v-else-if="reviewLoading" class="module-placeholder">
                <div class="loader"></div>
                <p>投稿详情加载中...</p>
              </div>
              <div v-else class="review-panel-card">
                <div class="review-header">
                  <div>
                    <h3>审核详情：{{ selectedSubmission.chinese_name }}</h3>
                    <p class="review-subtitle">
                      {{ selectedSubmission.target_species_id ? `纠错目标物种 #${selectedSubmission.target_species_id}` : '新物种投稿' }}
                      · 最近更新 {{ formatDateTime(selectedSubmission.updated_at) }}
                    </p>
                  </div>
                  <div class="review-actions">
                    <button class="reject-btn" :disabled="reviewSubmitting" @click="handleReject">拒绝</button>
                    <button class="approve-btn" :disabled="reviewSubmitting" @click="handleApprove">批准通过</button>
                  </div>
                </div>

                <div class="review-scroll-area">
                  <section class="review-section">
                    <h4>基础信息</h4>
                    <div class="review-meta-grid">
                      <div class="meta-card">
                        <span>中文名</span>
                        <strong>{{ selectedSubmission.chinese_name }}</strong>
                      </div>
                      <div class="meta-card">
                        <span>拉丁名</span>
                        <strong>{{ selectedSubmission.latin_name || '未填写' }}</strong>
                      </div>
                      <div class="meta-card">
                        <span>所属分类</span>
                        <strong>{{ getSubmissionTaxonomy(selectedSubmission) }}</strong>
                      </div>
                      <div class="meta-card">
                        <span>投稿类型</span>
                        <strong>{{ selectedSubmission.target_species_id ? '纠错投稿' : '新物种投稿' }}</strong>
                      </div>
                      <div class="meta-card">
                        <span>提交者</span>
                        <strong>#{{ selectedSubmission.submitter_id }}</strong>
                      </div>
                      <div class="meta-card">
                        <span>内容格式</span>
                        <strong>{{ selectedSubmission.content_format }}</strong>
                      </div>
                      <div class="meta-card">
                        <span>毒性</span>
                        <strong>{{ selectedSubmission.toxicity || '未填写' }}</strong>
                      </div>
                      <div class="meta-card">
                        <span>IUCN 状态</span>
                        <strong>{{ selectedSubmission.iucn_status || '未填写' }}</strong>
                      </div>
                      <div class="meta-card">
                        <span>发现者</span>
                        <strong>{{ selectedSubmission.discoverer || '未填写' }}</strong>
                      </div>
                      <div class="meta-card">
                        <span>发现年份</span>
                        <strong>{{ selectedSubmission.discover_year || '未填写' }}</strong>
                      </div>
                      <div class="meta-card wide">
                        <span>别名</span>
                        <div v-if="selectedSubmission.aliases?.length" class="review-tag-list">
                          <span v-for="alias in selectedSubmission.aliases" :key="alias" class="review-tag">{{ alias }}</span>
                        </div>
                        <p v-else class="review-text">未填写</p>
                      </div>
                      <div v-if="selectedSubmission.basic_intro" class="meta-card wide">
                        <span>物种简评</span>
                        <p class="review-text">{{ selectedSubmission.basic_intro }}</p>
                      </div>
                    </div>
                  </section>

                  <section v-if="reviewMeasurementItems.length" class="review-section">
                    <h4>度量数据</h4>
                    <div class="measurement-list">
                      <div v-for="item in reviewMeasurementItems" :key="item.key" class="measurement-item">
                        <span class="measurement-key">{{ item.key }}</span>
                        <strong class="measurement-value">{{ item.value }}</strong>
                      </div>
                    </div>
                  </section>

                  <section class="review-section">
                    <h4>图片资料</h4>
                    <div v-if="selectedSubmission.images.length" class="image-carousel">
                      <div v-for="(img, idx) in selectedSubmission.images" :key="idx" class="carousel-item">
                        <img :src="img.thumbnail_url || img.image_url" />
                        <p>{{ img.caption || '未填写说明' }}</p>
                      </div>
                    </div>
                    <div v-else class="empty-hint">投稿中未上传图片</div>
                  </section>

                  <section class="review-section">
                    <h4>百科内容</h4>
                    <div v-if="reviewContentBlocks.length" class="review-content-blocks">
                      <div v-for="block in reviewContentBlocks" :key="block.key" class="content-block">
                        <h5>{{ block.label }}</h5>
                        <p class="review-text">{{ block.value }}</p>
                      </div>
                    </div>
                    <div v-else class="empty-hint">投稿中未填写详细百科内容</div>
                  </section>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section v-if="activeTab === 'families'" class="manage-module">
          <div class="manage-layout">
            <div class="manage-form-card">
              <h3>{{ editingFamilyId ? '编辑科' : '新增科' }}</h3>
              <div class="manage-form-grid">
                <label class="field">
                  <span>中文名 *</span>
                  <input v-model="familyForm.chinese_name" type="text" placeholder="如：游蛇科" />
                </label>
                <label class="field">
                  <span>拉丁名 *</span>
                  <input v-model="familyForm.latin_name" type="text" placeholder="如：Colubridae" />
                </label>
                <label class="field full">
                  <span>描述</span>
                  <textarea v-model="familyForm.description" placeholder="科的特征描述（可选）"></textarea>
                </label>
              </div>
              <div class="manage-form-actions">
                <button class="save-btn" :disabled="familySaving" @click="saveFamily">
                  {{ familySaving ? '保存中...' : (editingFamilyId ? '更新科' : '创建科') }}
                </button>
                <button v-if="editingFamilyId" class="reset-btn" @click="cancelFamilyEdit">取消编辑</button>
              </div>
            </div>
            <div class="manage-list">
              <div v-if="!families.length" class="empty-hint">暂无科数据</div>
              <div v-for="f in families" :key="f.id" class="manage-item" :class="{ active: editingFamilyId === f.id }">
                <div class="manage-item-info">
                  <strong>{{ f.chinese_name }}</strong>
                  <span class="latin-small">{{ f.latin_name }}</span>
                  <span v-if="f.description" class="desc-preview">{{ f.description }}</span>
                </div>
                <div class="manage-item-actions">
                  <button class="img-btn edit" @click="startEditFamily(f)">编辑</button>
                  <button class="img-btn del" @click="deleteFamily(f.id)">删除</button>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section v-if="activeTab === 'genera'" class="manage-module">
          <div class="manage-layout">
            <div class="manage-form-card">
              <h3>{{ editingGenusId ? '编辑属' : '新增属' }}</h3>
              <div class="manage-form-grid">
                <label class="field full">
                  <span>所属科 *</span>
                  <select v-model="genusForm.family_id" class="select-input">
                    <option :value="null" disabled>请选择科...</option>
                    <option v-for="f in families" :key="f.id" :value="f.id">{{ f.chinese_name }} ({{ f.latin_name }})</option>
                  </select>
                </label>
                <label class="field">
                  <span>中文名 *</span>
                  <input v-model="genusForm.chinese_name" type="text" placeholder="如：锦蛇属" />
                </label>
                <label class="field">
                  <span>拉丁名 *</span>
                  <input v-model="genusForm.latin_name" type="text" placeholder="如：Euprepiophis" />
                </label>
                <label class="field full">
                  <span>描述</span>
                  <textarea v-model="genusForm.description" placeholder="属的特征描述（可选）"></textarea>
                </label>
              </div>
              <div class="manage-form-actions">
                <button class="save-btn" :disabled="genusSaving" @click="saveGenus">
                  {{ genusSaving ? '保存中...' : (editingGenusId ? '更新属' : '创建属') }}
                </button>
                <button v-if="editingGenusId" class="reset-btn" @click="cancelGenusEdit">取消编辑</button>
              </div>
            </div>
            <div class="manage-list">
              <div v-if="!genera.length" class="empty-hint">暂无属数据</div>
              <div v-for="f in families" :key="'f-' + f.id">
                <div v-for="g in genera.filter(i => i.family_id === f.id)" :key="g.id" class="manage-item" :class="{ active: editingGenusId === g.id }">
                  <div class="manage-item-info">
                    <strong>{{ g.chinese_name }}</strong>
                    <span class="latin-small">{{ g.latin_name }}</span>
                    <span class="family-tag">{{ f.chinese_name }}</span>
                    <span v-if="g.description" class="desc-preview">{{ g.description }}</span>
                  </div>
                  <div class="manage-item-actions">
                    <button class="img-btn edit" @click="startEditGenus(g)">编辑</button>
                    <button class="img-btn del" @click="deleteGenus(g.id)">删除</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<style scoped>
.editor-page { display: flex; height: calc(100vh - 68px); overflow: hidden; background: var(--bg-color); }

.catalog-sidebar { width: 320px; background: var(--card-bg); border-right: 1px solid var(--border-color); display: flex; flex-direction: column; transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.editor-page.catalog-closed .catalog-sidebar { transform: translateX(-100%); position: absolute; }

.sidebar-header { padding: 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); }
.sidebar-header h2 { margin: 0; font-size: 16px; }
.icon-btn { background: none; border: 1px solid var(--border-color); border-radius: 8px; cursor: pointer; padding: 4px 10px; font-size: 14px; }
.catalog-scroll { flex: 1; overflow-y: auto; padding: 12px; }

.f-name { font-size: 11px; font-weight: 800; text-transform: uppercase; color: var(--text-muted); padding: 12px 8px 4px; }
.g-name { font-size: 12px; font-weight: 700; color: var(--primary-color); padding: 8px 12px; opacity: 0.8; }
.species-item { padding: 10px 16px; border-radius: 8px; font-size: 14px; cursor: pointer; display: flex; flex-direction: column; gap: 2px; }
.species-item:hover { background: var(--bg-color); }
.species-item.active { background: var(--primary-soft); color: var(--primary-dark); font-weight: 700; }
.latin-small { font-size: 11px; font-style: italic; opacity: 0.6; }

.workspace { flex: 1; display: flex; flex-direction: column; min-width: 0; height: 100%; }
.workspace-tabs { background: var(--card-bg); border-bottom: 1px solid var(--border-color); padding: 0 20px; display: flex; gap: 4px; height: 50px; align-items: flex-end; flex-shrink: 0; }
.workspace-tabs button { padding: 0 20px; height: 40px; border: 1px solid transparent; border-bottom: none; background: transparent; cursor: pointer; font-size: 13px; font-weight: 600; border-top-left-radius: 10px; border-top-right-radius: 10px; }
.workspace-tabs button.active { background: var(--bg-color); border-color: var(--border-color); color: var(--primary-color); }
.workspace-tabs .count { background: #d64040; color: #fff; padding: 1px 6px; border-radius: 10px; font-size: 10px; margin-left: 4px; }
.new-species-btn { margin-left: auto; border: 1px solid var(--border-color) !important; border-bottom: 1px solid var(--border-color) !important; border-radius: 10px !important; height: 34px !important; align-self: center; background: var(--card-bg) !important; color: var(--text-main); }
.open-catalog-btn { margin-left: auto; align-self: center; height: 32px !important; border: 1px solid var(--border-color) !important; padding: 0 12px !important; border-radius: 8px !important; }

.tab-content { flex: 1; overflow: hidden; display: flex; flex-direction: column; min-height: 0; }

.edit-module { flex: 1; display: flex; flex-direction: column; min-height: 0; }

.editor-scroll { flex: 1; overflow-y: auto; padding: 24px; max-width: 900px; }

.form-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 20px; overflow: hidden; margin-bottom: 20px; box-shadow: var(--shadow-sm); }
.card-header { padding: 20px 24px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; }
.header-title { display: flex; align-items: center; gap: 16px; }
.step-num { width: 28px; height: 28px; border-radius: 50%; background: var(--primary-soft); color: var(--primary-color); display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 14px; }
.card-header h3 { margin: 0; font-size: 16px; }
.chevron { font-size: 12px; color: var(--text-muted); }
.card-body { padding: 0 24px 24px; border-top: 1px solid var(--bg-color); }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; padding-top: 20px; }
.field { display: flex; flex-direction: column; gap: 8px; }
.field.full { grid-column: span 2; }
.field span { font-size: 13px; font-weight: 700; color: var(--text-muted); }
.field input, .field textarea, .field select { background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 12px; padding: 12px; font-size: 14px; color: var(--text-main); outline: none; font-family: inherit; }
.field input:focus, .field textarea:focus, .field select:focus { border-color: var(--primary-color); }
.field textarea { min-height: 100px; resize: vertical; }
.select-input { appearance: auto; }

.tag-input { display: flex; flex-wrap: wrap; gap: 8px; background: var(--bg-color); padding: 8px; border-radius: 12px; border: 1.5px solid var(--border-color); }
.alias-tag { background: var(--card-bg); padding: 4px 10px; border-radius: 8px; font-size: 13px; display: flex; align-items: center; gap: 6px; border: 1px solid var(--border-color); }
.alias-tag button { border: none; background: transparent; cursor: pointer; opacity: 0.5; font-size: 14px; padding: 0; }
.tag-input input { border: none; background: transparent; padding: 4px; flex: 1; min-width: 100px; outline: none; font-size: 14px; color: var(--text-main); }

.textarea-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; padding-top: 20px; }

.kv-editor { display: flex; flex-direction: column; gap: 10px; }
.kv-row { display: flex; gap: 8px; align-items: center; }
.kv-key, .kv-value { background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 10px; padding: 10px; font-size: 14px; color: var(--text-main); outline: none; }
.kv-key { flex: 2; }
.kv-value { flex: 3; }
.kv-remove { background: #fee2e2; color: #d64040; border: none; border-radius: 8px; width: 32px; height: 32px; cursor: pointer; font-size: 12px; flex-shrink: 0; }
.kv-add { background: none; border: 1px dashed var(--border-color); border-radius: 10px; padding: 8px 16px; cursor: pointer; color: var(--text-muted); font-size: 13px; font-weight: 600; }
.kv-add:hover { border-color: var(--primary-color); color: var(--primary-color); }

.count-tag { background: var(--primary-soft); color: var(--primary-color); padding: 2px 10px; border-radius: 8px; font-size: 12px; font-weight: 700; }

.image-list { display: flex; flex-direction: column; gap: 12px; padding-top: 20px; }
.image-row { display: flex; gap: 16px; padding: 16px; border: 1px solid var(--border-color); border-radius: 14px; align-items: flex-start; }
.image-thumb { width: 80px; height: 60px; border-radius: 10px; overflow: hidden; position: relative; flex-shrink: 0; background: var(--bg-color); }
.image-thumb img { width: 100%; height: 100%; object-fit: cover; }
.cover-badge { position: absolute; bottom: 2px; left: 2px; background: var(--primary-color); color: #fff; font-size: 9px; padding: 1px 6px; border-radius: 6px; font-weight: 700; }
.image-info { flex: 1; display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.img-filename { font-size: 14px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.img-meta { font-size: 12px; color: var(--text-muted); }
.image-edit-grid { flex: 1; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.image-actions { display: flex; flex-direction: column; gap: 6px; flex-shrink: 0; }
.img-btn { padding: 6px 12px; border-radius: 8px; border: none; cursor: pointer; font-size: 12px; font-weight: 600; }
.img-btn.edit { background: var(--bg-color); color: var(--text-main); }
.img-btn.save { background: var(--primary-color); color: #fff; }
.img-btn.cancel { background: var(--bg-color); color: var(--text-muted); }
.img-btn.del { background: #fee2e2; color: #d64040; }

.mini-field { display: flex; flex-direction: column; gap: 4px; }
.mini-field span { font-size: 12px; font-weight: 700; color: var(--text-muted); }
.mini-field input { background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 8px; padding: 8px; font-size: 13px; color: var(--text-main); outline: none; }
.mini-field.check-field { flex-direction: row; align-items: center; gap: 6px; grid-column: span 2; }
.mini-field.check-field input { width: auto; }

.empty-hint { padding: 20px 0; color: var(--text-muted); font-size: 13px; text-align: center; }

.add-image-section { margin-top: 24px; padding-top: 20px; border-top: 1px dashed var(--border-color); }
.add-image-section h4 { margin: 0 0 12px; font-size: 14px; color: var(--text-main); }
.section-tip { margin: 0 0 12px; color: var(--text-muted); font-size: 13px; line-height: 1.6; }
.image-upload-actions { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
.upload-image-btn { background: var(--bg-color); border: 1px dashed var(--border-color); color: var(--text-main); padding: 10px 16px; border-radius: 10px; font-weight: 700; cursor: pointer; }
.upload-image-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.upload-url-preview { color: var(--text-muted); font-size: 12px; word-break: break-all; }
.add-image-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.add-image-submit { margin-top: 12px; background: var(--primary-color); color: #fff; border: none; padding: 10px 24px; border-radius: 10px; font-weight: 700; cursor: pointer; font-size: 13px; }
.add-image-submit:disabled { opacity: 0.5; cursor: not-allowed; }

.form-footer { padding: 24px 0; display: flex; gap: 12px; }
.save-btn { background: var(--primary-color); color: #fff; border: none; padding: 14px 40px; border-radius: 12px; font-weight: 800; cursor: pointer; box-shadow: var(--shadow-md); font-size: 14px; }
.save-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.reset-btn { background: var(--bg-color); color: var(--text-muted); border: 1px solid var(--border-color); padding: 14px 28px; border-radius: 12px; font-weight: 700; cursor: pointer; font-size: 14px; }

.module-placeholder { height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; color: var(--text-muted); opacity: 0.6; }
.module-placeholder .icon { font-size: 48px; margin-bottom: 16px; }
.loader { width: 36px; height: 36px; border: 3px solid #eee; border-top-color: var(--primary-color); border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 12px; }
@keyframes spin { to { transform: rotate(360deg); } }

.review-module { display: flex; height: 100%; }
.review-layout { display: grid; grid-template-columns: 280px 1fr; width: 100%; }
.pending-list { border-right: 1px solid var(--border-color); padding: 16px; overflow-y: auto; }
.review-sub-card { padding: 12px; border: 1px solid var(--border-color); border-radius: 12px; margin-bottom: 10px; cursor: pointer; }
.review-sub-card.active { border-color: var(--primary-color); background: var(--primary-soft); }
.review-card-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 6px; }
.review-kind { flex-shrink: 0; background: var(--bg-color); color: var(--text-muted); border-radius: 999px; padding: 2px 8px; font-size: 11px; font-weight: 700; }
.review-card-subline, .review-card-meta { display: block; }
.review-card-subline { font-size: 12px; color: var(--text-main); opacity: 0.8; margin-bottom: 6px; }
.review-card-meta { font-size: 11px; color: var(--text-muted); }
.review-detail { flex: 1; padding: 24px; overflow-y: auto; }
.review-panel-card { background: #fff; border-radius: 20px; border: 1px solid var(--border-color); box-shadow: var(--shadow-sm); overflow: hidden; display: flex; flex-direction: column; max-height: 100%; }
.review-header { padding: 20px 24px; border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; }
.review-subtitle { margin: 6px 0 0; color: var(--text-muted); font-size: 12px; }
.review-actions { display: flex; gap: 12px; }
.reject-btn { background: #fee2e2; color: #d64040; border: none; padding: 8px 16px; border-radius: 8px; font-weight: 700; cursor: pointer; }
.approve-btn { background: var(--primary-color); color: #fff; border: none; padding: 8px 16px; border-radius: 8px; font-weight: 700; cursor: pointer; }
.reject-btn:disabled, .approve-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.review-scroll-area { flex: 1; overflow-y: auto; padding: 24px; }
.review-section + .review-section { margin-top: 28px; }
.review-section h4 { margin: 0 0 14px; font-size: 15px; }
.review-meta-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.meta-card { background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 14px; padding: 14px 16px; min-width: 0; }
.meta-card.wide { grid-column: span 2; }
.meta-card span { display: block; margin-bottom: 6px; font-size: 12px; font-weight: 700; color: var(--text-muted); }
.meta-card strong { display: block; font-size: 14px; color: var(--text-main); overflow-wrap: anywhere; }
.review-tag-list { display: flex; flex-wrap: wrap; gap: 8px; }
.review-tag { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 999px; padding: 4px 10px; font-size: 12px; }
.measurement-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.measurement-item { background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 14px; padding: 12px 14px; }
.measurement-key { display: block; margin-bottom: 6px; color: var(--text-muted); font-size: 12px; font-weight: 700; }
.measurement-value { font-size: 14px; color: var(--text-main); }
.image-carousel { display: flex; gap: 16px; overflow-x: auto; padding-bottom: 8px; }
.carousel-item { flex-shrink: 0; width: 240px; }
.carousel-item img { width: 100%; height: 180px; object-fit: cover; border-radius: 12px; }
.carousel-item p { font-size: 11px; color: var(--text-muted); margin-top: 8px; }
.review-content-blocks { display: flex; flex-direction: column; gap: 16px; }
.content-block { background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 16px; padding: 18px; }
.content-block h5 { margin: 0 0 10px; font-size: 14px; color: var(--text-main); }
.review-text { margin: 0; line-height: 1.75; white-space: pre-wrap; color: var(--text-main); word-break: break-word; }

@media (max-width: 1200px) {
  .review-layout { grid-template-columns: 1fr; }
  .pending-list { border-right: none; border-bottom: 1px solid var(--border-color); height: 200px; }
}

@media (max-width: 820px) {
  .form-grid, .textarea-grid, .add-image-grid, .image-edit-grid { grid-template-columns: 1fr; }
  .field.full, .mini-field.check-field { grid-column: auto; }
  .review-meta-grid, .measurement-list { grid-template-columns: 1fr; }
  .meta-card.wide { grid-column: auto; }
  .review-header { flex-direction: column; align-items: flex-start; gap: 12px; }
}

.manage-module { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
.manage-layout { display: grid; grid-template-columns: 420px 1fr; height: 100%; overflow: hidden; }
.manage-form-card { padding: 24px; border-right: 1px solid var(--border-color); overflow-y: auto; }
.manage-form-card h3 { margin: 0 0 20px; font-size: 16px; }
.manage-form-grid { display: flex; flex-direction: column; gap: 16px; }
.manage-form-actions { margin-top: 20px; display: flex; gap: 12px; }
.manage-list { flex: 1; overflow-y: auto; padding: 16px; }
.manage-item { display: flex; align-items: center; justify-content: space-between; padding: 14px 16px; border: 1px solid var(--border-color); border-radius: 12px; margin-bottom: 8px; gap: 16px; }
.manage-item.active { border-color: var(--primary-color); background: var(--primary-soft); }
.manage-item-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.manage-item-info strong { font-size: 14px; }
.manage-item-actions { display: flex; gap: 8px; flex-shrink: 0; }
.family-tag { display: inline-block; background: var(--primary-soft); color: var(--primary-dark); border-radius: 6px; padding: 1px 8px; font-size: 11px; font-weight: 700; width: fit-content; }
.desc-preview { font-size: 12px; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

@media (max-width: 820px) {
  .manage-layout { grid-template-columns: 1fr; grid-template-rows: auto 1fr; }
  .manage-form-card { border-right: none; border-bottom: 1px solid var(--border-color); }
}
</style>
