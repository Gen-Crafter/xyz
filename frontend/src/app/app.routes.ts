import { Routes } from '@angular/router';
import { adminGuard } from './core/guards/admin.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./features/common-dashboard/common-dashboard.component').then(m => m.CommonDashboardComponent),
  },
  {
    path: 'ai-dashboard',
    loadComponent: () =>
      import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent),
  },
  {
    path: 'live-monitor',
    loadComponent: () =>
      import('./features/live-monitor/live-monitor.component').then(m => m.LiveMonitorComponent),
  },
  {
    path: 'policies',
    loadComponent: () =>
      import('./features/policies/policy-list.component').then(m => m.PolicyListComponent),
  },
  {
    path: 'endpoints',
    loadComponent: () =>
      import('./features/endpoints/endpoint-list.component').then(m => m.EndpointListComponent),
  },
  {
    path: 'ai-frameworks',
    loadComponent: () =>
      import('./features/ai-frameworks/ai-frameworks.component').then(m => m.AiFrameworksComponent),
  },
  {
    path: 'classifications',
    loadComponent: () =>
      import('./features/classifications/classification-rules.component').then(m => m.ClassificationRulesComponent),
  },
  {
    path: 'audit-log',
    loadComponent: () =>
      import('./features/audit-log/audit-log.component').then(m => m.AuditLogComponent),
  },
  {
    path: 'knowledge-base',
    loadComponent: () =>
      import('./features/knowledge-base/knowledge-base.component').then(m => m.KnowledgeBaseComponent),
  },
  {
    path: 'reports',
    loadComponent: () =>
      import('./features/reports/compliance-reports.component').then(m => m.ComplianceReportsComponent),
  },
  {
    path: 'blocked-agents',
    loadComponent: () =>
      import('./features/blocked-agents/blocked-agents.component').then(m => m.BlockedAgentsComponent),
  },
  {
    path: 'dpdp',
    loadComponent: () =>
      import('./features/dpdp/dpdp.component').then(m => m.DpdpComponent),
  },
  {
    path: 'users',
    canActivate: [adminGuard],
    loadComponent: () =>
      import('./features/user-management/user-management.component').then(m => m.UserManagementComponent),
  },
  {
    path: 'profile',
    loadComponent: () =>
      import('./features/profile/profile.component').then(m => m.ProfileComponent),
  },
];
