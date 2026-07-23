export interface Project {
  id: string
  name: string
  description: string
  system_prompt: string
  created_at: string
}

export interface ProjectCreate {
  name: string
  description: string
  system_prompt: string
}

export interface PromptOptimizationRequest {
  project_name: string
  description: string
  system_prompt: string
}

export interface PromptOptimizationResponse {
  safe: boolean
  reason: string | null
  original_prompt: string
  improved_prompt: string | null
  changes: string[]
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
  web_search_used?: boolean
}

export interface ChatResponse {
  user_message: ChatMessage
  assistant_message: ChatMessage
  web_search_used: boolean
}
