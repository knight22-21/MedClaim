import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to include auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken
        });
        
        const { access_token, refresh_token: newRefreshToken } = response.data.data;
        localStorage.setItem('access_token', access_token);
        localStorage.setItem('refresh_token', newRefreshToken);
        
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Refresh failed, clear tokens and redirect to login
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

export const api = {
  // Auth
  login: (email, password) => apiClient.post('/auth/login', { email, password }),
  logout: () => apiClient.post('/auth/logout'),
  getCurrentUser: () => apiClient.get('/auth/me'),
  refreshToken: (refreshToken) => apiClient.post('/auth/refresh', { refresh_token: refreshToken }),
  
  // Claims
  getClaims: () => apiClient.get('/claims'),
  getClaim: (id) => apiClient.get(`/claims/${id}`),
  ingestClaim: (claimData) => apiClient.post('/claims', claimData),
  approveClaim: (id, approvalData) => apiClient.post(`/claims/${id}/approve`, approvalData),
  rejectClaim: (id, rejectionData) => apiClient.post(`/claims/${id}/reject`, rejectionData),
  
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
  
  // Comments
  getClaimComments: (claimId) => apiClient.get(`/comments/claims/${claimId}`),
  createComment: (data) => apiClient.post('/comments', data),
  updateComment: (commentId, content) => apiClient.put(`/comments/${commentId}`, { content }),
  deleteComment: (commentId) => apiClient.delete(`/comments/${commentId}`),
  
  // Workflows
  getWorkflows: (isActive) => apiClient.get('/workflows', { params: { is_active: isActive } }),
  getWorkflow: (workflowId) => apiClient.get(`/workflows/${workflowId}`),
  createWorkflow: (data) => apiClient.post('/workflows', data),
  updateWorkflow: (workflowId, data) => apiClient.put(`/workflows/${workflowId}`, data),
  deleteWorkflow: (workflowId) => apiClient.delete(`/workflows/${workflowId}`),
  addWorkflowStep: (workflowId, data) => apiClient.post(`/workflows/${workflowId}/steps`, data),
  updateWorkflowStep: (stepId, data) => apiClient.put(`/workflows/steps/${stepId}`, data),
  deleteWorkflowStep: (stepId) => apiClient.delete(`/workflows/steps/${stepId}`),
  initiateClaimApproval: (claimId, workflowId) => apiClient.post(`/workflows/claims/${claimId}/initiate`, { workflow_id: workflowId }),
  processClaimApproval: (claimId, action, notes) => apiClient.post(`/workflows/claims/${claimId}/approve`, { action, notes }),
  getClaimApprovalStatus: (claimId) => apiClient.get(`/workflows/claims/${claimId}/status`),
  
  // Admin (User Management)
  getUsers: (role, limit, offset) => apiClient.get('/admin/users', { params: { role, limit, offset } }),
  getUser: (userId) => apiClient.get(`/admin/users/${userId}`),
  createUser: (data) => apiClient.post('/admin/users', data),
  updateUser: (userId, data) => apiClient.put(`/admin/users/${userId}`, data),
  deleteUser: (userId) => apiClient.delete(`/admin/users/${userId}`),
  inviteUser: (data) => apiClient.post('/admin/users/invite', data),
  
  // Public Website
  getBlogPosts: (category, limit, offset) => apiClient.get('/public/blog', { params: { category, limit, offset } }),
  getBlogPost: (slug) => apiClient.get(`/public/blog/${slug}`),
  submitDemoRequest: (data) => apiClient.post('/public/lead/demo', data),
  submitContactForm: (data) => apiClient.post('/public/lead/contact', data),
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
