import { useEffect, useState } from "react";
import { buildApiUrl } from "../../utils/api";
import Loader from "../ui/Loader/Loader";
import ConferenceCard from "./ConferenceCard";
import styles from "./Landing.module.css";

// Fixed group order; the server delivers the flat list already ordered
// running → future → past, and grouping preserves that order per group.
const GROUPS = [
  { status: "running", heading: "Running" },
  { status: "future", heading: "Upcoming" },
  { status: "past", heading: "Past" },
];

export default function Landing({ unknownSlug = null }) {
  const [conferences, setConferences] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch(buildApiUrl("/api/conferences/"))
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setConferences(data);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, []);

  return (
    <main className={styles.landing}>
      <h1 className={styles.pageTitle}>Conferences</h1>
      {unknownSlug && (
        <p className={styles.notFound}>
          Conference &quot;{unknownSlug}&quot; was not found.
        </p>
      )}
      {loading ? (
        <Loader />
      ) : error ? (
        <p className={styles.error}>Failed to load conferences.</p>
      ) : conferences.length === 0 ? (
        <p className={styles.empty}>No conferences yet.</p>
      ) : (
        GROUPS.map(({ status, heading }) => {
          const group = conferences.filter((c) => c.status === status);
          if (group.length === 0) return null;
          return (
            <section key={status} className={styles.group}>
              <h2 className={styles.groupHeading}>{heading}</h2>
              <div className={styles.cards}>
                {group.map((conference) => (
                  <ConferenceCard
                    key={conference.slug}
                    conference={conference}
                  />
                ))}
              </div>
            </section>
          );
        })
      )}
    </main>
  );
}
