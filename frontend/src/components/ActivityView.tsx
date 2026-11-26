import { ActivityItem } from '../types'
import { Activity, CalendarCheck2, XCircle, Search, Radio, Clock } from 'lucide-react'

interface ActivityViewProps {
  activities: ActivityItem[]
}

export const ActivityView = ({ activities }: ActivityViewProps) => {
  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'appointment.created':
        return <CalendarCheck2 className="w-4 h-4 text-positive" />
      case 'appointment.cancelled':
        return <XCircle className="w-4 h-4 text-error" />
      case 'availability.checked':
        return <Search className="w-4 h-4 text-primary" />
      case 'voice.session.started':
        return <Radio className="w-4 h-4 text-indigo-500" />
      default:
        return <Activity className="w-4 h-4 text-muted-text" />
    }
  }

  const getEventBadge = (eventType: string) => {
    switch (eventType) {
      case 'appointment.created':
        return 'bg-positive/10 text-positive'
      case 'appointment.cancelled':
        return 'bg-error/10 text-error'
      case 'availability.checked':
        return 'bg-primary/10 text-primary'
      case 'voice.session.started':
        return 'bg-indigo-50 text-indigo-600'
      default:
        return 'bg-background text-muted-text'
    }
  }

  return (
    <div className="space-y-6">
      <div className="bg-surface border border-border rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-bold text-ink">System Audit Trail</h3>
            <p className="text-xs text-muted-text">Real-time chronicle of appointments, voice interactions, and schedule changes</p>
          </div>
          <span className="text-xs font-semibold bg-background px-3 py-1 rounded-full border border-border text-muted-text">
            {activities.length} Recorded Events
          </span>
        </div>

        {activities.length === 0 ? (
          <div className="py-12 text-center text-muted-text text-sm">
            No system activity recorded yet.
          </div>
        ) : (
          <div className="divide-y divide-border">
            {activities.map((item) => (
              <div key={item.id} className="py-3.5 flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-background border border-border shrink-0 mt-0.5">
                    {getEventIcon(item.event_type)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${getEventBadge(item.event_type)}`}>
                        {item.event_type.replace('.', ' ')}
                      </span>
                      {item.appointment_id && (
                        <span className="text-[11px] font-mono text-muted-text">
                          ID: {item.appointment_id}
                        </span>
                      )}
                    </div>
                    <p className="text-xs font-medium text-ink mt-1 leading-relaxed">
                      {item.description}
                    </p>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <span className="text-[11px] text-muted-text flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {new Date(item.timestamp).toLocaleString([], {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
