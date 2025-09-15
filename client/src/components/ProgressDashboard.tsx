import React, { useState, useEffect } from 'react';

interface SkillProgress {
  skill_category: string;
  accuracy_score: number;
  exercises_completed: number;
}

interface RecentAttempt {
  id: number;
  exercise_title: string;
  score: number;
  completed_at: string;
  time_spent: number;
}

interface ProgressDashboardProps {
  darkMode?: boolean;
}

const ProgressDashboard: React.FC<ProgressDashboardProps> = ({ darkMode = false }) => {
  const [skillProgress, setSkillProgress] = useState<SkillProgress[]>([]);
  const [recentAttempts, setRecentAttempts] = useState<RecentAttempt[]>([]);
  const [overallStats, setOverallStats] = useState({
    totalExercises: 0,
    averageScore: 0,
    totalTimeSpent: 0,
    streak: 0
  });

  useEffect(() => {
    // Mock data for demonstration
    setSkillProgress([
      { skill_category: 'security', accuracy_score: 85, exercises_completed: 12 },
      { skill_category: 'performance', accuracy_score: 72, exercises_completed: 8 },
      { skill_category: 'logic', accuracy_score: 90, exercises_completed: 15 },
      { skill_category: 'style', accuracy_score: 68, exercises_completed: 6 }
    ]);

    setRecentAttempts([
      { id: 1, exercise_title: 'User Authentication Function', score: 85, completed_at: '2024-01-15T10:30:00Z', time_spent: 420 },
      { id: 2, exercise_title: 'Data Processing Function', score: 72, completed_at: '2024-01-14T15:45:00Z', time_spent: 380 },
      { id: 3, exercise_title: 'File Processing Script', score: 90, completed_at: '2024-01-13T09:15:00Z', time_spent: 290 }
    ]);

    setOverallStats({
      totalExercises: 41,
      averageScore: 79,
      totalTimeSpent: 18420, // in seconds
      streak: 7
    });
  }, []);

  const getSkillColor = (category: string) => {
    switch (category) {
      case 'security': return 'bg-red-500';
      case 'performance': return 'bg-blue-500';
      case 'logic': return 'bg-orange-500';
      case 'style': return 'bg-purple-500';
      default: return 'bg-gray-500';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="mb-8">
        <h2 className={`text-2xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>Progress Dashboard</h2>
        <p className={darkMode ? 'text-gray-400' : 'text-gray-600'}>Track your code review skills development and see how you're improving over time.</p>
      </div>

      {/* Overall Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className={`p-6 rounded-lg shadow border text-center ${darkMode ? 'bg-gray-700 border-gray-600' : 'bg-white border-gray-200'}`}>
          <div className="text-3xl font-bold text-blue-600 mb-2">{overallStats.totalExercises}</div>
          <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Exercises Completed</div>
        </div>
        <div className={`p-6 rounded-lg shadow border text-center ${darkMode ? 'bg-gray-700 border-gray-600' : 'bg-white border-gray-200'}`}>
          <div className="text-3xl font-bold text-green-600 mb-2">{overallStats.averageScore}%</div>
          <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Average Score</div>
        </div>
        <div className={`p-6 rounded-lg shadow border text-center ${darkMode ? 'bg-gray-700 border-gray-600' : 'bg-white border-gray-200'}`}>
          <div className="text-3xl font-bold text-purple-600 mb-2">{formatTime(overallStats.totalTimeSpent)}</div>
          <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Total Time Spent</div>
        </div>
        <div className={`p-6 rounded-lg shadow border text-center ${darkMode ? 'bg-gray-700 border-gray-600' : 'bg-white border-gray-200'}`}>
          <div className="text-3xl font-bold text-orange-600 mb-2">{overallStats.streak}</div>
          <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Day Streak</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Skill Progress */}
        <div className={`p-6 rounded-lg shadow border ${darkMode ? 'bg-gray-700 border-gray-600' : 'bg-white border-gray-200'}`}>
          <h3 className={`text-lg font-semibold mb-4 ${darkMode ? 'text-white' : 'text-gray-800'}`}>Skill Breakdown</h3>
          <div className="space-y-4">
            {skillProgress.map((skill) => (
              <div key={skill.skill_category}>
                <div className="flex justify-between items-center mb-2">
                  <div className="flex items-center space-x-2">
                    <div className={`w-3 h-3 rounded-full ${getSkillColor(skill.skill_category)}`}></div>
                    <span className="font-medium capitalize">{skill.skill_category}</span>
                  </div>
                  <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    {skill.accuracy_score}% • {skill.exercises_completed} exercises
                  </div>
                </div>
                <div className={`w-full rounded-full h-2 ${darkMode ? 'bg-gray-600' : 'bg-gray-200'}`}>
                  <div
                    className={`h-2 rounded-full ${getSkillColor(skill.skill_category)}`}
                    style={{ width: `${skill.accuracy_score}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-white p-6 rounded-lg shadow border">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Recent Activity</h3>
          <div className="space-y-3">
            {recentAttempts.map((attempt) => (
              <div key={attempt.id} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <div className="flex-1">
                  <div className="font-medium text-gray-800 text-sm">{attempt.exercise_title}</div>
                  <div className="text-xs text-gray-500">{formatDate(attempt.completed_at)}</div>
                </div>
                <div className="text-right">
                  <div className={`font-bold ${getScoreColor(attempt.score)}`}>
                    {attempt.score}%
                  </div>
                  <div className="text-xs text-gray-500">{formatTime(attempt.time_spent)}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Achievements */}
      <div className="bg-white p-6 rounded-lg shadow border">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Achievements</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-center space-x-3 p-4 bg-yellow-50 rounded-lg border border-yellow-200">
            <div className="w-8 h-8 bg-yellow-500 rounded-full flex items-center justify-center">
              <span className="text-white text-sm font-bold">S</span>
            </div>
            <div>
              <div className="font-medium text-yellow-800">Security Expert</div>
              <div className="text-sm text-yellow-600">Found 50+ security issues</div>
            </div>
          </div>
          <div className="flex items-center space-x-3 p-4 bg-blue-50 rounded-lg border border-blue-200">
            <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
              <span className="text-white text-sm font-bold">F</span>
            </div>
            <div>
              <div className="font-medium text-blue-800">Speed Reviewer</div>
              <div className="text-sm text-blue-600">Completed review in under 5 minutes</div>
            </div>
          </div>
          <div className="flex items-center space-x-3 p-4 bg-green-50 rounded-lg border border-green-200">
            <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
              <span className="text-white text-sm font-bold">P</span>
            </div>
            <div>
              <div className="font-medium text-green-800">Perfect Score</div>
              <div className="text-sm text-green-600">Achieved 100% on 5 exercises</div>
            </div>
          </div>
        </div>
      </div>

      {/* Learning Recommendations */}
      <div className="bg-white p-6 rounded-lg shadow-md">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Recommended Focus Areas</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between p-4 bg-purple-50 rounded-lg border border-purple-200">
            <div>
              <div className="font-medium text-purple-800">Code Style Reviews</div>
              <div className="text-sm text-purple-600">Your weakest area - practice more style-focused exercises</div>
            </div>
            <button className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors text-sm">
              Practice Now
            </button>
          </div>
          <div className="flex items-center justify-between p-4 bg-blue-50 rounded-lg border border-blue-200">
            <div>
              <div className="font-medium text-blue-800">Performance Optimization</div>
              <div className="text-sm text-blue-600">Good progress - try advanced performance exercises</div>
            </div>
            <button className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm">
              Level Up
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProgressDashboard;