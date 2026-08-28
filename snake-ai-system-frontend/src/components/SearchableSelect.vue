<script setup lang="ts" generic="T extends { id: number; chinese_name: string; latin_name: string }">
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: number | 'all' | null
    options: T[]
    placeholder?: string
    searchPlaceholder?: string
    disabled?: boolean
    allowAll?: boolean
  }>(),
  {
    placeholder: '请选择',
    searchPlaceholder: '关键词搜索...',
    disabled: false,
    allowAll: false,
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: number | 'all' | null): void
}>()

const rootRef = ref<HTMLElement | null>(null)
const searchInputRef = ref<HTMLInputElement | null>(null)
const isOpen = ref(false)
const searchQuery = ref('')

const selectedOption = computed<T | null>(() => {
  if (typeof props.modelValue !== 'number') return null
  return props.options.find((opt) => opt.id === props.modelValue) || null
})

const selectedLabel = computed(() => {
  if (props.modelValue === 'all') return '全部'
  if (!selectedOption.value) return props.placeholder
  return `${selectedOption.value.chinese_name} (${selectedOption.value.latin_name})`
})

const filteredOptions = computed(() => {
  const keyword = searchQuery.value.trim().toLowerCase()
  if (!keyword) return props.options
  return props.options.filter(
    (opt) =>
      opt.chinese_name.toLowerCase().includes(keyword) ||
      opt.latin_name.toLowerCase().includes(keyword),
  )
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
  if (isOpen.value) closePanel()
  else await openPanel()
}

const select = (val: number | 'all' | null) => {
  emit('update:modelValue', val)
  closePanel()
}

const handlePointerDown = (event: MouseEvent) => {
  if (!isOpen.value || !rootRef.value) return
  if (rootRef.value.contains(event.target as Node)) return
  closePanel()
}

document.addEventListener('mousedown', handlePointerDown)
onBeforeUnmount(() => document.removeEventListener('mousedown', handlePointerDown))
</script>

<template>
  <div ref="rootRef" class="searchable-select" :class="{ open: isOpen, disabled }">
    <button class="select-trigger" type="button" :disabled="disabled" @click="togglePanel">
      <span class="trigger-text" :class="{ placeholder: !selectedOption && modelValue !== 'all' }">
        {{ selectedLabel }}
      </span>
      <span class="trigger-arrow">{{ isOpen ? '▴' : '▾' }}</span>
    </button>

    <div v-if="isOpen" class="select-panel">
      <div class="panel-toolbar">
        <input
          ref="searchInputRef"
          v-model="searchQuery"
          type="text"
          class="search-input"
          :placeholder="searchPlaceholder"
        />
      </div>

      <div class="option-list">
        <button v-if="allowAll" class="option-item" :class="{ active: modelValue === 'all' }" @click="select('all')">
          <strong>全部</strong>
        </button>
        
        <div v-if="!filteredOptions.length" class="empty-state">未找到匹配项</div>

        <button
          v-for="opt in filteredOptions"
          :key="opt.id"
          class="option-item"
          :class="{ active: modelValue === opt.id }"
          @click="select(opt.id)"
        >
          <strong>{{ opt.chinese_name }}</strong>
          <span>{{ opt.latin_name }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.searchable-select { position: relative; width: 100%; }
.select-trigger { width: 100%; min-height: 42px; padding: 8px 12px; border: 1px solid var(--border-color); border-radius: 12px; background: var(--card-bg); color: var(--text-main); display: flex; align-items: center; justify-content: space-between; cursor: pointer; text-align: left; }
.trigger-text.placeholder { color: var(--text-muted); }
.disabled .select-trigger { background: var(--bg-color); opacity: 0.6; cursor: not-allowed; }

.select-panel { position: absolute; top: calc(100% + 8px); left: 0; right: 0; z-index: 100; border: 1px solid var(--border-color); border-radius: 14px; background: var(--card-bg); box-shadow: var(--shadow-md); overflow: hidden; }
.panel-toolbar { padding: 8px; border-bottom: 1px solid var(--border-color); background: var(--bg-color); }
.search-input { width: 100%; height: 36px; border: 1px solid var(--border-color); border-radius: 8px; padding: 0 10px; font-size: 13px; outline: none; }

.option-list { max-height: 240px; overflow-y: auto; padding: 8px; }
.option-item { width: 100%; padding: 10px; border: 1px solid transparent; border-radius: 10px; background: transparent; text-align: left; cursor: pointer; display: flex; flex-direction: column; gap: 2px; }
.option-item:hover { background: var(--bg-color); }
.option-item.active { background: var(--primary-soft); color: var(--primary-dark); }
.option-item strong { font-size: 14px; }
.option-item span { font-size: 11px; opacity: 0.6; font-style: italic; }
.empty-state { padding: 20px; text-align: center; color: var(--text-muted); font-size: 13px; }
</style>
