import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { fetchWithAuth } from "../../utils/api";
import EditSubmissionModal from "./EditSubmissionModal";

vi.mock("../../utils/api", async () => ({
  ...(await vi.importActual("../../utils/api")),
  fetchWithAuth: vi.fn(),
}));

const submission = {
  id: 7,
  name: "Jane Doe",
  email: "jane@example.com",
  affiliation: "CTU",
  abstract_title: "Numerical Methods",
  abstract_text: "Some abstract text",
  arrival_date: "2026-09-10",
  departure_date: "2026-09-12",
  status: "pending",
};

describe("EditSubmissionModal save paths", () => {
  let onClose;
  let onSave;

  beforeEach(() => {
    localStorage.clear();
    onClose = vi.fn();
    onSave = vi.fn();
    fetchWithAuth.mockReset();
  });

  function renderModal() {
    return render(
      <EditSubmissionModal
        submission={submission}
        onClose={onClose}
        onSave={onSave}
      />
    );
  }

  test("without a new photo sends PATCH with a JSON body", async () => {
    fetchWithAuth.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ...submission, name: "Jane Doe" }),
    });
    renderModal();

    fireEvent.submit(document.querySelector("form"));

    await waitFor(() => expect(fetchWithAuth).toHaveBeenCalledTimes(1));
    const [url, opts] = fetchWithAuth.mock.calls[0];
    expect(url).toBe("/api/admin/submissions/7/");
    expect(opts.method).toBe("PATCH");
    expect(JSON.parse(opts.body).name).toBe("Jane Doe");
  });

  test("with a new photo sends PUT with a FormData body", async () => {
    fetchWithAuth.mockResolvedValueOnce({
      ok: true,
      json: async () => submission,
    });
    renderModal();

    const file = new File(["fake"], "participant.png", {
      type: "image/png",
    });
    fireEvent.change(document.querySelector('input[type="file"]'), {
      target: { files: [file] },
    });
    fireEvent.submit(document.querySelector("form"));

    await waitFor(() => expect(fetchWithAuth).toHaveBeenCalledTimes(1));
    const [, opts] = fetchWithAuth.mock.calls[0];
    expect(opts.method).toBe("PUT");
    expect(opts.body).toBeInstanceOf(FormData);
    expect(opts.body.get("photo")).toBe(file);
    expect(opts.body.get("name")).toBe("Jane Doe");
  });

  test("a failed save shows the error modal and never calls onSave", async () => {
    fetchWithAuth.mockResolvedValueOnce({
      ok: false,
      status: 400,
      text: async () => "Validation failed",
    });
    renderModal();

    fireEvent.submit(document.querySelector("form"));

    expect(await screen.findByText("Save failed")).toBeInTheDocument();
    expect(onSave).not.toHaveBeenCalled();
  });

  test("a successful save surfaces onSave through the success modal", async () => {
    const updated = { ...submission, name: "Jane Changed" };
    fetchWithAuth.mockResolvedValueOnce({
      ok: true,
      json: async () => updated,
    });
    renderModal();

    fireEvent.submit(document.querySelector("form"));

    const confirmBtn = await screen.findByRole("button", {
      name: /confirm/i,
    });
    fireEvent.click(confirmBtn);
    expect(onSave).toHaveBeenCalledWith(updated);
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
