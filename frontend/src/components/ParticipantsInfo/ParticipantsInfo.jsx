import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styles from './ParticipantsInfo.module.css';
import Title from '../ui/Title/Title';
import Loader from '../ui/Loader/Loader';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faCircleCheck } from '@fortawesome/free-solid-svg-icons';
import {fetchWithAuth} from '../../utils/api.js';

export default function ParticipantsInfo() {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchSubmissions();
  }, []);

  async function fetchSubmissions() {

    try {
       const res = await fetchWithAuth('/api/admin/submissions/?status=');
      const data = await res.json();
      setSubmissions(data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  const total = submissions.length;
  const withAbstract = submissions.filter(s => s.abstract_title).length;

  return (
    <div className={styles.container}>
      <button onClick={() => navigate("/admin-panel")} className={styles.backBtn}>
        ← Back
      </button>

      <Title text="Participants Info" />

      {loading ? (
        <Loader />
      ) : (
        <div className={styles.fadeIn}>
          <p className={styles.summary}>
            Participants: <strong>{total}</strong>, with abstract: <strong>{withAbstract}</strong>
          </p>

          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>No.</th>
                  <th>Name</th>
                  <th>Student</th>
                  <th>Abstract</th>
                  <th>Period of stay</th>
                  <th>Info</th>
                </tr>
              </thead>
              <tbody>
                {submissions.map((sub, idx) => (
                  <tr key={sub.id}>
                    <td>{idx + 1}</td>
                    <td className={styles.nameCell}>{sub.name}</td>
                    <td style={{ textAlign: 'center', padding: '10px 0' }}>
                      {sub.is_student
                        ? <FontAwesomeIcon icon={faCircleCheck} className={styles.checkIcon} />
                        : ''}
                    </td>
                    <td style={{ textAlign: 'center', padding: '10px 0' }}>
                      {sub.abstract_title
                        ? <FontAwesomeIcon icon={faCircleCheck} className={styles.checkIcon} />
                        : ''}
                    </td>
                    <td>
                      {sub.arrival_date && sub.departure_date
                        ? `${formatDate(sub.arrival_date)} – ${formatDate(sub.departure_date)}`
                        : '—'}
                    </td>
                    <td className={styles.infoCell}>{sub.info || ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function formatDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}