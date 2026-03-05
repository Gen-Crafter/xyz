import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatDividerModule } from '@angular/material/divider';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { FormsModule } from '@angular/forms';
import { UserService, UserProfile } from '../../core/services/user.service';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule, MatButtonModule,
            MatInputModule, MatFormFieldModule, MatDividerModule, MatChipsModule, MatTooltipModule, FormsModule],
  template: `
    <div class="page">
      <h1>My Profile</h1>

      @if (!profile) {
        <mat-card class="auth-card">
          <div class="auth-header">
            <mat-icon class="auth-icon">lock_open</mat-icon>
            <h2>Welcome</h2>
            <p>Sign in to your account or create a new one</p>
          </div>

          <!-- Tab toggle -->
          <div class="auth-tabs">
            <button class="auth-tab" [class.active]="authMode === 'login'" (click)="authMode = 'login'"
                    matTooltip="Sign in with your existing credentials">
              Sign In
            </button>
            <button class="auth-tab" [class.active]="authMode === 'register'" (click)="authMode = 'register'"
                    matTooltip="Create a new account (first user becomes admin)">
              Register
            </button>
          </div>

          <!-- Login Form -->
          @if (authMode === 'login') {
            <div class="auth-form">
              <mat-form-field appearance="outline">
                <mat-label>Email</mat-label>
                <input matInput [(ngModel)]="loginForm.email" type="email" />
              </mat-form-field>
              <mat-form-field appearance="outline">
                <mat-label>Password</mat-label>
                <input matInput [(ngModel)]="loginForm.password" type="password"
                       (keydown.enter)="login()" />
              </mat-form-field>
              <button mat-flat-button color="primary" class="auth-btn" (click)="login()"
                      [disabled]="!loginForm.email || !loginForm.password"
                      matTooltip="Sign in to access compliance modules and features">
                <mat-icon>login</mat-icon> Sign In
              </button>
              @if (loginError) { <p class="error-msg">{{ loginError }}</p> }
            </div>
          }

          <!-- Register Form -->
          @if (authMode === 'register') {
            <div class="auth-form">
              <mat-form-field appearance="outline">
                <mat-label>Email</mat-label>
                <input matInput [(ngModel)]="regForm.email" type="email" />
              </mat-form-field>
              <mat-form-field appearance="outline">
                <mat-label>Full Name</mat-label>
                <input matInput [(ngModel)]="regForm.full_name" />
              </mat-form-field>
              <mat-form-field appearance="outline"
                [matTooltip]="pwTooltip" matTooltipPosition="right" matTooltipClass="pw-tooltip">
                <mat-label>Password</mat-label>
                <input matInput [(ngModel)]="regForm.password" type="password"
                       (keydown.enter)="register()" (ngModelChange)="onRegPwChange($event)" />
              </mat-form-field>
              <!-- Live complexity checklist -->
              @if (regForm.password && !isDefaultAdmin(regForm.email)) {
                <div class="pw-rules">
                  <div class="rule" [class.ok]="pwChecks(regForm.password).len"><mat-icon>{{ pwChecks(regForm.password).len ? 'check_circle' : 'cancel' }}</mat-icon> At least 10 characters</div>
                  <div class="rule" [class.ok]="pwChecks(regForm.password).upper"><mat-icon>{{ pwChecks(regForm.password).upper ? 'check_circle' : 'cancel' }}</mat-icon> Uppercase letter (A-Z)</div>
                  <div class="rule" [class.ok]="pwChecks(regForm.password).lower"><mat-icon>{{ pwChecks(regForm.password).lower ? 'check_circle' : 'cancel' }}</mat-icon> Lowercase letter (a-z)</div>
                  <div class="rule" [class.ok]="pwChecks(regForm.password).digit"><mat-icon>{{ pwChecks(regForm.password).digit ? 'check_circle' : 'cancel' }}</mat-icon> Number (0-9)</div>
                  <div class="rule" [class.ok]="pwChecks(regForm.password).special"><mat-icon>{{ pwChecks(regForm.password).special ? 'check_circle' : 'cancel' }}</mat-icon> Special character (!&#64;#$%…)</div>
                </div>
              }
              <button mat-flat-button color="primary" class="auth-btn" (click)="register()"
                      [disabled]="!regForm.email || !regForm.password || !pwValid(regForm.email, regForm.password)"
                      matTooltip="Register a new account. The first registered user is automatically an admin.">
                <mat-icon>person_add</mat-icon> Create Account
              </button>
              @if (regError) { <p class="error-msg">{{ regError }}</p> }
            </div>
          }
        </mat-card>
      }

      @if (profile) {
        <!-- Profile Card -->
        <mat-card class="profile-card">
          <div class="profile-header">
            <div class="avatar-lg" [style.background]="getAvatarColor(profile.email)">
              {{ getInitials(profile.full_name || profile.email) }}
            </div>
            <div class="profile-info">
              <h2>{{ profile.full_name || 'No name set' }}</h2>
              <span class="email">{{ profile.email }}</span>
              <div class="badges">
                <span class="role-chip" [class]="profile.is_admin ? 'role-admin' : 'role-user'">
                  {{ profile.is_admin ? 'Admin' : 'User' }}
                </span>
                <span class="status-chip" [class]="profile.is_active ? 'st-active' : 'st-inactive'">
                  {{ profile.is_active ? 'Active' : 'Disabled' }}
                </span>
              </div>
            </div>
          </div>
          <div class="logout-area">
            <button mat-flat-button color="warn" (click)="logout()"
                    matTooltip="Sign out and return to the login screen">
              <mat-icon>logout</mat-icon> Sign Out
            </button>
          </div>
          <mat-divider></mat-divider>
          <div class="detail-grid">
            <div class="detail-item">
              <mat-icon>fingerprint</mat-icon>
              <div>
                <span class="detail-label">User ID</span>
                <span class="detail-value mono">{{ profile.id }}</span>
              </div>
            </div>
            <div class="detail-item">
              <mat-icon>business</mat-icon>
              <div>
                <span class="detail-label">Tenant ID</span>
                <span class="detail-value mono">{{ profile.tenant_id }}</span>
              </div>
            </div>
            <div class="detail-item">
              <mat-icon>event</mat-icon>
              <div>
                <span class="detail-label">Joined</span>
                <span class="detail-value">{{ profile.created_at | date:'medium' }}</span>
              </div>
            </div>
            <div class="detail-item">
              <mat-icon>update</mat-icon>
              <div>
                <span class="detail-label">Last Updated</span>
                <span class="detail-value">{{ profile.updated_at | date:'medium' }}</span>
              </div>
            </div>
          </div>
        </mat-card>

        <!-- Edit Profile -->
        <mat-card class="section-card">
          <h3 matTooltip="Update your display name"><mat-icon>edit</mat-icon> Edit Profile</h3>
          <mat-divider></mat-divider>
          <div class="form-row">
            <mat-form-field appearance="outline" class="wide">
              <mat-label>Full Name</mat-label>
              <input matInput [(ngModel)]="editName" />
            </mat-form-field>
            <button mat-flat-button color="primary" (click)="saveName()" [disabled]="!editName"
                    matTooltip="Save your updated name">
              Save
            </button>
          </div>
          @if (editMsg) { <p class="success-msg">{{ editMsg }}</p> }
        </mat-card>

        <!-- Change Password -->
        <mat-card class="section-card">
          <h3 [matTooltip]="pwTooltip" matTooltipPosition="right"><mat-icon>lock</mat-icon> Change Password</h3>
          <mat-divider></mat-divider>
          <div class="form-row">
            <mat-form-field appearance="outline">
              <mat-label>Current Password</mat-label>
              <input matInput [(ngModel)]="pwForm.current" type="password" />
            </mat-form-field>
            <mat-form-field appearance="outline"
              [matTooltip]="pwTooltip" matTooltipPosition="right" matTooltipClass="pw-tooltip">
              <mat-label>New Password</mat-label>
              <input matInput [(ngModel)]="pwForm.newPw" type="password" />
            </mat-form-field>
            <button mat-flat-button color="warn" (click)="changePassword()"
                    [disabled]="!pwForm.current || !pwForm.newPw || !pwValid(profile?.email || '', pwForm.newPw)"
                    matTooltip="Confirm password change">
              Change
            </button>
          </div>
          @if (pwForm.newPw && profile && !isDefaultAdmin(profile.email)) {
            <div class="pw-rules">
              <div class="rule" [class.ok]="pwChecks(pwForm.newPw).len"><mat-icon>{{ pwChecks(pwForm.newPw).len ? 'check_circle' : 'cancel' }}</mat-icon> At least 10 characters</div>
              <div class="rule" [class.ok]="pwChecks(pwForm.newPw).upper"><mat-icon>{{ pwChecks(pwForm.newPw).upper ? 'check_circle' : 'cancel' }}</mat-icon> Uppercase letter (A-Z)</div>
              <div class="rule" [class.ok]="pwChecks(pwForm.newPw).lower"><mat-icon>{{ pwChecks(pwForm.newPw).lower ? 'check_circle' : 'cancel' }}</mat-icon> Lowercase letter (a-z)</div>
              <div class="rule" [class.ok]="pwChecks(pwForm.newPw).digit"><mat-icon>{{ pwChecks(pwForm.newPw).digit ? 'check_circle' : 'cancel' }}</mat-icon> Number (0-9)</div>
              <div class="rule" [class.ok]="pwChecks(pwForm.newPw).special"><mat-icon>{{ pwChecks(pwForm.newPw).special ? 'check_circle' : 'cancel' }}</mat-icon> Special character (!&#64;#$%…)</div>
            </div>
          }
          @if (pwMsg) { <p class="success-msg">{{ pwMsg }}</p> }
          @if (pwError) { <p class="error-msg">{{ pwError }}</p> }
        </mat-card>
      }
    </div>
  `,
  styles: [`
    .page { display: flex; flex-direction: column; gap: 16px; max-width: 800px; }
    h1 { margin: 0; font-size: 22px; color: var(--text-primary); font-weight: 700; }

    /* ── Auth Card ─────────────────────── */
    .auth-card {
      padding: 36px; display: flex; flex-direction: column; gap: 20px; max-width: 440px;
    }
    .auth-header {
      text-align: center; display: flex; flex-direction: column; align-items: center; gap: 8px;
    }
    .auth-icon { font-size: 48px; width: 48px; height: 48px; color: var(--brand-blue); }
    .auth-header h2 { margin: 0; font-size: 20px; font-weight: 700; color: var(--text-primary); }
    .auth-header p { margin: 0; color: var(--text-secondary); font-size: 13px; }

    .auth-tabs {
      display: flex; background: rgba(0,0,0,0.04); border-radius: 12px; padding: 3px;
    }
    .auth-tab {
      flex: 1; padding: 8px 0; border: none; background: transparent;
      font-size: 13px; font-weight: 600; color: var(--text-secondary);
      cursor: pointer; border-radius: 10px; transition: all 0.2s ease;
    }
    .auth-tab.active {
      background: #fff; color: var(--text-primary);
      box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }

    .auth-form {
      display: flex; flex-direction: column; gap: 4px;
    }
    .auth-form mat-form-field { width: 100%; }
    .auth-btn { width: 100%; height: 44px !important; font-size: 14px !important; }

    .logout-area { display: flex; justify-content: flex-end; }
    .form-row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
    .form-row mat-form-field { flex: 1; min-width: 180px; }
    .wide { flex: 2 !important; }
    .form-actions { display: flex; gap: 8px; }
    .error-msg { color: #C62828; font-size: 13px; margin: 4px 0 0; }
    .success-msg { color: #2E7D32; font-size: 13px; margin: 4px 0 0; }

    .profile-card { padding: 24px; display: flex; flex-direction: column; gap: 20px; }
    .profile-header { display: flex; align-items: center; gap: 20px; }
    .avatar-lg {
      width: 64px; height: 64px; border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      color: #fff; font-size: 22px; font-weight: 700; text-transform: uppercase;
    }
    .profile-info h2 { margin: 0; font-size: 18px; color: var(--text-primary); }
    .email { font-size: 13px; color: var(--text-secondary); }
    .badges { display: flex; gap: 6px; margin-top: 6px; }
    .role-chip, .status-chip {
      padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: uppercase;
    }
    .role-admin { background: #FFF3E0; color: #E65100; }
    .role-user { background: #E3F2FD; color: #1565C0; }
    .st-active { background: #E8F5E9; color: #2E7D32; }
    .st-inactive { background: #FFEBEE; color: #C62828; }

    .detail-grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px;
    }
    .detail-item { display: flex; align-items: center; gap: 10px; }
    .detail-item mat-icon { font-size: 20px; width: 20px; height: 20px; color: var(--text-disabled); }
    .detail-label { display: block; font-size: 11px; color: var(--text-disabled); text-transform: uppercase; letter-spacing: 0.5px; }
    .detail-value { display: block; font-size: 13px; color: var(--text-primary); }
    .mono { font-family: monospace; font-size: 11px; word-break: break-all; }

    .section-card { padding: 20px; display: flex; flex-direction: column; gap: 12px; }
    .section-card h3 {
      display: flex; align-items: center; gap: 8px;
      margin: 0; font-size: 15px; color: var(--text-primary);
    }
    .section-card h3 mat-icon { font-size: 20px; width: 20px; height: 20px; color: var(--brand-blue); }

    .pw-rules { display: flex; flex-direction: column; gap: 4px; margin: -4px 0 4px; }
    .rule {
      display: flex; align-items: center; gap: 6px;
      font-size: 12px; color: #C62828;
      mat-icon { font-size: 15px; width: 15px; height: 15px; color: #C62828; }
    }
    .rule.ok { color: #2E7D32; mat-icon { color: #2E7D32; } }
  `]
})
export class ProfileComponent implements OnInit {
  private svc = inject(UserService);
  private router = inject(Router);
  profile: UserProfile | null = null;
  authMode: 'login' | 'register' = 'login';
  loginForm = { email: '', password: '' };
  loginError = '';
  regForm = { email: '', full_name: '', password: '' };
  regError = '';
  editName = '';
  editMsg = '';
  pwForm = { current: '', newPw: '' };
  pwMsg = '';
  pwError = '';

  private readonly DEFAULT_ADMIN = 'parmeshwr.prasad@gmail.com';

  readonly pwTooltip = [
    'Password requirements:',
    '• Minimum 10 characters (longer is better)',
    '• Mix uppercase + lowercase letters',
    '• At least one number (0–9)',
    '• At least one special character: ! @ # $ % ^ & * etc.',
    '• Avoid personal info, dictionary words, or sequences like "12345"',
    '• Tip: Use a passphrase e.g. "CorrectHorseBatteryStaple@1"',
  ].join('\n');

  private avatarColors = ['#1565C0', '#6A1B9A', '#2E7D32', '#C62828', '#EF6C00', '#283593', '#00838F', '#4E342E'];

  ngOnInit() {
    this.loadProfile();
  }

  login() {
    this.loginError = '';
    this.svc.login(this.loginForm.email, this.loginForm.password).subscribe({
      next: () => {
        this.loginForm = { email: '', password: '' };
        this.loadProfile();
      },
      error: (err: any) => this.loginError = err?.error?.detail || 'Invalid email or password',
    });
  }

  register() {
    this.regError = '';
    this.svc.register(this.regForm).subscribe({
      next: () => {
        this.regForm = { email: '', full_name: '', password: '' };
        this.loadProfile();
      },
      error: (err: any) => this.regError = err?.error?.detail || 'Registration failed',
    });
  }

  logout() {
    this.svc.logout();
    this.profile = null;
    this.authMode = 'login';
  }

  private loadProfile() {
    this.svc.getProfile().subscribe({
      next: (u: UserProfile) => { this.profile = u; this.editName = u.full_name || ''; },
      error: () => {},
    });
  }

  saveName() {
    this.editMsg = '';
    this.svc.updateProfile({ full_name: this.editName }).subscribe({
      next: (u: UserProfile) => { this.profile = u; this.editMsg = 'Profile updated.'; },
    });
  }

  changePassword() {
    this.pwMsg = ''; this.pwError = '';
    this.svc.changePassword(this.pwForm.current, this.pwForm.newPw).subscribe({
      next: () => { this.pwMsg = 'Password changed successfully.'; this.pwForm = { current: '', newPw: '' }; },
      error: (err: any) => this.pwError = err?.error?.detail || 'Failed to change password',
    });
  }

  isDefaultAdmin(email: string): boolean {
    return (email || '').toLowerCase() === this.DEFAULT_ADMIN.toLowerCase();
  }

  pwChecks(pw: string): { len: boolean; upper: boolean; lower: boolean; digit: boolean; special: boolean } {
    return {
      len:     pw.length >= 10,
      upper:   /[A-Z]/.test(pw),
      lower:   /[a-z]/.test(pw),
      digit:   /\d/.test(pw),
      special: /[!@#$%^&*()\-_=+\[\]{};:'",.<>/?\\|`~]/.test(pw),
    };
  }

  pwValid(email: string, pw: string): boolean {
    if (this.isDefaultAdmin(email)) return true;
    const c = this.pwChecks(pw);
    return c.len && c.upper && c.lower && c.digit && c.special;
  }

  onRegPwChange(_val: string): void {}

  getInitials(name: string): string {
    return name.split(/[\s@]+/).slice(0, 2).map(s => s[0] || '').join('').toUpperCase();
  }

  getAvatarColor(email: string): string {
    let hash = 0;
    for (let i = 0; i < email.length; i++) hash = email.charCodeAt(i) + ((hash << 5) - hash);
    return this.avatarColors[Math.abs(hash) % this.avatarColors.length];
  }
}
