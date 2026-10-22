import { Link } from "react-router-dom";
import Title from "../ui/Title/Title";
import styles from "./NotFound.module.css";

// Catch-all for unmatched conference hash routes. PageLayout owns the page
// padding, and the flex shell owns footer placement — this fills content only.
export default function NotFound() {
  return (
    <section>
      <Title text="Page Not Found" />
      <p className={styles.message}>
        The page you are looking for does not exist.
      </p>
      <Link to="/" className={styles.homeLink}>
        Back to home
      </Link>
    </section>
  );
}
