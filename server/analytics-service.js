const sqlite3 = require('sqlite3').verbose();
const path = require('path');

class AnalyticsService {
  constructor() {
    this.db = new sqlite3.Database(path.join(__dirname, '../devflow.db'));
    this.initializeTables();
  }

  initializeTables() {
    // User sessions and performance tracking
    this.db.run(`
      CREATE TABLE IF NOT EXISTS user_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        session_start DATETIME DEFAULT CURRENT_TIMESTAMP,
        session_end DATETIME,
        exercises_completed INTEGER DEFAULT 0,
        total_score INTEGER DEFAULT 0,
        time_spent INTEGER DEFAULT 0,
        categories_practiced TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Detailed exercise analytics
    this.db.run(`
      CREATE TABLE IF NOT EXISTS exercise_analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        exercise_id TEXT NOT NULL,
        language TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        category TEXT NOT NULL,
        time_to_complete INTEGER,
        issues_found INTEGER,
        issues_correct INTEGER,
        accuracy_score REAL,
        hints_used INTEGER DEFAULT 0,
        completion_status TEXT DEFAULT 'completed',
        user_feedback_rating INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Learning pattern analysis
    this.db.run(`
      CREATE TABLE IF NOT EXISTS learning_patterns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        pattern_type TEXT NOT NULL,
        pattern_data TEXT NOT NULL,
        confidence_score REAL,
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Skill progression tracking
    this.db.run(`
      CREATE TABLE IF NOT EXISTS skill_progression (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        skill_category TEXT NOT NULL,
        previous_level INTEGER,
        current_level INTEGER,
        progression_rate REAL,
        exercises_to_next_level INTEGER,
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `);
  }

  async trackExerciseCompletion(userId, exerciseData) {
    const {
      exerciseId,
      language,
      difficulty,
      category,
      timeToComplete,
      issuesFound,
      issuesCorrect,
      hintsUsed,
      userFeedbackRating
    } = exerciseData;

    const accuracyScore = issuesCorrect > 0 ? (issuesCorrect / Math.max(issuesFound, issuesCorrect)) : 0;

    return new Promise((resolve, reject) => {
      this.db.run(`
        INSERT INTO exercise_analytics (
          user_id, exercise_id, language, difficulty, category,
          time_to_complete, issues_found, issues_correct, accuracy_score,
          hints_used, user_feedback_rating
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `, [
        userId, exerciseId, language, difficulty, category,
        timeToComplete, issuesFound, issuesCorrect, accuracyScore,
        hintsUsed, userFeedbackRating
      ], function(err) {
        if (err) reject(err);
        else resolve(this.lastID);
      });
    });
  }

  async getUserLearningInsights(userId) {
    return new Promise((resolve, reject) => {
      // Get comprehensive user analytics
      const queries = {
        // Overall performance metrics
        overall: `
          SELECT 
            COUNT(*) as total_exercises,
            AVG(accuracy_score) as avg_accuracy,
            AVG(time_to_complete) as avg_time,
            SUM(hints_used) as total_hints_used,
            AVG(user_feedback_rating) as avg_satisfaction
          FROM exercise_analytics 
          WHERE user_id = ? AND created_at >= datetime('now', '-30 days')
        `,
        
        // Performance by category
        byCategory: `
          SELECT 
            category,
            COUNT(*) as exercises_count,
            AVG(accuracy_score) as avg_accuracy,
            AVG(time_to_complete) as avg_time,
            MAX(accuracy_score) as best_score,
            MIN(accuracy_score) as worst_score
          FROM exercise_analytics 
          WHERE user_id = ? AND created_at >= datetime('now', '-30 days')
          GROUP BY category
          ORDER BY avg_accuracy DESC
        `,
        
        // Performance by difficulty
        byDifficulty: `
          SELECT 
            difficulty,
            COUNT(*) as exercises_count,
            AVG(accuracy_score) as avg_accuracy,
            AVG(time_to_complete) as avg_time
          FROM exercise_analytics 
          WHERE user_id = ? AND created_at >= datetime('now', '-30 days')
          GROUP BY difficulty
          ORDER BY 
            CASE difficulty 
              WHEN 'beginner' THEN 1 
              WHEN 'intermediate' THEN 2 
              WHEN 'advanced' THEN 3 
            END
        `,
        
        // Recent progress trend
        progressTrend: `
          SELECT 
            DATE(created_at) as date,
            COUNT(*) as exercises_completed,
            AVG(accuracy_score) as daily_accuracy,
            AVG(time_to_complete) as daily_avg_time
          FROM exercise_analytics 
          WHERE user_id = ? AND created_at >= datetime('now', '-14 days')
          GROUP BY DATE(created_at)
          ORDER BY date DESC
        `,
        
        // Weakness identification
        weaknesses: `
          SELECT 
            category,
            language,
            COUNT(*) as attempts,
            AVG(accuracy_score) as avg_accuracy,
            AVG(hints_used) as avg_hints
          FROM exercise_analytics 
          WHERE user_id = ? AND accuracy_score < 0.7
          GROUP BY category, language
          HAVING attempts >= 2
          ORDER BY avg_accuracy ASC, attempts DESC
          LIMIT 5
        `
      };

      const results = {};
      let completed = 0;
      const total = Object.keys(queries).length;

      Object.entries(queries).forEach(([key, query]) => {
        this.db.all(query, [userId], (err, rows) => {
          if (err) {
            console.error(`Error in ${key} query:`, err);
            results[key] = [];
          } else {
            results[key] = rows;
          }
          
          completed++;
          if (completed === total) {
            resolve(this.processLearningInsights(results));
          }
        });
      });
    });
  }

  processLearningInsights(rawData) {
    const insights = {
      summary: this.generateSummaryInsights(rawData.overall[0]),
      strengths: this.identifyStrengths(rawData.byCategory),
      weaknesses: this.identifyWeaknesses(rawData.byCategory, rawData.weaknesses),
      progressTrend: this.analyzeProgressTrend(rawData.progressTrend),
      recommendations: [],
      nextSteps: []
    };

    // Generate personalized recommendations
    insights.recommendations = this.generateRecommendations(insights, rawData);
    insights.nextSteps = this.generateNextSteps(insights, rawData);

    return insights;
  }

  generateSummaryInsights(overall) {
    if (!overall || overall.total_exercises === 0) {
      return {
        level: 'beginner',
        message: 'Just getting started! Complete a few exercises to see your progress.',
        score: 0
      };
    }

    const accuracy = overall.avg_accuracy || 0;
    const satisfaction = overall.avg_satisfaction || 0;
    
    let level, message;
    if (accuracy >= 0.85) {
      level = 'expert';
      message = 'Excellent code review skills! You consistently identify most issues.';
    } else if (accuracy >= 0.70) {
      level = 'advanced';
      message = 'Strong code review abilities. Focus on catching subtle issues.';
    } else if (accuracy >= 0.50) {
      level = 'intermediate';
      message = 'Good progress! Work on identifying more issue types.';
    } else {
      level = 'beginner';
      message = 'Keep practicing! Focus on common security and logic issues first.';
    }

    return {
      level,
      message,
      score: Math.round(accuracy * 100),
      totalExercises: overall.total_exercises,
      avgTime: Math.round(overall.avg_time || 0),
      satisfaction: Math.round(satisfaction * 10) / 10
    };
  }

  identifyStrengths(categoryData) {
    return categoryData
      .filter(cat => cat.avg_accuracy >= 0.75 && cat.exercises_count >= 3)
      .sort((a, b) => b.avg_accuracy - a.avg_accuracy)
      .slice(0, 3)
      .map(cat => ({
        category: cat.category,
        accuracy: Math.round(cat.avg_accuracy * 100),
        exerciseCount: cat.exercises_count,
        message: `Strong in ${cat.category} - ${Math.round(cat.avg_accuracy * 100)}% accuracy`
      }));
  }

  identifyWeaknesses(categoryData, weaknessData) {
    const weakCategories = categoryData
      .filter(cat => cat.avg_accuracy < 0.60 || cat.exercises_count < 2)
      .sort((a, b) => a.avg_accuracy - b.avg_accuracy)
      .slice(0, 3);

    return weakCategories.map(cat => ({
      category: cat.category,
      accuracy: Math.round(cat.avg_accuracy * 100),
      exerciseCount: cat.exercises_count,
      message: cat.exercises_count < 2 
        ? `Need more practice in ${cat.category}`
        : `Struggling with ${cat.category} - ${Math.round(cat.avg_accuracy * 100)}% accuracy`
    }));
  }

  analyzeProgressTrend(trendData) {
    if (trendData.length < 3) {
      return { trend: 'insufficient_data', message: 'Need more data to analyze trends' };
    }

    const recent = trendData.slice(0, 7); // Last 7 days
    const older = trendData.slice(7, 14); // Previous 7 days

    if (older.length === 0) {
      return { trend: 'new_user', message: 'Just started your learning journey!' };
    }

    const recentAvg = recent.reduce((sum, day) => sum + day.daily_accuracy, 0) / recent.length;
    const olderAvg = older.reduce((sum, day) => sum + day.daily_accuracy, 0) / older.length;

    const improvement = recentAvg - olderAvg;

    if (improvement > 0.1) {
      return { 
        trend: 'improving', 
        message: 'Great progress! Your accuracy is improving.',
        improvement: Math.round(improvement * 100)
      };
    } else if (improvement < -0.1) {
      return { 
        trend: 'declining', 
        message: 'Consider reviewing fundamentals or taking a break.',
        decline: Math.round(Math.abs(improvement) * 100)
      };
    } else {
      return { 
        trend: 'stable', 
        message: 'Consistent performance. Ready for new challenges?'
      };
    }
  }

  generateRecommendations(insights, rawData) {
    const recommendations = [];

    // Based on weaknesses
    if (insights.weaknesses.length > 0) {
      const weakest = insights.weaknesses[0];
      recommendations.push({
        type: 'skill_focus',
        priority: 'high',
        message: `Focus on ${weakest.category} exercises to improve your weakest area`,
        action: `Practice 3-5 ${weakest.category} exercises this week`
      });
    }

    // Based on progress trend
    if (insights.progressTrend.trend === 'improving') {
      recommendations.push({
        type: 'difficulty_increase',
        priority: 'medium',
        message: 'You\'re improving! Try more advanced exercises',
        action: 'Attempt intermediate or advanced level exercises'
      });
    }

    // Based on time spent
    const overall = rawData.overall[0];
    if (overall && overall.avg_time > 300) { // More than 5 minutes average
      recommendations.push({
        type: 'speed_improvement',
        priority: 'medium',
        message: 'Work on identifying issues more quickly',
        action: 'Set a 3-minute timer for beginner exercises'
      });
    }

    return recommendations;
  }

  generateNextSteps(insights, rawData) {
    const steps = [];

    // Immediate next step based on level
    switch (insights.summary.level) {
      case 'beginner':
        steps.push('Complete 5 security exercises to build foundation');
        steps.push('Focus on obvious issues like SQL injection and XSS');
        break;
      case 'intermediate':
        steps.push('Practice performance optimization exercises');
        steps.push('Learn to identify subtle logic errors');
        break;
      case 'advanced':
        steps.push('Master advanced security vulnerabilities');
        steps.push('Practice complex architectural issues');
        break;
      case 'expert':
        steps.push('Mentor others and create custom exercises');
        steps.push('Explore cutting-edge security patterns');
        break;
    }

    // Add weakness-specific steps
    if (insights.weaknesses.length > 0) {
      steps.push(`Dedicate 30 minutes daily to ${insights.weaknesses[0].category} practice`);
    }

    return steps.slice(0, 3); // Return top 3 steps
  }

  async getGlobalBenchmarks() {
    return new Promise((resolve, reject) => {
      this.db.all(`
        SELECT 
          category,
          difficulty,
          AVG(accuracy_score) as avg_accuracy,
          AVG(time_to_complete) as avg_time,
          COUNT(*) as sample_size
        FROM exercise_analytics 
        WHERE created_at >= datetime('now', '-30 days')
        GROUP BY category, difficulty
        HAVING sample_size >= 10
        ORDER BY category, difficulty
      `, [], (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });
  }
}

module.exports = AnalyticsService;