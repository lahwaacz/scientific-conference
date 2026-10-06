import { useConferenceInfo } from "./../hooks/useConferenceInfo";
import { conferenceTitle } from "../../utils/conferenceTitle";
import styles from "./Hero.module.css";

export default function Hero() {
  const info = useConferenceInfo();

  const dateStr =
    info?.date_start && info?.date_end
      ? `${formatDate(info.date_start)} - ${formatDate(info.date_end)}. ${info.location}.`
      : "";

  const title = conferenceTitle(info);

  return (
    <section className={styles.hero}>
      <div className={styles.container}>
        <div className={styles.leftSide}>
          <h1 className={styles.mainTitle}>{title}</h1>
          <h2 className={styles.date}>{dateStr}</h2>
        </div>
        <div className={styles.rightSide}>
          <p className={styles.text}>{info?.description}</p>
        </div>
      </div>
    </section>
  );
}

function formatDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-GB", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}
