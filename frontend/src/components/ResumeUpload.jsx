import React, { useCallback, useState } from 'react'
import { Upload, FileText, X } from 'lucide-react'

export default function ResumeUpload({ onUpload, loading }) {
  const [dragOver, setDragOver] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const [location, setLocation] = useState('')

  const handleFile = useCallback((file) => {
    if (!file) return
    const ext = file.name.split('.').pop().toLowerCase()
    if (!['pdf', 'docx', 'doc', 'txt'].includes(ext)) {
      alert('Please upload a PDF, DOCX, or TXT file.')
      return
    }
    setSelectedFile(file)
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setDragOver(false)
    handleFile(e.dataTransfer.files?.[0])
  }, [handleFile])

  const handleInputChange = (e) => {
    handleFile(e.target.files?.[0])
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (selectedFile) {
      onUpload(selectedFile, location)
    }
  }

  const removeFile = () => setSelectedFile(null)

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`relative flex flex-col items-center justify-center border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors duration-200
          ${dragOver ? 'border-linkedin-blue bg-blue-50' : 'border-gray-300 hover:border-linkedin-blue hover:bg-gray-50'}`}
        onClick={() => !selectedFile && document.getElementById('resume-input').click()}
      >
        <input
          id="resume-input"
          type="file"
          accept=".pdf,.docx,.doc,.txt"
          className="hidden"
          onChange={handleInputChange}
        />

        {selectedFile ? (
          <div className="flex items-center gap-3">
            <FileText className="w-8 h-8 text-linkedin-blue flex-shrink-0" />
            <div className="text-left">
              <p className="font-semibold text-gray-800 truncate max-w-xs">{selectedFile.name}</p>
              <p className="text-sm text-gray-500">{(selectedFile.size / 1024).toFixed(0)} KB</p>
            </div>
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); removeFile() }}
              className="ml-2 p-1 rounded-full hover:bg-gray-200 text-gray-500"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <>
            <Upload className="w-12 h-12 text-gray-400 mb-3" />
            <p className="font-semibold text-gray-700">Drop your resume here</p>
            <p className="text-sm text-gray-500 mt-1">or click to browse</p>
            <p className="text-xs text-gray-400 mt-3">PDF, DOCX, DOC, TXT — max 5 MB</p>
          </>
        )}
      </div>

      {/* Location filter */}
      <div>
        <label htmlFor="location" className="block text-sm font-medium text-gray-700 mb-1">
          Preferred Location <span className="text-gray-400">(optional)</span>
        </label>
        <input
          id="location"
          type="text"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="e.g. San Francisco, Remote, United States"
          className="w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm
                     focus:outline-none focus:ring-2 focus:ring-linkedin-blue focus:border-transparent"
        />
      </div>

      <button
        type="submit"
        disabled={!selectedFile || loading}
        className="btn-primary w-full justify-center py-3"
      >
        {loading ? (
          <>
            <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
            </svg>
            Analyzing resume &amp; searching jobs…
          </>
        ) : (
          <>
            <Upload className="w-4 h-4" />
            Find Matching Jobs
          </>
        )}
      </button>
    </form>
  )
}
