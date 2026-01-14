import { useEffect } from 'react';
import { AlertsPage } from '@/pages/AlertsPage';

export function NotificationsPage() {
  useEffect(() => {
    document.title = 'Notifications - WorkflowOps';
    return () => {
      document.title = 'WorkflowOps';
    };
  }, []);
  return <AlertsPage />;
}
