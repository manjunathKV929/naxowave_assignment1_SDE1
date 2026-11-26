import { useState, useEffect, FormEvent } from 'react'
import { Calendar, Clock, Stethoscope, CheckCircle2, AlertCircle } from 'lucide-react'
import { Doctor, DoctorAvailability } from '../types'
import { api } from '../services/api'

interface AvailabilityViewProps {
  doctors: Doctor[]
  onAppointmentBooked: () => void
}

export const AvailabilityView = ({ doctors, onAppointmentBooked }: AvailabilityViewProps) => {
  const [selectedSpeciality, setSelectedSpeciality] = useState<string>('All')
  const [selectedDoctorId, setSelectedDoctorId] = useState<string>('All')
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().split('T')[0]
  )
  const [availabilities, setAvailabilities] = useState<DoctorAvailability[]>([])
  const [loading, setLoading] = useState<boolean>(false)
  const [bookingModalSlot, setBookingModalSlot] = useState<{
    doctorId: string
    doctorName: string
    slotId: string
    time: string
    date: string
  } | null>(null)
  const [phoneNumberInput, setPhoneNumberInput] = useState<string>('')
  const [bookingStatus, setBookingStatus] = useState<string | null>(null)
  const [bookingError, setBookingError] = useState<string | null>(null)

  useEffect(() => {
    fetchAvailability()
  }, [selectedSpeciality, selectedDoctorId, selectedDate])

  const fetchAvailability = async () => {
    setLoading(true)
    try {
      const spec = selectedSpeciality === 'All' ? undefined : selectedSpeciality
      const res = await api.searchAvailability(spec, selectedDate)
      let list = res.availability || []
      if (selectedDoctorId !== 'All') {
        list = list.filter((a) => a.doctor_id === selectedDoctorId)
      }
      setAvailabilities(list)
    } catch (err) {
      console.error('Failed to load availability:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleBookSlot = async (e: FormEvent) => {
    e.preventDefault()
    if (!bookingModalSlot) return
    setBookingStatus('Booking appointment...')
    setBookingError(null)

    try {
      await api.bookAppointment({
        phone_number: phoneNumberInput,
        doctor_id: bookingModalSlot.doctorId,
        slot_id: bookingModalSlot.slotId,
      })
      setBookingStatus('Appointment confirmed successfully!')
      setTimeout(() => {
        setBookingModalSlot(null)
        setPhoneNumberInput('')
        setBookingStatus(null)
        fetchAvailability()
        onAppointmentBooked()
      }, 1000)
    } catch (err: any) {
      setBookingError(err.message || 'Failed to book slot.')
      setBookingStatus(null)
    }
  }

  // Aggregate all slots across returned doctors
  const allSlots = availabilities.flatMap((a) =>
    a.slots.map((s) => ({
      ...s,
      doctor_name: a.doctor_name,
      speciality: a.speciality,
    }))
  )

  const morningSlots = allSlots.filter((s) => s.start_time < '12:00')
  const afternoonSlots = allSlots.filter((s) => s.start_time >= '12:00' && s.start_time < '16:00')
  const eveningSlots = allSlots.filter((s) => s.start_time >= '16:00')

  return (
    <div className="space-y-6">
      {/* Filter Controls Header */}
      <div className="bg-surface border border-border rounded-xl p-4 shadow-sm grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Date Selector */}
        <div>
          <label className="block text-xs font-semibold text-muted-text mb-1 flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5 text-primary" /> Select Consultation Date
          </label>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="w-full bg-background border border-border rounded-lg px-3 py-1.5 text-xs text-ink focus:outline-none focus:border-primary"
          />
        </div>

        {/* Speciality Filter */}
        <div>
          <label className="block text-xs font-semibold text-muted-text mb-1 flex items-center gap-1.5">
            <Stethoscope className="w-3.5 h-3.5 text-primary" /> Filter by Speciality
          </label>
          <select
            value={selectedSpeciality}
            onChange={(e) => {
              setSelectedSpeciality(e.target.value)
              setSelectedDoctorId('All')
            }}
            className="w-full bg-background border border-border rounded-lg px-3 py-1.5 text-xs text-ink focus:outline-none focus:border-primary"
          >
            <option value="All">All Specialities</option>
            <option value="Cardiology">Cardiology</option>
            <option value="Dermatology">Dermatology</option>
            <option value="Pediatrics">Pediatrics</option>
            <option value="General Medicine">General Medicine</option>
            <option value="Orthopedics">Orthopedics</option>
            <option value="Neurology">Neurology</option>
          </select>
        </div>

        {/* Doctor Filter */}
        <div>
          <label className="block text-xs font-semibold text-muted-text mb-1">
            Filter by Doctor
          </label>
          <select
            value={selectedDoctorId}
            onChange={(e) => setSelectedDoctorId(e.target.value)}
            className="w-full bg-background border border-border rounded-lg px-3 py-1.5 text-xs text-ink focus:outline-none focus:border-primary"
          >
            <option value="All">All Doctors</option>
            {doctors.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.speciality})
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="bg-surface border border-border rounded-xl p-12 text-center text-sm text-muted-text">
          Loading doctor availability...
        </div>
      ) : (
        <div className="space-y-6">
          {/* Morning Slots */}
          <div className="bg-surface border border-border rounded-xl p-5 shadow-sm">
            <h4 className="text-xs font-bold text-ink uppercase tracking-wider mb-3 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-amber-500"></span> Morning Sessions (09:00 - 12:00)
            </h4>
            {morningSlots.length === 0 ? (
              <p className="text-xs text-muted-text">No morning slots for this selection.</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {morningSlots.map((slot) => (
                  <SlotCard
                    key={slot.id}
                    slot={slot}
                    onBook={() =>
                      setBookingModalSlot({
                        doctorId: slot.doctor_id,
                        doctorName: slot.doctor_name,
                        slotId: slot.id,
                        time: `${slot.start_time} - ${slot.end_time}`,
                        date: slot.date,
                      })
                    }
                  />
                ))}
              </div>
            )}
          </div>

          {/* Afternoon Slots */}
          <div className="bg-surface border border-border rounded-xl p-5 shadow-sm">
            <h4 className="text-xs font-bold text-ink uppercase tracking-wider mb-3 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-blue-500"></span> Afternoon Sessions (12:00 - 16:00)
            </h4>
            {afternoonSlots.length === 0 ? (
              <p className="text-xs text-muted-text">No afternoon slots for this selection.</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {afternoonSlots.map((slot) => (
                  <SlotCard
                    key={slot.id}
                    slot={slot}
                    onBook={() =>
                      setBookingModalSlot({
                        doctorId: slot.doctor_id,
                        doctorName: slot.doctor_name,
                        slotId: slot.id,
                        time: `${slot.start_time} - ${slot.end_time}`,
                        date: slot.date,
                      })
                    }
                  />
                ))}
              </div>
            )}
          </div>

          {/* Evening Slots */}
          <div className="bg-surface border border-border rounded-xl p-5 shadow-sm">
            <h4 className="text-xs font-bold text-ink uppercase tracking-wider mb-3 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-indigo-500"></span> Evening Sessions (16:00 - 20:00)
            </h4>
            {eveningSlots.length === 0 ? (
              <p className="text-xs text-muted-text">No evening slots for this selection.</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {eveningSlots.map((slot) => (
                  <SlotCard
                    key={slot.id}
                    slot={slot}
                    onBook={() =>
                      setBookingModalSlot({
                        doctorId: slot.doctor_id,
                        doctorName: slot.doctor_name,
                        slotId: slot.id,
                        time: `${slot.start_time} - ${slot.end_time}`,
                        date: slot.date,
                      })
                    }
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Manual Booking Modal */}
      {bookingModalSlot && (
        <div className="fixed inset-0 bg-ink/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-surface border border-border rounded-xl max-w-sm w-full p-6 shadow-xl space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-base font-bold text-ink">Book Consultation Slot</h3>
                <p className="text-xs text-muted-text mt-0.5">
                  {bookingModalSlot.doctorName}
                </p>
              </div>
              <button
                onClick={() => setBookingModalSlot(null)}
                className="text-muted-text hover:text-ink text-sm font-bold p-1 rounded-md"
              >
                ✕
              </button>
            </div>

            <div className="bg-background border border-border rounded-lg p-3 text-xs space-y-1">
              <div className="flex justify-between">
                <span className="text-muted-text">Date:</span>
                <span className="font-semibold text-ink">{bookingModalSlot.date}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-text">Time:</span>
                <span className="font-semibold text-ink">{bookingModalSlot.time}</span>
              </div>
            </div>

            <form onSubmit={handleBookSlot} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-ink mb-1">
                  Patient 10-Digit Phone Number
                </label>
                <input
                  type="tel"
                  placeholder="e.g. 9876543210"
                  value={phoneNumberInput}
                  onChange={(e) => setPhoneNumberInput(e.target.value)}
                  required
                  className="w-full bg-background border border-border rounded-lg px-3 py-2 text-xs font-mono text-ink placeholder:text-muted-text focus:outline-none focus:border-primary"
                />
              </div>

              {bookingStatus && (
                <div className="p-2.5 rounded-lg bg-positive/10 text-positive text-xs flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>{bookingStatus}</span>
                </div>
              )}

              {bookingError && (
                <div className="p-2.5 rounded-lg bg-error/10 text-error text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{bookingError}</span>
                </div>
              )}

              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setBookingModalSlot(null)}
                  className="w-1/2 bg-background hover:bg-border/60 text-ink text-xs font-semibold py-2 rounded-lg border border-border"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!phoneNumberInput.trim() || !!bookingStatus}
                  className="w-1/2 bg-primary hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-semibold py-2 rounded-lg shadow-sm"
                >
                  Confirm Booking
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

function SlotCard({ slot, onBook }: { slot: any; onBook: () => void }) {
  return (
    <div
      className={`p-3 rounded-lg border flex flex-col justify-between transition-all ${
        slot.is_available
          ? 'bg-surface border-border hover:border-primary/50 shadow-xs'
          : 'bg-background/80 border-border/60 opacity-60'
      }`}
    >
      <div>
        <div className="flex items-center justify-between text-xs">
          <span className="font-bold text-ink flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-muted-text" />
            {slot.start_time} - {slot.end_time}
          </span>
          <span
            className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
              slot.is_available ? 'bg-positive/10 text-positive' : 'bg-border text-muted-text'
            }`}
          >
            {slot.is_available ? 'Open' : 'Booked'}
          </span>
        </div>
        <div className="mt-2 text-xs">
          <p className="font-medium text-ink truncate">{slot.doctor_name}</p>
          <p className="text-[11px] text-muted-text">{slot.speciality}</p>
        </div>
      </div>

      <div className="mt-3 pt-2 border-t border-border/50">
        {slot.is_available ? (
          <button
            onClick={onBook}
            className="w-full text-center text-xs font-semibold text-primary hover:text-blue-700 py-1 rounded hover:bg-primary/5 transition-colors"
          >
            Book Slot
          </button>
        ) : (
          <span className="block text-center text-[11px] text-muted-text py-1">Unavailable</span>
        )}
      </div>
    </div>
  )
}
