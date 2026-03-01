import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialogModule } from '@angular/material/dialog';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { FormsModule } from '@angular/forms';
import { DpdpService } from '../dpdp.service';

@Component({
  selector: 'app-dpdp-inventory',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatButtonModule, MatChipsModule,
            MatDialogModule, MatInputModule, MatFormFieldModule, FormsModule],
  template: `
    <div class="inv-page">
      <div class="toolbar">
        <h2>Data Inventory</h2>
        <button mat-flat-button color="primary" (click)="showForm = !showForm">
          <mat-icon>add</mat-icon> Register System
        </button>
      </div>

      @if (showForm) {
        <mat-card class="form-card">
          <h3>New System</h3>
          <mat-form-field appearance="outline" class="full">
            <mat-label>System Name</mat-label>
            <input matInput [(ngModel)]="form.name" />
          </mat-form-field>
          <mat-form-field appearance="outline" class="full">
            <mat-label>Owner</mat-label>
            <input matInput [(ngModel)]="form.owner" />
          </mat-form-field>
          <mat-form-field appearance="outline" class="full">
            <mat-label>Description</mat-label>
            <input matInput [(ngModel)]="form.description" />
          </mat-form-field>
          <mat-form-field appearance="outline" class="full">
            <mat-label>Purposes (comma-separated)</mat-label>
            <input matInput [(ngModel)]="form.purposesRaw" />
          </mat-form-field>
          <div class="form-actions">
            <button mat-flat-button color="primary" (click)="addSystem()">Save</button>
            <button mat-button (click)="showForm = false">Cancel</button>
          </div>
        </mat-card>
      }

      <div class="grid">
        @for (sys of systems; track sys.id) {
          <mat-card class="sys-card">
            <div class="sys-header">
              <mat-icon class="sys-icon">dns</mat-icon>
              <div>
                <h3>{{ sys.name }}</h3>
                <span class="owner">{{ sys.owner }}</span>
              </div>
              <span class="risk-badge" [class]="'risk-' + (sys.risk_level || 'LOW').toLowerCase()">
                {{ sys.risk_level || 'LOW' }}
              </span>
            </div>
            <p class="desc">{{ sys.description || '—' }}</p>
            <div class="chips">
              @for (p of sys.purposes || []; track p) {
                <mat-chip-option selected disabled>{{ p }}</mat-chip-option>
              }
            </div>
            <div class="card-actions">
              <button mat-icon-button color="warn" (click)="removeSystem(sys.id)">
                <mat-icon>delete</mat-icon>
              </button>
            </div>
          </mat-card>
        }
        @if (!systems.length) {
          <mat-card class="empty">
            <mat-icon>info</mat-icon>
            <span>No systems registered yet. Click "Register System" to add one.</span>
          </mat-card>
        }
      </div>

      @if (datasets.length) {
        <h2 class="section-title">Datasets</h2>
        <div class="grid">
          @for (ds of datasets; track ds.id) {
            <mat-card class="sys-card">
              <div class="sys-header">
                <mat-icon class="sys-icon" style="color:#6A1B9A">storage</mat-icon>
                <div>
                  <h3>{{ ds.name }}</h3>
                  <span class="owner">{{ ds.category }}</span>
                </div>
              </div>
              <div class="chips">
                @for (f of ds.pii_fields || []; track f) {
                  <mat-chip-option selected disabled color="warn">{{ f }}</mat-chip-option>
                }
              </div>
            </mat-card>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .inv-page { display: flex; flex-direction: column; gap: 12px; }
    .toolbar { display: flex; align-items: center; justify-content: space-between; }
    .toolbar h2 { margin: 0; font-size: 18px; color: var(--text-primary); }
    .form-card { padding: 20px; display: flex; flex-direction: column; gap: 8px; }
    .form-card h3 { margin: 0 0 4px; font-size: 15px; }
    .full { width: 100%; }
    .form-actions { display: flex; gap: 8px; }

    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }
    .sys-card { padding: 16px; display: flex; flex-direction: column; gap: 10px; }
    .sys-header { display: flex; align-items: center; gap: 10px; }
    .sys-icon { color: #1565C0; font-size: 28px; width: 28px; height: 28px; }
    .sys-header h3 { margin: 0; font-size: 15px; color: var(--text-primary); }
    .owner { font-size: 12px; color: var(--text-secondary); }
    .risk-badge {
      margin-left: auto; padding: 2px 10px; border-radius: 12px;
      font-size: 11px; font-weight: 600; text-transform: uppercase;
    }
    .risk-low { background: #E8F5E9; color: #2E7D32; }
    .risk-medium { background: #FFF3E0; color: #E65100; }
    .risk-high { background: #FFEBEE; color: #C62828; }
    .desc { margin: 0; font-size: 13px; color: var(--text-secondary); }
    .chips { display: flex; flex-wrap: wrap; gap: 4px; }
    .card-actions { display: flex; justify-content: flex-end; }

    .empty {
      padding: 32px; display: flex; align-items: center; gap: 10px;
      color: var(--text-disabled); font-size: 13px; grid-column: 1 / -1;
    }
    .section-title { margin: 16px 0 0; font-size: 18px; color: var(--text-primary); }
  `]
})
export class DpdpInventoryComponent implements OnInit {
  private svc = inject(DpdpService);
  systems: any[] = [];
  datasets: any[] = [];
  showForm = false;
  form = { name: '', owner: '', description: '', purposesRaw: '' };

  ngOnInit() { this.load(); }

  load() {
    this.svc.listSystems().subscribe({ next: d => this.systems = d, error: () => {} });
    this.svc.listDatasets().subscribe({ next: d => this.datasets = d, error: () => {} });
  }

  addSystem() {
    const body = {
      name: this.form.name, owner: this.form.owner, description: this.form.description,
      purposes: this.form.purposesRaw.split(',').map(s => s.trim()).filter(Boolean),
    };
    this.svc.createSystem(body).subscribe({ next: () => { this.showForm = false; this.load(); } });
  }

  removeSystem(id: string) {
    this.svc.deleteSystem(id).subscribe({ next: () => this.load() });
  }
}
