import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { mockNavigate } from "../../testUtils/reactRouterDomStub";
import { fetchWithAuth, refreshAccessToken } from "../../utils/api";
import Footer from "./Footer";

vi.mock("../../utils/api", async () => ({
  ...(await vi.importActual("../../utils/api")),
  fetchWithAuth: vi.fn(),
  refreshAccessToken: vi.fn(),
}));

/**
 * The footer venue column renders the dedicated `footer_venue_text` field,
 * independent of the venue page's `venue_text`. `useConferenceInfo` GETs
 * /api/conference-info/ through the global fetch, which is mocked here.
 */

const infoPayload = {
  footer_venue_text: "Footer venue blurb",
  venue_text: "Venue page description",
};

function jsonOf(payload) {
  return { ok: true, json: async () => payload };
}

beforeEach(() => {
  document.body.style.cssText = "";
  mockNavigate.mockReset();
  fetchWithAuth.mockReset();
  refreshAccessToken.mockReset();
  globalThis.fetch = vi.fn().mockResolvedValue(jsonOf(infoPayload));
});

describe("Footer", () => {
  test("restores body scrolling after a successful admin login", async () => {
    fetchWithAuth
      .mockResolvedValueOnce({ ok: false })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          password_login_enabled: true,
          gitlab_login_enabled: false,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ access: "A", refresh: "R" }),
      });
    render(<Footer />);

    fireEvent.click(
      await screen.findByRole("button", { name: /administration/i })
    );
    await screen.findByPlaceholderText(/enter username/i);
    expect(document.body.style.position).toBe("fixed");
    expect(document.body.style.overflow).toBe("hidden");

    fireEvent.change(screen.getByPlaceholderText(/enter username/i), {
      target: { value: "admin" },
    });
    fireEvent.change(screen.getByPlaceholderText(/enter password/i), {
      target: { value: "pw" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^login$/i }));

    await waitFor(() => expect(document.body.style.position).toBe(""));
    expect(document.body.style.overflow).toBe("");
  });

  test("skips the login modal when the admin session is already active", async () => {
    fetchWithAuth.mockResolvedValueOnce({ ok: true });
    render(<Footer />);

    fireEvent.click(
      await screen.findByRole("button", { name: /administration/i })
    );

    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith("/admin-panel")
    );
    expect(
      screen.queryByPlaceholderText(/enter username/i)
    ).not.toBeInTheDocument();
  });

  test("refreshes an expired access cookie before opening the modal", async () => {
    fetchWithAuth.mockResolvedValueOnce({ ok: false, status: 401 });
    refreshAccessToken.mockResolvedValueOnce(true);
    render(<Footer />);

    fireEvent.click(
      await screen.findByRole("button", { name: /administration/i })
    );

    await waitFor(() =>
      expect(refreshAccessToken).toHaveBeenCalledWith({
        reloadOnFailure: false,
      })
    );
    expect(mockNavigate).toHaveBeenCalledWith("/admin-panel");
    expect(
      screen.queryByPlaceholderText(/enter username/i)
    ).not.toBeInTheDocument();
  });

  test("opens the modal when the auth probe fails", async () => {
    fetchWithAuth
      .mockRejectedValueOnce(new Error("network"))
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          password_login_enabled: true,
          gitlab_login_enabled: false,
        }),
      });
    render(<Footer />);

    fireEvent.click(
      await screen.findByRole("button", { name: /administration/i })
    );

    expect(
      await screen.findByPlaceholderText(/enter username/i)
    ).toBeInTheDocument();
  });

  test("opens the modal when the soft refresh fails", async () => {
    fetchWithAuth
      .mockResolvedValueOnce({ ok: false, status: 401 })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          password_login_enabled: true,
          gitlab_login_enabled: false,
        }),
      });
    refreshAccessToken.mockResolvedValueOnce(false);
    render(<Footer />);

    fireEvent.click(
      await screen.findByRole("button", { name: /administration/i })
    );

    expect(
      await screen.findByPlaceholderText(/enter username/i)
    ).toBeInTheDocument();
  });

  test("ignores repeated Administration clicks while probing", async () => {
    let resolveProbe;
    fetchWithAuth.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveProbe = resolve;
      })
    );
    render(<Footer />);

    const button = await screen.findByRole("button", {
      name: /administration/i,
    });
    fireEvent.click(button);
    fireEvent.click(button);

    expect(fetchWithAuth).toHaveBeenCalledTimes(1);
    resolveProbe({ ok: true });
    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith("/admin-panel")
    );
  });

  test("renders the footer venue field, not the venue page description", async () => {
    render(<Footer />);

    expect(await screen.findByText("Footer venue blurb")).toBeInTheDocument();
    expect(
      screen.queryByText("Venue page description")
    ).not.toBeInTheDocument();
  });
});
