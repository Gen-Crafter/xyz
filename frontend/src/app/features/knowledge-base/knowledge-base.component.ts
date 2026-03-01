import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-knowledge-base',
  standalone: true,
  imports: [CommonModule, FormsModule, MatCardModule, MatIconModule, MatButtonModule,
            MatFormFieldModule, MatInputModule, MatProgressBarModule, MatSnackBarModule],
  template: `
    <div class="page-header">
      <h1>RAG Knowledge Base</h1>
      <p>Regulation documents powering the context detection engine</p>
    </div>

    <div class="kpi-grid">
      @for (col of collections(); track col.collection_name) {
        <div class="kpi-card">
          <span class="kpi-label">{{ col.collection_name }}</span>
          <span class="kpi-value">{{ col.document_count }}</span>
          <span class="kpi-subtitle">{{ col.embedding_dim }}-dim embeddings</span>
        </div>
      }
      <div class="kpi-card">
        <span class="kpi-label">Embedding Model</span>
        <span class="kpi-value" style="font-size: 16px;">all-MiniLM-L6-v2</span>
        <span class="kpi-subtitle">384 dimensions, local</span>
      </div>
    </div>

    <div class="action-bar">
      <button mat-raised-button color="primary" (click)="ingest()" [disabled]="ingesting()">
        <mat-icon>cloud_download</mat-icon>
        {{ ingesting() ? 'Ingesting...' : 'Ingest Built-in Regulations' }}
      </button>
      @if (ingestResult()) {
        <span class="ingest-result">{{ ingestResult() }}</span>
      }
    </div>

    @if (ingesting()) {
      <mat-progress-bar mode="indeterminate"></mat-progress-bar>
    }

    <mat-card class="upload-card">
      <mat-card-header>
        <mat-card-title>
          <mat-icon>upload_file</mat-icon>
          Upload Document
        </mat-card-title>
      </mat-card-header>
      <mat-card-content>
        <p class="upload-hint">Upload regulation documents (.txt, .md, .csv) to expand the compliance knowledge base.</p>
        <div class="upload-form">
          <input type="file" #fileInput (change)="onFileSelected($event)"
                 accept=".txt,.md,.csv,.json,.log" style="display:none">
          <button mat-stroked-button (click)="fileInput.click()">
            <mat-icon>attach_file</mat-icon>
            {{ selectedFile ? selectedFile.name : 'Choose File' }}
          </button>

          <mat-form-field appearance="outline" class="upload-field">
            <mat-label>Regulation (optional)</mat-label>
            <input matInput [(ngModel)]="uploadRegulation" placeholder="e.g. GDPR, HIPAA">
          </mat-form-field>

          <mat-form-field appearance="outline" class="upload-field">
            <mat-label>Category (optional)</mat-label>
            <input matInput [(ngModel)]="uploadCategory" placeholder="e.g. data_transfers, PHI">
          </mat-form-field>

          <button mat-raised-button color="accent" (click)="uploadFile()" [disabled]="!selectedFile || uploading()">
            <mat-icon>cloud_upload</mat-icon>
            {{ uploading() ? 'Uploading...' : 'Upload & Ingest' }}
          </button>
        </div>
        @if (uploading()) {
          <mat-progress-bar mode="indeterminate" class="upload-progress"></mat-progress-bar>
        }
        @if (uploadResult()) {
          <div class="upload-result" [class.error]="uploadResult().startsWith('Error')">
            {{ uploadResult() }}
          </div>
        }
      </mat-card-content>
    </mat-card>

    <mat-card class="query-card">
      <mat-card-header>
        <mat-card-title>
          <mat-icon>search</mat-icon>
          RAG Query Tester
        </mat-card-title>
      </mat-card-header>
      <mat-card-content>
        <mat-form-field appearance="outline" class="query-input">
          <mat-label>Query the regulation knowledge base</mat-label>
          <input matInput [(ngModel)]="query"
                 placeholder="e.g., How does GDPR Article 17 conflict with HIPAA retention?"
                 (keydown.enter)="runQuery()">
        </mat-form-field>
        <button mat-raised-button color="accent" (click)="runQuery()" [disabled]="querying()">
          <mat-icon>send</mat-icon>
          {{ querying() ? 'Querying...' : 'Search' }}
        </button>

        @if (queryResult()) {
          <div class="query-results">
            @if (queryResult().llm_synthesis) {
              <div class="synthesis">
                <h4>AI Synthesis</h4>
                <p>{{ queryResult().llm_synthesis }}</p>
              </div>
            }
            <h4>Retrieved Chunks ({{ queryResult().chunks?.length || 0 }})</h4>
            @for (chunk of queryResult().chunks || []; track $index) {
              <div class="chunk-card">
                <div class="chunk-header">
                  <span class="chunk-source">{{ chunk.source || chunk.metadata?.regulation }}</span>
                  <span class="chunk-score">Relevance: {{ (chunk.relevance_score * 100).toFixed(0) }}%</span>
                </div>
                <p class="chunk-content">{{ chunk.content }}</p>
              </div>
            }
            <p class="query-time">Query time: {{ queryResult().processing_time_ms }}ms</p>
          </div>
        }
      </mat-card-content>
    </mat-card>
  `,
  styles: [`
    .action-bar { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }
    .ingest-result { font-size: 13px; color: var(--accent-green); }
    .upload-card {
      margin-bottom: 20px;
      mat-card-title { display: flex; align-items: center; gap: 8px; font-size: 16px;
        mat-icon { color: var(--accent-blue); }
      }
    }
    .upload-hint { font-size: 13px; color: var(--text-secondary); margin-bottom: 12px; }
    .upload-form {
      display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
    }
    .upload-field {
      width: 180px;
      ::ng-deep .mat-mdc-form-field-subscript-wrapper { display: none; }
    }
    .upload-progress { margin-top: 10px; }
    .upload-result {
      margin-top: 10px; font-size: 13px; color: var(--accent-green);
      &.error { color: var(--accent-red); }
    }
    .query-card {
      margin-top: 20px;
      mat-card-title { display: flex; align-items: center; gap: 8px; font-size: 16px;
        mat-icon { color: var(--accent-blue); }
      }
    }
    .query-input { width: 100%; margin-top: 12px; }
    .query-results { margin-top: 20px; }
    .synthesis {
      background: rgba(79, 141, 249, 0.08); border: 1px solid rgba(79, 141, 249, 0.2);
      border-radius: 8px; padding: 16px; margin-bottom: 16px;
      h4 { color: var(--accent-blue); margin-bottom: 8px; }
      p { font-size: 14px; line-height: 1.6; }
    }
    .chunk-card {
      background: var(--bg-secondary); border: 1px solid var(--border);
      border-radius: 8px; padding: 12px; margin-bottom: 8px;
    }
    .chunk-header { display: flex; justify-content: space-between; margin-bottom: 8px; }
    .chunk-source { font-weight: 600; font-size: 13px; color: var(--accent-purple); }
    .chunk-score { font-size: 12px; color: var(--text-secondary); }
    .chunk-content { font-size: 13px; line-height: 1.5; color: var(--text-secondary); }
    .query-time { font-size: 12px; color: var(--text-secondary); margin-top: 12px; }
  `],
})
export class KnowledgeBaseComponent implements OnInit {
  private api = inject(ApiService);
  private snackBar = inject(MatSnackBar);

  collections = signal<any[]>([]);
  ingesting = signal(false);
  ingestResult = signal<string>('');
  query = '';
  querying = signal(false);
  queryResult = signal<any>(null);

  // Upload state
  selectedFile: File | null = null;
  uploadRegulation = '';
  uploadCategory = '';
  uploading = signal(false);
  uploadResult = signal<string>('');

  ngOnInit() { this.loadStats(); }

  loadStats() {
    this.api.listCollections().subscribe({ next: (d) => this.collections.set(d), error: () => {} });
  }

  ingest() {
    this.ingesting.set(true);
    this.ingestResult.set('');
    this.api.ingestDocuments('all').subscribe({
      next: (r) => {
        this.ingesting.set(false);
        this.ingestResult.set(r.message || 'Done');
        this.loadStats();
      },
      error: () => {
        this.ingesting.set(false);
        this.snackBar.open('Ingestion failed', 'OK', { duration: 3000 });
      },
    });
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    this.selectedFile = input.files?.[0] || null;
    this.uploadResult.set('');
  }

  uploadFile() {
    if (!this.selectedFile) return;
    this.uploading.set(true);
    this.uploadResult.set('');
    this.api.uploadDocument(this.selectedFile, this.uploadRegulation, this.uploadCategory).subscribe({
      next: (r) => {
        this.uploading.set(false);
        this.uploadResult.set(r.message || 'Uploaded successfully');
        this.selectedFile = null;
        this.uploadRegulation = '';
        this.uploadCategory = '';
        this.loadStats();
      },
      error: (err) => {
        this.uploading.set(false);
        this.uploadResult.set('Error: ' + (err.error?.message || 'Upload failed'));
        this.snackBar.open('Upload failed', 'OK', { duration: 3000 });
      },
    });
  }

  runQuery() {
    if (!this.query) return;
    this.querying.set(true);
    this.queryResult.set(null);
    this.api.queryRag(this.query).subscribe({
      next: (r) => { this.querying.set(false); this.queryResult.set(r); },
      error: () => {
        this.querying.set(false);
        this.snackBar.open('Query failed', 'OK', { duration: 3000 });
      },
    });
  }
}
