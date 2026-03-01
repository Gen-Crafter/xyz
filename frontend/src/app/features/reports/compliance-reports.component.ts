import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-compliance-reports',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatButtonModule, MatProgressBarModule],
  template: `
    <div class="page-header">
      <h1>Compliance Reports & Trend Analytics</h1>
      <p>Violation trends, top offenders, regulation breakdown, and exportable audit reports</p>
    </div>

    <div class="kpi-grid">
      <div class="kpi-card">
        <span class="kpi-label">Agent Scans (30d)</span>
        <span class="kpi-value">{{ trends().total_scanned }}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">Total Violations</span>
        <span class="kpi-value" style="color: var(--accent-red)">{{ stats().total_violations }}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">Clean Requests</span>
        <span class="kpi-value" style="color: var(--accent-green)">{{ stats().total_clean }}</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">Avg Risk Score</span>
        <span class="kpi-value" [style.color]="stats().avg_risk_score >= 50 ? 'var(--accent-red)' : 'var(--accent-green)'">
          {{ stats().avg_risk_score }}
        </span>
      </div>
    </div>

    @if (loading()) {
      <mat-progress-bar mode="indeterminate"></mat-progress-bar>
    }

    <div class="report-grid">
      <!-- Daily Trend -->
      <mat-card class="report-card span-2">
        <mat-card-header>
          <mat-card-title><mat-icon>trending_up</mat-icon> Violation Frequency (30 days)</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          @if (trends().daily_trend?.length) {
            <div class="chart-area">
              @for (day of trends().daily_trend; track day.date) {
                <div class="chart-col" [title]="day.date + ': ' + day.violations + ' violations / ' + day.total + ' total'">
                  <div class="chart-bar-stack">
                    <div class="chart-bar viol" [style.height.px]="getBarH(day.violations, maxDaily)"></div>
                    <div class="chart-bar clean" [style.height.px]="getBarH(day.clean, maxDaily)"></div>
                  </div>
                  <span class="chart-label">{{ day.date.slice(5) }}</span>
                </div>
              }
            </div>
            <div class="chart-legend">
              <span class="legend-item"><span class="legend-dot viol"></span> Violations</span>
              <span class="legend-item"><span class="legend-dot clean"></span> Clean</span>
            </div>
          } @else {
            <p class="empty-msg">No data in the selected period.</p>
          }
        </mat-card-content>
      </mat-card>

      <!-- Top Offending Tools -->
      <mat-card class="report-card">
        <mat-card-header>
          <mat-card-title><mat-icon>build</mat-icon> Top Offending Tools</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          @for (tool of trends().top_offending_tools; track tool.tool_name) {
            <div class="bar-row">
              <span class="bar-label-text">{{ tool.tool_name }}</span>
              <div class="bar-track">
                <div class="bar-fill fill-red" [style.width.%]="getPercent(tool.count, maxToolCount)"></div>
              </div>
              <span class="bar-count">{{ tool.count }}</span>
            </div>
          }
          @if (!trends().top_offending_tools?.length) {
            <p class="empty-msg">No tool violations recorded yet.</p>
          }
        </mat-card-content>
      </mat-card>

      <!-- Regulation Breakdown -->
      <mat-card class="report-card">
        <mat-card-header>
          <mat-card-title><mat-icon>gavel</mat-icon> Regulation Breakdown</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          @for (reg of trends().regulation_breakdown; track reg.regulation) {
            <div class="bar-row">
              <span class="bar-label-text">{{ reg.regulation }}</span>
              <div class="bar-track">
                <div class="bar-fill fill-orange" [style.width.%]="getPercent(reg.count, maxRegCount)"></div>
              </div>
              <span class="bar-count">{{ reg.count }}</span>
            </div>
          }
          @if (!trends().regulation_breakdown?.length) {
            <p class="empty-msg">No regulation data yet.</p>
          }
        </mat-card-content>
      </mat-card>

      <!-- Severity Distribution -->
      <mat-card class="report-card">
        <mat-card-header>
          <mat-card-title><mat-icon>priority_high</mat-icon> Severity Distribution</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          @for (sev of trends().severity_distribution; track sev.severity) {
            <div class="bar-row">
              <span class="bar-label badge" [class]="'badge-' + sev.severity.toLowerCase()">{{ sev.severity }}</span>
              <div class="bar-track">
                <div class="bar-fill" [class]="'fill-sev-' + sev.severity.toLowerCase()" [style.width.%]="getPercent(sev.count, maxSevCount)"></div>
              </div>
              <span class="bar-count">{{ sev.count }}</span>
            </div>
          }
        </mat-card-content>
      </mat-card>

      <!-- Source App Breakdown -->
      <mat-card class="report-card">
        <mat-card-header>
          <mat-card-title><mat-icon>apps</mat-icon> Source App Breakdown</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          @for (app of trends().source_breakdown; track app.source_app) {
            <div class="bar-row">
              <span class="bar-label-text">{{ app.source_app }}</span>
              <div class="bar-track">
                <div class="bar-fill fill-red" [style.width.px]="getPercent(app.violations, maxAppViol) * 1.5"></div>
                <div class="bar-fill fill-green" [style.width.px]="getPercent(app.total - app.violations, maxAppViol) * 1.5"></div>
              </div>
              <span class="bar-count">{{ app.violations }}/{{ app.total }}</span>
            </div>
          }
          @if (!trends().source_breakdown?.length) {
            <p class="empty-msg">No source app data yet.</p>
          }
        </mat-card-content>
      </mat-card>

      <!-- Export -->
      <mat-card class="report-card">
        <mat-card-header>
          <mat-card-title><mat-icon>download</mat-icon> Export Reports</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <div class="export-options">
            <button mat-raised-button color="primary" (click)="exportAudit()">
              <mat-icon>description</mat-icon> Export Audit Log (JSON)
            </button>
            <p class="export-desc">Download full audit trail for regulatory submission</p>
          </div>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [`
    /* ── Report Grid (dashboard layout) ─────────────────────── */
    .report-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .report-card {
      mat-card-title {
        display: flex; align-items: center; gap: 8px; font-size: 14px !important; font-weight: 500 !important;
        mat-icon { font-size: 18px; width: 18px; height: 18px; color: var(--brand-blue); }
      }
      &.span-2 { grid-column: span 2; }
    }

    /* ── Bar Chart (data-viz) ───────────────────────────────── */
    .chart-area {
      display: flex; align-items: flex-end; gap: 3px; height: 140px;
      padding: 8px 0; overflow-x: auto;
    }
    .chart-col { display: flex; flex-direction: column; align-items: center; min-width: 20px; flex: 1; }
    .chart-bar-stack { display: flex; flex-direction: column-reverse; }
    .chart-bar {
      width: 14px; border-radius: 2px 2px 0 0; min-height: 0; transition: height 0.4s ease;
      &.viol { background: var(--status-danger); }
      &.clean { background: var(--status-success); opacity: 0.4; }
    }
    .chart-label { font-size: 9px; color: var(--text-disabled); margin-top: 4px; writing-mode: vertical-rl; transform: rotate(180deg); height: 36px; }
    .chart-legend { display: flex; gap: 20px; margin-top: 10px; padding-top: 8px; border-top: 1px solid var(--border-subtle); }
    .legend-item { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--text-secondary); }
    .legend-dot { width: 8px; height: 8px; border-radius: 2px;
      &.viol { background: var(--status-danger); }
      &.clean { background: var(--status-success); opacity: 0.4; }
    }

    /* ── Horizontal Bar Rows ──────────────────────────────── */
    .bar-row { display: flex; align-items: center; gap: 12px; margin: 8px 0; }
    .bar-label-text { min-width: 100px; font-size: 12px; font-weight: 400; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .bar-label { min-width: 80px; text-align: center; }
    .bar-track { flex: 1; height: 14px; background: var(--bg-secondary); border-radius: var(--radius-sm); overflow: hidden; display: flex; }
    .bar-fill { height: 100%; border-radius: var(--radius-sm); transition: width 0.5s ease; }
    .fill-red { background: var(--status-danger); }
    .fill-orange { background: var(--status-orange); }
    .fill-green { background: var(--status-success); }
    .fill-sev-critical { background: var(--status-danger); }
    .fill-sev-high { background: var(--status-orange); }
    .fill-sev-medium { background: var(--status-warning); }
    .fill-sev-low { background: var(--status-success); }
    .bar-count { min-width: 36px; text-align: right; font-weight: 600; font-size: 12px; color: var(--text-secondary); }

    /* ── Severity Badges ──────────────────────────────────────────────── */
    .badge {
      font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 100px;
      text-transform: uppercase; letter-spacing: 0.3px; text-align: center;
    }
    .badge-critical { background: rgba(196, 43, 28, 0.1); color: var(--status-danger); }
    .badge-high { background: rgba(212, 107, 8, 0.1); color: var(--status-orange); }
    .badge-medium { background: rgba(198, 127, 23, 0.1); color: var(--status-warning); }
    .badge-low { background: rgba(27, 135, 63, 0.1); color: var(--status-success); }

    /* ── Export Section ───────────────────────────────────────────────── */
    .export-options { padding: 12px 0; }
    .export-desc { color: var(--text-disabled); font-size: 12px; margin-top: 8px; }
    .empty-msg { color: var(--text-disabled); text-align: center; padding: 20px; font-size: 13px; }
  `],
})
export class ComplianceReportsComponent implements OnInit {
  private api = inject(ApiService);

  stats = signal<any>({ total_requests: 0, total_violations: 0, total_clean: 0, avg_risk_score: 0 });
  trends = signal<any>({ daily_trend: [], top_offending_tools: [], regulation_breakdown: [], severity_distribution: [], source_breakdown: [], total_scanned: 0 });
  loading = signal(true);

  maxDaily = 1;
  maxToolCount = 1;
  maxRegCount = 1;
  maxSevCount = 1;
  maxAppViol = 1;

  ngOnInit() {
    this.api.getAgentRequestStats().subscribe({ next: (d) => this.stats.set(d), error: () => {} });
    this.api.getAgentRequestTrends(30).subscribe({
      next: (d) => {
        this.trends.set(d);
        this.loading.set(false);
        this.maxDaily = Math.max(1, ...d.daily_trend.map((x: any) => x.total));
        this.maxToolCount = Math.max(1, ...(d.top_offending_tools || []).map((x: any) => x.count));
        this.maxRegCount = Math.max(1, ...(d.regulation_breakdown || []).map((x: any) => x.count));
        this.maxSevCount = Math.max(1, ...(d.severity_distribution || []).map((x: any) => x.count));
        this.maxAppViol = Math.max(1, ...(d.source_breakdown || []).map((x: any) => x.total));
      },
      error: () => this.loading.set(false),
    });
  }

  getBarH(value: number, max: number): number {
    return max > 0 ? Math.max(1, (value / max) * 120) : 0;
  }

  getPercent(count: number, max: number): number {
    return max > 0 ? (count / max) * 100 : 0;
  }

  exportAudit() {
    this.api.exportAuditLogs().subscribe({
      next: (data) => {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url; a.download = 'compliance-report.json'; a.click();
        URL.revokeObjectURL(url);
      },
    });
  }
}
