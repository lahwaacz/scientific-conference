import { Link } from "react-router-dom";
import { useConferenceInfo } from "./../hooks/useConferenceInfo";
import Separator from "../ui/Separator/Separator";
import Title from "../ui/Title/Title";
import styles from "./Registration.module.css";

export default function Registration() {
  const info = useConferenceInfo();

  const deadline = info?.registration_deadline
    ? new Date(info.registration_deadline).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : "";

  const instructions = !info
    ? []
    : info.registration_instructions
      ? info.registration_instructions.split("\n").filter(Boolean)
      : [
          "Name",
          "Your e-mail",
          "Affiliation",
          "The abstract of your contribution",
          "Arrival and departure dates",
        ];

  return (
    <section className={styles.registration}>
      <div className={styles.container}>
        <div className={styles.leftSide}>
          <Title text="Registration" />
          <p className={styles.description}>{info?.registration_fee_note}</p>
          <p className={styles.strong}>Required registration data:</p>
          <ol>
            {instructions.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ol>
          {deadline && (
            <p className={styles.deadline}>
              Please submit your registration <br /> until {deadline}
            </p>
          )}
        </div>
        <div className={styles.rightSide}>
          <Link to="/registration" className={styles.button}>
            TO THE REGISTRATION FORM
          </Link>
        </div>
      </div>
      <Separator />
    </section>
  );
}
