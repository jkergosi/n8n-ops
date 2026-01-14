/**
 * DirectEditWarningDialog - Warning modal before direct workflow edits
 *
 * Shows drift implications and requires acknowledgment before proceeding.
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
import { Checkbox } from '@/components/ui/checkbox';
import { AlertTriangle } from 'lucide-react';

interface DirectEditWarningDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workflowName: string;
  environmentType: string;
  onConfirm: () => void;
}

export function DirectEditWarningDialog({
  open,
  onOpenChange,
  workflowName,
  environmentType,
  onConfirm,
}: DirectEditWarningDialogProps) {
  const [acknowledged, setAcknowledged] = useState(false);

  const handleConfirm = () => {
    if (acknowledged) {
      onConfirm();
      setAcknowledged(false);
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      setAcknowledged(false);
    }
    onOpenChange(newOpen);
  };

  return (
    <AlertDialog open={open} onOpenChange={handleOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            Direct Edit Warning
          </AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-4">
              <p>
                You are about to directly edit <strong>{workflowName}</strong> in the{' '}
                <strong>{environmentType}</strong> environment.
              </p>

              <div className="bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-md p-3 text-sm">
                <p className="font-medium text-amber-800 dark:text-amber-200">
                  Direct edits create drift from Git.
                </p>
                <p className="mt-1 text-amber-700 dark:text-amber-300">
                  Recommended: Create a deployment instead to maintain version control and auditability.
                </p>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="acknowledge-drift"
                  checked={acknowledged}
                  onCheckedChange={(checked) => setAcknowledged(checked === true)}
                />
                <label
                  htmlFor="acknowledge-drift"
                  className="text-sm font-medium leading-none cursor-pointer"
                >
                  I understand this will create drift
                </label>
              </div>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={() => setAcknowledged(false)}>
            Cancel
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={!acknowledged}
            className="bg-amber-600 hover:bg-amber-700"
          >
            Edit Anyway
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
