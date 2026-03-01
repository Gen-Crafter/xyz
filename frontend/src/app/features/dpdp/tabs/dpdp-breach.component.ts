import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatTableModule } from '@angular/material/table';
import { FormsModule } from '@angular/forms';
import { DpdpService } from '../dpdp.service';

@Component({
  selector: 'app-dpdp-breach',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatButtonModule,
            MatSelectModule, MatInputModule, MatFormFieldModule, MatTableModule, FormsModule],
  template: `
    <div class="page">
      <div class="toolbar">
        <h2>Breach Management</h2>
        <button mat-flat-button color="warn" (click)="showForm = !showForm">
          <mat-icon>add_alert</mat-icon> Report Breach
        </button>
      </div>

      <mat-card class="hint-card warn">
        <mat-icon>warning</mat-icon>
        <div>
          <strong>DPDP Act §8(6) &amp; Rule 8</strong>: Every personal data breach must be reported to
          the Board and each affected Data Principal without delay, and in no case later than 72 hours.
          Include nature of breach, approximate records affected, and measures taken.
        </div>
      </mat-card>

      @if (showForm) {
        <mat-card class="form-card">
          <h3>Report New Breach</h3>
          <div class="form-row">
            <mat-form-field appearance="outline" class="wide">
              <mat-label>Title</mat-label>
              <input matInput [(ngModel)]="form.title" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Severity</mat-label>
              <mat-select [(ngModel)]="form.severity">
                <mat-option value="LOW">Low</mat-option>
                <mat-option value="MEDIUM">Medium</mat-option>
                <mat-option value="HIGH">High</mat-option>
                <mat-option value="CRITICAL">Critical</mat-option>
              </mat-select>
            </mat-form-field>
          </div>
          <mat-form-field appearance="outline" class="full">
            <mat-label>Description</mat-label>
            <textarea matInput [(ngModel)]="form.description" rows="3"></textarea>
          </mat-form-field>
          <div class="form-row">
            <mat-form-field appearance="outline">
              <mat-label>Impacted Records (est.)</mat-label>
              <input matInput type="number" [(ngModel)]="form.impacted_records" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Data Categories (comma-sep)</mat-label>
              <input matInput [(ngModel)]="form.data_categories_raw" />
            </mat-form-field>
          </div>
          <div class="form-actions">
            <button mat-flat-button color="warn" (click)="report()">Report</button>
            <button mat-button (click)="showForm = false">Cancel</button>
          </div>
        </mat-card>
      }

      <mat-card class="table-card">
        <table mat-table [dataSource]="breaches" class="full-table">
          <ng-container matColumnDef="title">
            <th mat-header-cell *matHeaderCellDef>Title</th>
            <td mat-cell *matCellDef="let row">{{ row.title }}</td>
          </ng-container>
          <ng-container matColumnDef="severity">
            <th mat-header-cell *matHeaderCellDef>Severity</th>
            <td mat-cell *matCellDef="let row">
              <span class="sev-chip" [class]="'sev-' + row.severity.toLowerCase()">{{ row.severity }}</span>
            </td>
          </ng-container>
          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef>Status</th>
            <td mat-cell *matCellDef="let row">
              <span class="status-chip" [class]="'st-' + row.status.toLowerCase()">{{ row.status }}</span>
            </td>
          </ng-container>
          <ng-container matColumnDef="impacted_records">
            <th mat-header-cell *matHeaderCellDef>Records</th>
            <td mat-cell *matCellDef="let row">{{ row.impacted_records | number }}</td>
          </ng-container>
          <ng-container matColumnDef="reported_at">
            <th mat-header-cell *matHeaderCellDef>Reported</th>
            <td mat-cell *matCellDef="let row">{{ row.reported_at | date:'medium' }}</td>
          </ng-container>
          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef></th>
            <td mat-cell *matCellDef="let row">
              @if (row.status !== 'RESOLVED') {
                <button mat-icon-button color="primary" (click)="resolve(row.id)">
                  <mat-icon>check_circle</mat-icon>
                </button>
              }
            </td>
          </ng-container>
          <tr mat-header-row *matHeaderRowDef="displayedCols"></tr>
          <tr mat-row *matRowDef="let row; columns: displayedCols;"></tr>
        </table>
        @if (!breaches.length) {
          <div class="empty">No breaches reported.</div>
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
    }
    .hint-card.warn { background: #FFF3E0; border-left: 4px solid #EF6C00; }
    .hint-card.warn mat-icon { color: #EF6C00; margin-top: 2px; }
    .hint-card.warn div { font-size: 13px; color: #BF360C; line-height: 1.5; }
    .form-card { padding: 20px; display: flex; flex-direction: column; gap: 8px; }
    .form-card h3 { margin: 0 0 4px; font-size: 15px; }
    .form-row { display: flex; gap: 12px; flex-wrap: wrap; }
    .form-row mat-form-field { flex: 1; min-width: 160px; }
    .wide { flex: 2 !important; }
    .full { width: 100%; }
    .form-actions { display: flex; gap: 8px; }
    .table-card { padding: 0; overflow: hidden; }
    .full-table { width: 100%; }
    .sev-chip {
      padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: uppercase;
    }
    .sev-low { background: #E8F5E9; color: #2E7D32; }
    .sev-medium { background: #FFF3E0; color: #E65100; }
    .sev-high { background: #FFEBEE; color: #C62828; }
    .sev-critical { background: #880E4F; color: #fff; }
    .status-chip {
      padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: uppercase;
    }
    .st-reported { background: #FFF3E0; color: #E65100; }
    .st-investigating { background: #E1F5FE; color: #0277BD; }
    .st-resolved { background: #E8F5E9; color: #2E7D32; }
    .empty { padding: 32px; text-align: center; color: var(--text-disabled); font-size: 13px; }
  `]
})
export class DpdpBreachComponent implements OnInit {
  private svc = inject(DpdpService);
  breaches: any[] = [];
  showForm = false;
  form = { title: '', severity: 'MEDIUM', description: '', impacted_records: 0, data_categories_raw: '' };
  displayedCols = ['title', 'severity', 'status', 'impacted_records', 'reported_at', 'actions'];

  ngOnInit() { this.load(); }
  load() { this.svc.listBreaches().subscribe({ next: (d: any[]) => this.breaches = d, error: () => {} }); }

  report() {
    const body = {
      title: this.form.title, severity: this.form.severity,
      description: this.form.description, impacted_records: this.form.impacted_records,
      data_categories: this.form.data_categories_raw.split(',').map((s: string) => s.trim()).filter(Boolean),
    };
    this.svc.createBreach(body).subscribe({
      next: () => { this.showForm = false; this.form = { title: '', severity: 'MEDIUM', description: '', impacted_records: 0, data_categories_raw: '' }; this.load(); }
    });
  }

  resolve(id: string) {
    this.svc.updateBreach(id, { status: 'RESOLVED' }).subscribe({ next: () => this.load() });
  }
}
