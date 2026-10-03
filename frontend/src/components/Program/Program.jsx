import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { buildApiUrl } from "../../utils/api";
import { useConferenceInfo } from "./../hooks/useConferenceInfo";
import Loader from "../ui/Loader/Loader";
import Title from "../ui/Title/Title";
import styles from "./Program.module.css";
import ProgramDay from "./ProgramDay";

export default function Program() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const location = useLocation();
  const info = useConferenceInfo();

  useEffect(() => {
    fetch(buildApiUrl("/api/program/"))
      .then((res) => res.json())
      .then((data) => {
        setData(data);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (loading) return;
    const params = new URLSearchParams(location.search);
    const talkId = params.get("talk");

    if (talkId) {
      setTimeout(() => {
        const el = document.getElementById(`talk-${talkId}`);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 300);
    }
  }, [location, data]);

  return (
    <section className={styles.programSection}>
      <Title text="Program" />
      {loading ? (
        <Loader />
      ) : (
        <div className={styles.fadeIn}>
          <h2 className={styles.subheading}>
            Registration for local participants
          </h2>
          <p className={styles.description}>
            {info?.program_local_registration_text || ""}
          </p>

          <h2 className={styles.subheading}>Regular talks</h2>
          <p className={styles.description}>
            {info?.program_regular_talks_text || ""}
          </p>

          <h2 className={styles.subheading}>Poster pitch talks</h2>
          <p className={styles.description}>
            {info?.program_poster_talks_text || ""}
          </p>

          <div className={styles.scheduleContainer}>
            <div className={styles.program}>
              {data.map((day) => (
                <ProgramDay key={day.id} day={day} />
              ))}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
