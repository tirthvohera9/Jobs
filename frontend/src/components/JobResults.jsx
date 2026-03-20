import React, { useState } from 'react'
import { Search, Briefcase, AlertCircle } from 'lucide-react'
import JobCard from './JobCard'

export default function JobResults({ data, onRefineSearch }) {
  const { resume, jobs, search_query, search_location, total_jobs } = data
  const [filterText, setFilterText] = useState('')

  const filtered = filterText
    ? jobs.filter(j =>
        j.title.toLowerCase().includes(filterText.toLowerCase()) ||
        j.company.toLowerCase().includes(filterText.toLowerCase()) ||
        j.location.toLowerCase().includes(filterText.toLowerCase())
      )
    : jobs

  return (
    <div className="space-y-6">
      {/* Resume summary */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-lg text-gray-800">Resume Summary</h2>
          {resume.ai_powered && (
            <span className="text-xs bg-green-50 text-green-700 border border-green-200 px-2 py-0.5 rounded-full font-medium">
              ✦ AI-Powered Analysis
            </span>
          )}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-2 text-sm">
          {resume.name && (
            <div><span className="text-gray-500">Name:</span> <span className="font-medium">{resume.name}</span></div>
          )}
          {resume.email && (
            <div><span className="text-gray-500">Email:</span> <span className="font-medium">{resume.email}</span></div>
          )}
          {resume.domain && (
            <div>
              <span className="text-gray-500">Detected Industry:</span>{' '}
              <span className="font-medium capitalize">{resume.domain.replace(/_/g, ' ')}</span>
            </div>
          )}
          {resume.experience_level && (
            <div>
              <span className="text-gray-500">Experience Level:</span>{' '}
              <span className="font-medium capitalize">{resume.experience_level.replace(/_/g, ' ')}</span>
            </div>
          )}
          {resume.education?.length > 0 && (
            <div>
              <span className="text-gray-500">Education:</span>{' '}
              <span className="font-medium capitalize">{resume.education.slice(0, 3).join(', ')}</span>
            </div>
          )}
          {resume.job_titles?.length > 0 && (
            <div className="sm:col-span-2">
              <span className="text-gray-500">Detected Roles:</span>{' '}
              <span className="font-medium">{resume.job_titles.slice(0, 4).join(' · ')}</span>
            </div>
          )}
          {resume.search_queries?.length > 0 && (
            <div className="sm:col-span-2">
              <span className="text-gray-500">Searched For:</span>{' '}
              <span className="font-medium">{resume.search_queries.join(' · ')}</span>
            </div>
          )}
        </div>

        {resume.skills?.length > 0 && (
          <div className="mt-3">
            <p className="text-sm text-gray-500 mb-2">Detected Skills ({resume.skills.length})</p>
            <div className="flex flex-wrap gap-1.5">
              {resume.skills.map(skill => (
                <span key={skill} className="skill-badge">{skill}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Search meta */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="font-semibold text-lg text-gray-800">
            {total_jobs} Jobs Found
          </h2>
          <p className="text-sm text-gray-500">
            Searched: <span className="font-medium">"{search_query}"</span>
            {search_location && <> · <span className="font-medium">{search_location}</span></>}
          </p>
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

      {/* Job list */}
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
