import { useState } from 'react'
import { Link } from 'react-router-dom'

const Navbar = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const userName = 'Apprenant' // Could be fetched from API

  const toggleMenu = () => setIsMenuOpen(!isMenuOpen)

  return (
    <nav className="navbar">
      <div className="navbar-logo">
        <span>SHELLFORGE</span>
      </div>
      <ul className="navbar-nav">
        <li>
          <Link to="/" className="nav-link">
            <span className="nav-icon">🏠</span>
            Accueil
          </Link>
        </li>
        <li>
          <Link to="/modules" className="nav-link">
            <span className="nav-icon">📚</span>
            Modules
          </Link>
        </li>
        <li>
          <Link to="/profile" className="nav-link">
            <span className="nav-icon">👤</span>
            Profil
          </Link>
        </li>
      </ul>
      <div className="navbar-actions">
        <button
          onClick={toggleMenu}
          className="btn btn-secondary"
          aria-label="Ouvrir le menu"
        >
          {isMenuOpen ? 'Fermer' : 'Menu'}
        </button>
      </div>
    </nav>
  )
}

export default Navbar