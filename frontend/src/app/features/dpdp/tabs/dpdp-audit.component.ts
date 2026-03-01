import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { DpdpService } from '../dpdp.service';

@Component({
  selector: 'app-dpdp-audit',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatTableModule, MatButtonModule],
  template: `
    <div class="page">
      <div class="toolbar">
        <h2>Audit &amp; Reports</h2>
        <button mat-stroked-button color="primary" (click)="load()">
          <mat-icon>refresh</mat-icon> Refresh
        </button>
      </div>

      <mat-card class="hint-card">
        <mat-icon>info</mat-icon>
        <div>
          <strong>Rule 6 — Security Safeguards</strong>: Maintain audit logs for at least 1 year.
          All DPDP actions (consent capture/withdrawal, rights requests, breach events, retention
          actions, vendor changes) are automatically logged with actor, timestamp, and evidence.
        </div>
      </mat-card>

      <mat-card class="table-card">
        <table mat-table [dataSource]="events" class="full-table">
          <ng-container matColumnDef="created_at">
            <th mat-header-cell *matHeaderCellDef>Time</th>
            <td mat-cell *matCellDef="let row">{{ row.created_at | date:'medium' }}</td>
          </ng-container>
          <ng-container matColumnDef="actor">
            <th mat-header-cell *matHeaderCellDef>Actor</th>
            <td mat-cell *matCellDef="let row">{{ row.actor }}</td>
          </ng-container>
          <ng-container matColumnDef="action">
            <th mat-header-cell *matHeaderCellDef>Action</th>
            <td mat-cell *matCellDef="let row">
              <span class="action-chip">{{ row.action }}</span>
            </td>
          </ng-container>
          <ng-container matColumnDef="entity_type">
            <th mat-header-cell *matHeaderCellDef>Entity</th>
            <td mat-cell *matCellDef="let row">{{ row.entity_type }}</td>
          </ng-container>
          <ng-container matColumnDef="entity_id">
            <th mat-header-cell *matHeaderCellDef>Entity ID</th>
            <td mat-cell *matCellDef="let row" class="mono">{{ row.entity_id | slice:0:12 }}…</td>
          </ng-container>
          <ng-container matColumnDef="details">
            <th mat-header-cell *matHeaderCellDef>Details</th>
            <td mat-cell *matCellDef="let row" class="details-cell">{{ row.details | json }}</td>
          </ng-container>
          <tr mat-header-row *matHeaderRowDef="displayedCols"></tr>
          <tr mat-row *matRowDef="let row; columns: displayedCols;"></tr>
        </table>
        @if (!events.length) {
          <div class="empty">No audit events recorded yet.</div>
        }
      </mat-card>
    </div>
  `,
  styles: [`
    .page { display: flex; flex-direction: column; gap: 12px; }
    .toolbar { display: flex; align-items: center; justify-content: space-between; }
    .toolbar h2 { margin: 0; font-size: 18px; color: var(--text-primary); }
    .hint-card {
      display: flex; align-items: flex-start; gap: 12px; padding: 16px;
      background: #ECEFF1; border-left: 4px solid #546E7A;
    }
    .hint-card mat-icon { color: #546E7A; margin-top: 2px; }
    .hint-card div { font-size: 13px; color: #263238; line-height: 1.5; }
    .table-card { padding: 0; overflow: hidden; }
    .full-table { width: 100%; }
    .action-chip {
      padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;
      background: #E3F2FD; color: #1565C0;
    }
    .mono { font-family: monospace; font-size: 12px; color: var(--text-secondary); }
    .details-cell {
      max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
      font-size: 12px; color: var(--text-disabled);
    }
    .empty { padding: 32px; text-align: center; color: var(--text-disabled); font-size: 13px; }
  `]
})
export class DpdpAuditComponent implements OnInit {
  private svc = inject(DpdpService);
  events: any[] = [];
  displayedCols = ['created_at', 'actor', 'action', 'entity_type', 'entity_id', 'details'];

  ngOnInit() { this.load(); }
  load() { this.svc.listAudit().subscribe({ next: (d: any[]) => this.events = d, error: () => {} }); }
}
