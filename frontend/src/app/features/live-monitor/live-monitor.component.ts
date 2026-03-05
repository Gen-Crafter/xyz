import { Component, OnInit, OnDestroy, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { ApiService } from '../../core/services/api.service';
import { WebSocketService } from '../../core/services/websocket.service';
import { Subscription } from 'rxjs';
import { jsPDF } from 'jspdf';

@Component({
  selector: 'app-live-monitor',
  standalone: true,
  imports: [CommonModule, FormsModule, MatCardModule, MatIconModule, MatButtonModule,
            MatFormFieldModule, MatInputModule, MatSelectModule, MatChipsModule,
            MatExpansionModule],
  template: `
    <div class="page-header">
      <h1>Live Compliance Monitor</h1>
      <p>Real-time monitoring of AI agent pipeline executions</p>
    </div>

    <div class="controls-bar">
      <mat-form-field appearance="outline" class="filter-field">
        <mat-label>Filter by status</mat-label>
        <mat-select [(value)]="filterStatus" (selectionChange)="applyFilter()">
          <mat-option value="">All</mat-option>
          <mat-option value="VIOLATION">Violations</mat-option>
          <mat-option value="CLEAN">Clean</mat-option>
        </mat-select>
      </mat-form-field>

      <mat-form-field appearance="outline" class="filter-field">
        <mat-label>Filter by deployment</mat-label>
        <mat-select [(value)]="filterDeployment" (selectionChange)="applyFilter()">
          <mat-option value="">All Deployments</mat-option>
          @for (d of deployments(); track d.source_app) {
            <mat-option [value]="d.source_app">
              {{ d.source_app }}
              @if (d.blocked) { <span class="blocked-badge"> BLOCKED</span> }
            </mat-option>
          }
        </mat-select>
      </mat-form-field>

      <button mat-raised-button color="primary" (click)="simulateAgentRequest()">
        <mat-icon>play_arrow</mat-icon>
        Simulate Agent Request
      </button>

      <button mat-stroked-button (click)="loadData()">
        <mat-icon>refresh</mat-icon>
        Refresh
      </button>

      <button mat-stroked-button (click)="exportReport()" [disabled]="filteredRequests().length === 0">
        <mat-icon>download</mat-icon>
        Export Report
      </button>

      <div class="live-indicator">
        <span class="dot green pulse"></span>
        <span>LIVE</span>
      </div>
    </div>

    <div class="request-feed">
      @if (agentRequests().length === 0) {
        <div class="empty-state">
          <mat-icon>monitor_heart</mat-icon>
          <p>Waiting for agent pipeline executions...</p>
          <p class="hint">Click "Simulate Agent Request" to test the compliance pipeline.</p>
        </div>
      }
      @for (req of filteredRequests(); track req.request_id) {
        <mat-card class="request-card" [class]="'card-' + (req.compliance_status || 'PENDING').toLowerCase()">
          <!-- Card Header -->
          <div class="card-header">
            <div class="card-header-left">
              <span class="status-badge" [class]="'status-' + (req.compliance_status || 'PENDING').toLowerCase()">
                @if (req.compliance_status === 'VIOLATION') { <mat-icon>warning</mat-icon> }
                @else if (req.compliance_status === 'CLEAN') { <mat-icon>check_circle</mat-icon> }
                @else { <mat-icon>pending</mat-icon> }
                {{ req.compliance_status || 'PENDING' }}
              </span>
              <span class="card-title">{{ req.title }}</span>
            </div>
            <div class="card-header-right">
              @if (req.risk_score > 0) {
                <span class="risk-badge" [style.color]="req.compliance_status === 'VIOLATION' ? 'var(--status-danger)' : req.risk_score >= 50 ? 'var(--status-warning)' : 'var(--status-success)'">
                  Risk: {{ req.risk_score }}
                </span>
              }
              <span class="card-time">{{ req.processing_time_ms || 0 }}ms</span>
              @if (req.source_app) {
                <span class="source-chip">{{ req.source_app }}</span>
              }
            </div>
          </div>

          <!-- Compact metadata row -->
          <div class="card-meta-row">
            @if (req.recommended_action) {
              <span class="action-badge" [class]="'action-' + req.recommended_action.toLowerCase()">{{ req.recommended_action }}</span>
            }
            @for (reg of uniqueArray(req.regulations_applicable); track reg) {
              <span class="tag tag-regulation">{{ reg }}</span>
            }
            @for (p of req.policies_triggered || []; track p) {
              <span class="tag tag-policy">{{ p }}</span>
            }
            @if (req.industry) {
              <span class="tag tag-industry">{{ req.industry }}</span>
            }
            @if (req.user_name) {
              <span class="tag tag-user"><mat-icon class="tag-icon">person</mat-icon>{{ req.user_name }}</span>
            }
            @if (req.created_at) {
              <span class="tag tag-time"><mat-icon class="tag-icon">schedule</mat-icon>{{ formatTime(req.created_at) }}</span>
            }
            <span class="meta-text">{{ req.violations?.length || 0 }} violation(s) across {{ getUniqueToolCount(req) }} tool(s)</span>
          </div>

          <!-- Violations — collapsible -->
          @if (req.violations?.length) {
            <mat-accordion class="violations-accordion">
              <mat-expansion-panel>
                <mat-expansion-panel-header>
                  <mat-panel-title>
                    <mat-icon class="viol-section-icon">gpp_bad</mat-icon>
                    <span class="viol-section-label">Violations</span>
                    <span class="viol-section-count">{{ req.violations.length }}</span>
                  </mat-panel-title>
                </mat-expansion-panel-header>
                <div class="violations-body">
                  @for (v of req.violations; track $index) {
                    <div class="violation-row">
                      <div class="viol-top">
                        <span class="viol-sev" [class]="'sev-' + (v.severity || 'MEDIUM').toLowerCase()">{{ v.severity }}</span>
                        <span class="viol-tool">{{ v.tool_name }}</span>
                        @if (v.field && v.field !== 'all') { <span class="viol-field">→ {{ v.field }}</span> }
                        <span class="viol-article">{{ v.article }}</span>
                      </div>
                      <div class="viol-desc">{{ v.description }}</div>
                      @if (v.remediation) {
                        <div class="viol-fix">
                          <mat-icon>lightbulb</mat-icon>
                          <span>{{ v.remediation }}</span>
                        </div>
                      }
                    </div>
                  }
                </div>
              </mat-expansion-panel>
            </mat-accordion>
          }

          <!-- Tool Chain Accordion -->
          @if (req.tool_chain?.length) {
            <mat-accordion class="tool-accordion">
              @for (tool of req.tool_chain; track tool.sequence) {
                <mat-expansion-panel>
                  <mat-expansion-panel-header>
                    <mat-panel-title>
                      <span class="tool-seq">{{ tool.sequence }}</span>
                      <span class="tool-name">{{ tool.tool_name }}</span>
                      @if (getToolViolationCount(req, tool.tool_name) > 0) {
                        <span class="tool-violation-badge">{{ getToolViolationCount(req, tool.tool_name) }} violation(s)</span>
                      }
                    </mat-panel-title>
                    <mat-panel-description>
                      <span class="tool-status" [class]="'ts-' + (tool.status || 'SUCCESS').toLowerCase()">{{ tool.status || 'SUCCESS' }}</span>
                      @if (tool.duration_ms) {
                        <span class="tool-duration">{{ tool.duration_ms }}ms</span>
                      }
                    </mat-panel-description>
                  </mat-expansion-panel-header>
                  <div class="tool-body">
                    @if (tool.description) {
                      <div class="tool-desc">{{ tool.description }}</div>
                    }
                    @if (tool.reasoning) {
                      <div class="tool-section">
                        <span class="tool-section-label">Reasoning</span>
                        <div class="tool-section-content">{{ tool.reasoning }}</div>
                      </div>
                    }
                    <div class="tool-io">
                      <div class="tool-section">
                        <span class="tool-section-label">Input</span>
                        <pre class="tool-json">{{ formatJson(tool.input) }}</pre>
                      </div>
                      <div class="tool-section">
                        <span class="tool-section-label">Output</span>
                        <pre class="tool-json">{{ tool.output?.summary || formatJson(tool.output) }}</pre>
                      </div>
                    </div>
                    <!-- Tool-specific violations -->
                    @for (v of getToolViolations(req, tool.tool_name); track $index) {
                      <div class="tool-violation">
                        <mat-icon>warning</mat-icon>
                        <span class="tv-article">{{ v.article }}</span>
                        <span class="tv-desc">{{ v.description }}</span>
                      </div>
                    }
                  </div>
                </mat-expansion-panel>
              }
            </mat-accordion>
          }

          <!-- User Input -->
          @if (req.user_input) {
            <div class="user-input-section">
              <span class="section-label">User Input:</span>
              <span class="user-input-text">{{ req.user_input }}</span>
            </div>
          }
        </mat-card>
      }
    </div>
  `,
  styles: [`
    /* ── Controls Bar (toolbar pattern) ─────────────────────── */
    .controls-bar {
      display: flex; align-items: center; gap: 12px; margin-bottom: 20px;
      padding: 12px 16px; background: var(--bg-card); border: 1px solid var(--border);
      border-radius: var(--radius-md);
    }
    .filter-field {
      width: 180px;
      ::ng-deep .mat-mdc-form-field-subscript-wrapper { display: none; }
    }
    .live-indicator {
      margin-left: auto; display: flex; align-items: center; gap: 8px;
      font-size: 12px; font-weight: 500; color: var(--status-success);
    }
    .dot {
      width: 6px; height: 6px; border-radius: 50%;
      &.green { background: var(--status-success); box-shadow: 0 0 4px var(--status-success); }
      &.pulse { animation: pulse 2s infinite; }
    }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

    /* ── Request Feed ────────────────────────────────────────────────── */
    .request-feed { display: flex; flex-direction: column; gap: 12px; }

    .request-card {
      border-left: 3px solid var(--border); overflow: visible;
      background: var(--bg-card) !important; border-radius: var(--radius-md) !important;
      &.card-violation { border-left-color: var(--status-danger); }
      &.card-clean { border-left-color: var(--status-success); }
      &.card-pending { border-left-color: var(--status-warning); }
    }

    .card-header {
      display: flex; justify-content: space-between; align-items: center;
      padding: 12px 16px; flex-wrap: wrap; gap: 8px;
    }
    .card-header-left { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }
    .card-header-right { display: flex; align-items: center; gap: 10px; }

    .status-badge {
      display: inline-flex; align-items: center; gap: 4px;
      padding: 3px 10px; border-radius: 100px; font-size: 11px; font-weight: 600;
      mat-icon { font-size: 14px; width: 14px; height: 14px; }
    }
    .status-violation { background: var(--tint-danger); color: var(--status-danger); }
    .status-clean { background: var(--tint-success); color: var(--status-success); }
    .status-pending { background: var(--tint-warning); color: var(--status-warning); }

    .card-title { font-weight: 500; font-size: 14px; color: var(--text-primary); }
    .card-time { color: var(--text-disabled); font-size: 11px; }
    .risk-badge { font-size: 12px; font-weight: 600; }
    .source-chip {
      background: var(--brand-blue-muted); color: var(--brand-blue);
      padding: 2px 8px; border-radius: 100px; font-size: 11px; font-weight: 500;
    }

    .card-tags {
      padding: 0 16px 8px; display: flex; gap: 6px; flex-wrap: wrap;
    }
    .tag {
      padding: 2px 8px; border-radius: 100px; font-size: 10px; font-weight: 600;
      letter-spacing: 0.3px;
    }
    .tag-regulation { background: var(--tint-orange); color: var(--status-orange); }
    .tag-policy { background: var(--tint-purple); color: var(--status-purple); }
    .tag-industry { background: #E8F5E9; color: #2E7D32; }
    .tag-user { background: #E3F2FD; color: #1565C0; display: inline-flex; align-items: center; gap: 3px; }
    .tag-time { background: #F3E5F5; color: #7B1FA2; display: inline-flex; align-items: center; gap: 3px; }
    .tag-icon { font-size: 11px; width: 11px; height: 11px; }
    .blocked-badge { color: var(--status-danger); font-weight: 700; font-size: 10px; margin-left: 4px; }

    /* ── Compact metadata row ─────────────────────────────────────────── */
    .card-meta-row {
      display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
      padding: 6px 16px 8px; border-top: 1px solid var(--border-subtle);
    }
    .meta-text { font-size: 11px; color: var(--text-disabled); margin-left: auto; }
    .action-badge {
      font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 100px;
      text-transform: uppercase; letter-spacing: 0.3px;
    }
    .action-block { background: var(--tint-danger); color: var(--status-danger); }
    .action-redact { background: var(--tint-warning); color: var(--status-warning); }
    .action-audit { background: var(--tint-orange); color: var(--status-orange); }
    .action-allow { background: var(--tint-success); color: var(--status-success); }

    /* ── Collapsible Violations ────────────────────────────────────────── */
    .violations-accordion {
      margin: 0 16px 8px;
      ::ng-deep .mat-expansion-panel {
        background: #FFF8F7 !important; border: 1px solid rgba(196, 43, 28, 0.15);
        border-radius: var(--radius-sm) !important; box-shadow: none !important;
      }
      ::ng-deep .mat-expansion-panel-header {
        height: 36px !important; font-size: 13px; padding: 0 14px;
      }
      ::ng-deep .mat-expansion-panel-body { padding: 0 14px 10px; }
    }
    .viol-section-icon { font-size: 16px; width: 16px; height: 16px; color: var(--status-danger); margin-right: 6px; }
    .viol-section-label { font-size: 12px; font-weight: 600; color: var(--status-danger); text-transform: uppercase; letter-spacing: 0.4px; }
    .viol-section-count {
      margin-left: 6px; font-size: 10px; font-weight: 700;
      background: var(--status-danger); color: #fff;
      padding: 1px 7px; border-radius: 100px; min-width: 18px; text-align: center;
    }
    .violations-body { }
    .violation-row {
      padding: 8px 10px; margin-bottom: 4px; border-radius: var(--radius-sm);
      background: #F8F9FB; border-left: 3px solid var(--status-danger);
    }
    .viol-top {
      display: flex; align-items: center; gap: 6px; margin-bottom: 3px; flex-wrap: wrap;
    }
    .viol-sev {
      font-size: 9px; font-weight: 700; padding: 1px 6px; border-radius: 100px;
      text-transform: uppercase; letter-spacing: 0.3px;
    }
    .sev-critical { background: var(--tint-danger); color: var(--status-danger); }
    .sev-high { background: var(--tint-orange); color: var(--status-orange); }
    .sev-medium { background: var(--tint-warning); color: var(--status-warning); }
    .viol-tool {
      font-size: 11px; font-weight: 600; color: var(--text-primary);
      font-family: 'Roboto Mono', monospace;
    }
    .viol-field { font-size: 11px; color: var(--text-disabled); }
    .viol-article {
      margin-left: auto; font-size: 11px; font-weight: 500; color: var(--status-orange);
    }
    .viol-desc {
      font-size: 12px; color: var(--text-secondary); line-height: 1.4;
      word-break: break-word; overflow-wrap: break-word;
    }
    .viol-fix {
      display: flex; align-items: flex-start; gap: 5px; font-size: 11px;
      color: #15713A; margin-top: 4px; padding: 5px 8px;
      background: rgba(27, 135, 63, 0.05); border-radius: var(--radius-sm);
      line-height: 1.4; word-break: break-word; overflow-wrap: break-word;
      mat-icon { font-size: 13px; width: 13px; height: 13px; flex-shrink: 0; margin-top: 1px; color: #15713A; }
      span { word-break: break-word; overflow-wrap: break-word; min-width: 0; }
    }

    /* ── Tool Accordion ──────────────────────────────────────────────── */
    .tool-accordion {
      margin: 0 16px 12px;
      ::ng-deep .mat-expansion-panel { background: var(--bg-secondary) !important; border: 1px solid var(--border-subtle); margin-bottom: 4px; border-radius: var(--radius-sm) !important; }
      ::ng-deep .mat-expansion-panel-header { font-size: 13px; }
    }
    .tool-seq {
      display: inline-flex; justify-content: center; align-items: center;
      width: 20px; height: 20px; border-radius: var(--radius-sm); font-size: 10px; font-weight: 600;
      background: var(--brand-blue-muted); color: var(--brand-blue); margin-right: 8px;
    }
    .tool-name { font-weight: 500; color: var(--text-primary); font-size: 13px; }
    .tool-violation-badge {
      margin-left: 8px; font-size: 10px; font-weight: 600;
      color: var(--status-danger); background: var(--tint-danger);
      padding: 1px 6px; border-radius: 100px;
    }
    .tool-status { font-size: 11px; font-weight: 500; margin-right: 8px; }
    .ts-success { color: var(--status-success); }
    .ts-failed { color: var(--status-danger); }
    .tool-duration { font-size: 11px; color: var(--text-disabled); }

    .tool-body { padding: 8px 0; }
    .tool-desc { font-size: 13px; color: var(--text-secondary); margin-bottom: 10px; }
    .tool-section { margin-bottom: 10px; }
    .tool-section-label {
      font-size: 10px; font-weight: 600; color: var(--text-disabled);
      text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 4px; display: block;
    }
    .tool-section-content { font-size: 13px; color: var(--text-primary); }
    .tool-io { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .tool-json {
      font-family: 'Roboto Mono', monospace; font-size: 11px; white-space: pre-wrap; word-break: break-all;
      background: var(--bg-primary); padding: 10px; border-radius: var(--radius-sm); max-height: 150px;
      overflow-y: auto; color: var(--text-primary); margin: 4px 0 0; border: 1px solid var(--border-subtle);
    }
    .tool-violation {
      display: flex; align-items: center; gap: 6px; padding: 6px 8px;
      margin-top: 8px; border-radius: var(--radius-sm); background: var(--tint-danger);
      font-size: 12px;
      mat-icon { font-size: 14px; width: 14px; height: 14px; color: var(--status-danger); }
    }
    .tv-article { font-weight: 500; color: var(--status-orange); }
    .tv-desc { color: var(--text-secondary); }

    .user-input-section {
      padding: 10px 16px; border-top: 1px solid var(--border-subtle); font-size: 13px;
    }
    .section-label { color: var(--text-disabled); font-weight: 500; margin-right: 8px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.4px; }
    .user-input-text { color: var(--text-primary); }

    .empty-state {
      text-align: center; padding: 60px 20px; color: var(--text-disabled);
      mat-icon { font-size: 48px; width: 48px; height: 48px; margin-bottom: 16px; opacity: 0.5; }
      .hint { font-size: 13px; margin-top: 8px; }
    }
  `],
})
export class LiveMonitorComponent implements OnInit, OnDestroy {
  private api = inject(ApiService);
  private ws = inject(WebSocketService);
  private wsSub?: Subscription;

  agentRequests = signal<any[]>([]);
  deployments = signal<any[]>([]);
  filterStatus = '';
  filterDeployment = '';

  ngOnInit() {
    this.loadData();
    this.loadDeployments();
    this.wsSub = this.ws.connect('interceptions').subscribe((event) => {
      if (event?.type === 'agent_request') {
        this.loadData();
        this.loadDeployments();
      }
    });
  }

  ngOnDestroy() {
    this.wsSub?.unsubscribe();
  }

  loadData() {
    this.api.listAgentRequests(50, undefined, this.filterDeployment || undefined).subscribe({
      next: (data) => this.agentRequests.set(data),
      error: () => {},
    });
  }

  loadDeployments() {
    this.api.listDeployments().subscribe({
      next: (data) => this.deployments.set(data),
      error: () => {},
    });
  }

  filteredRequests() {
    let requests = this.agentRequests();
    if (this.filterStatus) {
      requests = requests.filter(r => r.compliance_status === this.filterStatus);
    }
    return requests;
  }

  applyFilter() {
    this.loadData();
  }

  formatTime(ts: string | undefined): string {
    if (!ts) return '';
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
        + ' · ' + d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch { return ''; }
  }

  getToolViolationCount(req: any, toolName: string): number {
    return (req.violations || []).filter((v: any) => v.tool_name === toolName).length;
  }

  getToolViolations(req: any, toolName: string): any[] {
    return (req.violations || []).filter((v: any) => v.tool_name === toolName);
  }

  uniqueArray(arr: string[] | undefined): string[] {
    return arr ? [...new Set(arr)] : [];
  }

  getUniqueToolCount(req: any): number {
    return new Set((req.violations || []).map((v: any) => v.tool_name)).size;
  }

  formatJson(obj: any): string {
    if (!obj) return '{}';
    try { return JSON.stringify(obj, null, 2); }
    catch { return String(obj); }
  }

  exportReport() {
    const requests = this.filteredRequests();
    this.generatePdf(requests);
  }

  private generatePdf(requests: any[]) {
    const doc = new jsPDF({ unit: 'mm', format: 'a4' });
    const W = 210;
    const M = 18;       // margin
    const TW = W - 2 * M; // text width
    const LH = 4.5;     // line height
    let y = 0;
    let pageNum = 1;
    const brandBlue: [number, number, number] = [76, 111, 255];
    const brandDark: [number, number, number] = [20, 33, 61];
    const darkGray: [number, number, number] = [51, 51, 51];
    const medGray: [number, number, number] = [102, 102, 102];
    const ltGray: [number, number, number] = [153, 153, 153];
    const dangerRed: [number, number, number] = [196, 43, 28];
    const successGreen: [number, number, number] = [27, 135, 63];
    const warningAmber: [number, number, number] = [198, 127, 23];
    const now = new Date();

    const checkPage = (needed: number) => {
      if (y + needed > 272) { addFooter(); doc.addPage(); pageNum++; y = 20; }
    };

    const txt = (text: string, x: number, size = 9, style = 'normal', color: [number, number, number] = darkGray, maxW = TW - (x - M)) => {
      doc.setFontSize(size);
      doc.setFont('helvetica', style);
      doc.setTextColor(color[0], color[1], color[2]);
      const lines = doc.splitTextToSize(text || '', maxW);
      for (const line of lines) {
        checkPage(LH);
        doc.text(line, x, y);
        y += LH;
      }
    };

    const hLine = (color: [number, number, number] = [220, 220, 220], width = 0.3) => {
      doc.setDrawColor(color[0], color[1], color[2]);
      doc.setLineWidth(width);
      doc.line(M, y, W - M, y);
      y += 2;
    };

    const addFooter = () => {
      doc.setFontSize(7);
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(153, 153, 153);
      doc.text('GenCrafter  |  CONFIDENTIAL', M, 287);
      doc.setDrawColor(...brandBlue);
      doc.text(`Page ${pageNum}`, W - M - 12, 287);
      doc.setDrawColor(0, 118, 206);
      doc.setLineWidth(0.4);
      doc.line(M, 284, W - M, 284);
    };

    // ═══════ COVER / HEADER SECTION ═══════
    // Brand header bar
    doc.setFillColor(...brandBlue);
    doc.rect(0, 0, W, 42, 'F');

    // White text on blue
    doc.setFontSize(10);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(255, 255, 255);
    doc.text('GENCRAFTER', M, 14);

    doc.setFontSize(20);
    doc.setFont('helvetica', 'bold');
    doc.text('GenCrafter Compliance Report', M, 26);

    doc.setFontSize(9);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(200, 225, 255);
    doc.text('Enterprise Compliance — Automated Scan Results', M, 33);

    y = 52;

    // Report metadata block
    doc.setFillColor(245, 247, 250);
    doc.setDrawColor(220, 225, 230);
    doc.roundedRect(M, y - 2, TW, 20, 2, 2, 'FD');

    doc.setFontSize(8);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(102, 102, 102);
    doc.text('REPORT DATE', M + 4, y + 4);
    doc.text('TOTAL REQUESTS', M + 50, y + 4);
    doc.text('VIOLATIONS', M + 100, y + 4);
    doc.text('CLEAN', M + 140, y + 4);

    const totalViol = requests.filter(r => r.compliance_status === 'VIOLATION').length;
    const totalClean = requests.filter(r => r.compliance_status === 'CLEAN').length;

    doc.setFontSize(10);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(51, 51, 51);
    doc.text(now.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }), M + 4, y + 12);
    doc.text(String(requests.length), M + 50, y + 12);
    doc.setTextColor(dangerRed[0], dangerRed[1], dangerRed[2]);
    doc.text(String(totalViol), M + 100, y + 12);
    doc.setTextColor(successGreen[0], successGreen[1], successGreen[2]);
    doc.text(String(totalClean), M + 140, y + 12);

    y += 26;
    hLine(brandBlue, 0.6);
    y += 2;

    // ═══════ REQUEST DETAILS ═══════
    for (let i = 0; i < requests.length; i++) {
      const req = requests[i];
      const isViol = req.compliance_status === 'VIOLATION';

      checkPage(30);

      // Request title bar
      const titleColor = isViol ? dangerRed : successGreen;
      const statusLabel = isViol ? 'VIOLATION' : 'CLEAN';

      // Status pill background
      doc.setFontSize(7);
      doc.setFont('helvetica', 'bold');
      const pillW = doc.getTextWidth(statusLabel) + 6;
      const actualPillW = Math.max(pillW, 20);
      doc.setFillColor(titleColor[0], titleColor[1], titleColor[2]);
      doc.roundedRect(M, y - 3.5, actualPillW, 5, 1.5, 1.5, 'F');
      doc.setTextColor(255, 255, 255);
      doc.text(statusLabel, M + 3, y);

      // Title (wrapped)
      const titleX = M + actualPillW + 4;
      const titleMaxW = W - M - titleX;
      doc.setFontSize(11);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(titleColor[0], titleColor[1], titleColor[2]);
      const titleLines = doc.splitTextToSize(req.title || 'Untitled Request', titleMaxW);
      doc.text(titleLines[0], titleX, y);
      y += 5;
      for (let tl = 1; tl < titleLines.length; tl++) {
        checkPage(5);
        doc.text(titleLines[tl], M, y);
        y += 5;
      }

      // Metadata line
      const meta = [
        `ID: ${req.request_id}`,
        `Source: ${req.source_app || 'N/A'}`,
        `Risk: ${req.risk_score}`,
        `Action: ${req.recommended_action || 'N/A'}`
      ].join('  |  ');
      txt(meta, M, 8, 'normal', medGray);

      // Scan summary
      if (req.scan_summary) {
        txt(req.scan_summary, M, 8, 'italic', ltGray);
      }

      // Data types & regulations
      const types = [...new Set([...(req.data_classifications || []), ...(req.regulations_applicable || [])])];
      if (types.length) {
        txt(`Data Types / Regulations: ${types.join(', ')}`, M, 8, 'normal', brandDark);
      }

      // Policies
      if (req.policies_triggered?.length) {
        txt(`Policies Triggered: ${req.policies_triggered.join(', ')}`, M, 8, 'normal', [107, 63, 160]);
      }

      // Violations
      if (req.violations?.length) {
        y += 2;
        txt(`Violations (${req.violations.length}):`, M + 2, 9, 'bold', dangerRed);
        y += 1;

        const indent = M + 4;
        const indent2 = M + 8;
        const contentW = TW - 8;
        const contentW2 = TW - 12;

        for (const v of req.violations) {
          checkPage(20);

          // Colored left bar + severity pill + article
          const sevColor: [number, number, number] = v.severity === 'CRITICAL' ? dangerRed : v.severity === 'HIGH' ? [212, 107, 8] : warningAmber;

          // Severity pill
          doc.setFontSize(7);
          doc.setFont('helvetica', 'bold');
          const sevText = v.severity || 'MEDIUM';
          const sevW = doc.getTextWidth(sevText) + 5;
          doc.setFillColor(sevColor[0], sevColor[1], sevColor[2]);
          doc.roundedRect(indent, y - 3, sevW, 4, 1, 1, 'F');
          doc.setTextColor(255, 255, 255);
          doc.text(sevText, indent + 2.5, y - 0.3);

          // Article next to pill
          if (v.article) {
            doc.setFontSize(8);
            doc.setFont('helvetica', 'bold');
            doc.setTextColor(sevColor[0], sevColor[1], sevColor[2]);
            doc.text(v.article, indent + sevW + 3, y - 0.3);
          }

          // Tool name — right aligned
          doc.setFontSize(7);
          doc.setFont('helvetica', 'normal');
          doc.setTextColor(ltGray[0], ltGray[1], ltGray[2]);
          const toolStr = v.tool_name + (v.field && v.field !== 'all' ? ' → ' + v.field : '');
          const toolStrW = doc.getTextWidth(toolStr);
          doc.text(toolStr, W - M - toolStrW, y - 0.3);

          y += 4;

          // Description — full width wrapped
          doc.setFontSize(8);
          doc.setFont('helvetica', 'normal');
          doc.setTextColor(darkGray[0], darkGray[1], darkGray[2]);
          const descLines = doc.splitTextToSize(v.description || '', contentW2);
          for (const dl of descLines) {
            checkPage(LH);
            doc.text(dl, indent2, y);
            y += LH;
          }

          // Remediation — green box
          if (v.remediation) {
            checkPage(8);
            doc.setFontSize(7.5);
            doc.setFont('helvetica', 'italic');
            const remLines = doc.splitTextToSize('Remediation: ' + v.remediation, contentW2 - 4);
            const remH = remLines.length * LH + 2;

            doc.setFillColor(240, 249, 243);
            doc.setDrawColor(27, 135, 63);
            doc.setLineWidth(0.2);
            doc.roundedRect(indent2, y - 1, contentW2, remH, 1, 1, 'FD');

            doc.setTextColor(successGreen[0], successGreen[1], successGreen[2]);
            y += 1.5;
            for (const rl of remLines) {
              checkPage(LH);
              doc.text(rl, indent2 + 2, y);
              y += LH;
            }
            y += 1;
          }

          y += 2;
        }
      }

      // Tool Chain
      if (req.tool_chain?.length) {
        checkPage(10);
        y += 1;
        txt('Tool Chain:', M + 2, 9, 'bold', brandBlue);
        for (const tool of req.tool_chain) {
          checkPage(6);
          txt(`${tool.sequence}. ${tool.tool_name} (${tool.status || 'SUCCESS'}, ${tool.duration_ms || 0}ms)`, M + 6, 8, 'normal', medGray);
        }
      }

      y += 3;
      if (i < requests.length - 1) {
        hLine();
        y += 2;
      }
    }

    // ═══════ FOOTER ON LAST PAGE ═══════
    addFooter();

    doc.save(`compliance-report-${now.toISOString().slice(0, 10)}.pdf`);
  }

  simulateAgentRequest() {
    const samples = [
      {
        request_id: 'REQ-' + Date.now(),
        title: 'EU Customer Data Export to External Analytics',
        source_app: 'data-analytics-agent',
        user_name: 'Sarah Johnson',
        status: 'COMPLETED',
        user_input: 'Export all EU customer records including SSN and payment info for the analytics dashboard',
        tool_chain: [
          { tool_name: 'database_query', description: 'Query customer database', sequence: 1, input: { query: "SELECT name, ssn, email, credit_card FROM customers WHERE region='EU'" }, output: { summary: 'Retrieved 1,247 records including SSN 234-56-7890 and credit card 4532-0151-2345-6789', record_count: 1247 }, reasoning: 'Querying all fields to fulfill export request', duration_ms: 340, status: 'SUCCESS' },
          { tool_name: 'data_formatter', description: 'Format data for CSV export', sequence: 2, input: { format: 'csv', records: 1247 }, output: { summary: 'Formatted 1,247 records with unmasked PII columns' }, reasoning: 'Converting to CSV for analytics platform', duration_ms: 120, status: 'SUCCESS' },
          { tool_name: 'transfer_agent', description: 'Transfer to external vendor', sequence: 3, input: { destination: 'https://analytics.external-vendor.com/upload' }, output: { summary: 'Uploaded customer data to external vendor outside EU jurisdiction' }, reasoning: 'Sending to third-party analytics service', duration_ms: 1500, status: 'SUCCESS' },
        ],
        final_output: { summary: 'Exported 1,247 EU customer records to external analytics vendor' },
        metadata: { model: 'gpt-4', total_tokens: 4521 },
      },
      {
        request_id: 'REQ-' + Date.now(),
        title: 'Patient Record Summarization for Insurance',
        source_app: 'clinical-assistant',
        user_name: 'Dr. James Wilson',
        status: 'COMPLETED',
        user_input: 'Summarize patient Maria Garcia treatment history for insurance claim',
        tool_chain: [
          { tool_name: 'ehr_lookup', description: 'Query electronic health records', sequence: 1, input: { patient_id: 'P-44782', fields: ['diagnosis', 'medications', 'treatment'] }, output: { summary: 'Patient Maria Garcia, MRN 4478291, diagnosed with Type 2 Diabetes. Current prescription: Metformin 500mg, Lisinopril 10mg' }, reasoning: 'Looking up complete medical history', duration_ms: 250, status: 'SUCCESS' },
          { tool_name: 'summarizer', description: 'Generate treatment summary', sequence: 2, input: { template: 'insurance_claim' }, output: { summary: 'Generated 2-page treatment summary including diagnosis codes ICD-10 E11.9, medication history, and lab results' }, reasoning: 'Creating formatted summary for insurance claim submission', duration_ms: 800, status: 'SUCCESS' },
          { tool_name: 'email_sender', description: 'Send summary via email', sequence: 3, input: { to: 'claims@insurance-co.com', subject: 'Treatment Summary - Maria Garcia' }, output: { summary: 'Sent treatment summary with full PHI to external insurance email' }, reasoning: 'Delivering completed summary to insurance company', duration_ms: 200, status: 'SUCCESS' },
        ],
        final_output: { summary: 'Treatment summary sent to insurance company via email' },
        metadata: { model: 'gpt-4', total_tokens: 3200 },
      },
      {
        request_id: 'REQ-' + Date.now(),
        title: 'Code Review — Infrastructure Config',
        source_app: 'devops-copilot',
        user_name: 'Alex Chen',
        status: 'COMPLETED',
        user_input: 'Review and optimize our deployment configuration',
        tool_chain: [
          { tool_name: 'config_reader', description: 'Read deployment config files', sequence: 1, input: { path: '/etc/app/config.yml' }, output: { summary: 'Read config: DB_PASSWORD=SuperSecret123!, AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE, REDIS_URL=redis://cache:6379' }, reasoning: 'Reading current deployment configuration', duration_ms: 50, status: 'SUCCESS' },
          { tool_name: 'optimizer', description: 'Suggest optimizations', sequence: 2, input: { config: 'current deployment settings' }, output: { summary: 'Recommended: connection pooling, caching layer, secret rotation' }, reasoning: 'Analyzing configuration for performance improvements', duration_ms: 600, status: 'SUCCESS' },
        ],
        final_output: { summary: 'Config review complete with optimization recommendations' },
        metadata: { model: 'gpt-4o', total_tokens: 2100 },
      },
      {
        request_id: 'REQ-' + Date.now(),
        title: 'Generate Python Sorting Algorithm',
        source_app: 'code-assistant',
        user_name: 'Priya Patel',
        status: 'COMPLETED',
        user_input: 'Write a function to sort a list of dictionaries by key',
        tool_chain: [
          { tool_name: 'code_generator', description: 'Generate Python code', sequence: 1, input: { language: 'python', task: 'sort list of dicts by key' }, output: { summary: 'Generated type-hinted sort function with docstring' }, reasoning: 'Standard coding task with no sensitive data', duration_ms: 300, status: 'SUCCESS' },
        ],
        final_output: { summary: 'Clean code generation — no compliance issues' },
        metadata: { model: 'gpt-4o', total_tokens: 800 },
      },
    ];

    const sample = samples[Math.floor(Math.random() * samples.length)];
    sample.request_id = 'REQ-' + Date.now();
    this.api.ingestAgentRequest(sample).subscribe({
      next: () => this.loadData(),
      error: (err) => console.error('Simulation failed:', err),
    });
  }
}
