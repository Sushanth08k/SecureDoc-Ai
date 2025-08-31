import axios from 'axios'

// Base API configuration
const api = axios.create({
  baseURL: '/api', // This will use the proxy defined in vite.config.js
  headers: {
    'Content-Type': 'application/json',
  },
})

// Document service
export const documentService = {
  // Upload a document
  uploadDocument: async (file, options = {}) => {
    const formData = new FormData()
    formData.append('file', file)
    
    return api.post('/ingest/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      params: options,
    })
  },
  
  // Get document by ID
  getDocument: async (documentId) => {
    return api.get(`/ingest/document/${documentId}`)
  },
  
  // Redact document
  redactDocument: async (documentId, options = {}) => {
    return api.post(`/ingest/redact/${documentId}`, null, {
      params: options,
    })
  },
}

// Audit service
export const auditService = {
  // Get audit logs
  getAuditLogs: async () => {
    return api.get('/audit/logs')
  },
  
  // Get audit log by ID
  getAuditLog: async (logId) => {
    return api.get(`/audit/logs/${logId}`)
  },
}

export default {
  document: documentService,
  audit: auditService,
}
