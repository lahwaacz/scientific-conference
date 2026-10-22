import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { setTestParams } from "react-router-dom";
import { initConferenceSlug } from "../../utils/conferenceSlug";
import { cropToSquareFile } from "../../utils/imageCrop";
import Tracking from "./Tracking";

const { openWindowInfo, holder } = vi.hoisted(() => ({
  openWindowInfo: {
    registration_opening: null,
    registration_deadline: "2099-12-31",
    date_end: null,
    submission_edit_deadline: null,
  },
  holder: { info: null },
}));

vi.mock("../hooks/useConferenceInfo", () => ({
  useConferenceInfo: () => holder.info,
}));

vi.mock("../../utils/imageCrop", async () => ({
  ...(await vi.importActual("../../utils/imageCrop")),
  cropToSquareFile: vi.fn(),
}));

const trackUrl = "http://localhost:8000/api/wsc2026/track/tok123/";

const pendingSubmission = {
  participant_reference: "wsc2026-0042",
  name: "Alice Smith",
  email: "alice@example.com",
  affiliation: "CTU Prague",
  contribution_type: "talk",
  photo: "/media/photos/alice.jpg",
  abstract_title: "Quantum Widgets",
  abstract_text: "We study widgets.",
  additional_authors: "Bob Jones",
  additional_affiliations: "MIT",
  arrival_date: "2026-09-10",
  departure_date: "2026-09-12",
  status: "pending",
  submitted_at: "2026-01-15T10:30:00Z",
  reviewed_at: null,
  info: "Vegetarian",
  is_student: true,
};

const jsonResponse = (status, body) => ({
  ok: status >= 200 && status < 300,
  status,
  json: async () => body,
});

function setLocation(pathname) {
  Object.defineProperty(window, "location", {
    configurable: true,
    writable: true,
    value: { pathname },
  });
}

async function renderWithSubmission(submission, info = openWindowInfo) {
  globalThis.fetch.mockResolvedValueOnce(jsonResponse(200, submission));
  holder.info = info;
  render(<Tracking />);
  await screen.findByText(submission.participant_reference);
}

async function openEditForm() {
  fireEvent.click(
    await screen.findByRole("button", { name: /edit submission/i })
  );
  await screen.findByPlaceholderText(/your.email@example.com/i);
}

describe("Tracking", () => {
  beforeEach(() => {
    setLocation("/wsc2026/");
    initConferenceSlug();
    globalThis.fetch = vi.fn();
    setTestParams({ trackingToken: "tok123" });
    holder.info = openWindowInfo;
    cropToSquareFile.mockReset();
    // jsdom lacks URL.createObjectURL and ResizeObserver; the crop dialog
    // needs both.
    URL.createObjectURL = vi.fn(() => "blob:crop-preview");
    URL.revokeObjectURL = vi.fn();
    window.ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    };
  });

  afterEach(() => {
    vi.clearAllMocks();
    setTestParams({});
    document.body.style.cssText = "";
  });

  test("renders a pending submission with its fields and status badge", async () => {
    await renderWithSubmission(pendingSubmission);

    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    expect(globalThis.fetch).toHaveBeenCalledWith(trackUrl);
    expect(screen.getByText("wsc2026-0042")).toBeInTheDocument();
    expect(screen.getByText("Pending review")).toBeInTheDocument();
    expect(screen.getByText("Alice Smith")).toBeInTheDocument();
    expect(screen.getByText("alice@example.com")).toBeInTheDocument();
    expect(screen.getByText("CTU Prague")).toBeInTheDocument();
    expect(screen.getByText("Quantum Widgets")).toBeInTheDocument();
    expect(screen.getByText("We study widgets.")).toBeInTheDocument();
    expect(screen.getByText("Bob Jones")).toBeInTheDocument();
    expect(screen.getByText("MIT")).toBeInTheDocument();
    expect(screen.getByText("Vegetarian")).toBeInTheDocument();
    expect(screen.getByText("Student")).toBeInTheDocument();
    expect(screen.getByText("Yes")).toBeInTheDocument();
    expect(screen.getByText(/Submitted:/i)).toBeInTheDocument();
    expect(screen.getByText(/10 September 2026/)).toBeInTheDocument();
    expect(screen.getByText(/12 September 2026/)).toBeInTheDocument();
    expect(
      document.querySelector('img[src^="http://localhost:8000/media/"]')
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /edit submission/i })
    ).toBeInTheDocument();
  });

  test("renders an approved submission as Published with the re-review notice in edit mode", async () => {
    await renderWithSubmission({
      ...pendingSubmission,
      status: "approved",
      reviewed_at: "2026-02-01T09:00:00Z",
    });

    expect(screen.getByText("Published")).toBeInTheDocument();
    expect(screen.queryByText("Pending review")).not.toBeInTheDocument();
    expect(screen.getByText(/Reviewed:/i)).toBeInTheDocument();

    await openEditForm();

    expect(
      screen.getByText(/Saving changes sends your submission back for review/i)
    ).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/your.email@example.com/i)).toHaveValue(
      "alice@example.com"
    );
    expect(document.querySelector('input[name="arrival"]')).toHaveValue(
      "2026-09-10"
    );
    expect(document.querySelector('input[name="departure"]')).toHaveValue(
      "2026-09-12"
    );
    expect(document.querySelector('input[name="is_student"]')).toBeChecked();
  });

  test("renders a rejected submission with its message and no edit control", async () => {
    await renderWithSubmission({
      ...pendingSubmission,
      status: "rejected",
      reviewed_at: "2026-02-01T09:00:00Z",
      rejection_message: "Please contact the organizers for details.",
    });

    expect(screen.getByText("Rejected")).toBeInTheDocument();
    expect(
      screen.getByText("Please contact the organizers for details.")
    ).toBeInTheDocument();
    expect(
      screen.getByText(/can no longer be edited online/i)
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /edit submission/i })
    ).not.toBeInTheDocument();
  });

  test("edit submit with a new photo PATCHes multipart FormData with all field keys", async () => {
    // Without an existing photo the field renders the upload input (with
    // one, it renders the preview + Remove instead).
    await renderWithSubmission({ ...pendingSubmission, photo: null });
    await openEditForm();

    const fileInput = document.querySelector('input[type="file"]');
    const newPhoto = new File([new ArrayBuffer(128)], "new.jpg", {
      type: "image/jpeg",
    });
    fireEvent.change(fileInput, { target: { files: [newPhoto] } });

    globalThis.fetch
      .mockResolvedValueOnce(jsonResponse(200, pendingSubmission))
      .mockResolvedValueOnce(jsonResponse(200, pendingSubmission));

    fireEvent.submit(document.querySelector("form"));

    expect(await screen.findByText(/Changes saved/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledTimes(3);
    });
    const [patchUrl, patchOptions] = globalThis.fetch.mock.calls[1];
    expect(patchUrl).toBe(trackUrl);
    expect(patchOptions.method).toBe("PATCH");
    const body = patchOptions.body;
    expect(body).toBeInstanceOf(FormData);
    expect([...body.keys()]).toEqual([
      "name",
      "email",
      "affiliation",
      "contribution_type",
      "abstract_title",
      "abstract_text",
      "additional_authors",
      "additional_affiliations",
      "arrival_date",
      "departure_date",
      "info",
      "is_student",
      "photo",
    ]);
    expect(body.get("name")).toBe("Alice Smith");
    expect(body.get("arrival_date")).toBe("2026-09-10");
    expect(body.get("departure_date")).toBe("2026-09-12");
    expect(body.get("is_student")).toBe("true");
    expect(body.get("photo")).toBe(newPhoto);

    // Refetch after save pulls the fresh submission (GET, no options).
    expect(globalThis.fetch).toHaveBeenNthCalledWith(3, trackUrl);
  });

  test("edit submit with an untouched photo sends a JSON PATCH without the photo key", async () => {
    await renderWithSubmission(pendingSubmission);
    await openEditForm();

    globalThis.fetch
      .mockResolvedValueOnce(jsonResponse(200, pendingSubmission))
      .mockResolvedValueOnce(jsonResponse(200, pendingSubmission));

    fireEvent.submit(document.querySelector("form"));

    expect(await screen.findByText(/Changes saved/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledTimes(3);
    });
    const [patchUrl, patchOptions] = globalThis.fetch.mock.calls[1];
    expect(patchUrl).toBe(trackUrl);
    expect(patchOptions.method).toBe("PATCH");
    expect(patchOptions.headers["Content-Type"]).toBe("application/json");
    const payload = JSON.parse(patchOptions.body);
    expect(Object.keys(payload).sort()).toEqual([
      "abstract_text",
      "abstract_title",
      "additional_affiliations",
      "additional_authors",
      "affiliation",
      "arrival_date",
      "contribution_type",
      "departure_date",
      "email",
      "info",
      "is_student",
      "name",
    ]);
    expect(payload.is_student).toBe(true);
  });

  test("Just attend edit clears hidden contribution fields", async () => {
    await renderWithSubmission(pendingSubmission);
    await openEditForm();

    fireEvent.click(screen.getByRole("radio", { name: "Just attend" }));

    globalThis.fetch
      .mockResolvedValueOnce(jsonResponse(200, pendingSubmission))
      .mockResolvedValueOnce(jsonResponse(200, pendingSubmission));

    fireEvent.submit(document.querySelector("form"));

    expect(await screen.findByText(/Changes saved/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledTimes(3);
    });
    const payload = JSON.parse(globalThis.fetch.mock.calls[1][1].body);
    expect(payload.contribution_type).toBe("attend");
    expect(payload.abstract_title).toBe("");
    expect(payload.abstract_text).toBe("");
    expect(payload.additional_authors).toBe("");
    expect(payload.additional_affiliations).toBe("");
  });

  test("Remove on an existing photo sends an explicit-null JSON PATCH", async () => {
    await renderWithSubmission(pendingSubmission);
    await openEditForm();

    const removed = { ...pendingSubmission, photo: null };
    globalThis.fetch
      .mockResolvedValueOnce(jsonResponse(200, removed))
      .mockResolvedValueOnce(jsonResponse(200, removed));

    fireEvent.click(screen.getByRole("button", { name: /^remove$/i }));

    expect(await screen.findByText(/Photo removed/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledTimes(3);
    });
    const [patchUrl, patchOptions] = globalThis.fetch.mock.calls[1];
    expect(patchUrl).toBe(trackUrl);
    expect(patchOptions.method).toBe("PATCH");
    expect(patchOptions.headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(patchOptions.body)).toEqual({ photo: null });
  });

  test("renders 400 field errors from the server on the affected field", async () => {
    await renderWithSubmission(pendingSubmission);
    await openEditForm();

    globalThis.fetch.mockResolvedValueOnce(
      jsonResponse(400, { email: ["This email is already registered."] })
    );

    fireEvent.submit(document.querySelector("form"));

    expect(
      await screen.findByText(/This email is already registered/i)
    ).toBeInTheDocument();
    // Still editing: the form stays open with the values intact.
    expect(screen.getByPlaceholderText(/your.email@example.com/i)).toHaveValue(
      "alice@example.com"
    );
    expect(screen.queryByText(/Changes saved/i)).not.toBeInTheDocument();
  });

  test("404 renders the not-found panel with a link back to registration", async () => {
    globalThis.fetch.mockResolvedValueOnce(jsonResponse(404, {}));

    render(<Tracking />);

    expect(
      await screen.findByText(
        /Submission not found\. Check your tracking link or contact the organizers\./i
      )
    ).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /back to registration/i });
    expect(link).toHaveAttribute("href", "#/registration");
    expect(screen.queryByText("wsc2026-0042")).not.toBeInTheDocument();
  });

  test("closed registration window keeps the edit button while editing stays open", async () => {
    await renderWithSubmission(pendingSubmission, {
      registration_opening: null,
      registration_deadline: "2020-01-01",
      date_end: null,
      submission_edit_deadline: "2099-12-31",
    });

    expect(screen.getByText("wsc2026-0042")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /edit submission/i })
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/can no longer be edited online/i)
    ).not.toBeInTheDocument();
  });

  test("a past submission edit deadline hides the edit button and shows the locked notice", async () => {
    await renderWithSubmission(pendingSubmission, {
      registration_opening: null,
      registration_deadline: "2020-01-01",
      date_end: null,
      submission_edit_deadline: "2020-06-30",
    });

    expect(screen.getByText("wsc2026-0042")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Editing submissions closed on 30 June 2020 — your submission can no longer be edited online. Contact the organizers for changes."
      )
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /edit submission/i })
    ).not.toBeInTheDocument();
  });

  test("the conference end date locks editing even with no deadline or start date", async () => {
    await renderWithSubmission(pendingSubmission, {
      registration_opening: null,
      registration_deadline: null,
      date_start: null,
      date_end: "2020-06-30",
      submission_edit_deadline: null,
    });

    expect(screen.getByText("wsc2026-0042")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Editing submissions closed on 30 June 2020 — your submission can no longer be edited online. Contact the organizers for changes."
      )
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /edit submission/i })
    ).not.toBeInTheDocument();
  });

  test("an empty edit deadline locks editing the day before the conference starts", async () => {
    await renderWithSubmission(pendingSubmission, {
      registration_opening: null,
      registration_deadline: null,
      date_start: "2020-06-30",
      date_end: null,
      submission_edit_deadline: null,
    });

    expect(screen.getByText("wsc2026-0042")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Editing submissions closed on 29 June 2020 — your submission can no longer be edited online. Contact the organizers for changes."
      )
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /edit submission/i })
    ).not.toBeInTheDocument();
  });

  describe("photo cropping", () => {
    async function openEditWithoutPhoto() {
      // With no existing photo the field renders the upload input (with
      // one, the preview + Remove render instead and a pick is impossible).
      await renderWithSubmission({ ...pendingSubmission, photo: null });
      await openEditForm();
    }

    function pickImageFile() {
      const file = new File(["original-bytes"], "new.png", {
        type: "image/png",
      });
      fireEvent.change(document.querySelector('input[type="file"]'), {
        target: { files: [file] },
      });
      return file;
    }

    async function openCropDialog() {
      fireEvent.click(await screen.findByRole("button", { name: "Crop…" }));
      return screen.findByRole("dialog", { name: "Crop photo" });
    }

    async function waitForDialogClose() {
      await waitFor(() => {
        expect(
          screen.queryByRole("dialog", { name: "Crop photo" })
        ).not.toBeInTheDocument();
      });
    }

    test("does not offer Crop… for the existing server-side photo", async () => {
      await renderWithSubmission(pendingSubmission);
      await openEditForm();

      expect(screen.getByRole("img", { name: "Preview" })).toHaveAttribute(
        "src",
        "http://localhost:8000/media/photos/alice.jpg"
      );
      expect(
        screen.queryByRole("button", { name: "Crop…" })
      ).not.toBeInTheDocument();
    });

    test("offers the Crop… button only after a local photo is picked", async () => {
      await openEditWithoutPhoto();

      expect(
        screen.queryByRole("button", { name: "Crop…" })
      ).not.toBeInTheDocument();

      pickImageFile();

      expect(
        await screen.findByRole("button", { name: "Crop…" })
      ).toBeInTheDocument();
    });

    test("clicking Crop… opens the crop dialog", async () => {
      await openEditWithoutPhoto();
      pickImageFile();

      expect(await openCropDialog()).toBeInTheDocument();
      expect(screen.getByRole("img", { name: "Crop preview" })).toHaveAttribute(
        "src",
        "blob:crop-preview"
      );
    });

    test("applying the crop PATCHes multipart with the cropped file as photo", async () => {
      const croppedFile = new File(["cropped-bytes"], "new.png", {
        type: "image/png",
      });
      cropToSquareFile.mockResolvedValue(croppedFile);

      await openEditWithoutPhoto();
      pickImageFile();
      await openCropDialog();
      fireEvent.load(screen.getByRole("img", { name: "Crop preview" }));
      fireEvent.click(screen.getByRole("button", { name: "Crop & Save" }));
      await waitForDialogClose();
      expect(cropToSquareFile).toHaveBeenCalledTimes(1);

      globalThis.fetch
        .mockResolvedValueOnce(jsonResponse(200, pendingSubmission))
        .mockResolvedValueOnce(jsonResponse(200, pendingSubmission));
      fireEvent.submit(document.querySelector("form"));

      expect(await screen.findByText(/Changes saved/i)).toBeInTheDocument();
      await waitFor(() => {
        expect(globalThis.fetch).toHaveBeenCalledTimes(3);
      });
      const [patchUrl, patchOptions] = globalThis.fetch.mock.calls[1];
      expect(patchUrl).toBe(trackUrl);
      expect(patchOptions.method).toBe("PATCH");
      expect(patchOptions.body).toBeInstanceOf(FormData);
      expect(patchOptions.body.get("photo")).toBe(croppedFile);
    });

    test("cancelling the crop dialog keeps the originally picked file", async () => {
      await openEditWithoutPhoto();
      const original = pickImageFile();
      await openCropDialog();
      fireEvent.click(
        await screen.findByRole("button", { name: "Keep Original" })
      );
      await waitForDialogClose();
      expect(cropToSquareFile).not.toHaveBeenCalled();

      globalThis.fetch
        .mockResolvedValueOnce(jsonResponse(200, pendingSubmission))
        .mockResolvedValueOnce(jsonResponse(200, pendingSubmission));
      fireEvent.submit(document.querySelector("form"));

      expect(await screen.findByText(/Changes saved/i)).toBeInTheDocument();
      await waitFor(() => {
        expect(globalThis.fetch).toHaveBeenCalledTimes(3);
      });
      const [, patchOptions] = globalThis.fetch.mock.calls[1];
      expect(patchOptions.body.get("photo")).toBe(original);
    });
  });
});
