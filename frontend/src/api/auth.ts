import { api } from './client'
import type {
  LoginCredentials,
  MessageResponse,
  RegisterCredentials,
  User,
  UserUpdate,
} from '../types/auth'

export const authApi = {
  register(data: RegisterCredentials): Promise<MessageResponse> {
    return api.post<MessageResponse>('/auth/register', data).then((res) => res.data)
  },

  login(data: LoginCredentials): Promise<MessageResponse> {
    return api.post<MessageResponse>('/auth/login', data).then((res) => res.data)
  },

  logout(): Promise<MessageResponse> {
    return api.post<MessageResponse>('/auth/logout').then((res) => res.data)
  },

  refresh(): Promise<MessageResponse> {
    return api.post<MessageResponse>('/auth/refresh').then((res) => res.data)
  },
}

export const userApi = {
  getMe(): Promise<User> {
    return api.get<User>('/users/me', { skipAuthRefresh: true }).then((res) => res.data)
  },

  updateMe(data: UserUpdate): Promise<User> {
    return api.patch<User>('/users/me', data).then((res) => res.data)
  },
}
