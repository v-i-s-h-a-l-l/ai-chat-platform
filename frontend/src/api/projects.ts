import { api } from './client'
import { streamChatMessage } from './streamChat'
import type {
  ChatMessage,
  ChatResponse,
  Project,
  ProjectCreate,
  ProjectUpdate,
  PromptOptimizationRequest,
  PromptOptimizationResponse,
} from '../types/project'

export const projectApi = {
  list(): Promise<Project[]> {
    return api.get<Project[]>('/projects').then((res) => res.data)
  },

  get(id: string): Promise<Project> {
    return api.get<Project>(`/projects/${id}`).then((res) => res.data)
  },

  create(data: ProjectCreate): Promise<Project> {
    return api.post<Project>('/projects', data).then((res) => res.data)
  },

  update(id: string, data: ProjectUpdate): Promise<Project> {
    return api.patch<Project>(`/projects/${id}`, data).then((res) => res.data)
  },

  duplicate(id: string): Promise<Project> {
    return api.post<Project>(`/projects/${id}/duplicate`).then((res) => res.data)
  },

  optimizePrompt(data: PromptOptimizationRequest): Promise<PromptOptimizationResponse> {
    return api
      .post<PromptOptimizationResponse>('/projects/optimize-prompt', data)
      .then((res) => res.data)
  },

  delete(id: string): Promise<void> {
    return api.delete(`/projects/${id}`).then(() => undefined)
  },

  getMessages(id: string): Promise<ChatMessage[]> {
    return api.get<ChatMessage[]>(`/projects/${id}/messages`).then((res) => res.data)
  },

  sendMessage(id: string, message: string, model: string): Promise<ChatResponse> {
    return api
      .post<ChatResponse>(`/projects/${id}/chat`, { message, model })
      .then((res) => res.data)
  },

  streamMessage: streamChatMessage,
}
