/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { WhitelistItem } from './types';

// Allowlist de Software, Modelos IA y Tecnologías públicas (NO deben anonimizarse como Organización)
export const SOFTWARE_ALLOWLIST = new Set([
  'chatgpt', 'copilot', 'gemini', 'claude', 'llama', 'gpt', 'gpt-4', 'gpt-3.5',
  'windows', 'office', 'excel', 'word', 'powerpoint', 'google', 'microsoft',
  'python', 'docker', 'react', 'vite', 'node', 'express', 'spacy', 'presidio',
  'easyocr', 'pdf', 'csv', 'txt', 'docx', 'xlsx', 'json', 'html', 'css', 'javascript',
  'typescript', 'flet', 'github', 'gitlab', 'slack', 'teams', 'zoom'
]);

// Expresiones Regulares para datos PII en Español y Seguridad
const EMAIL_REGEX = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/gi;
const CREDIT_CARD_REGEX = /\b(?:\d[ -]?){13,16}\b/g;
const PHONE_REGEX = /(?:\+?\d{1,4}[-\s]?)?\(?\d{2,4}\)?[-\s]?\d{3,4}[-\s]?\d{3,4}/g;
const DNI_RUT_REGEX = /\b\d{7,10}[-\s]?[A-Za-z0-9]?\b/g;

// Nuevas expresiones solicitadas:
// 1. Dominios Web (ej. empresa.com, www.cliente.es, https://portal.corp.org)
const DOMAIN_REGEX = /\b(?:https?:\/\/)?(?:www\.)?([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.(?:com|es|org|net|co|io|gov|edu|biz|info|tech|app))\b/gi;

// 2. Contraseñas, API Keys, Tokens y Passwords
const SECRET_KEY_REGEX = /\b(?:sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|bearer\s+[a-zA-Z0-9._\-]+|(?:password|clave|contraseña|pwd|api_key|secret|token)\s*[:=]\s*['"]?([^\s'"]{4,})['"]?)\b/gi;

// 3. Usernames / Menciones / Asideros de usuario
const USERNAME_REGEX = /(?:@([a-zA-Z0-9._-]+)|\b(?:user|usuario|username|interlocutor|hablante)\s*[:=]\s*['"]?([a-zA-Z0-9._-]+)['"]?)/gi;

// Palabras clave contextuales que indican nombres en Español
const SPANISH_NAMES = [
  "Carlos Mendoza", "Santiago", "Alejandro Gómez", "Juan Pérez", "María Rodríguez", 
  "Laura Martínez", "Andrés Felipe", "Sofía Castro", "Santiago Valencia", "Gabriela",
  "Diego Armando", "Carlos", "Juan", "Gómez", "Mendoza", "Alejandro", "Sonia", "Beatriz",
  "Laura", "Noelia", "Pedro", "Ana", "Lucía", "Javier", "Martín", "Elena", "Carmen"
];

const SPANISH_LOCATIONS = [
  "Bogotá", "Madrid", "Medellín", "Barcelona", "Santiago", "Buenos Aires", 
  "Lima", "Ciudad de México", "Sevilla", "Valencia", "Colombia", "España"
];

const SPANISH_ORGS = [
  "Banco Santander", "InnovaTech", "Telefónica", "BBVA", "Mercadona", 
  "Lia Corp", "Empresa Textil S.A."
];

// Detección de Vocativos y Etiquetas de Diálogo en transcripciones de entrevistas
// Ej: "gracias, Laura", "mira, Noelia", "hola Juan", "estimada Sofía", "Entrevistador (Carlos):"
const VOCATIVE_COURTESY_REGEX = /(?:,\s*|\b(?:gracias|mira|oye|hola|estimado|estimada|buenos días|buenas tardes|saludos|escucha|dime)\s+)([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,})?)/g;
const SPEAKER_TAG_REGEX = /^(?:Interlocutor\s*\d*|Entrevistador\s*\d*|Hablante\s*\d*|Speaker\s*\d*|\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}\b)\s*\(([^)]+)\)\s*:/gm;

export function detectAndRedact(
  text: string, 
  customWords: WhitelistItem[]
): { redactedText: string; piiFound: { text: string; category: string; index: number }[]; keyMap: Record<string, string> } {
  const piiFound: { text: string; category: string; index: number }[] = [];
  const keyMap: Record<string, string> = {};
  
  if (!text || !text.trim()) {
    return { redactedText: text, piiFound, keyMap };
  }

  let textToProcess = text;

  // Helper para verificar si un término pertenece a la allowlist de software
  const isSoftwareOrPublicTerm = (val: string) => {
    return SOFTWARE_ALLOWLIST.has(val.trim().toLowerCase());
  };

  // 1. Aplicar Diccionario de Exclusiones de la Empresa (Whitelist/Blacklist personalizada)
  customWords.forEach((item, idx) => {
    const escapedWord = item.word.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
    const regex = new RegExp(`\\b${escapedWord}\\b`, 'gi');
    
    const matches = textToProcess.match(regex);
    if (matches) {
      matches.forEach((match) => {
        const token = `[TERMINO_CONFIDENCIAL_${idx + 1}]`;
        keyMap[token] = match;
        piiFound.push({
          text: match,
          category: `Diccionario (${item.category})`,
          index: textToProcess.indexOf(match)
        });
      });
      textToProcess = textToProcess.replace(regex, `[TERMINO_CONFIDENCIAL_${idx + 1}]`);
    }
  });

  // Helper para registrar y reemplazar coincidencias con sintaxis uniforme [ETIQUETA_N]
  const processMatch = (regex: RegExp, category: string, label: string, filterFn?: (val: string) => boolean) => {
    let match;
    let matchCounter = 1;
    regex.lastIndex = 0;
    
    let iterations = 0;
    while ((match = regex.exec(textToProcess)) !== null && iterations < 100) {
      iterations++;
      const fullMatch = match[0];
      const targetMatch = match[1] || fullMatch;
      
      // Evitar procesar si ya está redactado o si es software permitido
      if (targetMatch.startsWith('[') && targetMatch.endsWith(']')) continue;
      if (filterFn && !filterFn(targetMatch)) continue;

      const token = `[${label}_${matchCounter}]`;
      keyMap[token] = targetMatch;
      
      piiFound.push({
        text: targetMatch,
        category,
        index: match.index
      });

      const matchIdx = textToProcess.indexOf(targetMatch, match.index);
      if (matchIdx !== -1) {
        textToProcess = textToProcess.slice(0, matchIdx) + token + textToProcess.slice(matchIdx + targetMatch.length);
      }
      
      regex.lastIndex = 0;
      matchCounter++;
    }
  };

  // 2. Emails
  processMatch(EMAIL_REGEX, 'Correo Electrónico', 'CORREO');

  // 3. Dominios Web (Políticas: Categoría 4b)
  processMatch(DOMAIN_REGEX, 'Dominio Web', 'DOMINIO', (val) => !isSoftwareOrPublicTerm(val));

  // 4. Secretos / Passwords / API Keys (Punto 4c feedback usuario)
  processMatch(SECRET_KEY_REGEX, 'Clave / Contraseña / Token', 'CLAVE');

  // 5. Usernames / Menciones
  processMatch(USERNAME_REGEX, 'Nombre de Usuario', 'USUARIO');

  // 6. Tarjetas de Crédito
  processMatch(CREDIT_CARD_REGEX, 'Tarjeta de Crédito', 'TARJETA_CREDITO');

  // 7. Teléfonos
  processMatch(PHONE_REGEX, 'Teléfono', 'TELEFONO');

  // 8. Identificación Oficial (DNI, RUT, Cédula)
  processMatch(DNI_RUT_REGEX, 'ID Oficial / DNI', 'ID_OFICIAL');

  // 9. Vocativos y Hablantes en Diálogos (Bug 2 - NER Entrevistas)
  processMatch(VOCATIVE_COURTESY_REGEX, 'Persona (Vocativo)', 'PERSONA', (val) => !isSoftwareOrPublicTerm(val));
  processMatch(SPEAKER_TAG_REGEX, 'Persona (Interlocutor)', 'PERSONA', (val) => !isSoftwareOrPublicTerm(val));

  // 10. Nombres Propios de Personas (NLU contextual para Español)
  SPANISH_NAMES.forEach((name) => {
    if (isSoftwareOrPublicTerm(name)) return;
    const regex = new RegExp(`\\b${name}\\b`, 'gi');
    let matchCounter = 1;
    let match;
    while ((match = regex.exec(textToProcess)) !== null) {
      const fullMatch = match[0];
      if (fullMatch.startsWith('[') && fullMatch.endsWith(']')) continue;
      
      const token = `[PERSONA_${matchCounter}]`;
      keyMap[token] = fullMatch;
      piiFound.push({
        text: fullMatch,
        category: 'Persona',
        index: match.index
      });
      textToProcess = textToProcess.slice(0, match.index) + token + textToProcess.slice(match.index + fullMatch.length);
      regex.lastIndex = 0;
      matchCounter++;
    }
  });

  // 11. Ubicaciones
  SPANISH_LOCATIONS.forEach((loc) => {
    const regex = new RegExp(`\\b${loc}\\b`, 'gi');
    let matchCounter = 1;
    let match;
    while ((match = regex.exec(textToProcess)) !== null) {
      const fullMatch = match[0];
      if (fullMatch.startsWith('[') && fullMatch.endsWith(']')) continue;
      
      const token = `[UBICACION_${matchCounter}]`;
      keyMap[token] = fullMatch;
      piiFound.push({
        text: fullMatch,
        category: 'Ubicación',
        index: match.index
      });
      textToProcess = textToProcess.slice(0, match.index) + token + textToProcess.slice(match.index + fullMatch.length);
      regex.lastIndex = 0;
      matchCounter++;
    }
  });

  // 12. Organizaciones (Filtrando software/modelos comerciales como ChatGPT, Copilot)
  SPANISH_ORGS.forEach((org) => {
    if (isSoftwareOrPublicTerm(org)) return; // Bug 4a: No tratar software como organización
    const regex = new RegExp(`\\b${org}\\b`, 'gi');
    let matchCounter = 1;
    let match;
    while ((match = regex.exec(textToProcess)) !== null) {
      const fullMatch = match[0];
      if (fullMatch.startsWith('[') && fullMatch.endsWith(']')) continue;
      
      const token = `[ORGANIZACION_${matchCounter}]`;
      keyMap[token] = fullMatch;
      piiFound.push({
        text: fullMatch,
        category: 'Organización',
        index: match.index
      });
      textToProcess = textToProcess.slice(0, match.index) + token + textToProcess.slice(match.index + fullMatch.length);
      regex.lastIndex = 0;
      matchCounter++;
    }
  });

  return { redactedText: textToProcess, piiFound, keyMap };
}

/**
 * Bug 1: Sanitizador de Nombre de Archivo / Título
 * Si el nombre del archivo contiene información sensible (nombres, empresas, DNI, etc.),
 * sanitiza el título del archivo manteniendo su extensión original.
 */
export function sanitizeFilename(
  filename: string, 
  customWords: WhitelistItem[]
): { sanitizedName: string; filenameKeyMap: Record<string, string> } {
  const lastDotIndex = filename.lastIndexOf('.');
  const baseName = lastDotIndex !== -1 ? filename.substring(0, lastDotIndex) : filename;
  const ext = lastDotIndex !== -1 ? filename.substring(lastDotIndex) : '';

  // Reemplazar provisionalmente _ y - por espacios para la detección
  const baseNameWithSpaces = baseName.replace(/[_]/g, ' ');
  const { redactedText, keyMap } = detectAndRedact(baseNameWithSpaces, customWords);
  
  // Re-ensamblar el nombre del archivo sanitizado
  const sanitizedBase = redactedText.replace(/\s+/g, '_');
  return {
    sanitizedName: `${sanitizedBase}${ext}`,
    filenameKeyMap: keyMap
  };
}

export function restoreAnonymization(
  redactedText: string,
  keyMap: Record<string, string>
): string {
  if (!redactedText || !keyMap) return redactedText;
  let restored = redactedText;
  
  // Reemplazar de forma reversible todas las claves del diccionario
  Object.entries(keyMap).forEach(([token, originalValue]) => {
    restored = restored.replaceAll(token, originalValue);
  });
  
  return restored;
}
