import { Outlet, Link } from "react-router-dom";
import "./AuthLayout.css";

export function AuthLayout() {
  return (
    <div className="nl-auth">
      <div className="nl-auth__panel">
        <div className="nl-auth__intro">
          <h1 className="nl-auth__brand">NeighbourLink</h1>
          <p className="nl-auth__tagline">Your neighbourhood, connected.</p>
          <p className="nl-auth__blurb">
            Rent useful items from neighbours and find dependable local help — one trusted account for rentals and
            assistance.
          </p>
        </div>
        <div className="nl-auth__card">
          <Outlet />
          <p className="nl-auth__switch">
            <Link to="/login">Sign in</Link>
            <span aria-hidden="true"> · </span>
            <Link to="/register">Create account</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
