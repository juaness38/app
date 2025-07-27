import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AntaresApp = () => {
  const [systemInfo, setSystemInfo] = useState(null);
  const [protocolTypes, setProtocolTypes] = useState([]);
  const [availableTools, setAvailableTools] = useState([]);
  const [selectedProtocol, setSelectedProtocol] = useState("");
  const [sequence, setSequence] = useState("");
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const API_KEY = "antares-super-secret-key-2024";

  useEffect(() => {
    fetchSystemInfo();
    fetchProtocolTypes();
    fetchAvailableTools();
    fetchAnalyses();
  }, []);

  const fetchSystemInfo = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/`);
      setSystemInfo(response.data);
    } catch (e) {
      console.error("Error fetching system info:", e);
    }
  };

  const fetchProtocolTypes = async () => {
    try {
      const response = await axios.get(`${API}/analysis/protocols/types`, {
        headers: { "X-API-Key": API_KEY }
      });
      setProtocolTypes(response.data);
    } catch (e) {
      console.error("Error fetching protocol types:", e);
    }
  };

  const fetchAvailableTools = async () => {
    try {
      const response = await axios.get(`${API}/analysis/tools/available`, {
        headers: { "X-API-Key": API_KEY }
      });
      setAvailableTools(response.data);
    } catch (e) {
      console.error("Error fetching available tools:", e);
    }
  };

  const fetchAnalyses = async () => {
    try {
      const response = await axios.get(`${API}/analysis/`, {
        headers: { "X-API-Key": API_KEY }
      });
      setAnalyses(response.data);
    } catch (e) {
      console.error("Error fetching analyses:", e);
    }
  };

  const startAnalysis = async () => {
    if (!selectedProtocol || !sequence) {
      setError("Por favor selecciona un protocolo y proporciona una secuencia");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const requestData = {
        workspace_id: "workspace_001",
        protocol_type: selectedProtocol,
        sequence: sequence,
        parameters: {},
        priority: 1
      };

      const response = await axios.post(`${API}/analysis/`, requestData, {
        headers: { 
          "X-API-Key": API_KEY,
          "Content-Type": "application/json"
        }
      });

      setAnalyses([response.data, ...analyses]);
      setSequence("");
      setSelectedProtocol("");
      
    } catch (e) {
      setError(`Error iniciando análisis: ${e.response?.data?.detail || e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "COMPLETED": return "text-green-600";
      case "PROCESSING": return "text-blue-600";
      case "FAILED": return "text-red-600";
      case "QUEUED": return "text-yellow-600";
      default: return "text-gray-600";
    }
  };

  const formatProtocolName = (type) => {
    const names = {
      "PROTEIN_FUNCTION_ANALYSIS": "Análisis de Función de Proteína",
      "SEQUENCE_ALIGNMENT": "Alineamiento de Secuencias",
      "STRUCTURE_PREDICTION": "Predicción de Estructura",
      "DRUG_DESIGN": "Diseño de Fármacos",
      "BIOREACTOR_OPTIMIZATION": "Optimización de Bioreactor"
    };
    return names[type] || type;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-blue-900 text-white shadow-lg">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold">🧬 Astroflora Antares</h1>
              <p className="text-blue-200 mt-1">Sistema Cognitivo para Investigación Científica Autónoma</p>
            </div>
            <div className="text-right">
              <div className="text-sm text-blue-200">
                Versión: {systemInfo?.version || "Cargando..."}
              </div>
              <div className="text-sm text-blue-200">
                Entorno: {systemInfo?.environment || "Cargando..."}
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Panel de Nuevo Análisis */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-2xl font-bold mb-6 text-gray-800">
                🔬 Iniciar Nuevo Análisis
              </h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Tipo de Protocolo
                  </label>
                  <select
                    value={selectedProtocol}
                    onChange={(e) => setSelectedProtocol(e.target.value)}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="">Selecciona un protocolo...</option>
                    {protocolTypes.map(type => (
                      <option key={type} value={type}>
                        {formatProtocolName(type)}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Secuencia Biológica
                  </label>
                  <textarea
                    value={sequence}
                    onChange={(e) => setSequence(e.target.value)}
                    placeholder="Introduce la secuencia de ADN, ARN o proteína..."
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500 h-32 font-mono text-sm"
                  />
                </div>

                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <p className="text-red-800">{error}</p>
                  </div>
                )}

                <button
                  onClick={startAnalysis}
                  disabled={loading || !selectedProtocol || !sequence}
                  className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {loading ? (
                    <span className="flex items-center justify-center">
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Iniciando Análisis...
                    </span>
                  ) : (
                    "🚀 Iniciar Análisis"
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Panel de Información */}
          <div className="space-y-6">
            {/* Herramientas Disponibles */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h3 className="text-xl font-bold mb-4 text-gray-800">
                🛠️ Herramientas Disponibles
              </h3>
              <div className="space-y-2">
                {availableTools.map(tool => (
                  <div key={tool} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                    <span className="text-sm font-medium text-gray-700">
                      {tool.toUpperCase()}
                    </span>
                    <span className="text-xs text-green-600 font-medium">
                      ✓ Activo
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Capacidades del Sistema */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h3 className="text-xl font-bold mb-4 text-gray-800">
                ⚡ Capacidades del Sistema
              </h3>
              <div className="space-y-3">
                <div className="flex items-center text-sm">
                  <span className="w-3 h-3 bg-green-500 rounded-full mr-3"></span>
                  <span>Driver IA con OpenAI</span>
                </div>
                <div className="flex items-center text-sm">
                  <span className="w-3 h-3 bg-green-500 rounded-full mr-3"></span>
                  <span>Orquestador Inteligente</span>
                </div>
                <div className="flex items-center text-sm">
                  <span className="w-3 h-3 bg-green-500 rounded-full mr-3"></span>
                  <span>Circuit Breakers</span>
                </div>
                <div className="flex items-center text-sm">
                  <span className="w-3 h-3 bg-green-500 rounded-full mr-3"></span>
                  <span>Gestión de Capacidad</span>
                </div>
                <div className="flex items-center text-sm">
                  <span className="w-3 h-3 bg-green-500 rounded-full mr-3"></span>
                  <span>EventStore para Auditoría</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Análisis Recientes */}
        <div className="mt-8">
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">
              📊 Análisis Recientes
            </h2>
            
            {analyses.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <p>No hay análisis recientes. ¡Inicia tu primer análisis!</p>
              </div>
            ) : (
              <div className="space-y-4">
                {analyses.map(analysis => (
                  <div key={analysis.context_id} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="font-medium text-gray-900">
                          {formatProtocolName(analysis.protocol_type)}
                        </h4>
                        <p className="text-sm text-gray-600 mt-1">
                          ID: {analysis.context_id}
                        </p>
                        <p className="text-sm text-gray-600">
                          Creado: {new Date(analysis.created_at).toLocaleString()}
                        </p>
                      </div>
                      <div className="text-right">
                        <span className={`font-medium ${getStatusColor(analysis.status)}`}>
                          {analysis.status}
                        </span>
                        <div className="text-sm text-gray-500 mt-1">
                          Progreso: {analysis.progress}%
                        </div>
                      </div>
                    </div>
                    
                    {analysis.current_step && (
                      <div className="mt-3 p-3 bg-blue-50 rounded">
                        <p className="text-sm text-blue-800">
                          <span className="font-medium">Paso actual:</span> {analysis.current_step}
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <AntaresApp />
    </div>
  );
}

export default App;