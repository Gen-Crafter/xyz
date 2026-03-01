import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private baseUrl = '/api/v1';

  constructor(private http: HttpClient) {}

  // ─── Dashboard ────────────────────────────────────────────────────
  getDashboardKpis(): Observable<any> {
    return this.http.get(`${this.baseUrl}/dashboard/kpis`);
  }
  getInterceptionVolume(hours = 24): Observable<any> {
    return this.http.get(`${this.baseUrl}/dashboard/interception-volume`, { params: { hours } });
  }
  getActionBreakdown(): Observable<any> {
    return this.http.get(`${this.baseUrl}/dashboard/action-breakdown`);
  }
  getRecentInterceptions(limit = 20): Observable<any> {
    return this.http.get(`${this.baseUrl}/dashboard/recent-interceptions`, { params: { limit } });
  }

  // ─── Proxy ────────────────────────────────────────────────────────
  getProxyStatus(): Observable<any> {
    return this.http.get(`${this.baseUrl}/proxy/status`);
  }
  startProxy(): Observable<any> {
    return this.http.post(`${this.baseUrl}/proxy/start`, {});
  }
  stopProxy(): Observable<any> {
    return this.http.post(`${this.baseUrl}/proxy/stop`, {});
  }

  // ─── Context Detection ────────────────────────────────────────────
  analyzeContext(payload: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/context/analyze`, payload);
  }
  testContext(payload: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/context/test`, payload);
  }

  // ─── Filter Agent ─────────────────────────────────────────────────
  processInterception(payload: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/filter/process`, payload);
  }
  getFilterStats(): Observable<any> {
    return this.http.get(`${this.baseUrl}/filter/stats`);
  }

  // ─── Policies ─────────────────────────────────────────────────────
  listPolicies(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/policies`);
  }
  getPolicy(id: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/policies/${id}`);
  }
  createPolicy(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/policies`, data);
  }
  updatePolicy(id: string, data: any): Observable<any> {
    return this.http.put(`${this.baseUrl}/policies/${id}`, data);
  }
  deletePolicy(id: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/policies/${id}`);
  }
  togglePolicy(id: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/policies/${id}/toggle`, {});
  }
  testPolicy(payload: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/policies/test`, payload);
  }

  // ─── AI Endpoints ─────────────────────────────────────────────────
  listEndpoints(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/endpoints`);
  }
  createEndpoint(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/endpoints`, data);
  }
  updateEndpoint(id: string, data: any): Observable<any> {
    return this.http.put(`${this.baseUrl}/endpoints/${id}`, data);
  }
  deleteEndpoint(id: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/endpoints/${id}`);
  }

  // ─── MCP Deployments ───────────────────────────────────────────────
  listMcpDeployments(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/mcp-deployments`);
  }
  createMcpDeployment(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/mcp-deployments`, data);
  }
  updateMcpDeployment(id: string, data: any): Observable<any> {
    return this.http.patch(`${this.baseUrl}/mcp-deployments/${id}`, data);
  }
  deleteMcpDeployment(id: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/mcp-deployments/${id}`);
  }
  getMcpConfig(id: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/mcp-deployments/${id}/mcp-config`);
  }
  regenerateMcpKey(id: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/mcp-deployments/${id}/regenerate-key`, {});
  }
  getMcpDeploymentStats(): Observable<any> {
    return this.http.get(`${this.baseUrl}/mcp-deployments/stats/overview`);
  }

  // ─── Classifications ──────────────────────────────────────────────
  listClassifications(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/classifications`);
  }
  createClassification(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/classifications`, data);
  }
  updateClassification(id: string, data: any): Observable<any> {
    return this.http.put(`${this.baseUrl}/classifications/${id}`, data);
  }
  deleteClassification(id: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/classifications/${id}`);
  }
  testClassification(text: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/classifications/test`, { text });
  }

  // ─── Audit Log ────────────────────────────────────────────────────
  listAuditLogs(limit = 50, offset = 0, eventType?: string): Observable<any[]> {
    let params = new HttpParams().set('limit', limit).set('offset', offset);
    if (eventType) params = params.set('event_type', eventType);
    return this.http.get<any[]>(`${this.baseUrl}/audit`, { params });
  }
  exportAuditLogs(limit = 1000): Observable<any> {
    return this.http.get(`${this.baseUrl}/audit/export`, { params: { limit } });
  }
  verifyHashChain(): Observable<any> {
    return this.http.post(`${this.baseUrl}/audit/verify`, {});
  }

  // ─── Agent Requests ──────────────────────────────────────────────
  listAgentRequests(limit = 50, status?: string, sourceApp?: string): Observable<any[]> {
    let params = new HttpParams().set('limit', limit);
    if (status) params = params.set('status', status);
    if (sourceApp) params = params.set('source_app', sourceApp);
    return this.http.get<any[]>(`${this.baseUrl}/agent-requests`, { params });
  }
  getAgentRequest(requestId: string): Observable<any> {
    return this.http.get(`${this.baseUrl}/agent-requests/${requestId}`);
  }
  getAgentRequestStats(): Observable<any> {
    return this.http.get(`${this.baseUrl}/agent-requests/stats`);
  }
  getAgentRequestTrends(days = 30): Observable<any> {
    return this.http.get(`${this.baseUrl}/agent-requests/trends`, { params: { days } });
  }
  ingestAgentRequest(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/agent-requests`, data);
  }
  listDeployments(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/agent-requests/deployments/list`);
  }
  listBlockedAgents(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/agent-requests/blocked/list`);
  }
  blockAgent(sourceApp: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/agent-requests/blocked/${sourceApp}`, {});
  }
  unblockAgent(sourceApp: string): Observable<any> {
    return this.http.delete(`${this.baseUrl}/agent-requests/blocked/${sourceApp}`);
  }

  // ─── RAG Knowledge Base ───────────────────────────────────────────
  ingestDocuments(source = 'all'): Observable<any> {
    return this.http.post(`${this.baseUrl}/rag/ingest`, { source });
  }
  listCollections(): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/rag/collections`);
  }
  queryRag(query: string, topK = 5): Observable<any> {
    return this.http.post(`${this.baseUrl}/rag/query`, { query, top_k: topK });
  }
  getRagStats(): Observable<any> {
    return this.http.get(`${this.baseUrl}/rag/stats`);
  }
  uploadDocument(file: File, regulation = '', category = ''): Observable<any> {
    const fd = new FormData();
    fd.append('file', file);
    if (regulation) fd.append('regulation', regulation);
    if (category) fd.append('category', category);
    return this.http.post(`${this.baseUrl}/rag/upload`, fd);
  }
}
