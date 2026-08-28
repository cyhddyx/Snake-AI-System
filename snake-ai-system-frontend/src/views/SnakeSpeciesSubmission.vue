<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { submissionsApi, type SpeciesSubmission, type SubmissionImage } from '@/api/snake/submissions'
import { familiesApi, type Family } from '@/api/snake/families'
import { generaApi, type Genus } from '@/api/snake/genera'
import { speciesApi, type IUCNStatus, type ToxicityLevel } from '@/api/snake/species'
import { speciesContentApi } from '@/api/snake/speciesContent'
import { speciesImagesApi } from '@/api/snake/speciesImages'
import { imageServiceApi } from '@/api/imageService'
import GenusSelect from '@/components/GenusSelect.vue'
import { useFlashMessage } from '@/composables/useFlashMessage'

const route = useRoute()
const router = useRouter()
const { success, error: showError } = useFlashMessage()

const loading = ref(true)
const submitting = ref(false)
const uploadingImages = ref(false)
const mySubmissions = ref<SpeciesSubmission[]>([])
const families = ref<Family[]>([])
const genera = ref<Genus[]>([])
const imageInputRef = ref<HTMLInputElement | null>(null)

const editingId = ref<number | null>(null)
const expandedSections = ref<Set<string>>(new Set(['basic', 'images']))

const correctionSpeciesId = computed(() => {
  const id = route.query.species_id
  return id ? Number(id) : null
})
const isCorrection = computed(() => !!correctionSpeciesId.value && !editingId.value)
const pageTitle = computed(() => {
  if (editingId.value) return '编辑投稿'
  if (isCorrection.value) return '纠错投稿'
  return '物种投稿'
})
const pageSubtitle = computed(() => {
  if (isCorrection.value) return '你修改的内容将提交审核，通过后自动覆盖原文数据。'
  return '分享物种知识，共同完善蛇类数字化图鉴。你的每一条投稿都将经过专家审核。'
})
const toxicityOptions: ToxicityLevel[] = ['无毒', '微毒', '有毒', '剧毒', '极毒']
const iucnOptions: { value: IUCNStatus; label: string }[] = [
  { value: 'EX', label: '已灭绝' }, { value: 'EW', label: '野外灭绝' },
  { value: 'CR', label: '极危' }, { value: 'EN', label: '濒危' },
  { value: 'VU', label: '易危' }, { value: 'NT', label: '近危' },
  { value: 'LC', label: '无危' }, { value: 'DD', label: '数据不足' },
  { value: 'NE', label: '未评估' },
]

type SubmissionFormImage = SubmissionImage

const normalizeImages = (images: SubmissionFormImage[]) => {
  const coverIndex = images.findIndex((item) => item.is_cover)

  return images.map((item, index) => ({
    ...item,
    image_type: item.image_type || 'submission',
    sort_order: index,
    is_cover: coverIndex >= 0 ? index === coverIndex : index === 0,
  }))
}

const form = ref({
  chinese_name: '',
  latin_name: '',
  genus_id: null as number | null,
  aliases: [] as string[],
  toxicity: '' as ToxicityLevel | '',
  iucn_status: '' as IUCNStatus | '',
  discoverer: '',
  discover_year: '',
  basic_intro: '',
  measurements: [] as Array<{ key: string; value: string }>,
  zoology: '',
  morphology: '',
  history: '',
  distribution: '',
  habitat: '',
  behavior: '',
  reproduction: '',
  conservation: '',
  value: '',
  hazard: '',
  content_format: 'markdown',
  images: [] as SubmissionFormImage[],
})

const aliasInput = ref('')
const addAlias = () => {
  if (aliasInput.value.trim() && !form.value.aliases.includes(aliasInput.value.trim())) {
    form.value.aliases.push(aliasInput.value.trim())
    aliasInput.value = ''
  }
}

const toggleSection = (key: string) => {
  if (expandedSections.value.has(key)) expandedSections.value.delete(key)
  else expandedSections.value.add(key)
}

const addMeasurementRow = () => {
  form.value.measurements.push({ key: '', value: '' })
}

const removeMeasurementRow = (index: number) => {
  form.value.measurements.splice(index, 1)
}

const measurementsToRecord = () => {
  const record: Record<string, string | number> = {}
  for (const row of form.value.measurements) {
    const key = row.key.trim()
    if (!key) continue
    const rawValue = row.value.trim()
    record[key] = rawValue !== '' && !Number.isNaN(Number(rawValue)) ? Number(rawValue) : row.value
  }
  return Object.keys(record).length ? record : undefined
}

const recordToMeasurements = (record?: Record<string, unknown>) => {
  if (!record || typeof record !== 'object') return []
  return Object.entries(record).map(([key, value]) => ({
    key,
    value: value == null ? '' : String(value),
  }))
}

const loadData = async () => {
  try {
    const [fData, gData, sData] = await Promise.all([
      familiesApi.list(),
      generaApi.list(),
      submissionsApi.list({ mine_only: true }),
    ])
    families.value = fData
    genera.value = gData
    mySubmissions.value = sData
  } catch {
    showError('获取投稿数据失败')
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  form.value = {
    chinese_name: '', latin_name: '', genus_id: null, aliases: [],
    toxicity: '', iucn_status: '',
    discoverer: '', discover_year: '', basic_intro: '',
    measurements: [], zoology: '',
    morphology: '', history: '', distribution: '', habitat: '', behavior: '',
    reproduction: '', conservation: '', value: '', hazard: '',
    content_format: 'markdown', images: [],
  }
}

const cancelEdit = () => {
  editingId.value = null
  resetForm()
  if (correctionSpeciesId.value) {
    router.replace({ path: '/submit' })
  }
}

const startEdit = (sub: SpeciesSubmission) => {
  editingId.value = sub.id
  form.value = {
    chinese_name: sub.chinese_name,
    latin_name: sub.latin_name,
    genus_id: sub.genus_id,
    aliases: [...(sub.aliases || [])],
    toxicity: sub.toxicity || '',
    iucn_status: sub.iucn_status || '',
    discoverer: sub.discoverer || '',
    discover_year: sub.discover_year?.toString() || '',
    basic_intro: sub.basic_intro || '',
    measurements: recordToMeasurements(sub.measurements),
    zoology: sub.zoology || '',
    morphology: sub.morphology || '',
    history: sub.history || '',
    distribution: sub.distribution || '',
    habitat: sub.habitat || '',
    behavior: sub.behavior || '',
    reproduction: sub.reproduction || '',
    conservation: sub.conservation || '',
    value: sub.value || '',
    hazard: sub.hazard || '',
    content_format: sub.content_format || 'markdown',
    images: normalizeImages(sub.images.map((img: SubmissionImage) => ({ ...img }))),
  }
  expandedSections.value.add('content')
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const openImagePicker = () => {
  if (uploadingImages.value) return
  imageInputRef.value?.click()
}

const uploadImages = async (files: File[]) => {
  if (!files.length) return
  if (files.some((file) => !file.type.startsWith('image/'))) {
    showError('只能上传图片文件')
    return
  }

  uploadingImages.value = true
  try {
    const uploadedImages: SubmissionFormImage[] = []

    for (const file of files) {
      const asset = await imageServiceApi.upload(file)
      uploadedImages.push({
        image_url: asset.url,
        image_type: 'submission',
        sort_order: form.value.images.length + uploadedImages.length,
        is_cover: form.value.images.length + uploadedImages.length === 0,
      })
    }

    form.value.images = normalizeImages([...form.value.images, ...uploadedImages])
  } catch (err) {
    console.error('Failed to upload submission images', err)
    showError('图片上传失败，请先启动 E:\\Project\\Snake-AI-System\\image\\server.py')
  } finally {
    uploadingImages.value = false
    if (imageInputRef.value) imageInputRef.value.value = ''
  }
}

const onImageFileChange = async (event: Event) => {
  const files = Array.from((event.target as HTMLInputElement).files || [])
  await uploadImages(files)
}

const removeImage = (index: number) => {
  form.value.images = normalizeImages(form.value.images.filter((_, idx) => idx !== index))
}

const submitForm = async () => {
  if (uploadingImages.value) {
    showError('图片仍在上传中，请稍候')
    return
  }
  if (!form.value.chinese_name || !form.value.genus_id) {
    showError('请填写物种中文名并选择所属分类')
    return
  }
  
  submitting.value = true
  try {
    const payload = {
      chinese_name: form.value.chinese_name,
      latin_name: form.value.latin_name,
      genus_id: form.value.genus_id!,
      aliases: form.value.aliases,
      discoverer: form.value.discoverer || undefined,
      discover_year: form.value.discover_year ? Number(form.value.discover_year) : undefined,
      basic_intro: form.value.basic_intro || undefined,
      toxicity: form.value.toxicity || undefined,
      iucn_status: form.value.iucn_status || undefined,
      measurements: measurementsToRecord(),
      zoology: form.value.zoology || undefined,
      history: form.value.history || undefined,
      morphology: form.value.morphology || undefined,
      distribution: form.value.distribution || undefined,
      habitat: form.value.habitat || undefined,
      behavior: form.value.behavior || undefined,
      reproduction: form.value.reproduction || undefined,
      conservation: form.value.conservation || undefined,
      value: form.value.value || undefined,
      hazard: form.value.hazard || undefined,
      content_format: form.value.content_format || 'markdown',
      images: normalizeImages(form.value.images),
    }
    if (isCorrection.value && correctionSpeciesId.value) {
      Object.assign(payload, { target_species_id: correctionSpeciesId.value })
    }
    if (editingId.value) {
      await submissionsApi.update(editingId.value, payload)
      success('投稿已更新，请等待审核')
    } else {
      await submissionsApi.create(payload)
      success(isCorrection.value ? '纠错已提交，通过后将自动更新数据！' : '投稿已提交，感谢你的贡献！')
    }
    cancelEdit()
    await loadData()
  } catch {
    showError('提交失败，请重试')
  } finally {
    submitting.value = false
  }
}

const loadCorrectionData = async (speciesId: number) => {
  try {
    const [speciesData, contentData, imageData] = await Promise.all([
      speciesApi.get(speciesId),
      speciesContentApi.get(speciesId).catch(() => null),
      speciesImagesApi.list(speciesId).catch(() => []),
    ])
    form.value = {
      chinese_name: speciesData.chinese_name,
      latin_name: speciesData.latin_name,
      genus_id: speciesData.genus_id,
      aliases: [...(speciesData.aliases || [])],
      toxicity: speciesData.toxicity || '',
      iucn_status: speciesData.iucn_status || '',
      discoverer: speciesData.discoverer || '',
      discover_year: speciesData.discover_year?.toString() || '',
      basic_intro: speciesData.basic_intro || '',
      measurements: recordToMeasurements(speciesData.measurements),
      zoology: contentData?.zoology || '',
      morphology: contentData?.morphology || '',
      history: contentData?.history || '',
      distribution: contentData?.distribution || '',
      habitat: contentData?.habitat || '',
      behavior: contentData?.behavior || '',
      reproduction: contentData?.reproduction || '',
      conservation: contentData?.conservation || '',
      value: contentData?.value || '',
      hazard: contentData?.hazard || '',
      content_format: contentData?.content_format || 'markdown',
      images: imageData.map((img) => ({
        image_url: img.image_url,
        thumbnail_url: img.thumbnail_url,
        caption: img.caption,
        photographer: img.photographer,
        image_type: img.image_type,
        sort_order: img.sort_order,
        is_cover: img.is_cover,
      })),
    }
    expandedSections.value = new Set(['basic', 'images', 'content'])
  } catch (err) {
    console.error('Failed to load correction data', err)
    showError('加载物种数据失败')
  }
}

onMounted(async () => {
  await loadData()
  if (correctionSpeciesId.value) {
    await loadCorrectionData(correctionSpeciesId.value)
  }
})
</script>

<template>
  <div class="submit-page">
    <header class="submit-header">
      <div class="header-left">
        <p class="kicker">Contribute to Encyclopedia</p>
        <h1>{{ pageTitle }}</h1>
        <p class="subtitle">{{ pageSubtitle }}</p>
      </div>
      <div v-if="editingId || isCorrection" class="header-actions">
        <button class="cancel-btn" @click="cancelEdit">{{ isCorrection ? '放弃纠错' : '放弃编辑' }}</button>
      </div>
    </header>

    <div v-if="loading" class="state-wrap">
      <div class="loader"></div>
      <p>数据加载中...</p>
    </div>

    <div v-else class="submit-layout">
      <main class="form-container">
        <!-- Section 1 -->
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
                <span>所属科属 *</span>
                <GenusSelect v-model="form.genus_id" :genera="genera" :families="families" placeholder="搜索科或属..." />
              </div>
              <div class="field full">
                <span>别名 (常用俗称)</span>
                <div class="tag-input">
                  <span v-for="a in form.aliases" :key="a" class="alias-tag">{{ a }} <button @click="form.aliases = form.aliases.filter(i => i !== a)">×</button></span>
                  <input v-model="aliasInput" @keydown.enter.prevent="addAlias" placeholder="按回车添加" />
                </div>
              </div>
              <label class="field">
                <span>毒性</span>
                <select v-model="form.toxicity">
                  <option value="">未指定</option>
                  <option v-for="opt in toxicityOptions" :key="opt" :value="opt">{{ opt }}</option>
                </select>
              </label>
              <label class="field">
                <span>IUCN 保护状态</span>
                <select v-model="form.iucn_status">
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
                <span>度量数据</span>
                <div class="kv-editor">
                  <div v-for="(row, idx) in form.measurements" :key="idx" class="kv-row">
                    <input v-model="row.key" type="text" placeholder="属性名" class="kv-key" />
                    <input v-model="row.value" type="text" placeholder="属性值" class="kv-value" />
                    <button class="kv-remove" type="button" @click="removeMeasurementRow(idx)">✕</button>
                  </div>
                  <button class="kv-add" type="button" @click="addMeasurementRow">+ 添加属性</button>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- Section 2 -->
        <section class="form-card" :class="{ collapsed: !expandedSections.has('images') }">
          <header class="card-header" @click="toggleSection('images')">
            <div class="header-title">
              <span class="step-num">2</span>
              <h3>物种形态图像</h3>
            </div>
            <span class="chevron">{{ expandedSections.has('images') ? '▲' : '▼' }}</span>
          </header>
          <div v-if="expandedSections.has('images')" class="card-body">
            <input ref="imageInputRef" type="file" accept="image/*" multiple hidden @change="onImageFileChange" />
            <p class="section-tip">请选择本地图片文件，系统会自动上传并转换成 URL。首张图片将自动作为图鉴封面。</p>
            <div class="image-uploader">
              <div v-for="(img, idx) in form.images" :key="idx" class="image-preview-card">
                <img :src="img.thumbnail_url || img.image_url" />
                <span v-if="img.is_cover" class="cover-badge">封面</span>
                <button class="remove-img" type="button" @click="removeImage(idx)">✕</button>
              </div>
              <div v-if="uploadingImages" class="uploading-card">
                <div class="uploading-spinner"></div>
                <span>上传中...</span>
              </div>
              <button class="add-image-btn" type="button" :disabled="uploadingImages" @click="openImagePicker">
                {{ uploadingImages ? '上传中...' : '+ 上传图片' }}
              </button>
            </div>
          </div>
        </section>

        <!-- Section 3 -->
        <section class="form-card" :class="{ collapsed: !expandedSections.has('content') }">
          <header class="card-header" @click="toggleSection('content')">
            <div class="header-title">
              <span class="step-num">3</span>
              <h3>详细百科描述</h3>
            </div>
            <span class="chevron">{{ expandedSections.has('content') ? '▲' : '▼' }}</span>
          </header>
          <div v-if="expandedSections.has('content')" class="card-body">
            <div class="accordion-group">
              <div class="field full">
                <span>物种简评 (Abstract)</span>
                <textarea v-model="form.basic_intro" placeholder="一句话描述该物种的核心特征..."></textarea>
              </div>
              <div class="textarea-grid">
                <label class="field"><span>动物学信息</span><textarea v-model="form.zoology"></textarea></label>
                <label class="field"><span>分类历史</span><textarea v-model="form.history"></textarea></label>
                <label class="field"><span>形态特征</span><textarea v-model="form.morphology"></textarea></label>
                <label class="field"><span>地理分布</span><textarea v-model="form.distribution"></textarea></label>
                <label class="field"><span>栖息环境</span><textarea v-model="form.habitat"></textarea></label>
                <label class="field"><span>行为习性</span><textarea v-model="form.behavior"></textarea></label>
                <label class="field"><span>繁殖方式</span><textarea v-model="form.reproduction"></textarea></label>
                <label class="field"><span>保护现状</span><textarea v-model="form.conservation"></textarea></label>
                <label class="field"><span>生态与科研价值</span><textarea v-model="form.value"></textarea></label>
                <label class="field"><span>危险性说明</span><textarea v-model="form.hazard"></textarea></label>
              </div>
            </div>
          </div>
        </section>

        <div class="form-footer">
          <button class="submit-btn" :disabled="submitting || uploadingImages" @click="submitForm">
            {{ uploadingImages ? '图片上传中...' : (submitting ? '提交中...' : (editingId ? '保存更改' : (isCorrection ? '提交纠错' : '提交投稿'))) }}
          </button>
        </div>
      </main>

      <aside class="submission-sidebar">
        <section class="history-card">
          <h3>我的投稿历史</h3>
          <div v-if="!mySubmissions.length" class="empty-history">暂无历史记录</div>
          <div v-else class="history-list">
            <div v-for="sub in mySubmissions" :key="sub.id" class="history-item" :class="{ 'is-editing': editingId === sub.id }" @click="startEdit(sub)">
              <div class="item-main">
                <strong>{{ sub.chinese_name }}</strong>
                <span class="status-tag" :class="sub.status">{{ sub.status }}</span>
              </div>
              <span class="item-date">{{ new Date(sub.created_at).toLocaleDateString() }}</span>
            </div>
          </div>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.submit-page { padding: 24px; min-height: 100vh; max-width: 1300px; margin: 0 auto; }
.submit-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 32px; }
.kicker { font-size: 12px; font-weight: 800; color: var(--primary-color); text-transform: uppercase; }
.submit-header h1 { margin: 6px 0 0; font-size: 28px; }
.subtitle { color: var(--text-muted); font-size: 14px; margin: 8px 0 0; max-width: 600px; }
.submit-layout { display: grid; grid-template-columns: 1fr 320px; gap: 32px; }
.form-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 20px; overflow: visible; margin-bottom: 20px; box-shadow: var(--shadow-sm); }
.card-header { padding: 20px 24px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; }
.header-title { display: flex; align-items: center; gap: 16px; }
.step-num { width: 28px; height: 28px; border-radius: 50%; background: var(--primary-soft); color: var(--primary-color); display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 14px; }
.card-body { padding: 0 24px 24px; border-top: 1px solid var(--bg-color); }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; padding-top: 20px; }
.field { display: flex; flex-direction: column; gap: 8px; }
.field.full { grid-column: span 2; }
.field span { font-size: 13px; font-weight: 700; color: var(--text-muted); }
.field input, .field textarea, .field select { background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 12px; padding: 12px; font-size: 14px; color: var(--text-main); outline: none; font-family: inherit; }
.field textarea { min-height: 120px; resize: vertical; }
.section-tip { margin: 20px 0 0; color: var(--text-muted); font-size: 13px; line-height: 1.6; }
.tag-input { display: flex; flex-wrap: wrap; gap: 8px; background: var(--bg-color); padding: 8px; border-radius: 12px; border: 1.5px solid var(--border-color); }
.alias-tag { background: var(--card-bg); padding: 4px 10px; border-radius: 8px; font-size: 13px; display: flex; align-items: center; gap: 6px; }
.alias-tag button { border: none; background: transparent; cursor: pointer; opacity: 0.5; }
.tag-input input { border: none; background: transparent; padding: 4px; flex: 1; min-width: 100px; }
.kv-editor { display: flex; flex-direction: column; gap: 10px; }
.kv-row { display: flex; gap: 8px; align-items: center; }
.kv-key, .kv-value { background: var(--bg-color); border: 1px solid var(--border-color); border-radius: 10px; padding: 10px; font-size: 14px; color: var(--text-main); outline: none; }
.kv-key { flex: 2; }
.kv-value { flex: 3; }
.kv-remove { background: #fee2e2; color: #d64040; border: none; border-radius: 8px; width: 32px; height: 32px; cursor: pointer; font-size: 12px; flex-shrink: 0; }
.kv-add { background: none; border: 1px dashed var(--border-color); border-radius: 10px; padding: 8px 16px; cursor: pointer; color: var(--text-muted); font-size: 13px; font-weight: 600; align-self: flex-start; }
.image-uploader { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 20px; }
.image-preview-card { width: 120px; height: 90px; border-radius: 12px; overflow: hidden; position: relative; border: 1px solid var(--border-color); }
.image-preview-card img { width: 100%; height: 100%; object-fit: cover; }
.cover-badge { position: absolute; left: 6px; bottom: 6px; padding: 4px 8px; border-radius: 999px; background: rgba(0,0,0,0.7); color: #fff; font-size: 11px; font-weight: 700; }
.remove-img { position: absolute; top: 4px; right: 4px; z-index: 1; background: rgba(0,0,0,0.5); color: #fff; border: none; border-radius: 50%; width: 20px; height: 20px; cursor: pointer; }
.uploading-card,
.add-image-btn { width: 120px; height: 90px; border-radius: 12px; }
.uploading-card { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; border: 1px solid var(--border-color); background: var(--card-bg); color: var(--text-muted); font-size: 12px; font-weight: 600; }
.uploading-spinner { width: 20px; height: 20px; border: 2px solid rgba(0,0,0,0.12); border-top-color: var(--primary-color); border-radius: 50%; animation: spin 0.8s linear infinite; }
.add-image-btn { border: 2px dashed var(--border-color); background: var(--bg-color); color: var(--text-muted); cursor: pointer; font-size: 12px; font-weight: 600; }
.add-image-btn:disabled { cursor: wait; opacity: 0.7; }
.textarea-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }
.history-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 20px; padding: 20px; }
.history-item { padding: 12px; border: 1px solid var(--border-color); border-radius: 12px; cursor: pointer; margin-bottom: 10px; }
.history-item.is-editing { border-color: var(--primary-color); background: var(--primary-soft); }
.status-tag { font-size: 10px; padding: 2px 8px; border-radius: 99px; font-weight: 800; }
.status-tag.pending { background: #fef3c7; color: #92400e; }
.status-tag.approved { background: #d1fae5; color: #065f46; }
.submit-btn { background: var(--primary-color); color: #fff; border: none; padding: 14px 40px; border-radius: 12px; font-weight: 800; cursor: pointer; box-shadow: var(--shadow-md); }
.submit-btn:disabled { opacity: 0.7; cursor: not-allowed; }
.state-wrap { min-height: 400px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; color: var(--text-muted); }
.loader { width: 40px; height: 40px; border: 3px solid #eee; border-top-color: var(--primary-color); border-radius: 50%; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (max-width: 1000px) {
  .submit-layout { grid-template-columns: 1fr; }
  .form-grid, .textarea-grid { grid-template-columns: 1fr; }
  .field.full { grid-column: auto; }
}
</style>
