import styles from "./Participants.module.css";
import Title from "../ui/Title/Title";
import ParticipantsCard from "../ui/ParticipantsCard/ParticipantsCard";
import { useEffect, useState } from "react";
import Loader from "../ui/Loader/Loader";
import { buildApiUrl } from "../../utils/api";

export default function Participants() {
  const [participants, setParticipants] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(buildApiUrl("/api/participants/"))
      .then((res) => res.json())
      .then((data) => {
        setParticipants(data);
        setLoading(false);
      });
  }, []);

  return (
    <section className={styles.participantsSection}>
      <Title text="List of participants" />

      {loading ? (
        <Loader />
      ) : (
        <div className={`${styles.cardsContainer} ${styles.fadeIn}`}>
          {participants.map((person) => (
            <ParticipantsCard
              key={person.id}
              id={person.id}
              name={person.name}
              department={person.affiliation}
              email={person.email}
              abstractId={person.abstract_id}
              photo={person.photo}
            />
          ))}
        </div>
      )}
    </section>
  );
}
