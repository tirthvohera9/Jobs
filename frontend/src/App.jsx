import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { Briefcase, Search, ArrowLeft } from 'lucide-react'
import ResumeUpload from './components/ResumeUpload'
import JobResults from './components/JobResults'
import LinkedInSignIn from './components/LinkedInSignIn'
import JobFilters, { DEFAULT_FILTERS } from './components/JobFilters'

const API_BASE = import.meta.env.VITE_API_URL || ''

function readAuthFromUrl() {
  const params = new URLSearchParams(window.location.search)
  const token = params.get('access_token')
  const authError = params.get('auth_error')
  if (authError) return { error: decodeURIComponent(params.get('error_description') || authError) }
  if (token) return {
    access_token: token,
    name: decodeURIComponent(params.get('linkedin_name') || ''),
    email: decodeURIComponent(params.get('linkedin_email') || ''),
    picture: decodeURIComponent(params.get('linkedin_picture') || ''),
  }
  return null
}

function useLinkedInUser() {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem('linkedin_user') || 'null') }
    catch { return null }
  })
  const [authError, setAuthError] = useState(null)

  useEffect(() => {
    const parsed = readAuthFromUrl()
    if (!parsed) return
    if (parsed.error) {
      setAuthError(parsed.error)
    } else {
      setUser(parsed)
      sessionStorage.setItem('linkedin_user', JSON.stringify(parsed))
    }
    window.history.replaceState({}, '', window.location.pathname)
  }, [])

  const signOut = () => { setUser(null); sessionStorage.removeItem('linkedin_user') }
  return { user, signOut, authError, setAuthError }
}

function buildFilterParams(filters) {
  const p = new URLSearchParams()
  filters.job_types.forEach(v => p.append('job_types', v))
  filters.experience_levels.forEach(v => p.append('experience_levels', v))
  filters.work_types.forEach(v => p.append('work_types', v))
  if (filters.date_posted) p.set('date_posted', filters.date_posted)
  if (filters.easy_apply) p.set('easy_apply', 'true')
  if (filters.sort_by) p.set('sort_by', filters.sort_by)
  return p
}

export default function App() {
  const { user, signOut, authError, setAuthError } = useLinkedInUser()
  const [view, setView] = useState('upload')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [filters, setFilters] = useState(DEFAULT_FILTERS)

  // Direct search state
  const [searchKeywords, setSearchKeywords] = useState('')
  const [searchLocation, setSearchLocation] = useState('')
  const [searchLoading, setSearchLoading] = useState(false)

  // Last upload context for re-searching with new filters
  const [lastUpload, setLastUpload] = useState(null)

  const handleResumeUpload = async (file, location) => {
    setLoading(true)
    setError(null)
    setLastUpload({ type: 'resume', file, location })
    try {
      const formData = new FormData()
      formData.append('file', file)
      const params = new URLSearchParams({ max_results: 100, location: location || '' })
      if (user?.name) params.set('linkedin_name', user.name)
      buildFilterParams(filters).forEach((v, k) => params.set(k, v))

      const { data } = await axios.post(`${API_BASE}/api/parse-resume?${params}`, formData,
        { headers: { 'Content-Type': 'multipart/form-data' } })

      if (user && !data.resume.name) data.resume.name = user.name
      if (user && !data.resume.email) data.resume.email = user.email
      setResults(data)
      setView('results')
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleDirectSearch = async (e) => {
    e?.preventDefault()
    if (!searchKeywords.trim()) return
    setSearchLoading(true)
    setError(null)
    setLastUpload({ type: 'search', keywords: searchKeywords, location: searchLocation })
    try {
      const params = new URLSearchParams({
        keywords: searchKeywords,
        location: searchLocation,
        max_results: 50,
      })
      buildFilterParams(filters).forEach((v, k) => params.set(k, v))

      const { data } = await axios.get(`${API_BASE}/api/search-jobs?${params}`)
      setResults({ ...data, resume: { skills: [], job_titles: [], name: user?.name } })
      setView('results')
    } catch (err) {
      setError(err.response?.data?.detail || 'Search failed. Please try again.')
    } finally {
      setSearchLoading(false)
    }
  }

  // Re-run search when filters change (on results page)
  const handleFiltersChange = (newFilters) => {
    setFilters(newFilters)
  }

  const applyFilters = async () => {
    if (!lastUpload) return
    if (lastUpload.type === 'search') {
      await handleDirectSearch()
    } else if (lastUpload.type === 'resume') {
      await handleResumeUpload(lastUpload.file, lastUpload.location)
    }
  }

  const resetToUpload = () => {
    setView('upload'); setResults(null); setError(null)
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
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
              <button onClick={resetToUpload}
                className="flex items-center gap-1.5 text-sm text-gray-600 hover:text-linkedin-blue mr-1">
                <ArrowLeft className="w-4 h-4" />
                <span className="hidden sm:inline">New Search</span>
              </button>
            )}
            <LinkedInSignIn user={user} onSignOut={signOut} />
          </div>
        </div>
      </header>

      {authError && (
        <div className="bg-red-50 border-b border-red-200 px-4 py-2 text-sm text-red-700 flex items-center justify-between">
          <span>LinkedIn sign-in failed: {authError}</span>
          <button onClick={() => setAuthError(null)} className="ml-4 font-bold">✕</button>
        </div>
      )}

      {user && view === 'upload' && (
        <div className="bg-blue-50 border-b border-blue-100 px-4 py-2 text-sm text-blue-700 text-center">
          Signed in as <strong>{user.name}</strong> — your LinkedIn profile will enhance job matching
        </div>
      )}

      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-8">
        {view === 'upload' && (
          <div className="max-w-xl mx-auto">
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold text-gray-900 mb-2">Find Your Next Role</h2>
              <p className="text-gray-500 leading-relaxed">
                Upload your resume and we'll extract your skills, then search LinkedIn for
                matching opportunities — or sign in with LinkedIn for an enhanced experience.
              </p>
            </div>

            {/* Filters (on upload page) */}
            <div className="mb-4">
              <JobFilters filters={filters} onChange={setFilters} />
            </div>

            {/* Resume upload */}
            <div className="card p-6 mb-5">
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
                  <label className="block text-sm font-medium text-gray-700 mb-1">Job Title / Skills</label>
                  <input type="text" value={searchKeywords} onChange={e => setSearchKeywords(e.target.value)}
                    placeholder="e.g. React Developer, Data Scientist"
                    className="w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm
                               focus:outline-none focus:ring-2 focus:ring-linkedin-blue focus:border-transparent" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Location <span className="text-gray-400">(optional)</span>
                  </label>
                  <input type="text" value={searchLocation} onChange={e => setSearchLocation(e.target.value)}
                    placeholder="e.g. New York, Remote"
                    className="w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm
                               focus:outline-none focus:ring-2 focus:ring-linkedin-blue focus:border-transparent" />
                </div>
                <button type="submit" disabled={!searchKeywords.trim() || searchLoading}
                  className="btn-primary w-full justify-center py-2.5">
                  {searchLoading ? (
                    <><svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                    </svg>Searching…</>
                  ) : (
                    <><Search className="w-4 h-4" />Search Jobs</>
                  )}
                </button>
              </form>
            </div>

            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>
            )}
          </div>
        )}

        {view === 'results' && results && (
          <div className="space-y-5">
            {error && (
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>
            )}

            {/* Filters bar on results page */}
            <div>
              <JobFilters filters={filters} onChange={handleFiltersChange} />
              {/* Apply filters button */}
              <div className="mt-2 flex justify-end">
                <button
                  onClick={applyFilters}
                  disabled={loading || searchLoading}
                  className="btn-primary py-2 text-sm"
                >
                  {loading || searchLoading ? 'Searching…' : 'Apply Filters'}
                </button>
              </div>
            </div>

            <JobResults data={results} />
          </div>
        )}
      </main>

      <footer className="border-t border-gray-200 py-4 text-center text-xs text-gray-400">
        LinkedIn Job Finder · Uses LinkedIn's public job search · Not affiliated with LinkedIn
      </footer>
    </div>
  )
}
