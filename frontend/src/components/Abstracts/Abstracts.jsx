import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { buildApiUrl } from "../../utils/api";
import AbstractCard from "../ui/AbstractCard/AbstractCard";
import Loader from "../ui/Loader/Loader";
import Title from "../ui/Title/Title";
import styles from "./Abstracts.module.css";

export default function Abstracts() {
  const [abstracts, setAbstracts] = useState([]);
  const [loading, setLoading] = useState(true);
  // null = not yet known; false hides the card's program button. Fetch
  // failures and non-list payloads fail open so a backend hiccup never
  // hides the button.
  const [programReady, setProgramReady] = useState(null);
  const location = useLocation();

  useEffect(() => {
    fetch(buildApiUrl("/api/abstracts/"))
      .then((res) => res.json())
      .then((data) => {
        setAbstracts(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
    fetch(buildApiUrl("/api/program/"))
      .then((res) => (res.ok ? res.json() : null))
      .then((days) => setProgramReady(!Array.isArray(days) || days.length > 0))
      .catch(() => setProgramReady(true));
  }, []);

  useEffect(() => {
    // Also wait for programReady: the card shrinks when the program is
    // confirmed empty, so scrolling earlier would land off-target.
    if (loading || programReady === null) return;
    const params = new URLSearchParams(location.search);
    const abstractId = params.get("abstract");

    if (abstractId) {
      setTimeout(() => {
        const el = document.getElementById(`abstract-${abstractId}`);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 300);
    }
  }, [location, abstracts, loading, programReady]);

  return (
    <section className={styles.abstractsSection}>
      <Title text="Abstracts" />
      {loading ? (
        <Loader />
      ) : (
        <div className={`${styles.container} ${styles.fadeIn}`}>
          {abstracts.map((abstract) => (
            <AbstractCard
              key={abstract.id}
              id={abstract.id}
              title={abstract.title}
              authors={abstract.authors_string}
              department={abstract.department}
              abstractText={abstract.text}
              talkId={abstract.talk_id}
              programReady={programReady}
            />
          ))}
        </div>
      )}
    </section>
  );
}
