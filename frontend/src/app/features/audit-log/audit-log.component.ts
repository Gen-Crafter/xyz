import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-audit-log',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatButtonModule, MatTableModule, MatSnackBarModule, DatePipe],
  template: `
    <div class="page-header">
      <h1>Audit Log</h1>
      <p>Tamper-evident record of all interceptions and actions</p>
    </div>

    <div class="toolbar">
      <button mat-raised-button (click)="verifyChain()">
        <mat-icon>verified</mat-icon> Verify Hash Chain
      </button>
      <button mat-stroked-button (click)="exportLogs()">
        <mat-icon>download</mat-icon> Export
      </button>
      @if (chainStatus()) {
        <span class="chain-status" [class.valid]="chainStatus().valid" [class.invalid]="!chainStatus().valid">
          <mat-icon>{{ chainStatus().valid ? 'check_circle' : 'error' }}</mat-icon>
          {{ chainStatus().valid ? 'Hash chain valid' : 'Chain broken at entry ' + chainStatus().broken_at }}
          ({{ chainStatus().entries_checked }} entries checked)
        </span>
      }
    </div>

    <mat-card>
      <table mat-table [dataSource]="logs()" class="audit-table">
        <ng-container matColumnDef="id">
          <th mat-header-cell *matHeaderCellDef>ID</th>
          <td mat-cell *matCellDef="let row">{{ row.id }}</td>
        </ng-container>
        <ng-container matColumnDef="event_type">
          <th mat-header-cell *matHeaderCellDef>Event</th>
          <td mat-cell *matCellDef="let row">
            <span class="badge badge-audit">{{ row.event_type }}</span>
          </td>
        </ng-container>
        <ng-container matColumnDef="details">
          <th mat-header-cell *matHeaderCellDef>Details</th>
          <td mat-cell *matCellDef="let row" class="details-cell">
            {{ formatDetails(row.details) }}
          </td>
        </ng-container>
        <ng-container matColumnDef="hash">
          <th mat-header-cell *matHeaderCellDef>Hash</th>
          <td mat-cell *matCellDef="let row" class="hash-cell">
            <code>{{ row.current_hash?.substring(0, 12) }}...</code>
          </td>
        </ng-container>
        <ng-container matColumnDef="created_at">
          <th mat-header-cell *matHeaderCellDef>Time</th>
          <td mat-cell *matCellDef="let row">{{ row.created_at | date:'short' }}</td>
        </ng-container>
        <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
        <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
      </table>
    </mat-card>

    @if (logs().length === 0) {
      <div class="empty-state">
        <mat-icon>history</mat-icon>
        <p>No audit entries yet. Process some interceptions to populate the log.</p>
      </div>
    }
  `,
  styles: [`
    .toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
    .chain-status {
      display: flex; align-items: center; gap: 6px; font-size: 13px; margin-left: auto;
      &.valid { color: var(--accent-green); }
      &.invalid { color: var(--accent-red); }
      mat-icon { font-size: 18px; width: 18px; height: 18px; }
    }
    .audit-table { width: 100%; }
    .details-cell { max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
    .hash-cell code { font-size: 11px; color: var(--accent-purple); }
    .empty-state {
      text-align: center; padding: 60px; color: var(--text-secondary);
      mat-icon { font-size: 48px; width: 48px; height: 48px; margin-bottom: 12px; }
    }
  `],
})
export class AuditLogComponent implements OnInit {
  private api = inject(ApiService);
  private snackBar = inject(MatSnackBar);

  logs = signal<any[]>([]);
  chainStatus = signal<any>(null);
  displayedColumns = ['id', 'event_type', 'details', 'hash', 'created_at'];

  ngOnInit() { this.load(); }

  load() {
    this.api.listAuditLogs(100).subscribe({ next: (d) => this.logs.set(d), error: () => {} });
  }

  verifyChain() {
    this.api.verifyHashChain().subscribe({
      next: (r) => this.chainStatus.set(r),
      error: () => this.snackBar.open('Verification failed', 'OK', { duration: 3000 }),
    });
  }

  exportLogs() {
    this.api.exportAuditLogs().subscribe({
      next: (data) => {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = 'audit-log-export.json'; a.click();
        URL.revokeObjectURL(url);
      },
      error: () => this.snackBar.open('Export failed', 'OK', { duration: 3000 }),
    });
  }

  formatDetails(details: any): string {
    if (!details) return '';
    return JSON.stringify(details).substring(0, 100);
  }
}
