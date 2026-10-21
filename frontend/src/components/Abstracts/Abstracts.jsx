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
  const [filter, setFilter] = useState("all");
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

  const filterTypes = [
    { value: "talk", label: "Talks" },
    { value: "poster", label: "Posters" },
  ].filter((type) =>
    abstracts.some((abstract) => abstract.contribution_type === type.value)
  );
  const showFilters = filterTypes.length > 1;
  const visibleAbstracts =
    filter === "all"
      ? abstracts
      : abstracts.filter((abstract) => abstract.contribution_type === filter);

  return (
    <section className={styles.abstractsSection}>
      <Title text="Abstracts" />
      {loading ? (
        <Loader />
      ) : (
        <>
          {showFilters && (
            <fieldset
              className={styles.filterGroup}
              aria-label="Filter abstracts"
            >
              <div className={styles.filters}>
                <button
                  type="button"
                  className={`${styles.filterButton} ${
                    filter === "all" ? styles.filterButtonActive : ""
                  }`}
                  aria-pressed={filter === "all"}
                  onClick={() => setFilter("all")}
                >
                  All ({abstracts.length})
                </button>
                {filterTypes.map((type) => {
                  const count = abstracts.filter(
                    (abstract) => abstract.contribution_type === type.value
                  ).length;
                  return (
                    <button
                      key={type.value}
                      type="button"
                      className={`${styles.filterButton} ${
                        filter === type.value ? styles.filterButtonActive : ""
                      }`}
                      aria-pressed={filter === type.value}
                      onClick={() => setFilter(type.value)}
                    >
                      {type.label} ({count})
                    </button>
                  );
                })}
              </div>
            </fieldset>
          )}
          <div className={`${styles.container} ${styles.fadeIn}`}>
            {visibleAbstracts.map((abstract) => (
              <AbstractCard
                key={abstract.id}
                id={abstract.id}
                title={abstract.title}
                authors={abstract.authors_string}
                department={abstract.department}
                abstractText={abstract.text}
                contributionType={abstract.contribution_type}
                talkId={abstract.talk_id}
                sessionId={abstract.session_id}
                programReady={programReady}
              />
            ))}
          </div>
        </>
      )}
    </section>
  );
}
