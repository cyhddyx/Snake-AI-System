<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import { chatStream } from '@/api/useStream'
import { useFlashMessage } from '@/composables/useFlashMessage'

interface Message {
  role: 'user' | 'assistant'
  content: string
  isThinking?: boolean
  thought?: string
}

const { error: showError } = useFlashMessage()

const input = ref('')
const messages = ref<Message[]>([])
const loading = ref(false)
const scrollContainer = ref<HTMLElement | null>(null)
const isSidebarOpen = ref(window.innerWidth > 900)

// Issue 17: Local History
const CHAT_HISTORY_KEY = 'snake_ai_chat_history'

const saveHistory = () => {
  localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(messages.value.slice(-20)))
}

const clearHistory = () => {
  if (confirm('确定要清空所有聊天记录吗？')) {
    messages.value = []
    localStorage.removeItem(CHAT_HISTORY_KEY)
  }
}

// Issue 16: Simple Markdown Formatter
const formatContent = (text: string) => {
  if (!text) return ''
  return text
    .replace(/### (.*)/g, '<h4>$1</h4>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br/>')
}

const scrollToBottom = async () => {
  await nextTick()
  if (scrollContainer.value) {
    scrollContainer.value.scrollTop = scrollContainer.value.scrollHeight
  }
}

const sendMessage = async () => {
  const query = input.value.trim()
  if (!query || loading.value) return

  messages.value.push({ role: 'user', content: query })
  input.value = ''
  loading.value = true
  
  // Issue 18: Separate Thinking
  const assistantMsg = ref<Message>({ 
    role: 'assistant', 
    content: '', 
    isThinking: true, 
    thought: '正在思考中...' 
  })
  messages.value.push(assistantMsg.value)
  await scrollToBottom()

  try {
    await chatStream(query, {
      onThinking: (text: string) => {
        assistantMsg.value.isThinking = true
        assistantMsg.value.thought = text
        void scrollToBottom()
      },
      onContent: (chunk: string) => {
        assistantMsg.value.isThinking = false
        assistantMsg.value.content += chunk
        void scrollToBottom()
      },
      onDone: () => {
        assistantMsg.value.isThinking = false
        saveHistory()
      },
      onError: () => {
        showError('对话服务异常')
      }
    })
  } catch (err) {
    showError('对话服务暂时不可用，请稍后再试。')
    messages.value.pop()
  } finally {
    loading.value = false
    assistantMsg.value.isThinking = false
  }
}

const quickPrompt = (text: string) => {
  input.value = text
  void sendMessage()
  if (window.innerWidth <= 900) isSidebarOpen.value = false
}

onMounted(() => {
  const saved = localStorage.getItem(CHAT_HISTORY_KEY)
  if (saved) messages.value = JSON.parse(saved)
})

watch(messages, saveHistory, { deep: true })
</script>

<template>
  <div class="chat-page">
    <header class="chat-header">
      <div class="header-left">
        <p class="kicker">Expert Consultation</p>
        <h1>智能问答</h1>
        <p class="subtitle">与蛇类专家 AI 深度对话，获取关于习性、分布与急救的专业解答。</p>
      </div>
      <div class="header-actions">
        <button class="sidebar-toggle" @click="isSidebarOpen = !isSidebarOpen">
          {{ isSidebarOpen ? '收起助手' : '常用提示' }}
        </button>
        <button class="clear-btn" @click="clearHistory">清空对话</button>
      </div>
    </header>

    <div class="chat-shell" :class="{ 'sidebar-collapsed': !isSidebarOpen }">
      <!-- Issue 15/19: Collapsible Prompt Sidebar -->
      <aside class="prompt-sidebar" :class="{ open: isSidebarOpen }">
        <div class="sidebar-inner">
          <section class="prompt-group">
            <h3>常见咨询</h3>
            <button class="p-btn" @click="quickPrompt('如果被不知名的蛇咬伤了，第一步该做什么？')">被咬伤急救流程</button>
            <button class="p-btn" @click="quickPrompt('如何通过花纹初步判断蛇是否有毒？')">毒性识别技巧</button>
            <button class="p-btn" @click="quickPrompt('家里进蛇了怎么办？有什么驱蛇的方法吗？')">居家避蛇建议</button>
          </section>

          <section class="prompt-group">
            <h3>追问模板</h3>
            <button class="p-btn secondary" @click="quickPrompt('这个物种在中国哪些省份有分布？')">分布范围</button>
            <button class="p-btn secondary" @click="quickPrompt('它的食性是怎样的？主要吃什么？')">食性特征</button>
            <button class="p-btn secondary" @click="quickPrompt('这种蛇的平均寿命和繁殖周期是多久？')">繁殖周期</button>
          </section>
        </div>
      </aside>

      <main class="chat-main">
        <div ref="scrollContainer" class="messages-viewport">
          <div v-if="!messages.length" class="welcome-view">
            <div class="welcome-icon">💬</div>
            <h2>你好，我是你的蛇类百科助手</h2>
            <p>你可以问我任何关于蛇类分类、生物学特征或野外防护的问题。</p>
          </div>

          <div v-for="(msg, idx) in messages" :key="idx" class="message-row" :class="msg.role">
            <div class="avatar">{{ msg.role === 'user' ? 'U' : 'AI' }}</div>
            <div class="bubble">
              <!-- Issue 18: Distinct Thinking State -->
              <div v-if="msg.isThinking" class="thinking-box">
                <div class="dot-loader"><span>.</span><span>.</span><span>.</span></div>
                <span class="thought-text">{{ msg.thought }}</span>
              </div>
              
              <!-- Issue 16: Formatted Content -->
              <div class="bubble-text" v-html="formatContent(msg.content)"></div>
            </div>
          </div>
        </div>

        <footer class="input-area">
          <div class="input-wrapper">
            <textarea 
              v-model="input" 
              placeholder="在这里输入你的问题..." 
              @keydown.enter.prevent="sendMessage"
              rows="1"
            ></textarea>
            <button class="send-btn" :disabled="loading || !input.trim()" @click="sendMessage">
              <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
            </button>
          </div>
        </footer>
      </main>
    </div>
  </div>
</template>

<style scoped>
.chat-page { padding: 24px; min-height: 100vh; max-width: 1200px; margin: 0 auto; display: flex; flex-direction: column; }

.chat-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.kicker { font-size: 12px; font-weight: 800; color: var(--primary-color); text-transform: uppercase; }
.chat-header h1 { margin: 6px 0 0; font-size: 28px; }
.subtitle { color: var(--text-muted); font-size: 14px; margin: 8px 0 0; }

.header-actions { display: flex; gap: 12px; }
.sidebar-toggle, .clear-btn { background: var(--card-bg); border: 1px solid var(--border-color); padding: 8px 16px; border-radius: 10px; cursor: pointer; font-size: 13px; font-weight: 600; }
.clear-btn:hover { color: #d64040; border-color: #fecaca; }

.chat-shell { flex: 1; display: grid; grid-template-columns: 280px 1fr; gap: 24px; min-height: 0; transition: all 0.3s; }
.chat-shell.sidebar-collapsed { grid-template-columns: 0px 1fr; gap: 0; }

/* Sidebar */
.prompt-sidebar { overflow: hidden; opacity: 1; transition: all 0.3s; }
.chat-shell.sidebar-collapsed .prompt-sidebar { opacity: 0; pointer-events: none; }
.sidebar-inner { width: 280px; }
.prompt-group { margin-bottom: 32px; }
.prompt-group h3 { font-size: 12px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted); margin-bottom: 12px; }
.p-btn { width: 100%; text-align: left; background: var(--card-bg); border: 1px solid var(--border-color); padding: 12px; border-radius: 12px; font-size: 13px; margin-bottom: 8px; cursor: pointer; line-height: 1.4; transition: all 0.2s; }
.p-btn:hover { border-color: var(--primary-color); background: var(--primary-soft); }
.p-btn.secondary { background: var(--bg-color); color: var(--text-muted); border-style: dashed; }

/* Main Chat */
.chat-main { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 24px; display: flex; flex-direction: column; overflow: hidden; box-shadow: var(--shadow-sm); }
.messages-viewport { flex: 1; overflow-y: auto; padding: 24px; display: flex; flex-direction: column; gap: 20px; }

.welcome-view { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; color: var(--text-muted); }
.welcome-icon { font-size: 64px; margin-bottom: 20px; opacity: 0.3; }

.message-row { display: flex; gap: 16px; max-width: 85%; }
.message-row.user { align-self: flex-end; flex-direction: row-reverse; }
.avatar { width: 36px; height: 36px; border-radius: 12px; background: var(--border-color); display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 12px; flex-shrink: 0; }
.user .avatar { background: var(--primary-color); color: #fff; }

.bubble { padding: 14px 18px; border-radius: 18px; line-height: 1.7; font-size: 15px; position: relative; }
.user .bubble { background: var(--primary-color); color: #fff; border-top-right-radius: 2px; }
.assistant .bubble { background: var(--bg-color); color: var(--text-main); border-top-left-radius: 2px; }

.bubble-text :deep(h4) { margin: 16px 0 8px; color: var(--primary-color); }
.bubble-text :deep(code) { background: rgba(0,0,0,0.05); padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 0.9em; }
.assistant .bubble-text :deep(strong) { color: var(--primary-color); }

/* Thinking Box */
.thinking-box { display: flex; align-items: center; gap: 10px; color: var(--text-muted); font-size: 13px; font-style: italic; margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px dashed var(--border-color); }
.dot-loader span { animation: blink 1.4s infinite both; font-weight: 800; }
.dot-loader span:nth-child(2) { animation-delay: .2s; }
.dot-loader span:nth-child(3) { animation-delay: .4s; }
@keyframes blink { 0% { opacity: .2; } 20% { opacity: 1; } 100% { opacity: .2; } }

/* Input Area */
.input-area { padding: 20px; background: var(--card-bg); border-top: 1px solid var(--border-color); }
.input-wrapper { display: flex; align-items: flex-end; gap: 12px; background: var(--bg-color); padding: 8px 8px 8px 16px; border-radius: 16px; border: 1px solid var(--border-color); }
.input-wrapper textarea { flex: 1; background: transparent; border: none; outline: none; padding: 8px 0; resize: none; font-size: 15px; color: var(--text-main); max-height: 150px; }
.send-btn { width: 40px; height: 40px; border-radius: 12px; background: var(--primary-color); border: none; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: transform 0.2s; }
.send-btn:hover:not(:disabled) { transform: scale(1.05); }
.send-btn:disabled { opacity: 0.4; filter: grayscale(1); }
.send-btn svg { width: 20px; height: 20px; fill: #fff; transform: rotate(45deg); margin-left: -2px; }

@media (max-width: 900px) {
  .chat-shell { grid-template-columns: 1fr; }
  .prompt-sidebar { position: fixed; inset: 68px 0 0; z-index: 100; background: var(--bg-color); transform: translateX(-100%); padding: 24px; overflow-y: auto; }
  .prompt-sidebar.open { transform: translateX(0); }
  .message-row { max-width: 95%; }
}
</style>
