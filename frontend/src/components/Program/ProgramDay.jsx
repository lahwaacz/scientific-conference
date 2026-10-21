import styles from "./Program.module.css";
import Session from "./Session";
import Talk from "./Talk";

export default function ProgramDay({
  day,
  highlightTalkId,
  highlightSessionId,
}) {
  return (
    <div className={styles.day}>
      <h2 className={styles.date}>
        {new Date(day.date).toLocaleDateString("en-US", {
          weekday: "long",
          month: "long",
          day: "numeric",
        })}
      </h2>

      {day.timeline.map((item, index) => {
        if (item.type === "session") {
          return (
            <Session
              key={index}
              session={item.data}
              highlightTalkId={highlightTalkId}
              highlighted={String(item.data.id) === String(highlightSessionId)}
            />
          );
        } else {
          return (
            <Talk
              key={index}
              talk={item.data}
              highlighted={String(item.data.id) === String(highlightTalkId)}
            />
          );
        }
      })}
    </div>
  );
}
