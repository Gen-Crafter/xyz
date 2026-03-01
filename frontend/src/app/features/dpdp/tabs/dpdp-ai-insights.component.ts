import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';

interface AiCapability {
  id: string;
  title: string;
  icon: string;
  color: string;
  description: string;
  inputs: string[];
  outputs: string[];
  approvalRequired: boolean;
}

@Component({
  selector: 'app-dpdp-ai-insights',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatDividerModule],
  template: `
    <div class="page">
      <h2>AI Compliance Insights</h2>
      <p class="subtitle">AI-powered automation components for DPDP compliance — running on local Ollama LLM.</p>

      <div class="grid">
        @for (cap of capabilities; track cap.id) {
          <mat-card class="cap-card">
            <div class="cap-header">
              <div class="cap-icon" [style.background]="cap.color + '20'" [style.color]="cap.color">
                <mat-icon>{{ cap.icon }}</mat-icon>
              </div>
              <h3>{{ cap.title }}</h3>
            </div>
            <p class="desc">{{ cap.description }}</p>
            <mat-divider></mat-divider>
            <div class="io-section">
              <div class="io-block">
                <span class="io-label">Inputs</span>
                <ul>
                  @for (i of cap.inputs; track i) { <li>{{ i }}</li> }
                </ul>
              </div>
              <div class="io-block">
                <span class="io-label">Outputs</span>
                <ul>
                  @for (o of cap.outputs; track o) { <li>{{ o }}</li> }
                </ul>
              </div>
            </div>
            <div class="approval-row">
              <mat-icon [style.color]="cap.approvalRequired ? '#EF6C00' : '#43A047'">
                {{ cap.approvalRequired ? 'supervisor_account' : 'smart_toy' }}
              </mat-icon>
              <span>{{ cap.approvalRequired ? 'Human approval required' : 'Automated (configurable)' }}</span>
            </div>
          </mat-card>
        }
      </div>

      <mat-card class="llm-card">
        <h3><mat-icon>memory</mat-icon> LLM Runtime</h3>
        <p>All AI components run on a <strong>local Ollama instance</strong> — no data leaves the platform.
           Models can be swapped via Settings. Recommended: <code>llama3</code> or <code>mistral</code>.</p>
      </mat-card>
    </div>
  `,
  styles: [`
    .page { display: flex; flex-direction: column; gap: 16px; }
    h2 { margin: 0; font-size: 18px; color: var(--text-primary); }
    .subtitle { margin: -8px 0 0; color: var(--text-secondary); font-size: 13px; }

    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; }
    .cap-card { padding: 20px; display: flex; flex-direction: column; gap: 12px; }
    .cap-header { display: flex; align-items: center; gap: 12px; }
    .cap-icon {
      width: 40px; height: 40px; border-radius: 10px;
      display: flex; align-items: center; justify-content: center;
    }
    .cap-icon mat-icon { font-size: 22px; width: 22px; height: 22px; }
    .cap-header h3 { margin: 0; font-size: 15px; color: var(--text-primary); }
    .desc { margin: 0; font-size: 13px; color: var(--text-secondary); line-height: 1.5; }

    .io-section { display: flex; gap: 24px; margin-top: 8px; }
    .io-block { flex: 1; }
    .io-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-disabled); }
    .io-block ul { padding-left: 16px; margin: 4px 0 0; font-size: 12px; color: var(--text-secondary); line-height: 1.6; }

    .approval-row {
      display: flex; align-items: center; gap: 8px;
      font-size: 12px; color: var(--text-secondary); margin-top: auto;
    }
    .approval-row mat-icon { font-size: 18px; width: 18px; height: 18px; }

    .llm-card { padding: 20px; }
    .llm-card h3 {
      display: flex; align-items: center; gap: 8px;
      margin: 0 0 8px; font-size: 15px; color: var(--text-primary);
    }
    .llm-card h3 mat-icon { font-size: 20px; width: 20px; height: 20px; color: var(--brand-blue); }
    .llm-card p { margin: 0; font-size: 13px; color: var(--text-secondary); line-height: 1.6; }
    .llm-card code { background: #F5F5F5; padding: 2px 6px; border-radius: 4px; font-size: 12px; }
  `]
})
export class DpdpAiInsightsComponent {
  capabilities: AiCapability[] = [
    {
      id: 'classifier', title: 'AI Data Classifier', icon: 'fingerprint', color: '#1565C0',
      description: 'Automatically detect PII fields in datasets and tag risk levels using NER and pattern matching.',
      inputs: ['Database schemas', 'Sample field values', 'Existing labels'],
      outputs: ['PII type tags', 'Risk score per field', 'consent_required flag'],
      approvalRequired: false,
    },
    {
      id: 'monitor', title: 'AI Compliance Monitor', icon: 'monitor_heart', color: '#C62828',
      description: 'Detect unlawful processing patterns and consent-purpose mismatches in real time.',
      inputs: ['Processing events', 'Consent registry', 'Purpose definitions'],
      outputs: ['Mismatch alerts', 'Violation reports', 'Auto-block recommendations'],
      approvalRequired: true,
    },
    {
      id: 'retention', title: 'AI Retention Engine', icon: 'delete_sweep', color: '#6A1B9A',
      description: 'Monitor inactivity timelines and recommend deletion actions based on retention policies.',
      inputs: ['Last-activity timestamps', 'Retention policies', 'Legal hold flags'],
      outputs: ['Due-for-deletion list', 'Soft-delete tasks', 'Audit trail entries'],
      approvalRequired: true,
    },
    {
      id: 'rights', title: 'AI Rights Assistant', icon: 'support_agent', color: '#2E7D32',
      description: 'Auto-route data principal requests and draft compliant responses.',
      inputs: ['Rights request text', 'Principal history', 'Applicable policies'],
      outputs: ['Routing decision', 'Draft response', 'Evidence bundle'],
      approvalRequired: true,
    },
    {
      id: 'risk', title: 'AI Risk Scoring Engine', icon: 'speed', color: '#EF6C00',
      description: 'Real-time compliance score and Significant Data Fiduciary likelihood indicator.',
      inputs: ['Inventory stats', 'Breach history', 'Consent coverage', 'Rights SLA performance'],
      outputs: ['Compliance score (0–100)', 'SDF likelihood', 'Gap analysis report'],
      approvalRequired: false,
    },
  ];
}
