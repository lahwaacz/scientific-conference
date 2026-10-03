import avatar from "../../../assets/avatar.png";
import { buildMediaUrl } from "../../../utils/api";
import styles from "./HomeCard.module.css";

export default function HomeCard({ name, department, email, photo }) {
  const imgSrc = photo ? buildMediaUrl(photo) : avatar;
  return (
    <div className={styles.card}>
      <img src={imgSrc} alt={name} className={styles.image} />
      <div className={styles.info}>
        <h3 className={styles.name}>{name}</h3>
        <p className={styles.department}>{department}</p>
        <p className={styles.email}>{email}</p>
      </div>
    </div>
  );
}
