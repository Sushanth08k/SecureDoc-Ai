import { useState, useRef } from 'react'
import { documentService } from '../services/api'
import { useNavigate } from 'react-router-dom'

const Upload = () => {
  const [file, setFile] = useState(null)
  const [processMode, setProcessMode] = useState('ocr')
  const [isUploading, setIsUploading] = useState(false)
  const [response, setResponse] = useState(null)
  const [error, setError] = useState(null)
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef(null)
  
  const navigate = useNavigate()

  const processingOptions = [
    {
      value: 'ocr',
      label: 'OCR Only',
      description: 'Extract text from your document using optical character recognition',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      )
    },
    {
      value: 'pii',
      label: 'PII Detection',
      description: 'Extract text and identify personally identifiable information',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      )
    },
    {
      value: 'redact',
      label: 'Full Redaction',
      description: 'Complete document processing with PII redaction and secure output',
      icon: (
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
      )
    }
  ]

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelection(e.dataTransfer.files[0])
    }
  }

  // Make entire drop zone clickable & keyboard accessible
  const openFileDialog = () => {
    fileInputRef.current?.click()
  }

  const handleZoneKeyDown = (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      openFileDialog()
    }
  }

  const handleFileSelection = (selectedFile) => {
    const validTypes = ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png', 'image/tiff']
    const maxSize = 10 * 1024 * 1024 // 10MB
    
    if (!validTypes.includes(selectedFile.type)) {
      setError('Please select a valid file type (PDF, JPG, PNG, TIFF)')
      return
    }
    
    if (selectedFile.size > maxSize) {
      setError('File size must be less than 10MB')
      return
    }
    
    setFile(selectedFile)
    setError(null)
    setResponse(null)
  }

  const handleFileChange = (e) => {
    if (e.target.files.length > 0) {
      handleFileSelection(e.target.files[0])
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!file) {
      setError('Please select a file to upload')
      return
    }
    
    setIsUploading(true)
    setError(null)
    setResponse(null)
    
    try {
      let params = {}
      switch (processMode) {
        case 'ocr':
          params = { ocr: true, detect_pii: false, analyze_layout: false }
          break
        case 'pii':
          params = { ocr: true, detect_pii: true, analyze_layout: false }
          break
        case 'redact':
          // Run full processing on upload; redaction action can follow in preview using document_id
          params = { ocr: true, detect_pii: true, analyze_layout: true }
          break
        default:
          params = { ocr: true, detect_pii: false, analyze_layout: false }
      }

      const { data } = await documentService.uploadDocument(file, params)
      setResponse(data)

      if (processMode === 'redact' && data.document_id) {
        setTimeout(() => {
          navigate(`/preview?file=${data.document_id}`)
        }, 800)
      }
    } catch (err) {
      console.error('Error uploading document:', err)
      setError(err.response?.data?.message || 'Failed to upload document')
    } finally {
      setIsUploading(false)
    }
  }

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          Secure Document Processing
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          Upload your documents for secure text extraction, PII detection, and redaction using advanced AI technology.
        </p>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Upload Section */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-2xl shadow-card border border-gray-200 overflow-hidden">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Upload Document</h2>
              <p className="text-gray-600">Select a file to begin processing</p>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6 space-y-6">
              {/* File Upload Area */}
              <div
                className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-all duration-300 ${
                  dragActive
                    ? 'border-primary-400 bg-primary-50'
                    : file
                    ? 'border-success-300 bg-success-50'
                    : 'border-gray-300 hover:border-gray-400 bg-gray-50'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={openFileDialog}
                onKeyDown={handleZoneKeyDown}
                role="button"
                tabIndex={0}
                aria-label="File upload area. Click or press Enter/Space, or drag and drop to upload a file."
                aria-describedby="upload-hint"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  className="sr-only"
                  accept=".pdf,.jpg,.jpeg,.png,.tiff"
                  onChange={handleFileChange}
                />
                
                {file ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-center w-16 h-16 mx-auto bg-success-100 rounded-full">
                      <svg className="w-8 h-8 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-lg font-medium text-gray-900">{file.name}</p>
                      <p className="text-gray-500">{formatFileSize(file.size)}</p>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); openFileDialog() }}
                      className="text-sm text-primary-600 hover:text-primary-700 font-medium"
                    >
                      Choose a different file
                    </button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="flex items-center justify-center w-16 h-16 mx-auto bg-gray-100 rounded-full">
                      <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                    </div>
                    <div>
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); openFileDialog() }}
                        className="text-primary-600 hover:text-primary-700 font-medium"
                      >
                        Click to upload
                      </button>
                      <span id="upload-hint" className="text-gray-500"> or drag and drop</span>
                    </div>
                    <p className="text-sm text-gray-500">
                      PDF, PNG, JPG, TIFF up to 10MB
                    </p>
                  </div>
                )}
              </div>

              {/* Processing Mode */}
              <div>
                <label className="block text-sm font-medium text-gray-900 mb-3">
                  Processing Mode
                </label>
                <div className="space-y-3">
                  {processingOptions.map((option) => (
                    <label
                      key={option.value}
                      className={`relative flex items-start p-4 border rounded-xl cursor-pointer transition-all duration-200 ${
                        processMode === option.value
                          ? 'border-primary-300 bg-primary-50 shadow-sm'
                          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      <input
                        type="radio"
                        name="processMode"
                        value={option.value}
                        checked={processMode === option.value}
                        onChange={(e) => setProcessMode(e.target.value)}
                        className="sr-only"
                      />
                      <div className="flex items-start space-x-3 flex-1">
                        <div className={`flex-shrink-0 p-2 rounded-lg ${
                          processMode === option.value ? 'bg-primary-100 text-primary-600' : 'bg-gray-100 text-gray-400'
                        }`}>
                          {option.icon}
                        </div>
                        <div>
                          <h3 className={`font-medium ${
                            processMode === option.value ? 'text-primary-900' : 'text-gray-900'
                          }`}>
                            {option.label}
                          </h3>
                          <p className="text-sm text-gray-500 mt-1">
                            {option.description}
                          </p>
                        </div>
                      </div>
                      {processMode === option.value && (
                        <div className="flex-shrink-0">
                          <div className="w-5 h-5 bg-primary-600 rounded-full flex items-center justify-center">
                            <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                            </svg>
                          </div>
                        </div>
                      )}
                    </label>
                  ))}
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={!file || isUploading}
                aria-busy={isUploading}
                aria-label={isUploading ? 'Processing document' : file ? 'Upload and process selected document' : 'Select a file to enable processing'}
                className={`group w-full flex items-center justify-center px-6 py-5 rounded-2xl transition-all duration-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 ${
                  !file || isUploading
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-gradient-to-r from-primary-600 to-accent-600 text-white shadow-lg shadow-primary-600/20 hover:shadow-xl hover:-translate-y-0.5 active:translate-y-0 ring-1 ring-white/10'
                }`}
              >
                {isUploading ? (
                  <div className="flex items-center">
                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-current" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <div className="text-left">
                      <div className="font-semibold">Processing document…</div>
                      <div className="text-xs opacity-90">This may take a few seconds</div>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center">
                    <div className="mr-3 flex h-9 w-9 items-center justify-center rounded-full bg-white/10 group-hover:bg-white/15">
                      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                    </div>
                    <div className="text-left">
                      <div className="text-base font-semibold leading-tight">Upload & Process</div>
                      <div className="text-xs opacity-90 leading-tight">OCR, PII detection, and redaction per your selection</div>
                    </div>
                  </div>
                )}
              </button>

              {/* CTA helper */}
              <p className="text-xs text-gray-500 text-center -mt-1">
                {file ? 'Ready to go. Click the button above to start.' : 'Choose or drop a file to enable the Process button.'}
              </p>
            </form>
          </div>
        </div>

        {/* Info Panel */}
        <div className="space-y-6">
          <div className="bg-gradient-to-br from-primary-50 to-accent-50 rounded-2xl p-6 border border-primary-100">
            <h3 className="text-lg font-semibold text-primary-900 mb-4">Security Features</h3>
            <div className="space-y-3">
              <div className="flex items-start space-x-3">
                <div className="w-5 h-5 bg-primary-600 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                  <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-medium text-primary-800">End-to-End Encryption</p>
                  <p className="text-xs text-primary-600">Your documents are encrypted during upload and processing</p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <div className="w-5 h-5 bg-primary-600 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                  <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-medium text-primary-800">AI-Powered PII Detection</p>
                  <p className="text-xs text-primary-600">Advanced machine learning identifies sensitive information</p>
                </div>
              </div>
              <div className="flex items-start space-x-3">
                <div className="w-5 h-5 bg-primary-600 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                  <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </div>
                <div>
                  <p className="text-sm font-medium text-primary-800">Audit Trail</p>
                  <p className="text-xs text-primary-600">Complete processing history and compliance tracking</p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Supported Formats</h3>
            <div className="grid grid-cols-2 gap-3">
              {[
                { name: 'PDF', icon: '📄' },
                { name: 'JPEG', icon: '🖼️' },
                { name: 'PNG', icon: '🖼️' },
                { name: 'TIFF', icon: '🖼️' }
              ].map((format) => (
                <div key={format.name} className="flex items-center space-x-2 p-2 bg-gray-50 rounded-lg">
                  <span className="text-lg">{format.icon}</span>
                  <span className="text-sm font-medium text-gray-700">{format.name}</span>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-3">Maximum file size: 10MB</p>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-error-50 border border-error-200 rounded-xl p-4 animate-slide-down">
          <div className="flex items-start">
            <svg className="w-5 h-5 text-error-400 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-error-800">Upload Error</h3>
              <p className="text-sm text-error-700 mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}

  {/* Success Response */}
  {response && (response.status === 'success' || response.status === 'uploaded') && (
        <div className="bg-success-50 border border-success-200 rounded-xl p-6 animate-slide-down">
          <div className="flex items-start">
            <svg className="w-6 h-6 text-success-400 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <div className="ml-3 flex-1">
              <h3 className="text-lg font-medium text-success-800">Processing Complete!</h3>
              <p className="text-success-700 mt-1">Your document has been successfully processed.</p>
              
              {processMode === 'redact' && response.document_id && (
                <div className="mt-4">
                  <button
                    onClick={() => navigate(`/preview?file=${response.document_id}`)}
                    className="inline-flex items-center px-4 py-2 bg-success-600 text-white text-sm font-medium rounded-lg hover:bg-success-700 transition-colors duration-200"
                  >
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                    View Redacted Document
                  </button>
                </div>
              )}
              
              {/* Show response details in a collapsible section */}
              <details className="mt-4">
                <summary className="text-sm text-success-600 cursor-pointer hover:text-success-800 font-medium">
                  View processing details
                </summary>
                <div className="mt-2 p-3 bg-white rounded-lg border border-success-200">
                  <pre className="text-xs text-gray-600 overflow-auto">
                    {JSON.stringify(response, null, 2)}
                  </pre>
                </div>
              </details>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Upload
