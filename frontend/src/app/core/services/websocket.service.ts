import { Injectable } from '@angular/core';
import { Observable, Subject, timer } from 'rxjs';
import { retryWhen, delay } from 'rxjs/operators';

@Injectable({ providedIn: 'root' })
export class WebSocketService {
  private connections = new Map<string, WebSocket>();
  private subjects = new Map<string, Subject<any>>();

  connect(channel: string): Observable<any> {
    if (this.subjects.has(channel)) {
      return this.subjects.get(channel)!.asObservable();
    }

    const subject = new Subject<any>();
    this.subjects.set(channel, subject);
    this.createConnection(channel, subject);
    return subject.asObservable();
  }

  private createConnection(channel: string, subject: Subject<any>) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const port = '8000';
    const url = `${protocol}//${host}:${port}/ws/${channel}`;

    try {
      const ws = new WebSocket(url);
      this.connections.set(channel, ws);

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          subject.next(data);
        } catch {
          subject.next(event.data);
        }
      };

      ws.onerror = () => {
        // Reconnect after 5 seconds
        setTimeout(() => this.createConnection(channel, subject), 5000);
      };

      ws.onclose = () => {
        this.connections.delete(channel);
        // Reconnect after 3 seconds
        setTimeout(() => this.createConnection(channel, subject), 3000);
      };
    } catch {
      setTimeout(() => this.createConnection(channel, subject), 5000);
    }
  }

  disconnect(channel: string) {
    const ws = this.connections.get(channel);
    if (ws) {
      ws.close();
      this.connections.delete(channel);
    }
    this.subjects.get(channel)?.complete();
    this.subjects.delete(channel);
  }

  disconnectAll() {
    this.connections.forEach((ws) => ws.close());
    this.connections.clear();
    this.subjects.forEach((s) => s.complete());
    this.subjects.clear();
  }
}
