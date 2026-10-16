import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { buildMediaUrl, fetchWithAuth } from "../../utils/api";
import PhotoCropModal from "../PhotoCropModal/PhotoCropModal";
import Loader from "../ui/Loader/Loader";
import Title from "../ui/Title/Title";
import styles from "./EditWebInfoHome.module.css";

export default function EditWebInfoHome() {
  const [form, setForm] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [people, setPeople] = useState([]);
  const [personSaved, setPersonSaved] = useState(false);
  const [personError, setPersonError] = useState("");
  const [cardPhoto, setCardPhoto] = useState(null);
  const [cardPhotoFile, setCardPhotoFile] = useState(null);
  const [heroPhoto, setHeroPhoto] = useState(null);
  const [heroPhotoFile, setHeroPhotoFile] = useState(null);

  useEffect(() => {
    Promise.all([
      fetchWithAuth(`/api/conference-info/`).then((r) => r.json()),
      fetchWithAuth(`/api/people/`).then((r) => r.json()),
    ]).then(([info, personList]) => {
      // `year` is derived from date_start on the backend and the
      // photos are only replaced via the file inputs; the registration
      // fields (including the submission-editing deadline) are owned by
      // the Registration subsection editor and must not be written back
      // from here. None of them belongs in form state or the PATCH body.
      const {
        year,
        card_photo,
        hero_photo,
        venue_photo,
        registration_fee_note,
        registration_instructions,
        registration_opening,
        registration_deadline,
        submission_edit_deadline,
        ...formInfo
      } = info;
      setCardPhoto(card_photo || null);
      setHeroPhoto(hero_photo || null);
      setForm({
        title: "",
        location: "",
        date_start: "",
        date_end: "",
        short_description: "",
        badge_title: "",
        ...formInfo,
      });
      setPeople(Array.isArray(personList) ? personList : []);
      setLoading(false);
    });
  }, []);

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    setSaved(false);
  }

  function handleCardPhotoChange(e) {
    setCardPhotoFile(e.target.files[0]);
    setSaved(false);
  }

  function handleHeroPhotoChange(e) {
    setHeroPhotoFile(e.target.files[0]);
    setSaved(false);
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const fd = new FormData();
      for (const [key, value] of Object.entries(form)) {
        fd.append(key, value ?? "");
      }
      // Absent key = keep the existing photo (card and hero alike).
      if (cardPhotoFile) fd.append("card_photo", cardPhotoFile);
      if (heroPhotoFile) fd.append("hero_photo", heroPhotoFile);

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

  function handlePersonChange(index, field, value) {
    setPeople((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], [field]: value };
      return updated;
    });
  }

  function handlePersonRole(index, role) {
    setPeople((prev) => {
      const updated = [...prev];
      const person = updated[index];
      const roles = person.roles || [];
      updated[index] = {
        ...person,
        roles: roles.includes(role)
          ? roles.filter((r) => r !== role)
          : [...roles, role],
      };
      return updated;
    });
  }

  function handlePersonPhoto(index, file) {
    setPeople((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], _photoFile: file };
      return updated;
    });
  }

  async function savePerson(person) {
    const send = async (url, method, body) => {
      const res = await fetchWithAuth(url, { method, body });
      const text = await res.text();
      if (!res.ok) {
        throw new Error(text || `Request failed with ${res.status}`);
      }
      return text ? JSON.parse(text) : person;
    };

    // The JSON body always carries an explicit `roles` array: an empty
    // list clears the person's roles, which multipart FormData cannot
    // express (a missing key means "leave unchanged" on the backend).
    let saved = await send(
      person.id ? `/api/people/${person.id}/` : "/api/people/",
      person.id ? "PATCH" : "POST",
      JSON.stringify({
        name: person.name || "",
        affiliation: person.affiliation || "",
        email: person.email || "",
        roles: person.roles || [],
      })
    );

    // Photos need multipart; a follow-up PATCH swaps only the photo so
    // the explicit roles above survive (saved.id also covers new rows).
    if (person._photoFile && saved.id) {
      const fd = new FormData();
      fd.append("photo", person._photoFile);
      saved = await send(`/api/people/${saved.id}/`, "PATCH", fd);
    }

    return saved;
  }

  async function deletePerson(id) {
    //if (!window.confirm('Delete this person?')) return;
    if (id) {
      await fetchWithAuth(`/api/people/${id}/`, { method: "DELETE" });
    }
    setPeople((prev) => prev.filter((p) => p.id !== id));
  }

  function addPerson() {
    setPeople((prev) => [
      ...prev,
      { name: "", affiliation: "", email: "", photo: null, roles: [] },
    ]);
  }

  async function saveAllPeople() {
    setSaving(true);
    setPersonError("");
    setPersonSaved(false);

    try {
      const updated = await Promise.all(people.map((p) => savePerson(p)));
      setPeople(updated);
      setPersonSaved(true);
    } catch {
      setPersonError("Failed to save. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={styles.container}>
      <Link to="/admin-panel/edit-web-info" className={styles.backButton}>
        ← BACK
      </Link>
      <Title text="Edit Home" />

      {loading ? (
        <Loader />
      ) : (
        <div className={styles.fadeIn}>
          {/* Conference Info Form */}
          <form onSubmit={handleSave} className={styles.form}>
            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>Hero</h2>

              <div className={styles.field}>
                <label>Conference Title</label>
                <input
                  name="title"
                  value={form.title || ""}
                  onChange={handleChange}
                />
              </div>

              <div className={styles.field}>
                <label>Short Description</label>
                <input
                  name="short_description"
                  value={form.short_description || ""}
                  onChange={handleChange}
                />
              </div>

              <div className={styles.row}>
                <div className={styles.field}>
                  <label>Location</label>
                  <input
                    name="location"
                    value={form.location || ""}
                    onChange={handleChange}
                  />
                </div>
                <div className={styles.field}>
                  <label>Badge Title</label>
                  <input
                    name="badge_title"
                    value={form.badge_title || ""}
                    onChange={handleChange}
                  />
                </div>
              </div>

              <div className={styles.row}>
                <div className={styles.field}>
                  <label>Date Start</label>
                  <input
                    name="date_start"
                    type="date"
                    value={form.date_start || ""}
                    onChange={handleChange}
                  />
                </div>
                <div className={styles.field}>
                  <label>Date End</label>
                  <input
                    name="date_end"
                    type="date"
                    value={form.date_end || ""}
                    onChange={handleChange}
                  />
                </div>
              </div>

              <div className={styles.field}>
                <label>
                  Card photo{" "}
                  <span className={styles.hint}>
                    (leave empty to keep the current photo)
                  </span>
                </label>
                {cardPhotoFile ? (
                  <img
                    src={URL.createObjectURL(cardPhotoFile)}
                    alt="New card preview"
                    className={styles.photoPreview}
                  />
                ) : cardPhoto ? (
                  <img
                    src={buildMediaUrl(cardPhoto)}
                    alt="Conference card"
                    className={styles.photoPreview}
                  />
                ) : null}
                <input
                  type="file"
                  name="card_photo"
                  accept="image/*"
                  onChange={handleCardPhotoChange}
                />
              </div>

              <div className={styles.field}>
                <label>
                  Hero photo{" "}
                  <span className={styles.hint}>
                    (leave empty to keep the current photo)
                  </span>
                </label>
                {heroPhotoFile ? (
                  <img
                    src={URL.createObjectURL(heroPhotoFile)}
                    alt="New hero preview"
                    className={styles.photoPreview}
                  />
                ) : heroPhoto ? (
                  <img
                    src={buildMediaUrl(heroPhoto)}
                    alt="Conference hero"
                    className={styles.photoPreview}
                  />
                ) : null}
                <input
                  type="file"
                  name="hero_photo"
                  accept="image/*"
                  onChange={handleHeroPhotoChange}
                />
              </div>

              <div className={styles.field}>
                <label>Description</label>
                <textarea
                  name="description"
                  rows={5}
                  value={form.description || ""}
                  onChange={handleChange}
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

          {/* People (organisers and organising committee, one record each) */}
          <PersonSection
            title="People"
            list={people}
            saving={saving}
            savedMsg={personSaved ? "✓ Saved successfully" : ""}
            errorMsg={personError}
            onSaveAll={saveAllPeople}
            onDelete={deletePerson}
            onChange={handlePersonChange}
            onToggleRole={handlePersonRole}
            onPhoto={handlePersonPhoto}
            onAdd={addPerson}
          />
        </div>
      )}
    </div>
  );
}

function PersonSection({
  title,
  list,
  onSaveAll,
  onDelete,
  onChange,
  onToggleRole,
  onPhoto,
  onAdd,
  saving,
  savedMsg,
  errorMsg,
}) {
  // The dialog binds to the row OBJECT, not its index: focus is not
  // trapped inside the overlay, so a keyboard user can delete another
  // row behind it and shift the indices — an index binding would then
  // crop the wrong person. The index is re-derived from the object at
  // render/apply time; a stale target (its row deleted or replaced)
  // closes the dialog instead of writing to whatever row took its slot.
  const [cropTarget, setCropTarget] = useState(null);
  const cropIndex = cropTarget ? list.indexOf(cropTarget) : -1;

  return (
    <section className={styles.section} style={{ marginTop: 40 }}>
      <h2 className={styles.sectionTitle}>{title}</h2>

      {list.length === 0 && (
        <p className={styles.emptyMsg}>No people added yet.</p>
      )}

      {list.map((person, i) => (
        <div key={person.id ?? `new-${i}`} className={styles.personRow}>
          <div className={styles.photoCol}>
            {person._photoFile ? (
              <img
                src={URL.createObjectURL(person._photoFile)}
                alt="preview"
                className={styles.personPhoto}
              />
            ) : person.photo ? (
              <img
                src={buildMediaUrl(person.photo)}
                alt={person.name}
                className={styles.personPhoto}
              />
            ) : (
              <div className={styles.photoPlaceholder} />
            )}
            <label className={styles.photoLabel}>
              Change photo
              <input
                type="file"
                accept="image/*"
                onChange={(e) => onPhoto(i, e.target.files[0])}
                className={styles.fileInputHidden}
              />
            </label>
            {person._photoFile && (
              <button
                type="button"
                className={styles.cropButton}
                onClick={() => setCropTarget(person)}
              >
                Crop…
              </button>
            )}
          </div>

          <div className={styles.personFields}>
            <div className={styles.field}>
              <label>Name</label>
              <input
                value={person.name || ""}
                onChange={(e) => onChange(i, "name", e.target.value)}
              />
            </div>
            <div className={styles.field}>
              <label>Affiliation</label>
              <input
                value={person.affiliation || ""}
                onChange={(e) => onChange(i, "affiliation", e.target.value)}
              />
            </div>
            <div className={styles.field}>
              <label>Email</label>
              <input
                type="email"
                value={person.email || ""}
                onChange={(e) => onChange(i, "email", e.target.value)}
              />
            </div>
            <div className={styles.rolesField}>
              <span className={styles.rolesLegend}>Roles</span>
              <div className={styles.roleCheckboxes}>
                <label className={styles.roleCheckbox}>
                  <input
                    type="checkbox"
                    checked={(person.roles || []).includes("organizer")}
                    onChange={() => onToggleRole(i, "organizer")}
                  />
                  Organiser
                </label>
                <label className={styles.roleCheckbox}>
                  <input
                    type="checkbox"
                    checked={(person.roles || []).includes("committee")}
                    onChange={() => onToggleRole(i, "committee")}
                  />
                  Organising Committee
                </label>
              </div>
            </div>
          </div>

          <button
            type="button"
            className={styles.deleteButton}
            onClick={() => onDelete(person.id)}
          >
            ✕
          </button>
        </div>
      ))}

      {errorMsg && <p className={styles.error}>{errorMsg}</p>}

      <div className={styles.personActions}>
        <button type="button" className={styles.addButton} onClick={onAdd}>
          + ADD PERSON
        </button>
        <div className={styles.saveRow}>
          {savedMsg && <span className={styles.savedMsg}>{savedMsg}</span>}
          <button
            type="button"
            className={styles.saveButton}
            onClick={onSaveAll}
            disabled={saving}
          >
            {saving ? "Saving..." : `SAVE ${title.toUpperCase()}`}
          </button>
        </div>
      </div>

      {cropIndex !== -1 && cropTarget._photoFile && (
        <PhotoCropModal
          file={cropTarget._photoFile}
          onApply={(cropped) => {
            if (cropIndex !== -1) onPhoto(cropIndex, cropped);
            setCropTarget(null);
          }}
          onCancel={() => setCropTarget(null)}
        />
      )}
    </section>
  );
}
