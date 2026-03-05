import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDividerModule } from '@angular/material/divider';
import { MatTabsModule } from '@angular/material/tabs';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-endpoint-list',
  standalone: true,
  imports: [CommonModule, FormsModule, MatCardModule, MatIconModule, MatButtonModule,
            MatFormFieldModule, MatInputModule, MatSelectModule, MatSlideToggleModule,
            MatSnackBarModule, MatTooltipModule, MatDividerModule, MatTabsModule],
  template: `
    <div class="page-header">
      <h1>AI Projects</h1>
      <p>Register AI deployments and get MCP connection configs for compliance scanning</p>
    </div>

    <!-- Stats -->
    <div class="stats-grid">
      <div class="kpi-card" matTooltip="Total AI deployments registered">
        <span class="kpi-label">Deployments</span>
        <span class="kpi-value">{{ deployments().length }}</span>
      </div>
      <div class="kpi-card" matTooltip="Deployments currently active and sending data">
        <span class="kpi-label">Active</span>
        <span class="kpi-value" style="color:var(--status-success)">{{ activeCount() }}</span>
      </div>
      <div class="kpi-card" matTooltip="Total compliance scans across all deployments">
        <span class="kpi-label">Total Scans</span>
        <span class="kpi-value">{{ totalScans() }}</span>
      </div>
      <div class="kpi-card" matTooltip="Total violations detected across all deployments">
        <span class="kpi-label">Violations</span>
        <span class="kpi-value" style="color:var(--status-danger)">{{ totalViolations() }}</span>
      </div>
    </div>

    <!-- Register Button -->
    <div class="toolbar">
      <button mat-flat-button color="primary" (click)="showForm = !showForm; configPanel = null"
              matTooltip="Register a new AI project for MCP-based compliance scanning">
        <mat-icon>add</mat-icon> Register AI Deployment
      </button>
    </div>

    <!-- Registration Form -->
    @if (showForm) {
      <mat-card class="form-card">
        <h3><mat-icon>rocket_launch</mat-icon> Register New AI Deployment</h3>
        <p class="form-desc">Register your AI application to get an MCP connection config. GenCrafter will automatically scan all requests for compliance.</p>
        <mat-divider></mat-divider>
        <div class="form-grid">
          <mat-form-field appearance="outline">
            <mat-label>Deployment Name</mat-label>
            <input matInput [(ngModel)]="form.name" placeholder="My AI Agent" />
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Framework</mat-label>
            <mat-select [(ngModel)]="form.framework">
              <mat-option value="langchain">LangChain</mat-option>
              <mat-option value="crewai">CrewAI</mat-option>
              <mat-option value="autogen">AutoGen</mat-option>
              <mat-option value="openai">OpenAI Agents</mat-option>
              <mat-option value="anthropic">Anthropic Claude</mat-option>
              <mat-option value="custom">Custom / Other</mat-option>
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Environment</mat-label>
            <mat-select [(ngModel)]="form.environment">
              <mat-option value="development">Development</mat-option>
              <mat-option value="staging">Staging</mat-option>
              <mat-option value="production">Production</mat-option>
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Default Action</mat-label>
            <mat-select [(ngModel)]="form.default_action">
              <mat-option value="AUDIT">Audit (log only)</mat-option>
              <mat-option value="BLOCK">Block (enforce)</mat-option>
              <mat-option value="ALLOW">Allow (passthrough)</mat-option>
            </mat-select>
          </mat-form-field>
        </div>
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Description</mat-label>
          <textarea matInput [(ngModel)]="form.description" rows="2"
                    placeholder="Brief description of this AI deployment"></textarea>
        </mat-form-field>
        <div class="form-actions">
          <button mat-flat-button color="primary" (click)="createDeployment()"
                  [disabled]="!form.name" matTooltip="Register and generate MCP API key">
            <mat-icon>vpn_key</mat-icon> Register &amp; Get MCP Config
          </button>
          <button mat-button (click)="showForm = false">Cancel</button>
        </div>
      </mat-card>
    }

    <!-- MCP Config Panel -->
    @if (configPanel) {
      <mat-card class="config-card">
        <div class="config-header">
          <h3><mat-icon>integration_instructions</mat-icon> MCP Connection Config — {{ configPanel.name }}</h3>
          <button mat-icon-button (click)="configPanel = null" matTooltip="Close"><mat-icon>close</mat-icon></button>
        </div>
        <p class="config-desc">Use one of the snippets below to connect your AI agent to the GenCrafter MCP server.</p>

        <mat-tab-group animationDuration="200ms">
          <mat-tab label="Python (MCP Client)">
            <div class="snippet-wrap">
              <button mat-icon-button class="copy-btn" (click)="copyToClipboard(configPanel.snippets.python_generic)"
                      matTooltip="Copy to clipboard"><mat-icon>content_copy</mat-icon></button>
              <pre class="snippet">{{ configPanel.snippets.python_generic }}</pre>
            </div>
          </mat-tab>
          <mat-tab label="LangChain">
            <div class="snippet-wrap">
              <button mat-icon-button class="copy-btn" (click)="copyToClipboard(configPanel.snippets.python_langchain)"
                      matTooltip="Copy to clipboard"><mat-icon>content_copy</mat-icon></button>
              <pre class="snippet">{{ configPanel.snippets.python_langchain }}</pre>
            </div>
          </mat-tab>
          <mat-tab label="JSON Config">
            <div class="snippet-wrap">
              <button mat-icon-button class="copy-btn" (click)="copyToClipboard(configPanel.snippets.json_config)"
                      matTooltip="Copy to clipboard"><mat-icon>content_copy</mat-icon></button>
              <pre class="snippet">{{ configPanel.snippets.json_config }}</pre>
            </div>
          </mat-tab>
          <mat-tab label="Environment Variables">
            <div class="snippet-wrap">
              <button mat-icon-button class="copy-btn" (click)="copyToClipboard(configPanel.snippets.env_vars)"
                      matTooltip="Copy to clipboard"><mat-icon>content_copy</mat-icon></button>
              <pre class="snippet">{{ configPanel.snippets.env_vars }}</pre>
            </div>
          </mat-tab>
        </mat-tab-group>
      </mat-card>
    }

    <!-- Deployment Cards -->
    <div class="deploy-grid">
      @for (d of deployments(); track d.id) {
        <mat-card class="deploy-card" [class.inactive]="!d.is_active">
          <div class="dc-header">
            <div class="dc-icon" [style.background]="getFrameworkColor(d.framework) + '18'"
                 [style.color]="getFrameworkColor(d.framework)">
              <mat-icon>{{ getFrameworkIcon(d.framework) }}</mat-icon>
            </div>
            <div class="dc-info">
              <h3>{{ d.name }}</h3>
              <span class="dc-meta">{{ d.framework | titlecase }} · {{ d.environment | titlecase }}</span>
            </div>
            <mat-slide-toggle [checked]="d.is_active" (change)="toggleActive(d)"
                              matTooltip="Enable or disable this deployment" color="primary">
            </mat-slide-toggle>
          </div>

          @if (d.description) {
            <p class="dc-desc">{{ d.description }}</p>
          }

          <div class="dc-stats">
            <div class="dc-stat">
              <span class="dc-stat-val">{{ d.total_scans }}</span>
              <span class="dc-stat-label">Scans</span>
            </div>
            <div class="dc-stat">
              <span class="dc-stat-val" style="color:var(--status-danger)">{{ d.total_violations }}</span>
              <span class="dc-stat-label">Violations</span>
            </div>
            <div class="dc-stat">
              <span class="dc-stat-val dc-key" matTooltip="Click to reveal full API key" (click)="toggleKeyVisibility(d)">
                {{ d._showKey ? d.api_key : (d.api_key?.substring(0, 8) + '••••') }}
              </span>
              <span class="dc-stat-label">API Key</span>
            </div>
          </div>

          @if (d.last_seen_at) {
            <div class="dc-lastseen">
              <mat-icon>schedule</mat-icon> Last seen: {{ d.last_seen_at | date:'medium' }}
            </div>
          }

          <mat-divider></mat-divider>
          <div class="dc-actions">
            <button mat-stroked-button (click)="showConfig(d)" matTooltip="View MCP connection snippets">
              <mat-icon>code</mat-icon> MCP Config
            </button>
            <button mat-icon-button (click)="regenerateKey(d)" matTooltip="Generate a new API key (invalidates old one)">
              <mat-icon>refresh</mat-icon>
            </button>
            <button mat-icon-button color="warn" (click)="deleteDeployment(d.id)" matTooltip="Delete this deployment">
              <mat-icon>delete</mat-icon>
            </button>
          </div>
        </mat-card>
      }
    </div>

    @if (!deployments().length && !showForm) {
      <mat-card class="empty-card">
        <mat-icon class="empty-icon">hub</mat-icon>
        <h2>No AI deployments registered</h2>
        <p>Register your first AI project to get an MCP connection config for automatic compliance scanning.</p>
        <button mat-flat-button color="primary" (click)="showForm = true">
          <mat-icon>add</mat-icon> Register AI Deployment
        </button>
      </mat-card>
    }
  `,
  styles: [`
    .toolbar { margin-bottom: 16px; }

    /* ── Stats ────────────────────────────────── */
    .stats-grid {
      display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px;
    }

    /* ── Form ─────────────────────────────────── */
    .form-card { padding: 24px; margin-bottom: 20px; display: flex; flex-direction: column; gap: 12px; }
    .form-card h3 { margin: 0; display: flex; align-items: center; gap: 8px; font-size: 16px;
      mat-icon { color: var(--brand-blue); }
    }
    .form-desc { margin: 0; font-size: 13px; color: var(--text-secondary); }
    .form-grid {
      display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 8px;
    }
    .full-width { width: 100%; }
    .form-actions { display: flex; gap: 8px; }

    /* ── Config Panel ─────────────────────────── */
    .config-card { padding: 24px; margin-bottom: 20px; }
    .config-header { display: flex; justify-content: space-between; align-items: center;
      h3 { margin: 0; display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 700;
        mat-icon { color: var(--brand-blue); font-size: 20px; width: 20px; height: 20px; }
      }
    }
    .config-desc { margin: 4px 0 12px; font-size: 13px; color: var(--text-secondary); }
    .snippet-wrap { position: relative; margin-top: 12px; }
    .copy-btn { position: absolute; top: 4px; right: 4px; z-index: 2; }
    .snippet {
      background: #0f1629; color: #e0e6f0; padding: 18px 20px; border-radius: 12px;
      font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 12px;
      line-height: 1.6; overflow-x: auto; white-space: pre; margin: 0;
    }

    /* ── Deployment Cards ─────────────────────── */
    .deploy-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 16px;
    }
    .deploy-card { padding: 20px; transition: all 0.2s ease; }
    .deploy-card.inactive { opacity: 0.55; }
    .dc-header { display: flex; align-items: center; gap: 14px; margin-bottom: 10px; }
    .dc-icon {
      width: 44px; height: 44px; border-radius: 14px;
      display: flex; align-items: center; justify-content: center; flex-shrink: 0;
      mat-icon { font-size: 22px; width: 22px; height: 22px; }
    }
    .dc-info { flex: 1; min-width: 0; }
    .dc-info h3 { margin: 0; font-size: 15px; font-weight: 700; color: var(--text-primary); }
    .dc-meta { font-size: 12px; color: var(--text-secondary); }
    .dc-desc { margin: 0 0 10px; font-size: 12px; color: var(--text-secondary); line-height: 1.4; }

    .dc-stats { display: flex; gap: 24px; margin: 12px 0; }
    .dc-stat { display: flex; flex-direction: column; }
    .dc-stat-val { font-size: 16px; font-weight: 700; color: var(--text-primary); }
    .dc-stat-label { font-size: 10px; color: var(--text-disabled); text-transform: uppercase; letter-spacing: 0.5px; }
    .dc-key { font-family: monospace; font-size: 11px; cursor: pointer; word-break: break-all; }

    .dc-lastseen {
      display: flex; align-items: center; gap: 6px;
      font-size: 11px; color: var(--text-disabled); margin-bottom: 8px;
      mat-icon { font-size: 14px; width: 14px; height: 14px; }
    }

    .dc-actions { display: flex; gap: 6px; align-items: center; margin-top: 12px; }

    /* ── Empty ─────────────────────────────────── */
    .empty-card {
      padding: 56px !important; text-align: center;
      display: flex; flex-direction: column; align-items: center; gap: 10px;
    }
    .empty-icon { font-size: 56px; width: 56px; height: 56px; color: var(--text-disabled); }
    .empty-card h2 { margin: 0; font-size: 18px; color: var(--text-primary); }
    .empty-card p { margin: 0; font-size: 13px; color: var(--text-secondary); max-width: 400px; }
  `],
})
export class EndpointListComponent implements OnInit {
  private api = inject(ApiService);
  private snackBar = inject(MatSnackBar);

  deployments = signal<any[]>([]);
  showForm = false;
  form = { name: '', description: '', framework: 'custom', environment: 'development', default_action: 'AUDIT' };
  configPanel: any = null;

  ngOnInit() { this.load(); }

  activeCount() { return this.deployments().filter(d => d.is_active).length; }
  totalScans() { return this.deployments().reduce((s, d) => s + (d.total_scans || 0), 0); }
  totalViolations() { return this.deployments().reduce((s, d) => s + (d.total_violations || 0), 0); }

  load() {
    this.api.listMcpDeployments().subscribe({ next: (d) => this.deployments.set(d), error: () => {} });
  }

  createDeployment() {
    this.api.createMcpDeployment(this.form).subscribe({
      next: (d) => {
        this.showForm = false;
        this.form = { name: '', description: '', framework: 'custom', environment: 'development', default_action: 'AUDIT' };
        this.load();
        this.showConfig(d);
        this.snackBar.open('Deployment registered! Copy the MCP config below.', 'OK', { duration: 4000 });
      },
      error: () => this.snackBar.open('Registration failed', 'OK', { duration: 3000 }),
    });
  }

  showConfig(d: any) {
    this.api.getMcpConfig(d.id).subscribe({
      next: (snippets) => { this.configPanel = { name: d.name, snippets }; },
      error: () => this.snackBar.open('Could not load MCP config', 'OK', { duration: 3000 }),
    });
  }

  toggleActive(d: any) {
    this.api.updateMcpDeployment(d.id, { is_active: !d.is_active }).subscribe({
      next: () => this.load(),
      error: () => this.load(),
    });
  }

  regenerateKey(d: any) {
    this.api.regenerateMcpKey(d.id).subscribe({
      next: (updated) => {
        this.load();
        this.snackBar.open('New API key generated. Update your MCP config.', 'OK', { duration: 4000 });
      },
      error: () => this.snackBar.open('Failed to regenerate key', 'OK', { duration: 3000 }),
    });
  }

  deleteDeployment(id: string) {
    this.api.deleteMcpDeployment(id).subscribe({
      next: () => { this.load(); this.snackBar.open('Deployment deleted', 'OK', { duration: 2000 }); },
      error: () => {},
    });
  }

  toggleKeyVisibility(d: any) {
    d._showKey = !d._showKey;
  }

  copyToClipboard(text: string) {
    navigator.clipboard.writeText(text).then(() => {
      this.snackBar.open('Copied to clipboard', 'OK', { duration: 1500 });
    });
  }

  getFrameworkIcon(fw: string): string {
    const map: Record<string, string> = {
      langchain: 'link', crewai: 'groups', autogen: 'smart_toy',
      openai: 'psychology', anthropic: 'psychology_alt', custom: 'code',
    };
    return map[fw] || 'code';
  }

  getFrameworkColor(fw: string): string {
    const map: Record<string, string> = {
      langchain: '#10B981', crewai: '#8B5CF6', autogen: '#F59E0B',
      openai: '#000000', anthropic: '#D97706', custom: '#4C6FFF',
    };
    return map[fw] || '#4C6FFF';
  }
}
