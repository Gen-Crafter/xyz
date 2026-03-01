import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-blocked-agents',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatButtonModule, MatSnackBarModule],
  template: `
    <div class="page-header">
      <h1>Blocked Deployments</h1>
      <p>Manage deployments automatically blocked due to repeated compliance violations</p>
    </div>

    <div class="toolbar">
      <button mat-stroked-button (click)="load()">
        <mat-icon>refresh</mat-icon> Refresh
      </button>
    </div>

    @if (loading()) {
      <div class="empty-state">Loading…</div>
    } @else if (agents().length === 0) {
      <div class="empty-state">
        <mat-icon class="empty-icon">check_circle</mat-icon>
        <h3>No Blocked Deployments</h3>
        <p>All deployments are currently allowed to submit requests.</p>
      </div>
    } @else {
      <div class="agent-grid">
        @for (agent of agents(); track agent.source_app) {
          <mat-card class="agent-card">
            <div class="agent-header">
              <mat-icon class="agent-icon blocked">block</mat-icon>
              <div class="agent-info">
                <h3>{{ agent.source_app }}</h3>
                <span class="blocked-since">Blocked since {{ formatDate(agent.blocked_at) }}</span>
              </div>
            </div>
            <div class="agent-details">
              @if (agent.reason) {
                <div class="reason">
                  <mat-icon>info</mat-icon>
                  <span>{{ agent.reason }}</span>
                </div>
              }
              @if (agent.violation_count) {
                <div class="stat-row">
                  <span class="stat-label">Violations</span>
                  <span class="stat-value danger">{{ agent.violation_count }}</span>
                </div>
              }
            </div>
            <div class="agent-actions">
              <button mat-raised-button color="primary" (click)="unblock(agent.source_app)"
                      [disabled]="unblocking() === agent.source_app">
                <mat-icon>lock_open</mat-icon>
                {{ unblocking() === agent.source_app ? 'Unblocking…' : 'Unblock Deployment' }}
              </button>
            </div>
          </mat-card>
        }
      </div>
    }
  `,
  styles: [`
    .toolbar { margin-bottom: 16px; }

    .empty-state {
      text-align: center; padding: 64px 24px; color: var(--text-secondary);
    }
    .empty-icon {
      font-size: 48px; width: 48px; height: 48px;
      color: var(--status-success); margin-bottom: 12px;
    }
    .empty-state h3 { font-size: 18px; font-weight: 500; color: var(--text-primary); margin-bottom: 4px; }
    .empty-state p { font-size: 13px; color: var(--text-secondary); }

    .agent-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 16px;
    }

    .agent-card { padding: 20px; }

    .agent-header {
      display: flex; align-items: center; gap: 12px; margin-bottom: 16px;
    }
    .agent-icon {
      font-size: 32px; width: 32px; height: 32px;
    }
    .agent-icon.blocked { color: var(--status-danger, #E8262B); }

    .agent-info { flex: 1; }
    .agent-info h3 { font-size: 16px; font-weight: 600; margin: 0 0 2px 0; color: var(--text-primary); }
    .blocked-since { font-size: 12px; color: var(--text-secondary); }

    .agent-details { margin-bottom: 16px; }
    .reason {
      display: flex; align-items: flex-start; gap: 8px;
      padding: 10px 12px; border-radius: 6px;
      background: rgba(232, 38, 43, 0.06);
      font-size: 13px; color: var(--text-secondary);
      margin-bottom: 8px;
      mat-icon { font-size: 16px; width: 16px; height: 16px; color: var(--status-danger, #E8262B); margin-top: 1px; flex-shrink: 0; }
    }

    .stat-row {
      display: flex; justify-content: space-between; align-items: center;
      padding: 4px 0; font-size: 13px;
    }
    .stat-label { color: var(--text-secondary); }
    .stat-value { font-weight: 600; }
    .stat-value.danger { color: var(--status-danger, #E8262B); }

    .agent-actions {
      display: flex; justify-content: flex-end;
      padding-top: 12px; border-top: 1px solid var(--border, #eee);
    }
  `],
})
export class BlockedAgentsComponent implements OnInit {
  private api = inject(ApiService);
  private snackBar = inject(MatSnackBar);

  agents = signal<any[]>([]);
  loading = signal(false);
  unblocking = signal<string | null>(null);

  ngOnInit() { this.load(); }

  load() {
    this.loading.set(true);
    this.api.listBlockedAgents().subscribe({
      next: (data) => { this.agents.set(data); this.loading.set(false); },
      error: () => { this.agents.set([]); this.loading.set(false); },
    });
  }

  unblock(sourceApp: string) {
    this.unblocking.set(sourceApp);
    this.api.unblockAgent(sourceApp).subscribe({
      next: () => {
        this.snackBar.open(`Deployment "${sourceApp}" has been unblocked`, 'OK', { duration: 3000 });
        this.unblocking.set(null);
        this.load();
      },
      error: () => {
        this.snackBar.open(`Failed to unblock deployment "${sourceApp}"`, 'OK', { duration: 3000 });
        this.unblocking.set(null);
      },
    });
  }

  formatDate(ts: string): string {
    if (!ts) return '—';
    const d = new Date(ts);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
         + ' ' + d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  }
}

