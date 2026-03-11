import { useMemo } from 'react'
import { motion } from 'framer-motion'

/**
 * TextShimmer — animated light-sweep text component.
 * Works with plain CSS (no Tailwind required).
 *
 * Props:
 *   children  string          The text to animate
 *   as        ElementType     HTML tag to render (default: 'p')
 *   className string          Extra CSS classes
 *   duration  number          Sweep duration in seconds (default: 2)
 *   spread    number          Spread multiplier per character (default: 2)
 *   baseColor string          The resting text color
 *   glowColor string          The sweep highlight color
 */
export function TextShimmer({
  children,
  as: Component = 'p',
  className = '',
  duration = 2,
  spread = 2,
  baseColor = 'rgba(148, 163, 184, 0.65)',
  glowColor = '#ffffff',
}) {
  const MotionComponent = motion.create(Component)
  const dynamicSpread = useMemo(() => children.length * spread, [children, spread])

  return (
    <MotionComponent
      className={className}
      initial={{ backgroundPosition: '100% center' }}
      animate={{ backgroundPosition: '0% center' }}
      transition={{ repeat: Infinity, duration, ease: 'linear' }}
      style={{
        '--spread': `${dynamicSpread}px`,
        backgroundImage: [
          `linear-gradient(90deg,`,
          `  transparent calc(50% - var(--spread)),`,
          `  ${glowColor},`,
          `  transparent calc(50% + var(--spread))`,
          `),`,
          `linear-gradient(${baseColor}, ${baseColor})`,
        ].join(' '),
        backgroundSize: '250% 100%, auto',
        backgroundRepeat: 'no-repeat, padding-box',
        WebkitBackgroundClip: 'text',
        backgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        color: 'transparent',
        display: 'inline-block',
      }}
    >
      {children}
    </MotionComponent>
  )
}

export default TextShimmer
