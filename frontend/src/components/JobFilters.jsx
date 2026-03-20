import React, { useState } from 'react'
import { SlidersHorizontal, ChevronDown, ChevronUp, RotateCcw } from 'lucide-react'

// ── filter config ─────────────────────────────────────────────────────────────

const WORK_TYPES = [
  { value: 'remote',  label: 'Remote' },
  { value: 'hybrid',  label: 'Hybrid' },
  { value: 'on_site', label: 'On-site' },
]

const JOB_TYPES = [
  { value: 'full_time',  label: 'Full-time' },
  { value: 'part_time',  label: 'Part-time' },
  { value: 'contract',   label: 'Contract' },
  { value: 'internship', label: 'Internship' },
  { value: 'temporary',  label: 'Temporary' },
  { value: 'volunteer',  label: 'Volunteer' },
]

const EXP_LEVELS = [
  { value: 'internship', label: 'Internship' },
  { value: 'entry',      label: 'Entry level' },
  { value: 'associate',  label: 'Associate' },
  { value: 'mid_senior', label: 'Mid-Senior level' },
  { value: 'director',   label: 'Director' },
  { value: 'executive',  label: 'Executive' },
]

const DATE_OPTIONS = [
  { value: '',      label: 'Any time' },
  { value: 'month', label: 'Past month' },
  { value: 'week',  label: 'Past week' },
  { value: 'day',   label: 'Past 24 hours' },
]

const SORT_OPTIONS = [
  { value: 'relevant', label: 'Most relevant' },
  { value: 'recent',   label: 'Most recent' },
]

export const DEFAULT_FILTERS = {
  work_types: [],
  job_types: [],
  experience_levels: [],
  date_posted: '',
  easy_apply: false,
  sort_by: 'relevant',
}

function countActive(filters) {
  return (
    filters.work_types.length +
    filters.job_types.length +
    filters.experience_levels.length +
    (filters.date_posted ? 1 : 0) +
    (filters.easy_apply ? 1 : 0) +
    (filters.sort_by !== 'relevant' ? 1 : 0)
  )
}

// ── sub-components ────────────────────────────────────────────────────────────

function CheckGroup({ label, options, selected, onChange }) {
  const toggle = (val) =>
    onChange(selected.includes(val) ? selected.filter(v => v !== val) : [...selected, val])

  return (
    <div>
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{label}</p>
      <div className="flex flex-wrap gap-2">
        {options.map(opt => {
          const active = selected.includes(opt.value)
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => toggle(opt.value)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors duration-150
                ${active
                  ? 'bg-linkedin-blue text-white border-linkedin-blue'
                  : 'bg-white text-gray-600 border-gray-300 hover:border-linkedin-blue hover:text-linkedin-blue'
                }`}
            >
              {opt.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

function RadioGroup({ label, options, value, onChange }) {
  return (
    <div>
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{label}</p>
      <div className="flex flex-wrap gap-2">
        {options.map(opt => {
          const active = value === opt.value
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => onChange(opt.value)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors duration-150
                ${active
                  ? 'bg-linkedin-blue text-white border-linkedin-blue'
                  : 'bg-white text-gray-600 border-gray-300 hover:border-linkedin-blue hover:text-linkedin-blue'
                }`}
            >
              {opt.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ── main component ────────────────────────────────────────────────────────────

export default function JobFilters({ filters, onChange }) {
  const [open, setOpen] = useState(false)
  const active = countActive(filters)

  const update = (key, val) => onChange({ ...filters, [key]: val })
  const reset = () => onChange({ ...DEFAULT_FILTERS })

  return (
    <div className="card overflow-hidden">
      {/* Header / toggle */}
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="w-4 h-4 text-gray-500" />
          <span className="text-sm font-semibold text-gray-700">Filters</span>
          {active > 0 && (
            <span className="ml-1 inline-flex items-center justify-center w-5 h-5 rounded-full
                             bg-linkedin-blue text-white text-[10px] font-bold">
              {active}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {active > 0 && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); reset() }}
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-red-500 transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              Reset
            </button>
          )}
          {open ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
        </div>
      </button>

      {/* Filter body */}
      {open && (
        <div className="px-5 pb-5 border-t border-gray-100 space-y-5 pt-4">

          {/* Work setting */}
          <CheckGroup
            label="Work setting"
            options={WORK_TYPES}
            selected={filters.work_types}
            onChange={val => update('work_types', val)}
          />

          {/* Job type */}
          <CheckGroup
            label="Job type"
            options={JOB_TYPES}
            selected={filters.job_types}
            onChange={val => update('job_types', val)}
          />

          {/* Experience level */}
          <CheckGroup
            label="Experience level"
            options={EXP_LEVELS}
            selected={filters.experience_levels}
            onChange={val => update('experience_levels', val)}
          />

          {/* Date posted */}
          <RadioGroup
            label="Date posted"
            options={DATE_OPTIONS}
            value={filters.date_posted}
            onChange={val => update('date_posted', val)}
          />

          {/* Sort by */}
          <RadioGroup
            label="Sort by"
            options={SORT_OPTIONS}
            value={filters.sort_by}
            onChange={val => update('sort_by', val)}
          />

          {/* Easy Apply toggle */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
              Quick Apply
            </p>
            <button
              type="button"
              onClick={() => update('easy_apply', !filters.easy_apply)}
              className={`flex items-center gap-2.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors duration-150
                ${filters.easy_apply
                  ? 'bg-linkedin-blue text-white border-linkedin-blue'
                  : 'bg-white text-gray-600 border-gray-300 hover:border-linkedin-blue hover:text-linkedin-blue'
                }`}
            >
              <span className={`w-3.5 h-3.5 rounded-full border-2 flex items-center justify-center transition-colors
                ${filters.easy_apply ? 'border-white' : 'border-gray-400'}`}>
                {filters.easy_apply && <span className="w-1.5 h-1.5 rounded-full bg-white block" />}
              </span>
              Easy Apply only
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
