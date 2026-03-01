import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatDividerModule } from '@angular/material/divider';
import { FormsModule } from '@angular/forms';
import { CategoryService, Category } from '../../core/services/category.service';
import { UserService } from '../../core/services/user.service';

interface CategoryTemplate {
  name: string;
  slug: string;
  icon: string;
  description: string;
  route: string;
  color: string;
  subItems: number;
}

const CATEGORY_TEMPLATES: CategoryTemplate[] = [
  {
    name: 'AI Governance',
    slug: 'ai',
    icon: 'psychology',
    description: 'Monitor AI agent traffic, enforce compliance policies, manage endpoints, and audit AI system behavior in real-time.',
    route: '/ai-dashboard',
    color: '#4C6FFF',
    subItems: 10,
  },
  {
    name: 'DPDP Compliance',
    slug: 'dpdp',
    icon: 'shield',
    description: 'Manage Digital Personal Data Protection compliance including consent management, data rights, breach reporting, and vendor oversight.',
    route: '/dpdp',
    color: '#10B981',
    subItems: 10,
  },
];

@Component({
  selector: 'app-common-dashboard',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatButtonModule,
            MatSlideToggleModule, MatDividerModule, MatTooltipModule, FormsModule],
  template: `
    <div class="page">
      <div class="page-header">
        <div>
          <h1>Compliance Hub</h1>
          <p class="subtitle">Select a compliance module to get started</p>
        </div>
      </div>

      <!-- Admin: create categories that don't exist yet -->
      @if (userService.isAdmin()) {
        @if (availableToCreate().length > 0) {
          <div class="admin-section">
            <h3><mat-icon>add_circle</mat-icon> Available Modules</h3>
            <p class="section-desc">Enable compliance modules for your organization</p>
            <div class="template-grid">
              @for (tpl of availableToCreate(); track tpl.slug) {
                <mat-card class="template-card">
                  <div class="tpl-icon" [style.background]="tpl.color + '18'" [style.color]="tpl.color">
                    <mat-icon>{{ tpl.icon }}</mat-icon>
                  </div>
                  <div class="tpl-info">
                    <h4>{{ tpl.name }}</h4>
                    <p>{{ tpl.description }}</p>
                  </div>
                  <button mat-flat-button color="primary" (click)="enableCategory(tpl)"
                          matTooltip="Activate this module for all users in your organization">
                    <mat-icon>power_settings_new</mat-icon> Enable
                  </button>
                </mat-card>
              }
            </div>
          </div>
        }
      }

      <!-- Active categories -->
      @if (activeCategories().length > 0) {
        <div class="active-section">
          <h3><mat-icon>apps</mat-icon> Active Modules</h3>
          <div class="category-grid">
            @for (cat of activeCategories(); track cat.slug) {
              <mat-card class="category-card" (click)="navigate(cat)"
                        matTooltip="Click to open this compliance module" matTooltipPosition="above">
                <div class="cat-header">
                  <div class="cat-icon" [style.background]="getColor(cat.slug) + '18'" [style.color]="getColor(cat.slug)">
                    <mat-icon>{{ cat.icon }}</mat-icon>
                  </div>
                  @if (userService.isAdmin()) {
                    <mat-slide-toggle
                      [checked]="cat.is_active"
                      (change)="toggleCategory(cat, $event.checked)"
                      (click)="$event.stopPropagation()"
                      color="primary"
                      matTooltip="Toggle this module on or off for your organization">
                    </mat-slide-toggle>
                  }
                </div>
                <h2>{{ cat.name }}</h2>
                <p class="cat-desc">{{ cat.description }}</p>
                <div class="cat-footer">
                  <span class="cat-status active">
                    <span class="dot"></span> Active
                  </span>
                  <mat-icon class="arrow">arrow_forward</mat-icon>
                </div>
              </mat-card>
            }
          </div>
        </div>
      }

      <!-- Empty state -->
      @if (activeCategories().length === 0 && availableToCreate().length === 0) {
        <mat-card class="empty-card">
          <mat-icon class="empty-icon">category</mat-icon>
          <h2>No modules configured</h2>
          <p>Contact your administrator to enable compliance modules.</p>
        </mat-card>
      }

      @if (!userService.isAdmin() && activeCategories().length === 0 && categories().length === 0) {
        <mat-card class="empty-card">
          <mat-icon class="empty-icon">hourglass_empty</mat-icon>
          <h2>Modules not yet configured</h2>
          <p>Your administrator needs to enable compliance modules before you can use them.</p>
        </mat-card>
      }
    </div>
  `,
  styles: [`
    .page { max-width: 1000px; }
    .page-header { margin-bottom: 24px; }
    .page-header h1 { margin: 0; font-size: 26px; font-weight: 800; color: var(--text-primary); }
    .subtitle { margin: 4px 0 0; color: var(--text-secondary); font-size: 14px; }

    /* ── Admin section ─────────────────────────────── */
    .admin-section, .active-section { margin-bottom: 28px; }
    .admin-section h3, .active-section h3 {
      display: flex; align-items: center; gap: 8px;
      font-size: 15px; font-weight: 700; color: var(--text-primary); margin: 0 0 4px;
      mat-icon { font-size: 20px; width: 20px; height: 20px; color: var(--brand-blue); }
    }
    .section-desc { margin: 0 0 14px; font-size: 13px; color: var(--text-secondary); }

    .template-grid { display: flex; flex-direction: column; gap: 12px; }
    .template-card {
      display: flex !important; align-items: center; gap: 16px; padding: 18px 20px !important;
      cursor: default;
    }
    .tpl-icon {
      width: 48px; height: 48px; border-radius: 14px;
      display: flex; align-items: center; justify-content: center; flex-shrink: 0;
      mat-icon { font-size: 26px; width: 26px; height: 26px; }
    }
    .tpl-info { flex: 1; min-width: 0; }
    .tpl-info h4 { margin: 0; font-size: 15px; font-weight: 700; color: var(--text-primary); }
    .tpl-info p { margin: 4px 0 0; font-size: 12px; color: var(--text-secondary); line-height: 1.4; }

    /* ── Category cards ────────────────────────────── */
    .category-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px;
      margin-top: 14px;
    }
    .category-card {
      padding: 24px !important; cursor: pointer;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
      &:hover { transform: translateY(-2px); box-shadow: 0 8px 32px rgba(0,0,0,0.08); }
    }
    .cat-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
    .cat-icon {
      width: 52px; height: 52px; border-radius: 16px;
      display: flex; align-items: center; justify-content: center;
      mat-icon { font-size: 28px; width: 28px; height: 28px; }
    }
    .category-card h2 { margin: 0; font-size: 20px; font-weight: 700; color: var(--text-primary); }
    .cat-desc { margin: 8px 0 20px; font-size: 13px; color: var(--text-secondary); line-height: 1.5; }
    .cat-footer { display: flex; justify-content: space-between; align-items: center; }
    .cat-status {
      display: flex; align-items: center; gap: 6px;
      font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;
    }
    .cat-status.active { color: var(--status-success); }
    .dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
    .arrow { color: var(--text-disabled); font-size: 20px; width: 20px; height: 20px; }

    /* ── Empty ─────────────────────────────────────── */
    .empty-card {
      padding: 56px !important; text-align: center;
      display: flex; flex-direction: column; align-items: center; gap: 8px;
    }
    .empty-icon { font-size: 56px; width: 56px; height: 56px; color: var(--text-disabled); }
    .empty-card h2 { margin: 0; font-size: 18px; color: var(--text-primary); }
    .empty-card p { margin: 0; font-size: 13px; color: var(--text-secondary); }
  `]
})
export class CommonDashboardComponent implements OnInit {
  catService = inject(CategoryService);
  userService = inject(UserService);
  private router = inject(Router);

  categories = this.catService.categories;

  activeCategories = computed(() =>
    this.categories().filter(c => c.is_active)
  );

  availableToCreate = computed(() => {
    const existingSlugs = new Set(this.categories().map(c => c.slug));
    return CATEGORY_TEMPLATES.filter(t => !existingSlugs.has(t.slug));
  });

  ngOnInit() {
    if (this.userService.isLoggedIn()) {
      this.catService.load().subscribe({ error: () => {} });
    }
  }

  enableCategory(tpl: CategoryTemplate) {
    this.catService.create({
      name: tpl.name,
      slug: tpl.slug,
      icon: tpl.icon,
      description: tpl.description,
    }).subscribe({
      next: () => this.catService.load().subscribe(),
      error: () => {},
    });
  }

  toggleCategory(cat: Category, active: boolean) {
    this.catService.update(cat.id, { is_active: active }).subscribe({
      next: () => this.catService.load().subscribe(),
    });
  }

  navigate(cat: Category) {
    const tpl = CATEGORY_TEMPLATES.find(t => t.slug === cat.slug);
    if (tpl) {
      this.router.navigate([tpl.route]);
    }
  }

  getColor(slug: string): string {
    return CATEGORY_TEMPLATES.find(t => t.slug === slug)?.color || '#4C6FFF';
  }
}
