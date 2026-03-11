"use client";

import { motion, AnimatePresence } from 'framer-motion'
import { ArrowRight } from 'lucide-react'

/**
 * MenuVertical — animated vertical menu with sliding arrow + skew effect.
 * Adapted from Next.js/Tailwind original to React Router + plain CSS.
 *
 * Props:
 *   menuItems  { label, onClick, href? }[]   Menu entries
 *   color      string                         Hover accent colour (default: #a5f3fc)
 *   skew       number                         skewX on hover (default: 0)
 *   isOpen     boolean                        Controls visibility
 *   onClose    () => void                     Called when overlay is clicked
 */
export function MenuVertical({
  menuItems = [],
  color = '#a5f3fc',
  skew = -3,
  isOpen = false,
  onClose,
}) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="menu-vertical-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.22 }}
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            className="menu-vertical-panel"
            initial={{ x: '-100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '-100%', opacity: 0 }}
            transition={{ type: 'spring', stiffness: 260, damping: 30 }}
          >
            {/* Close button */}
            <button className="menu-vertical-close" onClick={onClose} aria-label="Close menu">
              ✕
            </button>

            <nav className="menu-vertical-list">
              {menuItems.map((item, index) => (
                <motion.div
                  key={index}
                  className="menu-vertical-item"
                  initial="initial"
                  whileHover="hover"
                >
                  {/* Sliding arrow */}
                  <motion.div
                    variants={{
                      initial: { x: '-140%', opacity: 0, color: 'inherit' },
                      hover: { x: 0, opacity: 1, color },
                    }}
                    transition={{ duration: 0.28, ease: 'easeOut' }}
                    className="menu-vertical-arrow"
                  >
                    <ArrowRight strokeWidth={3} size={28} />
                  </motion.div>

                  {/* Label */}
                  <motion.button
                    variants={{
                      initial: { x: -36, color: 'rgba(226, 232, 240, 0.85)' },
                      hover: { x: 0, color, skewX: skew },
                    }}
                    transition={{ duration: 0.28, ease: 'easeOut' }}
                    className="menu-vertical-label"
                    onClick={() => {
                      item.onClick?.()
                      onClose?.()
                    }}
                  >
                    {item.label}
                  </motion.button>
                </motion.div>
              ))}
            </nav>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

export default MenuVertical
