import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { fetchWithAuth } from "../../utils/api";
import { initConferenceSlug } from "../../utils/conferenceSlug";
import AdminLoginModal from "./AdminLoginModal";

vi.mock("../../utils/api", () => ({
  fetchWithAuth: vi.fn(),
}));

const PASSWORD_ONLY = {
  password_login_enabled: true,
  gitlab_login_enabled: false,
};
const GITLAB_ONLY = {
  password_login_enabled: false,
  gitlab_login_enabled: true,
};
const BOTH = { password_login_enabled: true, gitlab_login_enabled: true };
const NEITHER = { password_login_enabled: false, gitlab_login_enabled: false };

function configResponse(config) {
  return { ok: true, json: async () => config };
}

/** Config on any call; other URLs reject unless a test overrides them. */
function mockApi(config) {
  fetchWithAuth.mockImplementation((url) => {
    if (url === "/api/auth/config/") {
      return Promise.resolve(configResponse(config));
    }
    return Promise.reject(new Error(`unexpected fetchWithAuth call: ${url}`));
  });
}

let assignMock;

/**
 * The modal reads the slug from the conferenceSlug singleton (parsed from
 * window.location.pathname) and navigates via window.location.assign, so
 * each test points the location at a conference path and re-inits the slug.
 */
function setLocation(pathname = "/wsc2026/") {
  assignMock = vi.fn();
  Object.defineProperty(window, "location", {
    configurable: true,
    writable: true,
    value: { pathname, search: "", hash: "", assign: assignMock },
  });
  initConferenceSlug();
}

describe("AdminLoginModal", () => {
  let onSuccess;
  let onClose;

  const fillUsername = (value) => {
    fireEvent.change(screen.getByPlaceholderText(/enter username/i), {
      target: { value },
    });
  };

  const fillPassword = (value) => {
    fireEvent.change(screen.getByPlaceholderText(/enter password/i), {
      target: { value },
    });
  };

  const submit = () => {
    fireEvent.click(screen.getByRole("button", { name: /^login$/i }));
  };

  beforeEach(() => {
    localStorage.clear();
    onSuccess = vi.fn();
    onClose = vi.fn();
    fetchWithAuth.mockReset();
    setLocation();
  });

  test("asks the backend for the sign-in config on mount", async () => {
    mockApi(PASSWORD_ONLY);
    render(<AdminLoginModal onSuccess={onSuccess} onClose={onClose} />);

    await waitFor(() =>
      expect(fetchWithAuth).toHaveBeenCalledWith("/api/auth/config/")
    );
  });

  test("renders nothing actionable until the config arrives", () => {
    fetchWithAuth.mockImplementation(() => new Promise(() => {}));
    render(<AdminLoginModal onSuccess={onSuccess} onClose={onClose} />);

    expect(
      screen.queryByRole("button", { name: /^login$/i })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /sign in with gitlab/i })
    ).not.toBeInTheDocument();
  });

  describe("password login", () => {
    test("shows the password form (not GitLab) once the config arrives", async () => {
      mockApi(PASSWORD_ONLY);
      render(<AdminLoginModal onSuccess={onSuccess} onClose={onClose} />);

      // Focus is applied by an effect once the config lands; poll for it.
      await waitFor(() =>
        expect(screen.getByPlaceholderText(/enter username/i)).toHaveFocus()
      );
      expect(
        screen.getByPlaceholderText(/enter password/i)
      ).toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: /sign in with gitlab/i })
      ).not.toBeInTheDocument();
    });

    test("renders the password form directly, without the special-account section", async () => {
      mockApi(PASSWORD_ONLY);
      render(<AdminLoginModal onSuccess={onSuccess} onClose={onClose} />);

      await screen.findByPlaceholderText(/enter username/i);
      expect(screen.queryByText(/special account/i)).toBeNull();
      expect(screen.getByPlaceholderText(/enter username/i)).toBeVisible();
      expect(screen.getByPlaceholderText(/enter password/i)).toBeVisible();
    });

    test("posts to the login endpoint with the entered credentials", async () => {
      fetchWithAuth.mockImplementation((url) => {
        if (url === "/api/auth/config/") {
          return Promise.resolve(configResponse(PASSWORD_ONLY));
        }
        if (url === "/api/auth/login/") {
          return Promise.resolve({
            ok: true,
            json: async () => ({ access: "A", refresh: "R" }),
          });
        }
        return Promise.reject(new Error(`unexpected call: ${url}`));
      });
      render(<AdminLoginModal onSuccess={onSuccess} onClose={onClose} />);
      await screen.findByPlaceholderText(/enter username/i);
      fillUsername("alice");
      fillPassword("s3cret");
      submit();

      await waitFor(() =>
        expect(fetchWithAuth).toHaveBeenCalledWith(
          "/api/auth/login/",
          expect.objectContaining({ method: "POST" })
        )
      );
      const [, opts] = fetchWithAuth.mock.calls.find(
        ([callUrl]) => callUrl === "/api/auth/login/"
      );
      expect(JSON.parse(opts.body)).toEqual({
        username: "alice",
        password: "s3cret",
      });
    });

    test("calls onSuccess on a 200 without storing tokens", async () => {
      fetchWithAuth.mockImplementation((url) => {
        if (url === "/api/auth/config/") {
          return Promise.resolve(configResponse(PASSWORD_ONLY));
        }
        if (url === "/api/auth/login/") {
          return Promise.resolve({ ok: true });
        }
        return Promise.reject(new Error(`unexpected call: ${url}`));
      });
      render(<AdminLoginModal onSuccess={onSuccess} onClose={onClose} />);
      await screen.findByPlaceholderText(/enter username/i);
      fillUsername("alice");
      fillPassword("pw");
      submit();

      await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1));
      expect(localStorage.getItem("access_token")).toBeNull();
      expect(localStorage.getItem("refresh_token")).toBeNull();
    });

    test("shows the wrong-credentials message and does not persist on non-OK", async () => {
      fetchWithAuth.mockImplementation((url) => {
        if (url === "/api/auth/config/") {
          return Promise.resolve(configResponse(PASSWORD_ONLY));
        }
        if (url === "/api/auth/login/") {
          return Promise.resolve({ ok: false });
        }
        return Promise.reject(new Error(`unexpected call: ${url}`));
      });
      render(<AdminLoginModal onSuccess={onSuccess} onClose={onClose} />);
      await screen.findByPlaceholderText(/enter username/i);
      fillUsername("alice");
      fillPassword("bad");
      submit();

      expect(
        await screen.findByText(/wrong username or password/i)
      ).toBeInTheDocument();
      expect(onSuccess).not.toHaveBeenCalled();
      expect(localStorage.getItem("access_token")).toBeNull();
    });

    test("shows the connection-error message when the login call rejects", async () => {
      fetchWithAuth.mockImplementation((url) => {
        if (url === "/api/auth/config/") {
          return Promise.resolve(configResponse(PASSWORD_ONLY));
        }
        return Promise.reject(new Error("boom"));
      });
      render(<AdminLoginModal onSuccess={onSuccess} onClose={onClose} />);
      await screen.findByPlaceholderText(/enter username/i);
      fillUsername("alice");
      fillPassword("pw");
      submit();

      expect(await screen.findByText(/connection error/i)).toBeInTheDocument();
      expect(onSuccess).not.toHaveBeenCalled();
    });

    test("hides the password form when the config disables it", async () => {
      mockApi(GITLAB_ONLY);
      render(<AdminLoginModal onSuccess={onSuccess} onClose={onClose} />);

      await screen.findByRole("button", { name: /sign in with gitlab/i });
      expect(
        screen.queryByPlaceholderText(/enter username/i)
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: /^login$/i })
      ).not.toBeInTheDocument();
    });
  });

  describe("GitLab login", () => {
    test("shows the GitLab button (not the password form) when enabled", async () => {
      mockApi(GITLAB_ONLY);
      render(<AdminLoginModal onSuccess={onSuccess} onClose={onClose} />);

      expect(
        await screen.findByRole("button", { name: /sign in with gitlab/i })
      ).toBeInTheDocument();
    });

    test("shows both methods when both are enabled", async () => {
      mockApi(BOTH);
      render(<AdminLoginModal onSuccess={onSuccess} onClose={onClose} />);

      expect(
        await screen.findByRole("button", { name: /sign in with gitlab/i })
      ).toBeInTheDocument();
      expect(
        screen.getByPlaceholderText(/enter username/i)
      ).toBeInTheDocument();
    });

    test("keeps the password form inside the collapsed special-account section", async () => {
      mockApi(BOTH);
      render(<AdminLoginModal onSuccess={onSuccess} onClose={onClose} />);

      const summary = await screen.findByText(/special account/i);
      const details = summary.closest("details");
      expect(details).not.toBeNull();
      expect(details.open).toBe(false);
      expect(details).toContainElement(
        screen.getByPlaceholderText(/enter username/i)
      );
      expect(details).toContainElement(
        screen.getByPlaceholderText(/enter password/i)
      );
    });

    test("hides the GitLab button when the config disables it", async () => {
      mockApi(PASSWORD_ONLY);
      render(<AdminLoginModal onSuccess={onSuccess} onClose={onClose} />);

      await screen.findByPlaceholderText(/enter username/i);
      expect(
        screen.queryByRole("button", { name: /sign in with gitlab/i })
      ).not.toBeInTheDocument();
    });

    test("requests the authorize URL with the conference slug and redirects", async () => {
      fetchWithAuth.mockImplementation((url) => {
        if (url === "/api/auth/config/") {
          return Promise.resolve(configResponse(GITLAB_ONLY));
        }
        if (url.startsWith("/api/auth/gitlab/authorize/")) {
          return Promise.resolve({
            ok: true,
            json: async () => ({
              url: "https://gitlab.example.com/oauth/authorize?client_id=x",
            }),
          });
        }
        return Promise.reject(new Error(`unexpected call: ${url}`));
      });
      render(<AdminLoginModal onSuccess={onSuccess} onClose={onClose} />);

      fireEvent.click(
        await screen.findByRole("button", { name: /sign in with gitlab/i })
      );

      await waitFor(() =>
        expect(assignMock).toHaveBeenCalledWith(
          "https://gitlab.example.com/oauth/authorize?client_id=x"
        )
      );
      const [url, opts] = fetchWithAuth.mock.calls.find(([callUrl]) =>
        callUrl.startsWith("/api/auth/gitlab/authorize/")
      );
      expect(url).toBe("/api/auth/gitlab/authorize/?next=wsc2026");
      expect(opts.credentials).toBe("include");
    });

    test("shows an error and does not navigate when the authorize call fails", async () => {
      fetchWithAuth.mockImplementation((url) => {
        if (url === "/api/auth/config/") {
          return Promise.resolve(configResponse(GITLAB_ONLY));
        }
        return Promise.reject(new Error("boom"));
      });
      render(<AdminLoginModal onSuccess={onSuccess} onClose={onClose} />);

      fireEvent.click(
        await screen.findByRole("button", { name: /sign in with gitlab/i })
      );

      expect(
        await screen.findByText(/gitlab sign-in could not be started/i)
      ).toBeInTheDocument();
      expect(assignMock).not.toHaveBeenCalled();
    });
  });

  describe("broken configuration", () => {
    test("shows a configuration error when both login methods are disabled", async () => {
      mockApi(NEITHER);
      render(<AdminLoginModal onSuccess={onSuccess} onClose={onClose} />);

      expect(
        await screen.findByText(/sign-in is not configured/i)
      ).toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: /sign in with gitlab/i })
      ).not.toBeInTheDocument();
      expect(
        screen.queryByPlaceholderText(/enter username/i)
      ).not.toBeInTheDocument();
    });

    test("shows an error and no form when the config request fails", async () => {
      fetchWithAuth.mockRejectedValue(new Error("boom"));
      render(<AdminLoginModal onSuccess={onSuccess} onClose={onClose} />);

      expect(
        await screen.findByText(/sign-in options could not be loaded/i)
      ).toBeInTheDocument();
      expect(
        screen.queryByPlaceholderText(/enter username/i)
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: /sign in with gitlab/i })
      ).not.toBeInTheDocument();
    });

    test("shows an error when the config request responds non-OK", async () => {
      fetchWithAuth.mockResolvedValue({ ok: false, status: 500 });
      render(<AdminLoginModal onSuccess={onSuccess} onClose={onClose} />);

      expect(
        await screen.findByText(/sign-in options could not be loaded/i)
      ).toBeInTheDocument();
    });
  });
});
