import React, { useState, useEffect } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import { eventsAPI } from '../services/api';
import EventModal from './EventModal';
import './CalendarView.css';

const CalendarView = () => {
  const [events, setEvents] = useState([]);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchEvents();
  }, []);

  const fetchEvents = async () => {
    try {
      const response = await eventsAPI.getAll();
      const formattedEvents = response.data.map(event => ({
        id: event.id,
        title: event.title,
        start: event.start_time,
        end: event.end_time,
        backgroundColor: getEventColor(event.event_type),
        extendedProps: event
      }));
      setEvents(formattedEvents);
    } catch (error) {
      console.error('Error fetching events:', error);
    } finally {
      setLoading(false);
    }
  };

  const getEventColor = (eventType) => {
    const colors = {
      meeting: '#3788d8',
      interview: '#f59e0b',
      exam: '#ef4444',
      deadline: '#ec4899',
      prep_session: '#8b5cf6',
      default: '#667eea'
    };
    return colors[eventType] || colors.default;
  };

  const handleEventClick = (info) => {
    setSelectedEvent(info.event.extendedProps);
    setShowModal(true);
  };

  const handleDateSelect = (selectInfo) => {
    setSelectedEvent({
      start_time: selectInfo.startStr,
      end_time: selectInfo.endStr,
      isNew: true
    });
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setSelectedEvent(null);
  };

  const handleSaveEvent = async () => {
    await fetchEvents();
    handleCloseModal();
  };

  if (loading) {
    return <div className="loading">Loading calendar...</div>;
  }

  return (
    <div className="calendar-view">
      <div className="calendar-header">
        <h2>📅 Your Calendar</h2>
        <div className="legend">
          <span className="legend-item"><span className="dot" style={{background: '#3788d8'}}></span> Meeting</span>
          <span className="legend-item"><span className="dot" style={{background: '#f59e0b'}}></span> Interview</span>
          <span className="legend-item"><span className="dot" style={{background: '#ef4444'}}></span> Exam</span>
          <span className="legend-item"><span className="dot" style={{background: '#8b5cf6'}}></span> Prep Session</span>
        </div>
      </div>

      <div className="calendar-container">
        <FullCalendar
          plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
          initialView="timeGridWeek"
          headerToolbar={{
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
          }}
          events={events}
          editable={true}
          selectable={true}
          selectMirror={true}
          dayMaxEvents={true}
          weekends={true}
          eventClick={handleEventClick}
          select={handleDateSelect}
          height="auto"
        />
      </div>

      {showModal && (
        <EventModal
          event={selectedEvent}
          onClose={handleCloseModal}
          onSave={handleSaveEvent}
        />
      )}
    </div>
  );
};

export default CalendarView;
