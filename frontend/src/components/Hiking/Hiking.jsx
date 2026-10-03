import { useEffect, useState } from "react";
import styles from "./Hiking.module.css";
import Title from "../ui/Title/Title";
import Loader from "../ui/Loader/Loader";
import { buildApiUrl } from "../../utils/api";

export default function Hiking() {
  const [routes, setRoutes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(buildApiUrl("/api/hiking/"))
      .then((r) => r.json())
      .then((data) => {
        setRoutes(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div className={styles.container}>
      <Title text="HIKING" />

      {loading ? (
        <Loader />
      ) : (
        <div className={styles.fadeIn}>
          {routes.length === 0 && (
            <p className={styles.empty}>No hiking routes available yet.</p>
          )}

          {routes.map((route) => (
            <div key={route.id} className={styles.route}>
              <h2 className={styles.routeName}>{route.name.toUpperCase()}</h2>

              {route.way_description && (
                <p className={styles.routeWay}>
                  <span className={styles.label}>Way:</span>{" "}
                  {route.way_description}
                </p>
              )}

              {route.map_url && (
                <a
                  className={styles.mapLink}
                  href={route.map_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  → View on map
                </a>
              )}

              {route.stops && route.stops.length > 0 && (
                <div className={styles.stops}>
                  {route.stops.map((stop) => (
                    <div key={stop.id} className={styles.stopRow}>
                      {stop.photo && (
                        <img
                          className={styles.stopPhoto}
                          src={stop.photo}
                          alt={stop.name}
                        />
                      )}
                      <div className={styles.stopInfo}>
                        <h3 className={styles.stopName}>
                          {stop.name.toUpperCase()}
                        </h3>
                        {stop.description && (
                          <p className={styles.stopDescription}>
                            — {stop.description}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
