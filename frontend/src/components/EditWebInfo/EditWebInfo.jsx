import { library } from "@fortawesome/fontawesome-svg-core";
import { fas } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Link, useNavigate } from "react-router-dom";
import Title from "../ui/Title/Title";
import styles from "./EditWebInfo.module.css";

library.add(fas);

const sections = [
  {
    to: "/admin-panel/edit-web-info/home",
    icon: "fa-solid fa-house",
    title: "Home",
    description: "Edit conference title, date, location and description",
  },
  {
    to: "/admin-panel/edit-web-info/registration",
    icon: "fa-solid fa-pen-to-square",
    title: "Registration",
    description: "Edit registration instructions and deadline",
  },
  {
    to: "/admin-panel/edit-web-info/program",
    icon: "fa-solid fa-calendar-days",
    title: "Program",
    description: "Edit program page info texts",
  },
  {
    to: "/admin-panel/edit-web-info/venue",
    icon: "fa-solid fa-location-dot",
    title: "Venue",
    description: "Edit venue address and map link",
  },
  {
    to: "/admin-panel/edit-web-info/accommodation",
    icon: "fa-solid fa-bed",
    title: "Accommodation",
    description: "Edit accommodation description and options",
  },
  {
    to: "/admin-panel/edit-web-info/hiking",
    icon: "fa-solid fa-person-hiking",
    title: "Hiking",
    description: "Edit hiking routes and stops",
  },
  {
    to: "/admin-panel/edit-web-info/footer",
    icon: "fa-solid fa-file-lines",
    title: "Footer",
    description: "Edit footer texts, links and copyright",
  },
];

export default function EditWebInfo() {
  const navigate = useNavigate();

  return (
    <div className={styles.container}>
      <button
        onClick={() => navigate("/admin-panel")}
        className={styles.backBtn}
      >
        ← Back
      </button>
      <Title text="Edit Web Info" />
      <div className={`${styles.buttonGrid} ${styles.fadeIn}`}>
        {sections.map((section) => (
          <Link key={section.to} to={section.to} className={styles.adminButton}>
            <span className={styles.iconWrapper}>
              <FontAwesomeIcon
                icon={section.icon}
                className={styles.adminIcon}
              />
            </span>
            <h3 className={styles.buttonTitle}>{section.title}</h3>
            <p className={styles.description}>{section.description}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
