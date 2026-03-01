import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatTableModule } from '@angular/material/table';
import { FormsModule } from '@angular/forms';
import { DpdpService } from '../dpdp.service';

@Component({
  selector: 'app-dpdp-retention',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatButtonModule,
            MatInputModule, MatFormFieldModule, MatSlideToggleModule, MatTableModule, FormsModule],
  template: `
    <div class="page">
      <div class="toolbar">
        <h2>Retention &amp; Deletion</h2>
        <button mat-flat-button color="primary" (click)="showForm = !showForm">
          <mat-icon>add</mat-icon> Add Policy
        </button>
      </div>

      <mat-card class="hint-card">
        <mat-icon>info</mat-icon>
        <div>
          <strong>DPDP Act §8(7)</strong>: Personal data must be erased when consent is withdrawn or
          the specified purpose is no longer being served, unless retention is required by law.
        </div>
      </mat-card>

      @if (showForm) {
        <mat-card class="form-card">
          <h3>New Retention Policy</h3>
          <div class="form-row">
            <mat-form-field appearance="outline">
              <mat-label>Policy Name</mat-label>
              <input matInput [(ngModel)]="form.name" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Purpose</mat-label>
              <input matInput [(ngModel)]="form.purpose" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Retention (days)</mat-label>
              <input matInput type="number" [(ngModel)]="form.retention_days" />
            </mat-form-field>
          </div>
          <div class="form-row">
            <mat-form-field appearance="outline">
              <mat-label>System Scope</mat-label>
              <input matInput [(ngModel)]="form.system_scope" />
            </mat-form-field>
            <mat-slide-toggle [(ngModel)]="form.legal_hold">Legal Hold</mat-slide-toggle>
            <mat-slide-toggle [(ngModel)]="form.auto_delete">Auto Delete</mat-slide-toggle>
          </div>
          <div class="form-actions">
            <button mat-flat-button color="primary" (click)="add()">Save</button>
            <button mat-button (click)="showForm = false">Cancel</button>
          </div>
        </mat-card>
      }

      <mat-card class="table-card">
        <table mat-table [dataSource]="policies" class="full-table">
          <ng-container matColumnDef="name">
            <th mat-header-cell *matHeaderCellDef>Name</th>
            <td mat-cell *matCellDef="let row">{{ row.name }}</td>
          </ng-container>
          <ng-container matColumnDef="purpose">
            <th mat-header-cell *matHeaderCellDef>Purpose</th>
            <td mat-cell *matCellDef="let row">{{ row.purpose || '—' }}</td>
          </ng-container>
          <ng-container matColumnDef="retention_days">
            <th mat-header-cell *matHeaderCellDef>Days</th>
            <td mat-cell *matCellDef="let row">{{ row.retention_days }}</td>
          </ng-container>
          <ng-container matColumnDef="system_scope">
            <th mat-header-cell *matHeaderCellDef>Scope</th>
            <td mat-cell *matCellDef="let row">{{ row.system_scope }}</td>
          </ng-container>
          <ng-container matColumnDef="legal_hold">
            <th mat-header-cell *matHeaderCellDef>Legal Hold</th>
            <td mat-cell *matCellDef="let row">
              <mat-icon [style.color]="row.legal_hold ? '#C62828' : '#BDBDBD'">
                {{ row.legal_hold ? 'lock' : 'lock_open' }}
              </mat-icon>
            </td>
          </ng-container>
          <ng-container matColumnDef="auto_delete">
            <th mat-header-cell *matHeaderCellDef>Auto-Delete</th>
            <td mat-cell *matCellDef="let row">
              <mat-icon [style.color]="row.auto_delete ? '#2E7D32' : '#BDBDBD'">
                {{ row.auto_delete ? 'check_circle' : 'cancel' }}
              </mat-icon>
            </td>
          </ng-container>
          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef></th>
            <td mat-cell *matCellDef="let row">
              <button mat-icon-button color="warn" (click)="remove(row.id)">
                <mat-icon>delete</mat-icon>
              </button>
            </td>
          </ng-container>
          <tr mat-header-row *matHeaderRowDef="displayedCols"></tr>
          <tr mat-row *matRowDef="let row; columns: displayedCols;"></tr>
        </table>
        @if (!policies.length) {
          <div class="empty">No retention policies defined.</div>
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
      background: #F3E5F5; border-left: 4px solid #8E24AA;
    }
    .hint-card mat-icon { color: #8E24AA; margin-top: 2px; }
    .hint-card div { font-size: 13px; color: #4A148C; line-height: 1.5; }
    .form-card { padding: 20px; display: flex; flex-direction: column; gap: 8px; }
    .form-card h3 { margin: 0 0 4px; font-size: 15px; }
    .form-row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
    .form-row mat-form-field { flex: 1; min-width: 160px; }
    .form-actions { display: flex; gap: 8px; }
    .table-card { padding: 0; overflow: hidden; }
    .full-table { width: 100%; }
    .empty { padding: 32px; text-align: center; color: var(--text-disabled); font-size: 13px; }
  `]
})
export class DpdpRetentionComponent implements OnInit {
  private svc = inject(DpdpService);
  policies: any[] = [];
  showForm = false;
  form = { name: '', purpose: '', retention_days: 365, system_scope: '*', legal_hold: false, auto_delete: false };
  displayedCols = ['name', 'purpose', 'retention_days', 'system_scope', 'legal_hold', 'auto_delete', 'actions'];

  ngOnInit() { this.load(); }
  load() { this.svc.listRetention().subscribe({ next: (d: any[]) => this.policies = d, error: () => {} }); }

  add() {
    this.svc.createRetention(this.form).subscribe({
      next: () => { this.showForm = false; this.form = { name: '', purpose: '', retention_days: 365, system_scope: '*', legal_hold: false, auto_delete: false }; this.load(); }
    });
  }

  remove(id: string) {
    this.svc.deleteRetention(id).subscribe({ next: () => this.load() });
  }
}
