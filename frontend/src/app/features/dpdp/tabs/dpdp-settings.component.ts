import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatDividerModule } from '@angular/material/divider';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-dpdp-settings',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatSlideToggleModule, MatDividerModule, FormsModule],
  template: `
    <div class="page">
      <h2>DPDP Settings</h2>

      <mat-card class="settings-card">
        <h3><mat-icon>tune</mat-icon> Module Toggles</h3>
        <mat-divider></mat-divider>
        <div class="toggle-list">
          @for (t of toggles; track t.key) {
            <div class="toggle-row">
              <div>
                <span class="toggle-label">{{ t.label }}</span>
                <span class="toggle-desc">{{ t.description }}</span>
              </div>
              <mat-slide-toggle [(ngModel)]="t.enabled" color="primary"></mat-slide-toggle>
            </div>
          }
        </div>
      </mat-card>

      <mat-card class="settings-card">
        <h3><mat-icon>security</mat-icon> DPDP Roles</h3>
        <mat-divider></mat-divider>
        <div class="role-grid">
          @for (role of roles; track role.name) {
            <div class="role-item">
              <mat-icon [style.color]="role.color">{{ role.icon }}</mat-icon>
              <div>
                <span class="role-name">{{ role.name }}</span>
                <span class="role-desc">{{ role.description }}</span>
              </div>
            </div>
          }
        </div>
      </mat-card>

      <mat-card class="settings-card">
        <h3><mat-icon>schedule</mat-icon> SLA Configuration</h3>
        <mat-divider></mat-divider>
        <div class="sla-grid">
          @for (sla of slaItems; track sla.label) {
            <div class="sla-item">
              <span class="sla-label">{{ sla.label }}</span>
              <span class="sla-value">{{ sla.value }}</span>
            </div>
          }
        </div>
      </mat-card>

      <mat-card class="settings-card">
        <h3><mat-icon>memory</mat-icon> AI Engine</h3>
        <mat-divider></mat-divider>
        <div class="toggle-list">
          <div class="toggle-row">
            <div>
              <span class="toggle-label">LLM Provider</span>
              <span class="toggle-desc">Ollama (local) — no data leaves the platform</span>
            </div>
          </div>
          <div class="toggle-row">
            <div>
              <span class="toggle-label">Model</span>
              <span class="toggle-desc">llama3 (configurable via environment)</span>
            </div>
          </div>
          <div class="toggle-row">
            <div>
              <span class="toggle-label">Human Approval for AI Actions</span>
              <span class="toggle-desc">Require manual approval before AI-recommended actions are executed</span>
            </div>
            <mat-slide-toggle [ngModel]="true" color="primary"></mat-slide-toggle>
          </div>
        </div>
      </mat-card>
    </div>
  `,
  styles: [`
    .page { display: flex; flex-direction: column; gap: 16px; }
    h2 { margin: 0; font-size: 18px; color: var(--text-primary); }

    .settings-card { padding: 20px; display: flex; flex-direction: column; gap: 12px; }
    .settings-card h3 {
      display: flex; align-items: center; gap: 8px;
      margin: 0; font-size: 15px; color: var(--text-primary);
    }
    .settings-card h3 mat-icon { font-size: 20px; width: 20px; height: 20px; color: var(--brand-blue); }

    .toggle-list { display: flex; flex-direction: column; gap: 4px; }
    .toggle-row {
      display: flex; align-items: center; justify-content: space-between;
      padding: 10px 0; border-bottom: 1px solid var(--border-subtle, #f0f0f0);
    }
    .toggle-row:last-child { border-bottom: none; }
    .toggle-label { display: block; font-size: 13px; font-weight: 500; color: var(--text-primary); }
    .toggle-desc { display: block; font-size: 12px; color: var(--text-secondary); margin-top: 2px; }

    .role-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
    .role-item { display: flex; align-items: center; gap: 10px; padding: 8px 0; }
    .role-item mat-icon { font-size: 24px; width: 24px; height: 24px; }
    .role-name { display: block; font-size: 13px; font-weight: 600; color: var(--text-primary); }
    .role-desc { display: block; font-size: 12px; color: var(--text-secondary); }

    .sla-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
    .sla-item {
      display: flex; justify-content: space-between; align-items: center;
      padding: 10px 14px; background: var(--bg-hover, #fafafa); border-radius: 8px;
    }
    .sla-label { font-size: 13px; color: var(--text-primary); }
    .sla-value { font-size: 13px; font-weight: 600; color: var(--brand-blue); }
  `]
})
export class DpdpSettingsComponent {
  toggles = [
    { key: 'consent', label: 'Consent Management', description: 'Enable consent capture and withdrawal workflows', enabled: true },
    { key: 'rights', label: 'Rights Request Processing', description: 'Enable data principal rights request queue and SLA tracking', enabled: true },
    { key: 'breach', label: 'Breach Management', description: 'Enable breach reporting, notification, and regulator packet workflows', enabled: true },
    { key: 'retention', label: 'Retention & Deletion', description: 'Enable automated retention policy enforcement and deletion jobs', enabled: true },
    { key: 'vendor', label: 'Vendor Compliance', description: 'Track data processors, DPAs, and transfer basis', enabled: true },
    { key: 'ai', label: 'AI Compliance Insights', description: 'Enable AI-powered data classification, monitoring, and risk scoring', enabled: false },
    { key: 'sdf', label: 'SDF Readiness', description: 'Enable Significant Data Fiduciary controls (DPIA, algorithm review)', enabled: false },
  ];

  roles = [
    { name: 'DPO', icon: 'admin_panel_settings', color: '#1565C0', description: 'Data Protection Officer — full access' },
    { name: 'Legal', icon: 'gavel', color: '#6A1B9A', description: 'Legal team — consent & compliance review' },
    { name: 'Admin', icon: 'manage_accounts', color: '#2E7D32', description: 'System admin — settings & user management' },
    { name: 'Ops', icon: 'engineering', color: '#EF6C00', description: 'Operations — breach & retention actions' },
    { name: 'Viewer', icon: 'visibility', color: '#546E7A', description: 'Read-only access to dashboards & reports' },
  ];

  slaItems = [
    { label: 'Access Request', value: '30 days' },
    { label: 'Correction Request', value: '30 days' },
    { label: 'Erasure Request', value: '30 days' },
    { label: 'Grievance Response', value: '30 days' },
    { label: 'Breach Notification (Board)', value: '72 hours' },
    { label: 'Breach Notification (Principal)', value: '72 hours' },
  ];
}
