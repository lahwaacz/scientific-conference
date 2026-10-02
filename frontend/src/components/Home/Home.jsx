import Hero from '../Hero/Hero';
import Registration from '../Registration/Registration';
import OrganisingCommittee from '../OrganisingCommittee/OrganisingCommittee';
import Organisers from '../Organisers/Organisers';
import styles from './Home.module.css';




export default function Home() {
    return (
        <div className={styles.container}>
        <div className={styles.fadeIn}>
            <Hero />
            <Registration />
            <OrganisingCommittee />
            <Organisers />
        </div>
        </div>
    )
}