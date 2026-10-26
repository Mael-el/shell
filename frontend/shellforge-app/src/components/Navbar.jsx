import { Link, NavLink } from 'react-router-dom'

const Navbar = () => (
  <header className="topbar">
    <Link to="/" className="brand">
      <span className="brand-mark">›_</span>
      <span className="brand-text">
        SHELLFORGE
        <small>parcours offensif &amp; défensif</small>
      </span>
    </Link>
    <nav className="topnav">
      <NavLink to="/" end className="nav-link">
        Parcours
      </NavLink>
      <NavLink to="/progression" className="nav-link">
        Progression
      </NavLink>
      <a href="/docs" target="_blank" rel="noreferrer" className="nav-link nav-link-muted">
        API
      </a>
    </nav>
  </header>
)

export default Navbar
