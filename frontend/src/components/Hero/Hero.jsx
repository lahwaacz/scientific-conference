import { buildMediaUrl } from "../../utils/api";
import { conferenceTitle } from "../../utils/conferenceTitle";
import { useConferenceInfo } from "./../hooks/useConferenceInfo";
import styles from "./Hero.module.css";

export default function Hero() {
  const info = useConferenceInfo();

  const dateStr =
    info?.date_start && info?.date_end
      ? `${formatDate(info.date_start)} - ${formatDate(info.date_end)}. ${info.location}.`
      : "";

  const title = conferenceTitle(info);
  const description = info?.description?.trim() ?? "";
  const heroPhoto = info?.hero_photo ?? null;
  const hasBand = Boolean(title) || Boolean(dateStr);

  return (
    <section className={styles.hero}>
      {hasBand && (
        <div className={styles.band}>
          {title && <h1 className={styles.mainTitle}>{title}</h1>}
          {dateStr && <h2 className={styles.date}>{dateStr}</h2>}
        </div>
      )}

      {heroPhoto && description ? (
        <div className={styles.media}>
          <img
            src={buildMediaUrl(heroPhoto)}
            alt=""
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
          alt=""
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

function formatDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-GB", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}
