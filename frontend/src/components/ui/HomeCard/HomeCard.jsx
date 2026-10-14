import avatar from "../../../assets/avatar.png";
import { buildMediaUrl } from "../../../utils/api";
import styles from "./HomeCard.module.css";

export default function HomeCard({ name, affiliation, email, photo }) {
  const imgSrc = photo ? buildMediaUrl(photo) : avatar;
  return (
    <div className={styles.card}>
      <img src={imgSrc} alt={name} className={styles.image} />
      <div className={styles.info}>
        <h3 className={styles.name}>{name}</h3>
        <p className={styles.affiliation}>{affiliation}</p>
        {email && (
          <a href={`mailto:${email}`} className={styles.email}>
            {email}
          </a>
        )}
      </div>
    </div>
  );
}
