// Minimal react-router-dom stub for tests: the real package is ESM-only and
// jest's resolver (CRA) cannot locate it. Extend only as tests require.
export const Navigate = ({ to }) => <div data-testid="navigate" data-to={to} />;

export const Link = ({ to, children, ...rest }) => (
  <a href={to} {...rest}>
    {children}
  </a>
);

export const useNavigate = () => () => {};

export const useLocation = () => ({ pathname: "/" });
