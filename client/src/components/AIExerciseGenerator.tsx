import React, { useState } from 'react';

interface AIExerciseGeneratorProps {
  onExerciseGenerated: (exercise: any) => void;
  darkMode?: boolean;
}

const AIExerciseGenerator: React.FC<AIExerciseGeneratorProps> = ({ onExerciseGenerated, darkMode = false }) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState('');
  const [formData, setFormData] = useState({
    language: 'javascript',
    difficulty: 'intermediate',
    category: 'security',
    description: ''
  });

  const handleGenerate = async () => {
    setIsGenerating(true);
    setGenerationProgress('🤖 Initializing AI generation...');
    
    try {
      // Progress updates to keep user engaged during slow AI processing
      setTimeout(() => setGenerationProgress('🔍 Analyzing requirements...'), 1000);
      setTimeout(() => setGenerationProgress('⚡ Generating realistic code...'), 3000);
      setTimeout(() => setGenerationProgress('🎯 Adding educational flaws...'), 6000);
      setTimeout(() => setGenerationProgress('📝 Creating explanations...'), 9000);
      
      const response = await fetch('/api/exercises/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
      });

      if (!response.ok) {
        throw new Error('Failed to generate exercise');
      }

      const exercise = await response.json();
      setGenerationProgress('✅ Exercise ready!');
      setTimeout(() => onExerciseGenerated(exercise), 500);
    } catch (error) {
      console.error('Error generating exercise:', error);
      setGenerationProgress('❌ Generation failed');
      setTimeout(() => {
        alert('Failed to generate AI exercise. Make sure Ollama is running with gpt-oss:20b model.');
      }, 1000);
    } finally {
      setTimeout(() => {
        setIsGenerating(false);
        setGenerationProgress('');
      }, 1500);
    }
  };

  const suggestionPrompts = {
    security: [
      'Authentication system with password handling',
      'User input validation and sanitization',
      'API endpoint with potential vulnerabilities',
      'Database query with user input',
      'File upload functionality'
    ],
    performance: [
      'Data processing with nested loops',
      'Database queries in a loop',
      'Memory-intensive operations',
      'Inefficient sorting algorithms',
      'Resource-heavy computations'
    ],
    logic: [
      'Error handling and edge cases',
      'Resource management and cleanup',
      'Conditional logic with complex branches',
      'State management issues',
      'Race condition scenarios'
    ],
    style: [
      'Code organization and structure',
      'Variable naming and conventions',
      'Function complexity and readability',
      'Documentation and comments',
      'Code duplication issues'
    ]
  };

  return (
    <div className="p-6">
      {/* Clean Header */}
      <div className="mb-8">
        <h2 className={`text-2xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>AI Exercise Generator</h2>
        <p className={darkMode ? 'text-gray-400' : 'text-gray-600'}>Generate custom code review exercises using GPT-OSS</p>
      </div>

      {/* Configuration Form */}
      <div className={`rounded-lg p-6 mb-6 ${darkMode ? 'bg-gray-700' : 'bg-gray-50'}`}>
        <h3 className={`text-lg font-semibold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>Exercise Configuration</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div>
          <label className={`block text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            Programming Language
          </label>
          <select
            value={formData.language}
            onChange={(e) => setFormData({...formData, language: e.target.value})}
            className={`w-full p-3 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
              darkMode 
                ? 'bg-gray-600 border-gray-500 text-white' 
                : 'bg-white border-gray-300 text-gray-900'
            }`}
          >
            <option value="javascript">JavaScript</option>
            <option value="python">Python</option>
            <option value="typescript">TypeScript</option>
            <option value="java">Java</option>
            <option value="csharp">C#</option>
          </select>
        </div>

        <div>
          <label className={`block text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            Difficulty Level
          </label>
          <select
            value={formData.difficulty}
            onChange={(e) => setFormData({...formData, difficulty: e.target.value})}
            className={`w-full p-3 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
              darkMode 
                ? 'bg-gray-600 border-gray-500 text-white' 
                : 'bg-white border-gray-300 text-gray-900'
            }`}
          >
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
        </div>

        <div>
          <label className={`block text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            Focus Category
          </label>
          <select
            value={formData.category}
            onChange={(e) => setFormData({...formData, category: e.target.value})}
            className={`w-full p-3 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
              darkMode 
                ? 'bg-gray-600 border-gray-500 text-white' 
                : 'bg-white border-gray-300 text-gray-900'
            }`}
          >
            <option value="security">Security Issues</option>
            <option value="performance">Performance Problems</option>
            <option value="logic">Logic Errors</option>
            <option value="style">Code Style</option>
          </select>
        </div>

        <div className="md:col-span-2">
          <label className={`block text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            Scenario Description
          </label>
          <input
            type="text"
            value={formData.description}
            onChange={(e) => setFormData({...formData, description: e.target.value})}
            placeholder="e.g., Authentication system with password handling"
            className={`w-full p-3 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
              darkMode 
                ? 'bg-gray-600 border-gray-500 text-white placeholder-gray-400' 
                : 'bg-white border-gray-300 text-gray-900 placeholder-gray-500'
            }`}
          />
        </div>
      </div>

        {/* Suggestion chips */}
        <div className="mb-4">
          <label className={`block text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            Quick Suggestions:
          </label>
          <div className="flex flex-wrap gap-2">
            {suggestionPrompts[formData.category as keyof typeof suggestionPrompts]?.map((suggestion, index) => (
              <button
                key={index}
                onClick={() => setFormData({...formData, description: suggestion})}
                className={`px-3 py-1 text-xs rounded-full transition-colors ${
                  darkMode 
                    ? 'bg-blue-900 text-blue-300 hover:bg-blue-800' 
                    : 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                }`}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      </div>

      <button
        onClick={handleGenerate}
        disabled={isGenerating || !formData.description.trim()}
        className={`w-full px-6 py-3 rounded-md font-medium flex items-center justify-center transition-colors ${
          isGenerating || !formData.description.trim()
            ? 'bg-gray-400 cursor-not-allowed'
            : 'bg-blue-600 hover:bg-blue-700'
        } text-white`}
      >
        {isGenerating ? (
          <>
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
            Generating Exercise...
          </>
        ) : (
          'Generate AI Exercise'
        )}
      </button>

      {isGenerating && (
        <div className={`mt-4 p-4 rounded-lg border ${
          darkMode 
            ? 'bg-blue-900 border-blue-700' 
            : 'bg-blue-50 border-blue-200'
        }`}>
          <div className={`text-sm ${darkMode ? 'text-blue-300' : 'text-blue-700'}`}>
            <div className="font-medium mb-1">{generationProgress || 'AI is working...'}</div>
            <div className={`text-xs ${darkMode ? 'text-blue-400' : 'text-blue-600'}`}>
              This may take 10-30 seconds for quality results. AI is creating realistic, educational code examples.
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AIExerciseGenerator;