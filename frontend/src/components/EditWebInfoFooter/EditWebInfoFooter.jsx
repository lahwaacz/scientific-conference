import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchWithAuth } from "../../utils/api";
import Loader from "../ui/Loader/Loader";
import Title from "../ui/Title/Title";
import styles from "./EditWebInfoFooter.module.css";

export default function EditWebInfoFooter() {
  const [form, setForm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchWithAuth(`/api/conference-info/`)
      .then((r) => r.json())
      .then((data) => {
        setForm(data);
        setLoading(false);
      });
  }, []);

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    setSaved(false);
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const res = await fetchWithAuth(`/api/conference-info/edit/`, {
        method: "PATCH",
        body: JSON.stringify({
          grant_text: form.grant_text,
          venue_text: form.venue_text,
          conference_office_text: form.conference_office_text,
          website_url: form.website_url,
          poster_url: form.poster_url,
          info_desk_email: form.info_desk_email,
          copyright_text: form.copyright_text,
        }),
      });
      if (!res.ok) throw new Error();
      setSaved(true);
    } catch {
      setError("Failed to save. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={styles.container}>
      <Link to="/admin-panel/edit-web-info" className={styles.backButton}>
        ← BACK
      </Link>
      <Title text="Edit Footer" />

      {loading ? (
        <Loader />
      ) : (
        <form
          onSubmit={handleSave}
          className={`${styles.form} ${styles.fadeIn}`}
        >
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>
              Column 1 — Grant / Logo text
            </h2>
            <div className={styles.field}>
              <label>Grant Text</label>
              <textarea
                name="grant_text"
                rows={3}
                value={form.grant_text || ""}
                onChange={handleChange}
              />
            </div>
          </section>

          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Column 2 — Venue</h2>
            <div className={styles.field}>
              <label>Venue Text</label>
              <textarea
                name="venue_text"
                rows={3}
                value={form.venue_text || ""}
                onChange={handleChange}
              />
            </div>
          </section>

          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>
              Column 3 — Conference Office
            </h2>
            <div className={styles.field}>
              <label>Conference Office Text</label>
              <textarea
                name="conference_office_text"
                rows={3}
                value={form.conference_office_text || ""}
                onChange={handleChange}
              />
            </div>
          </section>

          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>
              Column 4 — Additional Information
            </h2>
            <div className={styles.field}>
              <label>Website URL</label>
              <input
                name="website_url"
                type="url"
                value={form.website_url || ""}
                onChange={handleChange}
                placeholder="https://..."
              />
            </div>
            <div className={styles.field}>
              <label>Conference Poster URL</label>
              <input
                name="poster_url"
                type="url"
                value={form.poster_url || ""}
                onChange={handleChange}
                placeholder="https://..."
              />
            </div>
            <div className={styles.field}>
              <label>Information Desk Email</label>
              <input
                name="info_desk_email"
                type="email"
                value={form.info_desk_email || ""}
                onChange={handleChange}
                placeholder="info@example.com"
              />
            </div>
          </section>

          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Bottom Row</h2>
            <div className={styles.field}>
              <label>Copyright Text</label>
              <input
                name="copyright_text"
                value={form.copyright_text || ""}
                onChange={handleChange}
                placeholder="© 2025 WSC. All rights reserved."
              />
            </div>
          </section>

          {error && <p className={styles.error}>{error}</p>}

          <div className={styles.actions}>
            {saved && (
              <span className={styles.savedMsg}>✓ Saved successfully</span>
            )}
            <button
              type="submit"
              className={styles.saveButton}
              disabled={saving}
            >
              {saving ? "Saving..." : "SAVE CHANGES"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
