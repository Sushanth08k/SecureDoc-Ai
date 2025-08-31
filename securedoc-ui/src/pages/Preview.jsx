import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { documentService } from '../services/api'

const Preview = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const fileId = searchParams.get('file')
  
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [documentData, setDocumentData] = useState(null)
  const [activeTab, setActiveTab] = useState('original')
  
  useEffect(() => {
    const fetchDocumentData = async () => {
      if (!fileId) {
        setError('No document ID provided')
        setIsLoading(false)
        return
      }
      
      try {
        const { data } = await documentService.getDocument(fileId)
        setDocumentData(data)
        
        // If there's a redacted version, show it by default
        if (data.redaction?.pdf?.path) {
          setActiveTab('redacted')
        }
      } catch (err) {
        console.error('Error fetching document:', err)
        setError(err.response?.data?.message || 'Failed to fetch document data')
      } finally {
        setIsLoading(false)
      }
    }
    
    fetchDocumentData()
  }, [fileId])

  const handleProcessNow = async () => {
    if (!fileId) return
    setIsLoading(true)
    setError(null)
    try {
      const { data } = await documentService.redactDocument(fileId)
      // Refetch to get updated state
      const refreshed = await documentService.getDocument(fileId)
      setDocumentData(refreshed.data)
      setActiveTab('redacted')
    } catch (err) {
      console.error('Error processing document:', err)
      setError(err.response?.data?.message || 'Failed to process document')
    } finally {
      setIsLoading(false)
    }
  }
  
  const renderDocumentPreview = (url, title) => {
    if (!url) return null
    
    // Check if it's a PDF
    if (url.toLowerCase().endsWith('.pdf')) {
      return (
        <iframe
          src={url}
          className="w-full h-full border-0 rounded-lg"
          title={title}
        />
      )
    }
    
    // For images
    return (
      <img
        src={url}
        alt={title}
        className="max-w-full max-h-full object-contain rounded-lg"
      />
    )
  }
  
  const handleDownload = (url, filename) => {
    const link = document.createElement('a')
    link.href = url
    link.download = filename || 'redacted-document'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-96 space-y-4">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary-200 border-t-primary-600"></div>
        <p className="text-gray-600">Loading document...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-error-50 border border-error-200 rounded-xl p-6">
          <div className="flex items-start">
            <svg className="w-6 h-6 text-error-400 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <div className="ml-3">
              <h3 className="text-lg font-medium text-error-800">Error Loading Document</h3>
              <p className="text-error-700 mt-1">{error}</p>
              <button
                onClick={() => navigate('/')}
                className="mt-3 text-sm text-error-600 hover:text-error-800 font-medium"
              >
                ← Return to Upload
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!documentData) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-warning-50 border border-warning-200 rounded-xl p-6">
          <div className="flex items-start">
            <svg className="w-6 h-6 text-warning-400 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <div className="ml-3">
              <h3 className="text-lg font-medium text-warning-800">No Document Data</h3>
              <p className="text-warning-700 mt-1">The requested document could not be found.</p>
              <button
                onClick={() => navigate('/')}
                className="mt-3 text-sm text-warning-600 hover:text-warning-800 font-medium"
              >
                ← Return to Upload
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Extract paths from document data
  const originalPath = documentData.original_path || ''
  const redactedPath = documentData.redaction?.pdf?.path || ''
  const hasRedactedVersion = !!redactedPath
  
  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-white rounded-2xl shadow-card border border-gray-200 p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center space-x-3 mb-2">
              <div className="w-10 h-10 bg-primary-100 rounded-xl flex items-center justify-center">
                <svg className="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  {documentData.filename || 'Document Preview'}
                </h1>
                <div className="flex items-center space-x-4 mt-1">
                  <span className="text-sm text-gray-500">
                    Uploaded: {formatDate(documentData.upload_date)}
                  </span>
                  {documentData.status && (
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      documentData.status === 'success' 
                        ? 'bg-success-100 text-success-800'
                        : documentData.status === 'error'
                        ? 'bg-error-100 text-error-800'
                        : 'bg-warning-100 text-warning-800'
                    }`}>
                      {documentData.status}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            {!hasRedactedVersion && (
              <button
                onClick={handleProcessNow}
                className="inline-flex items-center px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 transition-colors duration-200"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Process Now (Redact)
              </button>
            )}
            {hasRedactedVersion && (
              <button
                onClick={() => handleDownload(redactedPath, `${fileId}_redacted.pdf`)}
                className="inline-flex items-center px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 transition-colors duration-200"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Download Redacted
              </button>
            )}
            <button
              onClick={() => navigate('/')}
              className="inline-flex items-center px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors duration-200"
            >
              ← Upload New Document
            </button>
          </div>
        </div>
      </div>

      {/* Document Viewer */}
      <div className="bg-white rounded-2xl shadow-card border border-gray-200 overflow-hidden">
        {/* Tab Navigation */}
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8 px-6" aria-label="Tabs">
            <button
              onClick={() => setActiveTab('original')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors duration-200 ${
                activeTab === 'original'
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Original Document
            </button>
            {hasRedactedVersion && (
              <button
                onClick={() => setActiveTab('redacted')}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors duration-200 ${
                  activeTab === 'redacted'
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                Redacted Document
                <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800">
                  Secure
                </span>
              </button>
            )}
          </nav>
        </div>
        
        {/* Document Display */}
        <div className="p-6">
          <div className="bg-gray-50 rounded-xl border-2 border-dashed border-gray-200 h-128 overflow-hidden">
            {activeTab === 'original' && originalPath ? (
              renderDocumentPreview(originalPath, 'Original Document')
            ) : activeTab === 'redacted' && hasRedactedVersion ? (
              renderDocumentPreview(redactedPath, 'Redacted Document')
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-gray-500">
                <svg className="w-16 h-16 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="text-lg font-medium">Document not available</p>
                <p className="text-sm">The {activeTab} version of this document could not be loaded.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Processing Results */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* PII Detection Results */}
        {documentData.pii && (
          <div className="bg-white rounded-2xl shadow-card border border-gray-200 p-6">
            <div className="flex items-center space-x-3 mb-4">
              <div className="w-8 h-8 bg-accent-100 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-accent-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900">PII Detection Results</h3>
            </div>
            
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-500 mb-1">Total Entities</p>
                <p className="text-2xl font-bold text-gray-900">{documentData.pii.entity_count || 0}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-sm text-gray-500 mb-1">Sensitivity Level</p>
                <p className={`text-2xl font-bold capitalize ${
                  documentData.pii.sensitivity === 'high' ? 'text-error-600' :
                  documentData.pii.sensitivity === 'medium' ? 'text-warning-600' :
                  'text-success-600'
                }`}>
                  {documentData.pii.sensitivity || 'Low'}
                </p>
              </div>
            </div>
            
            {documentData.pii.entity_types && documentData.pii.entity_types.length > 0 && (
              <div>
                <p className="text-sm text-gray-500 mb-3">Detected Entity Types</p>
                <div className="flex flex-wrap gap-2">
                  {documentData.pii.entity_types.map((type, index) => (
                    <span 
                      key={index}
                      className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-accent-100 text-accent-800"
                    >
                      {type}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
        
        {/* Redaction Statistics */}
        {documentData.redaction && (
          <div className="bg-white rounded-2xl shadow-card border border-gray-200 p-6">
            <div className="flex items-center space-x-3 mb-4">
              <div className="w-8 h-8 bg-primary-100 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900">Redaction Statistics</h3>
            </div>
            
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-gray-50 rounded-lg p-4 text-center">
                <p className="text-sm text-gray-500 mb-1">Pages</p>
                <p className="text-2xl font-bold text-gray-900">{documentData.redaction.pages || 0}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 text-center">
                <p className="text-sm text-gray-500 mb-1">Redactions</p>
                <p className="text-2xl font-bold text-gray-900">{documentData.redaction.total_redactions || 0}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 text-center">
                <p className="text-sm text-gray-500 mb-1">Status</p>
                <p className={`text-lg font-bold capitalize ${
                  documentData.redaction.status === 'success' ? 'text-success-600' :
                  documentData.redaction.status === 'error' ? 'text-error-600' :
                  'text-warning-600'
                }`}>
                  {documentData.redaction.status || 'Unknown'}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Preview
