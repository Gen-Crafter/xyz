import { Injectable, signal, inject } from '@angular/core';
import { WebSocketService } from './websocket.service';

export interface AppNotification {
  id: string;
  type: 'interception' | 'alert' | 'info';
  title: string;
  message: string;
  action?: string;
  severity?: string;
  timestamp: Date;
  read: boolean;
}

@Injectable({ providedIn: 'root' })
export class NotificationService {
  private ws = inject(WebSocketService);

  notifications = signal<AppNotification[]>([]);
  unreadCount = signal(0);
  latestToast = signal<AppNotification | null>(null);

  constructor() {
    this.listenForInterceptions();
    this.listenForAlerts();
  }

  private listenForInterceptions() {
    this.ws.connect('interceptions').subscribe((data: any) => {
      let notif: AppNotification;

      if (data.type === 'agent_request') {
        const status = data.compliance_status || 'PENDING';
        const severity = status === 'VIOLATION' ? 'critical' : 'low';
        const action = status === 'VIOLATION' ? 'BLOCK' : 'ALLOW';
        const vCount = data.violations_count || 0;
        notif = {
          id: data.id || crypto.randomUUID(),
          type: 'interception',
          title: `${status} — ${data.title || 'Agent Request'}`,
          message: vCount > 0
            ? `${vCount} violation(s) detected. Risk: ${data.risk_score || 0}. Regulations: ${(data.regulations_applicable || []).join(', ') || 'N/A'}`
            : 'No compliance violations detected',
          action,
          severity,
          timestamp: new Date(),
          read: false,
        };
      } else {
        const action = data.action || 'ALLOW';
        const severity = action === 'BLOCK' ? 'critical' : action === 'REDACT' ? 'high' : 'low';
        notif = {
          id: data.interception_id || crypto.randomUUID(),
          type: 'interception',
          title: `${action} — ${data.destination || 'Unknown'}`,
          message: data.policies?.length
            ? `Policies: ${data.policies.join(', ')}`
            : 'No policies triggered',
          action,
          severity,
          timestamp: new Date(),
          read: false,
        };
      }

      this.addNotification(notif);
    });
  }

  private listenForAlerts() {
    this.ws.connect('alerts').subscribe((data: any) => {
      const notif: AppNotification = {
        id: crypto.randomUUID(),
        type: 'alert',
        title: data.title || 'Alert',
        message: data.message || JSON.stringify(data),
        severity: 'critical',
        timestamp: new Date(),
        read: false,
      };
      this.addNotification(notif);
    });
  }

  private addNotification(notif: AppNotification) {
    const current = this.notifications();
    const updated = [notif, ...current].slice(0, 50);
    this.notifications.set(updated);
    this.unreadCount.set(updated.filter(n => !n.read).length);
    this.latestToast.set(notif);

    // Auto-clear toast after 5 seconds
    setTimeout(() => {
      if (this.latestToast()?.id === notif.id) {
        this.latestToast.set(null);
      }
    }, 5000);
  }

  markAllRead() {
    const updated = this.notifications().map(n => ({ ...n, read: true }));
    this.notifications.set(updated);
    this.unreadCount.set(0);
  }

  dismissToast() {
    this.latestToast.set(null);
  }

  clear() {
    this.notifications.set([]);
    this.unreadCount.set(0);
  }
}
