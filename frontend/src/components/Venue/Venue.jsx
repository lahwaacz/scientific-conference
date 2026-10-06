import { buildMediaUrl } from "../../utils/api";
import { useConferenceInfo } from "./../hooks/useConferenceInfo";
import Loader from "../ui/Loader/Loader";
import Title from "../ui/Title/Title";
import styles from "./Venue.module.css";

export default function Venue() {
  const info = useConferenceInfo();

  return (
    <section className={styles.venueSection}>
      <Title text="Venue" />

      {!info ? (
        <Loader />
      ) : (
        <div className={styles.fadeIn}>
          <div className={styles.container}>
            <div className={styles.content}>
              <p className={styles.description}>{info?.venue_text || ""}</p>
              {info?.venue_photo && (
                <img
                  src={buildMediaUrl(info.venue_photo)}
                  alt="Venue"
                  className={styles.venuePhoto}
                />
              )}
              {info?.venue_map_embed_url && (
                <div className={styles.mapWrapper}>
                  <iframe
                    title="Venue map"
                    src={info.venue_map_embed_url}
                    width="100%"
                    height="400"
                    style={{ border: 0 }}
                    allowFullScreen=""
                    loading="lazy"
                    referrerPolicy="no-referrer-when-downgrade"
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
