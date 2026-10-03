import { Link } from "react-router-dom";
import styles from "./Program.module.css";

export default function Talk({ talk }) {
  const isBreak = talk.talk_type === "break" || talk.talk_type === "event";

  function formatTime(t) {
    const [h, m] = t.split(":");
    return `${h}:${m}`;
  }

  return (
    <div
      id={`talk-${talk.id}`}
      className={isBreak ? styles.break : styles.talk}
    >
      <div className={styles.time}>
        {formatTime(talk.start_time)} – {formatTime(talk.end_time)}
      </div>

      <div className={styles.abstractInfo}>
        <div className={styles.speaker}>{talk.participant?.name}</div>
        {isBreak ? (
          <div className={styles.title}>{talk.title}</div>
        ) : (
          <Link
            to={`/abstracts?abstract=${talk.abstract_id}`}
            className={styles.linkTitle}
          >
            {talk.title}
          </Link>
        )}
      </div>
    </div>
  );
}
