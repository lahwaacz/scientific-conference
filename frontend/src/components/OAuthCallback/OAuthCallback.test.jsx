import { render, screen, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import OAuthCallback from "./OAuthCallback";

vi.mock("../../utils/api", () => ({
  buildApiUrl: (path) => `http://backend.test${path}`,
}));

let replaceMock;

/**
 * The component reads window.location.search directly (HashRouter stub
 * never sees the pre-hash query of a backend redirect) and navigates via
 * window.location.replace; both are stubbed per test.
 */
function setLocation(search) {
  replaceMock = vi.fn();
  Object.defineProperty(window, "location", {
    configurable: true,
    writable: true,
    value: {
      pathname: "/conference/oauth/callback",
      search,
      hash: "",
      replace: replaceMock,
      assign: vi.fn(),
    },
  });
}

function exchangeResponse(payload, ok = true) {
  return Promise.resolve({ ok, json: async () => payload });
}

async function renderAndWaitForPost(search = "?code=abc123&state=xyz") {
  setLocation(search);
  globalThis.fetch = vi.fn(() =>
    exchangeResponse({
      user: { username: "alice" },
      next: "/conference/wsc2026/#/admin-panel",
    })
  );
  render(<OAuthCallback />);
  await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledTimes(1));
  return globalThis.fetch.mock.calls[0];
}

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  delete globalThis.__APP_CONFIG__;
});

describe("OAuthCallback", () => {
  test("posts the code and state to the GitLab exchange endpoint", async () => {
    const [url, opts] = await renderAndWaitForPost();

    expect(url).toBe("http://backend.test/api/auth/gitlab/");
    expect(opts.method).toBe("POST");
    expect(opts.credentials).toBe("include");
    expect(JSON.parse(opts.body)).toEqual({ code: "abc123", state: "xyz" });
  });

  test("redirects to the backend-provided next without storing tokens", async () => {
    await renderAndWaitForPost();

    await waitFor(() =>
      expect(replaceMock).toHaveBeenCalledWith(
        "/conference/wsc2026/#/admin-panel"
      )
    );
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
  });

  test("shows a loading state while the exchange is in flight", async () => {
    setLocation("?code=abc123&state=xyz");
    globalThis.fetch = vi.fn(() => new Promise(() => {}));
    render(<OAuthCallback />);

    expect(screen.getByText(/signing you in/i)).toBeInTheDocument();
    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledTimes(1));
  });

  test("falls back to the root when next is protocol-relative", async () => {
    setLocation("?code=abc123&state=xyz");
    globalThis.fetch = vi.fn(() =>
      exchangeResponse({ access: "A", refresh: "R", next: "//evil.test/x" })
    );
    render(<OAuthCallback />);

    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/"));
  });

  test("falls back to the deployment base when next is invalid", async () => {
    globalThis.__APP_CONFIG__ = { basePath: "/conference" };
    setLocation("?code=abc123&state=xyz");
    globalThis.fetch = vi.fn(() =>
      exchangeResponse({ access: "A", refresh: "R", next: "//evil.test/x" })
    );
    render(<OAuthCallback />);

    await waitFor(() =>
      expect(replaceMock).toHaveBeenCalledWith("/conference/")
    );
  });

  test("falls back to the root when next is an absolute URL", async () => {
    setLocation("?code=abc123&state=xyz");
    globalThis.fetch = vi.fn(() =>
      exchangeResponse({
        access: "A",
        refresh: "R",
        next: "https://evil.test/x",
      })
    );
    render(<OAuthCallback />);

    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/"));
  });

  test("falls back to the root when next contains a backslash", async () => {
    setLocation("?code=abc123&state=xyz");
    globalThis.fetch = vi.fn(() =>
      exchangeResponse({ access: "A", refresh: "R", next: "/\\evil.test/x" })
    );
    render(<OAuthCallback />);

    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/"));
  });

  test("posts the single-use code only once under React StrictMode", async () => {
    setLocation("?code=abc123&state=xyz");
    globalThis.fetch = vi.fn(() =>
      exchangeResponse({ access: "A", refresh: "R", next: "/" })
    );
    render(
      <StrictMode>
        <OAuthCallback />
      </StrictMode>
    );

    await waitFor(() => expect(replaceMock).toHaveBeenCalledWith("/"));
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });

  test("shows a cancelled/failed message when the provider returns an error", async () => {
    setLocation("?error=access_denied");
    globalThis.fetch = vi.fn();
    render(<OAuthCallback />);

    expect(await screen.findByText(/cancelled or failed/i)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /back to home/i })
    ).toBeInTheDocument();
    expect(globalThis.fetch).not.toHaveBeenCalled();
    expect(replaceMock).not.toHaveBeenCalled();
  });

  test("shows an error when code or state is missing", async () => {
    setLocation("?code=abc123");
    globalThis.fetch = vi.fn();
    render(<OAuthCallback />);

    expect(
      await screen.findByText(/authorization code or state is missing/i)
    ).toBeInTheDocument();
    expect(globalThis.fetch).not.toHaveBeenCalled();
    expect(replaceMock).not.toHaveBeenCalled();
  });

  test("shows an error when the exchange responds non-OK", async () => {
    setLocation("?code=abc123&state=xyz");
    globalThis.fetch = vi.fn(() => exchangeResponse({}, false));
    render(<OAuthCallback />);

    expect(
      await screen.findByText(/authorization code may have expired/i)
    ).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
  });

  test("shows a connection error when the exchange rejects", async () => {
    setLocation("?code=abc123&state=xyz");
    globalThis.fetch = vi.fn(() => Promise.reject(new Error("boom")));
    render(<OAuthCallback />);

    expect(await screen.findByText(/connection error/i)).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });
});
