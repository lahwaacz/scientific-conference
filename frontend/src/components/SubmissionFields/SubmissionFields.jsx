import styles from "./SubmissionFields.module.css";

export default function SubmissionFields({
  formData,
  errors,
  photoPreview,
  onChange,
  onPhotoChange,
  onRemovePhoto,
  wordCount,
}) {
  return (
    <>
      {/* Name */}
      <div className={styles.field}>
        <label className={styles.label}>
          Name <span className={styles.required}>*</span>
        </label>
        <input
          type="text"
          name="name"
          value={formData.name}
          onChange={onChange}
          maxLength={100}
          required
        />
        {errors.name && <span className={styles.error}>{errors.name}</span>}
      </div>

      {/* Email */}
      <div className={styles.field}>
        <label className={styles.label}>
          Email <span className={styles.required}>*</span>
        </label>
        <input
          type="email"
          name="email"
          placeholder="your.email@example.com"
          value={formData.email}
          onChange={onChange}
          maxLength={100}
          required
        />
        {errors.email && <span className={styles.error}>{errors.email}</span>}
      </div>

      {/* Affiliation */}
      <div className={styles.field}>
        <label className={styles.label}>
          Affiliation <span className={styles.required}>*</span>
        </label>
        <input
          type="text"
          name="affiliation"
          placeholder="University or Institution"
          value={formData.affiliation}
          onChange={onChange}
          maxLength={200}
          required
        />
        {errors.affiliation && (
          <span className={styles.error}>{errors.affiliation}</span>
        )}
      </div>

      {/* Photo */}
      <div className={styles.field}>
        <label className={styles.label}>Photo (optional)</label>
        <div className={styles.photoUpload}>
          {!photoPreview ? (
            <label className={styles.uploadButton}>
              <input
                type="file"
                accept="image/*"
                onChange={onPhotoChange}
                style={{ display: "none" }}
              />
              📷 Choose Photo
            </label>
          ) : (
            <div className={styles.photoPreview}>
              <img src={photoPreview} alt="Preview" />
              <button
                type="button"
                onClick={onRemovePhoto}
                className={styles.removePhoto}
              >
                Remove
              </button>
            </div>
          )}
        </div>
        {errors.photo && <span className={styles.error}>{errors.photo}</span>}
        <small className={styles.hint}>Max 5MB, JPG/PNG format</small>
      </div>

      {/* Abstract title */}
      <div className={styles.field}>
        <label className={styles.label}>Abstract Title</label>
        <input
          type="text"
          name="abstract_title"
          placeholder="Title of your presentation"
          value={formData.abstract_title}
          onChange={onChange}
          maxLength={400}
        />
      </div>

      {/* Abstract text */}
      <div className={styles.field}>
        <label className={styles.label}>
          Abstract Description
          <span className={styles.wordCount}> ({wordCount}/250 words)</span>
        </label>
        <textarea
          name="abstract_text"
          placeholder="Brief description of your contribution (max 250 words)"
          value={formData.abstract_text}
          onChange={onChange}
          maxLength={2500}
        />
        {errors.abstract_text && (
          <span className={styles.error}>{errors.abstract_text}</span>
        )}
      </div>

      {/* Additional authors */}
      <div className={styles.field}>
        <label className={styles.label}>Additional Authors</label>
        <input
          type="text"
          name="additional_authors"
          placeholder="Co-authors (if any)"
          value={formData.additional_authors}
          onChange={onChange}
          maxLength={300}
        />
      </div>

      {/* Additional affiliations */}
      <div className={styles.field}>
        <label className={styles.label}>Additional Affiliations</label>
        <textarea
          name="additional_affiliations"
          placeholder="Affiliations of co-authors (if any)"
          value={formData.additional_affiliations}
          onChange={onChange}
          rows="3"
          maxLength={500}
        />
      </div>

      {/* Dates */}
      <div className={styles.fieldRow}>
        <div>
          <label className={styles.date}>
            Arrival Date <span className={styles.required}>*</span>
          </label>
          <input
            type="date"
            name="arrival"
            value={formData.arrival}
            onChange={onChange}
            required
          />
          {errors.arrival && (
            <span className={styles.error}>{errors.arrival}</span>
          )}
        </div>
        <div>
          <label className={styles.date}>
            Departure Date <span className={styles.required}>*</span>
          </label>
          <input
            type="date"
            name="departure"
            value={formData.departure}
            onChange={onChange}
            required
          />
          {errors.departure && (
            <span className={styles.error}>{errors.departure}</span>
          )}
        </div>
      </div>

      {/* Student checkbox */}
      <div className={styles.field}>
        <label className={styles.checkboxLabel}>
          <input
            className={styles.checkbox}
            type="checkbox"
            name="is_student"
            checked={formData.is_student}
            onChange={onChange}
          />
          I am a student
        </label>
      </div>

      {/* Additional info */}
      <div className={styles.field}>
        <label className={styles.label}>Additional Information</label>
        <textarea
          name="info"
          placeholder="Any additional information (dietary restrictions, accessibility needs, etc.)"
          value={formData.info}
          onChange={onChange}
          rows="3"
          maxLength={1000}
        />
      </div>
    </>
  );
}
