import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatChipsModule } from '@angular/material/chips';
import { MatTableModule } from '@angular/material/table';
import { FormsModule } from '@angular/forms';
import { DpdpService } from '../dpdp.service';

@Component({
  selector: 'app-dpdp-consent',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatButtonModule,
            MatInputModule, MatFormFieldModule, MatChipsModule, MatTableModule, FormsModule],
  template: `
    <div class="page">
      <div class="toolbar">
        <h2>Consent Management</h2>
        <button mat-flat-button color="primary" (click)="showForm = !showForm">
          <mat-icon>add</mat-icon> Capture Consent
        </button>
      </div>

      <mat-card class="hint-card">
        <mat-icon>info</mat-icon>
        <div>
          <strong>DPDP Act §6 — Consent</strong>: Every Data Fiduciary must obtain free, specific, informed,
          unconditional, and unambiguous consent with a clear affirmative action. Consent must be
          itemised per purpose and in a language listed in the Eighth Schedule.
        </div>
      </mat-card>

      @if (showForm) {
        <mat-card class="form-card">
          <h3>New Consent Record</h3>
          <div class="form-row">
            <mat-form-field appearance="outline">
              <mat-label>Data Principal ID</mat-label>
              <input matInput [(ngModel)]="form.principal_id" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Purpose</mat-label>
              <input matInput [(ngModel)]="form.purpose" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Version</mat-label>
              <input matInput [(ngModel)]="form.version" />
            </mat-form-field>
          </div>
          <div class="form-actions">
            <button mat-flat-button color="primary" (click)="capture()">Save</button>
            <button mat-button (click)="showForm = false">Cancel</button>
          </div>
        </mat-card>
      }

      <mat-card class="table-card">
        <table mat-table [dataSource]="consents" class="full-table">
          <ng-container matColumnDef="principal_id">
            <th mat-header-cell *matHeaderCellDef>Principal</th>
            <td mat-cell *matCellDef="let row">{{ row.principal_id }}</td>
          </ng-container>
          <ng-container matColumnDef="purpose">
            <th mat-header-cell *matHeaderCellDef>Purpose</th>
            <td mat-cell *matCellDef="let row">{{ row.purpose }}</td>
          </ng-container>
          <ng-container matColumnDef="version">
            <th mat-header-cell *matHeaderCellDef>Version</th>
            <td mat-cell *matCellDef="let row">{{ row.version }}</td>
          </ng-container>
          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef>Status</th>
            <td mat-cell *matCellDef="let row">
              <span class="status-chip" [class]="'st-' + row.status.toLowerCase()">{{ row.status }}</span>
            </td>
          </ng-container>
          <ng-container matColumnDef="captured_at">
            <th mat-header-cell *matHeaderCellDef>Captured</th>
            <td mat-cell *matCellDef="let row">{{ row.captured_at | date:'medium' }}</td>
          </ng-container>
          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef></th>
            <td mat-cell *matCellDef="let row">
              @if (row.status === 'ACTIVE') {
                <button mat-icon-button color="warn" (click)="withdraw(row.id)" matTooltip="Withdraw">
                  <mat-icon>cancel</mat-icon>
                </button>
              }
            </td>
          </ng-container>
          <tr mat-header-row *matHeaderRowDef="displayedCols"></tr>
          <tr mat-row *matRowDef="let row; columns: displayedCols;"></tr>
        </table>
        @if (!consents.length) {
          <div class="empty">No consent records yet.</div>
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
      background: #E1F5FE; border-left: 4px solid #0288D1;
    }
    .hint-card mat-icon { color: #0288D1; margin-top: 2px; }
    .hint-card div { font-size: 13px; color: #01579B; line-height: 1.5; }
    .form-card { padding: 20px; display: flex; flex-direction: column; gap: 8px; }
    .form-card h3 { margin: 0 0 4px; font-size: 15px; }
    .form-row { display: flex; gap: 12px; flex-wrap: wrap; }
    .form-row mat-form-field { flex: 1; min-width: 180px; }
    .form-actions { display: flex; gap: 8px; }
    .table-card { padding: 0; overflow: hidden; }
    .full-table { width: 100%; }
    .status-chip {
      padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: uppercase;
    }
    .st-active { background: #E8F5E9; color: #2E7D32; }
    .st-withdrawn { background: #FFEBEE; color: #C62828; }
    .empty { padding: 32px; text-align: center; color: var(--text-disabled); font-size: 13px; }
  `]
})
export class DpdpConsentComponent implements OnInit {
  private svc = inject(DpdpService);
  consents: any[] = [];
  showForm = false;
  form = { principal_id: '', purpose: '', version: '1.0' };
  displayedCols = ['principal_id', 'purpose', 'version', 'status', 'captured_at', 'actions'];

  ngOnInit() { this.load(); }

  load() { this.svc.listConsents().subscribe({ next: (d: any[]) => this.consents = d, error: () => {} }); }

  capture() {
    this.svc.captureConsent(this.form).subscribe({
      next: () => { this.showForm = false; this.form = { principal_id: '', purpose: '', version: '1.0' }; this.load(); }
    });
  }

  withdraw(id: string) {
    this.svc.withdrawConsent(id).subscribe({ next: () => this.load() });
  }
}
