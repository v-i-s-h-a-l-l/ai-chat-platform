import { api, getErrorMessage } from './client'

export interface TranscribeResponse {
  text: string
}

export const speechApi = {
  transcribe(blob: Blob, filename = 'recording.webm'): Promise<TranscribeResponse> {
    const form = new FormData()
    form.append('file', blob, filename)
    return api
      .post<TranscribeResponse>('/speech/transcribe', form, {
        timeout: 35_000,
      })
      .then((res) => res.data)
  },
}

export { getErrorMessage as getSpeechErrorMessage }
