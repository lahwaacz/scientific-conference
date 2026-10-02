import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './EditProgram.module.css';
import Title from '../ui/Title/Title';
import Loader from '../ui/Loader/Loader';
import { clearProgramDirty } from '../../utils/programRefresh';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPenToSquare } from '@fortawesome/free-solid-svg-icons';
import Modal from '../ui/Modal/Modal';
import { fetchWithAuth, buildApiUrl } from '../../utils/api';

function TimeSelect({ onChange }) {
  const [hours, setHours] = useState('');
  const [minutes, setMinutes] = useState('');

  function handleHours(h) {
    setHours(h);
    if (h && minutes) onChange(`${h}:${minutes}:00`);
    else onChange('');
  }

  function handleMinutes(m) {
    setMinutes(m);
    if (hours && m) onChange(`${hours}:${m}:00`);
    else onChange('');
  }

  return (
    <div className={styles.timeSelect}>
      <select value={hours} onChange={e => handleHours(e.target.value)}>
        <option value="">HH</option>
        {Array.from({ length: 24 }, (_, i) => (
          <option key={i} value={String(i).padStart(2, '0')}>
            {String(i).padStart(2, '0')}
          </option>
        ))}
      </select>
      <span style={{ color: 'var(--color-text-secondary)' }}>:</span>
      <select value={minutes} onChange={e => handleMinutes(e.target.value)}>
        <option value="">MM</option>
        {['00', '05', '10', '15', '20', '25', '30', '35', '40', '45', '50', '55'].map(m => (
          <option key={m} value={m}>{m}</option>
        ))}
      </select>
    </div>
  );
}

function useModal() {
  const [modal, setModal] = useState({ isOpen: false });

  const showAlert = useCallback((message, title = '') => {
    return new Promise(resolve => {
      setModal({
        isOpen: true,
        title,
        message,
        confirmText: 'OK',
        onConfirm: () => { setModal({ isOpen: false }); resolve(true); },
        onCancel: null,
        type: 'default',
      });
    });
  }, []);

  const showConfirm = useCallback((message, title = '') => {
    return new Promise(resolve => {
      setModal({
        isOpen: true,
        title,
        message,
        confirmText: 'Confirm',
        cancelText: 'Cancel',
        onConfirm: () => { setModal({ isOpen: false }); resolve(true); },
        onCancel: () => { setModal({ isOpen: false }); resolve(false); },
        type: 'default',
      });
    });
  }, []);

  return { modal, showAlert, showConfirm };
}

export default function EditProgram() {
  const [unscheduledTalks, setUnscheduledTalks] = useState([]);
  const [days, setDays] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDayForm, setShowDayForm] = useState(false);
  const [newDate, setNewDate] = useState('');
  const navigate = useNavigate();
  const { modal, showAlert, showConfirm } = useModal();

  useEffect(() => {
    fetchData();
    function handleFocus() {
      if (localStorage.getItem('program_needs_refresh')) fetchData();
    }
    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, []);

  async function fetchData() {


    try {
      const [talksRes, programRes, sessionsRes] = await Promise.all([
        fetchWithAuth('/api/admin/talks/unscheduled/'),
        fetch(buildApiUrl('/api/program/')),
        fetchWithAuth('/api/admin/sessions/'),
      ]);

      const talksData = await talksRes.json();
      const programData = await programRes.json();
      const sessionsData = await sessionsRes.json();

      const sortedDays = Array.isArray(programData)
        ? [...programData].sort((a, b) => new Date(a.date) - new Date(b.date))
        : [];

      setUnscheduledTalks(Array.isArray(talksData) ? talksData : []);
      setDays(sortedDays);
      setSessions(Array.isArray(sessionsData) ? sessionsData : []);

      if (!Array.isArray(talksData)) {
        console.error('Unscheduled talks is not an array:', talksData);
      }

      clearProgramDirty();
    } catch (error) {
      console.error("Error fetching data:", error);
      setUnscheduledTalks([]);
      setDays([]);
      setSessions([]);
    } finally {
      setLoading(false);
    }
  }

  async function updateChair(sessionId, newChairName)   {
    try {
      const res = await fetchWithAuth(`/api/admin/sessions/${sessionId}/`, {
        method: 'PATCH',
        body: JSON.stringify({ chair: newChairName })
      });
      if (res.ok) { await showAlert('Chair updated!', 'Success'); fetchData(); }
      else await showAlert('Failed to update chair', 'Error');
    } catch { await showAlert('Connection error', 'Error'); }
  }

  async function deleteSession(sessionId)   {
    try {
      const res = await fetchWithAuth(`/api/admin/sessions/${sessionId}/delete/`, {
        method: 'DELETE',
      });
      if (res.ok) { await showAlert('Chair deleted!', 'Success'); fetchData(); }
      else await showAlert('Failed to delete chair', 'Error');
    } catch { await showAlert('Connection error', 'Error'); }
  }




  async function updateTalk(talkId, payload)   {
    try {
      const res = await fetchWithAuth(`/api/admin/talks/${talkId}/schedule/`, {
        method: 'PATCH',
        body: JSON.stringify(payload)
      });
      return res;
    } catch {
      return null;
    }
  }

  async function moveTalkToUnscheduled(talkId)   {
    try {
      const res = await fetchWithAuth(`/api/admin/talks/${talkId}/schedule/`, {
        method: 'PATCH',
        body: JSON.stringify({
          day: null,
          session: null,
          start_time: null,
          end_time: null
        })
      });
      return res;
    } catch {
      return null;
    }
  }
  async function deleteDay(dayId) {
    const confirmed = await showConfirm(
      'Are you sure you want to delete this day and all its scheduled items?',
      'Delete Day'
    );
    if (!confirmed) return;



    try {
      const res = await fetchWithAuth(`/api/admin/days/${dayId}/delete/`, {
        method: 'DELETE',
      });

      if (!res.ok) {
        const data = await res.json();
        await showAlert(`Failed to delete day: ${data.error || 'Unknown error'}`, 'Error');
        return;
      }

      await showAlert('Day deleted successfully!', 'Success');
      fetchData();
    } catch {
      await showAlert('Connection error', 'Error');
    }
  }

  async function updateTimeOnly(type, id, startTime, endTime) {

    const url = type === 'session'
      ? `/api/admin/sessions/${id}/update-time/`
      : `/api/admin/talks/${id}/schedule/`;
    try {
      const res = await fetchWithAuth(url, {
        method: 'PATCH',
        body: JSON.stringify({ start_time: startTime, end_time: endTime })
      });
      return res.ok;
    } catch {
      return false;
    }
  }

  async function updateTime(type, id, startTime, endTime) {
    const ok = await updateTimeOnly(type, id, startTime, endTime);
    if (ok) { await showAlert('Time updated!', 'Success'); fetchData(); }
    else await showAlert('Failed to update time', 'Error');
  }

  async function scheduleTalk(talkId, dayId, startTime, endTime, sessionId = null)   {
    try {
      const res = await fetchWithAuth(`/api/admin/talks/${talkId}/schedule/`, {
        method: 'PATCH',
        body: JSON.stringify({ day: dayId, start_time: startTime, end_time: endTime, session: sessionId })
      });
      if (res.ok) { await showAlert('Talk scheduled successfully!', 'Success'); fetchData(); }
      else await showAlert('Failed to schedule talk', 'Error');
    } catch (error) {
      await showAlert('Connection error', 'Error');
    }
  }

  async function deleteTalk(talkId) {
    const confirmed = await showConfirm('Are you sure you want to delete this talk?', 'Delete Talk');
    if (!confirmed) return;

    try {
      const res = await fetchWithAuth(`/api/admin/talks/${talkId}/delete/`, {
        method: 'DELETE',
      });
      if (res.ok) { await showAlert('Talk deleted successfully!', 'Success'); fetchData(); }
      else {
        const data = await res.json();
        await showAlert(`Failed to delete talk: ${data.error || 'Unknown error'}`, 'Error');
      }
    } catch {
      await showAlert('Connection error', 'Error');
    }
  }

  async function createSession(dayId, chair)   {
    try {
      const res = await fetchWithAuth('/api/admin/sessions/create/', {
        method: 'POST',
        body: JSON.stringify({ day: dayId, chair })
      });
      if (res.ok) { await showAlert('Session created successfully!', 'Success'); fetchData(); }
      else await showAlert('Failed to create session', 'Error');
    } catch { await showAlert('Connection error', 'Error'); }
  }

  async function createBreak(dayId, title, startTime, endTime)   {
    try {
      const res = await fetchWithAuth('/api/admin/talks/create-break/', {
        method: 'POST',
        body: JSON.stringify({ day: dayId, title, talk_type: 'break', start_time: startTime, end_time: endTime })
      });
      if (res.ok) { await showAlert('Break added successfully!', 'Success'); fetchData(); }
      else await showAlert('Failed to add break', 'Error');
    } catch { await showAlert('Connection error', 'Error'); }
  }

  async function createDay(date)   {
    try {
      const res = await fetchWithAuth('/api/admin/days/create/', {
        method: 'POST',
        body: JSON.stringify({ date })
      });
      if (res.ok) { await showAlert('Day added successfully!', 'Success'); fetchData(); }
      else {
        const data = await res.json();
        await showAlert(`Failed to add day: ${JSON.stringify(data)}`, 'Error');
      }
    } catch (error) {
      await showAlert('Connection error', 'Error');
    }
  }

  async function handleCreateDay() {
    if (!newDate) { await showAlert('Please select a date', 'Error'); return; }
    createDay(newDate);
    setShowDayForm(false);
    setNewDate('');
  }

  const sortedDays = [...days].sort(
  (a, b) => new Date(`${a.date}T00:00:00`) - new Date(`${b.date}T00:00:00`)
);

  return (
    <div className={styles.container}>
      <Modal {...modal} />
      <button onClick={() => navigate("/admin-panel")} className={styles.backBtn}>← Back</button>

      <Title text="Unscheduled Talks" />

      {loading ? (
        <Loader />
      ) : (
        <div className={styles.fadeIn}>
          <section className={styles.section}>
            {unscheduledTalks.length === 0 ? (
              <p className={styles.noData}>No unscheduled talks</p>
            ) : (
              <div className={styles.talksGrid}>
                {unscheduledTalks.map(talk => (
                  <TalkCard
                    key={talk.id}
                    talk={talk}
                    days={sortedDays}
                    onSchedule={scheduleTalk}
                    onDelete={deleteTalk}
                    sessions={sessions}
                    showAlert={showAlert}
                  />
                ))}
              </div>
            )}
          </section>

          <section className={styles.section}>
            <Title text="Conference Schedule" />

            <div className={styles.addDayRow}>
              {!showDayForm ? (
                <button className={styles.addDayBtn} onClick={() => setShowDayForm(true)}>
                  + Add Day
                </button>
              ) : (
                <div className={styles.dayForm}>
                  <label>
                    Date:
                    <input type="date" value={newDate} onChange={e => setNewDate(e.target.value)} />
                  </label>
                  <div className={styles.schedulerActions}>
                    <button className={styles.saveBtn} onClick={handleCreateDay}>Save</button>
                    <button className={styles.cancelBtn} onClick={() => setShowDayForm(false)}>Cancel</button>
                  </div>
                </div>
              )}
            </div>

            <div className={styles.programPreview}>
              {sortedDays.map(day => (
                <DaySchedule
                  key={day.id}
                  day={day}
                  sessions={sessions}
                  onUpdateChair={updateChair}
                  onDeleteSession={deleteSession}
                  onCreateBreak={createBreak}
                  onCreateSession={createSession}
                  onUpdateTime={updateTime}
                  onUpdateTalk={updateTalk}
                  onMoveTalkToUnscheduled={moveTalkToUnscheduled}
                  onUpdateTimeOnly={updateTimeOnly}
                  onDeleteDay={deleteDay}
                  onRefresh={fetchData}
                  showAlert={showAlert}
                  showConfirm={showConfirm}
                />
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

function TalkCard({ talk, days, onSchedule, onDelete, sessions, showAlert }) {
  const [selectedDay, setSelectedDay] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [showScheduler, setShowScheduler] = useState(false);
  const [selectedSession, setSelectedSession] = useState('');

  const daySessions = sessions?.filter(s => String(s.day) === String(selectedDay)) || [];

  async function handleSchedule() {
    if (!selectedDay || !startTime || !endTime) { await showAlert('Please fill all fields', 'Error'); return; }
    onSchedule(talk.id, selectedDay, startTime, endTime, selectedSession || null);
  }

  return (
    <div className={styles.talkCard}>
      <div className={styles.talkHeader}>
        <h3>{talk.title}</h3>
        <span className={styles.badge}>Unscheduled</span>
      </div>
      <div className={styles.talkBody}>
        <p><strong>Speaker:</strong> {talk.participant?.name || 'N/A'}</p>
        <p><strong>Affiliation:</strong> {talk.participant?.affiliation || 'N/A'}</p>
        {talk.abstract && (
          <p className={styles.abstractPreview}>{talk.abstract.text?.substring(0, 150)}...</p>
        )}
      </div>
      {!showScheduler ? (
        <div className={styles.talkCardActions}>
          <button className={styles.scheduleBtn} onClick={() => setShowScheduler(true)}>Add to Schedule</button>

        </div>
      ) : (
        <div className={styles.scheduler}>
          <label>
            Day:
            <select value={selectedDay} onChange={e => { setSelectedDay(e.target.value); setSelectedSession(''); }}>
              <option value="">Select day</option>
              {days.map(day => (
                <option key={day.id} value={day.id}>
                  {new Date(day.date).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
                </option>
              ))}
            </select>
          </label>
          {daySessions.length > 0 && (
            <label>
              Chair (optional):
              <select value={selectedSession} onChange={e => setSelectedSession(e.target.value)}>
                <option value="">No chair</option>
                {daySessions.map(s => (
                  <option key={s.id} value={s.id}>{s.chair ? `Chair: ${s.chair}` : `Chair #${s.id}`}</option>
                ))}
              </select>
            </label>
          )}
          <label>Start Time: <TimeSelect onChange={setStartTime} /></label>
          <label>End Time: <TimeSelect onChange={setEndTime} /></label>
          <div className={styles.schedulerActions}>
            <button className={styles.saveBtn} onClick={handleSchedule}>Save</button>
            <button className={styles.cancelBtn} onClick={() => setShowScheduler(false)}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}

function DaySchedule({
  day, sessions,
  onCreateBreak, onCreateSession,
  onUpdateTime, onUpdateTimeOnly, onRefresh,
  onUpdateChair, onDeleteSession, onMoveTalk,
  showAlert, showConfirm, onUpdateTalk, onMoveTalkToUnscheduled, onDeleteDay
}) {
  const [showBreakForm, setShowBreakForm] = useState(false);
  const [breakTitle, setBreakTitle] = useState('Coffee Break');
  const [breakStart, setBreakStart] = useState('');
  const [breakEnd, setBreakEnd] = useState('');
  const [showSessionForm, setShowSessionForm] = useState(false);
  const [sessionChair, setSessionChair] = useState('');
  const [editingItem, setEditingItem] = useState(null);
  const [editStart, setEditStart] = useState('');
  const [editEnd, setEditEnd] = useState('');
  const [editingChair, setEditingChair] = useState(null);
  const [editChairName, setEditChairName] = useState('');
  const [editingTalk, setEditingTalk] = useState(null);
  const [editTalkStart, setEditTalkStart] = useState('');
  const [editTalkEnd, setEditTalkEnd] = useState('');
  const [editTalkSession, setEditTalkSession] = useState('');

  const daySessions = sessions?.filter(s => String(s.day) === String(day.id)) || [];

  function closeAllEdits() {
    setEditingItem(null);
    setEditingChair(null);
    setEditingTalk(null);
    setShowBreakForm(false);
    setShowSessionForm(false);
  }

  function formatTime(t) { return t ? t.substring(0, 5) : ''; }

  async function handleAddBreak() {
    if (!breakStart || !breakEnd) { await showAlert('Please set start and end time', 'Error'); return; }
    onCreateBreak(day.id, breakTitle, breakStart, breakEnd);
    setShowBreakForm(false); setBreakTitle('Coffee Break'); setBreakStart(''); setBreakEnd('');
  }

  async function handleAddSession() {
    if (!sessionChair.trim()) { await showAlert('Please enter chair name', 'Error'); return; }
    onCreateSession(day.id, sessionChair);
    setShowSessionForm(false); setSessionChair('');
  }

  function handleStartEdit(type, data) {
    closeAllEdits();
    setEditingItem({ type, data }); setEditStart(''); setEditEnd('');
  }

  async function handleSaveTime() {
    if (!editStart || !editEnd) { await showAlert('Please set both start and end time', 'Error'); return; }
    onUpdateTime(editingItem.type, editingItem.data.id, editStart, editEnd);
    setEditingItem(null);
  }

  function handleEditChair(session) {
    closeAllEdits();
    setEditingChair(session);
    setEditChairName(session.chair || '');
  }

  async function handleSaveChair() {
    if (!editChairName.trim()) { await showAlert('Chair name cannot be empty', 'Error'); return; }
    onUpdateChair(editingChair.id, editChairName);
    setEditingChair(null);
  }

  async function handleDeleteChair() {
    const confirmed = await showConfirm(`Delete chair "${editingChair.chair}" and unlink all its talks?`, 'Delete Chair');
    if (!confirmed) return;
    onDeleteSession(editingChair.id);
    setEditingChair(null);
  }

  function handleEditTalk(talk, currentSessionId) {
    closeAllEdits();
    setEditingTalk({ talk, currentSessionId });
    setEditTalkStart('');
    setEditTalkEnd('');
    setEditTalkSession(currentSessionId || '');
  }
  async function handleMoveTalkToUnscheduled() {
    const confirmed = await showConfirm(
      `Move "${editingTalk.talk.title}" back to unscheduled talks?`,
      'Move to Unscheduled'
    );
    if (!confirmed) return;

    const res = await onMoveTalkToUnscheduled(editingTalk.talk.id);

    if (!res) {
      await showAlert('Connection error', 'Error');
      return;
    }

    if (!res.ok) {
      const data = await res.json();
      await showAlert(`Failed to move talk: ${JSON.stringify(data)}`, 'Error');
      return;
    }

    await showAlert('Talk moved to unscheduled!', 'Success');
    setEditingTalk(null);
    onRefresh();
  }
  async function handleDeleteBreak() {
    const confirmed = await showConfirm(
      `Delete break "${editingItem.data.title}"?`,
      'Delete Break'
    );
    if (!confirmed) return;



    try {
      const res = await fetchWithAuth(`/api/admin/talks/${editingItem.data.id}/delete/`, {
        method: 'DELETE',
      });

      if (!res.ok) {
        const data = await res.json();
        await showAlert(`Failed to delete break: ${data.error || 'Unknown error'}`, 'Error');
        return;
      }

      await showAlert('Break deleted successfully!', 'Success');
      setEditingItem(null);
      onRefresh();
    } catch {
      await showAlert('Connection error', 'Error');
    }
  }

  async function handleSaveTalk() {
    if (!editTalkStart || !editTalkEnd) {
      await showAlert('Please set both times', 'Error');
      return;
    }

    const res = await onUpdateTalk(editingTalk.talk.id, {
      start_time: editTalkStart,
      end_time: editTalkEnd,
      session: editTalkSession || null
    });

    if (!res) {
      await showAlert('Connection error', 'Error');
      return;
    }

    if (!res.ok) {
      const data = await res.json();
      await showAlert(`Failed to update talk: ${JSON.stringify(data)}`, 'Error');
      return;
    }

    await showAlert('Talk updated!', 'Success');
    setEditingTalk(null);
    onRefresh();
  }

  return (
    <div className={styles.daySchedule}>
      <div className={styles.dayHeader}>
        <h3>
          {new Date(day.date).toLocaleDateString('en-US', {
            weekday: 'long',
            month: 'long',
            day: 'numeric'
          })}
        </h3>

        <button
          type="button"
          className={styles.dayDeleteBtn}
          onClick={() => onDeleteDay(day.id)}
          aria-label="Delete day"
          title="Delete day"
        >
          ×
        </button>
      </div>

      {day.timeline && day.timeline.length > 0 ? (
        <div className={styles.timeline}>
          {day.timeline.map((item, idx) => (
            <div key={idx}>
              {item.type === 'session' ? (
                <div className={styles.sessionBlock}>
                  <div className={styles.sessionHeader}>
                    <span className={styles.time}>{formatTime(item.start_time)} - {formatTime(item.end_time)}</span>
                    <span className={styles.sessionTitle}>Chair: {item.data.chair}</span>
                    <button className={styles.editTimeBtn} onClick={() => handleEditChair(item.data)}>
                      <FontAwesomeIcon icon={faPenToSquare} />
                    </button>
                  </div>
                  {item.data.talks?.length > 0 && (
                    <div className={styles.sessionTalks}>
                      {item.data.talks.map((talk, tIdx) => (
                        <div key={tIdx} className={styles.sessionTalkItem}>
                          <span className={styles.time}>{formatTime(talk.start_time)} - {formatTime(talk.end_time)}</span>
                          <span className={styles.itemTitle}>
                            <span className={styles.speakerName}>
                              {talk.participant?.name || ''}
                              {talk.participant?.name ? ' — ' : ''}
                            </span>
                            {talk.title}
                          </span>
                          <button className={styles.editTimeBtn} onClick={() => handleEditTalk(talk, item.data.id)}>
                            <FontAwesomeIcon icon={faPenToSquare} />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className={styles.timelineItem}>
                  <span className={styles.time}>{formatTime(item.start_time)} - {formatTime(item.end_time)}</span>
                  <span className={styles.itemTitle}>
                    {item.data.title}
                    {item.type === 'talk' && item.data.participant?.name && (
                      <span className={styles.speakerName}>{' — '}{item.data.participant.name}</span>
                    )}
                  </span>
                  <button
                    className={styles.editTimeBtn}
                    onClick={() => {
                      if (item.data?.talk_type === 'break') {
                        handleStartEdit(item.type, item.data);
                      } else {
                        handleEditTalk(item.data, item.data.session || null);
                      }
                    }}
                  >
                    <FontAwesomeIcon icon={faPenToSquare} />
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className={styles.noSchedule}>No talks scheduled yet</p>
      )}

      {!showBreakForm && !showSessionForm && !editingItem && (
        <div className={styles.dayActions}>
          <button className={styles.addBreakBtn} onClick={() => setShowBreakForm(true)}>+ Add Break</button>
          <button className={styles.addSessionBtn} onClick={() => setShowSessionForm(true)}>+ Add Chair</button>
        </div>
      )}

      {editingItem && (
        <div className={styles.breakForm}>
          <p className={styles.editLabel}>
            Edit time: <strong>{editingItem.data.title || editingItem.data.chair}</strong>
          </p>

          <label>Start Time: <TimeSelect onChange={setEditStart} /></label>
          <label>End Time: <TimeSelect onChange={setEditEnd} /></label>

          <div className={styles.schedulerActions}>
            <button className={styles.saveBtn} onClick={handleSaveTime}>Save</button>

            {editingItem.data?.talk_type === 'break' && (
              <button className={styles.deleteBtn} onClick={handleDeleteBreak}>
                Delete
              </button>
            )}

            <button className={styles.cancelBtn} onClick={() => setEditingItem(null)}>Cancel</button>
          </div>
        </div>
      )}

      {editingChair && (
        <div className={styles.breakForm}>
          <p className={styles.editLabel}>Edit Chair</p>
          <label>
            Name:
            <input
              type="text"
              value={editChairName}
              onChange={e => setEditChairName(e.target.value)}
              placeholder="Chair name"
            />
          </label>
          <div className={styles.schedulerActions}>
            <button className={styles.saveBtn} onClick={handleSaveChair}>Save</button>
            <button className={styles.deleteBtn} onClick={handleDeleteChair}>Delete Chair</button>
            <button className={styles.cancelBtn} onClick={() => setEditingChair(null)}>Cancel</button>
          </div>
        </div>
      )}

      {editingTalk && (
        <div className={styles.breakForm}>
          <p className={styles.editLabel}>
            Edit: <strong>{editingTalk.talk.title}</strong>
          </p>
          <label>Start Time: <TimeSelect onChange={setEditTalkStart} /></label>
          <label>End Time: <TimeSelect onChange={setEditTalkEnd} /></label>
          <label>
            Chair:
            <select value={editTalkSession} onChange={e => setEditTalkSession(e.target.value)}>
              <option value="">No chair</option>
              {daySessions.map(s => (
                <option key={s.id} value={s.id}>
                  {s.chair ? `Chair: ${s.chair}` : `Chair #${s.id}`}
                </option>
              ))}
            </select>
          </label>
          <div className={styles.schedulerActions}>
            <button className={styles.saveBtn} onClick={handleSaveTalk}>Save</button>
            <button className={styles.deleteBtn} onClick={handleMoveTalkToUnscheduled}>
              Move to Unscheduled
            </button>
            <button className={styles.cancelBtn} onClick={() => setEditingTalk(null)}>Cancel</button>
          </div>
        </div>
      )}

      {showBreakForm && (
        <div className={styles.breakForm}>
          <label>Title: <input type="text" value={breakTitle} onChange={e => setBreakTitle(e.target.value)} placeholder="Coffee Break" /></label>
          <label>Start Time: <TimeSelect onChange={setBreakStart} /></label>
          <label>End Time: <TimeSelect onChange={setBreakEnd} /></label>
          <div className={styles.schedulerActions}>
            <button className={styles.saveBtn} onClick={handleAddBreak}>Save</button>
            <button className={styles.cancelBtn} onClick={() => setShowBreakForm(false)}>Cancel</button>
          </div>
        </div>
      )}

      {showSessionForm && (
        <div className={styles.breakForm}>
          <label>Chair: <input type="text" value={sessionChair} onChange={e => setSessionChair(e.target.value)} placeholder="Prof. Smith" /></label>
          <div className={styles.schedulerActions}>
            <button className={styles.saveBtn} onClick={handleAddSession}>Save</button>
            <button className={styles.cancelBtn} onClick={() => setShowSessionForm(false)}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}
