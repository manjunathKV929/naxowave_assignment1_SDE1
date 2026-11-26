import { 
  LayoutDashboard, 
  Stethoscope, 
  CalendarClock, 
  CalendarCheck2, 
  Activity, 
  PhoneCall, 
  CircleDot 
} from 'lucide-react'

interface SidebarProps {
  activeTab: string
  setActiveTab: (tab: string) => void
  onStartCall: () => void
  backendStatus: string
  appointmentCount: number
}

export const Sidebar = ({
  activeTab,
  setActiveTab,
  onStartCall,
  backendStatus,
  appointmentCount,
}: SidebarProps) => {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'doctors', label: 'Doctors', icon: Stethoscope },
    { id: 'availability', label: 'Available Slots', icon: CalendarClock },
    { id: 'appointments', label: 'Appointments', icon: CalendarCheck2, badge: appointmentCount > 0 ? appointmentCount : undefined },
    { id: 'activity', label: 'Recent Activity', icon: Activity },
  ]

  return (
    <aside className="w-64 bg-surface border-r border-border flex flex-col h-screen fixed left-0 top-0 z-20">
      {/* Brand Header */}
      <div className="p-5 border-b border-border flex items-center gap-3">
        <div className="w-9 h-9 rounded-lg bg-primary flex items-center justify-center text-white shadow-sm">
          <Stethoscope className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-base font-bold text-ink leading-tight tracking-tight">CareFlow AI</h1>
          <p className="text-xs text-muted-text">Clinical Appointment Suite</p>
        </div>
      </div>

      {/* Voice Call Action CTA */}
      <div className="p-4">
        <button
          onClick={onStartCall}
          className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-blue-700 text-white font-medium text-sm py-2.5 px-4 rounded-lg shadow-sm transition-all duration-150 active:scale-[0.98]"
        >
          <PhoneCall className="w-4 h-4" />
          <span>Try Voice Assistant</span>
        </button>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-2 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = activeTab === item.id
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary/10 text-primary'
                  : 'text-ink/80 hover:bg-background hover:text-ink'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? 'text-primary' : 'text-muted-text'}`} />
                <span>{item.label}</span>
              </div>
              {item.badge !== undefined && (
                <span className="bg-primary/15 text-primary text-xs font-semibold px-2 py-0.5 rounded-full">
                  {item.badge}
                </span>
              )}
            </button>
          )
        })}
      </nav>

      {/* System Health Status Footer */}
      <div className="p-4 border-t border-border bg-background/50">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-text font-medium flex items-center gap-1.5">
            <CircleDot className={`w-3.5 h-3.5 ${backendStatus === 'ok' ? 'text-positive' : 'text-warning'}`} />
            Backend System
          </span>
          <span className={`font-semibold capitalize px-2 py-0.5 rounded ${
            backendStatus === 'ok' ? 'bg-positive/10 text-positive' : 'bg-warning/10 text-warning'
          }`}>
            {backendStatus === 'ok' ? 'Online' : backendStatus}
          </span>
        </div>
      </div>
    </aside>
  )
}
