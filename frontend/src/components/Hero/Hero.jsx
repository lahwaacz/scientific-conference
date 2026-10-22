import { buildMediaUrl } from "../../utils/api";
import { conferenceTitle } from "../../utils/conferenceTitle";
import { formatDateRange } from "../../utils/dateRange";
import { useConferenceInfo } from "./../hooks/useConferenceInfo";
import styles from "./Hero.module.css";

export default function Hero() {
  const info = useConferenceInfo();

  const dateStr =
    info?.date_start && info?.date_end
      ? [formatDateRange(info.date_start, info.date_end), info.location]
          .filter(Boolean)
          .join(", ")
      : "";

  const title = conferenceTitle(info);
  const description = info?.description?.trim() ?? "";
  const heroPhoto = info?.hero_photo ?? null;

  return (
    <section className={styles.hero}>
      <div className={styles.band}>
        <h1 className={styles.mainTitle}>{title}</h1>
        <h2 className={styles.date}>{dateStr}</h2>
      </div>

      {heroPhoto && description ? (
        <div className={styles.media}>
          <img
            src={buildMediaUrl(heroPhoto)}
            alt={title}
            className={styles.heroPhoto}
          />
          <div className={styles.scrim} aria-hidden="true" />
          <div className={styles.descCol}>
            <p className={styles.text}>{description}</p>
          </div>
        </div>
      ) : heroPhoto ? (
        <img
          src={buildMediaUrl(heroPhoto)}
          alt={title}
          className={styles.photoOnly}
        />
      ) : description ? (
        <div className={styles.descPlain}>
          <p className={styles.text}>{description}</p>
        </div>
      ) : null}
    </section>
  );
}
