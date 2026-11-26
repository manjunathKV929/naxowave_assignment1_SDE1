import { useState } from 'react'
import { Calendar, Clock, DollarSign, Search, CheckCircle2, ChevronRight } from 'lucide-react'
import { Doctor } from '../types'
import { api } from '../services/api'

interface DoctorsViewProps {
  doctors: Doctor[]
  onSelectSlotBooking?: (doctorId: string, doctorName: string, slotId: string, time: string, date: string) => void
}

export const DoctorsView: React.FC<DoctorsViewProps> = ({ doctors }) => {
  const [selectedSpeciality, setSelectedSpeciality] = useState<string>('All')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [activeDoctorSlots, setActiveDoctorSlots] = useState<{
    doctorId: string
    doctorName: string
    date: string
    slots: Array<{ id: string; time: string; is_available: boolean }>
  } | null>(null)
  const [loadingSlots, setLoadingSlots] = useState<boolean>(false)

  const specialities = [
    'All',
    'Cardiology',
    'Dermatology',
    'Pediatrics',
    'General Medicine',
    'Orthopedics',
    'Neurology',
  ]

  const filteredDoctors = doctors.filter((doc) => {
    const matchesSpeciality =
      selectedSpeciality === 'All' || doc.speciality.toLowerCase() === selectedSpeciality.toLowerCase()
    const matchesSearch =
      doc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.speciality.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesSpeciality && matchesSearch
  })

  const handleCheckSchedule = async (doctor: Doctor) => {
    setLoadingSlots(true)
    try {
      const today = new Date().toISOString().split('T')[0]
      const res = await api.getDoctorAvailability(doctor.id, today)
      setActiveDoctorSlots({
        doctorId: doctor.id,
        doctorName: doctor.name,
        date: res.date || today,
        slots: res.slots.map((s) => ({
          id: s.id,
          time: `${s.start_time} - ${s.end_time}`,
          is_available: s.is_available,
        })),
      })
    } catch (err) {
      console.error('Failed to load slots:', err)
    } finally {
      setLoadingSlots(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Filters & Search Header */}
      <div className="bg-surface border border-border rounded-xl p-4 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Speciality Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full md:w-auto pb-2 md:pb-0">
          {specialities.map((spec) => (
            <button
              key={spec}
              onClick={() => setSelectedSpeciality(spec)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                selectedSpeciality === spec
                  ? 'bg-primary text-white shadow-sm'
                  : 'bg-background hover:bg-border/60 text-muted-text'
              }`}
            >
              {spec}
            </button>
          ))}
        </div>

        {/* Search input */}
        <div className="relative w-full md:w-64">
          <Search className="w-4 h-4 text-muted-text absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search doctors or clinics..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-background border border-border rounded-lg pl-9 pr-3 py-1.5 text-xs text-ink placeholder:text-muted-text focus:outline-none focus:border-primary"
          />
        </div>
      </div>

      {/* Doctors Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filteredDoctors.map((doc) => (
          <div
            key={doc.id}
            className="bg-surface border border-border rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between"
          >
            <div>
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-11 h-11 rounded-full bg-blue-50 border border-blue-100 flex items-center justify-center font-bold text-primary text-sm">
                    {doc.name.replace('Dr. ', '').split(' ').map((n) => n[0]).join('')}
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-ink leading-tight">{doc.name}</h4>
                    <span className="inline-block px-2 py-0.5 rounded text-[11px] font-semibold bg-primary/10 text-primary mt-1">
                      {doc.speciality}
                    </span>
                  </div>
                </div>

                <div className="flex items-center text-xs font-semibold text-ink bg-background px-2.5 py-1 rounded-md border border-border">
                  <DollarSign className="w-3.5 h-3.5 text-positive -mr-0.5" />
                  {doc.consultation_fee || 150}
                </div>
              </div>

              {doc.bio && (
                <p className="text-xs text-muted-text mt-3.5 line-clamp-2 leading-relaxed">
                  {doc.bio}
                </p>
              )}
            </div>

            <div className="mt-5 pt-4 border-t border-border flex items-center justify-between">
              <span className="text-[11px] text-muted-text flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-positive" /> Active Physician
              </span>

              <button
                onClick={() => handleCheckSchedule(doc)}
                className="text-xs font-semibold text-primary hover:text-blue-700 flex items-center gap-1 transition-colors"
              >
                <span>Check Schedule</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Modal / Sheet for Doctor Available Slots */}
      {activeDoctorSlots && (
        <div className="fixed inset-0 bg-ink/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-surface border border-border rounded-xl max-w-md w-full p-6 shadow-xl space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-base font-bold text-ink">{activeDoctorSlots.doctorName}</h3>
                <p className="text-xs text-muted-text flex items-center gap-1.5 mt-0.5">
                  <Calendar className="w-3.5 h-3.5" /> Schedule for {activeDoctorSlots.date}
                </p>
              </div>
              <button
                onClick={() => setActiveDoctorSlots(null)}
                className="text-muted-text hover:text-ink text-sm font-bold p-1 rounded-md"
              >
                ✕
              </button>
            </div>

            <div className="max-h-60 overflow-y-auto space-y-2 pr-1">
              {loadingSlots ? (
                <p className="text-xs text-center py-4 text-muted-text">Loading slots...</p>
              ) : activeDoctorSlots.slots.length === 0 ? (
                <p className="text-xs text-center py-4 text-muted-text">No slots found for this date.</p>
              ) : (
                activeDoctorSlots.slots.map((s) => (
                  <div
                    key={s.id}
                    className={`flex items-center justify-between p-2.5 rounded-lg border text-xs font-medium ${
                      s.is_available
                        ? 'bg-positive/5 border-positive/20 text-ink'
                        : 'bg-background border-border text-muted-text opacity-70'
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <Clock className="w-3.5 h-3.5 text-muted-text" /> {s.time}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                        s.is_available ? 'bg-positive/10 text-positive' : 'bg-border text-muted-text'
                      }`}
                    >
                      {s.is_available ? 'Available' : 'Booked'}
                    </span>
                  </div>
                ))
              )}
            </div>

            <div className="pt-2">
              <button
                onClick={() => setActiveDoctorSlots(null)}
                className="w-full bg-background hover:bg-border/60 text-ink text-xs font-semibold py-2 rounded-lg border border-border"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
