import Talk from "./Talk";
import Session from "./Session";
import styles from "./Program.module.css";

export default function ProgramDay({ day }) {
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
          return <Session key={index} session={item.data} />;
        } else {
          return <Talk key={index} talk={item.data} />;
        }
      })}
    </div>
  );
}
