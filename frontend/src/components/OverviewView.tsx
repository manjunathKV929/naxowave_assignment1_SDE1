import { Stethoscope, CalendarClock, CalendarCheck2, Activity, ArrowRight, PhoneCall, CheckCircle2 } from 'lucide-react'
import { Doctor, Appointment, ActivityItem } from '../types'

interface OverviewViewProps {
  doctors: Doctor[]
  appointments: Appointment[]
  activities: ActivityItem[]
  onNavigate: (tab: string) => void
  onStartCall: () => void
}

export const OverviewView = ({
  doctors,
  appointments,
  activities,
  onNavigate,
  onStartCall,
}: OverviewViewProps) => {
  const confirmedAppointments = appointments.filter((a) => a.status === 'CONFIRMED')
  const activeDoctors = doctors.filter((d) => d.is_active)

  return (
    <div className="space-y-6">
      {/* Voice Assistant Call-out Banner */}
      <div className="bg-gradient-to-r from-blue-900 to-indigo-950 text-white rounded-xl p-6 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/20 text-blue-200 border border-blue-400/20 mb-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            Real-time Voice Pipeline Online
          </div>
          <h3 className="text-xl font-bold tracking-tight">Need to book or reschedule a consultation?</h3>
          <p className="text-sm text-blue-200 max-w-xl">
            Experience our voice-first healthcare agent. Speak naturally to check doctor schedules, book visits, or cancel appointments with spoken phone confirmation.
          </p>
        </div>
        <button
          onClick={onStartCall}
          className="flex items-center gap-2.5 bg-primary hover:bg-blue-600 text-white font-semibold text-sm px-5 py-3 rounded-lg shadow-md transition-all duration-150 active:scale-95 whitespace-nowrap"
        >
          <PhoneCall className="w-4 h-4" />
          <span>Try Voice Assistant</span>
        </button>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-surface border border-border rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-text">Active Doctors</span>
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-primary flex items-center justify-center">
              <Stethoscope className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-ink">{activeDoctors.length}</span>
            <p className="text-xs text-muted-text mt-0.5">Across 7 medical specialities</p>
          </div>
        </div>

        <div className="bg-surface border border-border rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-text">Total Appointments</span>
            <div className="w-8 h-8 rounded-lg bg-green-50 text-positive flex items-center justify-center">
              <CalendarCheck2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-ink">{appointments.length}</span>
            <p className="text-xs text-positive font-medium mt-0.5 flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> {confirmedAppointments.length} confirmed
            </p>
          </div>
        </div>

        <div className="bg-surface border border-border rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-text">Seeded Slots</span>
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <CalendarClock className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-ink">168+</span>
            <p className="text-xs text-muted-text mt-0.5">Available for voice & web booking</p>
          </div>
        </div>

        <div className="bg-surface border border-border rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-text">Pipeline Status</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-emerald-700">Healthy</span>
            <p className="text-xs text-muted-text mt-0.5">Pipecat + ElevenLabs + Gemini</p>
          </div>
        </div>
      </div>

      {/* Two Column Layout: Upcoming Appointments & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Appointments Preview (2 cols) */}
        <div className="lg:col-span-2 bg-surface border border-border rounded-xl shadow-sm overflow-hidden">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <div>
              <h4 className="text-sm font-bold text-ink">Upcoming Appointments</h4>
              <p className="text-xs text-muted-text">Recent patient bookings from voice and web</p>
            </div>
            <button
              onClick={() => onNavigate('appointments')}
              className="text-xs font-semibold text-primary hover:text-blue-700 flex items-center gap-1"
            >
              View all <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="overflow-x-auto">
            {appointments.length === 0 ? (
              <div className="p-8 text-center text-muted-text text-sm">
                No appointments booked yet. Launch the voice assistant to book one!
              </div>
            ) : (
              <table className="w-full text-left text-xs">
                <thead className="bg-background/80 text-muted-text font-semibold border-b border-border">
                  <tr>
                    <th className="py-2.5 px-4">Doctor</th>
                    <th className="py-2.5 px-4">Speciality</th>
                    <th className="py-2.5 px-4">Date & Time</th>
                    <th className="py-2.5 px-4">Phone</th>
                    <th className="py-2.5 px-4">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {appointments.slice(0, 5).map((apt) => (
                    <tr key={apt.id} className="hover:bg-background/50 transition-colors">
                      <td className="py-3 px-4 font-semibold text-ink">{apt.doctor_name}</td>
                      <td className="py-3 px-4 text-muted-text">{apt.speciality}</td>
                      <td className="py-3 px-4 text-ink">
                        {apt.date} at {apt.time}
                      </td>
                      <td className="py-3 px-4 font-mono text-muted-text">{apt.patient_phone}</td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[11px] font-semibold ${
                            apt.status === 'CONFIRMED'
                              ? 'bg-positive/10 text-positive'
                              : 'bg-error/10 text-error'
                          }`}
                        >
                          {apt.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Activity Feed Preview (1 col) */}
        <div className="bg-surface border border-border rounded-xl shadow-sm flex flex-col">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <div>
              <h4 className="text-sm font-bold text-ink">Recent Activity</h4>
              <p className="text-xs text-muted-text">Live event stream</p>
            </div>
            <button
              onClick={() => onNavigate('activity')}
              className="text-xs font-semibold text-primary hover:text-blue-700 flex items-center gap-1"
            >
              History <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="p-4 flex-1 overflow-y-auto space-y-3.5 max-h-[340px]">
            {activities.length === 0 ? (
              <p className="text-xs text-muted-text text-center py-6">No recent events</p>
            ) : (
              activities.slice(0, 6).map((item) => (
                <div key={item.id} className="flex items-start gap-2.5 text-xs">
                  <div className="w-2 h-2 rounded-full bg-primary mt-1.5 shrink-0"></div>
                  <div>
                    <p className="text-ink font-medium leading-relaxed">{item.description}</p>
                    <span className="text-[10px] text-muted-text">
                      {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
