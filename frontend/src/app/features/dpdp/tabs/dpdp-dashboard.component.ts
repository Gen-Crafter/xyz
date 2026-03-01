import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { DpdpService } from '../dpdp.service';

@Component({
  selector: 'app-dpdp-dashboard',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatProgressBarModule],
  template: `
    <div class="grid">
      @for (card of cards; track card.label) {
        <mat-card class="stat-card">
          <div class="stat-icon-wrap" [style.background]="card.bg">
            <mat-icon [style.color]="card.color">{{ card.icon }}</mat-icon>
          </div>
          <div class="stat-body">
            <span class="stat-value">{{ card.value }}</span>
            <span class="stat-label">{{ card.label }}</span>
          </div>
        </mat-card>
      }
    </div>

    <mat-card class="score-card">
      <h3>Compliance Score</h3>
      <div class="score-row">
        <mat-progress-bar mode="determinate" [value]="stats.compliance_score" class="score-bar"></mat-progress-bar>
        <span class="score-val">{{ stats.compliance_score }}%</span>
      </div>
      <p class="score-hint">Based on consent coverage, retention policies, breach status, and open requests.</p>
    </mat-card>

    <div class="section-grid">
      <mat-card class="info-card">
        <h3><mat-icon>gavel</mat-icon> DPDP Act 2023</h3>
        <ul>
          <li>Applies to processing of digital personal data within India</li>
          <li>Establishes rights of Data Principals (access, correction, erasure, grievance, nomination)</li>
          <li>Mandates lawful purpose and informed consent</li>
          <li>Data Fiduciary must implement reasonable security safeguards</li>
          <li>Breach notification to Board and affected Data Principals</li>
        </ul>
      </mat-card>
      <mat-card class="info-card">
        <h3><mat-icon>description</mat-icon> DPDP Rules 2025</h3>
        <ul>
          <li>Rule 3 — Notice &amp; consent: clear, itemised, in scheduled languages</li>
          <li>Rule 4 — Registration of consent managers with the Board</li>
          <li>Rule 5 — Rights of Data Principals within prescribed timelines</li>
          <li>Rule 6 — Reasonable security safeguards (encryption, access control, logging)</li>
          <li>Rule 8 — Breach notification within 72 hours</li>
          <li>Rule 12 — Significant Data Fiduciary obligations (DPIA, audit)</li>
        </ul>
      </mat-card>
    </div>
  `,
  styles: [`
    .grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px; margin-bottom: 16px;
    }
    .stat-card {
      display: flex; align-items: center; gap: 14px; padding: 16px;
    }
    .stat-icon-wrap {
      width: 42px; height: 42px; border-radius: 10px;
      display: flex; align-items: center; justify-content: center;
    }
    .stat-icon-wrap mat-icon { font-size: 22px; width: 22px; height: 22px; }
    .stat-body { display: flex; flex-direction: column; }
    .stat-value { font-size: 22px; font-weight: 700; color: var(--text-primary); line-height: 1; }
    .stat-label { font-size: 11px; color: var(--text-secondary); margin-top: 4px; }

    .score-card { padding: 20px; margin-bottom: 16px; }
    .score-card h3 { margin: 0 0 12px; font-size: 15px; color: var(--text-primary); }
    .score-row { display: flex; align-items: center; gap: 12px; }
    .score-bar { flex: 1; height: 10px; border-radius: 5px; }
    .score-val { font-size: 20px; font-weight: 700; color: var(--brand-blue); min-width: 50px; text-align: right; }
    .score-hint { margin: 8px 0 0; font-size: 12px; color: var(--text-disabled); }

    .section-grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px;
    }
    .info-card { padding: 20px; }
    .info-card h3 {
      display: flex; align-items: center; gap: 8px;
      margin: 0 0 12px; font-size: 15px; color: var(--text-primary);
    }
    .info-card h3 mat-icon { font-size: 20px; width: 20px; height: 20px; color: var(--brand-blue); }
    .info-card ul { padding-left: 18px; margin: 0; line-height: 1.7; color: var(--text-secondary); font-size: 13px; }
  `]
})
export class DpdpDashboardComponent implements OnInit {
  private svc = inject(DpdpService);

  stats: any = {
    total_systems: 0, total_datasets: 0, total_pii_fields: 0,
    active_consents: 0, withdrawn_consents: 0,
    open_rights_requests: 0, active_breaches: 0,
    retention_policies: 0, vendors: 0, compliance_score: 0,
  };

  cards: { label: string; value: number; icon: string; color: string; bg: string }[] = [];

  ngOnInit() {
    this.svc.getDashboard().subscribe({
      next: (d: any) => {
        this.stats = d;
        this.buildCards();
      },
      error: () => this.buildCards(),
    });
  }

  private buildCards() {
    const s = this.stats;
    this.cards = [
      { label: 'Systems', value: s.total_systems, icon: 'dns', color: '#1565C0', bg: '#E3F2FD' },
      { label: 'Datasets', value: s.total_datasets, icon: 'storage', color: '#6A1B9A', bg: '#F3E5F5' },
      { label: 'PII Fields', value: s.total_pii_fields, icon: 'fingerprint', color: '#E65100', bg: '#FFF3E0' },
      { label: 'Active Consents', value: s.active_consents, icon: 'verified_user', color: '#2E7D32', bg: '#E8F5E9' },
      { label: 'Withdrawn', value: s.withdrawn_consents, icon: 'cancel', color: '#C62828', bg: '#FFEBEE' },
      { label: 'Open Requests', value: s.open_rights_requests, icon: 'person_search', color: '#0277BD', bg: '#E1F5FE' },
      { label: 'Active Breaches', value: s.active_breaches, icon: 'report_problem', color: '#BF360C', bg: '#FBE9E7' },
      { label: 'Retention Policies', value: s.retention_policies, icon: 'delete_sweep', color: '#4E342E', bg: '#EFEBE9' },
      { label: 'Vendors', value: s.vendors, icon: 'business', color: '#283593', bg: '#E8EAF6' },
    ];
  }
}
