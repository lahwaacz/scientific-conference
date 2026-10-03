import { useConferenceInfo } from "./../hooks/useConferenceInfo";
import styles from "./Hero.module.css";

export default function Hero() {
  const info = useConferenceInfo();

  const dateStr =
    info?.date_start && info?.date_end
      ? `${formatDate(info.date_start)} - ${formatDate(info.date_end)}. ${info.location}.`
      : "";

  return (
    <section className={styles.hero}>
      <div className={styles.container}>
        <div className={styles.leftSide}>
          <h1 className={styles.mainTitle}>
            {info
              ? `${info.title} ${info.year}`
              : "Workshop on Scientific Computing 2025"}
          </h1>
          <h2 className={styles.date}>{dateStr}</h2>
        </div>
        <div className={styles.rightSide}>
          <p className={styles.text}>
            {info?.description ||
              "The international scientific colloquium is organized by the Faculty of Nuclear Sciences and Physical Engineering of the Czech Technical University in Prague on annual basis. It is devoted to the meeting of students and young applied mathematicians dealing with numerical solution of partial differential equations, mathematical modelling, numerical simulation of problems in technology, environment, biology and computer science."}
          </p>
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
