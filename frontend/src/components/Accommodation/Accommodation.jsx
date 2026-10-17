import { useEffect, useState } from "react";
import { buildApiUrl, buildMediaUrl } from "../../utils/api";
import Loader from "../ui/Loader/Loader";
import Markdown from "../ui/Markdown/Markdown";
import Title from "../ui/Title/Title";
import styles from "./Accommodation.module.css";

export default function Accommodation() {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(buildApiUrl("/api/accommodation/"))
      .then((res) => res.json())
      .then((payload) =>
        setData({
          ...payload,
          options: Array.isArray(payload.options) ? payload.options : [],
        })
      );
  }, []);

  return (
    <section className={styles.section}>
      <div className={styles.container}>
        <Title text="Accommodation" />

        {!data ? (
          <Loader />
        ) : (
          <div className={styles.fadeIn}>
            {data.description && (
              <Markdown
                text={data.description}
                className={styles.description}
              />
            )}
            <div className={styles.options}>
              {data.options.map((option) => (
                <div key={option.id} className={styles.option}>
                  {option.photo && (
                    <img
                      src={buildMediaUrl(option.photo)}
                      alt={option.name}
                      className={styles.photo}
                    />
                  )}
                  <div className={styles.optionInfo}>
                    <a
                      href={option.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={styles.optionName}
                    >
                      {option.name}
                    </a>
                    {option.description && (
                      <Markdown
                        text={option.description}
                        className={styles.optionDesc}
                      />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
