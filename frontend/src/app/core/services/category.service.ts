import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';

const BASE = '/api/v1/categories';

export interface Category {
  id: string;
  tenant_id: string;
  name: string;
  slug: string;
  icon: string;
  description: string;
  is_active: boolean;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

@Injectable({ providedIn: 'root' })
export class CategoryService {
  private http = inject(HttpClient);
  categories = signal<Category[]>([]);

  load(): Observable<Category[]> {
    return this.http.get<Category[]>(BASE).pipe(
      tap(cats => this.categories.set(cats))
    );
  }

  create(body: { name: string; slug: string; icon?: string; description?: string }): Observable<Category> {
    return this.http.post<Category>(BASE, body);
  }

  update(id: string, body: { name?: string; icon?: string; description?: string; is_active?: boolean }): Observable<Category> {
    return this.http.patch<Category>(`${BASE}/${id}`, body);
  }

  delete(id: string): Observable<void> {
    return this.http.delete<void>(`${BASE}/${id}`);
  }

  isEnabled(slug: string): boolean {
    return this.categories().some(c => c.slug === slug && c.is_active);
  }
}
