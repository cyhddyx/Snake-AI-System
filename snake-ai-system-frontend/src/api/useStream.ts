const BASE_URL = 'http://127.0.0.1:8002'

interface SSEMessage {
  type: 'thinking' | 'content' | 'done'
  content?: string
}

interface ChatCallbacks {
  onThinking?: (content: string) => void
  onContent?: (content: string) => void
  onDone?: () => void
  onError?: (error: Error) => void
}

export async function chatStream(query: string, callbacks: ChatCallbacks): Promise<void> {
  const response = await fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })

  if (!response.ok || !response.body) {
    throw new Error(`请求失败: ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const data: SSEMessage = JSON.parse(line.slice(6))

      switch (data.type) {
        case 'thinking':
          callbacks.onThinking?.(data.content ?? '')
          break
        case 'content':
          callbacks.onContent?.(data.content ?? '')
          break
        case 'done':
          callbacks.onDone?.()
          break
      }
    }
  }
}
