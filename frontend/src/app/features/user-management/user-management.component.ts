import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatTableModule } from '@angular/material/table';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatDividerModule } from '@angular/material/divider';
import { FormsModule } from '@angular/forms';
import { UserService, UserProfile } from '../../core/services/user.service';

@Component({
  selector: 'app-user-management',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatButtonModule,
            MatInputModule, MatFormFieldModule, MatTableModule,
            MatSlideToggleModule, MatChipsModule, MatTooltipModule, MatSelectModule,
            MatProgressBarModule, MatDividerModule, FormsModule],
  template: `
    <div class="page">
      <div class="toolbar">
        <div>
          <h1>User Management</h1>
          <p class="subtitle">Manage platform users, roles, and access</p>
        </div>
        <div class="toolbar-btns">
          <button mat-stroked-button (click)="showImport = !showImport; showForm = false"
                  matTooltip="Bulk import users from Active Directory, SAML, or OIDC/SSO">
            <mat-icon>cloud_download</mat-icon> Import from SSO / AD
          </button>
          <button mat-flat-button color="primary" (click)="showForm = !showForm; showImport = false"
                  matTooltip="Manually create a single user with email and password">
            <mat-icon>person_add</mat-icon> Add User
          </button>
        </div>
      </div>

      <!-- Stats -->
      <div class="stats-grid">
        <mat-card class="stat-card" matTooltip="Total registered users across your organization">
          <div class="stat-icon-wrap" style="background:#E3F2FD">
            <mat-icon style="color:#1565C0">people</mat-icon>
          </div>
          <div class="stat-body">
            <span class="stat-value">{{ stats.total_users }}</span>
            <span class="stat-label">Total Users</span>
          </div>
        </mat-card>
        <mat-card class="stat-card" matTooltip="Users with active accounts who can currently sign in">
          <div class="stat-icon-wrap" style="background:#E8F5E9">
            <mat-icon style="color:#2E7D32">check_circle</mat-icon>
          </div>
          <div class="stat-body">
            <span class="stat-value">{{ stats.active_users }}</span>
            <span class="stat-label">Active</span>
          </div>
        </mat-card>
        <mat-card class="stat-card" matTooltip="Users with admin privileges who can manage settings and users">
          <div class="stat-icon-wrap" style="background:#FFF3E0">
            <mat-icon style="color:#E65100">admin_panel_settings</mat-icon>
          </div>
          <div class="stat-body">
            <span class="stat-value">{{ stats.admin_users }}</span>
            <span class="stat-label">Admins</span>
          </div>
        </mat-card>
        <mat-card class="stat-card" matTooltip="Isolated organizational units sharing this platform">
          <div class="stat-icon-wrap" style="background:#F3E5F5">
            <mat-icon style="color:#6A1B9A">business</mat-icon>
          </div>
          <div class="stat-body">
            <span class="stat-value">{{ stats.tenants }}</span>
            <span class="stat-label">Tenants</span>
          </div>
        </mat-card>
      </div>

      <!-- Add User Form -->
      @if (showForm) {
        <mat-card class="form-card">
          <h3>Create New User</h3>
          <div class="form-row">
            <mat-form-field appearance="outline">
              <mat-label>Email</mat-label>
              <input matInput [(ngModel)]="form.email" type="email" #emailInput="ngModel"
                     pattern="[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}" />
              @if (emailInput.invalid && emailInput.touched) {
                <mat-error>Enter a valid email address</mat-error>
              }
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Full Name</mat-label>
              <input matInput [(ngModel)]="form.full_name" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Password</mat-label>
              <input matInput [(ngModel)]="form.password" type="password" />
            </mat-form-field>
          </div>
          <div class="form-row">
            <mat-slide-toggle [(ngModel)]="form.is_admin" color="primary"
                              matTooltip="Admins can manage users, categories, and platform settings">Admin</mat-slide-toggle>
          </div>
          <div class="form-actions">
            <button mat-flat-button color="primary" (click)="addUser()" [disabled]="!form.email || !form.password || !emailValid()"
                    matTooltip="Create the user account with the specified details">
              Create User
            </button>
            <button mat-button (click)="showForm = false" matTooltip="Discard and close this form">Cancel</button>
          </div>
          @if (formError) {
            <p class="error-msg">{{ formError }}</p>
          }
        </mat-card>
      }

      <!-- Import Users from IdP -->
      @if (showImport) {
        <mat-card class="import-card">
          <div class="import-header">
            <mat-icon class="import-icon">cloud_download</mat-icon>
            <div>
              <h3>Import Users from Identity Provider</h3>
              <p>Connect to Active Directory, SAML, or OIDC/SSO to import users in bulk</p>
            </div>
          </div>
          <mat-divider></mat-divider>

          <!-- Existing connections -->
          @if (idps.length > 0) {
            <div class="idp-list">
              @for (idp of idps; track idp.id) {
                <div class="idp-row">
                  <div class="idp-type-badge" [class]="'badge-' + idp.provider_type">
                    {{ idp.provider_type | uppercase }}
                  </div>
                  <div class="idp-info">
                    <span class="idp-name">{{ idp.name }}</span>
                    <span class="idp-meta">
                      @if (idp.last_sync_at) {
                        Last sync: {{ idp.last_sync_at | date:'medium' }} · {{ idp.last_sync_count }} imported
                      } @else {
                        Never synced
                      }
                    </span>
                  </div>
                  <div class="idp-actions">
                    <button mat-stroked-button (click)="testConnection(idp)" [disabled]="idpTesting"
                            matTooltip="Verify connectivity to this identity provider">
                      <mat-icon>wifi_tethering</mat-icon> Test
                    </button>
                    <button mat-flat-button color="primary" (click)="importUsers(idp)" [disabled]="idpImporting"
                            matTooltip="Fetch and import all users from this provider">
                      <mat-icon>group_add</mat-icon> Import
                    </button>
                    <button mat-icon-button color="warn" (click)="deleteIdp(idp.id)"
                            matTooltip="Remove this identity provider connection">
                      <mat-icon>delete</mat-icon>
                    </button>
                  </div>
                </div>
              }
            </div>
          }

          @if (idpMessage) {
            <div class="idp-message" [class.success]="idpMessageType === 'success'" [class.error]="idpMessageType === 'error'">
              <mat-icon>{{ idpMessageType === 'success' ? 'check_circle' : 'error' }}</mat-icon>
              {{ idpMessage }}
            </div>
          }

          @if (importResult) {
            <div class="import-result">
              <span class="ir-stat"><strong>{{ importResult.total_found }}</strong> found</span>
              <span class="ir-stat success"><strong>{{ importResult.imported }}</strong> imported</span>
              <span class="ir-stat warning"><strong>{{ importResult.skipped }}</strong> skipped</span>
              @if (importResult.errors.length) {
                <span class="ir-stat error"><strong>{{ importResult.errors.length }}</strong> errors</span>
              }
            </div>
          }

          @if (idpImporting) {
            <mat-progress-bar mode="indeterminate"></mat-progress-bar>
          }

          <mat-divider></mat-divider>

          <!-- Add new connection -->
          <h4>Add New Connection</h4>
          <div class="form-row">
            <mat-form-field appearance="outline">
              <mat-label>Connection Name</mat-label>
              <input matInput [(ngModel)]="idpForm.name" placeholder="e.g. Corporate AD" />
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Provider Type</mat-label>
              <mat-select [(ngModel)]="idpForm.provider_type">
                <mat-option value="ldap">Active Directory (LDAP)</mat-option>
                <mat-option value="saml">SAML 2.0</mat-option>
                <mat-option value="oidc">OIDC / SSO</mat-option>
              </mat-select>
            </mat-form-field>
          </div>

          <!-- LDAP Config -->
          @if (idpForm.provider_type === 'ldap') {
            <div class="config-section">
              <span class="config-label">LDAP / Active Directory Settings</span>
              <div class="form-row">
                <mat-form-field appearance="outline">
                  <mat-label>Server URL</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.server_url" placeholder="ldap://ad.company.com:389" />
                </mat-form-field>
                <mat-slide-toggle [(ngModel)]="idpForm.config.use_ssl" color="primary">Use SSL (LDAPS)</mat-slide-toggle>
              </div>
              <div class="form-row">
                <mat-form-field appearance="outline">
                  <mat-label>Base DN</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.base_dn" placeholder="dc=company,dc=com" />
                </mat-form-field>
                <mat-form-field appearance="outline">
                  <mat-label>Bind DN</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.bind_dn" placeholder="cn=admin,dc=company,dc=com" />
                </mat-form-field>
              </div>
              <div class="form-row">
                <mat-form-field appearance="outline">
                  <mat-label>Bind Password</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.bind_password" type="password" />
                </mat-form-field>
                <mat-form-field appearance="outline">
                  <mat-label>User Search Base</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.user_search_base" placeholder="ou=users,dc=company,dc=com" />
                </mat-form-field>
              </div>
              <div class="form-row">
                <mat-form-field appearance="outline">
                  <mat-label>User Search Filter</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.user_search_filter" placeholder="(objectClass=person)" />
                </mat-form-field>
                <mat-form-field appearance="outline">
                  <mat-label>Email Attribute</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.email_attribute" placeholder="mail" />
                </mat-form-field>
              </div>
              <div class="form-row">
                <mat-form-field appearance="outline">
                  <mat-label>Name Attribute</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.name_attribute" placeholder="displayName" />
                </mat-form-field>
                <mat-form-field appearance="outline">
                  <mat-label>Admin Group DN (optional)</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.admin_group_dn" placeholder="cn=admins,ou=groups,dc=company,dc=com" />
                </mat-form-field>
              </div>
            </div>
          }

          <!-- SAML Config -->
          @if (idpForm.provider_type === 'saml') {
            <div class="config-section">
              <span class="config-label">SAML 2.0 Settings</span>
              <div class="form-row">
                <mat-form-field appearance="outline">
                  <mat-label>IdP Metadata URL</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.metadata_url"
                         placeholder="https://idp.company.com/metadata"
                         matTooltip="Auto-discovers SSO endpoint, certificates, and entity ID from IdP metadata" />
                </mat-form-field>
              </div>
              <div class="form-row">
                <mat-form-field appearance="outline">
                  <mat-label>SP Entity ID</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.entity_id" placeholder="https://yourapp.com/saml/metadata" />
                </mat-form-field>
                <mat-form-field appearance="outline">
                  <mat-label>IdP Entity ID</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.idp_entity_id" placeholder="https://idp.company.com" />
                </mat-form-field>
              </div>
              <div class="form-row">
                <mat-form-field appearance="outline">
                  <mat-label>SSO URL</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.sso_url" placeholder="https://idp.company.com/sso/saml" />
                </mat-form-field>
                <mat-form-field appearance="outline">
                  <mat-label>SLO URL</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.slo_url" placeholder="https://idp.company.com/slo/saml" />
                </mat-form-field>
              </div>
              <div class="form-row">
                <mat-form-field appearance="outline">
                  <mat-label>Name ID Format</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.name_id_format" />
                </mat-form-field>
              </div>
              <div class="form-row">
                <mat-form-field appearance="outline">
                  <mat-label>Email Attribute</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.email_attribute" placeholder="email" />
                </mat-form-field>
                <mat-form-field appearance="outline">
                  <mat-label>Name Attribute</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.name_attribute" placeholder="displayName" />
                </mat-form-field>
              </div>
              <div class="form-row wide-row">
                <mat-form-field appearance="outline" class="full-width">
                  <mat-label>X.509 Certificate (PEM)</mat-label>
                  <textarea matInput [(ngModel)]="idpForm.config.certificate" rows="4"
                            placeholder="-----BEGIN CERTIFICATE-----..."></textarea>
                </mat-form-field>
              </div>
              <div class="form-row">
                <mat-slide-toggle [(ngModel)]="idpForm.config.sign_requests" color="primary">Sign Requests</mat-slide-toggle>
                <mat-slide-toggle [(ngModel)]="idpForm.config.want_assertions_signed" color="primary">Require Signed Assertions</mat-slide-toggle>
              </div>
              <mat-divider></mat-divider>
              <span class="config-label" style="margin-top:12px">
                SCIM Provisioning (required for bulk import)
              </span>
              <div class="form-row">
                <mat-form-field appearance="outline">
                  <mat-label>SCIM Endpoint</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.scim_endpoint"
                         placeholder="https://idp.company.com/scim/v2"
                         matTooltip="SCIM 2.0 endpoint exposed by your IdP for user provisioning" />
                </mat-form-field>
                <mat-form-field appearance="outline">
                  <mat-label>SCIM Bearer Token</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.scim_token" type="password"
                         matTooltip="API token with read access to SCIM /Users endpoint" />
                </mat-form-field>
              </div>
            </div>
          }

          <!-- OIDC Config -->
          @if (idpForm.provider_type === 'oidc') {
            <div class="config-section">
              <span class="config-label">OIDC / SSO Settings</span>
              <div class="form-row">
                <mat-form-field appearance="outline">
                  <mat-label>Issuer URL</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.issuer_url" placeholder="https://accounts.google.com" />
                </mat-form-field>
                <mat-form-field appearance="outline">
                  <mat-label>Client ID</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.client_id" />
                </mat-form-field>
              </div>
              <div class="form-row">
                <mat-form-field appearance="outline">
                  <mat-label>Client Secret</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.client_secret" type="password" />
                </mat-form-field>
                <mat-form-field appearance="outline">
                  <mat-label>Redirect URI</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.redirect_uri" placeholder="https://yourapp.com/auth/callback" />
                </mat-form-field>
              </div>
              <div class="form-row">
                <mat-form-field appearance="outline">
                  <mat-label>Authorization Endpoint</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.authorization_endpoint" />
                </mat-form-field>
                <mat-form-field appearance="outline">
                  <mat-label>Token Endpoint</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.token_endpoint" />
                </mat-form-field>
              </div>
              <div class="form-row">
                <mat-form-field appearance="outline">
                  <mat-label>UserInfo Endpoint</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.userinfo_endpoint" />
                </mat-form-field>
                <mat-form-field appearance="outline">
                  <mat-label>Scopes</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.scopes" placeholder="openid email profile" />
                </mat-form-field>
              </div>
              <div class="form-row">
                <mat-form-field appearance="outline">
                  <mat-label>Email Claim</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.email_claim" placeholder="email" />
                </mat-form-field>
                <mat-form-field appearance="outline">
                  <mat-label>Name Claim</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.name_claim" placeholder="name" />
                </mat-form-field>
              </div>
              <div class="form-row">
                <mat-form-field appearance="outline">
                  <mat-label>SCIM Endpoint (optional)</mat-label>
                  <input matInput [(ngModel)]="idpForm.config.scim_endpoint"
                         placeholder="https://provider.com/scim/v2"
                         matTooltip="Override auto-detected SCIM endpoint for user import" />
                </mat-form-field>
              </div>
            </div>
          }

          <div class="form-actions">
            <button mat-flat-button color="primary" (click)="saveIdp()" [disabled]="!idpForm.name || !idpForm.provider_type"
                    matTooltip="Save this identity provider connection for future imports">
              <mat-icon>save</mat-icon> Save Connection
            </button>
            <button mat-button (click)="showImport = false" matTooltip="Discard and close">Cancel</button>
          </div>
          @if (idpFormError) { <p class="error-msg">{{ idpFormError }}</p> }
        </mat-card>
      }

      <!-- Users Table -->
      <mat-card class="table-card">
        <table mat-table [dataSource]="users" class="full-table">
          <ng-container matColumnDef="full_name">
            <th mat-header-cell *matHeaderCellDef>Name</th>
            <td mat-cell *matCellDef="let row">
              <div class="user-cell">
                <div class="avatar" [style.background]="getAvatarColor(row.email)">
                  {{ getInitials(row.full_name || row.email) }}
                </div>
                <div>
                  <span class="user-name">{{ row.full_name || '—' }}</span>
                  <span class="user-email">{{ row.email }}</span>
                </div>
              </div>
            </td>
          </ng-container>
          <ng-container matColumnDef="role">
            <th mat-header-cell *matHeaderCellDef>Role</th>
            <td mat-cell *matCellDef="let row">
              <span class="role-chip" [class]="row.is_admin ? 'role-admin' : 'role-user'">
                {{ row.is_admin ? 'Admin' : 'User' }}
              </span>
            </td>
          </ng-container>
          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef>Status</th>
            <td mat-cell *matCellDef="let row">
              <span class="status-chip" [class]="row.is_active ? 'st-active' : 'st-inactive'">
                {{ row.is_active ? 'Active' : 'Disabled' }}
              </span>
            </td>
          </ng-container>
          <ng-container matColumnDef="created_at">
            <th mat-header-cell *matHeaderCellDef>Joined</th>
            <td mat-cell *matCellDef="let row">{{ row.created_at | date:'mediumDate' }}</td>
          </ng-container>
          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef></th>
            <td mat-cell *matCellDef="let row">
              <button mat-icon-button (click)="toggleActive(row)" [matTooltip]="row.is_active ? 'Disable' : 'Enable'">
                <mat-icon>{{ row.is_active ? 'block' : 'check_circle' }}</mat-icon>
              </button>
              <button mat-icon-button (click)="toggleAdmin(row)" [matTooltip]="row.is_admin ? 'Remove admin' : 'Make admin'">
                <mat-icon>{{ row.is_admin ? 'person_remove' : 'admin_panel_settings' }}</mat-icon>
              </button>
              <button mat-icon-button color="warn" (click)="removeUser(row.id)" matTooltip="Permanently delete this user">
                <mat-icon>delete</mat-icon>
              </button>
            </td>
          </ng-container>
          <tr mat-header-row *matHeaderRowDef="displayedCols"></tr>
          <tr mat-row *matRowDef="let row; columns: displayedCols;"></tr>
        </table>
        @if (!users.length) {
          <div class="empty">No users registered yet. Click "Add User" to create one.</div>
        }
      </mat-card>
    </div>
  `,
  styles: [`
    .page { display: flex; flex-direction: column; gap: 16px; }
    .toolbar { display: flex; align-items: center; justify-content: space-between; }
    .toolbar h1 { margin: 0; font-size: 22px; color: var(--text-primary); }
    .subtitle { margin: 4px 0 0; color: var(--text-secondary); font-size: 13px; }

    .stats-grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px;
    }
    .stat-card { display: flex; align-items: center; gap: 14px; padding: 16px; }
    .stat-icon-wrap {
      width: 42px; height: 42px; border-radius: 10px;
      display: flex; align-items: center; justify-content: center;
    }
    .stat-icon-wrap mat-icon { font-size: 22px; width: 22px; height: 22px; }
    .stat-body { display: flex; flex-direction: column; }
    .stat-value { font-size: 22px; font-weight: 700; color: var(--text-primary); line-height: 1; }
    .stat-label { font-size: 11px; color: var(--text-secondary); margin-top: 4px; }

    .form-card { padding: 20px; display: flex; flex-direction: column; gap: 10px; }
    .form-card h3 { margin: 0 0 4px; font-size: 15px; }
    .form-row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
    .form-row mat-form-field { flex: 1; min-width: 180px; }
    .form-actions { display: flex; gap: 8px; }
    .error-msg { color: #C62828; font-size: 13px; margin: 4px 0 0; }

    .table-card { padding: 0; overflow: hidden; }
    .full-table { width: 100%; }

    .user-cell { display: flex; align-items: center; gap: 10px; }
    .avatar {
      width: 32px; height: 32px; border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      color: #fff; font-size: 12px; font-weight: 600;
      text-transform: uppercase;
    }
    .user-name { display: block; font-size: 13px; font-weight: 500; color: var(--text-primary); }
    .user-email { display: block; font-size: 11px; color: var(--text-secondary); }

    .role-chip {
      padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: uppercase;
    }
    .role-admin { background: #FFF3E0; color: #E65100; }
    .role-user { background: #E3F2FD; color: #1565C0; }

    .status-chip {
      padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: uppercase;
    }
    .st-active { background: #E8F5E9; color: #2E7D32; }
    .st-inactive { background: #FFEBEE; color: #C62828; }

    .empty { padding: 32px; text-align: center; color: var(--text-disabled); font-size: 13px; }

    .toolbar-btns { display: flex; gap: 8px; }

    /* ── Import Card ────────────────────────────── */
    .import-card { padding: 24px !important; display: flex; flex-direction: column; gap: 16px; }
    .import-header { display: flex; align-items: center; gap: 16px; }
    .import-icon { font-size: 36px; width: 36px; height: 36px; color: var(--brand-blue); }
    .import-header h3 { margin: 0; font-size: 16px; font-weight: 700; color: var(--text-primary); }
    .import-header p { margin: 2px 0 0; font-size: 13px; color: var(--text-secondary); }
    .import-card h4 { margin: 0; font-size: 14px; font-weight: 600; color: var(--text-primary); }

    .config-section { display: flex; flex-direction: column; gap: 8px; }
    .config-label {
      font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px;
      color: var(--text-disabled); margin-bottom: 4px;
    }
    .wide-row { flex-direction: column !important; }
    .full-width { width: 100% !important; min-width: 100% !important; }

    /* ── IdP List ───────────────────────────────── */
    .idp-list { display: flex; flex-direction: column; gap: 8px; }
    .idp-row {
      display: flex; align-items: center; gap: 14px;
      padding: 12px 16px; border-radius: 12px;
      background: rgba(0,0,0,0.02); border: 1px solid rgba(0,0,0,0.04);
    }
    .idp-type-badge {
      padding: 4px 10px; border-radius: 8px; font-size: 10px; font-weight: 800;
      letter-spacing: 0.5px;
    }
    .badge-ldap { background: #E3F2FD; color: #1565C0; }
    .badge-saml { background: #FFF3E0; color: #E65100; }
    .badge-oidc { background: #F3E5F5; color: #6A1B9A; }
    .idp-info { flex: 1; display: flex; flex-direction: column; }
    .idp-name { font-size: 14px; font-weight: 600; color: var(--text-primary); }
    .idp-meta { font-size: 11px; color: var(--text-secondary); }
    .idp-actions { display: flex; gap: 6px; align-items: center; }

    .idp-message {
      display: flex; align-items: center; gap: 8px;
      padding: 10px 14px; border-radius: 10px; font-size: 13px; font-weight: 500;
    }
    .idp-message.success { background: #E8F5E9; color: #2E7D32; }
    .idp-message.error { background: #FFEBEE; color: #C62828; }
    .idp-message mat-icon { font-size: 18px; width: 18px; height: 18px; }

    .import-result {
      display: flex; gap: 16px; padding: 10px 0;
    }
    .ir-stat { font-size: 13px; color: var(--text-secondary); }
    .ir-stat.success { color: #2E7D32; }
    .ir-stat.warning { color: #E65100; }
    .ir-stat.error { color: #C62828; }
  `]
})
export class UserManagementComponent implements OnInit {
  private svc = inject(UserService);
  users: UserProfile[] = [];
  stats = { total_users: 0, active_users: 0, admin_users: 0, tenants: 0 };
  showForm = false;
  form = { email: '', full_name: '', password: '', is_admin: false };
  formError = '';
  private emailRegex = /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/;
  displayedCols = ['full_name', 'role', 'status', 'created_at', 'actions'];

  // Identity provider state
  showImport = false;
  idps: any[] = [];
  idpForm: any = this.freshIdpForm();
  idpFormError = '';
  idpTesting = false;
  idpImporting = false;
  idpMessage = '';
  idpMessageType: 'success' | 'error' = 'success';
  importResult: any = null;

  private avatarColors = ['#1565C0', '#6A1B9A', '#2E7D32', '#C62828', '#EF6C00', '#283593', '#00838F', '#4E342E'];

  ngOnInit() { this.load(); this.loadIdps(); }

  load() {
    this.svc.listUsers().subscribe({ next: (d: UserProfile[]) => this.users = d, error: () => {} });
    this.svc.getStats().subscribe({ next: (d: any) => this.stats = d, error: () => {} });
  }

  emailValid(): boolean {
    return this.emailRegex.test(this.form.email);
  }

  addUser() {
    this.formError = '';
    if (!this.emailValid()) {
      this.formError = 'Please enter a valid email address';
      return;
    }
    this.svc.createUser(this.form).subscribe({
      next: () => {
        this.showForm = false;
        this.form = { email: '', full_name: '', password: '', is_admin: false };
        this.load();
      },
      error: (err: any) => this.formError = err?.error?.detail || 'Failed to create user',
    });
  }

  toggleActive(user: UserProfile) {
    this.svc.updateUser(user.id, { is_active: !user.is_active }).subscribe({ next: () => this.load() });
  }

  toggleAdmin(user: UserProfile) {
    this.svc.updateUser(user.id, { is_admin: !user.is_admin }).subscribe({ next: () => this.load() });
  }

  removeUser(id: string) {
    this.svc.deleteUser(id).subscribe({ next: () => this.load() });
  }

  getInitials(name: string): string {
    return name.split(/[\s@]+/).slice(0, 2).map(s => s[0] || '').join('').toUpperCase();
  }

  getAvatarColor(email: string): string {
    let hash = 0;
    for (let i = 0; i < email.length; i++) hash = email.charCodeAt(i) + ((hash << 5) - hash);
    return this.avatarColors[Math.abs(hash) % this.avatarColors.length];
  }

  // ── Identity Providers ─────────────────────────────────

  freshIdpForm(): any {
    return {
      name: '', provider_type: 'ldap',
      config: {
        server_url: '', use_ssl: false, base_dn: '', bind_dn: '', bind_password: '',
        user_search_base: '', user_search_filter: '(objectClass=person)',
        email_attribute: 'mail', name_attribute: 'displayName',
        admin_group_dn: '',
        entity_id: '', idp_entity_id: '', sso_url: '', slo_url: '', certificate: '',
        name_id_format: 'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress',
        sign_requests: true, want_assertions_signed: true,
        issuer_url: '', client_id: '', client_secret: '', redirect_uri: '',
        authorization_endpoint: '', token_endpoint: '', userinfo_endpoint: '',
        scopes: 'openid email profile', email_claim: 'email', name_claim: 'name',
      }
    };
  }

  loadIdps() {
    this.svc.listIdps().subscribe({ next: (d: any[]) => this.idps = d, error: () => {} });
  }

  saveIdp() {
    this.idpFormError = '';
    this.svc.createIdp({
      name: this.idpForm.name,
      provider_type: this.idpForm.provider_type,
      config: this.idpForm.config,
    }).subscribe({
      next: () => {
        this.idpForm = this.freshIdpForm();
        this.loadIdps();
      },
      error: (err: any) => this.idpFormError = err?.error?.detail || 'Failed to save connection',
    });
  }

  deleteIdp(id: string) {
    this.svc.deleteIdp(id).subscribe({ next: () => this.loadIdps() });
  }

  testConnection(idp: any) {
    this.idpTesting = true;
    this.idpMessage = '';
    this.svc.testIdp(idp.id).subscribe({
      next: (res: any) => {
        this.idpTesting = false;
        this.idpMessage = res.message;
        this.idpMessageType = res.status === 'ok' ? 'success' : 'error';
      },
      error: (err: any) => {
        this.idpTesting = false;
        this.idpMessage = err?.error?.detail || 'Connection test failed';
        this.idpMessageType = 'error';
      },
    });
  }

  importUsers(idp: any) {
    this.idpImporting = true;
    this.idpMessage = '';
    this.importResult = null;
    this.svc.importFromIdp(idp.id).subscribe({
      next: (res: any) => {
        this.idpImporting = false;
        this.importResult = res;
        this.idpMessage = `Import complete: ${res.imported} users imported, ${res.skipped} skipped.`;
        this.idpMessageType = 'success';
        this.load();
        this.loadIdps();
      },
      error: (err: any) => {
        this.idpImporting = false;
        this.idpMessage = err?.error?.detail || 'Import failed';
        this.idpMessageType = 'error';
      },
    });
  }
}
