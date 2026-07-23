import { useEffect, useRef, type RefObject } from 'react'

const NEAR_BOTTOM_THRESHOLD = 100

interface UseChatAutoScrollOptions {
  containerRef: RefObject<HTMLElement | null>
  observeTargetRef: RefObject<HTMLElement | null>
  messageCount: number
  streamingId: string | null
}

export function useChatAutoScroll({
  containerRef,
  observeTargetRef,
  messageCount,
  streamingId,
}: UseChatAutoScrollOptions) {
  const shouldAutoScrollRef = useRef(true)
  const prevMessageCountRef = useRef(messageCount)
  const prevStreamingIdRef = useRef<string | null>(streamingId)
  const rafScrollRef = useRef<number | null>(null)

  function scheduleScroll(behavior: ScrollBehavior) {
    const container = containerRef.current
    if (!container || !shouldAutoScrollRef.current) return

    if (rafScrollRef.current !== null) {
      cancelAnimationFrame(rafScrollRef.current)
    }

    rafScrollRef.current = requestAnimationFrame(() => {
      container.scrollTo({ top: container.scrollHeight, behavior })
      rafScrollRef.current = null
    })
  }

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const scrollEl = container
    let lastScrollTop = scrollEl.scrollTop

    function onScroll() {
      const distanceFromBottom =
        scrollEl.scrollHeight - scrollEl.scrollTop - scrollEl.clientHeight

      if (
        scrollEl.scrollTop < lastScrollTop &&
        distanceFromBottom > NEAR_BOTTOM_THRESHOLD
      ) {
        shouldAutoScrollRef.current = false
      }

      if (distanceFromBottom <= NEAR_BOTTOM_THRESHOLD) {
        shouldAutoScrollRef.current = true
      }

      lastScrollTop = scrollEl.scrollTop
    }

    scrollEl.addEventListener('scroll', onScroll, { passive: true })
    return () => scrollEl.removeEventListener('scroll', onScroll)
  }, [containerRef])

  useEffect(() => {
    const newMessages = messageCount > prevMessageCountRef.current
    const streamStarted = Boolean(streamingId && streamingId !== prevStreamingIdRef.current)

    if (newMessages || streamStarted) {
      shouldAutoScrollRef.current = true
      scheduleScroll('smooth')
    }

    prevMessageCountRef.current = messageCount
    prevStreamingIdRef.current = streamingId
  }, [messageCount, streamingId])

  useEffect(() => {
    const container = containerRef.current
    const target = observeTargetRef.current
    if (!container || !target) return

    const observer = new ResizeObserver(() => {
      if (!shouldAutoScrollRef.current) return

      const distanceFromBottom =
        container.scrollHeight - container.scrollTop - container.clientHeight

      if (distanceFromBottom <= NEAR_BOTTOM_THRESHOLD + 20) {
        scheduleScroll('auto')
      }
    })

    observer.observe(target)
    return () => observer.disconnect()
  }, [containerRef, observeTargetRef])

  useEffect(() => {
    return () => {
      if (rafScrollRef.current !== null) {
        cancelAnimationFrame(rafScrollRef.current)
      }
    }
  }, [])
}
