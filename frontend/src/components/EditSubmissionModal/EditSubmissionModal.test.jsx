import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { fetchWithAuth } from "../../utils/api";
import { cropToSquareFile } from "../../utils/imageCrop";
import EditSubmissionModal from "./EditSubmissionModal";

vi.mock("../../utils/api", async () => ({
  ...(await vi.importActual("../../utils/api")),
  fetchWithAuth: vi.fn(),
}));

vi.mock("../../utils/imageCrop", async () => ({
  ...(await vi.importActual("../../utils/imageCrop")),
  cropToSquareFile: vi.fn(),
}));

const conferenceInfo = vi.hoisted(() => ({
  value: {
    registration_allow_talk: true,
    registration_allow_poster: true,
    registration_allow_attend: true,
  },
}));

vi.mock("../hooks/useConferenceInfo", () => ({
  useConferenceInfo: () => conferenceInfo.value,
}));

const submission = {
  id: 7,
  name: "Jane Doe",
  email: "jane@example.com",
  affiliation: "CTU",
  contribution_type: "talk",
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
    conferenceInfo.value = {
      registration_allow_talk: true,
      registration_allow_poster: true,
      registration_allow_attend: true,
    };
    onClose = vi.fn();
    onSave = vi.fn();
    fetchWithAuth.mockReset();
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
    document.body.style.cssText = "";
  });

  function renderModal(submissionOverride) {
    return render(
      <EditSubmissionModal
        submission={{ ...submission, ...submissionOverride }}
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

  test("attend hides contribution fields and clears their stale JSON values", async () => {
    fetchWithAuth.mockResolvedValueOnce({
      ok: true,
      json: async () => submission,
    });
    renderModal({
      contribution_type: "attend",
      abstract_title: "Stale title",
      abstract_text: "Stale abstract",
      additional_authors: "Stale Author",
      additional_affiliations: "Stale Affiliation",
    });

    expect(document.querySelector('input[name="abstract_title"]')).toBeNull();
    expect(document.querySelector('textarea[name="abstract_text"]')).toBeNull();
    expect(
      document.querySelector('input[name="additional_authors"]')
    ).toBeNull();
    expect(
      document.querySelector('textarea[name="additional_affiliations"]')
    ).toBeNull();

    fireEvent.submit(document.querySelector("form"));

    await waitFor(() => expect(fetchWithAuth).toHaveBeenCalledTimes(1));
    const payload = JSON.parse(fetchWithAuth.mock.calls[0][1].body);
    expect(payload).toMatchObject({
      contribution_type: "attend",
      abstract_title: "",
      abstract_text: "",
      additional_authors: "",
      additional_affiliations: "",
    });
  });

  test("attend clears stale contribution values in the multipart body", async () => {
    fetchWithAuth.mockResolvedValueOnce({
      ok: true,
      json: async () => submission,
    });
    renderModal({
      contribution_type: "attend",
      abstract_title: "Stale title",
      abstract_text: "Stale abstract",
      additional_authors: "Stale Author",
      additional_affiliations: "Stale Affiliation",
    });

    fireEvent.change(document.querySelector('input[type="file"]'), {
      target: {
        files: [new File(["fake"], "participant.png", { type: "image/png" })],
      },
    });
    fireEvent.submit(document.querySelector("form"));

    await waitFor(() => expect(fetchWithAuth).toHaveBeenCalledTimes(1));
    const body = fetchWithAuth.mock.calls[0][1].body;
    expect(body).toBeInstanceOf(FormData);
    for (const key of [
      "abstract_title",
      "abstract_text",
      "additional_authors",
      "additional_affiliations",
    ]) {
      expect(body.get(key)).toBe("");
    }
  });

  test("derived stay provenance is read-only and is not sent by the client", async () => {
    fetchWithAuth.mockResolvedValueOnce({
      ok: true,
      json: async () => submission,
    });
    renderModal({ stay_dates_derived: true });

    expect(
      screen.getByText(/Full conference stay: these dates were derived/i)
    ).toBeInTheDocument();
    expect(document.querySelector('[name="stay_dates_derived"]')).toBeNull();

    fireEvent.submit(document.querySelector("form"));

    await waitFor(() => expect(fetchWithAuth).toHaveBeenCalledTimes(1));
    const payload = JSON.parse(fetchWithAuth.mock.calls[0][1].body);
    expect(payload).not.toHaveProperty("stay_dates_derived");
  });

  test("equal collected dates show the repair banner and block the save", async () => {
    renderModal({ departure_date: submission.arrival_date });

    expect(screen.getByRole("alert")).toHaveTextContent(
      "This submission used the full conference day; set a departure date after arrival to save changes."
    );
    expect(document.querySelector('input[name="arrival_date"]')).toHaveValue(
      "2026-09-10"
    );
    expect(document.querySelector('input[name="departure_date"]')).toHaveValue(
      "2026-09-10"
    );

    fireEvent.submit(document.querySelector("form"));

    expect(await screen.findByText("Date repair required")).toBeInTheDocument();
    expect(fetchWithAuth).not.toHaveBeenCalled();
  });

  test("equal admin dates remain editable and save when collection is off", async () => {
    conferenceInfo.value.registration_collect_dates = false;
    fetchWithAuth.mockResolvedValueOnce({
      ok: true,
      json: async () => submission,
    });
    renderModal({ departure_date: submission.arrival_date });

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    fireEvent.submit(document.querySelector("form"));

    await waitFor(() => expect(fetchWithAuth).toHaveBeenCalledTimes(1));
    const payload = JSON.parse(fetchWithAuth.mock.calls[0][1].body);
    expect(payload.arrival_date).toBe("2026-09-10");
    expect(payload.departure_date).toBe("2026-09-10");
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

  test("prefills and saves additional info and the student flag over JSON", async () => {
    fetchWithAuth.mockResolvedValueOnce({
      ok: true,
      json: async () => submission,
    });
    renderModal({ info: "Vegetarian", is_student: true });

    const info = document.querySelector('textarea[name="info"]');
    const student = document.querySelector('input[name="is_student"]');
    expect(info).toHaveValue("Vegetarian");
    expect(student).toBeChecked();

    fireEvent.change(info, { target: { value: "Wheelchair access" } });
    fireEvent.click(student);
    fireEvent.submit(document.querySelector("form"));

    await waitFor(() => expect(fetchWithAuth).toHaveBeenCalledTimes(1));
    const [, opts] = fetchWithAuth.mock.calls[0];
    expect(opts.method).toBe("PATCH");
    expect(JSON.parse(opts.body)).toMatchObject({
      info: "Wheelchair access",
      is_student: false,
    });
  });

  test("sends additional info and the student flag in the multipart body", async () => {
    fetchWithAuth.mockResolvedValueOnce({
      ok: true,
      json: async () => submission,
    });
    renderModal({ info: "Vegetarian", is_student: true });

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
    expect(opts.body.get("info")).toBe("Vegetarian");
    expect(opts.body.get("is_student")).toBe("true");
  });

  test("a failed save shows the error modal and never calls onSave", async () => {
    fetchWithAuth.mockResolvedValueOnce({
      ok: false,
      status: 400,
      text: async () =>
        JSON.stringify({
          contribution_type: ["Unschedule the talk before changing this type."],
        }),
    });
    renderModal();

    fireEvent.submit(document.querySelector("form"));

    expect(await screen.findByText("Save failed")).toBeInTheDocument();
    expect(
      await screen.findByText(
        "contribution_type: Unschedule the talk before changing this type."
      )
    ).toBeInTheDocument();
    expect(onSave).not.toHaveBeenCalled();
  });

  test("only offers contribution types enabled for the conference", () => {
    conferenceInfo.value = {
      registration_allow_talk: true,
      registration_allow_poster: false,
      registration_allow_attend: false,
    };
    renderModal();

    expect(screen.getByLabelText("Talk")).toBeInTheDocument();
    expect(screen.queryByLabelText("Poster")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Just attend")).not.toBeInTheDocument();
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
      name: /ok/i,
    });
    fireEvent.click(confirmBtn);
    expect(onSave).toHaveBeenCalledWith(updated);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  describe("photo cropping", () => {
    function pickImageFile() {
      const file = new File(["original-bytes"], "participant.png", {
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

    test("offers the Crop… button only after a local photo is picked", async () => {
      renderModal();

      expect(
        screen.queryByRole("button", { name: "Crop…" })
      ).not.toBeInTheDocument();

      pickImageFile();

      expect(
        await screen.findByRole("button", { name: "Crop…" })
      ).toBeInTheDocument();
    });

    test("does not offer Crop… for the existing server-side photo", () => {
      renderModal({ photo: "/media/photos/jane.jpg" });

      expect(screen.getByRole("img", { name: "Preview" })).toHaveAttribute(
        "src",
        "http://localhost:8000/media/photos/jane.jpg"
      );
      expect(
        screen.queryByRole("button", { name: "Crop…" })
      ).not.toBeInTheDocument();
    });

    test("clicking Crop… opens the crop dialog", async () => {
      renderModal();
      pickImageFile();

      expect(await openCropDialog()).toBeInTheDocument();
      expect(screen.getByRole("img", { name: "Crop preview" })).toHaveAttribute(
        "src",
        "blob:crop-preview"
      );
    });

    test("applying the crop PUTs the multipart body with the cropped file as photo", async () => {
      const croppedFile = new File(["cropped-bytes"], "participant.png", {
        type: "image/png",
      });
      cropToSquareFile.mockResolvedValue(croppedFile);
      fetchWithAuth.mockResolvedValueOnce({
        ok: true,
        json: async () => submission,
      });
      renderModal();

      pickImageFile();
      await openCropDialog();
      fireEvent.load(screen.getByRole("img", { name: "Crop preview" }));
      fireEvent.click(screen.getByRole("button", { name: "Crop & Save" }));
      await waitForDialogClose();
      expect(cropToSquareFile).toHaveBeenCalledTimes(1);

      fireEvent.submit(document.querySelector("form"));

      await waitFor(() => expect(fetchWithAuth).toHaveBeenCalledTimes(1));
      const [url, opts] = fetchWithAuth.mock.calls[0];
      expect(url).toBe("/api/admin/submissions/7/");
      expect(opts.method).toBe("PUT");
      expect(opts.body).toBeInstanceOf(FormData);
      expect(opts.body.get("photo")).toBe(croppedFile);
    });

    test("cancelling the crop dialog keeps the originally picked file", async () => {
      fetchWithAuth.mockResolvedValueOnce({
        ok: true,
        json: async () => submission,
      });
      renderModal();

      const original = pickImageFile();
      await openCropDialog();
      fireEvent.click(
        await screen.findByRole("button", { name: "Keep Original" })
      );
      await waitForDialogClose();
      expect(cropToSquareFile).not.toHaveBeenCalled();

      fireEvent.submit(document.querySelector("form"));

      await waitFor(() => expect(fetchWithAuth).toHaveBeenCalledTimes(1));
      expect(fetchWithAuth.mock.calls[0][1].body.get("photo")).toBe(original);
    });
  });
});

// Regression: the crop dialog stacks its own body-scroll lock on top of
// the edit modal's lock. useLockBodyScroll must restore the outer lock on
// close; blanking inline styles would silently destroy it. The REAL
// PhotoCropModal is rendered so the two hooks actually interact.
describe("nested scroll lock with the crop dialog", () => {
  beforeEach(() => {
    localStorage.clear();
    fetchWithAuth.mockReset();
    cropToSquareFile.mockReset();
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
  });

  test("closing the crop dialog preserves the edit modal's scroll lock", async () => {
    render(
      <EditSubmissionModal
        submission={submission}
        onClose={vi.fn()}
        onSave={vi.fn()}
      />
    );
    // The edit modal locks scrolling directly on mount.
    expect(document.body.style.overflow).toBe("hidden");

    fireEvent.change(document.querySelector('input[type="file"]'), {
      target: {
        files: [
          new File(["original-bytes"], "participant.png", {
            type: "image/png",
          }),
        ],
      },
    });
    fireEvent.click(await screen.findByRole("button", { name: "Crop…" }));
    expect(
      await screen.findByRole("dialog", { name: "Crop photo" })
    ).toBeInTheDocument();
    expect(document.body.style.overflow).toBe("hidden");

    fireEvent.click(screen.getByRole("button", { name: "Keep Original" }));
    await waitFor(() =>
      expect(
        screen.queryByRole("dialog", { name: "Crop photo" })
      ).not.toBeInTheDocument()
    );

    expect(document.body.style.overflow).toBe("hidden");
  });
});
