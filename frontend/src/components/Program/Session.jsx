import styles from "./Program.module.css";
import Talk from "./Talk";

export default function Session({ session }) {
  return (
    <div className={styles.session}>
      {session.chair && (
        <div className={styles.chair}>Chair: {session.chair}</div>
      )}

      {session.talks.map((talk) => (
        <Talk key={talk.id} talk={talk} />
      ))}
    </div>
  );
}
