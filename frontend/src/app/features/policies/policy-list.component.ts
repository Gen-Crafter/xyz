import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-policy-list',
  standalone: true,
  imports: [CommonModule, FormsModule, MatCardModule, MatIconModule, MatButtonModule,
            MatTableModule, MatSlideToggleModule, MatDialogModule, MatFormFieldModule,
            MatInputModule, MatSelectModule, MatSnackBarModule],
  template: `
    <div class="page-header">
      <h1>Policy Management</h1>
      <p>Configure and enforce compliance policies for AI traffic</p>
    </div>

    <div class="toolbar">
      <button mat-raised-button color="primary" (click)="showCreateForm = !showCreateForm">
        <mat-icon>add</mat-icon>
        New Policy
      </button>
      <div class="policy-test-area">
        <mat-form-field appearance="outline" class="test-input">
          <mat-label>Test payload text</mat-label>
          <input matInput [(ngModel)]="testPayload" placeholder="e.g., Patient SSN 123-45-6789">
        </mat-form-field>
        <button mat-stroked-button (click)="testPolicies()">
          <mat-icon>play_arrow</mat-icon>
          Test
        </button>
      </div>
    </div>

    @if (testResult()) {
      <mat-card class="test-result-card">
        <mat-card-content>
          <div class="test-result">
            <span class="badge" [class]="'badge-' + testResult().action.toLowerCase()">{{ testResult().action }}</span>
            <span>Triggered: {{ testResult().triggered_policies.join(', ') || 'None' }}</span>
            <span class="test-details">{{ testResult().details }}</span>
          </div>
        </mat-card-content>
      </mat-card>
    }

    @if (showCreateForm) {
      <mat-card class="create-form-card">
        <mat-card-header><mat-card-title>Create New Policy</mat-card-title></mat-card-header>
        <mat-card-content>
          <div class="form-grid">
            <mat-form-field appearance="outline">
              <mat-label>Policy ID</mat-label>
              <input matInput [(ngModel)]="newPolicy.id" placeholder="POL-CUSTOM-001">
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Name</mat-label>
              <input matInput [(ngModel)]="newPolicy.name" placeholder="Policy name">
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Regulation</mat-label>
              <mat-select [(ngModel)]="newPolicy.regulation">
                <mat-option value="HIPAA">HIPAA</mat-option>
                <mat-option value="GDPR">GDPR</mat-option>
                <mat-option value="PCI-DSS">PCI-DSS</mat-option>
                <mat-option value="INTERNAL">Internal</mat-option>
              </mat-select>
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Action</mat-label>
              <mat-select [(ngModel)]="newPolicy.action">
                <mat-option value="BLOCK">Block</mat-option>
                <mat-option value="REDACT">Redact</mat-option>
                <mat-option value="AUDIT">Audit</mat-option>
                <mat-option value="ALLOW">Allow</mat-option>
              </mat-select>
            </mat-form-field>
            <mat-form-field appearance="outline" class="full-width">
              <mat-label>Description</mat-label>
              <input matInput [(ngModel)]="newPolicy.description">
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Priority (lower = higher)</mat-label>
              <input matInput type="number" [(ngModel)]="newPolicy.priority">
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Data Classifications (comma-sep)</mat-label>
              <input matInput [(ngModel)]="newPolicy.classificationsCsv" placeholder="PHI,PII">
            </mat-form-field>
          </div>
          <div class="form-actions">
            <button mat-raised-button color="primary" (click)="createPolicy()">Create Policy</button>
            <button mat-stroked-button (click)="showCreateForm = false">Cancel</button>
          </div>
        </mat-card-content>
      </mat-card>
    }

    <div class="policy-grid">
      @for (policy of policies(); track policy.id) {
        <mat-card class="policy-card">
          <div class="policy-header">
            <div class="policy-title-row">
              <span class="policy-id">{{ policy.id }}</span>
              <mat-slide-toggle [checked]="policy.enabled" (change)="togglePolicy(policy.id)">
              </mat-slide-toggle>
            </div>
            <h3>{{ policy.name }}</h3>
            <p class="policy-desc">{{ policy.description }}</p>
          </div>
          <div class="policy-meta">
            <span class="badge" [class]="'badge-' + policy.action.toLowerCase()">{{ policy.action }}</span>
            <span class="meta-tag">{{ policy.regulation || 'General' }}</span>
            <span class="meta-priority">Priority: {{ policy.priority }}</span>
          </div>
          <div class="policy-actions">
            <button mat-icon-button color="warn" (click)="deletePolicy(policy.id)">
              <mat-icon>delete</mat-icon>
            </button>
          </div>
        </mat-card>
      }
    </div>
  `,
  styles: [`
    /* ── Toolbar (action bar) ───────────────────────────────── */
    .toolbar {
      display: flex; align-items: center; gap: 12px;
      margin-bottom: 16px; flex-wrap: wrap;
      padding: 12px 16px; background: var(--bg-card); border: 1px solid var(--border);
      border-radius: var(--radius-md);
    }
    .policy-test-area {
      display: flex; align-items: center; gap: 8px; margin-left: auto;
    }
    .test-input {
      width: 280px;
      ::ng-deep .mat-mdc-form-field-subscript-wrapper { display: none; }
    }
    .test-result-card { margin-bottom: 16px; }
    .test-result { display: flex; align-items: center; gap: 12px; font-size: 13px; }
    .test-details { color: var(--text-secondary); font-size: 12px; }

    /* ── Create Form ─────────────────────────────────────────────────── */
    .create-form-card { margin-bottom: 16px; }
    .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px; }
    .full-width { grid-column: 1 / -1; }
    .form-actions { display: flex; gap: 12px; margin-top: 16px; }

    /* ── Policy Grid (card grid) ────────────────────────────── */
    .policy-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 12px;
    }
    .policy-card { padding: 16px; }
    .policy-header { margin-bottom: 10px; }
    .policy-title-row {
      display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;
    }
    .policy-id {
      font-family: 'Roboto Mono', monospace; font-size: 11px;
      color: var(--brand-blue); background: var(--brand-blue-muted);
      padding: 2px 8px; border-radius: 100px; font-weight: 500;
    }
    .policy-desc { color: var(--text-secondary); font-size: 12px; margin-top: 4px; line-height: 1.5; }
    .policy-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
    .meta-tag {
      font-size: 11px; color: var(--text-secondary); background: var(--bg-hover);
      padding: 2px 8px; border-radius: 100px;
    }
    .meta-priority { font-size: 11px; color: var(--text-disabled); margin-left: auto; }
    .policy-actions { text-align: right; }
  `],
})
export class PolicyListComponent implements OnInit {
  private api = inject(ApiService);
  private snackBar = inject(MatSnackBar);

  policies = signal<any[]>([]);
  testResult = signal<any>(null);
  showCreateForm = false;
  testPayload = '';
  newPolicy: any = {
    id: '', name: '', description: '', regulation: 'INTERNAL',
    action: 'BLOCK', priority: 50, classificationsCsv: '',
  };

  ngOnInit() {
    this.loadPolicies();
  }

  loadPolicies() {
    this.api.listPolicies().subscribe({
      next: (data) => this.policies.set(data),
      error: () => {},
    });
  }

  togglePolicy(id: string) {
    this.api.togglePolicy(id).subscribe({
      next: () => this.loadPolicies(),
      error: () => this.snackBar.open('Failed to toggle policy', 'OK', { duration: 3000 }),
    });
  }

  deletePolicy(id: string) {
    this.api.deletePolicy(id).subscribe({
      next: () => {
        this.snackBar.open('Policy deleted', 'OK', { duration: 2000 });
        this.loadPolicies();
      },
      error: () => this.snackBar.open('Failed to delete', 'OK', { duration: 3000 }),
    });
  }

  createPolicy() {
    const classifications = this.newPolicy.classificationsCsv
      .split(',').map((s: string) => s.trim()).filter((s: string) => s);
    const payload = {
      id: this.newPolicy.id || undefined,
      name: this.newPolicy.name,
      description: this.newPolicy.description,
      regulation: this.newPolicy.regulation,
      action: this.newPolicy.action,
      priority: this.newPolicy.priority,
      enabled: true,
      conditions: { data_classifications: classifications },
    };
    this.api.createPolicy(payload).subscribe({
      next: () => {
        this.snackBar.open('Policy created', 'OK', { duration: 2000 });
        this.showCreateForm = false;
        this.loadPolicies();
      },
      error: () => this.snackBar.open('Failed to create', 'OK', { duration: 3000 }),
    });
  }

  testPolicies() {
    if (!this.testPayload) return;
    this.api.testPolicy({ payload_text: this.testPayload }).subscribe({
      next: (result) => this.testResult.set(result),
      error: () => this.snackBar.open('Test failed', 'OK', { duration: 3000 }),
    });
  }
}
