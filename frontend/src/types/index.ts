export interface Doctor {
  id: string
  name: string
  speciality: string
  email?: string
  phone?: string
  bio?: string
  consultation_fee?: number
  is_active: boolean
}

export interface Slot {
  id: string
  doctor_id: string
  date: string
  start_time: string
  end_time: string
  is_available: boolean
}

export interface DoctorAvailability {
  doctor_id: string
  doctor_name: string
  speciality: string
  date: string
  slots: Slot[]
}

export interface Appointment {
  id: string
  doctor_id: string
  doctor_name: string
  speciality: string
  slot_id: string
  date: string
  time: string
  patient_phone: string
  status: 'CONFIRMED' | 'CANCELLED'
  created_at: string
}

export interface ActivityItem {
  id: string
  event_type: string
  description: string
  appointment_id?: string
  phone_number?: string
  timestamp: string
}

export interface VoiceTranscriptItem {
  id: string
  role: 'user' | 'agent' | 'system'
  text: string
  timestamp: string
}

export interface VoiceToolEvent {
  tool: string
  status: 'started' | 'completed' | 'failed'
  params?: Record<string, any>
  result?: Record<string, any>
  timestamp: string
}
