import { Routes } from '@angular/router';
import { adminGuard } from './core/guards/admin.guard';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
  {
    path: 'dashboard',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/common-dashboard/common-dashboard.component').then(m => m.CommonDashboardComponent),
  },
  {
    path: 'ai-dashboard',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent),
  },
  {
    path: 'live-monitor',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/live-monitor/live-monitor.component').then(m => m.LiveMonitorComponent),
  },
  {
    path: 'policies',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/policies/policy-list.component').then(m => m.PolicyListComponent),
  },
  {
    path: 'endpoints',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/endpoints/endpoint-list.component').then(m => m.EndpointListComponent),
  },
  {
    path: 'mcp-registration',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/endpoints/endpoint-list.component').then(m => m.EndpointListComponent),
  },
  {
    path: 'ai-frameworks',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/ai-frameworks/ai-frameworks.component').then(m => m.AiFrameworksComponent),
  },
  {
    path: 'classifications',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/classifications/classification-rules.component').then(m => m.ClassificationRulesComponent),
  },
  {
    path: 'audit-log',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/audit-log/audit-log.component').then(m => m.AuditLogComponent),
  },
  {
    path: 'knowledge-base',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/knowledge-base/knowledge-base.component').then(m => m.KnowledgeBaseComponent),
  },
  {
    path: 'reports',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/reports/compliance-reports.component').then(m => m.ComplianceReportsComponent),
  },
  {
    path: 'blocked-agents',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/blocked-agents/blocked-agents.component').then(m => m.BlockedAgentsComponent),
  },
  {
    path: 'dpdp',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/dpdp/dpdp.component').then(m => m.DpdpComponent),
  },
  {
    path: 'users',
    canActivate: [authGuard, adminGuard],
    loadComponent: () =>
      import('./features/user-management/user-management.component').then(m => m.UserManagementComponent),
  },
  {
    path: 'profile',
    loadComponent: () =>
      import('./features/profile/profile.component').then(m => m.ProfileComponent),
  },
];
