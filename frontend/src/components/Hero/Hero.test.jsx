import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Hero from "./Hero";

const INFO = {
  title: "Workshop on Scientific Computing",
  year: 2027,
  description: "An annual colloquium.",
  date_start: "2027-05-25",
  date_end: "2027-05-27",
  location: "Prague",
};

const INFO_WITH_PHOTO = {
  ...INFO,
  hero_photo: "/media/conferences/wsc2026-hero.jpg",
};

describe("Hero", () => {
  beforeEach(() => {
    document.title = "";
  });

  it("renders no text while the conference info has not arrived", () => {
    globalThis.fetch = vi.fn(() => new Promise(() => {}));
    render(<Hero />);

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("");
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("");
    expect(screen.queryByText(/workshop on scientific computing/i)).toBeNull();
    expect(screen.queryByText(/organized by the faculty/i)).toBeNull();
  });

  it("renders the conference title and description once the info arrives", async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({ ok: true, json: async () => INFO })
    );
    render(<Hero />);

    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent(
      "Workshop on Scientific Computing 2027"
    );
    expect(screen.getByText("An annual colloquium.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent(
      "25 May 2027 - 27 May 2027. Prague."
    );
  });

  it("renders the hero photo with the media URL once the info arrives", async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({ ok: true, json: async () => INFO_WITH_PHOTO })
    );
    render(<Hero />);

    await screen.findByRole("heading", { level: 1 });
    const img = screen.getByRole("img", {
      name: "Workshop on Scientific Computing 2027",
    });
    expect(img).toHaveAttribute(
      "src",
      "http://localhost:8000/media/conferences/wsc2026-hero.jpg"
    );
  });

  it("renders no hero photo when the info has none", async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({ ok: true, json: async () => INFO })
    );
    render(<Hero />);

    await screen.findByRole("heading", { level: 1 });
    expect(screen.queryByRole("img")).toBeNull();
  });

  it("syncs the browser tab title with the loaded conference", async () => {
    globalThis.fetch = vi.fn(() =>
      Promise.resolve({ ok: true, json: async () => INFO })
    );
    render(<Hero />);

    await waitFor(() =>
      expect(document.title).toBe("Workshop on Scientific Computing 2027")
    );
  });
});
