import { useLocation } from "react-router-dom";
import styles from "./PageLayout.module.css";

export default function PageLayout({ children }) {
  const { pathname } = useLocation();
  return (
    <div className={pathname === "/" ? styles.home : styles.page}>
      {children}
    </div>
  );
}
