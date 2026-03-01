import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, MatCardModule, MatIconModule, MatButtonModule,
            MatFormFieldModule, MatInputModule, MatSelectModule, MatSlideToggleModule],
  template: `
    <div class="page-header">
      <h1>Settings</h1>
      <p>Configure proxy, LLM, and system settings</p>
    </div>

    <div class="settings-grid">
      <mat-card>
        <mat-card-header>
          <mat-card-title><mat-icon>router</mat-icon> Proxy Configuration</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <div class="setting-row">
            <span>Proxy Status</span>
            <div class="status-controls">
              <span class="badge badge-allow">{{ proxyStatus() }}</span>
              <button mat-stroked-button (click)="toggleProxy()">
                {{ proxyStatus() === 'active' ? 'Stop' : 'Start' }}
              </button>
            </div>
          </div>
          <div class="setting-row">
            <span>Proxy Port</span>
            <span>8080</span>
          </div>
          <div class="setting-row">
            <span>PAC File URL</span>
            <code>http://localhost:8000/api/v1/proxy/pac</code>
          </div>
        </mat-card-content>
      </mat-card>

      <mat-card>
        <mat-card-header>
          <mat-card-title><mat-icon>psychology</mat-icon> LLM Configuration</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <div class="setting-row">
            <span>Provider</span>
            <span>Ollama (local, no auth)</span>
          </div>
          <div class="setting-row">
            <span>Model</span>
            <span>llama3.2:3b</span>
          </div>
          <div class="setting-row">
            <span>Ollama URL</span>
            <code>http://ollama:11434</code>
          </div>
          <div class="setting-row">
            <span>Embedding Model</span>
            <span>all-MiniLM-L6-v2 (local)</span>
          </div>
          <div class="setting-row">
            <span>RAG Top-K</span>
            <span>5</span>
          </div>
        </mat-card-content>
      </mat-card>

      <mat-card>
        <mat-card-header>
          <mat-card-title><mat-icon>account_tree</mat-icon> CIL Pipeline</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <div class="setting-row"><span>Step 1</span><span>Signal Collection (Browser Extension)</span></div>
          <div class="setting-row"><span>Step 2</span><span>Context Classification (MiniLM embedding)</span></div>
          <div class="setting-row"><span>Step 3</span><span>PII Detection / NER (regex + keywords)</span></div>
          <div class="setting-row"><span>Step 4</span><span>Intent Detection (Ollama LLM)</span></div>
          <div class="setting-row"><span>Step 5</span><span>Context Object Builder (CIL output)</span></div>
        </mat-card-content>
      </mat-card>

      <mat-card>
        <mat-card-header>
          <mat-card-title><mat-icon>storage</mat-icon> Database</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <div class="setting-row"><span>PostgreSQL</span><span>localhost:5432</span></div>
          <div class="setting-row"><span>Redis</span><span>localhost:6379</span></div>
          <div class="setting-row"><span>ChromaDB</span><span>localhost:8001</span></div>
        </mat-card-content>
      </mat-card>

      <mat-card>
        <mat-card-header>
          <mat-card-title><mat-icon>info</mat-icon> System Info</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <div class="setting-row"><span>Version</span><span>1.0.0</span></div>
          <div class="setting-row"><span>API Docs</span><a href="/docs" target="_blank">Swagger UI</a></div>
          <div class="setting-row"><span>Health</span><a href="/health" target="_blank">/health</a></div>
        </mat-card-content>
      </mat-card>

      <mat-card class="full-width">
        <mat-card-header>
          <mat-card-title><mat-icon>vpn_lock</mat-icon> MITM Proxy Setup (Runtime Interception)</mat-card-title>
        </mat-card-header>
        <mat-card-content>
          <p class="setup-desc">The MITM proxy intercepts real AI traffic (OpenAI, Anthropic, etc.) and routes it through the compliance pipeline before forwarding.</p>
          <div class="setting-row"><span>MITM Proxy Port</span><code>localhost:8080</code></div>
          <div class="setting-row"><span>Service</span><span>mitmproxy (mitmdump)</span></div>
          <div class="setting-row"><span>Intercepted Domains</span><span>api.openai.com, api.anthropic.com, copilot.microsoft.com, ...</span></div>
          <div class="setup-section">
            <h4>Option 1: System-wide proxy (recommended)</h4>
            <code class="code-block">export http_proxy=http://&lt;VM_IP&gt;:8080<br>export https_proxy=http://&lt;VM_IP&gt;:8080</code>
          </div>
          <div class="setup-section">
            <h4>Option 2: PAC file (selective)</h4>
            <code class="code-block">Configure browser/OS to use PAC URL:<br>http://&lt;VM_IP&gt;:8000/api/v1/proxy/pac</code>
          </div>
          <div class="setup-section">
            <h4>Option 3: Test with curl</h4>
            <code class="code-block">curl -x http://&lt;VM_IP&gt;:8080 \<br>&nbsp;&nbsp;-H "Content-Type: application/json" \<br>&nbsp;&nbsp;-d '&#123;"messages":[&#123;"role":"user","content":"Patient SSN 123-45-6789"&#125;]&#125;' \<br>&nbsp;&nbsp;http://api.openai.com/v1/chat/completions</code>
          </div>
          <div class="setup-section">
            <h4>For HTTPS interception</h4>
            <p class="setup-hint">Install the mitmproxy CA certificate on client machines:<br>
            <code>http://&lt;VM_IP&gt;:8080/cert/pem</code> (visit via browser while proxy is set)</p>
          </div>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [`
    .settings-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    mat-card-title {
      display: flex; align-items: center; gap: 8px; font-size: 16px;
      mat-icon { color: var(--accent-blue); }
    }
    .setting-row {
      display: flex; justify-content: space-between; align-items: center;
      padding: 12px 0; border-bottom: 1px solid var(--border); font-size: 14px;
      &:last-child { border-bottom: none; }
    }
    .status-controls { display: flex; align-items: center; gap: 12px; }
    .full-width { grid-column: 1 / -1; }
    code { font-size: 12px; color: var(--accent-purple); }
    a { color: var(--accent-blue); text-decoration: none; }
    .setup-desc { color: var(--text-secondary); font-size: 13px; margin-bottom: 12px; padding-top: 8px; }
    .setup-section {
      margin-top: 16px; padding: 12px; background: var(--bg-secondary);
      border: 1px solid var(--border); border-radius: 8px;
      h4 { font-size: 13px; color: var(--accent-blue); margin-bottom: 8px; }
    }
    .code-block {
      display: block; font-size: 12px; color: var(--accent-green);
      background: var(--bg-primary); padding: 10px 12px; border-radius: 6px;
      line-height: 1.6; word-break: break-all;
    }
    .setup-hint { font-size: 13px; color: var(--text-secondary); line-height: 1.5; }
  `],
})
export class SettingsComponent {
  private api = inject(ApiService);
  proxyStatus = signal('active');

  toggleProxy() {
    if (this.proxyStatus() === 'active') {
      this.api.stopProxy().subscribe({ next: () => this.proxyStatus.set('stopped') });
    } else {
      this.api.startProxy().subscribe({ next: () => this.proxyStatus.set('active') });
    }
  }
}
