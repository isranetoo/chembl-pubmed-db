const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function buildUrl(path, params = {}) {
  const url = new URL(path, API_BASE_URL)

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    url.searchParams.set(key, String(value))
  })

  return url.toString()
}

async function request(path, params = {}) {
  const response = await fetch(buildUrl(path, params))

  if (!response.ok) {
    const errorPayload = await response.json().catch(() => ({}))
    throw new Error(errorPayload.detail || 'Erro ao consultar a API.')
  }

  return response.json()
}

export const api = {
  getStats: () => request('/stats'),
  getCompounds: (params) => request('/compounds', params),
  getCompound: (chemblId) => request(`/compounds/${chemblId}`),
  getCompoundAdmet: (chemblId) => request(`/compounds/${chemblId}/admet`),
  getCompoundIndications: (chemblId, params) => request(`/compounds/${chemblId}/indications`, params),
  getCompoundMechanisms: (chemblId) => request(`/compounds/${chemblId}/mechanisms`),
  getCompoundBioactivities: (chemblId, params) => request(`/compounds/${chemblId}/bioactivities`, params),
  getCompoundArticles: (chemblId, params) => request(`/compounds/${chemblId}/articles`, params),
  getArticles: (params) => request('/articles', params),
  getTargets: (params) => request('/targets', params),
  search: (params) => request('/search', params),
}
