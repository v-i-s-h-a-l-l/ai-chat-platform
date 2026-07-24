import { useCallback, useEffect, useLayoutEffect, useRef, useState, type RefObject } from 'react'

const NEAR_BOTTOM_PX = 80
const SHOW_BUTTON_PX = 120

interface UseChatAutoScrollOptions {
  containerRef: RefObject<HTMLElement | null>
  observeTargetRef: RefObject<HTMLElement | null>
  bottomSentinelRef: RefObject<HTMLElement | null>
  messageCount: number
  streamingId: string | null
}

export interface ChatAutoScrollApi {
  showScrollToBottom: boolean
  newMessageCount: number
  scrollToBottom: () => void
}

function distanceFromBottom(el: HTMLElement): number {
  return el.scrollHeight - el.scrollTop - el.clientHeight
}

export function useChatAutoScroll({
  containerRef,
  observeTargetRef,
  bottomSentinelRef,
  messageCount,
  streamingId,
}: UseChatAutoScrollOptions): ChatAutoScrollApi {
  const shouldAutoScrollRef = useRef(true)
  const prevMessageCountRef = useRef(messageCount)
  const prevStreamingIdRef = useRef<string | null>(streamingId)
  const newMessageCountRef = useRef(0)
  const showRef = useRef(false)

  const [showScrollToBottom, setShowScrollToBottom] = useState(false)
  const [newMessageCount, setNewMessageCount] = useState(0)

  const setShow = useCallback((next: boolean) => {
    if (showRef.current === next) return
    showRef.current = next
    setShowScrollToBottom(next)
  }, [])

  const syncUi = useCallback(() => {
    const container = containerRef.current
    if (!container) return

    const scrollTop = container.scrollTop
    const scrollHeight = container.scrollHeight
    const clientHeight = container.clientHeight
    const distance = scrollHeight - scrollTop - clientHeight
    const scrollable = scrollHeight > clientHeight + 1
    const show = scrollable && distance > SHOW_BUTTON_PX

    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.log('[scroll-to-bottom]', {
        scrollTop,
        scrollHeight,
        clientHeight,
        distanceFromBottom: distance,
        scrollable,
        showButton: show,
        stickToBottom: shouldAutoScrollRef.current,
      })
    }

    setShow(show)

    if (distance <= NEAR_BOTTOM_PX) {
      shouldAutoScrollRef.current = true
      if (newMessageCountRef.current !== 0) {
        newMessageCountRef.current = 0
        setNewMessageCount(0)
      }
    }
  }, [containerRef, setShow])

  const scrollToBottom = useCallback(() => {
    const container = containerRef.current
    if (!container) return

    shouldAutoScrollRef.current = true
    newMessageCountRef.current = 0
    setNewMessageCount(0)
    setShow(false)

    container.scrollTo({
      top: container.scrollHeight,
      behavior: 'smooth',
    })
  }, [containerRef, setShow])

  const followBottom = useCallback(
    (behavior: ScrollBehavior) => {
      const container = containerRef.current
      if (!container || !shouldAutoScrollRef.current) return
      container.scrollTo({ top: container.scrollHeight, behavior })
    },
    [containerRef],
  )

  useLayoutEffect(() => {
    const container = containerRef.current
    const sentinel = bottomSentinelRef.current
    if (!container) {
      if (import.meta.env.DEV) {
        // eslint-disable-next-line no-console
        console.warn('[scroll-to-bottom] scroll container ref is null')
      }
      return
    }

    const scrollEl = container

    function onScroll() {
      const distance = distanceFromBottom(scrollEl)
      shouldAutoScrollRef.current = distance <= NEAR_BOTTOM_PX
      syncUi()
    }

    scrollEl.addEventListener('scroll', onScroll, { passive: true })

    let io: IntersectionObserver | undefined
    if (sentinel) {
      io = new IntersectionObserver(
        () => syncUi(),
        {
          root: container,
          threshold: 0,
          rootMargin: `0px 0px -${SHOW_BUTTON_PX}px 0px`,
        },
      )
      io.observe(sentinel)
    }

    const ro = new ResizeObserver(() => {
      if (shouldAutoScrollRef.current) {
        followBottom('auto')
      }
      syncUi()
    })
    ro.observe(container)
    if (observeTargetRef.current) {
      ro.observe(observeTargetRef.current)
    }

    syncUi()

    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.log('[scroll-to-bottom] listener attached', {
        clientHeight: container.clientHeight,
        scrollHeight: container.scrollHeight,
      })
    }

    return () => {
      scrollEl.removeEventListener('scroll', onScroll)
      io?.disconnect()
      ro.disconnect()
    }
  }, [containerRef, bottomSentinelRef, observeTargetRef, syncUi, followBottom])

  useEffect(() => {
    const streamStarted = Boolean(streamingId && streamingId !== prevStreamingIdRef.current)
    const added = messageCount - prevMessageCountRef.current

    if (streamStarted) {
      shouldAutoScrollRef.current = true
      newMessageCountRef.current = 0
      setNewMessageCount(0)
      followBottom('smooth')
    } else if (added > 0) {
      if (shouldAutoScrollRef.current) {
        followBottom('smooth')
      } else {
        newMessageCountRef.current += added
        setNewMessageCount(newMessageCountRef.current)
        syncUi()
      }
    }

    prevMessageCountRef.current = messageCount
    prevStreamingIdRef.current = streamingId
  }, [messageCount, streamingId, followBottom, syncUi])

  return { showScrollToBottom, newMessageCount, scrollToBottom }
}
