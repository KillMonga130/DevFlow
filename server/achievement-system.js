class AchievementSystem {
  constructor(db) {
    this.db = db;
    this.achievements = this.defineAchievements();
    this.initializeTables();
  }

  initializeTables() {
    this.db.run(`
      CREATE TABLE IF NOT EXISTS user_achievements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        achievement_id TEXT NOT NULL,
        earned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        progress INTEGER DEFAULT 0,
        completed BOOLEAN DEFAULT FALSE,
        UNIQUE(user_id, achievement_id)
      )
    `);

    this.db.run(`
      CREATE TABLE IF NOT EXISTS user_badges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        badge_id TEXT NOT NULL,
        badge_name TEXT NOT NULL,
        badge_description TEXT,
        earned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        rarity TEXT DEFAULT 'common'
      )
    `);
  }

  defineAchievements() {
    return {
      // Completion-based achievements
      first_steps: {
        id: 'first_steps',
        name: 'First Steps',
        description: 'Complete your first code review exercise',
        icon: '🎯',
        type: 'milestone',
        requirement: { exercises_completed: 1 },
        points: 10,
        rarity: 'common'
      },
      
      getting_started: {
        id: 'getting_started',
        name: 'Getting Started',
        description: 'Complete 5 code review exercises',
        icon: '🚀',
        type: 'milestone',
        requirement: { exercises_completed: 5 },
        points: 25,
        rarity: 'common'
      },

      dedicated_learner: {
        id: 'dedicated_learner',
        name: 'Dedicated Learner',
        description: 'Complete 25 exercises',
        icon: '📚',
        type: 'milestone',
        requirement: { exercises_completed: 25 },
        points: 100,
        rarity: 'uncommon'
      },

      code_review_master: {
        id: 'code_review_master',
        name: 'Code Review Master',
        description: 'Complete 100 exercises',
        icon: '👑',
        type: 'milestone',
        requirement: { exercises_completed: 100 },
        points: 500,
        rarity: 'rare'
      },

      // Accuracy-based achievements
      sharp_eye: {
        id: 'sharp_eye',
        name: 'Sharp Eye',
        description: 'Achieve 90% accuracy on 5 consecutive exercises',
        icon: '👁️',
        type: 'skill',
        requirement: { consecutive_high_accuracy: 5, accuracy_threshold: 0.9 },
        points: 75,
        rarity: 'uncommon'
      },

      perfectionist: {
        id: 'perfectionist',
        name: 'Perfectionist',
        description: 'Achieve 100% accuracy on an exercise',
        icon: '💎',
        type: 'skill',
        requirement: { perfect_score: 1 },
        points: 50,
        rarity: 'uncommon'
      },

      // Speed-based achievements
      speed_demon: {
        id: 'speed_demon',
        name: 'Speed Demon',
        description: 'Complete an exercise in under 60 seconds',
        icon: '⚡',
        type: 'speed',
        requirement: { time_under: 60 },
        points: 30,
        rarity: 'uncommon'
      },

      lightning_fast: {
        id: 'lightning_fast',
        name: 'Lightning Fast',
        description: 'Complete 10 exercises in under 2 minutes each',
        icon: '🏃‍♂️',
        type: 'speed',
        requirement: { fast_completions: 10, time_threshold: 120 },
        points: 100,
        rarity: 'rare'
      },

      // Category-specific achievements
      security_specialist: {
        id: 'security_specialist',
        name: 'Security Specialist',
        description: 'Complete 15 security exercises with 80%+ accuracy',
        icon: '🔒',
        type: 'category',
        requirement: { category: 'security', exercises: 15, accuracy: 0.8 },
        points: 150,
        rarity: 'rare'
      },

      performance_guru: {
        id: 'performance_guru',
        name: 'Performance Guru',
        description: 'Complete 15 performance exercises with 80%+ accuracy',
        icon: '🚀',
        type: 'category',
        requirement: { category: 'performance', exercises: 15, accuracy: 0.8 },
        points: 150,
        rarity: 'rare'
      },

      logic_master: {
        id: 'logic_master',
        name: 'Logic Master',
        description: 'Complete 15 logic exercises with 80%+ accuracy',
        icon: '🧠',
        type: 'category',
        requirement: { category: 'logic', exercises: 15, accuracy: 0.8 },
        points: 150,
        rarity: 'rare'
      },

      // Streak-based achievements
      consistent_learner: {
        id: 'consistent_learner',
        name: 'Consistent Learner',
        description: 'Practice for 7 days in a row',
        icon: '🔥',
        type: 'streak',
        requirement: { daily_streak: 7 },
        points: 100,
        rarity: 'uncommon'
      },

      unstoppable: {
        id: 'unstoppable',
        name: 'Unstoppable',
        description: 'Practice for 30 days in a row',
        icon: '🌟',
        type: 'streak',
        requirement: { daily_streak: 30 },
        points: 500,
        rarity: 'legendary'
      },

      // Special achievements
      night_owl: {
        id: 'night_owl',
        name: 'Night Owl',
        description: 'Complete 10 exercises between 10 PM and 6 AM',
        icon: '🦉',
        type: 'special',
        requirement: { night_exercises: 10 },
        points: 50,
        rarity: 'uncommon'
      },

      early_bird: {
        id: 'early_bird',
        name: 'Early Bird',
        description: 'Complete 10 exercises between 5 AM and 9 AM',
        icon: '🐦',
        type: 'special',
        requirement: { morning_exercises: 10 },
        points: 50,
        rarity: 'uncommon'
      },

      polyglot: {
        id: 'polyglot',
        name: 'Polyglot',
        description: 'Complete exercises in 5 different programming languages',
        icon: '🌍',
        type: 'special',
        requirement: { languages: 5 },
        points: 200,
        rarity: 'rare'
      }
    };
  }

  async checkAchievements(userId, exerciseData) {
    const newAchievements = [];
    
    // Get user's current stats
    const userStats = await this.getUserStats(userId);
    
    // Check each achievement
    for (const [achievementId, achievement] of Object.entries(this.achievements)) {
      const hasAchievement = await this.userHasAchievement(userId, achievementId);
      
      if (!hasAchievement && await this.meetsRequirement(userId, achievement, userStats, exerciseData)) {
        await this.awardAchievement(userId, achievement);
        newAchievements.push(achievement);
      }
    }

    return newAchievements;
  }

  async getUserStats(userId) {
    return new Promise((resolve, reject) => {
      const queries = {
        // Basic completion stats
        basic: `
          SELECT 
            COUNT(*) as total_exercises,
            AVG(accuracy_score) as avg_accuracy,
            AVG(time_to_complete) as avg_time,
            MAX(accuracy_score) as best_accuracy,
            MIN(time_to_complete) as fastest_time
          FROM exercise_analytics 
          WHERE user_id = ?
        `,
        
        // Category-specific stats
        categories: `
          SELECT 
            category,
            COUNT(*) as count,
            AVG(accuracy_score) as avg_accuracy
          FROM exercise_analytics 
          WHERE user_id = ?
          GROUP BY category
        `,
        
        // Language diversity
        languages: `
          SELECT COUNT(DISTINCT language) as language_count
          FROM exercise_analytics 
          WHERE user_id = ?
        `,
        
        // Recent streak and timing
        recent: `
          SELECT 
            DATE(created_at) as date,
            COUNT(*) as daily_count,
            strftime('%H', created_at) as hour
          FROM exercise_analytics 
          WHERE user_id = ? AND created_at >= datetime('now', '-30 days')
          GROUP BY DATE(created_at)
          ORDER BY date DESC
        `,
        
        // Consecutive high accuracy
        consecutive: `
          SELECT accuracy_score, created_at
          FROM exercise_analytics 
          WHERE user_id = ?
          ORDER BY created_at DESC
          LIMIT 10
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
            resolve(this.processUserStats(results));
          }
        });
      });
    });
  }

  processUserStats(rawStats) {
    const basic = rawStats.basic[0] || {};
    const categories = rawStats.categories || [];
    const languages = rawStats.languages[0] || {};
    const recent = rawStats.recent || [];
    const consecutive = rawStats.consecutive || [];

    // Calculate streak
    let currentStreak = 0;
    const today = new Date().toISOString().split('T')[0];
    let checkDate = new Date();
    
    for (const day of recent) {
      const dayStr = checkDate.toISOString().split('T')[0];
      if (day.date === dayStr) {
        currentStreak++;
        checkDate.setDate(checkDate.getDate() - 1);
      } else {
        break;
      }
    }

    // Calculate consecutive high accuracy
    let consecutiveHighAccuracy = 0;
    for (const exercise of consecutive) {
      if (exercise.accuracy_score >= 0.9) {
        consecutiveHighAccuracy++;
      } else {
        break;
      }
    }

    // Time-based stats
    const nightExercises = recent.filter(r => {
      const hour = parseInt(r.hour);
      return hour >= 22 || hour <= 6;
    }).length;

    const morningExercises = recent.filter(r => {
      const hour = parseInt(r.hour);
      return hour >= 5 && hour <= 9;
    }).length;

    return {
      totalExercises: basic.total_exercises || 0,
      avgAccuracy: basic.avg_accuracy || 0,
      avgTime: basic.avg_time || 0,
      bestAccuracy: basic.best_accuracy || 0,
      fastestTime: basic.fastest_time || 999999,
      categories: categories.reduce((acc, cat) => {
        acc[cat.category] = {
          count: cat.count,
          avgAccuracy: cat.avg_accuracy
        };
        return acc;
      }, {}),
      languageCount: languages.language_count || 0,
      currentStreak,
      consecutiveHighAccuracy,
      nightExercises,
      morningExercises,
      hasPerfectScore: basic.best_accuracy === 1.0
    };
  }

  async meetsRequirement(userId, achievement, userStats, exerciseData) {
    const req = achievement.requirement;

    switch (achievement.type) {
      case 'milestone':
        return userStats.totalExercises >= req.exercises_completed;

      case 'skill':
        if (req.consecutive_high_accuracy) {
          return userStats.consecutiveHighAccuracy >= req.consecutive_high_accuracy;
        }
        if (req.perfect_score) {
          return userStats.hasPerfectScore;
        }
        break;

      case 'speed':
        if (req.time_under) {
          return exerciseData.timeToComplete <= req.time_under;
        }
        if (req.fast_completions) {
          // Check if user has enough fast completions
          return await this.countFastCompletions(userId, req.time_threshold) >= req.fast_completions;
        }
        break;

      case 'category':
        const categoryStats = userStats.categories[req.category];
        return categoryStats && 
               categoryStats.count >= req.exercises && 
               categoryStats.avgAccuracy >= req.accuracy;

      case 'streak':
        return userStats.currentStreak >= req.daily_streak;

      case 'special':
        if (req.night_exercises) {
          return userStats.nightExercises >= req.night_exercises;
        }
        if (req.morning_exercises) {
          return userStats.morningExercises >= req.morning_exercises;
        }
        if (req.languages) {
          return userStats.languageCount >= req.languages;
        }
        break;
    }

    return false;
  }

  async countFastCompletions(userId, timeThreshold) {
    return new Promise((resolve, reject) => {
      this.db.get(`
        SELECT COUNT(*) as count
        FROM exercise_analytics 
        WHERE user_id = ? AND time_to_complete <= ?
      `, [userId, timeThreshold], (err, row) => {
        if (err) reject(err);
        else resolve(row.count || 0);
      });
    });
  }

  async userHasAchievement(userId, achievementId) {
    return new Promise((resolve, reject) => {
      this.db.get(`
        SELECT completed FROM user_achievements 
        WHERE user_id = ? AND achievement_id = ? AND completed = TRUE
      `, [userId, achievementId], (err, row) => {
        if (err) reject(err);
        else resolve(!!row);
      });
    });
  }

  async awardAchievement(userId, achievement) {
    return new Promise((resolve, reject) => {
      this.db.run(`
        INSERT OR REPLACE INTO user_achievements 
        (user_id, achievement_id, completed, progress) 
        VALUES (?, ?, TRUE, 100)
      `, [userId, achievement.id], function(err) {
        if (err) {
          reject(err);
        } else {
          // Also add to badges table for display
          this.db.run(`
            INSERT INTO user_badges 
            (user_id, badge_id, badge_name, badge_description, rarity) 
            VALUES (?, ?, ?, ?, ?)
          `, [userId, achievement.id, achievement.name, achievement.description, achievement.rarity]);
          
          resolve(this.lastID);
        }
      });
    });
  }

  async getUserAchievements(userId) {
    return new Promise((resolve, reject) => {
      this.db.all(`
        SELECT 
          ua.*,
          ub.badge_name,
          ub.badge_description,
          ub.rarity,
          ub.earned_at
        FROM user_achievements ua
        LEFT JOIN user_badges ub ON ua.user_id = ub.user_id AND ua.achievement_id = ub.badge_id
        WHERE ua.user_id = ? AND ua.completed = TRUE
        ORDER BY ua.earned_at DESC
      `, [userId], (err, rows) => {
        if (err) reject(err);
        else {
          const achievements = rows.map(row => ({
            ...this.achievements[row.achievement_id],
            earnedAt: row.earned_at
          }));
          resolve(achievements);
        }
      });
    });
  }

  async getLeaderboard(category = 'overall', limit = 10) {
    let query;
    
    switch (category) {
      case 'overall':
        query = `
          SELECT 
            user_id,
            COUNT(*) as total_exercises,
            AVG(accuracy_score) as avg_accuracy,
            (COUNT(*) * AVG(accuracy_score)) as score
          FROM exercise_analytics 
          WHERE created_at >= datetime('now', '-30 days')
          GROUP BY user_id
          ORDER BY score DESC
          LIMIT ?
        `;
        break;
        
      case 'speed':
        query = `
          SELECT 
            user_id,
            AVG(time_to_complete) as avg_time,
            COUNT(*) as total_exercises
          FROM exercise_analytics 
          WHERE created_at >= datetime('now', '-30 days')
          GROUP BY user_id
          HAVING total_exercises >= 5
          ORDER BY avg_time ASC
          LIMIT ?
        `;
        break;
        
      default:
        query = `
          SELECT 
            user_id,
            COUNT(*) as exercises_in_category,
            AVG(accuracy_score) as avg_accuracy
          FROM exercise_analytics 
          WHERE category = ? AND created_at >= datetime('now', '-30 days')
          GROUP BY user_id
          ORDER BY avg_accuracy DESC, exercises_in_category DESC
          LIMIT ?
        `;
    }

    return new Promise((resolve, reject) => {
      const params = category === 'overall' || category === 'speed' ? [limit] : [category, limit];
      
      this.db.all(query, params, (err, rows) => {
        if (err) reject(err);
        else resolve(rows);
      });
    });
  }
}

module.exports = AchievementSystem;