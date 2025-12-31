/**
 * HardDeleteConfirmDialog - Confirmation modal for permanent workflow deletion
 *
 * Admin-only dialog requiring explicit confirmation by typing DELETE.
 */

import { useState } from 'react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Input } from '@/components/ui/input';
import { Trash2 } from 'lucide-react';

interface HardDeleteConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workflowName: string;
  onConfirm: () => void;
}

export function HardDeleteConfirmDialog({
  open,
  onOpenChange,
  workflowName,
  onConfirm,
}: HardDeleteConfirmDialogProps) {
  const [confirmText, setConfirmText] = useState('');
  const expectedText = 'DELETE';

  const handleConfirm = () => {
    if (confirmText === expectedText) {
      onConfirm();
      setConfirmText('');
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      setConfirmText('');
    }
    onOpenChange(newOpen);
  };

  return (
    <AlertDialog open={open} onOpenChange={handleOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2 text-destructive">
            <Trash2 className="h-5 w-5" />
            Permanently Delete Workflow
          </AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-4">
              <p>
                You are about to <strong>permanently delete</strong>{' '}
                <strong>{workflowName}</strong>.
              </p>

              <div className="bg-destructive/10 border border-destructive/20 rounded-md p-3 text-sm">
                <p className="font-medium text-destructive">
                  This action cannot be undone.
                </p>
                <ul className="mt-2 list-disc list-inside text-destructive/80 space-y-1">
                  <li>The workflow will be removed from N8N</li>
                  <li>Execution history may be lost or become inaccessible</li>
                  <li>The workflow cannot be recovered from this system</li>
                  <li>This will create permanent drift from Git</li>
                </ul>
              </div>

              <div className="space-y-2">
                <label htmlFor="confirm-delete" className="text-sm font-medium">
                  Type <code className="bg-muted px-1 rounded">{expectedText}</code> to confirm:
                </label>
                <Input
                  id="confirm-delete"
                  value={confirmText}
                  onChange={(e) => setConfirmText(e.target.value.toUpperCase())}
                  placeholder="Type DELETE"
                  className="font-mono"
                />
              </div>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={() => setConfirmText('')}>
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={confirmText !== expectedText}
            className="bg-destructive hover:bg-destructive/90"
          >
            Delete Permanently
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
