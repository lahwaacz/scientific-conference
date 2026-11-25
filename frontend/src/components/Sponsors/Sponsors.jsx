import { useEffect, useState } from "react";
import { buildApiUrl, buildMediaUrl } from "../../utils/api";
import Separator from "../ui/Separator/Separator";
import Title from "../ui/Title/Title";
import styles from "./Sponsors.module.css";

export default function Sponsors() {
  const [sponsors, setSponsors] = useState([]);

  useEffect(() => {
    let cancelled = false;

    fetch(buildApiUrl("/api/sponsors/"))
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load sponsors");
        return res.json();
      })
      .then((data) => {
        if (!cancelled) {
          setSponsors(Array.isArray(data) ? data : []);
        }
      })
      .catch(() => {
        if (!cancelled) setSponsors([]);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (!sponsors || sponsors.length === 0) return null;

  return (
    <section className={styles.sponsorsSection}>
      <div className={styles.wrapper}>
        <Title text="Sponsors" />
        <div className={`${styles.grid} ${styles.fadeIn}`}>
          {sponsors.map((sponsor) => {
            const hasSafeUrl =
              typeof sponsor.url === "string" &&
              /^https?:\/\//i.test(sponsor.url);
            const content = sponsor.logo ? (
              <img
                src={buildMediaUrl(sponsor.logo)}
                alt={sponsor.name}
                className={styles.logo}
                loading="lazy"
                decoding="async"
              />
            ) : (
              <span className={styles.name}>{sponsor.name}</span>
            );

            if (hasSafeUrl) {
              return (
                <a
                  key={sponsor.id}
                  href={sponsor.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`${styles.tile} ${styles.tileLink}`}
                >
                  {content}
                </a>
              );
            }

            return (
              <div key={sponsor.id} className={styles.tile}>
                {content}
              </div>
            );
          })}
        </div>
      </div>
      <Separator />
    </section>
  );
}
