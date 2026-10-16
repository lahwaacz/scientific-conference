import { cropToSquareFile, defaultSquareCrop } from "./imageCrop";

// jsdom has no real canvas: getContext returns null and toBlob is not
// implemented. These stubs capture the drawing calls instead.
function stubCanvas() {
  const ctx = {
    fillStyle: null,
    imageSmoothingEnabled: false,
    imageSmoothingQuality: null,
    fillRect: vi.fn(),
    drawImage: vi.fn(),
  };

  let lastCanvas = null;
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(
    function getContext() {
      lastCanvas = this;
      return ctx;
    }
  );

  const toBlob = vi
    .spyOn(HTMLCanvasElement.prototype, "toBlob")
    .mockImplementation((callback, mimeType) => {
      callback(new Blob(["encoded"], { type: mimeType }));
    });

  return { ctx, toBlob, getLastCanvas: () => lastCanvas };
}

function makeImage({ naturalWidth, naturalHeight, width, height }) {
  const img = document.createElement("img");
  Object.defineProperties(img, {
    naturalWidth: { value: naturalWidth },
    naturalHeight: { value: naturalHeight },
    width: { value: width },
    height: { value: height },
  });
  return img;
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("defaultSquareCrop", () => {
  test("centers the largest square on a landscape image", () => {
    const crop = defaultSquareCrop(600, 400);
    expect(crop.unit).toBe("%");
    expect(crop.x).toBeCloseTo(100 / 6);
    expect(crop.y).toBe(0);
    expect(crop.width).toBeCloseTo(200 / 3);
    expect(crop.height).toBe(100);
  });

  test("centers the largest square on a portrait image", () => {
    const crop = defaultSquareCrop(400, 600);
    expect(crop.unit).toBe("%");
    expect(crop.x).toBe(0);
    expect(crop.y).toBeCloseTo(100 / 6);
    expect(crop.width).toBe(100);
    expect(crop.height).toBeCloseTo(200 / 3);
  });

  test("returns the whole image when it is already square", () => {
    expect(defaultSquareCrop(500, 500)).toEqual({
      unit: "%",
      x: 0,
      y: 0,
      width: 100,
      height: 100,
    });
  });

  test("falls back to the whole image for non-positive dimensions", () => {
    // A zero-layout image (jsdom, display:none) must not produce NaN.
    const whole = { unit: "%", x: 0, y: 0, width: 100, height: 100 };
    expect(defaultSquareCrop(0, 0)).toEqual(whole);
    expect(defaultSquareCrop(0, 400)).toEqual(whole);
    expect(defaultSquareCrop(400, 0)).toEqual(whole);
    expect(defaultSquareCrop(-600, -400)).toEqual(whole);
  });
});

describe("cropToSquareFile", () => {
  test("maps a px crop to natural pixels and encodes a File", async () => {
    const { ctx, toBlob, getLastCanvas } = stubCanvas();
    // Rendered at half resolution: the px crop must be doubled.
    const img = makeImage({
      naturalWidth: 2000,
      naturalHeight: 1000,
      width: 1000,
      height: 500,
    });
    const crop = { unit: "px", x: 500, y: 0, width: 500, height: 500 };

    const file = await cropToSquareFile(img, crop);

    // The canvas is capped by maxSize against the cropped natural size
    // (1000 px here, so no downscale) and the source rect is in natural px.
    expect(getLastCanvas().width).toBe(1000);
    expect(getLastCanvas().height).toBe(1000);
    expect(ctx.drawImage).toHaveBeenCalledWith(
      img,
      1000,
      0,
      1000,
      1000,
      0,
      0,
      1000,
      1000
    );
    expect(toBlob).toHaveBeenCalledWith(
      expect.any(Function),
      "image/jpeg",
      0.9
    );
    expect(file).toBeInstanceOf(File);
    expect(file.name).toBe("photo.jpg");
    expect(file.type).toBe("image/jpeg");
  });

  test("fills the canvas white before drawing so PNGs do not turn black", async () => {
    const { ctx } = stubCanvas();
    const img = makeImage({
      naturalWidth: 800,
      naturalHeight: 800,
      width: 400,
      height: 400,
    });

    await cropToSquareFile(img, {
      unit: "px",
      x: 0,
      y: 0,
      width: 400,
      height: 400,
    });

    expect(ctx.fillStyle).toBe("#ffffff");
    expect(ctx.fillRect).toHaveBeenCalledWith(0, 0, 800, 800);
    const fillOrder = ctx.fillRect.mock.invocationCallOrder[0];
    const drawOrder = ctx.drawImage.mock.invocationCallOrder[0];
    expect(fillOrder).toBeLessThan(drawOrder);
  });

  test("downscales crops larger than maxSize", async () => {
    const { getLastCanvas } = stubCanvas();
    const img = makeImage({
      naturalWidth: 4000,
      naturalHeight: 4000,
      width: 1000,
      height: 1000,
    });

    await cropToSquareFile(img, {
      unit: "px",
      x: 0,
      y: 0,
      width: 1000,
      height: 1000,
    });

    expect(getLastCanvas().width).toBe(1024);
    expect(getLastCanvas().height).toBe(1024);
  });

  test("never upscales a crop smaller than maxSize", async () => {
    const { getLastCanvas } = stubCanvas();
    const img = makeImage({
      naturalWidth: 400,
      naturalHeight: 400,
      width: 100,
      height: 100,
    });

    await cropToSquareFile(img, {
      unit: "px",
      x: 0,
      y: 0,
      width: 100,
      height: 100,
    });

    expect(getLastCanvas().width).toBe(400);
    expect(getLastCanvas().height).toBe(400);
  });

  test("honors custom maxSize, quality, and mimeType", async () => {
    const { toBlob, getLastCanvas } = stubCanvas();
    const img = makeImage({
      naturalWidth: 2000,
      naturalHeight: 2000,
      width: 1000,
      height: 1000,
    });

    const file = await cropToSquareFile(
      img,
      { unit: "px", x: 0, y: 0, width: 1000, height: 1000 },
      { maxSize: 512, quality: 0.8, mimeType: "image/png" }
    );

    expect(getLastCanvas().width).toBe(512);
    expect(getLastCanvas().height).toBe(512);
    expect(toBlob).toHaveBeenCalledWith(expect.any(Function), "image/png", 0.8);
    expect(file.type).toBe("image/png");
  });

  test("names the File photo.jpg by default", async () => {
    stubCanvas();
    const img = makeImage({
      naturalWidth: 800,
      naturalHeight: 800,
      width: 800,
      height: 800,
    });

    const file = await cropToSquareFile(img, {
      unit: "px",
      x: 0,
      y: 0,
      width: 800,
      height: 800,
    });

    expect(file.name).toBe("photo.jpg");
  });

  test("derives the File extension from mimeType", async () => {
    stubCanvas();
    const img = makeImage({
      naturalWidth: 800,
      naturalHeight: 800,
      width: 800,
      height: 800,
    });
    const crop = { unit: "px", x: 0, y: 0, width: 800, height: 800 };

    const png = await cropToSquareFile(img, crop, { mimeType: "image/png" });
    const webp = await cropToSquareFile(img, crop, { mimeType: "image/webp" });
    const odd = await cropToSquareFile(img, crop, { mimeType: "image/avif" });

    expect(png.name).toBe("photo.png");
    expect(png.type).toBe("image/png");
    expect(webp.name).toBe("photo.webp");
    expect(odd.name).toBe("photo.jpg");
    expect(odd.type).toBe("image/avif");
  });

  test("supports %-unit crops", async () => {
    const { ctx } = stubCanvas();
    const img = makeImage({
      naturalWidth: 2000,
      naturalHeight: 1000,
      width: 1000,
      height: 500,
    });

    await cropToSquareFile(img, {
      unit: "%",
      x: 25,
      y: 0,
      width: 50,
      height: 100,
    });

    expect(ctx.drawImage).toHaveBeenCalledWith(
      img,
      500,
      0,
      1000,
      1000,
      0,
      0,
      1000,
      1000
    );
  });

  test("clamps a crop that overflows the natural bounds", async () => {
    const { ctx } = stubCanvas();
    const img = makeImage({
      naturalWidth: 1000,
      naturalHeight: 500,
      width: 1000,
      height: 500,
    });

    await cropToSquareFile(img, {
      unit: "px",
      x: 900,
      y: 0,
      width: 200,
      height: 200,
    });

    expect(ctx.drawImage).toHaveBeenCalledWith(
      img,
      900,
      0,
      100,
      200,
      0,
      0,
      100,
      200
    );
  });

  test("rejects when the image is not loaded", async () => {
    stubCanvas();
    const img = makeImage({
      naturalWidth: 0,
      naturalHeight: 0,
      width: 100,
      height: 100,
    });

    await expect(
      cropToSquareFile(img, { unit: "px", x: 0, y: 0, width: 50, height: 50 })
    ).rejects.toThrow(/not loaded/);
  });

  test("rejects on an empty crop", async () => {
    stubCanvas();
    const img = makeImage({
      naturalWidth: 1000,
      naturalHeight: 1000,
      width: 500,
      height: 500,
    });

    await expect(
      cropToSquareFile(img, { unit: "px", x: 0, y: 0, width: 0, height: 0 })
    ).rejects.toThrow(/empty/);
  });

  test("rejects when encoding produces no blob", async () => {
    const { toBlob } = stubCanvas();
    toBlob.mockImplementation((callback) => {
      callback(null);
    });
    const img = makeImage({
      naturalWidth: 100,
      naturalHeight: 100,
      width: 100,
      height: 100,
    });

    await expect(
      cropToSquareFile(img, { unit: "px", x: 0, y: 0, width: 50, height: 50 })
    ).rejects.toThrow(/encode/);
  });

  test("rejects when the 2D context is unavailable", async () => {
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
    const img = makeImage({
      naturalWidth: 100,
      naturalHeight: 100,
      width: 100,
      height: 100,
    });

    await expect(
      cropToSquareFile(img, { unit: "px", x: 0, y: 0, width: 50, height: 50 })
    ).rejects.toThrow(/2D context/);
  });
});
