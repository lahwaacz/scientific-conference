import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import ReactCrop from "react-image-crop";
import "react-image-crop/dist/ReactCrop.css";
import { cropToSquareFile, defaultSquareCrop } from "../../utils/imageCrop.js";
import { useLockBodyScroll } from "../hooks/useLockBodyScroll";
import styles from "./PhotoCropModal.module.css";

/**
 * Square-crop dialog for a freshly picked photo File. Never traps the
 * user: if the canvas encode fails, the original file is applied.
 *
 * Deliberately contains no <input type="file">: call sites clear their
 * own inputs via a global document.querySelector, and an extra file
 * input inside a portal would break that lookup.
 *
 * @param {{file: File, onApply: (cropped: File) => void, onCancel: () => void}} props
 */
export default function PhotoCropModal({ file, onApply, onCancel }) {
  const [imageUrl, setImageUrl] = useState(null);
  const [imageEl, setImageEl] = useState(null);
  const [crop, setCrop] = useState();
  const [completedCrop, setCompletedCrop] = useState();
  const [applying, setApplying] = useState(false);
  const modalRef = useRef(null);

  useLockBodyScroll(true);

  useEffect(() => {
    const url = URL.createObjectURL(file);
    setImageUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  useEffect(() => {
    function onKeyDown(event) {
      if (event.key === "Escape") {
        onCancel();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onCancel]);

  // Focus management: focus falls into the dialog on open, Tab/Shift-Tab
  // cycle within it, and closing hands focus back to whatever had it.
  useEffect(() => {
    const modal = modalRef.current;
    if (!modal) return undefined;

    const previousFocus =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    modal.focus();

    function trapTab(event) {
      if (event.key !== "Tab") return;
      const focusables = Array.from(
        modal.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        )
      ).filter((el) => !el.disabled);
      const first = focusables[0];
      const last = focusables[focusables.length - 1];

      if (!modal.contains(document.activeElement)) {
        // Focus escaped the dialog entirely: pull it back.
        event.preventDefault();
        (first || modal).focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        (first || modal).focus();
      } else if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        (last || modal).focus();
      }
    }

    document.addEventListener("keydown", trapTab);
    return () => {
      document.removeEventListener("keydown", trapTab);
      if (previousFocus?.isConnected) {
        previousFocus.focus();
      }
    };
  }, []);

  function onImageLoad(event) {
    const img = event.currentTarget;
    setImageEl(img);
    // ReactCrop measures crops in the rendered image's coordinate space.
    const centered = defaultSquareCrop(img.width, img.height);
    setCrop(centered);
    setCompletedCrop(centered);
  }

  async function handleApply() {
    setApplying(true);
    const activeCrop = completedCrop || crop;
    try {
      const cropped = await cropToSquareFile(imageEl, activeCrop);
      onApply(cropped);
    } catch {
      // Encoding can fail on exotic formats: fall back to the original
      // file so the user is never stuck in the dialog.
      onApply(file);
    }
  }

  // biome-ignore-start lint/a11y/noStaticElementInteractions lint/a11y/useKeyWithClickEvents: backdrop close/stopPropagation are redundant with the close button and Escape; dialog role carries semantics.
  return createPortal(
    <div className={styles.overlay} onClick={onCancel} role="presentation">
      <div
        ref={modalRef}
        className={styles.modal}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Crop photo"
        tabIndex={-1}
      >
        <button
          className={styles.closeBtn}
          onClick={onCancel}
          type="button"
          aria-label="Close"
        >
          ×
        </button>

        <h2 className={styles.title}>Crop Photo</h2>
        <p className={styles.hint}>
          Drag the square to frame your face. The photo will be saved as a
          square crop.
        </p>

        {imageUrl && (
          <div className={styles.cropArea}>
            <ReactCrop
              crop={crop}
              // react-image-crop v11 always reports the first argument in
              // px and the second in %, regardless of the crop prop's unit
              // (ReactCrop.tsx passes convertToPixelCrop/convertToPercent
              // Crop). Take the percent crop so the stored selection
              // survives resizes.
              onChange={(_pixelCrop, percentCrop) => setCrop(percentCrop)}
              onComplete={(_pixelCrop, percentCrop) =>
                setCompletedCrop(percentCrop)
              }
              aspect={1}
              locked={false}
              // In rendered px (library convention): keeps an accidental
              // tiny drag from producing a thumbnail-sized photo.<ext>.
              minWidth={64}
              minHeight={64}
            >
              <img
                src={imageUrl}
                alt="Crop preview"
                onLoad={onImageLoad}
                className={styles.image}
              />
            </ReactCrop>
          </div>
        )}

        <div className={styles.actions}>
          <button
            type="button"
            className={styles.saveBtn}
            onClick={handleApply}
            disabled={applying || !crop}
          >
            {applying ? "Saving..." : "Crop & Save"}
          </button>
          <button type="button" className={styles.cancelBtn} onClick={onCancel}>
            Keep Original
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
  // biome-ignore-end lint/a11y/noStaticElementInteractions lint/a11y/useKeyWithClickEvents: end of backdrop scope
}
