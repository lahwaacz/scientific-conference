// Minimal react-router-dom stub for tests. The real package ships ESM
// that resolves fine under Vitest; the stub is kept anyway so component
// tests stay free of real router machinery. Extend only as tests require.
export const Navigate = ({ to }) => <div data-testid="navigate" data-to={to} />;

export const Link = ({ to, children, ...rest }) => (
  <a href={to} {...rest}>
    {children}
  </a>
);

// Recorded navigate for tests to assert on; vi.clearAllMocks() resets it.
export const mockNavigate = vi.fn();

export const useNavigate = () => mockNavigate;

let testLocation = { pathname: "/", search: "" };

/** Point useLocation at a specific location for the current test. */
export const setTestLocation = (location) => {
  testLocation = location;
};

export const useLocation = () => testLocation;

let testParams = {};

/** Set the route params useParams() returns for the current test. */
export const setTestParams = (params) => {
  testParams = params;
};

export const useParams = () => testParams;
