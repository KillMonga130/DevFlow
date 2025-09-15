import React, { useState } from 'react';

interface Exercise {
  id: number;
  language: string;
  difficulty: string;
  category: string;
  title: string;
  description: string;
  code_content: string;
  issues: any[];
}

interface ExerciseListProps {
  exercises: Exercise[];
  onExerciseSelect: (exercise: Exercise) => void;
}

const ExerciseList: React.FC<ExerciseListProps> = ({ exercises, onExerciseSelect }) => {
  const [filters, setFilters] = useState({
    language: '',
    difficulty: '',
    category: ''
  });

  const filteredExercises = exercises.filter(exercise => {
    return (
      (!filters.language || exercise.language === filters.language) &&
      (!filters.difficulty || exercise.difficulty === filters.difficulty) &&
      (!filters.category || exercise.category === filters.category)
    );
  });

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'beginner': return 'bg-green-100 text-green-800';
      case 'intermediate': return 'bg-yellow-100 text-yellow-800';
      case 'advanced': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'security': return 'bg-red-100 text-red-800';
      case 'performance': return 'bg-blue-100 text-blue-800';
      case 'style': return 'bg-purple-100 text-purple-800';
      case 'logic': return 'bg-orange-100 text-orange-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h2 className="text-2xl font-bold mb-4 text-gray-800">Code Review Exercises</h2>
        <p className="text-gray-600 mb-6">
          Practice your code review skills by identifying issues in real-world code examples.
          Each exercise contains intentional bugs, security vulnerabilities, or performance problems.
        </p>
        
        {/* Filters */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Language
            </label>
            <select
              value={filters.language}
              onChange={(e) => setFilters({...filters, language: e.target.value})}
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Languages</option>
              <option value="javascript">JavaScript</option>
              <option value="python">Python</option>
              <option value="typescript">TypeScript</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Difficulty
            </label>
            <select
              value={filters.difficulty}
              onChange={(e) => setFilters({...filters, difficulty: e.target.value})}
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Levels</option>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Category
            </label>
            <select
              value={filters.category}
              onChange={(e) => setFilters({...filters, category: e.target.value})}
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Categories</option>
              <option value="security">Security</option>
              <option value="performance">Performance</option>
              <option value="style">Code Style</option>
              <option value="logic">Logic</option>
            </select>
          </div>
        </div>
      </div>

      {/* Exercise Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredExercises.map(exercise => (
          <div
            key={exercise.id}
            className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow cursor-pointer"
            onClick={() => onExerciseSelect(exercise)}
          >
            <div className="p-6">
              <div className="flex justify-between items-start mb-3">
                <h3 className="text-lg font-semibold text-gray-800 line-clamp-2">
                  {exercise.title}
                </h3>
                <span className="text-xs font-medium px-2 py-1 rounded-full bg-gray-100 text-gray-600 uppercase tracking-wide">
                  {exercise.language}
                </span>
              </div>
              
              <p className="text-gray-600 text-sm mb-4 line-clamp-3">
                {exercise.description}
              </p>
              
              <div className="flex flex-wrap gap-2 mb-4">
                <span className={`text-xs font-medium px-2 py-1 rounded-full ${getDifficultyColor(exercise.difficulty)}`}>
                  {exercise.difficulty}
                </span>
                <span className={`text-xs font-medium px-2 py-1 rounded-full ${getCategoryColor(exercise.category)}`}>
                  {exercise.category}
                </span>
              </div>
              
              <div className="flex justify-between items-center text-sm text-gray-500">
                <span>{exercise.issues.length} issues to find</span>
                <span className="text-blue-600 hover:text-blue-800 font-medium">
                  Start Review →
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {filteredExercises.length === 0 && (
        <div className="text-center py-12">
          <div className="text-gray-500 text-lg">No exercises match your current filters</div>
          <button
            onClick={() => setFilters({ language: '', difficulty: '', category: '' })}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            Clear Filters
          </button>
        </div>
      )}
    </div>
  );
};

export default ExerciseList;