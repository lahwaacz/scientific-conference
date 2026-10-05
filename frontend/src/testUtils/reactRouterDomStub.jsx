// Minimal react-router-dom stub for tests. The real package ships ESM
// that resolves fine under Vitest; the stub is kept anyway so component
// tests stay free of real router machinery. Extend only as tests require.
export const Navigate = ({ to }) => <div data-testid="navigate" data-to={to} />;

export const Link = ({ to, children, ...rest }) => (
  <a href={to} {...rest}>
    {children}
  </a>
);

export const useNavigate = () => () => {};

let testLocation = { pathname: "/", search: "" };

/** Point useLocation at a specific location for the current test. */
export const setTestLocation = (location) => {
  testLocation = location;
};

export const useLocation = () => testLocation;
