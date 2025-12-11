/**
 * CSV Export Utilities
 * Provides functions for exporting data to CSV format with proper escaping and download
 */

type ExportableValue = string | number | boolean | null | undefined | Date;

interface ExportColumn<T> {
  key: keyof T | ((item: T) => ExportableValue);
  header: string;
  formatter?: (value: ExportableValue) => string;
}

/**
 * Escape a value for CSV format
 */
function escapeCSVValue(value: ExportableValue): string {
  if (value === null || value === undefined) {
    return '';
  }

  if (value instanceof Date) {
    return value.toISOString();
  }

  const stringValue = String(value);

  // If the value contains commas, quotes, or newlines, wrap in quotes and escape existing quotes
  if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
    return `"${stringValue.replace(/"/g, '""')}"`;
  }

  return stringValue;
}

/**
 * Convert an array of objects to CSV string
 */
export function toCSV<T extends Record<string, unknown>>(
  data: T[],
  columns: ExportColumn<T>[]
): string {
  // Create header row
  const headers = columns.map(col => escapeCSVValue(col.header)).join(',');

  // Create data rows
  const rows = data.map(item => {
    return columns.map(col => {
      let value: ExportableValue;

      if (typeof col.key === 'function') {
        value = col.key(item);
      } else {
        value = item[col.key] as ExportableValue;
      }

      if (col.formatter) {
        value = col.formatter(value);
      }

      return escapeCSVValue(value);
    }).join(',');
  });

  return [headers, ...rows].join('\n');
}

/**
 * Trigger a file download in the browser
 */
export function downloadFile(content: string, filename: string, mimeType: string = 'text/csv'): void {
  const blob = new Blob([content], { type: `${mimeType};charset=utf-8;` });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  // Clean up the URL object
  URL.revokeObjectURL(url);
}

/**
 * Export data to CSV and trigger download
 */
export function exportToCSV<T extends Record<string, unknown>>(
  data: T[],
  columns: ExportColumn<T>[],
  filename: string
): void {
  const csv = toCSV(data, columns);
  const timestamp = new Date().toISOString().slice(0, 10);
  const fullFilename = `${filename}_${timestamp}.csv`;
  downloadFile(csv, fullFilename);
}

/**
 * Format date for export
 */
export function formatDateForExport(date: string | Date | null | undefined): string {
  if (!date) return '';
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toISOString();
}

/**
 * Format currency for export
 */
export function formatCurrencyForExport(amount: number | null | undefined, currency: string = 'USD'): string {
  if (amount === null || amount === undefined) return '';
  return `${currency} ${(amount / 100).toFixed(2)}`;
}

/**
 * Format boolean for export
 */
export function formatBooleanForExport(value: boolean | null | undefined): string {
  if (value === null || value === undefined) return '';
  return value ? 'Yes' : 'No';
}

/**
 * Format percentage for export
 */
export function formatPercentageForExport(value: number | null | undefined): string {
  if (value === null || value === undefined) return '';
  return `${value.toFixed(1)}%`;
}

// Pre-defined column configurations for common exports

export const tenantExportColumns = [
  { key: 'id' as const, header: 'Tenant ID' },
  { key: 'name' as const, header: 'Tenant Name' },
  { key: 'owner_email' as const, header: 'Owner Email' },
  { key: 'plan' as const, header: 'Plan' },
  { key: 'status' as const, header: 'Status' },
  { key: 'workflow_count' as const, header: 'Workflows' },
  { key: 'environment_count' as const, header: 'Environments' },
  { key: 'user_count' as const, header: 'Users' },
  { key: 'created_at' as const, header: 'Created At', formatter: formatDateForExport },
];

export const auditLogExportColumns = [
  { key: 'id' as const, header: 'Log ID' },
  { key: 'timestamp' as const, header: 'Timestamp', formatter: formatDateForExport },
  { key: 'actor_email' as const, header: 'Actor Email' },
  { key: 'actor_name' as const, header: 'Actor Name' },
  { key: 'tenant_name' as const, header: 'Tenant' },
  { key: 'action_type' as const, header: 'Action Type' },
  { key: 'resource_type' as const, header: 'Resource Type' },
  { key: 'resource_name' as const, header: 'Resource Name' },
  { key: 'reason' as const, header: 'Reason' },
  { key: 'ip_address' as const, header: 'IP Address' },
];

export const transactionExportColumns = [
  { key: 'id' as const, header: 'Transaction ID' },
  { key: 'tenant' as const, header: 'Tenant' },
  { key: 'type' as const, header: 'Type' },
  { key: 'amount' as const, header: 'Amount' },
  { key: 'status' as const, header: 'Status' },
  { key: 'date' as const, header: 'Date', formatter: formatDateForExport },
];

export const usageExportColumns = [
  { key: 'tenant_name' as const, header: 'Tenant' },
  { key: 'plan' as const, header: 'Plan' },
  { key: 'metric' as const, header: 'Metric' },
  { key: 'current_value' as const, header: 'Current Value' },
  { key: 'limit' as const, header: 'Limit' },
  { key: 'percentage' as const, header: 'Usage %', formatter: formatPercentageForExport },
  { key: 'status' as const, header: 'Status' },
];
