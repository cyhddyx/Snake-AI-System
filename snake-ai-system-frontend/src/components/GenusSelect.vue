<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import type { Family } from '@/api/snake/families'
import type { Genus } from '@/api/snake/genera'

const props = withDefaults(
  defineProps<{
    modelValue: number | null
    genera: Genus[]
    families?: Family[]
    familyId?: number | null
    placeholder?: string
    disabled?: boolean
  }>(),
  {
    families: () => [],
    familyId: null,
    placeholder: '请选择属',
    disabled: false,
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: number | null): void
}>()

const rootRef = ref<HTMLElement | null>(null)
const searchInputRef = ref<HTMLInputElement | null>(null)
const isOpen = ref(false)
const searchQuery = ref('')

const familyById = computed(() => {
  const map = new Map<number, Family>()
  props.families.forEach((item) => map.set(item.id, item))
  return map
})

const selectedGenus = computed(() =>
  props.modelValue ? props.genera.find((item) => item.id === props.modelValue) || null : null,
)

const selectedLabel = computed(() => {
  if (!selectedGenus.value) return props.placeholder
  const familyName = familyById.value.get(selectedGenus.value.family_id)?.chinese_name
  return familyName
    ? `${selectedGenus.value.chinese_name} · ${familyName}`
    : selectedGenus.value.chinese_name
})

const normalizedKeyword = computed(() => searchQuery.value.trim().toLowerCase())

const visibleGenera = computed(() => {
  const keyword = normalizedKeyword.value

  return props.genera
    .filter((item) => (props.familyId ? item.family_id === props.familyId : true))
    .filter((item) => {
      if (!keyword) return true
      const family = familyById.value.get(item.family_id)
      return (
        item.chinese_name.toLowerCase().includes(keyword) ||
        item.latin_name.toLowerCase().includes(keyword) ||
        family?.chinese_name.toLowerCase().includes(keyword) ||
        family?.latin_name.toLowerCase().includes(keyword)
      )
    })
    .sort((a, b) => {
      if (a.family_id !== b.family_id) {
        return a.family_id - b.family_id
      }
      return a.chinese_name.localeCompare(b.chinese_name, 'zh-Hans-CN')
    })
})

const groupedGenera = computed(() => {
  const groups = new Map<number, { familyId: number; label: string; items: Genus[] }>()

  visibleGenera.value.forEach((item) => {
    const family = familyById.value.get(item.family_id)
    const label = family ? `${family.chinese_name} / ${family.latin_name}` : '未分组'
    const existing = groups.get(item.family_id)
    if (existing) {
      existing.items.push(item)
      return
    }
    groups.set(item.family_id, {
      familyId: item.family_id,
      label,
      items: [item],
    })
  })

  return Array.from(groups.values())
})

const openPanel = async () => {
  if (props.disabled) return
  isOpen.value = true
  await nextTick()
  searchInputRef.value?.focus()
}

const closePanel = () => {
  isOpen.value = false
  searchQuery.value = ''
}

const togglePanel = async () => {
  if (isOpen.value) {
    closePanel()
    return
  }
  await openPanel()
}

const selectGenus = (id: number | null) => {
  emit('update:modelValue', id)
  closePanel()
}

const handlePointerDown = (event: MouseEvent) => {
  if (!isOpen.value || !rootRef.value) return
  const target = event.target as Node | null
  if (target && rootRef.value.contains(target)) return
  closePanel()
}

const handleEscape = (event: KeyboardEvent) => {
  if (event.key !== 'Escape' || !isOpen.value) return
  closePanel()
}

watch(
  () => props.disabled,
  (disabled) => {
    if (disabled) {
      closePanel()
    }
  },
)

document.addEventListener('mousedown', handlePointerDown)
window.addEventListener('keydown', handleEscape)

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handlePointerDown)
  window.removeEventListener('keydown', handleEscape)
})
</script>

<template>
  <div ref="rootRef" class="genus-select" :class="{ open: isOpen, disabled }">
    <button class="select-trigger" type="button" :disabled="disabled" @click="togglePanel">
      <span class="trigger-text" :class="{ placeholder: !selectedGenus }">{{ selectedLabel }}</span>
      <span class="trigger-arrow">{{ isOpen ? '▴' : '▾' }}</span>
    </button>

    <div v-if="isOpen" class="select-panel">
      <div class="panel-toolbar">
        <input
          ref="searchInputRef"
          v-model="searchQuery"
          type="text"
          class="search-input"
          placeholder="搜索属名、拉丁名或所属科"
        />
        <button v-if="modelValue !== null" class="clear-btn" type="button" @click="selectGenus(null)">
          清除
        </button>
      </div>

      <div class="option-list">
        <div v-if="!groupedGenera.length" class="empty-state">没有匹配的属</div>

        <section v-for="group in groupedGenera" :key="group.familyId" class="option-group">
          <h4 v-if="familyId === null">{{ group.label }}</h4>
          <button
            v-for="item in group.items"
            :key="item.id"
            class="option-item"
            :class="{ active: modelValue === item.id }"
            type="button"
            @click="selectGenus(item.id)"
          >
            <strong>{{ item.chinese_name }}</strong>
            <span>{{ item.latin_name }}</span>
          </button>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.genus-select {
  position: relative;
}

.select-trigger,
.search-input {
  width: 100%;
  border: 1px solid #d7dfe7;
  border-radius: 12px;
  background: #fff;
  color: #2f3745;
  font-size: 14px;
}

.select-trigger {
  min-height: 42px;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  text-align: left;
  cursor: pointer;
}

.trigger-text.placeholder {
  color: #8a94a3;
}

.trigger-arrow {
  flex-shrink: 0;
  color: #6a7381;
  font-size: 12px;
}

.genus-select.disabled .select-trigger {
  background: #f5f7fa;
  color: #97a0ad;
  cursor: not-allowed;
}

.select-panel {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  z-index: 30;
  border: 1px solid #d7dfe7;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 14px 32px rgba(28, 39, 53, 0.14);
  overflow: hidden;
}

.panel-toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  padding: 10px;
  border-bottom: 1px solid #e6ebf0;
  background: #fafcfd;
}

.search-input {
  height: 38px;
  padding: 0 12px;
  outline: none;
}

.clear-btn {
  height: 38px;
  padding: 0 12px;
  border: 1px solid #d7dfe7;
  border-radius: 10px;
  background: #fff;
  color: #536173;
  font-size: 13px;
  cursor: pointer;
}

.option-list {
  max-height: 280px;
  overflow-y: auto;
  padding: 10px;
  scrollbar-width: thin;
  scrollbar-color: #b8c2cf #f3f6f8;
}

.option-list::-webkit-scrollbar {
  width: 10px;
}

.option-list::-webkit-scrollbar-track {
  background: #f3f6f8;
  border-radius: 999px;
}

.option-list::-webkit-scrollbar-thumb {
  background: #b8c2cf;
  border-radius: 999px;
  border: 2px solid #f3f6f8;
}

.option-list::-webkit-scrollbar-thumb:hover {
  background: #97a3b2;
}

.empty-state {
  padding: 18px 12px;
  color: #7a8696;
  font-size: 13px;
  text-align: center;
}

.option-group + .option-group {
  margin-top: 10px;
}

.option-group h4 {
  margin: 0 0 8px;
  color: #6a7583;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.option-item {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e3e8ed;
  border-radius: 10px;
  background: #fff;
  color: #2f3745;
  text-align: left;
  cursor: pointer;
}

.option-item + .option-item {
  margin-top: 6px;
}

.option-item strong,
.option-item span {
  display: block;
}

.option-item span {
  margin-top: 4px;
  color: #6d7888;
  font-size: 12px;
}

.option-item.active {
  border-color: #8ebd2f;
  background: #eef7da;
}
@media (max-width: 820px) {
  .select-panel {
    position: relative;
    top: 8px;
  }
}
</style>
