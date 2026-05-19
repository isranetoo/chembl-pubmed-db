import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from './api'

export function useStats() {
  return useQuery({ queryKey: ['stats'], queryFn: api.getStats })
}
export function useCompounds(params) {
  return useQuery({ queryKey: ['compounds', params], queryFn: () => api.getCompounds(params) })
}
export function useCompound(chemblId) {
  return useQuery({ queryKey: ['compound', chemblId], queryFn: () => api.getCompound(chemblId), enabled: !!chemblId })
}
export function useCompoundAdmet(chemblId) {
  return useQuery({ queryKey: ['compound-admet', chemblId], queryFn: () => api.getCompoundAdmet(chemblId), enabled: !!chemblId })
}
export function useCompoundIndications(chemblId, params = {}) {
  return useQuery({ queryKey: ['compound-indications', chemblId, params], queryFn: () => api.getCompoundIndications(chemblId, params), enabled: !!chemblId })
}
export function useCompoundMechanisms(chemblId) {
  return useQuery({ queryKey: ['compound-mechanisms', chemblId], queryFn: () => api.getCompoundMechanisms(chemblId), enabled: !!chemblId })
}
export function useCompoundBioactivities(chemblId, params = {}) {
  return useQuery({ queryKey: ['compound-bioactivities', chemblId, params], queryFn: () => api.getCompoundBioactivities(chemblId, params), enabled: !!chemblId })
}
export function useCompoundArticles(chemblId, params = {}) {
  return useQuery({ queryKey: ['compound-articles', chemblId, params], queryFn: () => api.getCompoundArticles(chemblId, params), enabled: !!chemblId })
}
export function useArticles(params) {
  return useQuery({ queryKey: ['articles', params], queryFn: () => api.getArticles(params) })
}
export function useTargets(params) {
  return useQuery({ queryKey: ['targets', params], queryFn: () => api.getTargets(params) })
}
export function useTarget(chemblId) {
  return useQuery({ queryKey: ['target', chemblId], queryFn: () => api.getTarget(chemblId), enabled: !!chemblId })
}
export function useTargetCompounds(chemblId, params = {}) {
  return useQuery({
    queryKey: ['target-compounds', chemblId, params],
    queryFn: () => api.getTargetCompounds(chemblId, params),
    enabled: !!chemblId,
  })
}
export function useTargetBioactivities(chemblId, params = {}) {
  return useQuery({
    queryKey: ['target-bioactivities', chemblId, params],
    queryFn: () => api.getTargetBioactivities(chemblId, params),
    enabled: !!chemblId,
  })
}
export function useGlobalSearch(params) {
  return useQuery({ queryKey: ['search', params], queryFn: () => api.search(params), enabled: Boolean(params?.q) })
}
export function useCompoundTrials(chemblId, params = {}) {
  return useQuery({
    queryKey: ['compound-trials', chemblId, params],
    queryFn: () => api.getCompoundTrials(chemblId, params),
    enabled: !!chemblId,
  })
}
export function useSyncCompoundTrials(chemblId) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (drugName) => api.syncCompoundTrials(chemblId, drugName ? { drug_name: drugName } : {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['compound-trials', chemblId] }),
  })
}

// ── Clinical Trials — global ───────────────────────────────────
export function useTrials(params) {
  return useQuery({ queryKey: ['trials', params], queryFn: () => api.getTrials(params) })
}
export function useTrialsStats() {
  return useQuery({ queryKey: ['trials-stats'], queryFn: api.getTrialsStats })
}
export function useTrialsSponsors(params) {
  return useQuery({ queryKey: ['trials-sponsors', params], queryFn: () => api.getTrialsSponsors(params) })
}
export function useTrialsConditions(params) {
  return useQuery({ queryKey: ['trials-conditions', params], queryFn: () => api.getTrialsConditions(params) })
}
export function useEndpointAnalysis(params) {
  return useQuery({ queryKey: ['trials-endpoints', params], queryFn: () => api.analyzeEndpoints(params) })
}

// ── Histopatologia (Owkin / TCGA) ──────────────────────────────
export function useHistopathStats() {
  return useQuery({ queryKey: ['histopath-stats'], queryFn: api.getHistopathStats })
}
export function useHistopathSummary() {
  return useQuery({ queryKey: ['histopath-summary'], queryFn: api.getHistopathSummary })
}
export function useHistopathCohorts() {
  return useQuery({ queryKey: ['histopath-cohorts'], queryFn: api.getHistopathCohorts })
}
export function useHistopathFeatures() {
  return useQuery({ queryKey: ['histopath-features'], queryFn: api.getHistopathFeatures })
}
export function useCohortTme(cohort, params = {}) {
  return useQuery({
    queryKey: ['cohort-tme', cohort, params],
    queryFn: () => api.getCohortTme(cohort, params),
    enabled: !!cohort,
  })
}
export function useCohortSlides(cohort, params = {}) {
  return useQuery({
    queryKey: ['cohort-slides', cohort, params],
    queryFn: () => api.getCohortSlides(cohort, params),
    enabled: !!cohort && !!params.feature,
  })
}
export function useCompoundHistopath(chemblId) {
  return useQuery({
    queryKey: ['compound-histopath', chemblId],
    queryFn: () => api.getCompoundHistopath(chemblId),
    enabled: !!chemblId,
  })
}
