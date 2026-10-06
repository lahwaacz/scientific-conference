import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { buildMediaUrl, fetchWithAuth } from "../../utils/api";
import Loader from "../ui/Loader/Loader";
import Title from "../ui/Title/Title";
import styles from "./EditWebInfoVenue.module.css";

export default function EditWebInfoVenue() {
  const [form, setForm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [venuePhotoFile, setVenuePhotoFile] = useState(null);

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

  function handleVenuePhotoChange(e) {
    setVenuePhotoFile(e.target.files[0]);
    setSaved(false);
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const fd = new FormData();
      fd.append("venue_text", form.venue_text ?? "");
      fd.append("venue_map_embed_url", form.venue_map_embed_url ?? "");
      // Absent key = keep the existing photo.
      if (venuePhotoFile) fd.append("venue_photo", venuePhotoFile);

      const res = await fetchWithAuth(`/api/conference-info/edit/`, {
        method: "PATCH",
        body: fd,
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

      <Title text="Edit Venue" />

      {loading ? (
        <Loader />
      ) : (
        <>
          <form
            onSubmit={handleSave}
            className={`${styles.form} ${styles.fadeIn}`}
          >
            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>Venue</h2>

              <div className={styles.field}>
                <label>Venue</label>
                <textarea
                  name="venue_text"
                  rows={5}
                  value={form.venue_text || ""}
                  onChange={handleChange}
                />
              </div>

              <div className={styles.field}>
                <label>
                  Venue photo{" "}
                  <span className={styles.hint}>
                    (leave empty to keep the current one)
                  </span>
                </label>
                {venuePhotoFile ? (
                  <img
                    src={URL.createObjectURL(venuePhotoFile)}
                    alt="New venue preview"
                    className={styles.photoPreview}
                  />
                ) : form.venue_photo ? (
                  <img
                    src={buildMediaUrl(form.venue_photo)}
                    alt="Venue"
                    className={styles.photoPreview}
                  />
                ) : null}
                <input
                  type="file"
                  name="venue_photo"
                  accept="image/*"
                  onChange={handleVenuePhotoChange}
                />
              </div>

              <div className={styles.field}>
                <label>Google Maps Embed URL</label>
                <small className={styles.hint}>
                  Google Maps → Share → Embed a map → Copy src from iframe
                </small>
                <input
                  name="venue_map_embed_url"
                  value={form.venue_map_embed_url || ""}
                  onChange={handleChange}
                  placeholder="https://www.google.com/maps/embed?pb=..."
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

          {(form.venue_text ||
            form.venue_map_embed_url ||
            form.venue_photo ||
            venuePhotoFile) && (
            <section className={styles.section} style={{ marginTop: 40 }}>
              <h2 className={styles.sectionTitle}>Preview</h2>

              {form.venue_text && (
                <p className={styles.previewText}>{form.venue_text}</p>
              )}

              {venuePhotoFile ? (
                <img
                  src={URL.createObjectURL(venuePhotoFile)}
                  alt="Venue"
                  className={styles.photoPreview}
                />
              ) : form.venue_photo ? (
                <img
                  src={buildMediaUrl(form.venue_photo)}
                  alt="Venue"
                  className={styles.photoPreview}
                />
              ) : null}

              {form.venue_map_embed_url && (
                <iframe
                  src={form.venue_map_embed_url}
                  className={styles.mapPreview}
                  allowFullScreen=""
                  loading="lazy"
                  title="Venue map"
                />
              )}
            </section>
          )}
        </>
      )}
    </div>
  );
}
