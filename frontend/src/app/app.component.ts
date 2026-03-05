import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { Router, RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatBadgeModule } from '@angular/material/badge';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { NotificationService } from './core/services/notification.service';
import { UserService } from './core/services/user.service';
import { CategoryService } from './core/services/category.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, CommonModule,
            MatSidenavModule, MatListModule, MatIconModule, MatToolbarModule,
            MatBadgeModule, MatButtonModule, MatTooltipModule],
  template: `
    <div class="app-layout">
      <!-- ── Brand Top Bar ──────────────────────────────────────────────── -->
      <header class="top-bar">
        <div class="top-bar-left">
          <img class="top-bar-logo" src="assets/gencrafter-logo.png" alt="GenCrafter" />
          <span class="top-bar-divider"></span>
          <span class="top-bar-product">GenCrafter</span>
        </div>
        <div class="top-bar-right">
          <div class="notif-wrapper" (click)="showNotifPanel.set(!showNotifPanel())"
               matTooltip="View compliance alerts and system notifications" matTooltipPosition="below">
            <mat-icon class="notif-icon">notifications_none</mat-icon>
            @if (notifService.unreadCount() > 0) {
              <span class="notif-count">{{ notifService.unreadCount() }}</span>
            }
          </div>
          <div class="profile-btn" (click)="goToProfile()"
               matTooltip="Your profile, settings, and logout" matTooltipPosition="below">
            <mat-icon class="notif-icon">account_circle</mat-icon>
          </div>
        </div>
      </header>

      <div class="body-layout">
        <!-- ── Clean Sidebar ───────────────────────────────────────────── -->
        <nav class="sidebar">
          <div class="nav-links">
            <!-- Common -->
            <a routerLink="/dashboard" routerLinkActive="active" class="nav-item"
               matTooltip="Compliance Hub — enable and manage compliance modules" matTooltipPosition="right">
              <mat-icon>home</mat-icon><span>Home</span>
            </a>

            <!-- AI Governance group -->
            @if (catService.isEnabled('ai')) {
              <div class="nav-group-label">AI Governance</div>
              @for (item of aiNavItems; track item.path) {
                <a [routerLink]="item.path" routerLinkActive="active" class="nav-item"
                   [matTooltip]="item.tooltip" matTooltipPosition="right">
                  <mat-icon>{{ item.icon }}</mat-icon><span>{{ item.label }}</span>
                </a>
              }
            }

            <!-- DPDP Compliance -->
            @if (catService.isEnabled('dpdp')) {
              <div class="nav-group-label">DPDP Compliance</div>
              <a routerLink="/dpdp" routerLinkActive="active" class="nav-item"
                 matTooltip="Digital Personal Data Protection — consent, rights, breach & vendor management" matTooltipPosition="right">
                <mat-icon>shield</mat-icon><span>DPDP Compliance</span>
              </a>
            }

            <!-- Admin -->
            @if (userService.isAdmin()) {
              <div class="nav-group-label">Admin</div>
              <a routerLink="/users" routerLinkActive="active" class="nav-item"
                 matTooltip="Add, remove, and manage users. Import from AD, SAML, or SSO." matTooltipPosition="right">
                <mat-icon>people</mat-icon><span>User Management</span>
              </a>
            }
          </div>
          <div class="sidebar-footer">
            <div class="status-row" matTooltip="All services are running normally" matTooltipPosition="right">
              <span class="status-dot"></span>
              <span class="status-text">System Active</span>
            </div>
          </div>
        </nav>

        <!-- ── Main Content Area ───────────────────────────────────────── -->
        <main class="main-content">
          <!-- Notification Panel -->
          @if (showNotifPanel()) {
            <div class="notif-overlay" (click)="showNotifPanel.set(false)"></div>
            <div class="notif-panel">
              <div class="notif-header">
                <h3>Notifications</h3>
                <div class="notif-actions">
                  <button mat-button (click)="notifService.markAllRead()">Mark all read</button>
                  <button mat-icon-button (click)="showNotifPanel.set(false)"><mat-icon>close</mat-icon></button>
                </div>
              </div>
              <div class="notif-list">
                @for (n of notifService.notifications(); track n.id) {
                  <div class="notif-item" [class.unread]="!n.read" [class]="'sev-' + (n.severity || 'low')">
                    <div class="notif-icon">
                      @if (n.action === 'BLOCK') { <mat-icon>block</mat-icon> }
                      @else if (n.action === 'REDACT') { <mat-icon>edit_off</mat-icon> }
                      @else if (n.action === 'AUDIT') { <mat-icon>visibility</mat-icon> }
                      @else { <mat-icon>check_circle</mat-icon> }
                    </div>
                    <div class="notif-body">
                      <div class="notif-title">{{ n.title }}</div>
                      <div class="notif-msg">{{ n.message }}</div>
                      <div class="notif-time">{{ n.timestamp | date:'HH:mm:ss' }}</div>
                    </div>
                  </div>
                }
                @if (!notifService.notifications().length) {
                  <div class="notif-empty">No notifications yet</div>
                }
              </div>
            </div>
          }

          <!-- Toast notification -->
          @if (notifService.latestToast()) {
            <div class="toast" [class]="'toast-' + (notifService.latestToast()?.severity || 'low')"
                 (click)="notifService.dismissToast()">
              <mat-icon>
                @if (notifService.latestToast()?.action === 'BLOCK') { block }
                @else if (notifService.latestToast()?.action === 'REDACT') { edit_off }
                @else { check_circle }
              </mat-icon>
              <div class="toast-body">
                <strong>{{ notifService.latestToast()?.title }}</strong>
                <span>{{ notifService.latestToast()?.message }}</span>
              </div>
            </div>
          }

          <div class="content-area">
            <router-outlet />
          </div>
        </main>
      </div>
    </div>
  `,
  styles: [`
    /* ── Layout ──────────────────────────────────────────────────────── */
    .app-layout { display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
    .body-layout { display: flex; flex: 1; overflow: hidden; }

    /* ── Brand Top Bar — Dark gradient ──────────────────────────────── */
    .top-bar {
      display: flex; align-items: center; justify-content: space-between;
      height: 56px; min-height: 56px;
      padding: 0 24px;
      background: var(--header-gradient);
      color: #fff;
      z-index: 100;
      box-shadow: 0 4px 24px rgba(10, 14, 39, 0.3);
    }
    .top-bar-left {
      display: flex; align-items: center; gap: 0;
    }
    .top-bar-logo { height: 28px; width: auto; display: block; }
    .top-bar-divider {
      width: 1px; height: 28px;
      background: rgba(255,255,255,0.15);
      margin: 0 16px;
    }
    .top-bar-product {
      font-size: 15px; font-weight: 600;
      color: rgba(255,255,255,0.95); letter-spacing: -0.2px;
    }
    .top-bar-right {
      display: flex; align-items: center; gap: 6px;
    }
    .notif-wrapper {
      position: relative; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      width: 38px; height: 38px; border-radius: 12px;
      transition: background 0.2s;
      &:hover { background: rgba(255,255,255,0.1); }
    }
    .notif-icon {
      color: rgba(255,255,255,0.8); font-size: 22px; width: 22px; height: 22px;
    }
    .profile-btn {
      cursor: pointer; display: flex; align-items: center; justify-content: center;
      width: 38px; height: 38px; border-radius: 12px; transition: background 0.2s;
      &:hover { background: rgba(255,255,255,0.1); }
    }
    .notif-count {
      position: absolute; top: 4px; right: 4px;
      min-width: 16px; height: 16px; line-height: 16px;
      padding: 0 4px; border-radius: 8px;
      background: #ef4444; color: #fff;
      font-size: 9px; font-weight: 700; text-align: center;
      box-shadow: 0 2px 6px rgba(239, 68, 68, 0.4);
    }

    /* ── Sidebar — Glass effect ──────────────────────────────────────── */
    .sidebar {
      width: 220px; min-width: 220px;
      background: rgba(255, 255, 255, 0.7);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-right: 1px solid rgba(255, 255, 255, 0.5);
      display: flex; flex-direction: column;
    }

    .nav-links {
      flex: 1; padding: 12px 8px; overflow-y: auto;
      display: flex; flex-direction: column; gap: 2px;
    }

    .nav-item {
      display: flex; align-items: center; gap: 12px;
      padding: 10px 14px;
      color: var(--text-secondary);
      text-decoration: none;
      font-size: 13px; font-weight: 500;
      transition: all 0.2s ease;
      border-radius: 12px;
      border-left: none;

      mat-icon { font-size: 20px; width: 20px; height: 20px; color: var(--text-disabled); transition: color 0.2s ease; }

      &:hover {
        background: rgba(76, 111, 255, 0.06);
        color: var(--text-primary);
        mat-icon { color: var(--text-secondary); }
      }

      &.active {
        background: rgba(76, 111, 255, 0.1);
        color: var(--brand-blue); font-weight: 600;
        box-shadow: 0 2px 8px rgba(76, 111, 255, 0.12);
        mat-icon { color: var(--brand-blue); }
      }
    }

    .sidebar-footer {
      padding: 14px 16px;
      border-top: 1px solid rgba(0, 0, 0, 0.06);
    }
    .status-row {
      display: flex; align-items: center; gap: 8px;
    }
    .status-dot {
      width: 7px; height: 7px; border-radius: 50%;
      background: var(--status-success);
      box-shadow: 0 0 6px rgba(16, 185, 129, 0.4);
    }
    .status-text { font-size: 11px; color: var(--text-disabled); font-weight: 500; }

    .nav-group-label {
      font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px;
      color: var(--text-disabled); padding: 16px 14px 4px; margin-top: 4px;
    }

    /* ── Main Content ────────────────────────────────────────────────── */
    .main-content {
      flex: 1; display: flex; flex-direction: column;
      overflow: hidden; position: relative;
      background: var(--bg-primary);
    }

    .content-area {
      flex: 1; overflow-y: auto;
      padding: 28px 36px;
    }

    /* ── Notification Panel — Glassmorphism ───────────────────────────── */
    .notif-overlay {
      position: fixed; inset: 0; z-index: 9998;
      background: rgba(0,0,0,0.2);
      backdrop-filter: blur(4px);
    }
    .notif-panel {
      position: fixed; top: 64px; right: 16px; width: 380px; max-height: 75vh;
      background: rgba(255, 255, 255, 0.85);
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      border: 1px solid rgba(255, 255, 255, 0.5);
      border-radius: 18px;
      z-index: 9999; box-shadow: var(--shadow-lg); overflow: hidden;
    }
    .notif-header {
      display: flex; justify-content: space-between; align-items: center;
      padding: 16px 18px; border-bottom: 1px solid rgba(0,0,0,0.06);
      h3 { font-size: 15px; font-weight: 700; color: var(--text-primary); }
    }
    .notif-actions { display: flex; align-items: center; gap: 4px; }
    .notif-list { max-height: 60vh; overflow-y: auto; }
    .notif-item {
      display: flex; gap: 12px; padding: 14px 18px;
      border-bottom: 1px solid rgba(0,0,0,0.04); cursor: pointer;
      transition: background 0.15s;
      &:hover { background: rgba(76, 111, 255, 0.04); }
      &.unread { background: rgba(76, 111, 255, 0.06); }
    }
    .notif-icon {
      padding-top: 2px;
      mat-icon { font-size: 18px; width: 18px; height: 18px; }
    }
    .sev-critical .notif-icon { color: var(--status-danger); }
    .sev-high .notif-icon { color: var(--status-orange); }
    .sev-low .notif-icon { color: var(--status-success); }
    .notif-body { flex: 1; min-width: 0; }
    .notif-title { font-size: 13px; font-weight: 600; color: var(--text-primary); }
    .notif-msg { font-size: 12px; color: var(--text-secondary); margin-top: 2px;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .notif-time { font-size: 10px; color: var(--text-disabled); margin-top: 4px; }
    .notif-empty { padding: 40px; text-align: center; color: var(--text-disabled); font-size: 13px; }

    /* ── Toast — Floating glass card ─────────────────────────────────── */
    .toast {
      position: fixed; top: 68px; right: 16px; z-index: 99999;
      display: flex; align-items: center; gap: 12px;
      padding: 14px 18px; border-radius: 16px; cursor: pointer;
      background: rgba(255, 255, 255, 0.88);
      backdrop-filter: blur(20px);
      border: 1px solid rgba(255, 255, 255, 0.5);
      box-shadow: var(--shadow-lg);
      animation: slideIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
      max-width: 400px;
    }
    .toast-critical { border-left: 3px solid var(--status-danger); }
    .toast-critical mat-icon { color: var(--status-danger); }
    .toast-high { border-left: 3px solid var(--status-orange); }
    .toast-high mat-icon { color: var(--status-orange); }
    .toast-low { border-left: 3px solid var(--status-success); }
    .toast-low mat-icon { color: var(--status-success); }
    .toast-body {
      display: flex; flex-direction: column; gap: 2px;
      strong { font-size: 13px; font-weight: 600; color: var(--text-primary); }
      span { font-size: 12px; color: var(--text-secondary);
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 280px; }
    }
    @keyframes slideIn {
      from { transform: translateY(-16px) scale(0.96); opacity: 0; }
      to { transform: translateY(0) scale(1); opacity: 1; }
    }
  `],
})
export class AppComponent implements OnInit {
  notifService = inject(NotificationService);
  userService = inject(UserService);
  catService = inject(CategoryService);
  showNotifPanel = signal(false);

  aiNavItems = [
    { path: '/ai-dashboard', icon: 'dashboard', label: 'AI Dashboard', tooltip: 'Overview of AI compliance KPIs, violations, and risk scores' },
    { path: '/mcp-registration', icon: 'hub', label: 'MCP Registration', tooltip: 'Register AI deployments and get MCP connection configs for compliance scanning' },
    { path: '/ai-frameworks', icon: 'account_tree', label: 'AI Frameworks', tooltip: 'Configure AI governance frameworks and standards' },
    { path: '/live-monitor', icon: 'monitor_heart', label: 'Live Monitor', tooltip: 'Real-time view of AI agent traffic and interceptions' },
    { path: '/policies', icon: 'policy', label: 'Policies', tooltip: 'Create and manage compliance rules that govern AI behavior' },
    { path: '/classifications', icon: 'label', label: 'Classifications', tooltip: 'Define data classification rules for PII and sensitive data detection' },
    { path: '/audit-log', icon: 'history', label: 'Audit Log', tooltip: 'Tamper-proof record of all compliance events and actions' },
    { path: '/knowledge-base', icon: 'menu_book', label: 'Knowledge Base', tooltip: 'Regulation documents used by AI for compliance decisions' },
    { path: '/reports', icon: 'assessment', label: 'Reports', tooltip: 'Generate and export compliance reports and analytics' },
    { path: '/blocked-agents', icon: 'block', label: 'Blocked Deployments', tooltip: 'View AI agents blocked for policy violations' },
  ];

  private router = inject(Router);

  ngOnInit() {
    if (this.userService.isLoggedIn()) {
      this.catService.load().subscribe({ error: () => {} });
    }
  }

  goToProfile() { this.router.navigate(['/profile']); }
}
