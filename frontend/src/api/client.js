import axios from 'axios';

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
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  submitTextQuery: (text) => apiClient.post('/voice/text-query', { query: text }),
  
  // Agents Pipeline (Background Jobs)
  startPipeline: (id) => apiClient.post(`/agents/process/${id}`),
  getJobStatus: (jobId) => apiClient.get(`/agents/status/${jobId}`),
  getJobsForClaim: (claimId) => apiClient.get(`/agents/jobs/${claimId}`),
};

/**
 * Poll a pipeline job until it reaches a terminal state.
 * Returns the final job object.
 * 
 * @param {string} jobId - The job ID to poll
 * @param {function} onStatusUpdate - Callback for each status check
 * @param {number} intervalMs - Polling interval in ms (default 2000)
 * @param {number} maxAttempts - Max poll attempts (default 60 = 2 minutes)
 */
export async function pollJobUntilDone(jobId, onStatusUpdate, intervalMs = 2000, maxAttempts = 60) {
  for (let i = 0; i < maxAttempts; i++) {
    const res = await api.getJobStatus(jobId);
    const job = res.data.data;
    
    if (onStatusUpdate) onStatusUpdate(job);
    
    if (job.status === 'COMPLETED' || job.status === 'FAILED') {
      return job;
    }
    
    // Wait before next poll
    await new Promise(resolve => setTimeout(resolve, intervalMs));
  }
  
  throw new Error('Job polling timed out');
}
