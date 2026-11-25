import { fireEvent, render, screen } from "@testing-library/react";
import { fetchWithAuth } from "../../utils/api";
import EditWebInfoSponsors from "./EditWebInfoSponsors";

vi.mock("../../utils/api", async () => ({
  ...(await vi.importActual("../../utils/api")),
  fetchWithAuth: vi.fn(),
}));

const existingSponsor = {
  id: 7,
  name: "Existing Sponsor",
  url: "https://existing.example",
  logo: "/media/sponsors/existing.png",
  order: 2,
};

function jsonOf(payload) {
  return {
    ok: true,
    status: 200,
    json: async () => payload,
    text: async () => "",
  };
}

async function renderLoaded() {
  fetchWithAuth.mockResolvedValueOnce(jsonOf([existingSponsor]));
  const view = render(<EditWebInfoSponsors />);
  await screen.findByDisplayValue("Existing Sponsor");
  return view;
}

function requestCall(url, method) {
  const call = fetchWithAuth.mock.calls.find(
    ([requestUrl, options]) => requestUrl === url && options?.method === method
  );
  expect(call).toBeDefined();
  return call;
}

describe("EditWebInfoSponsors", () => {
  beforeEach(() => {
    fetchWithAuth.mockReset();
    URL.createObjectURL = vi.fn(() => "blob:logo-preview");
    URL.revokeObjectURL = vi.fn();
  });

  test("creates a new sponsor with its selected logo in FormData", async () => {
    await renderLoaded();

    fireEvent.click(screen.getByRole("button", { name: "+ ADD SPONSOR" }));
    fireEvent.change(screen.getAllByLabelText("Name")[1], {
      target: { value: "New Sponsor" },
    });
    fireEvent.change(screen.getAllByLabelText("Website URL")[1], {
      target: { value: "https://new.example" },
    });
    fireEvent.change(screen.getAllByLabelText("Order")[1], {
      target: { value: "4" },
    });

    const file = new File(["fake logo"], "sponsor.png", {
      type: "image/png",
    });
    fireEvent.change(screen.getAllByLabelText("Change logo")[1], {
      target: { files: [file] },
    });

    const createdSponsor = {
      id: 8,
      name: "New Sponsor",
      url: "https://new.example",
      logo: "/media/sponsors/sponsor.png",
      order: 4,
    };
    fetchWithAuth
      .mockResolvedValueOnce(jsonOf(existingSponsor))
      .mockResolvedValueOnce(jsonOf(createdSponsor));

    fireEvent.click(screen.getByRole("button", { name: "SAVE SPONSORS" }));
    expect(
      await screen.findByText("Sponsors saved successfully.")
    ).toBeInTheDocument();

    const [, options] = requestCall("/api/admin/sponsors/", "POST");
    expect(options.body).toBeInstanceOf(FormData);
    expect(options.body.get("name")).toBe("New Sponsor");
    expect(options.body.get("url")).toBe("https://new.example");
    expect(options.body.get("order")).toBe("4");
    expect(options.body.get("logo")).toBe(file);
  });

  test("updates an existing sponsor without a logo field when no new file is selected", async () => {
    await renderLoaded();
    fetchWithAuth.mockResolvedValueOnce(jsonOf(existingSponsor));

    fireEvent.click(screen.getByRole("button", { name: "SAVE SPONSORS" }));
    expect(
      await screen.findByText("Sponsors saved successfully.")
    ).toBeInTheDocument();

    const [, options] = requestCall("/api/admin/sponsors/7/", "PATCH");
    expect(options.body).toBeInstanceOf(FormData);
    expect(options.body.get("name")).toBe("Existing Sponsor");
    expect(options.body.get("url")).toBe("https://existing.example");
    expect(options.body.get("order")).toBe("2");
    expect(options.body.has("logo")).toBe(false);
  });

  test("shows an error modal when loading sponsors returns an HTTP error", async () => {
    fetchWithAuth.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({ detail: "Ignored error payload" }),
      text: async () => "Unable to load current sponsors",
    });
    render(<EditWebInfoSponsors />);

    expect(await screen.findByText("Connection error")).toBeInTheDocument();
    expect(
      screen.getByText("Unable to load current sponsors")
    ).toBeInTheDocument();
    expect(screen.queryByDisplayValue("Existing Sponsor")).toBeNull();
  });

  test("keeps ids from fulfilled requests when another request rejects", async () => {
    await renderLoaded();
    fireEvent.click(screen.getByRole("button", { name: "+ ADD SPONSOR" }));
    fireEvent.change(screen.getAllByLabelText("Name")[1], {
      target: { value: "Network Survivor" },
    });

    const createdSponsor = {
      id: 8,
      name: "Network Survivor",
      url: "",
      logo: null,
      order: 1,
    };
    fetchWithAuth
      .mockRejectedValueOnce(new Error("Network down"))
      .mockResolvedValueOnce(jsonOf(createdSponsor));

    fireEvent.click(screen.getByRole("button", { name: "SAVE SPONSORS" }));
    expect(await screen.findByText("Network down")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "OK" }));

    expect(
      await screen.findByDisplayValue("Network Survivor")
    ).toBeInTheDocument();

    fetchWithAuth
      .mockResolvedValueOnce(jsonOf(existingSponsor))
      .mockResolvedValueOnce(jsonOf(createdSponsor));
    fireEvent.click(screen.getByRole("button", { name: "SAVE SPONSORS" }));
    expect(
      await screen.findByText("Sponsors saved successfully.")
    ).toBeInTheDocument();

    const postCalls = fetchWithAuth.mock.calls.filter(
      ([url, options]) =>
        url === "/api/admin/sponsors/" && options?.method === "POST"
    );
    expect(postCalls).toHaveLength(1);
    requestCall("/api/admin/sponsors/8/", "PATCH");
  });

  test("saves a cleared order as zero", async () => {
    await renderLoaded();
    fireEvent.click(screen.getByRole("button", { name: "+ ADD SPONSOR" }));
    fireEvent.change(screen.getAllByLabelText("Name")[1], {
      target: { value: "Blank Order" },
    });
    fireEvent.change(screen.getAllByLabelText("Order")[1], {
      target: { value: "" },
    });

    const createdSponsor = {
      id: 8,
      name: "Blank Order",
      url: "",
      logo: null,
      order: 0,
    };
    fetchWithAuth
      .mockResolvedValueOnce(jsonOf(existingSponsor))
      .mockResolvedValueOnce(jsonOf(createdSponsor));

    fireEvent.click(screen.getByRole("button", { name: "SAVE SPONSORS" }));
    expect(
      await screen.findByText("Sponsors saved successfully.")
    ).toBeInTheDocument();

    const [, options] = requestCall("/api/admin/sponsors/", "POST");
    expect(options.body.get("order")).toBe("0");
  });

  test("does not duplicate a successfully created sponsor when retrying a partial save failure", async () => {
    await renderLoaded();
    fireEvent.click(screen.getByRole("button", { name: "+ ADD SPONSOR" }));
    fireEvent.change(screen.getAllByLabelText("Name")[1], {
      target: { value: "New Sponsor" },
    });

    const createdSponsor = {
      id: 8,
      name: "New Sponsor",
      url: "",
      logo: null,
      order: 1,
    };
    fetchWithAuth
      .mockResolvedValueOnce({
        ok: false,
        status: 400,
        text: async () => "Existing row is invalid",
      })
      .mockResolvedValueOnce(jsonOf(createdSponsor));

    fireEvent.click(screen.getByRole("button", { name: "SAVE SPONSORS" }));
    expect(
      await screen.findByText("Existing row is invalid")
    ).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "OK" }));

    expect(await screen.findByDisplayValue("New Sponsor")).toBeInTheDocument();
    fetchWithAuth
      .mockResolvedValueOnce(jsonOf(existingSponsor))
      .mockResolvedValueOnce(jsonOf(createdSponsor));
    fireEvent.click(screen.getByRole("button", { name: "SAVE SPONSORS" }));
    expect(
      await screen.findByText("Sponsors saved successfully.")
    ).toBeInTheDocument();

    const postCalls = fetchWithAuth.mock.calls.filter(
      ([url, options]) =>
        url === "/api/admin/sponsors/" && options?.method === "POST"
    );
    expect(postCalls).toHaveLength(1);
    requestCall("/api/admin/sponsors/8/", "PATCH");
  });
});
