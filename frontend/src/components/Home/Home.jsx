import Hero from "../Hero/Hero";
import Organisers from "../Organisers/Organisers";
import OrganisingCommittee from "../OrganisingCommittee/OrganisingCommittee";
import Registration from "../Registration/Registration";
import Sponsors from "../Sponsors/Sponsors";
import styles from "./Home.module.css";

export default function Home() {
  return (
    <div className={styles.container}>
      <div className={styles.fadeIn}>
        <Hero />
        <Registration />
        <Sponsors />
        <OrganisingCommittee />
        <Organisers />
      </div>
    </div>
  );
}
