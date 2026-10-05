import { render, screen } from "@testing-library/react";
import { fetchWithAuth } from "../../utils/api";
import ParticipantsInfo from "./ParticipantsInfo";

vi.mock("../../utils/api", async () => ({
  ...(await vi.importActual("../../utils/api")),
  fetchWithAuth: vi.fn(),
}));

const submission = {
  id: 11,
  name: "Jana Novotná",
  email: "jana.novotna@example.org",
  is_student: false,
  abstract_title: "Finite volume schemes",
  arrival_date: "2025-05-29",
  departure_date: "2025-05-30",
  info: "",
};

function listResponse(items) {
  return { ok: true, json: async () => items };
}

describe("ParticipantsInfo", () => {
  beforeEach(() => {
    fetchWithAuth.mockReset();
  });

  test("links each participant name to their card on Edit Participants", async () => {
    fetchWithAuth.mockResolvedValue(listResponse([submission]));

    render(<ParticipantsInfo />);

    const link = await screen.findByRole("link", { name: "Jana Novotná" });
    expect(link.getAttribute("href")).toBe(
      "/admin-panel/edit-participants?submission=11"
    );
  });

  test("renders the participant summary and stay period", async () => {
    fetchWithAuth.mockResolvedValue(listResponse([submission]));

    render(<ParticipantsInfo />);

    expect(
      await screen.findByText(
        (_, el) =>
          el?.tagName === "P" &&
          el.textContent === "Participants: 1, with abstract: 1"
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        (_, el) => el?.tagName === "TD" && el.textContent === "May 29 – May 30"
      )
    ).toBeInTheDocument();
  });
});
