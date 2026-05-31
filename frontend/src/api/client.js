import axios from 'axios';

// The base URL should point to the FastAPI backend
const API_BASE_URL = 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // Claims
  getClaims: () => apiClient.get('/claims'),
  getClaim: (id) => apiClient.get(`/claims/${id}`),
  ingestClaim: (claimData) => apiClient.post('/claims', claimData),
  
  // Analytics
  getSummary: () => apiClient.get('/analytics/summary'),
  getDenialsByPayer: () => apiClient.get('/analytics/denials'),
  getVolume: () => apiClient.get('/analytics/volume'),
  
  // Voice AI
  submitVoiceQuery: (audioBlob) => {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'voice-query.wav');
    return apiClient.post('/voice/query', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  submitTextQuery: (text) => apiClient.post('/voice/text-query', { query: text }),
  
  // Agents Pipeline
  startPipeline: (id) => apiClient.post(`/agents/process/${id}`),
  getPipelineStatus: (id) => apiClient.get(`/agents/status/${id}`),
};
