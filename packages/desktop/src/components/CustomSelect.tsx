import { useState, useRef, useEffect } from 'react'
import { ChevronDown, Check } from 'lucide-react'

interface Option {
  value: string
  label: string
}

interface CustomSelectProps {
  value: string
  onChange: (value: string) => void
  options: Option[]
  placeholder?: string
  className?: string
}

export default function CustomSelect({ value, onChange, options, placeholder, className = '' }: CustomSelectProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const selected = options.find((o) => o.value === value)

  // 点击外部关闭
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={ref} className={`relative ${className}`}>
      {/* Trigger */}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full input-field flex items-center justify-between gap-2 text-left"
      >
        <span className={selected ? 'text-white' : 'text-imeet-text-muted'}>
          {selected?.label || placeholder || 'Select...'}
        </span>
        <ChevronDown size={14} className={`text-imeet-text-muted transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute z-50 top-full left-0 right-0 mt-1 bg-imeet-card border border-imeet-border rounded-lg shadow-xl overflow-hidden py-1 max-h-60 overflow-y-auto">
          {options.map((opt) => (
            <button
              key={opt.value}
              onClick={() => { onChange(opt.value); setOpen(false) }}
              className={`w-full px-4 py-2.5 text-left text-sm flex items-center justify-between transition-colors ${
                opt.value === value
                  ? 'bg-imeet-gold/10 text-imeet-gold'
                  : 'text-white/80 hover:bg-white/5'
              }`}
            >
              {opt.label}
              {opt.value === value && <Check size={14} className="text-imeet-gold" />}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
