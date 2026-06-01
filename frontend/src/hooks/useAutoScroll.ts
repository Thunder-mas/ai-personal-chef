import { useEffect, useRef } from 'react'

export function useAutoScroll<T>(
  containerRef: React.RefObject<HTMLDivElement | null>,
  dependency: T
) {
  const isAtBottom = useRef(true)

  useEffect(() => {
    const el = containerRef.current
    if (!el) return

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = el
      isAtBottom.current = scrollHeight - scrollTop - clientHeight < 100
    }

    el.addEventListener('scroll', handleScroll)
    return () => el.removeEventListener('scroll', handleScroll)
  }, [containerRef])

  useEffect(() => {
    if (isAtBottom.current && containerRef.current) {
      containerRef.current.scrollTo({
        top: containerRef.current.scrollHeight,
        behavior: 'smooth',
      })
    }
  }, [dependency, containerRef])
}
