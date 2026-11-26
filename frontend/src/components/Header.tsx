import { PhoneCall, Sparkles } from 'lucide-react'

interface HeaderProps {
  title: string
  subtitle?: string
  onStartCall: () => void
}

export const Header = ({ title, subtitle, onStartCall }: HeaderProps) => {
  const currentDate = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  })

  return (
    <header className="h-16 bg-surface border-b border-border px-8 flex items-center justify-between sticky top-0 z-10">
      <div>
        <h2 className="text-lg font-bold text-ink tracking-tight">{title}</h2>
        {subtitle && <p className="text-xs text-muted-text">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-4">
        <span className="text-xs font-medium text-muted-text hidden md:inline-block">
          {currentDate}
        </span>

        <button
          onClick={onStartCall}
          className="flex items-center gap-2 bg-ink hover:bg-ink/90 text-white text-xs font-semibold py-2 px-3.5 rounded-lg transition-colors shadow-sm"
        >
          <PhoneCall className="w-3.5 h-3.5 text-primary" />
          <span>Launch Voice Call</span>
          <Sparkles className="w-3 h-3 text-yellow-400" />
        </button>
      </div>
    </header>
  )
}
