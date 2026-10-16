import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { cropToSquareFile } from "../../utils/imageCrop";
import PhotoCropModal from "./PhotoCropModal";

vi.mock("../../utils/imageCrop", async () => ({
  ...(await vi.importActual("../../utils/imageCrop")),
  cropToSquareFile: vi.fn(),
}));

const originalFile = new File(["original-bytes"], "portrait.png", {
  type: "image/png",
});

describe("PhotoCropModal", () => {
  let onApply;
  let onCancel;

  beforeEach(() => {
    onApply = vi.fn();
    onCancel = vi.fn();
    cropToSquareFile.mockReset();

    // jsdom lacks URL.createObjectURL and ResizeObserver.
    URL.createObjectURL = vi.fn(() => "blob:crop-preview");
    URL.revokeObjectURL = vi.fn();
    window.ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    };
    window.scrollTo = vi.fn();
  });

  afterEach(() => {
    document.body.style.cssText = "";
    vi.restoreAllMocks();
  });

  function renderModal() {
    return render(
      <PhotoCropModal
        file={originalFile}
        onApply={onApply}
        onCancel={onCancel}
      />
    );
  }

  test("renders the preview image, the framing hint, and both actions", () => {
    renderModal();

    expect(URL.createObjectURL).toHaveBeenCalledWith(originalFile);
    const preview = screen.getByRole("img", { name: "Crop preview" });
    expect(preview).toHaveAttribute("src", "blob:crop-preview");
    expect(
      screen.getByText(/Drag the square to frame your face/)
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Crop & Save" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Keep Original" })
    ).toBeInTheDocument();
  });

  test("revokes the object URL on unmount", () => {
    const { unmount } = renderModal();

    unmount();

    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:crop-preview");
  });

  test("sets the initial square crop when the image loads", () => {
    renderModal();

    const applyButton = screen.getByRole("button", { name: "Crop & Save" });
    expect(applyButton).toBeDisabled();

    fireEvent.load(screen.getByRole("img", { name: "Crop preview" }));

    expect(applyButton).toBeEnabled();
  });

  test("Crop & Save encodes the crop and forwards the result", async () => {
    const croppedFile = new File(["cropped-bytes"], "photo.jpg", {
      type: "image/jpeg",
    });
    cropToSquareFile.mockResolvedValue(croppedFile);
    renderModal();

    fireEvent.load(screen.getByRole("img", { name: "Crop preview" }));
    fireEvent.click(screen.getByRole("button", { name: "Crop & Save" }));

    await waitFor(() => expect(onApply).toHaveBeenCalledTimes(1));
    // Files compare structurally-equal here; identity proves which file was applied.
    expect(onApply.mock.calls[0][0]).toBe(croppedFile);
    expect(cropToSquareFile).toHaveBeenCalledTimes(1);
    const [imageArg, cropArg] = cropToSquareFile.mock.calls[0];
    expect(imageArg).toBeInstanceOf(HTMLImageElement);
    expect(cropArg).toEqual(expect.objectContaining({ unit: "%" }));
    expect(onCancel).not.toHaveBeenCalled();
  });

  test("Crop & Save falls back to the original file when encoding fails", async () => {
    cropToSquareFile.mockRejectedValue(new Error("canvas exploded"));
    renderModal();

    fireEvent.load(screen.getByRole("img", { name: "Crop preview" }));
    fireEvent.click(screen.getByRole("button", { name: "Crop & Save" }));

    await waitFor(() => expect(onApply).toHaveBeenCalledTimes(1));
    expect(onApply.mock.calls[0][0]).toBe(originalFile);
    expect(cropToSquareFile).toHaveBeenCalledTimes(1);
    expect(onCancel).not.toHaveBeenCalled();
  });

  test("Keep Original cancels without touching the crop util", () => {
    renderModal();

    fireEvent.click(screen.getByRole("button", { name: "Keep Original" }));

    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(cropToSquareFile).not.toHaveBeenCalled();
    expect(onApply).not.toHaveBeenCalled();
  });

  test("Escape cancels the dialog", () => {
    renderModal();

    fireEvent.keyDown(window, { key: "Escape" });

    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  test("clicking the backdrop cancels, clicking the dialog does not", () => {
    renderModal();

    const dialog = screen.getByRole("dialog", { name: "Crop photo" });
    fireEvent.click(dialog);
    expect(onCancel).not.toHaveBeenCalled();

    fireEvent.click(dialog.parentElement);
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  test("the close button cancels", () => {
    renderModal();

    fireEvent.click(screen.getByRole("button", { name: "Close" }));

    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  // ReactCrop derives crops from its wrapper's bounding box; jsdom has no
  // layout, so give every element a deterministic box and drive the crop
  // through the drag handles' keyboard surface.
  function stubRenderedBox(width, height) {
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
      width,
      height,
      x: 0,
      y: 0,
      top: 0,
      left: 0,
      right: width,
      bottom: height,
      toJSON: () => ({}),
    });
  }

  function seHandle() {
    // The drag handles are ReactCrop's keyboard-accessible resize surface
    // (class names are the library's public CSS surface).
    return document.querySelector(".ReactCrop__drag-handle.ord-se");
  }

  test("keeps the crop in % units after the user adjusts it", async () => {
    stubRenderedBox(400, 300);
    cropToSquareFile.mockResolvedValue(
      new File(["cropped-bytes"], "photo.jpg", { type: "image/jpeg" })
    );
    renderModal();

    fireEvent.load(screen.getByRole("img", { name: "Crop preview" }));
    expect(seHandle()).not.toBeNull();
    fireEvent.keyDown(seHandle(), { key: "ArrowLeft" });
    fireEvent.click(screen.getByRole("button", { name: "Crop & Save" }));

    await waitFor(() => expect(onApply).toHaveBeenCalledTimes(1));
    const [, cropArg] = cropToSquareFile.mock.calls[0];
    expect(cropArg.unit).toBe("%");
    for (const key of ["x", "y", "width", "height"]) {
      expect(Number.isFinite(cropArg[key])).toBe(true);
    }
    expect(cropArg.width).toBeGreaterThan(0);
    expect(cropArg.height).toBeGreaterThan(0);
  });

  test("the minimum selection floor stops a near-zero resize", async () => {
    stubRenderedBox(400, 300);
    cropToSquareFile.mockResolvedValue(
      new File(["cropped-bytes"], "photo.jpg", { type: "image/jpeg" })
    );
    renderModal();

    fireEvent.load(screen.getByRole("img", { name: "Crop preview" }));
    // Shrink step by step far past the floor (1 px per plain arrow key);
    // the clamp must stop at minWidth/minHeight instead of degrading to
    // a zero-size photo.
    for (let i = 0; i < 400; i++) {
      fireEvent.keyDown(seHandle(), { key: "ArrowLeft" });
    }
    fireEvent.click(screen.getByRole("button", { name: "Crop & Save" }));

    await waitFor(() => expect(onApply).toHaveBeenCalledTimes(1));
    const [, cropArg] = cropToSquareFile.mock.calls[0];
    expect(cropArg.unit).toBe("%");
    expect(cropArg.width).toBeCloseTo((64 / 400) * 100, 5);
    expect(cropArg.height).toBeCloseTo((64 / 300) * 100, 5);
  });

  test("moves focus into the dialog on open and restores it on close", () => {
    const before = document.createElement("button");
    before.textContent = "Before the dialog";
    document.body.appendChild(before);
    before.focus();
    expect(document.activeElement).toBe(before);

    const { unmount } = renderModal();

    expect(document.activeElement).toBe(
      screen.getByRole("dialog", { name: "Crop photo" })
    );

    unmount();

    expect(document.activeElement).toBe(before);
    before.remove();
  });

  test("cycles Tab and Shift+Tab within the dialog", () => {
    renderModal();

    const dialog = screen.getByRole("dialog", { name: "Crop photo" });
    const closeBtn = screen.getByRole("button", { name: "Close" });
    const cancelBtn = screen.getByRole("button", { name: "Keep Original" });

    // Focus starts inside the dialog (the dialog itself is focused).
    fireEvent.keyDown(document, { key: "Tab" });
    expect(dialog.contains(document.activeElement)).toBe(true);

    cancelBtn.focus();
    fireEvent.keyDown(document, { key: "Tab" });
    expect(document.activeElement).toBe(closeBtn);

    closeBtn.focus();
    fireEvent.keyDown(document, { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(cancelBtn);
  });
});
