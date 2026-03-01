import { Component, OnInit, signal, inject, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { WebSocketService } from '../../core/services/websocket.service';
import { Subscription, interval } from 'rxjs';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatProgressSpinnerModule, MatTooltipModule, RouterLink],
  template: `
    <div class="page-header">
      <h1>Dashboard</h1>
      <p>AI Agent Compliance Monitoring Overview</p>
    </div>

    <div class="kpi-grid">
      <div class="kpi-card" matTooltip="Total AI agent pipeline requests scanned for compliance">
        <span class="kpi-label">Total Requests</span>
        <span class="kpi-value">{{ agentStats().total_requests }}</span>
        <span class="kpi-subtitle">Pipelines scanned</span>
      </div>
      <div class="kpi-card" matTooltip="Requests that violated one or more compliance policies">
        <span class="kpi-label">Violations Detected</span>
        <span class="kpi-value" style="color: var(--accent-red)">{{ agentStats().total_violations }}</span>
        <span class="kpi-subtitle">Compliance breaches</span>
      </div>
      <div class="kpi-card" matTooltip="Requests that passed all compliance checks successfully">
        <span class="kpi-label">Clean Requests</span>
        <span class="kpi-value" style="color: var(--accent-green)">{{ agentStats().total_clean }}</span>
        <span class="kpi-subtitle">No issues found</span>
      </div>
      <div class="kpi-card" matTooltip="Average risk score (0–100) across all scanned pipelines. Lower is better.">
        <span class="kpi-label">Avg Risk Score</span>
        <span class="kpi-value" [style.color]="agentStats().avg_risk_score >= 50 ? 'var(--accent-red)' : 'var(--accent-green)'">
          {{ agentStats().avg_risk_score }}
        </span>
        <span class="kpi-subtitle">Across all pipelines</span>
      </div>
      <div class="kpi-card" matTooltip="Percentage of requests that are clean. Aim for 80% or above.">
        <span class="kpi-label">Compliance Score</span>
        <span class="kpi-value" [style.color]="complianceScore() >= 80 ? 'var(--accent-green)' : 'var(--accent-red)'">
          {{ complianceScore() }}%
        </span>
        <span class="kpi-subtitle">Clean / Total ratio</span>
      </div>
      <div class="kpi-card" matTooltip="Number of compliance policies currently active and enforcing rules">
        <span class="kpi-label">Active Policies</span>
        <span class="kpi-value">{{ kpis().active_policies }}</span>
        <span class="kpi-subtitle">Enforcing compliance</span>
      </div>
    </div>

    <!-- Compliance Score Donut -->
    <div class="donut-row">
      <mat-card class="donut-card" matTooltip="Visual compliance breakdown — green is good, red needs attention">
        <svg viewBox="0 0 200 200" class="score-donut">
          <circle cx="100" cy="100" r="80" fill="none" stroke="#EBF0F5" stroke-width="18" />
          <circle cx="100" cy="100" r="80" fill="none"
            [attr.stroke]="complianceScore() >= 80 ? '#1B873F' : complianceScore() >= 50 ? '#C67F17' : '#C42B1C'"
            stroke-width="18" stroke-linecap="round"
            [attr.stroke-dasharray]="complianceDash()"
            transform="rotate(-90 100 100)" />
          <text x="100" y="92" text-anchor="middle" class="score-value">{{ complianceScore() }}%</text>
          <text x="100" y="112" text-anchor="middle" class="score-label">Compliance</text>
        </svg>
        <div class="donut-info">
          <div class="donut-stat"><span class="ds-val" style="color: var(--status-danger)">{{ agentStats().total_violations }}</span><span class="ds-label">Violations</span></div>
          <div class="donut-stat"><span class="ds-val" style="color: var(--status-success)">{{ agentStats().total_clean }}</span><span class="ds-label">Clean</span></div>
          <div class="donut-stat"><span class="ds-val">{{ agentStats().total_requests }}</span><span class="ds-label">Total Scans</span></div>
        </div>
      </mat-card>
    </div>

    <!-- Recent Activity -->
    <div class="cards-row">
      <mat-card class="section-card">
        <mat-card-header>
          <mat-card-title>
            <mat-icon>gpp_bad</mat-icon>
            Recent Violations
          </mat-card-title>
        </mat-card-header>
        <mat-card-content>
          @if (recentViolations().length === 0) {
            <p class="empty-state">No violations detected yet.</p>
          }
          @for (item of recentViolations().slice(0, 6); track item.request_id) {
            <div class="activity-item violation-row">
              <span class="status-dot violation"></span>
              <span class="activity-title">{{ item.title }}</span>
              <span class="activity-time">{{ formatTime(item.created_at) }}</span>
              <div class="activity-tags">
                @for (cls of (item.data_classifications || []).slice(0, 2); track cls) {
                  <span class="mini-tag">{{ cls }}</span>
                }
                @if (item.industry) {
                  <span class="mini-tag industry-tag">{{ item.industry }}</span>
                }
                @if (item.source_app) {
                  <span class="mini-tag agent-tag">{{ item.source_app }}</span>
                }
              </div>
              <span class="activity-risk" [style.color]="item.risk_score >= 80 ? 'var(--status-danger)' : 'var(--status-orange)'">
                {{ item.risk_score }}
              </span>
            </div>
          }
        </mat-card-content>
      </mat-card>

      <mat-card class="section-card">
        <mat-card-header>
          <mat-card-title>
            <mat-icon>check_circle</mat-icon>
            Recent Clean Requests
          </mat-card-title>
        </mat-card-header>
        <mat-card-content>
          @if (recentClean().length === 0) {
            <p class="empty-state">No clean requests yet.</p>
          }
          @for (item of recentClean().slice(0, 6); track item.request_id) {
            <div class="activity-item">
              <span class="status-dot clean"></span>
              <span class="activity-title">{{ item.title }}</span>
              <span class="activity-time">{{ formatTime(item.created_at) }}</span>
              @if (item.source_app) {
                <span class="source-tag">{{ item.source_app }}</span>
              }
            </div>
          }
        </mat-card-content>
      </mat-card>
    </div>

    <div class="bottom-link">
      <a routerLink="/live-monitor" matTooltip="Open the real-time AI traffic monitor with full tool chain details">View Live Monitor for detailed tool chain analysis &rarr;</a>
    </div>
  `,
  styles: [`
    /* ── Dashboard Cards ─────────────────────────────────────────────── */
    .cards-row {
      display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 8px;
    }
    .section-card {
      mat-card-header {
        margin-bottom: 12px;
        mat-card-title {
          display: flex; align-items: center; gap: 8px; font-size: 14px !important; font-weight: 500 !important;
          mat-icon { font-size: 18px; width: 18px; height: 18px; color: var(--brand-blue); }
        }
      }
    }
    .activity-item {
      display: flex; align-items: center; gap: 10px;
      padding: 9px 0; border-bottom: 1px solid var(--border-subtle); font-size: 13px;
      &:last-child { border-bottom: none; }
    }
    .status-dot {
      width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0;
      &.violation { background: var(--status-danger); }
      &.clean { background: var(--status-success); }
    }
    .activity-title {
      flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
      color: var(--text-primary); font-size: 13px;
    }
    .activity-tags { display: flex; gap: 4px; }
    .mini-tag {
      font-size: 10px; padding: 1px 6px; border-radius: 100px;
      background: var(--tint-danger); color: var(--status-danger); font-weight: 600;
      letter-spacing: 0.3px;
    }
    .industry-tag { background: #E8F5E9; color: #2E7D32; }
    .agent-tag { background: var(--brand-blue-muted); color: var(--brand-blue); }
    .activity-risk { font-size: 12px; font-weight: 600; }
    .source-tag {
      font-size: 10px; padding: 2px 8px; border-radius: 100px;
      background: var(--brand-blue-muted); color: var(--brand-blue); font-weight: 500;
    }
    .activity-time {
      font-size: 10px; color: var(--text-disabled); white-space: nowrap; flex-shrink: 0;
    }
    .empty-state {
      color: var(--text-disabled); text-align: center;
      padding: 40px 20px; font-size: 13px;
    }

    /* ── Compliance Donut ──────────────────────────────────────────── */
    .donut-row { margin-top: 8px; }
    .donut-card {
      display: flex !important; align-items: center; gap: 32px;
      padding: 20px 32px !important;
    }
    .score-donut { width: 140px; height: 140px; flex-shrink: 0; }
    .score-value { font-size: 32px; font-weight: 700; fill: var(--text-primary); }
    .score-label { font-size: 12px; fill: var(--text-disabled); }
    .donut-info { display: flex; gap: 32px; }
    .donut-stat { display: flex; flex-direction: column; align-items: center; }
    .ds-val { font-size: 28px; font-weight: 700; color: var(--text-primary); }
    .ds-label { font-size: 11px; color: var(--text-disabled); margin-top: 2px; }

    .bottom-link {
      margin-top: 20px; text-align: center;
      a { color: var(--brand-blue); font-size: 13px; text-decoration: none; font-weight: 500;
        &:hover { text-decoration: underline; }
      }
    }
  `],
})
export class DashboardComponent implements OnInit, OnDestroy {
  private api = inject(ApiService);
  private ws = inject(WebSocketService);
  private pollSub?: Subscription;
  private wsSub?: Subscription;

  kpis = signal<any>({
    total_interceptions: 0, total_blocked: 0, total_redacted: 0,
    total_allowed: 0, compliance_score: 100, active_policies: 0,
    active_endpoints: 0, avg_processing_time_ms: 0,
  });
  agentStats = signal<any>({
    total_requests: 0, total_violations: 0, total_clean: 0, avg_risk_score: 0,
  });
  recentViolations = signal<any[]>([]);
  recentClean = signal<any[]>([]);

  complianceScore() {
    const s = this.agentStats();
    if (!s.total_requests) return 100;
    return Math.round((s.total_clean / s.total_requests) * 100);
  }

  complianceDash(): string {
    const C = 2 * Math.PI * 80;
    const pct = this.complianceScore() / 100;
    return `${pct * C} ${C}`;
  }

  formatTime(ts: string | undefined): string {
    if (!ts) return '';
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
        + ' ' + d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch { return ''; }
  }

  ngOnInit() {
    this.loadData();
    this.pollSub = interval(5000).subscribe(() => this.loadData());
    this.wsSub = this.ws.connect('interceptions').subscribe(() => this.loadData());
  }

  ngOnDestroy() {
    this.pollSub?.unsubscribe();
    this.wsSub?.unsubscribe();
  }

  private loadData() {
    this.api.getDashboardKpis().subscribe({ next: (d) => this.kpis.set(d), error: () => {} });
    this.api.getAgentRequestStats().subscribe({ next: (d) => this.agentStats.set(d), error: () => {} });
    this.api.listAgentRequests(8, 'VIOLATION').subscribe({ next: (d) => this.recentViolations.set(d), error: () => {} });
    this.api.listAgentRequests(8, 'CLEAN').subscribe({ next: (d) => this.recentClean.set(d), error: () => {} });
  }
}
