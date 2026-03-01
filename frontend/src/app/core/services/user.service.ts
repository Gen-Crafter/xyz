import { Injectable, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';

const BASE = '/api/v1/users';

export interface UserProfile {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_admin: boolean;
  tenant_id: string;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  email: string;
  full_name: string | null;
  is_admin: boolean;
  tenant_id: string;
}

@Injectable({ providedIn: 'root' })
export class UserService {
  currentUser = signal<UserProfile | null>(null);
  isLoggedIn = computed(() => !!this.currentUser());
  isAdmin = computed(() => this.currentUser()?.is_admin === true);

  constructor(private http: HttpClient) {
    this.bootstrap();
  }

  /** On app init, if a token exists, fetch the profile to restore session. */
  bootstrap(): void {
    const token = localStorage.getItem('access_token');
    if (token) {
      this.getProfile().subscribe({
        error: () => {
          localStorage.removeItem('access_token');
          this.currentUser.set(null);
        },
      });
    }
  }

  // Auth
  register(body: { email: string; password: string; full_name?: string }): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${BASE}/register`, body).pipe(
      tap(res => {
        localStorage.setItem('access_token', res.access_token);
      })
    );
  }

  login(email: string, password: string): Observable<TokenResponse> {
    return this.http.post<TokenResponse>(`${BASE}/login`, { email, password }).pipe(
      tap(res => {
        localStorage.setItem('access_token', res.access_token);
      })
    );
  }

  logout(): void {
    localStorage.removeItem('access_token');
    this.currentUser.set(null);
  }

  // Profile
  getProfile(): Observable<UserProfile> {
    return this.http.get<UserProfile>(`${BASE}/profile`).pipe(
      tap(u => this.currentUser.set(u))
    );
  }

  updateProfile(body: { full_name?: string }): Observable<UserProfile> {
    return this.http.patch<UserProfile>(`${BASE}/profile`, body).pipe(
      tap(u => this.currentUser.set(u))
    );
  }

  changePassword(current_password: string, new_password: string): Observable<any> {
    return this.http.post(`${BASE}/profile/change-password`, { current_password, new_password });
  }

  // Admin: user management
  listUsers(): Observable<UserProfile[]> { return this.http.get<UserProfile[]>(BASE); }
  createUser(body: any): Observable<UserProfile> { return this.http.post<UserProfile>(BASE, body); }
  updateUser(id: string, body: any): Observable<UserProfile> { return this.http.patch<UserProfile>(`${BASE}/${id}`, body); }
  deleteUser(id: string): Observable<void> { return this.http.delete<void>(`${BASE}/${id}`); }
  getStats(): Observable<any> { return this.http.get(`${BASE}/stats`); }

  // Admin: identity providers
  private readonly IDP = '/api/v1/identity-providers';
  listIdps(): Observable<any[]> { return this.http.get<any[]>(this.IDP); }
  createIdp(body: any): Observable<any> { return this.http.post<any>(this.IDP, body); }
  updateIdp(id: string, body: any): Observable<any> { return this.http.patch<any>(`${this.IDP}/${id}`, body); }
  deleteIdp(id: string): Observable<void> { return this.http.delete<void>(`${this.IDP}/${id}`); }
  testIdp(id: string): Observable<any> { return this.http.post<any>(`${this.IDP}/${id}/test`, {}); }
  importFromIdp(id: string): Observable<any> { return this.http.post<any>(`${this.IDP}/${id}/import`, {}); }
}
