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
  selector: 'app-dpdp-rights',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatButtonModule,
            MatSelectModule, MatInputModule, MatFormFieldModule, MatTableModule, FormsModule],
  template: `
    <div class="page">
      <div class="toolbar">
        <h2>Data Principal Rights Requests</h2>
        <button mat-flat-button color="primary" (click)="showForm = !showForm">
          <mat-icon>add</mat-icon> New Request
        </button>
      </div>

      <mat-card class="hint-card">
        <mat-icon>info</mat-icon>
        <div>
          <strong>DPDP Act §11-14 &amp; Rule 5</strong>: Data Principals have the right to access,
          correction, erasure, grievance redressal, and nomination. Requests must be fulfilled
          within prescribed timelines (SLA tracked automatically).
        </div>
      </mat-card>

      @if (showForm) {
        <mat-card class="form-card">
          <h3>Create Rights Request</h3>
          <div class="form-row">
            <mat-form-field appearance="outline">
              <mat-label>Principal ID</mat-label>
              <input matInput [(ngModel)]="form.principal_id" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Request Type</mat-label>
              <mat-select [(ngModel)]="form.request_type">
                <mat-option value="ACCESS">Access</mat-option>
                <mat-option value="CORRECTION">Correction</mat-option>
                <mat-option value="ERASURE">Erasure</mat-option>
                <mat-option value="GRIEVANCE">Grievance</mat-option>
                <mat-option value="NOMINATION">Nomination</mat-option>
              </mat-select>
            </mat-form-field>
            <mat-form-field appearance="outline" class="wide">
              <mat-label>Description</mat-label>
              <input matInput [(ngModel)]="form.description" />
            </mat-form-field>
          </div>
          <div class="form-actions">
            <button mat-flat-button color="primary" (click)="create()">Submit</button>
            <button mat-button (click)="showForm = false">Cancel</button>
          </div>
        </mat-card>
      }

      <mat-card class="table-card">
        <table mat-table [dataSource]="requests" class="full-table">
          <ng-container matColumnDef="request_type">
            <th mat-header-cell *matHeaderCellDef>Type</th>
            <td mat-cell *matCellDef="let row">
              <span class="type-badge">{{ row.request_type }}</span>
            </td>
          </ng-container>
          <ng-container matColumnDef="principal_id">
            <th mat-header-cell *matHeaderCellDef>Principal</th>
            <td mat-cell *matCellDef="let row">{{ row.principal_id }}</td>
          </ng-container>
          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef>Status</th>
            <td mat-cell *matCellDef="let row">
              <span class="status-chip" [class]="'st-' + row.status.toLowerCase()">{{ row.status }}</span>
            </td>
          </ng-container>
          <ng-container matColumnDef="sla_due">
            <th mat-header-cell *matHeaderCellDef>SLA Due</th>
            <td mat-cell *matCellDef="let row">{{ row.sla_due | date:'mediumDate' }}</td>
          </ng-container>
          <ng-container matColumnDef="created_at">
            <th mat-header-cell *matHeaderCellDef>Created</th>
            <td mat-cell *matCellDef="let row">{{ row.created_at | date:'medium' }}</td>
          </ng-container>
          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef></th>
            <td mat-cell *matCellDef="let row">
              @if (row.status === 'OPEN') {
                <button mat-icon-button color="primary" (click)="resolve(row.id)" matTooltip="Resolve">
                  <mat-icon>check_circle</mat-icon>
                </button>
              }
            </td>
          </ng-container>
          <tr mat-header-row *matHeaderRowDef="displayedCols"></tr>
          <tr mat-row *matRowDef="let row; columns: displayedCols;"></tr>
        </table>
        @if (!requests.length) {
          <div class="empty">No rights requests yet.</div>
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
      background: #E8F5E9; border-left: 4px solid #43A047;
    }
    .hint-card mat-icon { color: #43A047; margin-top: 2px; }
    .hint-card div { font-size: 13px; color: #1B5E20; line-height: 1.5; }
    .form-card { padding: 20px; display: flex; flex-direction: column; gap: 8px; }
    .form-card h3 { margin: 0 0 4px; font-size: 15px; }
    .form-row { display: flex; gap: 12px; flex-wrap: wrap; }
    .form-row mat-form-field { flex: 1; min-width: 160px; }
    .wide { flex: 2 !important; }
    .form-actions { display: flex; gap: 8px; }
    .table-card { padding: 0; overflow: hidden; }
    .full-table { width: 100%; }
    .type-badge {
      padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;
      background: #E8EAF6; color: #283593;
    }
    .status-chip {
      padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: uppercase;
    }
    .st-open { background: #FFF3E0; color: #E65100; }
    .st-resolved { background: #E8F5E9; color: #2E7D32; }
    .st-closed { background: #ECEFF1; color: #546E7A; }
    .empty { padding: 32px; text-align: center; color: var(--text-disabled); font-size: 13px; }
  `]
})
export class DpdpRightsComponent implements OnInit {
  private svc = inject(DpdpService);
  requests: any[] = [];
  showForm = false;
  form = { principal_id: '', request_type: 'ACCESS', description: '' };
  displayedCols = ['request_type', 'principal_id', 'status', 'sla_due', 'created_at', 'actions'];

  ngOnInit() { this.load(); }
  load() { this.svc.listRights().subscribe({ next: (d: any[]) => this.requests = d, error: () => {} }); }

  create() {
    this.svc.createRight(this.form).subscribe({
      next: () => { this.showForm = false; this.form = { principal_id: '', request_type: 'ACCESS', description: '' }; this.load(); }
    });
  }

  resolve(id: string) {
    this.svc.updateRight(id, { status: 'RESOLVED' }).subscribe({ next: () => this.load() });
  }
}
