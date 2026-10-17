import { useNavigate } from "react-router-dom";
import styles from "./AbstractCard.module.css";

export default function AbstractCard({
  id,
  title,
  authors,
  department,
  abstractText,
  talkId,
  programReady,
}) {
  const navigate = useNavigate();

  function goToProgram() {
    navigate(`/program?talk=${talkId}`);
  }

  return (
    <div id={`abstract-${id}`} className={styles.card}>
      <h3 className={styles.title}>{title}</h3>
      <p className={styles.authors}>{authors}</p>
      <p className={styles.department}>{department}</p>
      <hr className={styles.separator} />
      <p className={styles.abstractText}>{abstractText}</p>
      {/* Hidden only once the program is known to be not ready; unknown
          (null) and fetch-failure (true, fail open) keep the button. */}
      {programReady !== false && (
        <button className={styles.button} onClick={goToProgram}>
          TO THE PROGRAM
        </button>
      )}
    </div>
  );
}
