import { motion } from 'framer-motion'

const container = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.04, delayChildren: 0.1 },
  },
}

const letter = {
  hidden: { opacity: 0, y: '0.3em' },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.25, ease: [0.2, 0.65, 0.3, 0.9] },
  },
}

export default function AnimatedText({ text, className = '' }: { text: string; className?: string }) {
  return (
    <motion.span
      className={className}
      variants={container}
      initial="hidden"
      animate="visible"
      style={{ display: 'inline-flex', flexWrap: 'wrap' }}
    >
      {text.split('').map((char, i) => (
        <motion.span key={i} variants={letter} style={{ display: 'inline-block' }}>
          {char === ' ' ? '\u00A0' : char}
        </motion.span>
      ))}
    </motion.span>
  )
}
