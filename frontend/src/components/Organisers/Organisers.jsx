import { useEffect, useState } from "react";
import { buildApiUrl } from "../../utils/api";
import HomeCard from "../ui/HomeCard/HomeCard";
import Loader from "../ui/Loader/Loader";
import Title from "../ui/Title/Title";
import styles from "./Organisers.module.css";

export default function Organisers() {
  const [organisers, setOrganisers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(buildApiUrl("/api/organizers/"))
      .then((res) => res.json())
      .then((data) => {
        setOrganisers(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <section className={styles.organisersSection}>
      <div className={styles.cardsWrapper}>
        <Title text="Organisers" />
        {loading ? (
          <Loader />
        ) : (
          <div className={`${styles.cardsContainer} ${styles.fadeIn}`}>
            {organisers.map((person) => (
              <HomeCard
                key={person.id}
                name={person.name}
                department={person.department}
                email={person.email}
                photo={person.photo}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
