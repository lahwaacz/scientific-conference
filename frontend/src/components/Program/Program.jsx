import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { buildApiUrl } from "../../utils/api";
import { useConferenceInfo } from "./../hooks/useConferenceInfo";
import Loader from "../ui/Loader/Loader";
import Markdown from "../ui/Markdown/Markdown";
import Title from "../ui/Title/Title";
import styles from "./Program.module.css";
import ProgramDay from "./ProgramDay";

export default function Program() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const location = useLocation();
  const info = useConferenceInfo();
  const params = new URLSearchParams(location.search);
  const highlightTalkId = params.get("talk");
  const highlightSessionId = params.get("session");

  useEffect(() => {
    fetch(buildApiUrl("/api/program/"))
      .then((res) => res.json())
      .then((data) => {
        setData(Array.isArray(data) ? data : []);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (loading) return;
    const targetId = highlightSessionId
      ? `session-${highlightSessionId}`
      : highlightTalkId
        ? `talk-${highlightTalkId}`
        : null;

    if (targetId) {
      setTimeout(() => {
        const el = document.getElementById(targetId);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 300);
    }
  }, [loading, highlightSessionId, highlightTalkId]);

  return (
    <section className={styles.programSection}>
      <Title text="Program" />
      {loading ? (
        <Loader />
      ) : (
        <div className={styles.fadeIn}>
          <Markdown text={info?.program_text} className={styles.description} />
          {data.length === 0 && (
            <p className={styles.description}>The program is not ready yet.</p>
          )}

          <div className={styles.scheduleContainer}>
            <div className={styles.program}>
              {data.map((day) => (
                <ProgramDay
                  key={day.id}
                  day={day}
                  highlightTalkId={highlightTalkId}
                  highlightSessionId={highlightSessionId}
                />
              ))}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
