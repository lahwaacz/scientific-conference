import { buildMediaUrl } from "../../utils/api";
import { conferenceUrl } from "../../utils/conferenceSlug";
import styles from "./Landing.module.css";

// The whole card is a plain anchor: full navigation to the conference site
// at `<base><slug>/`. Never a react-router Link (HashRouter would
// hash-prefix the href) and never window.location.
export default function ConferenceCard({ conference }) {
  const {
    slug,
    title,
    date_start,
    date_end,
    year,
    location,
    photo,
    short_description,
  } = conference;
  // Same title-year pairing as the conference page Hero.
  const fullTitle = [title, year].filter(Boolean).join(" ");

  return (
    <a href={conferenceUrl(slug)} className={styles.card}>
      {photo && (
        <img src={buildMediaUrl(photo)} alt={title} className={styles.photo} />
      )}
      <div className={styles.cardBody}>
        <h3 className={styles.cardTitle}>{fullTitle}</h3>
        <p className={styles.dates}>
          {dateRangeText(date_start, date_end, year)}
        </p>
        <p className={styles.location}>{location}</p>
        <p className={styles.description}>{short_description}</p>
      </div>
    </a>
  );
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

function dateRangeText(dateStart, dateEnd, year) {
  if (dateStart && dateEnd) {
    return `${formatDate(dateStart)} – ${formatDate(dateEnd)}`;
  }
  if (!dateStart && !dateEnd) {
    return "Dates TBA";
  }
  return year ? String(year) : "Dates TBA";
}
