import axios from 'axios'

export interface UploadConfirmationDetail {
  message: string
  code: 'upload_confirmation_required'
  document_type?: string | null
  confidence?: number | null
}

export function isUploadConfirmationDetail(detail: unknown): detail is UploadConfirmationDetail {
  return (
    typeof detail === 'object' &&
    detail !== null &&
    'code' in detail &&
    (detail as UploadConfirmationDetail).code === 'upload_confirmation_required'
  )
}

export function parseUploadConfirmationError(error: unknown): UploadConfirmationDetail | null {
  if (typeof error !== 'object' || error === null) return null
  const axiosError = error as { response?: { status?: number; data?: { detail?: unknown } } }
  if (axiosError.response?.status !== 409) return null
  const detail = axiosError.response.data?.detail
  if (isUploadConfirmationDetail(detail)) return detail
  return null
}
