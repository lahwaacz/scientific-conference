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
  const location = useLocation();

  useEffect(() => {
    fetch(buildApiUrl("/api/abstracts/"))
      .then((res) => res.json())
      .then((data) => {
        setAbstracts(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (loading) return;
    const params = new URLSearchParams(location.search);
    const abstractId = params.get("abstract");

    if (abstractId) {
      setTimeout(() => {
        const el = document.getElementById(`abstract-${abstractId}`);
        if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 300);
    }
  }, [location, abstracts]);

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
            />
          ))}
        </div>
      )}
    </section>
  );
}
