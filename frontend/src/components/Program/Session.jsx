import styles from "./Program.module.css";
import Talk from "./Talk";

export default function Session({
  session,
  highlighted = false,
  highlightTalkId = null,
}) {
  const isPosterSession = session.kind === "poster";
  const formatTime = (time) => (time ? time.substring(0, 5) : "");
  const hasHeader = isPosterSession || Boolean(session.chair);

  return (
    <div
      id={`session-${session.id}`}
      className={`${styles.session} ${highlighted ? styles.highlighted : ""}`}
    >
      {hasHeader && (
        <div className={styles.sessionHeader}>
          {isPosterSession && (
            <span className={styles.sessionTime}>
              {formatTime(session.start_time)} – {formatTime(session.end_time)}
            </span>
          )}
          {isPosterSession && (
            <span className={styles.sessionBadge}>Poster session</span>
          )}
          {session.chair && (
            <span className={styles.chair}>Chair: {session.chair}</span>
          )}
        </div>
      )}

      {session.talks.map((talk) => (
        <Talk
          key={talk.id}
          talk={talk}
          highlighted={String(talk.id) === String(highlightTalkId)}
          showTime={!isPosterSession}
        />
      ))}
    </div>
  );
}
