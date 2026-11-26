import { useState } from 'react'
import { Calendar, Clock, Stethoscope, Phone, AlertCircle, CheckCircle2, XCircle, Search } from 'lucide-react'
import { Appointment } from '../types'
import { api } from '../services/api'

interface AppointmentsViewProps {
  appointments: Appointment[]
  onRefresh: () => void
}

export const AppointmentsView = ({ appointments, onRefresh }: AppointmentsViewProps) => {
  const [filterStatus, setFilterStatus] = useState<'ALL' | 'CONFIRMED' | 'CANCELLED'>('ALL')
  const [searchPhone, setSearchPhone] = useState<string>('')
  const [cancellingId, setCancellingId] = useState<string | null>(null)
  const [cancelModalAppointment, setCancelModalAppointment] = useState<Appointment | null>(null)
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const filteredAppointments = appointments.filter((apt) => {
    const matchesStatus = filterStatus === 'ALL' || apt.status === filterStatus
    const matchesPhone = searchPhone ? apt.patient_phone.includes(searchPhone) : true
    return matchesStatus && matchesPhone
  })

  const handleCancelAppointment = async (appointmentId: string) => {
    setCancellingId(appointmentId)
    setActionMessage(null)
    try {
      await api.cancelAppointment(appointmentId)
      setActionMessage({ type: 'success', text: 'Appointment cancelled successfully.' })
      setCancelModalAppointment(null)
      onRefresh()
    } catch (err: any) {
      setActionMessage({ type: 'error', text: err.message || 'Failed to cancel appointment.' })
    } finally {
      setCancellingId(null)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header & Filter Controls */}
      <div className="bg-surface border border-border rounded-xl p-4 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Status Tabs */}
        <div className="flex items-center gap-1.5 w-full md:w-auto">
          {(['ALL', 'CONFIRMED', 'CANCELLED'] as const).map((status) => (
            <button
              key={status}
              onClick={() => setFilterStatus(status)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition-colors ${
                filterStatus === status
                  ? 'bg-primary text-white shadow-sm'
                  : 'bg-background hover:bg-border/60 text-muted-text'
              }`}
            >
              {status.toLowerCase()} ({status === 'ALL' ? appointments.length : appointments.filter((a) => a.status === status).length})
            </button>
          ))}
        </div>

        {/* Search by masked phone */}
        <div className="relative w-full md:w-64">
          <Search className="w-4 h-4 text-muted-text absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by phone suffix..."
            value={searchPhone}
            onChange={(e) => setSearchPhone(e.target.value)}
            className="w-full bg-background border border-border rounded-lg pl-9 pr-3 py-1.5 text-xs text-ink placeholder:text-muted-text focus:outline-none focus:border-primary font-mono"
          />
        </div>
      </div>

      {actionMessage && (
        <div
          className={`p-3 rounded-lg text-xs flex items-center justify-between gap-2 ${
            actionMessage.type === 'success'
              ? 'bg-positive/10 text-positive border border-positive/20'
              : 'bg-error/10 text-error border border-error/20'
          }`}
        >
          <div className="flex items-center gap-2">
            {actionMessage.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 shrink-0" />
            )}
            <span>{actionMessage.text}</span>
          </div>
          <button onClick={() => setActionMessage(null)} className="text-xs font-bold px-1">
            ✕
          </button>
        </div>
      )}

      {/* Appointments Data Table */}
      <div className="bg-surface border border-border rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          {filteredAppointments.length === 0 ? (
            <div className="p-12 text-center text-muted-text text-sm">
              No appointments found matching this filter.
            </div>
          ) : (
            <table className="w-full text-left text-xs">
              <thead className="bg-background/80 text-muted-text font-semibold border-b border-border">
                <tr>
                  <th className="py-3 px-5">Doctor & Speciality</th>
                  <th className="py-3 px-5">Date & Time</th>
                  <th className="py-3 px-5">Patient Phone (Masked)</th>
                  <th className="py-3 px-5">Status</th>
                  <th className="py-3 px-5">Booked At</th>
                  <th className="py-3 px-5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredAppointments.map((apt) => (
                  <tr key={apt.id} className="hover:bg-background/50 transition-colors">
                    <td className="py-3.5 px-5">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-full bg-blue-50 text-primary flex items-center justify-center font-bold text-xs shrink-0">
                          <Stethoscope className="w-3.5 h-3.5" />
                        </div>
                        <div>
                          <p className="font-bold text-ink">{apt.doctor_name}</p>
                          <p className="text-[11px] text-muted-text">{apt.speciality}</p>
                        </div>
                      </div>
                    </td>

                    <td className="py-3.5 px-5">
                      <div className="space-y-0.5">
                        <p className="font-medium text-ink flex items-center gap-1.5">
                          <Calendar className="w-3 h-3 text-muted-text" /> {apt.date}
                        </p>
                        <p className="text-[11px] text-muted-text flex items-center gap-1.5">
                          <Clock className="w-3 h-3 text-muted-text" /> {apt.time}
                        </p>
                      </div>
                    </td>

                    <td className="py-3.5 px-5 font-mono text-ink font-medium">
                      <span className="flex items-center gap-1.5">
                        <Phone className="w-3 h-3 text-muted-text" />
                        {apt.patient_phone}
                      </span>
                    </td>

                    <td className="py-3.5 px-5">
                      <span
                        className={`inline-block px-2.5 py-0.5 rounded text-[11px] font-semibold ${
                          apt.status === 'CONFIRMED'
                            ? 'bg-positive/10 text-positive'
                            : 'bg-error/10 text-error'
                        }`}
                      >
                        {apt.status}
                      </span>
                    </td>

                    <td className="py-3.5 px-5 text-muted-text text-[11px]">
                      {new Date(apt.created_at).toLocaleString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>

                    <td className="py-3.5 px-5 text-right">
                      {apt.status === 'CONFIRMED' ? (
                        <button
                          onClick={() => setCancelModalAppointment(apt)}
                          disabled={cancellingId === apt.id}
                          className="px-2.5 py-1 text-xs font-semibold text-error hover:bg-error/10 rounded transition-colors"
                        >
                          Cancel
                        </button>
                      ) : (
                        <span className="text-muted-text text-[11px] italic">Cancelled</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Confirmation Modal for Cancellation */}
      {cancelModalAppointment && (
        <div className="fixed inset-0 bg-ink/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-surface border border-border rounded-xl max-w-sm w-full p-6 shadow-xl space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-full bg-error/10 text-error flex items-center justify-center shrink-0">
                <XCircle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-ink">Cancel Appointment?</h3>
                <p className="text-xs text-muted-text mt-1 leading-relaxed">
                  Are you sure you want to cancel the appointment with{' '}
                  <span className="font-semibold text-ink">{cancelModalAppointment.doctor_name}</span> on{' '}
                  <span className="font-semibold text-ink">
                    {cancelModalAppointment.date} at {cancelModalAppointment.time}
                  </span>
                  ? This will release the slot back to the clinic's schedule.
                </p>
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={() => setCancelModalAppointment(null)}
                className="w-1/2 bg-background hover:bg-border/60 text-ink text-xs font-semibold py-2 rounded-lg border border-border"
              >
                Keep Appointment
              </button>
              <button
                type="button"
                onClick={() => handleCancelAppointment(cancelModalAppointment.id)}
                disabled={cancellingId === cancelModalAppointment.id}
                className="w-1/2 bg-error hover:bg-red-700 disabled:opacity-50 text-white text-xs font-semibold py-2 rounded-lg shadow-sm"
              >
                {cancellingId === cancelModalAppointment.id ? 'Cancelling...' : 'Yes, Cancel'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
