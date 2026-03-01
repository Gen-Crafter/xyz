import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-classification-rules',
  standalone: true,
  imports: [CommonModule, FormsModule, MatCardModule, MatIconModule, MatButtonModule,
            MatFormFieldModule, MatInputModule, MatSelectModule, MatSnackBarModule],
  template: `
    <div class="page-header">
      <h1>Data Classification Rules</h1>
      <p>Configure patterns and keywords for PII, PHI, PCI detection</p>
    </div>

    <div class="toolbar">
      <mat-form-field appearance="outline" class="test-input">
        <mat-label>Test classification</mat-label>
        <input matInput [(ngModel)]="testText" placeholder="e.g., SSN 123-45-6789 patient John Smith">
      </mat-form-field>
      <button mat-stroked-button (click)="testClassification()">
        <mat-icon>science</mat-icon> Test
      </button>
      <button mat-flat-button color="primary" (click)="showCreateForm.set(!showCreateForm())">
        <mat-icon>add</mat-icon> New Rule
      </button>
    </div>

    @if (testResult()) {
      <mat-card class="test-result">
        <mat-card-content>
          <p><strong>Classifications:</strong> {{ testResult().classifications?.join(', ') || 'None' }}</p>
          <p><strong>Entities:</strong></p>
          @for (entity of testResult().entities || []; track $index) {
            <div class="entity-item">
              <span class="badge badge-high">{{ entity.type }}</span>
              <code>{{ entity.value }}</code>
            </div>
          }
          @if (!testResult().entities?.length) {
            <p class="no-entities">No entities detected</p>
          }
        </mat-card-content>
      </mat-card>
    }

    @if (showCreateForm()) {
      <mat-card class="create-form">
        <h3>Create New Classification Rule</h3>
        <div class="form-grid">
          <mat-form-field appearance="outline">
            <mat-label>Rule Name</mat-label>
            <input matInput [(ngModel)]="newRule.name" placeholder="e.g., Bank Account Number">
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Category</mat-label>
            <mat-select [(ngModel)]="newRule.category">
              <mat-option value="PII">PII</mat-option>
              <mat-option value="PHI">PHI</mat-option>
              <mat-option value="PCI">PCI</mat-option>
              <mat-option value="CUSTOM">CUSTOM</mat-option>
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Regex Pattern</mat-label>
            <input matInput [(ngModel)]="newRule.pattern" placeholder="e.g., \\b\\d&#123;3&#125;-\\d&#123;2&#125;-\\d&#123;4&#125;\\b">
          </mat-form-field>
          <mat-form-field appearance="outline" class="full-width">
            <mat-label>Keywords (comma-separated)</mat-label>
            <input matInput [(ngModel)]="newRule.keywordsStr" placeholder="e.g., bank account, routing number">
          </mat-form-field>
        </div>
        <div class="form-actions">
          <button mat-stroked-button (click)="showCreateForm.set(false)">Cancel</button>
          <button mat-flat-button color="primary" (click)="createRule()" [disabled]="!newRule.name || !newRule.category">
            <mat-icon>save</mat-icon> Create Rule
          </button>
        </div>
      </mat-card>
    }

    <div class="rules-grid">
      @for (rule of rules(); track rule.id) {
        <mat-card class="rule-card">
          <div class="rule-header">
            <span class="badge" [class]="'badge-' + getCategoryClass(rule.category)">{{ rule.category }}</span>
            <h3>{{ rule.name }}</h3>
          </div>
          @if (rule.pattern) {
            <div class="rule-detail"><strong>Pattern:</strong> <code>{{ rule.pattern }}</code></div>
          }
          @if (rule.keywords?.length) {
            <div class="rule-detail"><strong>Keywords:</strong> {{ rule.keywords.join(', ') }}</div>
          }
          <div class="rule-actions">
            <button mat-icon-button color="warn" (click)="deleteRule(rule.id)"><mat-icon>delete</mat-icon></button>
          </div>
        </mat-card>
      }
    </div>
  `,
  styles: [`
    .toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
    .test-input {
      width: 400px;
      ::ng-deep .mat-mdc-form-field-subscript-wrapper { display: none; }
    }
    .test-result { margin-bottom: 16px; }
    .entity-item { display: flex; align-items: center; gap: 8px; margin: 4px 0; font-size: 13px; }
    .no-entities { color: var(--text-secondary); font-size: 13px; }
    .create-form {
      margin-bottom: 20px; padding: 20px !important;
      h3 { font-size: 16px; font-weight: 600; margin-bottom: 16px; }
    }
    .form-grid {
      display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px;
      .full-width { grid-column: 1 / -1; }
    }
    .form-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 8px; }
    .rules-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; }
    .rule-card { padding: 16px; }
    .rule-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
    .rule-header h3 { font-size: 15px; }
    .rule-detail { font-size: 13px; color: var(--text-secondary); margin-bottom: 6px; }
    .rule-detail code { color: var(--accent-purple); }
    .rule-actions { text-align: right; }
  `],
})
export class ClassificationRulesComponent implements OnInit {
  private api = inject(ApiService);
  private snackBar = inject(MatSnackBar);

  rules = signal<any[]>([]);
  testText = '';
  testResult = signal<any>(null);
  showCreateForm = signal(false);
  newRule = { name: '', category: 'PII', pattern: '', keywordsStr: '' };

  ngOnInit() { this.load(); }

  load() {
    this.api.listClassifications().subscribe({ next: (d) => this.rules.set(d), error: () => {} });
  }

  createRule() {
    const payload = {
      name: this.newRule.name,
      category: this.newRule.category,
      pattern: this.newRule.pattern,
      keywords: this.newRule.keywordsStr.split(',').map(k => k.trim()).filter(k => k),
      enabled: true,
    };
    this.api.createClassification(payload).subscribe({
      next: () => {
        this.snackBar.open('Rule created', 'OK', { duration: 3000 });
        this.showCreateForm.set(false);
        this.newRule = { name: '', category: 'PII', pattern: '', keywordsStr: '' };
        this.load();
      },
      error: () => this.snackBar.open('Failed to create rule', 'OK', { duration: 3000 }),
    });
  }

  deleteRule(id: string) {
    this.api.deleteClassification(id).subscribe({ next: () => this.load(), error: () => {} });
  }

  testClassification() {
    if (!this.testText) return;
    this.api.testClassification(this.testText).subscribe({
      next: (r) => this.testResult.set(r),
      error: () => this.snackBar.open('Test failed', 'OK', { duration: 3000 }),
    });
  }

  getCategoryClass(cat: string): string {
    const map: Record<string, string> = { PHI: 'critical', PII: 'high', PCI: 'critical', CUSTOM: 'medium' };
    return map[cat] || 'low';
  }
}
