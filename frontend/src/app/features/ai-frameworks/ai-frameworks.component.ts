import { Component, OnInit, computed, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatSelectModule } from '@angular/material/select';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatDividerModule } from '@angular/material/divider';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';

interface FrameworkGuide {
  id: string;
  title: string;
  summary: string;
  bullets: string[];
}

interface Project {
  id: string;
  name: string;
  owner: string;
  tags: string[];
  deploymentId?: string;
}

interface McpDeploymentOption {
  id: string;
  name: string;
  framework: string;
  environment: string;
}

@Component({
  selector: 'app-ai-frameworks',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatSelectModule,
    MatChipsModule,
    MatIconModule,
    MatButtonModule,
    MatDividerModule,
    MatFormFieldModule,
    MatInputModule,
    FormsModule,
  ],
  template: `
    <div class="page">
      <div class="page-header">
        <div>
          <h1>AI Frameworks</h1>
          <p>Map AI Projects to NIST AI RMF (AI 600-1 Generative AI Profile) with quick, actionable hints.</p>
        </div>
        <a class="doc-link" href="https://doi.org/10.6028/NIST.AI.600-1" target="_blank" rel="noreferrer">
          <mat-icon>open_in_new</mat-icon>
          NIST AI 600-1
        </a>
      </div>

      <mat-card class="selector-card">
        <div class="selector">
          <div class="selector-left">
            <label for="project">AI Project</label>
            <mat-select id="project" [(value)]="selectedProjectId">
              <mat-option *ngFor="let project of projects" [value]="project.id">
                {{ project.name }} — {{ project.owner }}
              </mat-option>
            </mat-select>
          </div>
          <div class="selector-right" *ngIf="selectedProject() as proj">
            <div class="pill-row">
              <mat-chip-listbox>
                <mat-chip *ngFor="let tag of proj.tags" color="primary" selected>{{ tag }}</mat-chip>
              </mat-chip-listbox>
            </div>
            <button mat-stroked-button color="primary" (click)="reset()">
              <mat-icon>refresh</mat-icon>
              Reset selection
            </button>
          </div>
        </div>

        <mat-divider></mat-divider>

        <div class="create-grid">
          <div class="create-header">
            <h3>Create new project</h3>
            <p>Capture owner, tags, and link an MCP deployment for NIST AI RMF mapping.</p>
          </div>
          <div class="create-form">
            <mat-form-field appearance="outline">
              <mat-label>Project name</mat-label>
              <input matInput [(ngModel)]="form.name" placeholder="GenAI Copilot" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Owner</mat-label>
              <input matInput [(ngModel)]="form.owner" placeholder="Data Science" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Tags (comma-separated)</mat-label>
              <input matInput [(ngModel)]="form.tags" placeholder="LLM, RAG, Prod" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>MCP Deployment</mat-label>
              <mat-select [(ngModel)]="form.deploymentId" [disabled]="deployments().length === 0">
                <mat-option *ngFor="let d of deployments()" [value]="d.id">
                  {{ d.name }} — {{ d.framework }} ({{ d.environment }})
                </mat-option>
              </mat-select>
            </mat-form-field>
          </div>
          <button mat-flat-button color="primary" (click)="addProject()" [disabled]="!form.name || !form.owner">
            <mat-icon>add</mat-icon>
            Add project
          </button>
        </div>
      </mat-card>

      <div class="grid">
        <mat-card class="guide" *ngFor="let guide of guides">
          <div class="guide-header">
            <div class="eyebrow">{{ guide.id }}</div>
            <h3>{{ guide.title }}</h3>
            <p class="summary">{{ guide.summary }}</p>
          </div>
          <mat-divider></mat-divider>
          <ul>
            <li *ngFor="let bullet of guide.bullets">{{ bullet }}</li>
          </ul>
          <div class="cta">
            <mat-icon>lightbulb</mat-icon>
            <span>
              Use with {{ selectedProject()?.name || 'your project' }}
              <ng-container *ngIf="selectedProject()?.deploymentId">
                (MCP: {{ displayDeployment(selectedProject()?.deploymentId) }})
              </ng-container>
              to map risks and actions.
            </span>
          </div>
        </mat-card>
      </div>
    </div>
  `,
  styles: [`
    .page { display: flex; flex-direction: column; gap: 16px; }
    .page-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    .page-header h1 { margin: 0; font-size: 22px; color: var(--text-primary); }
    .page-header p { margin: 4px 0 0; color: var(--text-secondary); }
    .doc-link { display: inline-flex; align-items: center; gap: 6px; text-decoration: none; color: var(--brand-blue); font-weight: 600; }

    .selector-card { padding: 16px; }
    .selector { display: flex; flex-wrap: wrap; gap: 16px; align-items: center; justify-content: space-between; }
    .selector-left { min-width: 260px; flex: 1; display: flex; flex-direction: column; gap: 6px; }
    label { font-weight: 600; color: var(--text-primary); font-size: 13px; }
    mat-select { width: 100%; }
    .selector-right { display: flex; align-items: center; gap: 12px; }
    .pill-row mat-chip { background: var(--brand-blue-muted) !important; color: var(--brand-blue) !important; font-weight: 600; }
    .create-grid { margin-top: 16px; display: flex; flex-direction: column; gap: 12px; }
    .create-header h3 { margin: 0; font-size: 15px; font-weight: 700; }
    .create-header p { margin: 4px 0 0; font-size: 12px; color: var(--text-secondary); }
    .create-form { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }

    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }
    .guide { display: flex; flex-direction: column; gap: 12px; min-height: 220px; }
    .guide-header .eyebrow { text-transform: uppercase; font-size: 11px; letter-spacing: 0.6px; color: var(--text-secondary); }
    .guide-header h3 { margin: 4px 0; font-size: 16px; color: var(--text-primary); }
    .summary { margin: 0; color: var(--text-secondary); font-size: 13px; }
    ul { padding-left: 18px; margin: 8px 0 0; color: var(--text-primary); line-height: 1.5; }
    li { margin-bottom: 6px; }
    .cta { margin-top: auto; display: inline-flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-secondary); }
    .cta mat-icon { font-size: 16px; width: 16px; height: 16px; color: var(--brand-blue); }
  `]
})
export class AiFrameworksComponent implements OnInit {
  private api = inject(ApiService);

  projects: Project[] = [
    { id: 'proj-1', name: 'Customer Care Copilot', owner: 'Contact Center', tags: ['LLM', 'RAG', 'Prod'] },
    { id: 'proj-2', name: 'Model Governance API', owner: 'Platform', tags: ['Service', 'API'] },
    { id: 'proj-3', name: 'Analyst Workspace', owner: 'GRC', tags: ['Analytics', 'Internal'] },
  ];

  deployments = signal<McpDeploymentOption[]>([]);

  guides: FrameworkGuide[] = [
    {
      id: 'Govern',
      title: 'Govern (GV 1.x)',
      summary: 'Scope AI projects, roles, and policies; align with legal/regulatory needs.',
      bullets: [
        'Define acceptable use + risk tiers; decide no-go triggers for GAI and third-party components.',
        'Track provenance of training/grounding data; document supplier chain and CA/PII constraints.',
        'Set escalation + deactivation criteria for incidents; name owners for approval gates.',
      ],
    },
    {
      id: 'Map',
      title: 'Map (MP 1.x)',
      summary: 'Understand context, stakeholders, and risks before deployment.',
      bullets: [
        'Describe project purpose, data flows, human-in-the-loop, and downstream impacts.',
        'Identify trust characteristics (fairness, privacy, security, safety, explainability) per use case.',
        'Link risks to NIST AI 600-1 GAI profile: confabulation, CBRN misuse, content integrity, IP.',
      ],
    },
    {
      id: 'Measure',
      title: 'Measure (MS 1.x)',
      summary: 'Test and benchmark the system against NIST AI 600-1 suggested actions.',
      bullets: [
        'Design TEVV for jailbreaks, toxic/violent content, privacy leakage, and bias across groups.',
        'Exercise red-teaming (general + expert) and log fail/pass with remediation owners.',
        'Track metrics: refusal/over-refusal rates, grounding accuracy, PII recall, content provenance.',
      ],
    },
    {
      id: 'Manage',
      title: 'Manage (MG 1.x–4.x)',
      summary: 'Operate, monitor, and iterate with playbooks and provenance.',
      bullets: [
        'Instrument runtime monitoring for harmful outputs, drift, and incident intake channels.',
        'Keep model cards/system cards current; publish change logs and stakeholder comms.',
        'Plan rollback/deactivate paths; continuously fine-tune guardrails and filters.',
      ],
    },
  ];

  selectedProjectId = this.projects[0]?.id;
  selectedProject = computed(() => this.projects.find(p => p.id === this.selectedProjectId));

  form: { name: string; owner: string; tags: string; deploymentId?: string } = {
    name: '', owner: '', tags: '', deploymentId: undefined,
  };

  ngOnInit() {
    this.loadDeployments();
  }

  loadDeployments() {
    this.api.listMcpDeployments().subscribe({
      next: (d: any[]) => {
        const opts = d.map(x => ({ id: x.id, name: x.name, framework: x.framework, environment: x.environment }));
        this.deployments.set(opts);
      },
      error: () => this.deployments.set([]),
    });
  }

  reset() {
    this.selectedProjectId = undefined as unknown as string;
  }

  addProject() {
    const newProj: Project = {
      id: crypto.randomUUID(),
      name: this.form.name.trim(),
      owner: this.form.owner.trim(),
      tags: this.form.tags.split(',').map(t => t.trim()).filter(Boolean),
      deploymentId: this.form.deploymentId,
    };
    this.projects = [...this.projects, newProj];
    this.selectedProjectId = newProj.id;
    this.form = { name: '', owner: '', tags: '', deploymentId: undefined };
  }

  displayDeployment(id?: string): string {
    const d = this.deployments().find(x => x.id === id);
    return d ? `${d.name}` : '';
  }
}
