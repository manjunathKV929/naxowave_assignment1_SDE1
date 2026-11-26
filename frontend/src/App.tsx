import { useState, useEffect } from 'react'
import { Sidebar } from './components/Sidebar'
import { Header } from './components/Header'
import { OverviewView } from './components/OverviewView'
import { DoctorsView } from './components/DoctorsView'
import { AvailabilityView } from './components/AvailabilityView'
import { AppointmentsView } from './components/AppointmentsView'
import { ActivityView } from './components/ActivityView'
import { CallModal } from './components/CallModal'
import { api } from './services/api'
import { Doctor, Appointment, ActivityItem } from './types'

export default function App() {
  const [activeTab, setActiveTab] = useState<string>('overview')
  const [backendStatus, setBackendStatus] = useState<string>('checking...')
  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [activities, setActivities] = useState<ActivityItem[]>([])
  const [isCallModalOpen, setIsCallModalOpen] = useState<boolean>(false)

  // Initial load
  useEffect(() => {
    checkHealth()
    loadInitialData()

    // Periodically refresh activity and appointments every 10s
    const interval = setInterval(() => {
      refreshDataSilently()
    }, 10000)

    return () => clearInterval(interval)
  }, [])

  const checkHealth = async () => {
    try {
      const res = await api.getHealth()
      setBackendStatus(res.status || 'ok')
    } catch {
      setBackendStatus('offline')
    }
  }

  const loadInitialData = async () => {
    try {
      const [docRes, aptRes, actRes] = await Promise.all([
        api.getDoctors(),
        api.getAppointments(),
        api.getActivity(30),
      ])
      setDoctors(docRes.doctors || [])
      setAppointments(aptRes.appointments || [])
      setActivities(actRes.activities || [])
    } catch (err) {
      console.error('Failed to load initial data:', err)
    }
  }

  const refreshDataSilently = async () => {
    try {
      const [aptRes, actRes] = await Promise.all([
        api.getAppointments(),
        api.getActivity(30),
      ])
      setAppointments(aptRes.appointments || [])
      setActivities(actRes.activities || [])
    } catch {
      // Background refresh error suppressed
    }
  }

  const getPageTitle = () => {
    switch (activeTab) {
      case 'overview':
        return 'Overview Dashboard'
      case 'doctors':
        return 'Doctors & Medical Staff'
      case 'availability':
        return 'Consultation Schedules'
      case 'appointments':
        return 'Appointments Ledger'
      case 'activity':
        return 'System Audit Log'
      default:
        return 'CareFlow AI'
    }
  }

  const getPageSubtitle = () => {
    switch (activeTab) {
      case 'overview':
        return 'Real-time clinic metrics and voice-assistant operational status'
      case 'doctors':
        return 'Explore credentialed physicians and consultation fees'
      case 'availability':
        return 'Browse real-time open slots across clinical specialities'
      case 'appointments':
        return 'Manage upcoming and past patient appointments with masked phone records'
      case 'activity':
        return 'Real-time chronicle of events, bookings, and voice sessions'
      default:
        return undefined
    }
  }

  return (
    <div className="min-h-screen bg-background text-ink flex">
      {/* 240px Fixed Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onStartCall={() => setIsCallModalOpen(true)}
        backendStatus={backendStatus}
        appointmentCount={appointments.filter((a) => a.status === 'CONFIRMED').length}
      />

      {/* Main Content Area */}
      <div className="flex-1 ml-64 flex flex-col min-h-screen">
        <Header
          title={getPageTitle()}
          subtitle={getPageSubtitle()}
          onStartCall={() => setIsCallModalOpen(true)}
        />

        <main className="flex-1 p-8 max-w-7xl w-full mx-auto">
          {activeTab === 'overview' && (
            <OverviewView
              doctors={doctors}
              appointments={appointments}
              activities={activities}
              onNavigate={(tab) => setActiveTab(tab)}
              onStartCall={() => setIsCallModalOpen(true)}
            />
          )}

          {activeTab === 'doctors' && <DoctorsView doctors={doctors} />}

          {activeTab === 'availability' && (
            <AvailabilityView
              doctors={doctors}
              onAppointmentBooked={refreshDataSilently}
            />
          )}

          {activeTab === 'appointments' && (
            <AppointmentsView
              appointments={appointments}
              onRefresh={refreshDataSilently}
            />
          )}

          {activeTab === 'activity' && <ActivityView activities={activities} />}
        </main>
      </div>

      {/* Real-time Voice Call Modal */}
      <CallModal
        isOpen={isCallModalOpen}
        onClose={() => setIsCallModalOpen(false)}
        onAppointmentUpdated={refreshDataSilently}
      />
    </div>
  )
}
