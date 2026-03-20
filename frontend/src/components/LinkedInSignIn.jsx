import React from 'react'
import { Linkedin } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_URL || ''

export default function LinkedInSignIn({ user, onSignOut }) {
  const handleSignIn = () => {
    // Redirect to backend OAuth endpoint which proxies to LinkedIn
    window.location.href = `${API_BASE}/api/auth/linkedin/login`
  }

  if (user) {
    return (
      <div className="flex items-center gap-3">
        {user.picture && (
          <img
            src={user.picture}
            alt={user.name}
            className="w-8 h-8 rounded-full border-2 border-linkedin-blue object-cover"
          />
        )}
        <div className="text-sm leading-tight hidden sm:block">
          <p className="font-semibold text-gray-800">{user.name}</p>
          {user.email && <p className="text-gray-400 text-xs">{user.email}</p>}
        </div>
        <button
          onClick={onSignOut}
          className="text-xs text-gray-500 hover:text-red-500 transition-colors underline"
        >
          Sign out
        </button>
      </div>
    )
  }

  return (
    <button
      onClick={handleSignIn}
      className="flex items-center gap-2 px-4 py-2 rounded-lg border-2 border-linkedin-blue
                 text-linkedin-blue font-semibold text-sm hover:bg-linkedin-blue hover:text-white
                 transition-colors duration-200"
    >
      <Linkedin className="w-4 h-4" />
      Sign in with LinkedIn
    </button>
  )
}
