import React, { useState } from 'react';
import Editor from '@monaco-editor/react';

const AICodeAnalyzer: React.FC = () => {
  const [code, setCode] = useState('');
  const [language, setLanguage] = useState('javascript');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<any>(null);

  const handleAnalyze = async () => {
    if (!code.trim()) return;

    setIsAnalyzing(true);
    
    try {
      const response = await fetch('/api/code/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ code, language })
      });

      if (!response.ok) {
        throw new Error('Failed to analyze code');
      }

      const result = await response.json();
      setAnalysis(result);
    } catch (error) {
      console.error('Error analyzing code:', error);
      alert('Failed to analyze code. Make sure Ollama is running with gpt-oss model.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-100 text-red-800 border-red-200';
      case 'high': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low': return 'bg-blue-100 text-blue-800 border-blue-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'security': return '🔒';
      case 'performance': return '⚡';
      case 'logic': return '🧠';
      case 'style': return '🎨';
      case 'maintainability': return '🔧';
      default: return '⚠️';
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow-md">
        <div className="flex items-center mb-4">
          <div className="text-2xl mr-3">🔍</div>
          <div>
            <h3 className="text-lg font-semibold text-gray-800">AI Code Analyzer</h3>
            <p className="text-sm text-gray-600">Paste your code and get instant AI-powered analysis</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Programming Language
              </label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="javascript">JavaScript</option>
                <option value="python">Python</option>
                <option value="typescript">TypeScript</option>
                <option value="java">Java</option>
                <option value="csharp">C#</option>
              </select>
            </div>

            <div className="border rounded-lg overflow-hidden">
              <div className="bg-gray-50 px-4 py-2 border-b">
                <h4 className="font-medium text-gray-800">Code to Analyze</h4>
              </div>
              <div className="h-64">
                <Editor
                  height="100%"
                  language={language}
                  value={code}
                  onChange={(value) => setCode(value || '')}
                  options={{
                    minimap: { enabled: false },
                    lineNumbers: 'on',
                    wordWrap: 'on',
                    fontSize: 14
                  }}
                  theme="vs-light"
                />
              </div>
            </div>

            <button
              onClick={handleAnalyze}
              disabled={isAnalyzing || !code.trim()}
              className="mt-4 w-full px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-md hover:from-purple-700 hover:to-blue-700 disabled:from-gray-400 disabled:to-gray-500 disabled:cursor-not-allowed transition-all font-medium flex items-center justify-center"
            >
              {isAnalyzing ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                  Analyzing with AI...
                </>
              ) : (
                <>
                  <span className="mr-2">🤖</span>
                  Analyze Code with AI
                </>
              )}
            </button>
          </div>

          <div className="space-y-4">
            {analysis && (
              <div className="bg-gray-50 p-4 rounded-lg">
                <h4 className="font-medium text-gray-800 mb-2">Analysis Results</h4>
                <div className="text-sm text-gray-600 space-y-1">
                  <div>Issues Found: {analysis.issues?.length || 0}</div>
                  <div>AI Powered: {analysis.ai_powered ? '✅' : '❌'}</div>
                  <div>Timestamp: {new Date(analysis.analysis_timestamp).toLocaleTimeString()}</div>
                </div>
              </div>
            )}

            <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
              <h4 className="font-medium text-blue-800 mb-2">How it works</h4>
              <div className="text-sm text-blue-700 space-y-1">
                <div>• AI analyzes your code structure</div>
                <div>• Identifies security vulnerabilities</div>
                <div>• Spots performance bottlenecks</div>
                <div>• Suggests improvements</div>
                <div>• Provides learning explanations</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {analysis && analysis.issues && analysis.issues.length > 0 && (
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">
            AI Analysis Results ({analysis.issues.length} issues found)
          </h3>
          
          <div className="space-y-4">
            {analysis.issues.map((issue: any, index: number) => (
              <div key={index} className={`p-4 rounded-lg border ${getSeverityColor(issue.severity)}`}>
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-lg">{getTypeIcon(issue.type)}</span>
                    <h4 className="font-medium">{issue.title}</h4>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs px-2 py-1 bg-white rounded-full">
                      Line {issue.line}
                    </span>
                    <span className="text-xs px-2 py-1 bg-white rounded-full capitalize">
                      {issue.severity}
                    </span>
                  </div>
                </div>
                
                <p className="text-sm mb-2">{issue.description}</p>
                
                <div className="bg-white bg-opacity-50 p-3 rounded text-sm">
                  <strong>💡 Suggestion:</strong> {issue.suggestion}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default AICodeAnalyzer;