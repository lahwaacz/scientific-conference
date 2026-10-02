import styles from './OrganisingCommittee.module.css';
import HomeCard from '../ui/HomeCard/HomeCard';
import Separator from '../ui/Separator/Separator';
import Title from '../ui/Title/Title';
import Loader from '../ui/Loader/Loader';
import { useEffect, useState } from "react";
import { buildApiUrl } from '../../utils/api';

export default function OrganisingCommittee() {
    const [organisers, setOrganisers] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch(buildApiUrl("/api/committees/"))
            .then(res => res.json())
            .then(data => {
                setOrganisers(data);
                setLoading(false);
            })
            .catch(() => setLoading(false));
    }, []);

    return (
        <section className={styles.committeeSection}>
            <div className={styles.container}>
                <Title text="Organising Committee" />
                {loading ? (
                    <Loader />
                ) : (
        <div className={`${styles.cardsContainer} ${styles.fadeIn}`}>
          {organisers.map(person => (
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
            <Separator />
        </section>
    );
}