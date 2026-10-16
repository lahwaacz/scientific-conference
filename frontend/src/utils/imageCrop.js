/**
 * Geometry + canvas encode helpers for the square photo crop shared by
 * every photo-upload path. Kept DOM-free at module scope so the geometry
 * half is pure and the encode half takes its <img> element as an argument.
 */

const FILE_EXTENSIONS = {
  "image/jpeg": "jpg",
  "image/png": "png",
  "image/webp": "webp",
};

/**
 * Largest centered square over an image, as a ReactCrop crop in percent
 * units, so the selection survives layout resizes (react-image-crop
 * resolves % crops against the media's own dimensions). Callers pass the
 * element's displayed width/height; only their ratio matters.
 *
 * @param {number} width rendered image width in px
 * @param {number} height rendered image height in px
 * @returns {{unit: "%", x: number, y: number, width: number, height: number}}
 */
export function defaultSquareCrop(width, height) {
  // A zero-layout image (jsdom, or defensively display:none) would divide
  // by zero and poison the crop with NaN; treat "no geometry" as the
  // whole image.
  if (!(width > 0) || !(height > 0)) {
    return { unit: "%", x: 0, y: 0, width: 100, height: 100 };
  }

  const side = Math.min(width, height);
  return {
    unit: "%",
    x: ((width - side) / 2 / width) * 100,
    y: ((height - side) / 2 / height) * 100,
    width: (side / width) * 100,
    height: (side / height) * 100,
  };
}

/**
 * Render the selected crop of an already-loaded <img> into a square-ish
 * JPEG/PNG/WebP File. Rejects on any failure — the caller falls back to
 * the original file. The File is named photo.<ext>, the extension
 * following mimeType (default photo.jpg); unrecognised types fall back
 * to jpg.
 *
 * @param {HTMLImageElement} imageEl loaded image element (browsers apply
 *   EXIF orientation when drawing from the element)
 * @param {{unit: "px"|"%", x: number, y: number, width: number, height: number}} crop
 *   crop in the image's rendered coordinate space (or % of it)
 * @param {{maxSize?: number, quality?: number, mimeType?: string}} options
 * @returns {Promise<File>}
 */
export function cropToSquareFile(
  imageEl,
  crop,
  { maxSize = 1024, quality = 0.9, mimeType = "image/jpeg" } = {}
) {
  return new Promise((resolve, reject) => {
    if (!imageEl?.naturalWidth || !imageEl?.naturalHeight) {
      reject(new Error("Image is not loaded."));
      return;
    }
    if (!crop || !(crop.width > 0) || !(crop.height > 0)) {
      reject(new Error("Crop selection is empty."));
      return;
    }

    // Convert the crop into natural pixels. A "px" crop is in rendered
    // pixels, so scale by natural/rendered; a "%" crop is a fraction.
    const renderedWidth = imageEl.width || imageEl.naturalWidth;
    const renderedHeight = imageEl.height || imageEl.naturalHeight;
    let srcX;
    let srcY;
    let srcW;
    let srcH;
    if (crop.unit === "%") {
      srcX = (crop.x / 100) * imageEl.naturalWidth;
      srcY = (crop.y / 100) * imageEl.naturalHeight;
      srcW = (crop.width / 100) * imageEl.naturalWidth;
      srcH = (crop.height / 100) * imageEl.naturalHeight;
    } else {
      const scaleX = imageEl.naturalWidth / renderedWidth;
      const scaleY = imageEl.naturalHeight / renderedHeight;
      srcX = crop.x * scaleX;
      srcY = crop.y * scaleY;
      srcW = crop.width * scaleX;
      srcH = crop.height * scaleY;
    }

    // Rounding can push the rect a pixel outside the image; clamp it.
    srcX = Math.min(Math.max(srcX, 0), imageEl.naturalWidth);
    srcY = Math.min(Math.max(srcY, 0), imageEl.naturalHeight);
    srcW = Math.min(srcW, imageEl.naturalWidth - srcX);
    srcH = Math.min(srcH, imageEl.naturalHeight - srcY);
    if (!(srcW > 0) || !(srcH > 0)) {
      reject(new Error("Crop selection is outside the image."));
      return;
    }

    // Never upscale: shrink only when the crop exceeds maxSize.
    const scale = Math.min(1, maxSize / srcW, maxSize / srcH);
    const outW = Math.max(1, Math.round(srcW * scale));
    const outH = Math.max(1, Math.round(srcH * scale));

    const canvas = document.createElement("canvas");
    canvas.width = outW;
    canvas.height = outH;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      reject(new Error("Canvas 2D context is unavailable."));
      return;
    }
    // JPEG has no alpha: fill white first so transparent PNGs do not
    // come out black.
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, outW, outH);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(imageEl, srcX, srcY, srcW, srcH, 0, 0, outW, outH);

    canvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error("Failed to encode the cropped image."));
          return;
        }
        const ext = FILE_EXTENSIONS[mimeType] || "jpg";
        resolve(new File([blob], `photo.${ext}`, { type: mimeType }));
      },
      mimeType,
      quality
    );
  });
}
