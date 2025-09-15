import { useState, useEffect } from 'react';
import './App.css';
import { ExerciseList, CodeReviewInterface, ProgressDashboard } from './components';
import AIExerciseGenerator from './components/AIExerciseGenerator';
import AICodeAnalyzer from './components/AICodeAnalyzer';

interface Exercise {
  id: number;
  language: string;
  difficulty: string;
  category: string;
  title: string;
  description: string;
  code_content: string;
  issues: Issue[];
}

interface Issue {
  line: number;
  type: string;
  severity: string;
  title: string;
  description: string;
  suggestion: string;
}

type View = 'exercises' | 'review' | 'progress' | 'ai-generator' | 'ai-analyzer';

function App() {
  const [currentView, setCurrentView] = useState<View>('exercises');
  const [selectedExercise, setSelectedExercise] = useState<Exercise | null>(null);
  const [exercises, setExercises] = useState<Exercise[]>([]);
  const [loading, setLoading] = useState(true);
  const [aiStatus, setAiStatus] = useState<{available: boolean, model: string}>({available: false, model: 'checking...'});
  const [darkMode, setDarkMode] = useState(false);

  useEffect(() => {
    fetchExercises();
    checkAIStatus();
  }, []);

  const fetchExercises = async () => {
    try {
      const response = await fetch('/api/exercises');
      const data = await response.json();
      setExercises(data);
    } catch (error) {
      console.error('Error fetching exercises:', error);
    } finally {
      setLoading(false);
    }
  };

  const checkAIStatus = async () => {
    try {
      const response = await fetch('/api/health');
      const data = await response.json();
      setAiStatus({
        available: data.ai_powered || false,
        model: data.model || 'Not available'
      });
    } catch (error) {
      console.error('Error checking AI status:', error);
      setAiStatus({available: false, model: 'Connection error'});
    }
  };

  const handleAIExerciseGenerated = (exercise: Exercise) => {
    setExercises([exercise, ...exercises]);
    setCurrentView('exercises');
    // Optionally auto-select the new exercise
    setSelectedExercise(exercise);
    setCurrentView('review');
  };

  const handleExerciseSelect = (exercise: Exercise) => {
    setSelectedExercise(exercise);
    setCurrentView('review');
  };

  const handleBackToExercises = () => {
    setCurrentView('exercises');
    setSelectedExercise(null);
  };

  const renderNavigation = () => (
    <nav className={`border-b shadow-sm ${darkMode ? 'bg-gray-900 border-gray-700' : 'bg-white border-gray-200'}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo & Branding */}
          <div className="flex items-center space-x-8">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">DF</span>
              </div>
              <div>
                <h1 className={`text-xl font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>DevFlow</h1>
              </div>
            </div>
            
            {/* Status Indicator */}
            <div className="hidden md:flex items-center space-x-2">
              <div className={`flex items-center space-x-2 px-3 py-1 rounded-md text-sm ${
                aiStatus.available 
                  ? darkMode 
                    ? 'bg-green-900 text-green-300 border border-green-700' 
                    : 'bg-green-50 text-green-700 border border-green-200'
                  : darkMode 
                    ? 'bg-red-900 text-red-300 border border-red-700' 
                    : 'bg-red-50 text-red-700 border border-red-200'
              }`}>
                <div className={`w-2 h-2 rounded-full ${aiStatus.available ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span>{aiStatus.available ? 'AI Ready' : 'AI Offline'}</span>
              </div>
            </div>
          </div>

          {/* Navigation */}
          <div className="flex items-center space-x-1">
            {[
              { id: 'exercises', label: 'Exercises' },
              { id: 'ai-generator', label: 'AI Generator' },
              { id: 'ai-analyzer', label: 'AI Analyzer' },
              { id: 'progress', label: 'Progress' }
            ].map((item) => (
              <button
                key={item.id}
                onClick={() => setCurrentView(item.id as View)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  currentView === item.id
                    ? darkMode 
                      ? 'bg-blue-900 text-blue-300' 
                      : 'bg-blue-100 text-blue-700'
                    : darkMode 
                      ? 'text-gray-400 hover:text-gray-200 hover:bg-gray-800' 
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                }`}
              >
                {item.label}
              </button>
            ))}
          </div>

          {/* User Profile & Dark Mode Toggle */}
          <div className="flex items-center space-x-3">
            {/* Dark Mode Toggle */}
            <button
              onClick={() => setDarkMode(!darkMode)}
              className={`p-2 rounded-md transition-colors ${
                darkMode 
                  ? 'text-gray-400 hover:text-gray-200 hover:bg-gray-800' 
                  : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
              }`}
              title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            >
              {darkMode ? (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                </svg>
              )}
            </button>
            
            <div className="hidden md:block text-right">
              <div className={`text-sm font-medium ${darkMode ? 'text-white' : 'text-gray-900'}`}>Alex Chen</div>
              <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>Senior Developer</div>
            </div>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${darkMode ? 'bg-gray-700' : 'bg-gray-300'}`}>
              <span className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>AC</span>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );

  const renderContent = () => {
    if (loading) {
      return (
        <div className="flex justify-center items-center h-64">
          <div className="text-xl text-gray-600">Loading exercises...</div>
        </div>
      );
    }

    switch (currentView) {
      case 'exercises':
        return (
          <ExerciseList 
            exercises={exercises} 
            onExerciseSelect={handleExerciseSelect}
          />
        );
      case 'review':
        return selectedExercise ? (
          <CodeReviewInterface 
            exercise={selectedExercise}
            onBack={handleBackToExercises}
          />
        ) : (
          <div className="text-center text-gray-600">No exercise selected</div>
        );
      case 'ai-generator':
        return <AIExerciseGenerator onExerciseGenerated={handleAIExerciseGenerated} darkMode={darkMode} />;
      case 'ai-analyzer':
        return <AICodeAnalyzer />;
      case 'progress':
        return <ProgressDashboard darkMode={darkMode} />;
      default:
        return <div>Unknown view</div>;
    }
  };

  return (
    <div className={`min-h-screen ${darkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
      {renderNavigation()}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <div className={`rounded-lg shadow overflow-hidden ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          {renderContent()}
        </div>
      </main>

      {/* Clean Footer */}
      <footer className={`border-t mt-16 ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className={`flex items-center space-x-4 text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${aiStatus.available ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span>AI Status: {aiStatus.available ? 'Active' : 'Offline'}</span>
              </div>
              <div>Powered by GPT-OSS & Kiro</div>
            </div>
            <div className={`text-sm mt-4 md:mt-0 ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
              © 2025 DevFlow - Code Review Training Platform
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;