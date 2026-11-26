import { Doctor, DoctorAvailability, Appointment, ActivityItem } from '../types'

const API_BASE = '/api'

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  const data = await res.json()
  if (!res.ok || (data.success === false && data.error)) {
    const errorMsg = data.error?.message || `Request failed with status ${res.status}`
    throw new Error(errorMsg)
  }
  return data
}

export const api = {
  // Health
  async getHealth(): Promise<{ status: string }> {
    return request<{ status: string }>(`${API_BASE}/health`)
  },

  // Doctors
  async getDoctors(speciality?: string): Promise<{ doctors: Doctor[] }> {
    const query = speciality ? `?speciality=${encodeURIComponent(speciality)}` : ''
    return request<{ doctors: Doctor[] }>(`${API_BASE}/doctors${query}`)
  },

  async getDoctorById(id: string): Promise<{ doctor: Doctor }> {
    return request<{ doctor: Doctor }>(`${API_BASE}/doctors/${id}`)
  },

  async getDoctorAvailability(doctorId: string, date?: string): Promise<DoctorAvailability> {
    const query = date ? `?date=${encodeURIComponent(date)}` : ''
    return request<DoctorAvailability>(`${API_BASE}/doctors/${doctorId}/availability${query}`)
  },

  async searchAvailability(speciality?: string, date?: string): Promise<{ availability: DoctorAvailability[] }> {
    const params = new URLSearchParams()
    if (speciality) params.set('speciality', speciality)
    if (date) params.set('date', date)
    const query = params.toString() ? `?${params.toString()}` : ''
    return request<{ availability: DoctorAvailability[] }>(`${API_BASE}/availability${query}`)
  },

  // Appointments
  async getAppointments(status?: string, date?: string, phone?: string): Promise<{ appointments: Appointment[] }> {
    const params = new URLSearchParams()
    if (status) params.set('status', status)
    if (date) params.set('date', date)
    if (phone) params.set('phone', phone)
    const query = params.toString() ? `?${params.toString()}` : ''
    return request<{ appointments: Appointment[] }>(`${API_BASE}/appointments${query}`)
  },

  async bookAppointment(payload: { phone_number: string; doctor_id: string; slot_id: string }): Promise<{
    success: boolean
    appointment: { id: string; status: string }
  }> {
    return request<{
      success: boolean
      appointment: { id: string; status: string }
    }>(`${API_BASE}/appointments`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async cancelAppointment(appointmentId: string): Promise<{
    success: boolean
    appointment_id: string
    status: string
  }> {
    return request<{
      success: boolean
      appointment_id: string
      status: string
    }>(`${API_BASE}/appointments/${appointmentId}/cancel`, {
      method: 'POST',
    })
  },

  async cancelAppointmentByPhone(phoneNumber: string): Promise<{
    success: boolean
    appointment_id: string
    status: string
  }> {
    return request<{
      success: boolean
      appointment_id: string
      status: string
    }>(`${API_BASE}/appointments/cancel`, {
      method: 'POST',
      body: JSON.stringify({ phone_number: phoneNumber }),
    })
  },

  // Activity Feed
  async getActivity(limit: number = 30): Promise<{ activities: ActivityItem[] }> {
    return request<{ activities: ActivityItem[] }>(`${API_BASE}/activity?limit=${limit}`)
  },
}
