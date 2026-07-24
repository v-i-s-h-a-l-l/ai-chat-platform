export interface User {
  id: string
  name: string
  email: string
  preferred_llm_model?: string | null
}

export interface UserUpdate {
  preferred_llm_model?: string | null
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterCredentials {
  name: string
  email: string
  password: string
}

export interface MessageResponse {
  message: string
}

export interface ApiError {
  detail: string
}
