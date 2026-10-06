import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { fetchWithAuth } from "../../utils/api";
import EditProgramInfo from "./EditProgramInfo";

vi.mock("../../utils/api", () => ({
  fetchWithAuth: vi.fn(),
}));

describe("EditProgramInfo", () => {
  beforeEach(() => {
    fetchWithAuth.mockReset();
    fetchWithAuth.mockResolvedValue({
      ok: true,
      json: async () => ({ program_text: "## Existing\n\nBody." }),
    });
  });

  test("loads the program text and patches exactly program_text on save", async () => {
    render(<EditProgramInfo />);

    const textarea = await screen.findByDisplayValue(/## Existing/);
    fireEvent.change(textarea, {
      target: { name: "program_text", value: "## New content" },
    });
    fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => expect(fetchWithAuth).toHaveBeenCalledTimes(2));
    const [url, options] = fetchWithAuth.mock.calls[1];
    expect(url).toBe("/api/conference-info/edit/");
    expect(options.method).toBe("PATCH");
    expect(JSON.parse(options.body)).toEqual({
      program_text: "## New content",
    });

    expect(await screen.findByText(/saved successfully/i)).toBeInTheDocument();
  });
});
