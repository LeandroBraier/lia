/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export interface AuditLog {
  id: string;
  timestamp: string;
  fileName: string;
  fileSize: string;
  fileType: string;
  piiCount: number;
  entitiesDetected: string[];
}

export interface WhitelistItem {
  id: string;
  word: string;
  category: string;
}

export interface ProcessedFile {
  id: string;
  name: string;
  originalSize: number;
  type: string;
  status: 'pending' | 'processing' | 'done' | 'error';
  originalContent: string;
  redactedContent: string;
  piiFound: { text: string; category: string; index: number }[];
  keyMap: Record<string, string>; // Maps redacted tokens to original text for reverse translation
}

export interface LicenceState {
  isValid: boolean;
  message: string;
  daysRemaining: number;
  clientName: string;
  expirationDate: string;
}
