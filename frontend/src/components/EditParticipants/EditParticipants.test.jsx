import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { setTestLocation } from "../../testUtils/reactRouterDomStub";
import { fetchWithAuth } from "../../utils/api";
import { isProgramDirty } from "../../utils/programRefresh";
import EditParticipants from "./EditParticipants";

vi.mock("../../utils/api", async () => ({
  ...(await vi.importActual("../../utils/api")),
  fetchWithAuth: vi.fn(),
}));

const pendingSubmission = {
  id: 11,
  name: "Pending Person",
  email: "pending@example.com",
  affiliation: "CTU",
  abstract_title: "Wear Methods",
  abstract_text: "text",
  arrival_date: "2026-09-10",
  departure_date: "2026-09-12",
  submitted_at: "2026-09-01",
  stay_duration: 2,
  status: "pending",
};

const approvedSubmission = {
  ...pendingSubmission,
  id: 12,
  name: "Approved Person",
  status: "approved",
};

const rejectedSubmission = {
  ...pendingSubmission,
  id: 13,
  name: "Rejected Person",
  status: "rejected",
  rejection_message: "Please contact the organizers.",
};

function listResponse(items) {
  return { ok: true, json: async () => items };
}

describe("EditParticipants workflows", () => {
  beforeEach(() => {
    localStorage.clear();
    fetchWithAuth.mockReset();
    setTestLocation({ pathname: "/admin-panel/edit-participants", search: "" });
  });

  test("loads pending submissions and refetches when the filter changes", async () => {
    fetchWithAuth
      .mockResolvedValueOnce(listResponse([pendingSubmission]))
      .mockResolvedValueOnce(listResponse([]));

    render(<EditParticipants />);

    expect(await screen.findByText("Pending Person")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Delete" })
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Published" }));

    await waitFor(() => expect(fetchWithAuth).toHaveBeenCalledTimes(2));
    expect(fetchWithAuth.mock.calls[1][0]).toBe(
      "/api/admin/submissions/?status=approved"
    );
  });

  test("publish confirmation posts to publish/ and refetches the list", async () => {
    fetchWithAuth
      .mockResolvedValueOnce(listResponse([pendingSubmission]))
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce(listResponse([]));

    render(<EditParticipants />);
    fireEvent.click(await screen.findByRole("button", { name: "Publish" }));

    expect(await screen.findByText("Publish submission")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));

    expect(await screen.findByText("Success")).toBeInTheDocument();
    expect(
      fetchWithAuth.mock.calls.some(
        ([url, opts]) =>
          url === "/api/admin/submissions/11/publish/" && opts.method === "POST"
      )
    ).toBe(true);
    expect(fetchWithAuth).toHaveBeenCalledTimes(3);
  });

  test("rejects a pending submission with an optional participant message", async () => {
    fetchWithAuth
      .mockResolvedValueOnce(listResponse([pendingSubmission]))
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce(listResponse([]));

    render(<EditParticipants />);
    fireEvent.click(
      await screen.findByRole("button", { name: "Reject registration" })
    );

    expect(
      await screen.findByRole("heading", { name: "Reject registration" })
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/message for participant/i), {
      target: { value: "Please provide a longer abstract." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Reject" }));

    expect(
      await screen.findByText("Registration rejected")
    ).toBeInTheDocument();
    expect(
      fetchWithAuth.mock.calls.some(([url, opts]) => {
        if (url !== "/api/admin/submissions/11/reject/") return false;
        return (
          opts.method === "POST" &&
          JSON.parse(opts.body).message === "Please provide a longer abstract."
        );
      })
    ).toBe(true);
    expect(fetchWithAuth).toHaveBeenCalledTimes(3);
  });

  test("allows rejecting without a participant message", async () => {
    fetchWithAuth
      .mockResolvedValueOnce(listResponse([pendingSubmission]))
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce(listResponse([]));

    render(<EditParticipants />);
    fireEvent.click(
      await screen.findByRole("button", { name: "Reject registration" })
    );
    fireEvent.click(await screen.findByRole("button", { name: "Reject" }));

    expect(
      await screen.findByText("Registration rejected")
    ).toBeInTheDocument();
    expect(
      fetchWithAuth.mock.calls.some(
        ([url, opts]) =>
          url === "/api/admin/submissions/11/reject/" &&
          opts.method === "POST" &&
          JSON.parse(opts.body).message === ""
      )
    ).toBe(true);
  });

  test("shows rejected submissions in their own tab and restores one", async () => {
    fetchWithAuth
      .mockResolvedValueOnce(listResponse([]))
      .mockResolvedValueOnce(listResponse([rejectedSubmission]))
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce(listResponse([]));

    render(<EditParticipants />);
    fireEvent.click(await screen.findByRole("button", { name: "Rejected" }));

    expect(await screen.findByText("Rejected Person")).toBeInTheDocument();
    expect(
      screen.getByText("Please contact the organizers.")
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Edit" })
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Restore" }));
    expect(await screen.findByText("Restore submission")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));

    expect(await screen.findByText("Submission restored")).toBeInTheDocument();
    expect(
      fetchWithAuth.mock.calls.some(
        ([url, opts]) =>
          url === "/api/admin/submissions/13/restore/" && opts.method === "POST"
      )
    ).toBe(true);
    expect(fetchWithAuth.mock.calls[1][0]).toBe(
      "/api/admin/submissions/?status=rejected"
    );
  });

  test("unpublishing an approved submission keeps it and marks the program dirty", async () => {
    fetchWithAuth
      .mockResolvedValueOnce(listResponse([approvedSubmission]))
      .mockResolvedValueOnce({ ok: true, json: async () => ({}) })
      .mockResolvedValueOnce(listResponse([]));

    render(<EditParticipants />);
    fireEvent.click(await screen.findByRole("button", { name: "Unpublish" }));

    expect(
      await screen.findByText(/removes the published Participant/i)
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }));

    expect(
      await screen.findByText(/The submission is pending review/i)
    ).toBeInTheDocument();
    expect(
      fetchWithAuth.mock.calls.some(
        ([url, opts]) =>
          url === "/api/admin/submissions/12/unpublish/" &&
          opts.method === "POST"
      )
    ).toBe(true);
    expect(isProgramDirty()).toBe(true);
  });

  test("renders the participant reference and copies the tracking link", async () => {
    fetchWithAuth.mockResolvedValueOnce(
      listResponse([
        {
          ...pendingSubmission,
          tracking_token: "tok123",
          participant_reference: "wsc2026-0042",
        },
      ])
    );
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText },
      configurable: true,
    });

    render(<EditParticipants />);

    expect(await screen.findByText("wsc2026-0042")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Copy tracking link" }));

    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1));
    expect(writeText.mock.calls[0][0]).toMatch(/#\/track\/tok123$/);
    expect(
      await screen.findByRole("button", { name: "Link copied" })
    ).toBeInTheDocument();

    delete navigator.clipboard;
  });

  test("renders no copy button when the submission has no tracking token", async () => {
    fetchWithAuth.mockResolvedValueOnce(listResponse([pendingSubmission]));

    render(<EditParticipants />);

    await screen.findByText("Pending Person");
    expect(
      screen.queryByRole("button", { name: "Copy tracking link" })
    ).not.toBeInTheDocument();
  });

  test("a ?submission= link loads the All tab and scrolls to that card", async () => {
    setTestLocation({
      pathname: "/admin-panel/edit-participants",
      search: "?submission=12",
    });
    fetchWithAuth.mockResolvedValue(
      listResponse([pendingSubmission, approvedSubmission])
    );
    const scrollIntoView = vi.fn();
    Element.prototype.scrollIntoView = scrollIntoView;

    render(<EditParticipants />);

    await screen.findByText("Approved Person");

    // The link forces the All tab, not the pending default.
    expect(fetchWithAuth.mock.calls[0][0]).toBe(
      "/api/admin/submissions/?status="
    );
    expect(document.getElementById("submission-12")).not.toBeNull();
    await waitFor(() => expect(scrollIntoView).toHaveBeenCalledTimes(1));

    // Scroll only — the edit modal stays closed.
    expect(screen.queryByText("Edit Submission")).not.toBeInTheDocument();
  });
});
