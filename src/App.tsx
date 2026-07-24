/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef, FormEvent, ChangeEvent } from 'react';
import { 
  Shield, 
  Lock, 
  RefreshCw, 
  FileText, 
  Book, 
  Terminal, 
  CheckCircle2, 
  AlertTriangle, 
  Download, 
  Upload, 
  Copy, 
  Plus, 
  Trash2, 
  Activity, 
  FileSpreadsheet, 
  FileImage, 
  X, 
  Key, 
  Layers, 
  ArrowLeftRight, 
  Info,
  Check,
  Eye,
  AlertOctagon,
  Play
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { WhitelistItem, ProcessedFile, AuditLog } from './types';
import { detectAndRedact, restoreAnonymization, sanitizeFilename } from './anonymizer';
import { CODE_SNIPPETS } from './codeSnippets';

// Archivos de muestra para demostración inmediata
const SAMPLE_FILES: Omit<ProcessedFile, 'id'>[] = [
  {
    name: "reunion_ejecutiva.txt",
    originalSize: 284,
    type: "text/plain",
    status: 'pending',
    originalContent: "Ayer en la oficina de Bogotá, Carlos Mendoza se reunió con la directiva de InnovaTech para ultimar la adquisición. Estuvieron presentes Santiago y Alejandro Gómez. Para el cobro de la licencia se usará la tarjeta 4532 8812 3456 1122 de Banco Santander y el correo carlos.mendoza@empresa.com.",
    redactedContent: "",
    piiFound: [],
    keyMap: {}
  },
  {
    name: "ventas_clientes.csv",
    originalSize: 450,
    type: "text/csv",
    status: 'pending',
    originalContent: "ID,Nombre,Email,Telefono,DNI\n1,Juan Pérez,juan.perez@email.com,+34 611223344,49830294C\n2,María Rodríguez,maria.r@gmail.com,+34 622334455,12345678A\n3,Santiago Valencia,santiago.v@hotmail.com,+57 312345678,98765432B",
    redactedContent: "",
    piiFound: [],
    keyMap: {}
  },
  {
    name: "contrato_oficina.docx",
    originalSize: 10400,
    type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    status: 'pending',
    originalContent: "CONTRATO DE SERVICIOS PROFESIONALES\n\nEste contrato de servicios vincula a la profesional Sonia Gómez con domicilio en Madrid y a la corporación Lia Corp. El proyecto secreto asignado será el Proyecto Halcon bajo la dirección de Alejandro. Se acuerda un pago inicial de garantía bancaria.",
    redactedContent: "",
    piiFound: [],
    keyMap: {}
  },
  {
    name: "escaneo_identificacion.png",
    originalSize: 84200,
    type: "image/png",
    status: 'pending',
    originalContent: "REPUBLICA DE ESPAÑA\nDOCUMENTO NACIONAL DE IDENTIDAD\nNOMBRE: ALEJANDRO GÓMEZ\nID: 49830294C\nNACIMIENTO: 18/07/1992\nDIRECCION: MADRID, ESPAÑA\nEMAIL: alejandro.gomez@corporation.es\nCARD: 5412 7512 3456 7890",
    redactedContent: "",
    piiFound: [],
    keyMap: {}
  }
];

export default function App() {
  // --- ESTADOS DE LA APLICACIÓN ---
  const [activeTab, setActiveTab] = useState<'sanitizer' | 'reverse' | 'whitelist' | 'license' | 'code'>('sanitizer');
  const [licenseState, setLicenseState] = useState<'activa' | 'expirada' | 'reloj' | 'corrupta'>('activa');
  
  // Lista de archivos cargados / en proceso
  const [files, setFiles] = useState<ProcessedFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<ProcessedFile | null>(null);

  // Estados de Preloaders & Drag and Drop
  const [isProcessing, setIsProcessing] = useState(false);
  const [isReversing, setIsReversing] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  
  // Whitelist/Diccionario Corporativo
  const [whitelist, setWhitelist] = useState<WhitelistItem[]>([
    { id: "1", word: "Proyecto Halcon", category: "Proyecto Secreto" },
    { id: "2", word: "Lia Corp", category: "Cliente VIP" },
    { id: "3", word: "Adquisición Alfa", category: "Fusión y Adquisición" }
  ]);
  const [newWord, setNewWord] = useState('');
  const [newCategory, setNewCategory] = useState('Proyecto Secreto');

  // Logs de Auditoría
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([
    {
      id: "log_1",
      timestamp: new Date(Date.now() - 3600000 * 2).toLocaleTimeString(),
      fileName: "reporte_mensual_demo.csv",
      fileSize: "1.2 KB",
      fileType: "text/csv",
      piiCount: 8,
      entitiesDetected: ["Correo", "ID Oficial", "Teléfono"]
    },
    {
      id: "log_2",
      timestamp: new Date(Date.now() - 3600000 * 5).toLocaleTimeString(),
      fileName: "contrato_servicios_demo.docx",
      fileSize: "12 KB",
      fileType: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      piiCount: 4,
      entitiesDetected: ["Persona", "Ubicación"]
    }
  ]);

  // Traducción Inversa
  const [reverseText, setReverseText] = useState('');
  const [reverseKeyInput, setReverseKeyInput] = useState('');
  const [reverseOutput, setReverseOutput] = useState('');
  const [isReverseDone, setIsReverseDone] = useState(false);
  const [reverseFileName, setReverseFileName] = useState('documento_restaurado.docx');
  const [reverseFileExt, setReverseFileExt] = useState('docx');

  // Snippet activo en la pestaña de código
  const [activeSnippetTab, setActiveSnippetTab] = useState<'app_offline' | 'app_grafica' | 'validador' | 'dockerfile' | 'requirements'>('app_grafica');
  const [isCopied, setIsCopied] = useState(false);

  // OCR Visual Interactivo (Estado para la simulación de imagen)
  const [blacklistedAreas, setBlacklistedAreas] = useState<Record<string, boolean>>({
    name: true,
    id: true,
    email: true,
    card: false
  });

  // Alerta de reloj / manipulación temporal (Simulador)
  const [customLicenseDate, setCustomLicenseDate] = useState('2027-07-19');
  const [customClientName, setCustomClientName] = useState('ORGANIZACION_TEXTIL_SL');

  // Cargar archivos de muestra por defecto en el primer render
  useEffect(() => {
    const initialized = SAMPLE_FILES.map((f, idx) => ({
      ...f,
      id: `sample_${idx + 1}`
    }));
    setFiles(initialized);
  }, []);

  // --- ACCIONES Y PROCESAMIENTO ---

  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  const addWhitelistWord = (e: FormEvent) => {
    e.preventDefault();
    if (!newWord.trim()) return;
    const item: WhitelistItem = {
      id: Date.now().toString(),
      word: newWord.trim(),
      category: newCategory
    };
    setWhitelist([...whitelist, item]);
    setNewWord('');
  };

  const removeWhitelistWord = (id: string) => {
    setWhitelist(whitelist.filter(w => w.id !== id));
  };

  // Handlers para Drag & Drop (Nice to Have 1)
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const fileList = Array.from(e.dataTransfer.files) as File[];
      processUploadedFiles(fileList);
    }
  };

  const processUploadedFiles = (fileList: File[]) => {
    fileList.forEach(file => {
      const reader = new FileReader();
      reader.onload = (event) => {
        const content = event.target?.result as string || "Contenido no legible o binario simulado";
        const newFile: ProcessedFile = {
          id: `upload_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
          name: file.name,
          originalSize: file.size,
          type: file.type || "text/plain",
          status: 'pending',
          originalContent: content,
          redactedContent: '',
          piiFound: [],
          keyMap: {}
        };
        setFiles(prev => [newFile, ...prev]);
      };
      reader.readAsText(file);
    });
  };

  // Sanitizar un archivo localmente usando el motor de anonymizer.ts y sanitizando el título (Bug 1)
  const processFileLocal = (fileId: string) => {
    setIsProcessing(true);
    setTimeout(() => {
      setFiles(prev => prev.map(f => {
        if (f.id === fileId) {
          const { redactedText, piiFound, keyMap } = detectAndRedact(f.originalContent, whitelist);
          const { sanitizedName, filenameKeyMap } = sanitizeFilename(f.name, whitelist);
          const mergedKeyMap = { ...filenameKeyMap, ...keyMap };
          
          // Registrar log de auditoría
          const categories = Array.from(new Set(piiFound.map(p => p.category)));
          const newLog: AuditLog = {
            id: `log_${Date.now()}`,
            timestamp: new Date().toLocaleTimeString(),
            fileName: sanitizedName,
            fileSize: `${(f.originalSize / 1024).toFixed(1)} KB`,
            fileType: f.type,
            piiCount: piiFound.length,
            entitiesDetected: categories
          };
          setAuditLogs(prevLogs => [newLog, ...prevLogs]);

          return {
            ...f,
            name: sanitizedName,
            status: 'done',
            redactedContent: redactedText,
            piiFound,
            keyMap: mergedKeyMap
          };
        }
        return f;
      }));
      setIsProcessing(false);
    }, 450);
  };

  const processAllFiles = () => {
    setIsProcessing(true);
    setTimeout(() => {
      files.forEach(f => {
        if (f.status === 'pending') {
          processFileLocal(f.id);
        }
      });
      setIsProcessing(false);
    }, 600);
  };

  const handleFileUpload = (e: ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const fileList = Array.from(e.target.files) as File[];
    processUploadedFiles(fileList);
  };

  // Simulación de OCR para imagen interactiva
  const handleToggleRedactArea = (area: string) => {
    setBlacklistedAreas(prev => ({
      ...prev,
      [area]: !prev[area]
    }));
  };

  // Reversión interactiva con Preloader (Bug 5) y Formato Preservado (Bug 6)
  const handleReverseFileUpload = (e: ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    const ext = file.name.substring(file.name.lastIndexOf('.') + 1) || 'docx';
    setReverseFileName(`restaurado_${file.name}`);
    setReverseFileExt(ext.toLowerCase());

    const reader = new FileReader();
    reader.onload = (evt) => {
      const text = evt.target?.result as string || '';
      if (file.name.endsWith('.key') || file.name.endsWith('.json')) {
        setReverseKeyInput(text);
      } else {
        setReverseText(text);
      }
    };
    reader.readAsText(file);
  };

  const handleReverseKeyFileUpload = (e: ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    const reader = new FileReader();
    reader.onload = (evt) => {
      const text = evt.target?.result as string || '';
      setReverseKeyInput(text);
    };
    reader.readAsText(file);
  };

  const runReverseTranslation = () => {
    if (!reverseText) return;
    setIsReversing(true);
    setTimeout(() => {
      try {
        const parsedKey = JSON.parse(reverseKeyInput || '{}');
        const restored = restoreAnonymization(reverseText, parsedKey);
        setReverseOutput(restored);
        setIsReverseDone(true);
      } catch (e) {
        alert("Error: El mapa .key ingresado no es un JSON válido.");
      } finally {
        setIsReversing(false);
      }
    }, 500);
  };

  // Generar licencia offline (.key)
  const downloadLicenseKeyFile = () => {
    const formattedDate = customLicenseDate;
    const formattedClient = customClientName;
    const integrityToken = btoa(`${formattedDate}|${formattedClient}|LIA_VAULT_SECURITY_SALT`);
    const fileContent = `${integrityToken}\n${formattedDate}|${formattedClient}`;
    
    const blob = new Blob([fileContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'licencia.key';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Restaurar licencia a estado activa
  const handleRestoreLicense = () => {
    setLicenseState('activa');
  };

  return (
    <div 
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className="min-h-screen bg-zinc-50 font-sans text-zinc-900 selection:bg-amber-500 selection:text-white relative overflow-hidden"
    >
      
      {/* --- PANTALLA DE BLOQUEO CORPORATIVO (OFFLINE LICENSE LOCK) --- */}
      <AnimatePresence>
        {licenseState !== 'activa' && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-zinc-950/90 backdrop-blur-md flex items-center justify-center p-4"
          >
            <motion.div 
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              className="bg-white border-2 border-red-500/50 rounded-2xl max-w-lg w-full p-8 shadow-2xl text-center relative"
            >
              <div className="absolute top-4 right-4 text-xs font-mono px-3 py-1 bg-red-50 text-red-700 border border-red-200 rounded-full">
                Vault Lockout Activo
              </div>
              <div className="flex justify-center mb-6">
                <div className="p-4 bg-red-50 rounded-full border border-red-100">
                  <AlertOctagon className="h-16 w-16 text-red-600" />
                </div>
              </div>
              <h1 className="text-2xl font-black tracking-tight text-zinc-900 mb-2 font-sans">
                LIA VAULT - ACCESO BLOQUEADO
              </h1>
              <p className="text-sm text-zinc-500 mb-6 font-sans">
                Procesamiento local temporalmente deshabilitado por el motor de validación de licencias corporativo.
              </p>

              <div className="bg-zinc-950 rounded-xl p-4 mb-6 border border-zinc-800 text-left font-mono text-xs text-zinc-300">
                <div className="flex items-center gap-2 text-red-400 mb-2 font-semibold">
                  <AlertTriangle className="h-4 w-4" />
                  <span>Código de Diagnóstico de Seguridad</span>
                </div>
                {licenseState === 'expirada' && (
                  <p className="text-zinc-300">
                    ERR_LICENSE_EXPIRED: El periodo de prueba (Trial de 1 año) ha expirado en la fecha registrada 2027-07-19. Se requiere renovación anual de 199€.
                  </p>
                )}
                {licenseState === 'reloj' && (
                  <p className="text-zinc-300">
                    ERR_SYSTEM_CLOCK_TAMPER: Se detectó manipulación del reloj del sistema. La hora de ejecución es anterior al último registro en el archivo de logs oculto (.vault_log.db).
                  </p>
                )}
                {licenseState === 'corrupta' && (
                  <p className="text-zinc-300">
                    ERR_LICENSE_CORRUPTED: La firma de integridad digital en licencia.key no coincide con el SALT de seguridad local. El archivo de llave fue modificado o alterado.
                  </p>
                )}
              </div>

              <div className="space-y-3 mb-6">
                <p className="text-xs text-zinc-500">
                  Para restaurar el funcionamiento, genere o cargue un archivo <code className="text-amber-600 font-bold">licencia.key</code> válido utilizando el simulador inferior, o reestablezca el estado.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <button 
                  onClick={handleRestoreLicense}
                  className="px-5 py-2.5 bg-zinc-100 hover:bg-zinc-200 text-zinc-700 text-sm font-semibold rounded-lg transition border border-zinc-200"
                >
                  Omitir / Reactivar Licencia
                </button>
                <button 
                  onClick={() => {
                    handleRestoreLicense();
                    setActiveTab('license');
                  }}
                  className="px-5 py-2.5 bg-[#f99c00] hover:bg-[#e08b00] text-white text-sm font-semibold rounded-lg transition shadow-md shadow-amber-500/10"
                >
                  Ir al Portal de Licencias
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* --- HEADER PRINCIPAL --- */}
      <header className="border-b border-zinc-200 bg-white/80 backdrop-blur-md sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-amber-500 to-[#f99c00] flex items-center justify-center shadow-lg shadow-amber-500/20">
              <Shield className="h-5.5 w-5.5 text-white" />
            </div>
            <div>
              <span className="text-[9px] font-extrabold text-amber-600 tracking-[0.25em] uppercase block mb-0.5">
                UNA APLICACIÓN DESARROLLADA POR KOR.®
              </span>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-black tracking-tight text-zinc-900 leading-none">LIA VAULT</h1>
                <span className="text-[10px] uppercase tracking-widest font-mono bg-amber-50 text-amber-700 px-2 py-0.5 border border-amber-200 rounded-full font-bold">
                  On-Premise
                </span>
              </div>
              <p className="text-[11px] text-zinc-500 font-sans mt-0.5">100% Offline PII Anonymization Suite</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden md:flex items-center gap-2 bg-zinc-100 border border-zinc-200 px-3.5 py-1.5 rounded-full text-xs font-mono">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-ping"></span>
              <span className="text-zinc-600">Servidor Local: </span>
              <span className="text-amber-600 font-bold">127.0.0.1:8502 (LAN)</span>
            </div>

            <div className="flex items-center gap-2 bg-zinc-100 border border-zinc-200 px-3 py-1.5 rounded-lg text-xs font-mono">
              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              <span className="text-zinc-600 hidden sm:inline">Licencia: </span>
              <span className="text-emerald-600 font-bold">Trial Activo (365d)</span>
            </div>
          </div>
        </div>
      </header>

      {/* --- CUERPO PRINCIPAL --- */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* COLUMNA IZQUIERDA - MENU DE NAVEGACION */}
          <div className="lg:col-span-3 space-y-6">
            <div className="bg-white border border-zinc-200 rounded-2xl p-4 space-y-1.5 shadow-sm">
              <p className="text-[11px] uppercase tracking-widest text-zinc-400 font-bold px-3 mb-2">Funciones Locales</p>
              
              <button 
                onClick={() => setActiveTab('sanitizer')}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold transition ${activeTab === 'sanitizer' ? 'bg-[#f99c00] text-white font-bold shadow-sm' : 'text-zinc-600 hover:bg-zinc-100'}`}
              >
                <Shield className="h-4.5 w-4.5" />
                <span>Sanitizador de Archivos</span>
              </button>

              <button 
                onClick={() => setActiveTab('reverse')}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold transition ${activeTab === 'reverse' ? 'bg-[#f99c00] text-white font-bold shadow-sm' : 'text-zinc-600 hover:bg-zinc-100'}`}
              >
                <ArrowLeftRight className="h-4.5 w-4.5" />
                <span>Traducción Inversa</span>
              </button>

              <button 
                onClick={() => setActiveTab('whitelist')}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold transition ${activeTab === 'whitelist' ? 'bg-[#f99c00] text-white font-bold shadow-sm' : 'text-zinc-600 hover:bg-zinc-100'}`}
              >
                <Book className="h-4.5 w-4.5" />
                <span>Diccionario Empresa</span>
              </button>

              <p className="text-[11px] uppercase tracking-widest text-zinc-400 font-bold px-3 mt-4 mb-2">Despliegue & Admin</p>

              <button 
                onClick={() => setActiveTab('license')}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold transition ${activeTab === 'license' ? 'bg-[#f99c00] text-white font-bold shadow-sm' : 'text-zinc-600 hover:bg-zinc-100'}`}
              >
                <Key className="h-4.5 w-4.5" />
                <span>Licencias y Simulación</span>
              </button>

              <button 
                onClick={() => setActiveTab('code')}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold transition ${activeTab === 'code' ? 'bg-[#f99c00] text-white font-bold shadow-sm' : 'text-zinc-600 hover:bg-zinc-100'}`}
              >
                <Terminal className="h-4.5 w-4.5" />
                <span>Código On-Premise (Python)</span>
              </button>
            </div>

            {/* WIDGET DE ADVERTENCIA DE PRIVACIDAD */}
            <div className="bg-white border border-zinc-200 rounded-2xl p-5 space-y-4 shadow-sm">
              <div className="flex items-center gap-2 text-emerald-600">
                <Lock className="h-4.5 w-4.5" />
                <h3 className="text-xs font-bold uppercase tracking-wider">Compromiso Offline</h3>
              </div>
              <p className="text-xs text-zinc-600 leading-relaxed font-sans">
                Lia Vault opera de forma <strong>100% aislada</strong> en su navegador. Ningún documento o cadena de texto es transmitida a internet. Todo el procesamiento OCR e IA se calcula utilizando el motor WebAssembly y regex de Lia Corp.
              </p>
              <div className="text-[10px] text-zinc-500 font-mono flex items-center gap-1.5">
                <Check className="h-3 w-3 text-emerald-600" />
                <span>Sin trackers, sin cookies en la nube.</span>
              </div>
            </div>
          </div>

          {/* COLUMNA DERECHA - CONTENIDO DE LA TAB ACTIVA */}
          <div className="lg:col-span-9 space-y-6">
            
            {/* --- CONTENIDO TAB: SANITIZADOR --- */}
            {activeTab === 'sanitizer' && (
              <div className="space-y-6">
                
                {/* ZONA DE ARRASTRE / ACCIÓN DE CARGA */}
                <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center bg-white border border-zinc-200 p-6 rounded-2xl shadow-sm">
                  <div className="md:col-span-7 space-y-2">
                    <h2 className="text-lg font-bold text-zinc-900 flex items-center gap-2">
                      <Layers className="h-5 w-5 text-amber-500" />
                      Sanitizador de Archivos Corporativos
                    </h2>
                    <p className="text-xs text-zinc-500 font-sans leading-relaxed">
                      Arrastre sus documentos administrativos, tablas de nómina, contratos o transcripciones. El motor offline buscará datos sensibles y generará un clon protegido listo para su uso en Copilot o ChatGPT.
                    </p>
                  </div>
                  
                  <div className="md:col-span-5 flex flex-col gap-3">
                    <label 
                      onDragOver={handleDragOver}
                      onDragLeave={handleDragLeave}
                      onDrop={handleDrop}
                      className={`w-full flex flex-col items-center justify-center border-2 border-dashed p-5 rounded-xl cursor-pointer transition text-center group ${isDragging ? 'border-amber-500 bg-amber-50 scale-[1.02] shadow-md' : 'border-zinc-200 hover:border-amber-500 bg-zinc-50 hover:bg-zinc-100/50'}`}
                    >
                      <Upload className={`h-6 w-6 transition mb-2 ${isDragging ? 'text-amber-600 animate-bounce' : 'text-zinc-400 group-hover:text-amber-500'}`} />
                      <span className="text-xs font-semibold text-zinc-700">
                        {isDragging ? '¡Suelte los archivos aquí!' : 'Seleccionar o arrastrar archivos'}
                      </span>
                      <span className="text-[10px] text-zinc-400 font-mono mt-1">TXT, CSV, DOCX, XLSX, PDF, PNG/JPG</span>
                      <input 
                        type="file" 
                        multiple 
                        onChange={handleFileUpload} 
                        className="hidden" 
                      />
                    </label>
                    <button 
                      onClick={processAllFiles}
                      disabled={isProcessing}
                      className="w-full py-2.5 bg-[#f99c00] hover:bg-[#e08b00] disabled:bg-amber-300 text-white font-bold text-xs uppercase tracking-wider rounded-xl transition flex items-center justify-center gap-2 shadow-md shadow-amber-500/10"
                    >
                      {isProcessing ? (
                        <>
                          <RefreshCw className="h-4 w-4 animate-spin" />
                          <span>Procesando y Sanitizando Archivos...</span>
                        </>
                      ) : (
                        <>
                          <Shield className="h-4 w-4" />
                          <span>Procesar Todo el Lote (IA Local)</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* ARCHIVOS DE COLA Y COMPORTAMIENTO INTERACTIVO */}
                <div className="bg-white border border-zinc-200 rounded-2xl p-6 space-y-4 shadow-sm">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-zinc-800 uppercase tracking-wider flex items-center gap-2">
                      <Activity className="h-4 w-4 text-amber-500" />
                      Cola de Archivos Listos ({files.length})
                    </h3>
                    <button 
                      onClick={() => setFiles([])}
                      className="text-[10px] uppercase font-bold tracking-wider text-red-600 hover:text-red-700 flex items-center gap-1.5 transition"
                    >
                      <Trash2 className="h-3 w-3" />
                      Limpiar todo
                    </button>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
                    {/* Lista de archivos */}
                    <div className="md:col-span-4 space-y-2 max-h-[420px] overflow-y-auto pr-1">
                      {files.map((file) => (
                        <div 
                          key={file.id}
                          onClick={() => setSelectedFile(file)}
                          className={`p-3 rounded-xl border transition cursor-pointer text-left flex items-center justify-between ${selectedFile?.id === file.id ? 'bg-amber-50/40 border-amber-500 ring-1 ring-amber-500' : 'bg-zinc-50 border-zinc-200 hover:bg-zinc-100'}`}
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            {file.type.includes('csv') ? (
                              <FileSpreadsheet className="h-8 w-8 text-emerald-600 shrink-0" />
                            ) : file.type.includes('image') ? (
                              <FileImage className="h-8 w-8 text-amber-500 shrink-0" />
                            ) : (
                              <FileText className="h-8 w-8 text-zinc-500 shrink-0" />
                            )}
                            <div className="min-w-0">
                              <p className="text-xs font-bold text-zinc-800 truncate">{file.name}</p>
                              <p className="text-[10px] text-zinc-500 font-mono">{(file.originalSize / 1024).toFixed(1)} KB</p>
                            </div>
                          </div>

                          <div className="flex flex-col items-end gap-1.5">
                            {file.status === 'done' ? (
                              <span className="text-[9px] uppercase tracking-widest font-mono font-bold px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full">
                                Listo
                              </span>
                            ) : (
                              <span className="text-[9px] uppercase tracking-widest font-mono font-bold px-2 py-0.5 bg-amber-50 text-amber-700 border border-amber-200 rounded-full">
                                Pendiente
                              </span>
                            )}
                            <button 
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedFile(file);
                                if (file.status === 'pending') {
                                  processFileLocal(file.id);
                                }
                              }}
                              className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider bg-amber-500 hover:bg-amber-600 disabled:bg-emerald-600 text-white rounded-md shadow-sm transition flex items-center gap-1"
                              disabled={file.status === 'done' || isProcessing}
                            >
                              <Shield className="h-3 w-3" />
                              <span>{file.status === 'done' ? 'Anonimizado' : 'Anonimizar'}</span>
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Visor de contenido del archivo seleccionado */}
                    <div className="md:col-span-8 bg-zinc-50 border border-zinc-200 rounded-xl p-5 min-h-[300px] flex flex-col justify-between shadow-inner">
                      {selectedFile ? (
                        <div className="space-y-4 h-full flex flex-col justify-between">
                          <div className="flex items-center justify-between border-b border-zinc-200 pb-3">
                            <div>
                              <h4 className="text-sm font-bold text-zinc-900">{selectedFile.name}</h4>
                              <p className="text-[10px] text-zinc-500 font-mono">{selectedFile.type}</p>
                            </div>
                            
                            {selectedFile.status === 'done' && (
                              <div className="flex gap-2">
                                <button 
                                  onClick={() => {
                                    const blob = new Blob([selectedFile.redactedContent], { type: selectedFile.type || 'text/plain' });
                                    const url = URL.createObjectURL(blob);
                                    const link = document.createElement('a');
                                    link.href = url;
                                    link.download = `sanitizado_${selectedFile.name}`;
                                    document.body.appendChild(link);
                                    link.click();
                                    document.body.removeChild(link);
                                  }}
                                  className="px-2.5 py-1.5 bg-white hover:bg-zinc-100 text-amber-600 border border-zinc-200 shadow-sm rounded text-xs flex items-center gap-1.5 transition font-semibold"
                                >
                                  <Download className="h-3 w-3" />
                                  <span>Descargar Sanitizado</span>
                                </button>
                                
                                <button 
                                  onClick={() => {
                                    const blob = new Blob([JSON.stringify(selectedFile.keyMap, null, 2)], { type: 'application/json' });
                                    const url = URL.createObjectURL(blob);
                                    const link = document.createElement('a');
                                    link.href = url;
                                    link.download = `${selectedFile.name}.reverse.key`;
                                    document.body.appendChild(link);
                                    link.click();
                                    document.body.removeChild(link);
                                  }}
                                  className="px-2.5 py-1.5 bg-white hover:bg-zinc-100 text-emerald-600 border border-zinc-200 shadow-sm rounded text-xs flex items-center gap-1.5 transition font-semibold"
                                >
                                  <Key className="h-3 w-3" />
                                  <span>Descargar .key</span>
                                </button>
                              </div>
                            )}
                          </div>

                          {/* Render especial interactivo para Imagen / OCR */}
                          {selectedFile.type.includes('image') ? (
                            <div className="space-y-4">
                              <div className="bg-amber-50/40 border border-amber-200/50 p-3 rounded-lg text-xs text-zinc-600">
                                <span className="text-amber-600 font-bold">Simulación de OCR Visual: </span>
                                Haga clic en los bloques marcados para alternar la censura / blackout antes de exportar el archivo gráfico.
                              </div>

                              <div className="relative bg-white rounded-xl p-6 border border-zinc-200 max-w-sm mx-auto shadow-md font-mono text-xs text-zinc-800 space-y-3">
                                <div className="absolute top-2 right-2 text-[9px] bg-amber-50 text-amber-700 border border-amber-200 px-2.5 py-0.5 rounded-full font-bold">
                                  DNI_ESPAÑA
                                </div>
                                <div className="text-center font-bold text-zinc-400 text-[10px] tracking-widest border-b border-zinc-100 pb-2">
                                  REPUBLICA DE ESPAÑA / MINISTERIO DE INTERIOR
                                </div>

                                <div className="space-y-2">
                                  <div className="flex items-center justify-between">
                                    <span>NOMBRE:</span>
                                    <span 
                                      onClick={() => handleToggleRedactArea('name')}
                                      className={`px-2 py-0.5 rounded cursor-pointer transition font-bold select-none ${blacklistedAreas.name ? 'bg-zinc-950 text-white border border-zinc-900' : 'bg-amber-50 text-amber-700 border border-amber-200'}`}
                                      title="Haga clic para censurar"
                                    >
                                      {blacklistedAreas.name ? "█ █ █ █ █ █ █ █ █ █" : "ALEJANDRO GÓMEZ"}
                                    </span>
                                  </div>

                                  <div className="flex items-center justify-between">
                                    <span>ID / DNI:</span>
                                    <span 
                                      onClick={() => handleToggleRedactArea('id')}
                                      className={`px-2 py-0.5 rounded cursor-pointer transition font-bold select-none ${blacklistedAreas.id ? 'bg-zinc-950 text-white border border-zinc-900' : 'bg-amber-50 text-amber-700 border border-amber-200'}`}
                                      title="Haga clic para censurar"
                                    >
                                      {blacklistedAreas.id ? "█ █ █ █ █ █ █ █" : "49830294C"}
                                    </span>
                                  </div>

                                  <div className="flex items-center justify-between">
                                    <span>EMAIL:</span>
                                    <span 
                                      onClick={() => handleToggleRedactArea('email')}
                                      className={`px-2 py-0.5 rounded cursor-pointer transition font-bold select-none ${blacklistedAreas.email ? 'bg-zinc-950 text-white border border-zinc-900' : 'bg-amber-50 text-amber-700 border border-amber-200'}`}
                                      title="Haga clic para censurar"
                                    >
                                      {blacklistedAreas.email ? "█ █ █ █ █ █ █ █ █ █ █ █ █ █" : "alejandro.gomez@corp.es"}
                                    </span>
                                  </div>

                                  <div className="flex items-center justify-between">
                                    <span>CARD:</span>
                                    <span 
                                      onClick={() => handleToggleRedactArea('card')}
                                      className={`px-2 py-0.5 rounded cursor-pointer transition font-bold select-none ${blacklistedAreas.card ? 'bg-zinc-950 text-white border border-zinc-900' : 'bg-amber-50 text-amber-700 border border-amber-200'}`}
                                      title="Haga clic para censurar"
                                    >
                                      {blacklistedAreas.card ? "█ █ █ █ █ █ █ █ █ █ █ █" : "5412 7512 3456 7890"}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            </div>
                          ) : (
                            /* Render para archivos planos de Texto / CSV */
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-[240px] overflow-y-auto">
                              <div>
                                <p className="text-[10px] uppercase font-bold tracking-wider text-zinc-400 mb-2 font-mono">Contenido Original</p>
                                <div className="bg-white border border-zinc-200 rounded-lg p-3 text-xs font-mono text-zinc-800 h-[200px] overflow-y-auto whitespace-pre-wrap">
                                  {selectedFile.originalContent}
                                </div>
                              </div>

                              <div>
                                <p className="text-[10px] uppercase font-bold tracking-wider text-zinc-400 mb-2 font-mono">Contenido Sanitizado</p>
                                <div className="bg-amber-50/10 border border-amber-200/50 rounded-lg p-3 text-xs font-mono text-zinc-800 h-[200px] overflow-y-auto whitespace-pre-wrap relative">
                                  {isProcessing ? (
                                    <div className="flex flex-col items-center justify-center h-full text-amber-600 space-y-2">
                                      <RefreshCw className="h-6 w-6 animate-spin text-amber-500" />
                                      <p className="text-xs font-semibold">Sanitizando datos sensibles...</p>
                                    </div>
                                  ) : selectedFile.status === 'done' ? (
                                    selectedFile.redactedContent
                                  ) : (
                                    <button 
                                      onClick={() => processFileLocal(selectedFile.id)}
                                      className="w-full h-full flex flex-col items-center justify-center text-amber-600 hover:text-amber-700 bg-amber-50/40 hover:bg-amber-50/80 rounded-lg p-4 transition border border-dashed border-amber-300/80 cursor-pointer group"
                                    >
                                      <Shield className="h-7 w-7 text-amber-500 group-hover:scale-110 transition mb-2" />
                                      <span className="text-xs font-bold uppercase tracking-wider">Anonimizar ahora con IA Local</span>
                                      <span className="text-[10px] text-zinc-500 font-sans mt-1">Haga clic aquí para sanitizar datos sensibles</span>
                                    </button>
                                  )}
                                </div>
                              </div>
                            </div>
                          )}

                          {/* Estadísticas de Entidades Detectadas */}
                          {selectedFile.status === 'done' && (
                            <div className="border-t border-zinc-200 pt-4 mt-2">
                              <h5 className="text-[11px] font-bold uppercase tracking-wider text-zinc-400 mb-2">Entidades Identificadas por la IA</h5>
                              <div className="flex flex-wrap gap-2">
                                {selectedFile.piiFound.length > 0 ? (
                                  Array.from(new Set(selectedFile.piiFound.map(p => p.category))).map((cat, idx) => {
                                    const count = selectedFile.piiFound.filter(p => p.category === cat).length;
                                    return (
                                      <span key={idx} className="text-[10px] font-semibold font-mono bg-white text-amber-700 border border-zinc-200 shadow-sm px-2.5 py-1 rounded-md">
                                        {cat}: <strong className="text-zinc-900">{count}</strong>
                                      </span>
                                    );
                                  })
                                ) : (
                                  <span className="text-[10px] font-mono text-zinc-500">Ningún PII detectado bajo las reglas configuradas.</span>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="flex flex-col items-center justify-center py-16 text-zinc-400">
                          <Eye className="h-10 w-10 text-zinc-300 mb-3" />
                          <p className="text-sm font-semibold text-zinc-850">Ningún archivo seleccionado</p>
                          <p className="text-xs text-zinc-500 text-center max-w-xs mt-1">Seleccione un archivo de la cola para ver el análisis de datos e iniciar la anonimización.</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* LOGS DE AUDITORÍA CORPORATIVA */}
                <div className="bg-white border border-zinc-200 rounded-2xl p-6 shadow-sm">
                  <div className="flex items-center gap-2 mb-4">
                    <Activity className="h-5 w-5 text-amber-500" />
                    <h3 className="text-sm font-bold text-zinc-800 uppercase tracking-wider">Historial de Auditoría de Datos Local</h3>
                  </div>
                  
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs font-mono">
                      <thead className="bg-zinc-50 border-b border-zinc-200 text-zinc-500 uppercase tracking-wider">
                        <tr>
                          <th className="p-3">Hora</th>
                          <th className="p-3">Archivo Sanitizado</th>
                          <th className="p-3">Tipo</th>
                          <th className="p-3">Tamaño</th>
                          <th className="p-3">PII Bloqueados</th>
                          <th className="p-3">Categorías</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-100">
                        {auditLogs.map((log) => (
                          <tr key={log.id} className="hover:bg-zinc-50/50">
                            <td className="p-3 text-zinc-500">{log.timestamp}</td>
                            <td className="p-3 font-semibold text-zinc-800">{log.fileName}</td>
                            <td className="p-3 text-zinc-500">{log.fileType.split('/')[1] || 'docx'}</td>
                            <td className="p-3 text-zinc-500">{log.fileSize}</td>
                            <td className="p-3">
                              <span className="bg-red-50 text-red-600 border border-red-100 px-2 py-0.5 rounded-full font-bold">
                                {log.piiCount}
                              </span>
                            </td>
                            <td className="p-3 text-amber-600">{log.entitiesDetected.join(', ') || 'N/A'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

              </div>
            )}

            {/* --- CONTENIDO TAB: TRADUCCIÓN INVERSA --- */}
            {activeTab === 'reverse' && (
              <div className="space-y-6">
                <div className="bg-white border border-zinc-200 p-6 rounded-2xl space-y-3 shadow-sm">
                  <h2 className="text-lg font-bold text-zinc-900 flex items-center gap-2">
                    <ArrowLeftRight className="h-5 w-5 text-amber-500" />
                    Traducción Inversa (Reversible PII Portal)
                  </h2>
                  <p className="text-xs text-zinc-500 leading-relaxed font-sans">
                    Cargue el documento devuelto por la IA (`.docx`, `.csv`, `.txt`, `.xlsx`) y el archivo de llave <code className="text-emerald-600 font-bold">.reverse.key</code> para desanonimizar los datos y exportar el documento desanonimizado en el **mismo formato original**.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Entrada del texto y del JSON key */}
                  <div className="bg-white border border-zinc-200 p-5 rounded-2xl space-y-4 shadow-sm">
                    {/* Carga de archivo para desencriptar (Bug 6 & Preloader Bug 5) */}
                    <div className="space-y-2">
                      <label className="block text-xs uppercase tracking-wider font-bold text-zinc-500 font-mono">
                        Subir Documento Procesado por IA (.docx, .csv, .txt, .xlsx)
                      </label>
                      <label className="w-full flex items-center justify-center gap-2 border border-zinc-200 hover:border-emerald-500 bg-zinc-50 hover:bg-zinc-100 p-3 rounded-lg cursor-pointer transition text-xs font-semibold text-zinc-700">
                        <Upload className="h-4 w-4 text-emerald-600" />
                        <span>{reverseFileName !== 'documento_restaurado.docx' ? reverseFileName : 'Seleccionar Documento para Desanonimizar'}</span>
                        <input 
                          type="file" 
                          accept=".txt,.csv,.docx,.xlsx,.json"
                          onChange={handleReverseFileUpload}
                          className="hidden" 
                        />
                      </label>
                    </div>

                    <div>
                      <label className="block text-xs uppercase tracking-wider font-bold text-zinc-500 mb-2 font-mono">
                        Texto / Contenido Anonimizado
                      </label>
                      <textarea 
                        rows={4}
                        placeholder="Pegue aquí el texto devuelto por la IA o cargue un documento arriba..."
                        value={reverseText}
                        onChange={(e) => setReverseText(e.target.value)}
                        className="w-full bg-zinc-50 border border-zinc-200 rounded-lg p-3 text-xs font-mono text-zinc-800 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 focus:outline-none"
                      />
                      <div className="flex gap-2 mt-2">
                        <button 
                          onClick={() => {
                            setReverseFileName('transcripcion_entrevista_restaurada.docx');
                            setReverseFileExt('docx');
                            setReverseText("Interlocutor 1 (Laura): Hola, el contrato de [PERSONA_1] para el dominio [DOMINIO_1] ha sido guardado por [ORGANIZACION_1] con la clave [CLAVE_1].");
                          }}
                          className="text-[10px] bg-zinc-100 border border-zinc-200 text-zinc-600 hover:bg-zinc-200 px-2 py-1 rounded transition"
                        >
                          Cargar transcripción de prueba (DOCX)
                        </button>
                      </div>
                    </div>

                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <label className="block text-xs uppercase tracking-wider font-bold text-zinc-500 font-mono">
                          Llave de Reversión (.reverse.key)
                        </label>
                        <label className="text-[10px] text-emerald-600 hover:underline cursor-pointer font-bold">
                          Subir archivo .key
                          <input type="file" accept=".key,.json" onChange={handleReverseKeyFileUpload} className="hidden" />
                        </label>
                      </div>
                      <textarea 
                        rows={4}
                        placeholder='Ejemplo de mapeo JSON:&#10;{&#10;  "[PERSONA_1]": "Carlos Mendoza",&#10;  "[DOMINIO_1]": "miempresa.com",&#10;  "[ORGANIZACION_1]": "InnovaTech"&#10;}'
                        value={reverseKeyInput}
                        onChange={(e) => setReverseKeyInput(e.target.value)}
                        className="w-full bg-zinc-50 border border-zinc-200 rounded-lg p-3 text-xs font-mono text-zinc-800 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 focus:outline-none"
                      />
                      <div className="flex gap-2 mt-2">
                        <button 
                          onClick={() => setReverseKeyInput('{\n  "[PERSONA_1]": "Carlos Mendoza",\n  "[DOMINIO_1]": "miempresa.com",\n  "[ORGANIZACION_1]": "InnovaTech",\n  "[CLAVE_1]": "sk-proj-7819238"\n}')}
                          className="text-[10px] bg-zinc-100 border border-zinc-200 text-zinc-600 hover:bg-zinc-200 px-2 py-1 rounded transition"
                        >
                          Cargar llave de ejemplo
                        </button>
                      </div>
                    </div>

                    <button 
                      onClick={runReverseTranslation}
                      disabled={isReversing}
                      className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-300 text-white font-bold text-xs uppercase tracking-wider rounded-xl transition flex items-center justify-center gap-2 shadow-sm"
                    >
                      {isReversing ? (
                        <>
                          <RefreshCw className="h-4 w-4 animate-spin" />
                          <span>Desanonimizando documento...</span>
                        </>
                      ) : (
                        <>
                          <RefreshCw className="h-4 w-4" />
                          <span>Restaurar Datos Reales</span>
                        </>
                      )}
                    </button>
                  </div>

                  {/* Salida del texto original restaurado y Exportación Formato Original (Bug 6) */}
                  <div className="bg-white border border-zinc-200 p-5 rounded-2xl flex flex-col justify-between shadow-sm">
                    <div>
                      <h4 className="text-xs uppercase tracking-wider font-bold text-zinc-500 mb-4 font-mono flex items-center justify-between">
                        <span>Resultado Desanonimizado</span>
                        {isReverseDone && (
                          <span className="text-[10px] bg-emerald-50 text-emerald-700 border border-emerald-200 px-2.5 py-0.5 rounded-full font-bold flex items-center gap-1">
                            <CheckCircle2 className="h-3 w-3" />
                            Formato Preservado (.{reverseFileExt.toUpperCase()})
                          </span>
                        )}
                      </h4>

                      <div className="bg-zinc-50 border border-zinc-100 rounded-lg p-4 text-xs font-mono text-zinc-800 min-h-[220px] whitespace-pre-wrap relative">
                        {isReversing ? (
                          <div className="flex flex-col items-center justify-center h-full text-emerald-600 space-y-2 py-12">
                            <RefreshCw className="h-7 w-7 animate-spin text-emerald-500" />
                            <p className="text-xs font-semibold">Reemplazando tokens y reconstruyendo archivo...</p>
                          </div>
                        ) : reverseOutput ? (
                          reverseOutput
                        ) : (
                          <span className="text-zinc-400 italic">Complete la información de entrada a la izquierda y presione 'Restaurar Datos Reales'.</span>
                        )}
                      </div>
                    </div>

                    {isReverseDone && (
                      <div className="mt-4 pt-4 border-t border-zinc-100 flex items-center justify-between">
                        <div className="text-[11px] font-mono text-zinc-500">
                          Exportar como: <span className="font-bold text-emerald-700">.{reverseFileExt.toUpperCase()}</span>
                        </div>
                        <button 
                          onClick={() => {
                            const mimeMap: Record<string, string> = {
                              docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                              csv: 'text/csv',
                              txt: 'text/plain',
                              xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                            };
                            const mime = mimeMap[reverseFileExt] || 'text/plain';
                            const blob = new Blob([reverseOutput], { type: mime });
                            const url = URL.createObjectURL(blob);
                            const link = document.createElement('a');
                            link.href = url;
                            link.download = reverseFileName.endsWith(`.${reverseFileExt}`) ? reverseFileName : `${reverseFileName}.${reverseFileExt}`;
                            document.body.appendChild(link);
                            link.click();
                            document.body.removeChild(link);
                          }}
                          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold shadow-sm rounded-xl text-xs flex items-center gap-2 transition"
                        >
                          <Download className="h-4 w-4" />
                          <span>Exportar Documento (.{reverseFileExt.toUpperCase()})</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* --- CONTENIDO TAB: WHITELIST / DICCIONARIO --- */}
            {activeTab === 'whitelist' && (
              <div className="space-y-6">
                <div className="bg-white border border-zinc-200 p-6 rounded-2xl space-y-3 shadow-sm">
                  <h2 className="text-lg font-bold text-zinc-900 flex items-center gap-2">
                    <Book className="h-5 w-5 text-amber-500" />
                    Diccionario de Exclusiones de la Empresa (Palabras Prohibidas)
                  </h2>
                  <p className="text-xs text-zinc-500 leading-relaxed font-sans">
                    Además del comportamiento estándar de la IA local que detecta correos y DNI, muchas empresas poseen nombres de código confidenciales o proyectos secretos que no constituyen datos personales de por sí, pero cuya revelación a nubes externas debe evitarse a toda costa. Registre estos términos a continuación para censurarlos automáticamente.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
                  {/* Formulario de agregar */}
                  <form onSubmit={addWhitelistWord} className="md:col-span-5 bg-white border border-zinc-200 p-5 rounded-2xl space-y-4 shadow-sm">
                    <h3 className="text-xs uppercase tracking-wider font-bold text-zinc-500 mb-2 font-mono">
                      Registrar Nuevo Término
                    </h3>
                    
                    <div>
                      <label className="block text-xs text-zinc-500 mb-1.5 font-sans">Palabra o Frase Exacta</label>
                      <input 
                        type="text" 
                        placeholder="Ej: Proyecto Halcón"
                        value={newWord}
                        onChange={(e) => setNewWord(e.target.value)}
                        className="w-full bg-zinc-50 border border-zinc-200 rounded-lg px-3 py-2 text-xs font-mono text-zinc-800 focus:border-amber-500 focus:ring-1 focus:ring-amber-500 focus:outline-none"
                      />
                    </div>

                    <div>
                      <label className="block text-xs text-zinc-500 mb-1.5 font-sans">Clasificación / Categoría</label>
                      <select 
                        value={newCategory}
                        onChange={(e) => setNewCategory(e.target.value)}
                        className="w-full bg-zinc-50 border border-zinc-200 rounded-lg px-3 py-2 text-xs font-sans text-zinc-800 focus:border-amber-500 focus:ring-1 focus:ring-amber-500 focus:outline-none"
                      >
                        <option value="Proyecto Secreto">Proyecto Secreto</option>
                        <option value="Cliente VIP">Cliente VIP</option>
                        <option value="Patente / Tecnología">Patente / Tecnología</option>
                        <option value="Código Interno">Código Interno</option>
                      </select>
                    </div>

                    <button 
                      type="submit"
                      className="w-full py-2 bg-[#f99c00] hover:bg-[#e08b00] text-white font-bold text-xs uppercase tracking-wider rounded-xl transition flex items-center justify-center gap-2 shadow-sm"
                    >
                      <Plus className="h-4 w-4" />
                      Agregar al Diccionario
                    </button>
                  </form>

                  {/* Tabla de términos registrados */}
                  <div className="md:col-span-7 bg-white border border-zinc-200 p-5 rounded-2xl space-y-4 shadow-sm">
                    <h3 className="text-xs uppercase tracking-wider font-bold text-zinc-500 mb-2 font-mono">
                      Términos Activos ({whitelist.length})
                    </h3>

                    <div className="space-y-2 max-h-[240px] overflow-y-auto">
                      {whitelist.map((item) => (
                        <div key={item.id} className="flex items-center justify-between p-2.5 bg-zinc-50 border border-zinc-200 rounded-lg">
                          <div>
                            <p className="text-xs font-bold font-mono text-zinc-800">{item.word}</p>
                            <p className="text-[10px] text-zinc-500 font-sans">{item.category}</p>
                          </div>
                          
                          <button 
                            type="button"
                            onClick={() => removeWhitelistWord(item.id)}
                            className="text-zinc-400 hover:text-red-600 p-1.5 rounded transition"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* --- CONTENIDO TAB: LICENCIA & SIMULACIÓN --- */}
            {activeTab === 'license' && (
              <div className="space-y-6">
                <div className="bg-white border border-zinc-200 p-6 rounded-2xl space-y-3 shadow-sm">
                  <h2 className="text-lg font-bold text-zinc-900 flex items-center gap-2">
                    <Key className="h-5 w-5 text-amber-500" />
                    Portal de Gestión de Licencias Offline (Simulador Admin)
                  </h2>
                  <p className="text-xs text-zinc-500 leading-relaxed font-sans">
                    La aplicación funciona mediante una llave criptográfica llamada <code className="text-amber-600 font-bold">licencia.key</code> en la raíz de su servidor. Utilice este portal para simular diferentes escenarios de validación de licencias para sus clientes, o comprobar cómo el sistema bloquea los accesos temporalmente en caso de incidencias de seguridad.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Selector de estado de simulación */}
                  <div className="bg-white border border-zinc-200 p-5 rounded-2xl space-y-4 shadow-sm">
                    <h3 className="text-xs uppercase tracking-wider font-bold text-zinc-500 mb-2 font-mono">
                      Simular Estado del Servidor Local
                    </h3>

                    <div className="space-y-2">
                      <button 
                        onClick={() => setLicenseState('activa')}
                        className={`w-full flex items-center justify-between p-3 rounded-xl border text-xs font-semibold text-left transition ${licenseState === 'activa' ? 'bg-emerald-50 border-emerald-500 text-emerald-700 font-bold' : 'bg-zinc-50 border-zinc-200 text-zinc-600 hover:bg-zinc-100'}`}
                      >
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="h-4 w-4" />
                          <span>Licencia Activa (Funcionamiento Normal)</span>
                        </div>
                        <span className="text-[10px] font-mono">OK_200</span>
                      </button>

                      <button 
                        onClick={() => setLicenseState('expirada')}
                        className={`w-full flex items-center justify-between p-3 rounded-xl border text-xs font-semibold text-left transition ${licenseState === 'expirada' ? 'bg-red-50 border-red-500 text-red-700 font-bold' : 'bg-zinc-50 border-zinc-200 text-zinc-600 hover:bg-zinc-100'}`}
                      >
                        <div className="flex items-center gap-2">
                          <AlertOctagon className="h-4 w-4" />
                          <span>Licencia Expirada (Trial de 1 año vencido)</span>
                        </div>
                        <span className="text-[10px] font-mono">ERR_403</span>
                      </button>

                      <button 
                        onClick={() => setLicenseState('reloj')}
                        className={`w-full flex items-center justify-between p-3 rounded-xl border text-xs font-semibold text-left transition ${licenseState === 'reloj' ? 'bg-red-50 border-red-500 text-red-700 font-bold' : 'bg-zinc-50 border-zinc-200 text-zinc-600 hover:bg-zinc-100'}`}
                      >
                        <div className="flex items-center gap-2">
                          <AlertTriangle className="h-4 w-4" />
                          <span>Fraude de Reloj (Fecha del sistema atrasada)</span>
                        </div>
                        <span className="text-[10px] font-mono">ERR_CLOCK</span>
                      </button>

                      <button 
                        onClick={() => setLicenseState('corrupta')}
                        className={`w-full flex items-center justify-between p-3 rounded-xl border text-xs font-semibold text-left transition ${licenseState === 'corrupta' ? 'bg-red-50 border-red-500 text-red-700 font-bold' : 'bg-zinc-50 border-zinc-200 text-zinc-600 hover:bg-zinc-100'}`}
                      >
                        <div className="flex items-center gap-2">
                          <AlertOctagon className="h-4 w-4" />
                          <span>Firma Corrupta / Licencia Alterada</span>
                        </div>
                        <span className="text-[10px] font-mono">ERR_SIGN</span>
                      </button>
                    </div>

                    <div className="bg-zinc-50 p-3 rounded-xl border border-zinc-200 text-[11px] text-zinc-500 leading-relaxed">
                      <span className="text-amber-600 font-bold">Comportamiento: </span>
                      Al simular un estado erróneo, se congelará la aplicación de inmediato bajo un escudo rojo de bloqueo corporativo, demostrando la solidez del sistema local de Lia Vault.
                    </div>
                  </div>

                  {/* Creador de llave licencia.key */}
                  <div className="bg-white border border-zinc-200 p-5 rounded-2xl space-y-4 shadow-sm">
                    <h3 className="text-xs uppercase tracking-wider font-bold text-zinc-500 mb-2 font-mono">
                      Generador de Archivos de Licencia (.key)
                    </h3>

                    <div>
                      <label className="block text-[11px] text-zinc-500 mb-1.5 font-sans font-medium">Nombre del Cliente / Empresa</label>
                      <input 
                        type="text" 
                        value={customClientName}
                        onChange={(e) => setCustomClientName(e.target.value)}
                        className="w-full bg-zinc-50 border border-zinc-200 rounded-lg px-3 py-1.5 text-xs font-mono text-zinc-800 focus:border-amber-500 focus:ring-1 focus:ring-amber-500 focus:outline-none"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] text-zinc-500 mb-1.5 font-sans font-medium">Fecha de Vencimiento de Prueba</label>
                      <input 
                        type="date" 
                        value={customLicenseDate}
                        onChange={(e) => setCustomLicenseDate(e.target.value)}
                        className="w-full bg-zinc-50 border border-zinc-200 rounded-lg px-3 py-1.5 text-xs font-mono text-zinc-800 focus:border-amber-500 focus:ring-1 focus:ring-amber-500 focus:outline-none"
                      />
                    </div>

                    <button 
                      onClick={downloadLicenseKeyFile}
                      className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs uppercase tracking-wider rounded-xl transition flex items-center justify-center gap-2 shadow-sm"
                    >
                      <Download className="h-4 w-4" />
                      Descargar licencia.key Firmada
                    </button>

                    <div className="p-3 bg-zinc-50 rounded-xl text-[10px] text-zinc-400 leading-relaxed font-sans">
                      Este generador simula la clave asimétrica oficial del backend de Lia Corp. La firma SHA-256 contenida impedirá que los administradores de sistemas de la PYME aumenten los días del periodo de prueba de forma manual.
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* --- CONTENIDO TAB: CÓDIGO ON-PREMISE --- */}
            {activeTab === 'code' && (
              <div className="space-y-6">
                <div className="bg-white border border-zinc-200 p-6 rounded-2xl space-y-3 shadow-sm">
                  <div className="flex items-center justify-between">
                    <h2 className="text-lg font-bold text-zinc-900 flex items-center gap-2">
                      <Terminal className="h-5 w-5 text-amber-500" />
                      Código Fuente Completo y Refactorizado (On-Premise Suite)
                    </h2>
                    
                    <button 
                      onClick={() => handleCopyCode(CODE_SNIPPETS[activeSnippetTab])}
                      className="px-3 py-1.5 bg-zinc-100 hover:bg-zinc-200 border border-zinc-200 text-amber-600 text-xs font-bold rounded-lg flex items-center gap-1.5 transition shadow-sm"
                    >
                      {isCopied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
                      <span>{isCopied ? '¡Copiado!' : 'Copiar Archivo'}</span>
                    </button>
                  </div>
                  <p className="text-xs text-zinc-500 leading-relaxed font-sans">
                    Navegue por la estructura de módulos completa que hemos creado en el espacio de trabajo local de su computadora. Estos archivos están listos para ser empaquetados en Windows/Mac o desplegados con Docker en la red local de su oficina.
                  </p>
                </div>

                {/* Sub-pestañas de archivos Python */}
                <div className="flex flex-wrap gap-1 bg-zinc-100 p-1.5 border border-zinc-200 rounded-xl">
                  <button 
                    onClick={() => setActiveSnippetTab('app_grafica')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-mono transition ${activeSnippetTab === 'app_grafica' ? 'bg-white text-amber-600 border border-zinc-200 shadow-xs' : 'text-zinc-500 hover:text-zinc-700'}`}
                  >
                    app_grafica.py (Flet UI)
                  </button>

                  <button 
                    onClick={() => setActiveSnippetTab('app_offline')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-mono transition ${activeSnippetTab === 'app_offline' ? 'bg-white text-amber-600 border border-zinc-200 shadow-xs' : 'text-zinc-500 hover:text-zinc-700'}`}
                  >
                    app_offline.py (IA Local)
                  </button>

                  <button 
                    onClick={() => setActiveSnippetTab('validador')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-mono transition ${activeSnippetTab === 'validador' ? 'bg-white text-amber-600 border border-zinc-200 shadow-xs' : 'text-zinc-500 hover:text-zinc-700'}`}
                  >
                    validador.py (Seguridad)
                  </button>

                  <button 
                    onClick={() => setActiveSnippetTab('dockerfile')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-mono transition ${activeSnippetTab === 'dockerfile' ? 'bg-white text-amber-600 border border-zinc-200 shadow-xs' : 'text-zinc-500 hover:text-zinc-700'}`}
                  >
                    Dockerfile (LAN Server)
                  </button>

                  <button 
                    onClick={() => setActiveSnippetTab('requirements')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-mono transition ${activeSnippetTab === 'requirements' ? 'bg-white text-amber-600 border border-zinc-200 shadow-xs' : 'text-zinc-500 hover:text-zinc-700'}`}
                  >
                    requirements.txt
                  </button>
                </div>

                {/* Área de Visualización de Código */}
                <div className="bg-zinc-950 border border-zinc-900 rounded-2xl overflow-hidden shadow-xl">
                  <div className="bg-zinc-900 px-4 py-2 flex items-center justify-between border-b border-zinc-950">
                    <span className="text-xs text-zinc-400 font-mono">
                      {activeSnippetTab === 'requirements' ? 'requirements.txt' : activeSnippetTab === 'dockerfile' ? 'Dockerfile' : `${activeSnippetTab}.py`}
                    </span>
                    <span className="text-[10px] uppercase font-mono bg-amber-950/50 text-amber-400 px-2.5 py-0.5 rounded border border-amber-900/50">
                      Sintaxis Verificada
                    </span>
                  </div>

                  <pre className="p-5 text-xs text-zinc-300 font-mono overflow-auto max-h-[420px] text-left leading-relaxed whitespace-pre-wrap">
                    <code>{CODE_SNIPPETS[activeSnippetTab]}</code>
                  </pre>
                </div>

                {/* Guía de instalación de PyInstaller */}
                <div className="bg-white border border-zinc-200 p-5 rounded-2xl flex items-start gap-4 shadow-sm">
                  <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 text-amber-600 shrink-0">
                    <Info className="h-6 w-6" />
                  </div>
                  <div className="space-y-1">
                    <h4 className="text-xs font-bold text-zinc-900 uppercase tracking-wider">Cómo generar el ejecutable para probar localmente</h4>
                    <p className="text-xs text-zinc-500 font-sans leading-relaxed">
                      Abra la terminal de su computadora en el directorio del proyecto y ejecute: <code className="text-amber-600 font-bold">pyinstaller --name="LiaVault" --noconsole --onefile app_grafica.py</code>. Se empaquetará la interfaz Flet en un archivo binario autoejecutable dentro de la carpeta <code className="text-amber-600 font-bold">dist/</code>. Para ver instrucciones de Docker, consulte la guía de despliegue en su espacio de trabajo.
                    </p>
                  </div>
                </div>

              </div>
            )}

          </div>
        </div>
      </main>

      {/* --- FOOTER PRINCIPAL --- */}
      <footer className="border-t border-zinc-200 py-8 bg-white mt-16 text-xs text-zinc-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col md:flex-row items-center justify-between gap-4 text-center md:text-left">
          <div className="space-y-1">
            <p className="font-bold text-zinc-700 font-mono">LIA VAULT • ESCUDO LOCAL PYME</p>
            <p className="text-[11px] text-zinc-500">Herramienta offline de cumplimiento legal y protección de propiedad intelectual contra fugas en IA.</p>
          </div>
          <div className="text-[11px] text-zinc-500 font-mono">
            Licenciado a: <span className="text-zinc-700 font-bold">{customClientName}</span> • Version 1.4.0 (On-Premise)
          </div>
        </div>
      </footer>
    </div>
  );
}
