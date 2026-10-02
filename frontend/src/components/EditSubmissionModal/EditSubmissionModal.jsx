import styles from './EditSubmissionModal.module.css';
import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import avatar from '../../assets/avatar.png';
import Title from '../ui/Title/Title';
import Modal from '../ui/Modal/Modal';

import { fetchWithAuth, buildMediaUrl } from '../../utils/api.js';

export default function EditSubmissionModal({ submission, onClose, onSave }) {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    affiliation: "",
    abstract_title: "",
    abstract_text: "",
    additional_authors: "",
    additional_affiliations: "",
    arrival_date: "",
    departure_date: "",
    admin_notes: "",
  });

  const [photo, setPhoto] = useState(null);

  const [photoPreview, setPhotoPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [wordCount, setWordCount] = useState(0);
  const [modal, setModal] = useState({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: null,
    type: 'default'
  });

  function openModal(config) {
    setModal({
      isOpen: true,
      ...config
    });
  }

  function closeModal() {
    setModal(prev => ({ ...prev, isOpen: false }));
  }

  useEffect(() => {
    document.body.style.overflow = 'hidden';
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
    document.body.style.paddingRight = `${scrollbarWidth}px`;

    if (submission) {
      setFormData({
        name: submission.name || "",
        email: submission.email || "",
        affiliation: submission.affiliation || "",
        abstract_title: submission.abstract_title || "",
        abstract_text: submission.abstract_text || "",
        additional_authors: submission.additional_authors || "",
        additional_affiliations: submission.additional_affiliations || "",
        arrival_date: submission.arrival_date || "",
        departure_date: submission.departure_date || "",
        admin_notes: submission.admin_notes || "",
      });

      if (submission.photo) {
        setPhotoPreview(buildMediaUrl(submission.photo));
      }

      if (submission.abstract_text) {
        const words = submission.abstract_text.trim().split(/\s+/).filter(w => w.length > 0);
        setWordCount(words.length);
      }
    }

    return () => {
      document.body.style.overflow = '';
      document.body.style.paddingRight = '';
    };
  }, [submission]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));

    if (name === "abstract_text") {
      const words = value.trim().split(/\s+/).filter(w => w.length > 0);
      setWordCount(words.length);
    }
  };

  const handlePhotoChange = (e) => {
  const file = e.target.files[0];

  if (file) {
    if (!file.type.startsWith('image/')) {
      openModal({
        title: "Invalid file",
        message: "Please select a valid image file.",
        type: "danger",
        onConfirm: closeModal
      });
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      openModal({
        title: "File too large",
        message: "Photo size must not exceed 5MB.",
        type: "danger",
        onConfirm: closeModal
      });
      return;
    }

    setPhoto(file);

    const reader = new FileReader();
    reader.onloadend = () => {
      setPhotoPreview(reader.result);
    };
    reader.readAsDataURL(file);
  }
 };

  const removePhoto = async () => {
  setLoading(true);

  try {
    const response = await fetchWithAuth(`/api/admin/submissions/${submission.id}/`, {
      method: 'PATCH',
      body: JSON.stringify({
        photo: null
      }),
    });

    if (response.ok) {
      const updated = await response.json();

      setPhoto(null);
      setPhotoPreview(null);

      const fileInput = document.querySelector('input[type="file"]');
      if (fileInput) {
        fileInput.value = '';
      }

      openModal({
        title: "Success",
        message: "Photo removed successfully!",
        type: "success",
        onConfirm: () => {
          closeModal();
          onSave(updated);
        }
      });
    } else {
      const errorText = await response.text();
      openModal({
        title: "Error",
        message: errorText || "Failed to remove photo.",
        type: "danger",
        onConfirm: closeModal
      });
    }
  } catch (error) {
    openModal({
      title: "Connection error",
      message: error.message || "Server is unreachable.",
      type: "danger",
      onConfirm: closeModal
    });
  } finally {
    setLoading(false);
  }
};

  const handleSubmit = async (e) => {
  e.preventDefault();
  setLoading(true);

  try {
    let response;

    if (photo) {
      const submitData = new FormData();
      Object.keys(formData).forEach(key => {
        if (formData[key] !== null && formData[key] !== undefined) {
          submitData.append(key, formData[key]);
        }
      });
      submitData.append('photo', photo);

      response = await fetchWithAuth(`/api/admin/submissions/${submission.id}/`, {
        method: 'PUT',
        body: submitData,
      });
    } else {
      response = await fetchWithAuth(`/api/admin/submissions/${submission.id}/`, {
        method: 'PATCH',
        body: JSON.stringify(formData),
      });
    }

    if (response.ok) {
      const updated = await response.json();
      openModal({
        title: "Success",
        message: "Changes saved successfully!",
        type: "success",
        onConfirm: () => {
          closeModal();
          onSave(updated);
          onClose();
        }
      });
    } else {
      const errorText = await response.text();
      openModal({
        title: "Save failed",
        message: errorText || `Failed to save (${response.status}).`,
        type: "danger",
        onConfirm: closeModal
      });
    }
  } catch (error) {
    openModal({
      title: "Connection error",
      message: error.message || "Server is unreachable.",
      type: "danger",
      onConfirm: closeModal
    });
  } finally {
    setLoading(false);
  }
};
  if (!submission) return null;

  return createPortal(
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <button
          className={styles.closeBtn}
          onClick={onClose}
          type="button"
        >
          ×
        </button>

        <Title text="Edit Submission" />

        {submission.status === 'approved' && (
          <div className={styles.approvedNotice}>
            This submission is published. Changes will update the public Participant and Abstract.
          </div>
        )}

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.photoSection}>
            {photoPreview ? (
              <div className={styles.photoPreview}>
                <img src={photoPreview} alt="Preview" />
              </div>
            ) : (
              <img src={avatar} alt="No photo" className={styles.avatarPlaceholder} />
            )}

            <div className={styles.photoButtons}>
              <label className={styles.uploadButton}>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handlePhotoChange}
                  style={{ display: 'none' }}
                />
                Change Photo
              </label>

              {photoPreview && (
                <button
                  type="button"
                  onClick={removePhoto}
                  className={styles.removeButton}
                  disabled={loading}
                >
                  Remove Photo
                </button>
              )}
            </div>
          </div>

          <div className={styles.formGrid}>
            <div className={styles.field}>
              <label>Name *</label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                required
              />
            </div>

            <div className={styles.field}>
              <label>Email *</label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
              />
            </div>

            <div className={styles.fieldFull}>
              <label>Affiliation *</label>
              <input
                type="text"
                name="affiliation"
                value={formData.affiliation}
                onChange={handleChange}
                required
              />
            </div>

            <div className={styles.fieldFull}>
              <label>Abstract Title</label>
              <input
                type="text"
                name="abstract_title"
                value={formData.abstract_title}
                onChange={handleChange}
              />
            </div>

            <div className={styles.fieldFull}>
              <label>
                Abstract Description
                <span className={styles.wordCount}>({wordCount} words)</span>
              </label>
              <textarea
                name="abstract_text"
                value={formData.abstract_text}
                onChange={handleChange}
                rows="8"
              />
            </div>

            <div className={styles.fieldFull}>
              <label>Additional Authors</label>
              <input
                type="text"
                name="additional_authors"
                value={formData.additional_authors}
                onChange={handleChange}
              />
            </div>

            <div className={styles.fieldFull}>
              <label>Additional Affiliations</label>
              <textarea
                name="additional_affiliations"
                value={formData.additional_affiliations}
                onChange={handleChange}
                rows="3"
              />
            </div>

            <div className={styles.field}>
              <label>Arrival Date *</label>
              <input
                type="date"
                name="arrival_date"
                value={formData.arrival_date}
                onChange={handleChange}
                required
              />
            </div>

            <div className={styles.field}>
              <label>Departure Date *</label>
              <input
                type="date"
                name="departure_date"
                value={formData.departure_date}
                onChange={handleChange}
                required
              />
            </div>

            <div className={styles.fieldFull}>
              <label>Admin Notes (internal)</label>
              <textarea
                name="admin_notes"
                value={formData.admin_notes}
                onChange={handleChange}
                rows="4"
                placeholder="Internal notes for admins..."
              />
            </div>
          </div>

          <div className={styles.actions}>
            <button type="submit" disabled={loading} className={styles.saveBtn}>
              {loading ? "Saving..." : "Save Changes"}
            </button>
            <button type="button" onClick={onClose} className={styles.cancelBtn}>
              Cancel
            </button>
          </div>
        </form>
        <Modal
          isOpen={modal.isOpen}
          title={modal.title}
          message={modal.message}
          type={modal.type}
          onConfirm={modal.onConfirm}
          onCancel={closeModal}
        />
      </div>
    </div>,
    document.body
  );
}