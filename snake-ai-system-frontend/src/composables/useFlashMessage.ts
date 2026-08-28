import { ref } from 'vue'

export type FlashType = 'success' | 'error' | 'info' | 'warning'

interface FlashMessage {
  id: number
  type: FlashType
  text: string
}

const messages = ref<FlashMessage[]>([])
let nextId = 0

export function useFlashMessage() {
  const showMessage = (text: string, type: FlashType = 'info', duration = 4000) => {
    const id = nextId++
    messages.value.push({ id, type, text })
    
    setTimeout(() => {
      messages.value = messages.value.filter(m => m.id !== id)
    }, duration)
  }

  const removeMessage = (id: number) => {
    messages.value = messages.value.filter(m => m.id !== id)
  }

  return {
    messages,
    showMessage,
    removeMessage,
    success: (text: string) => showMessage(text, 'success'),
    error: (text: string) => showMessage(text, 'error'),
    info: (text: string) => showMessage(text, 'info'),
    warning: (text: string) => showMessage(text, 'warning')
  }
}
