import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

const BASE = '/api/v1/dpdp';

@Injectable({ providedIn: 'root' })
export class DpdpService {
  constructor(private http: HttpClient) {}

  // Dashboard
  getDashboard(): Observable<any> { return this.http.get(`${BASE}/dashboard`); }

  // Inventory
  listSystems(): Observable<any[]> { return this.http.get<any[]>(`${BASE}/inventory/systems`); }
  createSystem(body: any): Observable<any> { return this.http.post(`${BASE}/inventory/systems`, body); }
  deleteSystem(id: string): Observable<void> { return this.http.delete<void>(`${BASE}/inventory/systems/${id}`); }

  listDatasets(): Observable<any[]> { return this.http.get<any[]>(`${BASE}/inventory/datasets`); }
  createDataset(body: any): Observable<any> { return this.http.post(`${BASE}/inventory/datasets`, body); }

  // Consent
  listConsents(): Observable<any[]> { return this.http.get<any[]>(`${BASE}/consents`); }
  captureConsent(body: any): Observable<any> { return this.http.post(`${BASE}/consents`, body); }
  withdrawConsent(id: string): Observable<any> { return this.http.post(`${BASE}/consents/${id}/withdraw`, {}); }

  // Rights
  listRights(): Observable<any[]> { return this.http.get<any[]>(`${BASE}/rights`); }
  createRight(body: any): Observable<any> { return this.http.post(`${BASE}/rights`, body); }
  updateRight(id: string, body: any): Observable<any> { return this.http.patch(`${BASE}/rights/${id}`, body); }

  // Breaches
  listBreaches(): Observable<any[]> { return this.http.get<any[]>(`${BASE}/breaches`); }
  createBreach(body: any): Observable<any> { return this.http.post(`${BASE}/breaches`, body); }
  updateBreach(id: string, body: any): Observable<any> { return this.http.patch(`${BASE}/breaches/${id}`, body); }

  // Retention
  listRetention(): Observable<any[]> { return this.http.get<any[]>(`${BASE}/retention`); }
  createRetention(body: any): Observable<any> { return this.http.post(`${BASE}/retention`, body); }
  deleteRetention(id: string): Observable<void> { return this.http.delete<void>(`${BASE}/retention/${id}`); }

  // Vendors
  listVendors(): Observable<any[]> { return this.http.get<any[]>(`${BASE}/vendors`); }
  createVendor(body: any): Observable<any> { return this.http.post(`${BASE}/vendors`, body); }
  deleteVendor(id: string): Observable<void> { return this.http.delete<void>(`${BASE}/vendors/${id}`); }

  // Audit
  listAudit(limit = 100): Observable<any[]> { return this.http.get<any[]>(`${BASE}/audit?limit=${limit}`); }
}
