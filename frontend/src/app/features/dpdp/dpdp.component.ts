import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTabsModule } from '@angular/material/tabs';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

import { DpdpDashboardComponent } from './tabs/dpdp-dashboard.component';
import { DpdpInventoryComponent } from './tabs/dpdp-inventory.component';
import { DpdpConsentComponent } from './tabs/dpdp-consent.component';
import { DpdpRightsComponent } from './tabs/dpdp-rights.component';
import { DpdpBreachComponent } from './tabs/dpdp-breach.component';
import { DpdpRetentionComponent } from './tabs/dpdp-retention.component';
import { DpdpVendorComponent } from './tabs/dpdp-vendor.component';
import { DpdpAiInsightsComponent } from './tabs/dpdp-ai-insights.component';
import { DpdpAuditComponent } from './tabs/dpdp-audit.component';
import { DpdpSettingsComponent } from './tabs/dpdp-settings.component';

interface SubTab {
  label: string;
  icon: string;
  tooltip: string;
}

@Component({
  selector: 'app-dpdp',
  standalone: true,
  imports: [
    CommonModule, MatTabsModule, MatIconModule, MatTooltipModule,
    DpdpDashboardComponent, DpdpInventoryComponent, DpdpConsentComponent,
    DpdpRightsComponent, DpdpBreachComponent, DpdpRetentionComponent,
    DpdpVendorComponent, DpdpAiInsightsComponent, DpdpAuditComponent,
    DpdpSettingsComponent,
  ],
  template: `
    <div class="dpdp-page">
      <div class="dpdp-header">
        <div>
          <h1>DPDP Compliance</h1>
          <p class="subtitle">Digital Personal Data Protection Act 2023 &amp; Rules 2025</p>
        </div>
        <a class="doc-link" href="https://www.meity.gov.in/writereaddata/files/Digital%20Personal%20Data%20Protection%20Act%202023.pdf"
           target="_blank" rel="noreferrer"
           matTooltip="Open the full DPDP Act 2023 document from MeitY">
          <mat-icon>open_in_new</mat-icon> DPDP Act 2023
        </a>
      </div>

      <mat-tab-group [(selectedIndex)]="activeTab" animationDuration="200ms" class="dpdp-tabs">
        @for (tab of tabs; track tab.label) {
          <mat-tab>
            <ng-template mat-tab-label>
              <div [matTooltip]="tab.tooltip" matTooltipPosition="above">
                <mat-icon>{{ tab.icon }}</mat-icon>
                <span class="tab-label">{{ tab.label }}</span>
              </div>
            </ng-template>
          </mat-tab>
        }
      </mat-tab-group>

      <div class="tab-content">
        @switch (activeTab) {
          @case (0) { <app-dpdp-dashboard /> }
          @case (1) { <app-dpdp-inventory /> }
          @case (2) { <app-dpdp-consent /> }
          @case (3) { <app-dpdp-rights /> }
          @case (4) { <app-dpdp-breach /> }
          @case (5) { <app-dpdp-retention /> }
          @case (6) { <app-dpdp-vendor /> }
          @case (7) { <app-dpdp-ai-insights /> }
          @case (8) { <app-dpdp-audit /> }
          @case (9) { <app-dpdp-settings /> }
        }
      </div>
    </div>
  `,
  styles: [`
    .dpdp-page { display: flex; flex-direction: column; gap: 0; }

    .dpdp-header {
      display: flex; align-items: center; justify-content: space-between;
      margin-bottom: 16px;
    }
    .dpdp-header h1 { margin: 0; font-size: 22px; color: var(--text-primary); }
    .subtitle { margin: 4px 0 0; color: var(--text-secondary); font-size: 13px; }
    .doc-link {
      display: inline-flex; align-items: center; gap: 6px;
      text-decoration: none; color: var(--brand-blue); font-weight: 600; font-size: 13px;
    }

    .dpdp-tabs {
      ::ng-deep .mat-mdc-tab-labels { gap: 0; }
      ::ng-deep .mat-mdc-tab { min-width: 0; padding: 0 14px; }
      ::ng-deep .mat-mdc-tab .mdc-tab__content { gap: 6px; }
      ::ng-deep .mat-mdc-tab mat-icon { font-size: 18px; width: 18px; height: 18px; }
    }
    .tab-label { font-size: 12px; white-space: nowrap; }

    .tab-content { margin-top: 16px; }
  `]
})
export class DpdpComponent {
  activeTab = 0;

  tabs: SubTab[] = [
    { label: 'Dashboard', icon: 'dashboard', tooltip: 'DPDP compliance overview with key metrics and risk indicators' },
    { label: 'Data Inventory', icon: 'storage', tooltip: 'Catalog and classify personal data your organization processes' },
    { label: 'Consent', icon: 'verified_user', tooltip: 'Track and manage data principal consent records' },
    { label: 'Rights Requests', icon: 'person_search', tooltip: 'Handle data access, correction, and erasure requests from data principals' },
    { label: 'Breaches', icon: 'report_problem', tooltip: 'Report and track personal data breaches as required by DPDP Act' },
    { label: 'Retention', icon: 'delete_sweep', tooltip: 'Define data retention policies and track scheduled deletions' },
    { label: 'Vendors', icon: 'business', tooltip: 'Manage data processor agreements and vendor compliance' },
    { label: 'AI Insights', icon: 'psychology', tooltip: 'AI-powered analysis of your DPDP compliance posture' },
    { label: 'Audit', icon: 'history', tooltip: 'Complete audit trail of all DPDP compliance activities' },
    { label: 'Settings', icon: 'settings', tooltip: 'Configure DPDP module preferences and organization details' },
  ];
}
