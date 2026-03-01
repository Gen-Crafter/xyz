import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatChipsModule } from '@angular/material/chips';
import { FormsModule } from '@angular/forms';
import { DpdpService } from '../dpdp.service';

@Component({
  selector: 'app-dpdp-vendor',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatButtonModule,
            MatInputModule, MatFormFieldModule, MatChipsModule, FormsModule],
  template: `
    <div class="page">
      <div class="toolbar">
        <h2>Vendor Compliance</h2>
        <button mat-flat-button color="primary" (click)="showForm = !showForm">
          <mat-icon>add</mat-icon> Add Vendor
        </button>
      </div>

      <mat-card class="hint-card">
        <mat-icon>info</mat-icon>
        <div>
          <strong>DPDP Act §8(2)</strong>: A Data Fiduciary may engage a Data Processor only under a
          valid contract. The fiduciary remains responsible for ensuring the processor complies with
          DPDP obligations including security safeguards and purpose limitation.
        </div>
      </mat-card>

      @if (showForm) {
        <mat-card class="form-card">
          <h3>Register Vendor / Processor</h3>
          <div class="form-row">
            <mat-form-field appearance="outline">
              <mat-label>Vendor Name</mat-label>
              <input matInput [(ngModel)]="form.name" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Service Type</mat-label>
              <input matInput [(ngModel)]="form.service_type" />
            </mat-form-field>
          </div>
          <div class="form-row">
            <mat-form-field appearance="outline">
              <mat-label>Data Shared (comma-sep)</mat-label>
              <input matInput [(ngModel)]="form.data_shared_raw" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Transfer Basis</mat-label>
              <input matInput [(ngModel)]="form.transfer_basis" />
            </mat-form-field>
          </div>
          <div class="form-actions">
            <button mat-flat-button color="primary" (click)="add()">Save</button>
            <button mat-button (click)="showForm = false">Cancel</button>
          </div>
        </mat-card>
      }

      <div class="grid">
        @for (v of vendors; track v.id) {
          <mat-card class="vendor-card">
            <div class="v-header">
              <mat-icon>business</mat-icon>
              <div>
                <h3>{{ v.name }}</h3>
                <span class="svc-type">{{ v.service_type || '—' }}</span>
              </div>
              <span class="dpa-badge" [class]="'dpa-' + (v.dpa_status || 'PENDING').toLowerCase()">
                DPA: {{ v.dpa_status }}
              </span>
            </div>
            <div class="chips" *ngIf="v.data_shared?.length">
              <span class="chip" *ngFor="let d of v.data_shared">{{ d }}</span>
            </div>
            <div class="v-footer">
              <span class="basis">Basis: {{ v.transfer_basis || '—' }}</span>
              <button mat-icon-button color="warn" (click)="remove(v.id)">
                <mat-icon>delete</mat-icon>
              </button>
            </div>
          </mat-card>
        }
        @if (!vendors.length) {
          <mat-card class="empty">
            <mat-icon>info</mat-icon>
            <span>No vendors registered yet.</span>
          </mat-card>
        }
      </div>
    </div>
  `,
  styles: [`
    .page { display: flex; flex-direction: column; gap: 12px; }
    .toolbar { display: flex; align-items: center; justify-content: space-between; }
    .toolbar h2 { margin: 0; font-size: 18px; color: var(--text-primary); }
    .hint-card {
      display: flex; align-items: flex-start; gap: 12px; padding: 16px;
      background: #E8EAF6; border-left: 4px solid #3F51B5;
    }
    .hint-card mat-icon { color: #3F51B5; margin-top: 2px; }
    .hint-card div { font-size: 13px; color: #1A237E; line-height: 1.5; }
    .form-card { padding: 20px; display: flex; flex-direction: column; gap: 8px; }
    .form-card h3 { margin: 0 0 4px; font-size: 15px; }
    .form-row { display: flex; gap: 12px; flex-wrap: wrap; }
    .form-row mat-form-field { flex: 1; min-width: 180px; }
    .form-actions { display: flex; gap: 8px; }

    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }
    .vendor-card { padding: 16px; display: flex; flex-direction: column; gap: 10px; }
    .v-header { display: flex; align-items: center; gap: 10px; }
    .v-header mat-icon { color: #283593; font-size: 28px; width: 28px; height: 28px; }
    .v-header h3 { margin: 0; font-size: 15px; color: var(--text-primary); }
    .svc-type { font-size: 12px; color: var(--text-secondary); }
    .dpa-badge {
      margin-left: auto; padding: 2px 10px; border-radius: 12px;
      font-size: 11px; font-weight: 600; text-transform: uppercase;
    }
    .dpa-pending { background: #FFF3E0; color: #E65100; }
    .dpa-active { background: #E8F5E9; color: #2E7D32; }
    .dpa-expired { background: #FFEBEE; color: #C62828; }
    .chips { display: flex; flex-wrap: wrap; gap: 4px; }
    .chip {
      padding: 2px 10px; border-radius: 12px; font-size: 11px;
      background: #E3F2FD; color: #1565C0; font-weight: 500;
    }
    .v-footer { display: flex; align-items: center; justify-content: space-between; }
    .basis { font-size: 12px; color: var(--text-secondary); }
    .empty {
      padding: 32px; display: flex; align-items: center; gap: 10px;
      color: var(--text-disabled); font-size: 13px; grid-column: 1 / -1;
    }
  `]
})
export class DpdpVendorComponent implements OnInit {
  private svc = inject(DpdpService);
  vendors: any[] = [];
  showForm = false;
  form = { name: '', service_type: '', data_shared_raw: '', transfer_basis: '' };

  ngOnInit() { this.load(); }
  load() { this.svc.listVendors().subscribe({ next: (d: any[]) => this.vendors = d, error: () => {} }); }

  add() {
    const body = {
      name: this.form.name, service_type: this.form.service_type,
      data_shared: this.form.data_shared_raw.split(',').map((s: string) => s.trim()).filter(Boolean),
      transfer_basis: this.form.transfer_basis,
    };
    this.svc.createVendor(body).subscribe({
      next: () => { this.showForm = false; this.form = { name: '', service_type: '', data_shared_raw: '', transfer_basis: '' }; this.load(); }
    });
  }

  remove(id: string) {
    this.svc.deleteVendor(id).subscribe({ next: () => this.load() });
  }
}
