import React, { useState, useEffect } from 'react';
import { Trophy, Target, TrendingUp, Star, Zap } from 'lucide-react';

const ProgressTracker = ({ userId }) => {
  const [userStats, setUserStats] = useState({
    totalExercises: 0,
    averageScore: 0,
    streak: 0,
    skillLevels: {
      security: 0,
      performance: 0,
      logic: 0,
      style: 0,
      maintainability: 0
    },
    badges: [],
    weeklyGoal: 5,
    weeklyProgress: 0
  });

  const [achievements, setAchievements] = useState([]);

  useEffect(() => {
    fetchUserProgress();
  }, [userId]);

  const fetchUserProgress = async () => {
    try {
      const response = await fetch(`/api/users/${userId}/progress`);
      const data = await response.json();
      setUserStats(data.stats);
      setAchievements(data.recentAchievements || []);
    } catch (error) {
      console.error('Error fetching progress:', error);
    }
  };

  const getSkillColor = (level) => {
    if (level >= 80) return 'text-green-600 bg-green-100';
    if (level >= 60) return 'text-blue-600 bg-blue-100';
    if (level >= 40) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getStreakEmoji = (streak) => {
    if (streak >= 30) return '🔥';
    if (streak >= 14) return '⚡';
    if (streak >= 7) return '💪';
    return '🎯';
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800">Your Progress</h2>
        <div className="flex items-center space-x-2 text-orange-600">
          <Zap className="w-5 h-5" />
          <span className="font-semibold">{userStats.streak} day streak {getStreakEmoji(userStats.streak)}</span>
        </div>
      </div>

      {/* Weekly Goal Progress */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Weekly Goal</span>
          <span className="text-sm text-gray-600">{userStats.weeklyProgress}/{userStats.weeklyGoal}</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className="bg-gradient-to-r from-blue-500 to-indigo-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${Math.min((userStats.weeklyProgress / userStats.weeklyGoal) * 100, 100)}%` }}
          ></div>
        </div>
      </div>

      {/* Overall Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-600">{userStats.totalExercises}</div>
          <div className="text-sm text-gray-600">Exercises</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-green-600">{userStats.averageScore}%</div>
          <div className="text-sm text-gray-600">Avg Score</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-purple-600">{userStats.badges.length}</div>
          <div className="text-sm text-gray-600">Badges</div>
        </div>
      </div>

      {/* Skill Levels */}
      <div>
        <h3 className="text-lg font-semibold text-gray-800 mb-3 flex items-center">
          <Target className="w-5 h-5 mr-2" />
          Skill Levels
        </h3>
        <div className="space-y-3">
          {Object.entries(userStats.skillLevels).map(([skill, level]) => (
            <div key={skill} className="flex items-center justify-between">
              <span className="capitalize text-sm font-medium text-gray-700">{skill}</span>
              <div className="flex items-center space-x-2">
                <div className="w-24 bg-gray-200 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full transition-all duration-300 ${
                      level >= 80 ? 'bg-green-500' : 
                      level >= 60 ? 'bg-blue-500' : 
                      level >= 40 ? 'bg-yellow-500' : 'bg-red-500'
                    }`}
                    style={{ width: `${level}%` }}
                  ></div>
                </div>
                <span className={`text-xs px-2 py-1 rounded-full ${getSkillColor(level)}`}>
                  {level}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Achievements */}
      {achievements.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-800 mb-3 flex items-center">
            <Trophy className="w-5 h-5 mr-2 text-yellow-500" />
            Recent Achievements
          </h3>
          <div className="space-y-2">
            {achievements.slice(0, 3).map((achievement, index) => (
              <div key={index} className="flex items-center space-x-3 p-2 bg-yellow-50 rounded-lg">
                <Star className="w-4 h-4 text-yellow-500" />
                <div>
                  <div className="text-sm font-medium text-gray-800">{achievement.title}</div>
                  <div className="text-xs text-gray-600">{achievement.description}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Next Milestone */}
      <div className="bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-4">
        <h4 className="font-semibold text-gray-800 mb-2 flex items-center">
          <TrendingUp className="w-4 h-4 mr-2" />
          Next Milestone
        </h4>
        <p className="text-sm text-gray-600">
          Complete 2 more exercises to unlock the "Security Specialist" badge!
        </p>
      </div>
    </div>
  );
};

export default ProgressTracker;