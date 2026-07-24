import { describe, expect, it, vi } from 'vitest'

describe('refreshAccessToken single-flight', () => {
  it('shares one in-flight refresh promise', async () => {
    vi.resetModules()

    const post = vi.fn(
      () =>
        new Promise<{ data: { message: string } }>((resolve) => {
          setTimeout(() => resolve({ data: { message: 'ok' } }), 30)
        }),
    )

    vi.doMock('axios', async () => {
      const actual = await vi.importActual<typeof import('axios')>('axios')
      return {
        ...actual,
        default: {
          ...actual.default,
          create: () => ({
            post,
            interceptors: { response: { use: vi.fn() } },
            defaults: { headers: {} },
          }),
        },
      }
    })

    const { refreshAccessToken } = await import('../api/client')
    await Promise.all([refreshAccessToken(), refreshAccessToken()])
    expect(post).toHaveBeenCalledTimes(1)
  })
})
