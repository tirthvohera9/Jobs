import React, { useState } from 'react'
import { MapPin, Building2, Calendar, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react'

function timeAgo(dateStr) {
  if (!dateStr) return null
  const date = new Date(dateStr)
  const diffMs = Date.now() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays} days ago`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
  return `${Math.floor(diffDays / 30)} months ago`
}

export default function JobCard({ job, index }) {
  const [expanded, setExpanded] = useState(false)
  const postedLabel = timeAgo(job.posted_date)

  return (
    <div className="card p-5 hover:shadow-md transition-shadow duration-200">
      <div className="flex items-start gap-4">
        {/* Logo */}
        <div className="w-12 h-12 rounded-lg border border-gray-100 bg-gray-50 flex-shrink-0 overflow-hidden flex items-center justify-center">
          {job.logo_url ? (
            <img
              src={job.logo_url}
              alt={job.company}
              className="w-full h-full object-contain"
              onError={(e) => { e.target.style.display = 'none' }}
            />
          ) : (
            <Building2 className="w-6 h-6 text-gray-400" />
          )}
        </div>

        {/* Main info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="font-semibold text-gray-900 leading-tight">{job.title}</h3>
                {job.is_internship && (
                  <span className="text-xs bg-purple-50 text-purple-700 border border-purple-200 px-2 py-0.5 rounded-full font-medium">
                    Internship
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-600 mt-0.5">{job.company}</p>
            </div>
            <span className="text-xs font-semibold text-white bg-linkedin-blue px-2 py-0.5 rounded-full flex-shrink-0">
              #{index + 1}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-gray-500">
            {job.location && (
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5" />
                {job.location}
              </span>
            )}
            {postedLabel && (
              <span className="flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5" />
                {postedLabel}
              </span>
            )}
          </div>

          {/* Description toggle */}
          {job.description && (
            <div className="mt-3">
              <button
                onClick={() => setExpanded(!expanded)}
                className="flex items-center gap-1 text-xs text-linkedin-blue hover:underline"
              >
                {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                {expanded ? 'Hide description' : 'Show description'}
              </button>
              {expanded && (
                <p className="mt-2 text-sm text-gray-600 leading-relaxed whitespace-pre-wrap line-clamp-[12]">
                  {job.description}
                </p>
              )}
            </div>
          )}

          {/* Apply button */}
          {job.url && (
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 mt-3 text-sm font-medium text-linkedin-blue hover:text-linkedin-darkblue"
            >
              View on LinkedIn
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
        </div>
      </div>
    </div>
  )
}
