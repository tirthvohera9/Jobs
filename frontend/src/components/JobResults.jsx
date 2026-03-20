import React, { useState } from 'react'
import { Search, Briefcase, GraduationCap, Lightbulb, Target, AlertCircle } from 'lucide-react'
import JobCard from './JobCard'

export default function JobResults({ data, onRefineSearch }) {
  const { resume, jobs, search_location, total_jobs, jobs_count, internships_count } = data
  const [filterText, setFilterText] = useState('')
  const [tab, setTab] = useState('all') // 'all' | 'jobs' | 'internships'

  const tabFiltered = tab === 'jobs'
    ? jobs.filter(j => !j.is_internship)
    : tab === 'internships'
      ? jobs.filter(j => j.is_internship)
      : jobs

  const filtered = filterText
    ? tabFiltered.filter(j =>
        (j.title || '').toLowerCase().includes(filterText.toLowerCase()) ||
        (j.company || '').toLowerCase().includes(filterText.toLowerCase()) ||
        (j.location || '').toLowerCase().includes(filterText.toLowerCase())
      )
    : tabFiltered

  const hasNotes = resume.notes && Object.keys(resume.notes).some(k => resume.notes[k])

  return (
    <div className="space-y-5">
      {/* ── AI Resume Analysis Card ─────────────────────────────────── */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-lg text-gray-800">Resume Analysis</h2>
          {resume.ai_powered && (
            <span className="text-xs bg-green-50 text-green-700 border border-green-200 px-2 py-0.5 rounded-full font-medium">
              ✦ AI-Powered
            </span>
          )}
        </div>

        {/* Candidate summary */}
        {resume.candidate_summary && (
          <div className="mb-4 p-3 bg-blue-50 border border-blue-100 rounded-lg">
            <p className="text-sm text-gray-700 leading-relaxed">{resume.candidate_summary}</p>
          </div>
        )}

        {/* AI Notes */}
        {hasNotes && (
          <div className="mb-4 space-y-2">
            {resume.notes.education && (
              <div className="flex items-start gap-2 text-sm">
                <GraduationCap className="w-4 h-4 text-linkedin-blue mt-0.5 flex-shrink-0" />
                <span className="text-gray-700">{resume.notes.education}</span>
              </div>
            )}
            {resume.notes.top_skills && (
              <div className="flex items-start gap-2 text-sm">
                <Lightbulb className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
                <span className="text-gray-700">{resume.notes.top_skills}</span>
              </div>
            )}
            {resume.notes.career_stage && (
              <div className="flex items-start gap-2 text-sm">
                <Target className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                <span className="text-gray-700">{resume.notes.career_stage}</span>
              </div>
            )}
          </div>
        )}

        {/* Basic fields */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-1.5 text-sm">
          {resume.name && (
            <div><span className="text-gray-500">Name:</span> <span className="font-medium">{resume.name}</span></div>
          )}
          {resume.domain && (
            <div>
              <span className="text-gray-500">Industry:</span>{' '}
              <span className="font-medium capitalize">{resume.domain.replace(/_/g, ' ')}</span>
            </div>
          )}
          {resume.experience_level && (
            <div>
              <span className="text-gray-500">Level:</span>{' '}
              <span className="font-medium capitalize">{resume.experience_level.replace(/_/g, ' ')}</span>
            </div>
          )}
          {resume.education?.length > 0 && (
            <div>
              <span className="text-gray-500">Education:</span>{' '}
              <span className="font-medium capitalize">{resume.education.slice(0, 2).join(', ')}</span>
            </div>
          )}
          {resume.job_titles?.length > 0 && (
            <div className="sm:col-span-2">
              <span className="text-gray-500">Target Roles:</span>{' '}
              <span className="font-medium">{resume.job_titles.slice(0, 4).join(' · ')}</span>
            </div>
          )}
          {resume.job_queries?.length > 0 && (
            <div className="sm:col-span-2">
              <span className="text-gray-500">Job Searches:</span>{' '}
              <span className="font-medium">{resume.job_queries.join(' · ')}</span>
            </div>
          )}
          {resume.internship_queries?.length > 0 && (
            <div className="sm:col-span-2">
              <span className="text-gray-500">Internship Searches:</span>{' '}
              <span className="font-medium">{resume.internship_queries.join(' · ')}</span>
            </div>
          )}
        </div>

        {/* Skills */}
        {resume.skills?.length > 0 && (
          <div className="mt-3">
            <p className="text-sm text-gray-500 mb-2">Skills ({resume.skills.length})</p>
            <div className="flex flex-wrap gap-1.5">
              {resume.skills.map(skill => (
                <span key={skill} className="skill-badge">{skill}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Results header + tabs ────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="font-semibold text-lg text-gray-800">
            {jobs_count > 0 && (
              <span>{jobs_count} Job{jobs_count !== 1 ? 's' : ''}</span>
            )}
            {jobs_count > 0 && internships_count > 0 && (
              <span className="text-gray-400 mx-1">+</span>
            )}
            {internships_count > 0 && (
              <span>{internships_count} Internship{internships_count !== 1 ? 's' : ''}</span>
            )}
            {!jobs_count && !internships_count && (
              <span>{total_jobs} Results</span>
            )}
            {' '}Found
          </h2>
          {search_location && (
            <p className="text-sm text-gray-500">in <span className="font-medium">{search_location}</span></p>
          )}
        </div>

        {/* Inline filter */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            placeholder="Filter results…"
            className="pl-9 pr-4 py-2 text-sm border border-gray-300 rounded-lg
                       focus:outline-none focus:ring-2 focus:ring-linkedin-blue focus:border-transparent"
          />
        </div>
      </div>

      {/* Tabs: All / Jobs / Internships */}
      {internships_count > 0 && jobs_count > 0 && (
        <div className="flex gap-2">
          {[
            { key: 'all',          label: `All (${total_jobs})` },
            { key: 'jobs',         label: `Jobs (${jobs_count})` },
            { key: 'internships',  label: `Internships (${internships_count})` },
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                tab === key
                  ? 'bg-linkedin-blue text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      )}

      {/* ── Job list ────────────────────────────────────────────────── */}
      {filtered.length > 0 ? (
        <div className="space-y-3">
          {filtered.map((job, i) => (
            <JobCard key={job.id || i} job={job} index={i} />
          ))}
        </div>
      ) : (
        <div className="card p-10 text-center">
          <AlertCircle className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">
            {jobs.length === 0
              ? 'No jobs found. LinkedIn may be rate-limiting requests. Try again in a moment.'
              : 'No jobs match your filter.'}
          </p>
        </div>
      )}
    </div>
  )
}
