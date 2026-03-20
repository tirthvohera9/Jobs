import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { Briefcase, Search, ArrowLeft } from 'lucide-react'
import ResumeUpload from './components/ResumeUpload'
import JobResults from './components/JobResults'
import LinkedInSignIn from './components/LinkedInSignIn'

const API_BASE = import.meta.env.VITE_API_URL || ''

/**
 * Read LinkedIn auth params from the URL (set after OAuth callback redirect).
 * Returns { access_token, name, email, picture } or null.
 */
function readAuthFromUrl() {
  const params = new URLSearchParams(window.location.search)
  const token = params.get('access_token')
  const authError = params.get('auth_error')

  if (authError) {
    return { error: decodeURIComponent(params.get('error_description') || authError) }
  }

  if (token) {
    return {
      access_token: token,
      name: decodeURIComponent(params.get('linkedin_name') || ''),
      email: decodeURIComponent(params.get('linkedin_email') || ''),
      picture: decodeURIComponent(params.get('linkedin_picture') || ''),
    }
  }

  return null
}

function useLinkedInUser() {
  const [user, setUser] = useState(() => {
    try {
      const stored = sessionStorage.getItem('linkedin_user')
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  })

  const [authError, setAuthError] = useState(null)

  useEffect(() => {
    const parsed = readAuthFromUrl()
    if (parsed?.error) {
      setAuthError(parsed.error)
      window.history.replaceState({}, '', window.location.pathname)
      return
    }
    if (parsed?.access_token) {
      const userObj = {
        access_token: parsed.access_token,
        name: parsed.name,
        email: parsed.email,
        picture: parsed.picture,
      }
      setUser(userObj)
      sessionStorage.setItem('linkedin_user', JSON.stringify(userObj))
      // Clean up URL
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [])

  const signOut = () => {
    setUser(null)
    sessionStorage.removeItem('linkedin_user')
  }

  return { user, signOut, authError, setAuthError }
}


export default function App() {
  const { user, signOut, authError, setAuthError } = useLinkedInUser()
  const [view, setView] = useState('upload')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Direct search state
  const [searchKeywords, setSearchKeywords] = useState('')
  const [searchLocation, setSearchLocation] = useState('')
  const [searchLoading, setSearchLoading] = useState(false)

  const handleResumeUpload = async (file, location) => {
    setLoading(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const params = new URLSearchParams({ max_results: 20 })
      if (location) params.append('location', location)
      if (user?.name) params.append('linkedin_name', user.name)

      const headers = { 'Content-Type': 'multipart/form-data' }
      if (user?.access_token) {
        headers['X-LinkedIn-Token'] = user.access_token
      }

      const { data } = await axios.post(
        `${API_BASE}/api/parse-resume?${params}`,
        formData,
        { headers }
      )

      // If signed in, enrich with LinkedIn profile data
      if (user && !data.resume.name) {
        data.resume.name = user.name
        data.resume.email = data.resume.email || user.email
      }

      setResults(data)
      setView('results')
    } catch (err) {
      const msg = err.response?.data?.detail || 'Something went wrong. Please try again.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const handleDirectSearch = async (e) => {
    e.preventDefault()
    if (!searchKeywords.trim()) return
    setSearchLoading(true)
    setError(null)
    try {
      const { data } = await axios.get(`${API_BASE}/api/search-jobs`, {
        params: { keywords: searchKeywords, location: searchLocation, max_results: 20 },
      })
      setResults({ ...data, resume: { skills: [], job_titles: [], name: user?.name } })
      setView('results')
    } catch (err) {
      const msg = err.response?.data?.detail || 'Search failed. Please try again.'
      setError(msg)
    } finally {
      setSearchLoading(false)
    }
  }

  const resetToUpload = () => {
    setView('upload')
    setResults(null)
    setError(null)
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <button onClick={resetToUpload} className="flex items-center gap-2.5 hover:opacity-80 transition-opacity">
            <div className="w-9 h-9 bg-linkedin-blue rounded-lg flex items-center justify-center">
              <Briefcase className="w-5 h-5 text-white" />
            </div>
            <div className="text-left">
              <p className="font-bold text-gray-900 text-sm leading-tight">LinkedIn Job Finder</p>
              <p className="text-xs text-gray-400 leading-tight">Resume-Powered Search</p>
            </div>
          </button>

          <div className="flex items-center gap-3">
            {view === 'results' && (
              <button
                onClick={resetToUpload}
                className="flex items-center gap-1.5 text-sm text-gray-600 hover:text-linkedin-blue mr-2"
              >
                <ArrowLeft className="w-4 h-4" />
                <span className="hidden sm:inline">New Search</span>
              </button>
            )}
            <LinkedInSignIn user={user} onSignOut={signOut} />
          </div>
        </div>
      </header>

      {/* Auth error banner */}
      {authError && (
        <div className="bg-red-50 border-b border-red-200 px-4 py-2 text-sm text-red-700 flex items-center justify-between">
          <span>LinkedIn sign-in failed: {authError}</span>
          <button onClick={() => setAuthError(null)} className="ml-4 font-bold">✕</button>
        </div>
      )}

      {/* LinkedIn connected banner */}
      {user && view === 'upload' && (
        <div className="bg-blue-50 border-b border-blue-100 px-4 py-2 text-sm text-blue-700 text-center">
          Signed in as <strong>{user.name}</strong> — your LinkedIn profile will enhance job matching
        </div>
      )}

      {/* Main content */}
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-8">
        {view === 'upload' && (
          <div className="max-w-xl mx-auto">
            {/* Hero */}
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold text-gray-900 mb-2">Find Your Next Role</h2>
              <p className="text-gray-500 leading-relaxed">
                Upload your resume and we'll extract your skills, then search LinkedIn for
                matching opportunities — or sign in with LinkedIn for an enhanced experience.
              </p>
            </div>

            {/* Upload card */}
            <div className="card p-6 mb-6">
              <h3 className="font-semibold text-gray-800 mb-4">
                {user ? `Hi ${user.name?.split(' ')[0]}, upload your resume` : 'Upload Your Resume'}
              </h3>
              <ResumeUpload onUpload={handleResumeUpload} loading={loading} />
            </div>

            {/* Divider */}
            <div className="flex items-center gap-3 my-5">
              <div className="flex-1 h-px bg-gray-200" />
              <span className="text-xs text-gray-400 font-medium">OR SEARCH DIRECTLY</span>
              <div className="flex-1 h-px bg-gray-200" />
            </div>

            {/* Manual search */}
            <div className="card p-6">
              <form onSubmit={handleDirectSearch} className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Job Title / Skills
                  </label>
                  <input
                    type="text"
                    value={searchKeywords}
                    onChange={(e) => setSearchKeywords(e.target.value)}
                    placeholder="e.g. React Developer, Data Scientist"
                    className="w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm
                               focus:outline-none focus:ring-2 focus:ring-linkedin-blue focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Location <span className="text-gray-400">(optional)</span>
                  </label>
                  <input
                    type="text"
                    value={searchLocation}
                    onChange={(e) => setSearchLocation(e.target.value)}
                    placeholder="e.g. New York, Remote"
                    className="w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm
                               focus:outline-none focus:ring-2 focus:ring-linkedin-blue focus:border-transparent"
                  />
                </div>
                <button
                  type="submit"
                  disabled={!searchKeywords.trim() || searchLoading}
                  className="btn-primary w-full justify-center py-2.5"
                >
                  {searchLoading ? (
                    <>
                      <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                      </svg>
                      Searching…
                    </>
                  ) : (
                    <>
                      <Search className="w-4 h-4" />
                      Search Jobs
                    </>
                  )}
                </button>
              </form>
            </div>

            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                {error}
              </div>
            )}
          </div>
        )}

        {view === 'results' && results && (
          <>
            {error && (
              <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                {error}
              </div>
            )}
            <JobResults data={results} />
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 py-4 text-center text-xs text-gray-400">
        LinkedIn Job Finder · Uses LinkedIn's public job search · Not affiliated with LinkedIn
      </footer>
    </div>
  )
}
